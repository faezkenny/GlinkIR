"""
FastAPI backend for IRPhotolink.
Handles photo link scraping and image search requests.
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
import asyncio
import json
from scraper import scrape_photo_links
from processor import get_processor, ImageProcessor
import uvicorn

app = FastAPI(title="IRPhotolink API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        for album_url, image_urls in image_urls_by_album.items():
            matching_images = []
            
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
            
            results[album_url] = matching_images
        
        # Count total matches
        total_matches = sum(len(urls) for urls in results.values())
        print(f"Found {total_matches} matching images")
        
        return JSONResponse(content={
            "message": f"Found {total_matches} matching images",
            "results": results,
            "total_matches": total_matches,
            "total_images_searched": total_images
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
