"""
Cloud provider integrations for Google Drive and OneDrive.
Handles OAuth and file listing/downloading.
"""
import httpx
import re
from typing import List, Dict, Any, Optional
import base64
import hashlib


def detect_provider(url: str) -> str:
    """Detect cloud provider from URL."""
    if "drive.google.com" in url or "docs.google.com" in url:
        return "google_drive"
    elif "onedrive.live.com" in url or "1drv.ms" in url or "sharepoint.com" in url:
        return "onedrive"
    else:
        return "unknown"


def extract_google_drive_folder_id(folder_url: str) -> str:
    """Extract folder ID from Google Drive URL."""
    patterns = [
        r"/folders/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, folder_url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract folder ID from URL: {folder_url}")


def extract_onedrive_share_id(url: str) -> Optional[str]:
    """Extract share ID or convert OneDrive URL to shareable format."""
    # OneDrive URLs can be in various formats
    # For now, we'll use the URL as-is and let Graph API handle it
    # In production, you might want to convert short URLs to full URLs
    return url


async def list_google_drive_images(access_token: str, folder_id: str) -> List[Dict[str, Any]]:
    """List all image files in a Google Drive folder."""
    files: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {
                "q": query,
                "fields": "nextPageToken,files(id,name,mimeType,thumbnailLink,webContentLink)",
                "pageSize": 1000,
            }
            if page_token:
                params["pageToken"] = page_token
            
            response = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Drive API error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            
            data = response.json()
            files.extend(data.get("files", []))
            
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    
    return files


async def download_google_drive_file(access_token: str, file_id: str) -> bytes:
    """Download a file from Google Drive."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            url,
            params={"alt": "media"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to download file {file_id}: {response.status_code}")
        
        return response.content


async def list_onedrive_images(access_token: str, share_url: str) -> List[Dict[str, Any]]:
    """List all image files in a OneDrive shared folder."""
    # Convert share URL to shareId format for Graph API
    # OneDrive share URLs need to be base64url encoded
    share_id = base64.urlsafe_b64encode(share_url.encode()).decode().rstrip('=')
    
    files: List[Dict[str, Any]] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Method 1: Use shares endpoint to resolve the share
        try:
            share_response = await client.get(
                f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if share_response.status_code == 200:
                drive_item = share_response.json()
                
                # If it's a folder, list children
                if drive_item.get("folder"):
                    children_url = f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/children"
                else:
                    # Single file - return if it's an image
                    mime_type = drive_item.get("mimeType", "").lower()
                    if "image" in mime_type:
                        return [drive_item]
                    else:
                        return []
            else:
                # Method 2: Try using /me/drive/root if share doesn't work
                # Extract item ID from URL if possible
                raise Exception("Share resolution failed, trying alternative method")
        except Exception:
            # Fallback: Try to use /me/drive/root with path
            # This requires the URL to be in a specific format
            # For now, we'll raise an error and suggest using the share endpoint
            raise Exception("OneDrive share URL format not supported. Please use a shared folder link.")
        
        # List children (images only)
        next_link: Optional[str] = None
        while True:
            if next_link:
                url = next_link
                params = None
            else:
                url = children_url
                params = {
                    "$filter": "mimeType contains 'image/'",
                    "$select": "id,name,mimeType,webUrl,@microsoft.graph.downloadUrl",
                    "$top": 1000,
                }
            
            response = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Graph API error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            
            data = response.json()
            files.extend(data.get("value", []))
            
            next_link = data.get("@odata.nextLink")
            if not next_link:
                break
    
    return files


async def download_onedrive_file(access_token: str, file_id: str) -> bytes:
    """Download a file from OneDrive using Graph API."""
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to download file {file_id}: {response.status_code}")
        
        return response.content
