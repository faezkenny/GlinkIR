"""
FastAPI backend for IRPhotolink.
Handles photo link scraping and image search requests.
Supports Google Drive and OneDrive via OAuth + API.
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
import secrets
import httpx
from scraper import scrape_photo_links
from processor import get_processor, ImageProcessor
from cloud_providers import (
    detect_provider,
    extract_google_drive_folder_id,
    list_google_drive_images,
    download_google_drive_file,
    list_onedrive_images,
    download_onedrive_file,
)
import uvicorn

app = FastAPI(title="IRPhotolink API", version="1.1.0")

# Configuration from environment
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:8080")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/auth/microsoft/callback")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (replace with Redis/DB in production)
SESSIONS: Dict[str, Dict[str, Any]] = {}
OAUTH_STATES: Dict[str, Dict[str, Any]] = {}
JOBS: Dict[str, Dict[str, Any]] = {}

# Initialize processor
processor: Optional[ImageProcessor] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the image processor on startup."""
    global processor
    processor = get_processor()
    print("Image processor initialized.")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "IRPhotolink API is running"}


@app.post("/search")
async def search_photos(
    links: str = Form(...),
    face_image: Optional[UploadFile] = File(None),
    search_text: Optional[str] = Form(None)
):
    """
    Search for photos matching face or text criteria across multiple cloud links.
    
    Args:
        links: Comma-separated list of up to 5 photo album URLs
        face_image: Optional image file for face matching
        search_text: Optional text/jersey number to search for
        
    Returns:
        Dictionary mapping album URLs to lists of matching image URLs
    """
    # Validate inputs
    if not face_image and not search_text:
        raise HTTPException(
            status_code=400,
            detail="Either face_image or search_text must be provided"
        )
    
    # Parse links (comma-separated, max 5)
    link_list = [link.strip() for link in links.split(",") if link.strip()]
    
    if len(link_list) == 0:
        raise HTTPException(status_code=400, detail="At least one link is required")
    
    if len(link_list) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 links allowed")
    
    # Validate URLs
    for link in link_list:
        if not link.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL format: {link}"
            )
    
    try:
        # Step 1: Scrape all links to get image URLs
        print(f"Scraping {len(link_list)} links...")
        image_urls_by_album = await scrape_photo_links(link_list)
        
        # Check if we got any images
        total_images = sum(len(urls) for urls in image_urls_by_album.values())
        if total_images == 0:
            return JSONResponse(content={
                "message": "No images found in the provided links",
                "results": {}
            })
        
        print(f"Found {total_images} total images across all albums")
        
        # Step 2: Process images based on search criteria
        face_encodings = None
        
        if face_image:
            # Read and encode face from uploaded image
            image_data = await face_image.read()
            face_encodings = processor.encode_face_from_image(image_data)
            
            if not face_encodings:
                raise HTTPException(
                    status_code=400,
                    detail="No faces detected in the uploaded image"
                )
            
            print(f"Encoded {len(face_encodings)} face(s) from uploaded image")
        
        # Step 3: Search for matches
        print("Processing images for matches...")
        
        # Process images with progress tracking
        results = {}
        processed_count = 0
        
        # Calculate total images for progress tracking
        total_images_to_process = total_images
        
        for album_url, image_urls in image_urls_by_album.items():
            matching_images = []
            
            print(f"Processing {len(image_urls)} images from {album_url}")
            
            for idx, image_url in enumerate(image_urls):
                match_found = False
                
                # Check face match if face encodings provided
                if face_encodings:
                    if processor.find_faces_in_image(image_url, face_encodings):
                        match_found = True
                
                # Check text match if search text provided
                if search_text and not match_found:
                    if processor.find_text_in_image(image_url, search_text):
                        match_found = True
                
                if match_found:
                    matching_images.append(image_url)
                
                processed_count += 1
                
                # Log progress every 10 images or at the end
                if (processed_count % 10 == 0) or (processed_count == total_images_to_process):
                    print(f"Processed {processed_count}/{total_images_to_process} images...")
            
            results[album_url] = matching_images
        
        # Count total matches
        total_matches = sum(len(urls) for urls in results.values())
        print(f"Found {total_matches} matching images")
        
        return JSONResponse(content={
            "message": f"Found {total_matches} matching images",
            "results": results,
            "total_matches": total_matches,
            "total_images_searched": total_images,
            "images_by_album": {url: len(urls) for url, urls in image_urls_by_album.items()}
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing search request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "processor_initialized": processor is not None
    }


# ==================== OAuth Endpoints ====================

def _get_or_create_session_id(request: Request) -> str:
    """Get or create session ID from cookie."""
    sid = request.cookies.get("irpl_sid")
    if not sid:
        sid = secrets.token_urlsafe(24)
    if sid not in SESSIONS:
        SESSIONS[sid] = {"google_token": None, "microsoft_token": None}
    return sid


def _require_google_token(request: Request) -> str:
    """Require Google access token."""
    sid = request.cookies.get("irpl_sid")
    if not sid or sid not in SESSIONS or not SESSIONS[sid].get("google_token"):
        raise HTTPException(status_code=401, detail="Not logged in with Google")
    return SESSIONS[sid]["google_token"]["access_token"]


def _require_microsoft_token(request: Request) -> str:
    """Require Microsoft access token."""
    sid = request.cookies.get("irpl_sid")
    if not sid or sid not in SESSIONS or not SESSIONS[sid].get("microsoft_token"):
        raise HTTPException(status_code=401, detail="Not logged in with Microsoft")
    return SESSIONS[sid]["microsoft_token"]["access_token"]


@app.get("/auth/google/start")
async def google_auth_start(request: Request):
    """Start Google OAuth flow."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    
    sid = _get_or_create_session_id(request)
    state = secrets.token_urlsafe(24)
    OAUTH_STATES[state] = {"sid": sid, "provider": "google"}
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    
    auth_url = httpx.URL("https://accounts.google.com/o/oauth2/v2/auth").copy_add_params(params)
    resp = RedirectResponse(str(auth_url), status_code=302)
    resp.set_cookie("irpl_sid", sid, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.get("/auth/google/callback")
async def google_auth_callback(code: str, state: str):
    """Handle Google OAuth callback."""
    if state not in OAUTH_STATES or OAUTH_STATES[state]["provider"] != "google":
        raise HTTPException(status_code=400, detail="Invalid state")
    
    sid = OAUTH_STATES.pop(state)["sid"]
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    
    token_data = token_res.json()
    if token_res.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=token_data.get("error_description") or "Token exchange failed"
        )
    
    SESSIONS[sid]["google_token"] = token_data
    
    resp = RedirectResponse(FRONTEND_ORIGIN, status_code=302)
    resp.set_cookie("irpl_sid", sid, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.get("/auth/microsoft/start")
async def microsoft_auth_start(request: Request):
    """Start Microsoft OAuth flow."""
    if not MICROSOFT_CLIENT_ID:
        raise HTTPException(status_code=500, detail="MICROSOFT_CLIENT_ID not configured")
    
    sid = _get_or_create_session_id(request)
    state = secrets.token_urlsafe(24)
    OAUTH_STATES[state] = {"sid": sid, "provider": "microsoft"}
    
    params = {
        "client_id": MICROSOFT_CLIENT_ID,
        "redirect_uri": MICROSOFT_REDIRECT_URI,
        "response_type": "code",
        "scope": "Files.Read offline_access",
        "state": state,
    }
    
    auth_url = httpx.URL("https://login.microsoftonline.com/common/oauth2/v2.0/authorize").copy_add_params(params)
    resp = RedirectResponse(str(auth_url), status_code=302)
    resp.set_cookie("irpl_sid", sid, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.get("/auth/microsoft/callback")
async def microsoft_auth_callback(code: str, state: str):
    """Handle Microsoft OAuth callback."""
    if state not in OAUTH_STATES or OAUTH_STATES[state]["provider"] != "microsoft":
        raise HTTPException(status_code=400, detail="Invalid state")
    
    sid = OAUTH_STATES.pop(state)["sid"]
    
    if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Microsoft OAuth not configured")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_res = await client.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": MICROSOFT_CLIENT_ID,
                "client_secret": MICROSOFT_CLIENT_SECRET,
                "code": code,
                "redirect_uri": MICROSOFT_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    
    token_data = token_res.json()
    if token_res.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=token_data.get("error_description") or "Token exchange failed"
        )
    
    SESSIONS[sid]["microsoft_token"] = token_data
    
    resp = RedirectResponse(FRONTEND_ORIGIN, status_code=302)
    resp.set_cookie("irpl_sid", sid, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@app.get("/auth/me")
async def auth_me(request: Request):
    """Check authentication status."""
    sid = request.cookies.get("irpl_sid")
    if not sid or sid not in SESSIONS:
        return {"loggedIn": False, "google": False, "microsoft": False}
    
    session = SESSIONS[sid]
    return {
        "loggedIn": bool(session.get("google_token") or session.get("microsoft_token")),
        "google": bool(session.get("google_token")),
        "microsoft": bool(session.get("microsoft_token")),
    }


# ==================== Job Queue Endpoints ====================

async def _run_job(
    job_id: str,
    folder_url: str,
    search_text: Optional[str],
    face_bytes: Optional[bytes],
    request: Request,
):
    """Run a search job in the background."""
    job = JOBS[job_id]
    provider = detect_provider(folder_url)
    
    try:
        job["phase"] = "listing"
        
        # Get files based on provider
        if provider == "google_drive":
            access_token = _require_google_token(request)
            folder_id = extract_google_drive_folder_id(folder_url)
            files = await list_google_drive_images(access_token, folder_id)
            job["total"] = len(files)
            
            job["phase"] = "processing"
            face_encodings = None
            if face_bytes:
                face_encodings = processor.encode_face_from_image(face_bytes)
            
            for file_info in files:
                try:
                    img_bytes = await download_google_drive_file(access_token, file_info["id"])
                    
                    matched = False
                    if face_encodings:
                        matched = processor.find_faces_in_uploaded_bytes(img_bytes, face_encodings)
                    if (not matched) and search_text:
                        matched = processor.find_text_in_uploaded_bytes(img_bytes, search_text)
                    
                    if matched:
                        job["matches"].append({
                            "fileId": file_info["id"],
                            "name": file_info.get("name"),
                            "thumbnailLink": file_info.get("thumbnailLink"),
                            "webContentLink": file_info.get("webContentLink"),
                        })
                except Exception as e:
                    job["errors"].append({
                        "fileId": file_info.get("id"),
                        "name": file_info.get("name"),
                        "error": str(e),
                    })
                finally:
                    job["processed"] += 1
        
        elif provider == "onedrive":
            access_token = _require_microsoft_token(request)
            files = await list_onedrive_images(access_token, folder_url)
            job["total"] = len(files)
            
            job["phase"] = "processing"
            face_encodings = None
            if face_bytes:
                face_encodings = processor.encode_face_from_image(face_bytes)
            
            for file_info in files:
                try:
                    img_bytes = await download_onedrive_file(access_token, file_info["id"])
                    
                    matched = False
                    if face_encodings:
                        matched = processor.find_faces_in_uploaded_bytes(img_bytes, face_encodings)
                    if (not matched) and search_text:
                        matched = processor.find_text_in_uploaded_bytes(img_bytes, search_text)
                    
                    if matched:
                        job["matches"].append({
                            "fileId": file_info["id"],
                            "name": file_info.get("name"),
                            "webUrl": file_info.get("webUrl"),
                            "downloadUrl": file_info.get("@microsoft.graph.downloadUrl"),
                        })
                except Exception as e:
                    job["errors"].append({
                        "fileId": file_info.get("id"),
                        "name": file_info.get("name"),
                        "error": str(e),
                    })
                finally:
                    job["processed"] += 1
        
        else:
            raise Exception(f"Unsupported provider: {provider}")
        
        job["phase"] = "done"
    
    except Exception as e:
        job["phase"] = "error"
        job["error"] = str(e)


def _job_public(job: Dict[str, Any]) -> Dict[str, Any]:
    """Return public job data."""
    return {
        "jobId": job["jobId"],
        "phase": job["phase"],
        "processed": job["processed"],
        "total": job["total"],
        "matches": job["matches"][-100:],  # Last 100 matches
        "errors": job["errors"][-20:],    # Last 20 errors
        "error": job.get("error"),
    }


@app.post("/jobs/start")
async def jobs_start(
    request: Request,
    folder_url: str = Form(...),
    search_text: Optional[str] = Form(None),
    face_image: Optional[UploadFile] = File(None),
):
    """Start a new search job."""
    provider = detect_provider(folder_url)
    
    if provider == "google_drive":
        _require_google_token(request)
    elif provider == "onedrive":
        _require_microsoft_token(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider. Please use Google Drive or OneDrive links.")
    
    face_bytes = None
    if face_image:
        face_bytes = await face_image.read()
    
    if not face_bytes and not search_text:
        raise HTTPException(status_code=400, detail="Either face_image or search_text must be provided")
    
    job_id = secrets.token_urlsafe(16)
    JOBS[job_id] = {
        "jobId": job_id,
        "phase": "queued",
        "processed": 0,
        "total": 0,
        "matches": [],
        "errors": [],
    }
    
    # Start background task
    asyncio.create_task(_run_job(job_id, folder_url, search_text, face_bytes, request))
    
    return _job_public(JOBS[job_id])


@app.get("/jobs/{job_id}/status")
async def jobs_status(job_id: str):
    """Get job status."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_public(JOBS[job_id])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
