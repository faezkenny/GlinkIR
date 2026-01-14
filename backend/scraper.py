"""
Scraper module for extracting image URLs from public cloud photo links.
Currently supports Google Photos shared album links.
"""
import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, Page
import re


class PhotoScraper:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_google_photos(self, url: str) -> List[str]:
        """
        Scrape Google Photos shared album link to extract all image URLs.
        
        Args:
            url: Google Photos shared album URL
            
        Returns:
            List of direct image URLs
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")
        
        page = await self.browser.new_page()
        image_urls = []
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for images to load
            await page.wait_for_timeout(3000)
            
            # Scroll to load all images (Google Photos uses infinite scroll)
            last_height = 0
            scroll_attempts = 0
            max_scrolls = 50  # Prevent infinite loops
            
            while scroll_attempts < max_scrolls:
                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)  # Wait for images to load
                
                # Check if we've reached the bottom
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Extract image URLs
            # Google Photos stores images in various formats, we'll look for img tags and background images
            images = await page.query_selector_all("img")
            
            for img in images:
                src = await img.get_attribute("src")
                if src and ("googleusercontent.com" in src or "google.com" in src):
                    # Convert to full resolution if possible
                    # Google Photos URLs can be modified to get higher resolution
                    if "=w" in src or "=h" in src:
                        # Replace with higher resolution (s2048 for width/height)
                        src = re.sub(r'=w\d+-h\d+', '=s2048', src)
                        src = re.sub(r'=w\d+', '=s2048', src)
                        src = re.sub(r'=h\d+', '=s2048', src)
                    image_urls.append(src)
            
            # Also check for background images in divs
            divs = await page.query_selector_all("div[style*='background-image']")
            for div in divs:
                style = await div.get_attribute("style")
                if style:
                    match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                    if match:
                        img_url = match.group(1)
                        if "googleusercontent.com" in img_url or "google.com" in img_url:
                            if "=w" in img_url or "=h" in img_url:
                                img_url = re.sub(r'=w\d+-h\d+', '=s2048', img_url)
                                img_url = re.sub(r'=w\d+', '=s2048', img_url)
                                img_url = re.sub(r'=h\d+', '=s2048', img_url)
                            if img_url not in image_urls:
                                image_urls.append(img_url)
        
        except Exception as e:
            print(f"Error scraping Google Photos: {e}")
        finally:
            await page.close()
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in image_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls

    async def scrape_link(self, url: str) -> List[str]:
        """
        Generic scraper that detects the type of link and uses appropriate method.
        
        Args:
            url: Public photo album link
            
        Returns:
            List of direct image URLs
        """
        if "photos.google.com" in url or "photos.app.goo.gl" in url:
            return await self.scrape_google_photos(url)
        else:
            # For other cloud services, try generic scraping
            return await self.scrape_generic(url)

    async def scrape_generic(self, url: str) -> List[str]:
        """
        Generic scraper for other cloud photo services.
        Attempts to find all image URLs on the page.
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")
        
        page = await self.browser.new_page()
        image_urls = []
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)
            
            # Scroll to load all images
            last_height = 0
            scroll_attempts = 0
            max_scrolls = 30
            
            while scroll_attempts < max_scrolls:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Extract all image URLs
            images = await page.query_selector_all("img")
            for img in images:
                src = await img.get_attribute("src")
                if src and src.startswith(("http://", "https://")):
                    # Filter out small icons/thumbnails
                    if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        if src not in image_urls:
                            image_urls.append(src)
        
        except Exception as e:
            print(f"Error scraping generic link: {e}")
        finally:
            await page.close()
        
        return image_urls


async def scrape_photo_links(urls: List[str]) -> dict:
    """
    Scrape multiple photo links and return a dictionary mapping URLs to image lists.
    
    Args:
        urls: List of public photo album URLs (up to 5)
        
    Returns:
        Dictionary with structure: {album_url: [image_url1, image_url2, ...]}
    """
    results = {}
    
    async with PhotoScraper() as scraper:
        for url in urls:
            if url.strip():
                try:
                    print(f"Scraping {url}...")
                    images = await scraper.scrape_link(url.strip())
                    results[url] = images
                    print(f"Found {len(images)} images in {url}")
                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")
                    results[url] = []
    
    return results
