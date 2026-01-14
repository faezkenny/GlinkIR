"""
Image processing module for facial recognition and OCR.
Implements high recall strategy to minimize false negatives.
"""
import face_recognition
import easyocr
import cv2
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from typing import List, Dict, Optional, Tuple
import hashlib
import os
import json
import re


class ImageProcessor:
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize the image processor with OCR reader and cache directory.
        
        Args:
            cache_dir: Directory to cache processed image data
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize EasyOCR reader (supports multiple languages)
        # Using English by default, can be extended
        print("Initializing EasyOCR...")
        self.ocr_reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR initialized.")
        
        # High recall tolerance for face recognition (more permissive = higher recall)
        # Default is 0.6, we use 0.7-0.8 to catch more potential matches
        self.face_tolerance = 0.75
        
        # Lower confidence threshold for OCR to catch more text
        self.ocr_confidence_threshold = 0.3

    def _get_cache_key(self, image_url: str) -> str:
        """Generate a cache key for an image URL."""
        return hashlib.md5(image_url.encode()).hexdigest()

    def _load_image_from_url(self, url: str) -> Optional[np.ndarray]:
        """
        Load an image from a URL.
        
        Args:
            url: Image URL
            
        Returns:
            numpy array of the image, or None if failed
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            return np.array(image)
        except Exception as e:
            print(f"Error loading image from {url}: {e}")
            return None

    def encode_face_from_image(self, image_data: bytes) -> Optional[List[np.ndarray]]:
        """
        Encode faces from uploaded image data.
        
        Args:
            image_data: Bytes of the uploaded image
            
        Returns:
            List of face encodings, or None if no faces found
        """
        try:
            image = Image.open(BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image_array = np.array(image)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image_array)
            
            if not face_locations:
                return None
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            return face_encodings
        except Exception as e:
            print(f"Error encoding face: {e}")
            return None

    def find_faces_in_image(self, image_url: str, target_encodings: List[np.ndarray]) -> bool:
        """
        Check if any target faces are found in an image.
        Uses high recall tolerance to minimize false negatives.
        
        Args:
            image_url: URL of the image to check
            target_encodings: List of face encodings to search for
            
        Returns:
            True if a match is found, False otherwise
        """
        cache_key = self._get_cache_key(image_url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}_faces.json")
        
        # Check cache first
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_encodings = json.load(f)
                    cached_encodings = [np.array(enc) for enc in cached_encodings]
                    
                    # Compare with target encodings
                    for target_enc in target_encodings:
                        matches = face_recognition.compare_faces(
                            cached_encodings, 
                            target_enc, 
                            tolerance=self.face_tolerance
                        )
                        if any(matches):
                            return True
                    return False
            except Exception as e:
                print(f"Error reading cache: {e}")
        
        # Load and process image
        image_array = self._load_image_from_url(image_url)
        if image_array is None:
            return False
        
        try:
            # Find faces in the image
            face_locations = face_recognition.face_locations(image_array)
            
            if not face_locations:
                # Cache empty result
                with open(cache_file, 'w') as f:
                    json.dump([], f)
                return False
            
            # Get encodings for all faces found
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            # Cache the encodings
            try:
                with open(cache_file, 'w') as f:
                    json.dump([enc.tolist() for enc in face_encodings], f)
            except Exception as e:
                print(f"Error caching face encodings: {e}")
            
            # Compare with target encodings using high recall tolerance
            for target_enc in target_encodings:
                matches = face_recognition.compare_faces(
                    face_encodings,
                    target_enc,
                    tolerance=self.face_tolerance  # More permissive = higher recall
                )
                if any(matches):
                    return True
            
            return False
        except Exception as e:
            print(f"Error processing faces in {image_url}: {e}")
            return False

    def find_text_in_image(self, image_url: str, search_text: str) -> bool:
        """
        Search for text (jersey number or other text) in an image using OCR.
        Uses lower confidence threshold for higher recall.
        
        Args:
            image_url: URL of the image to check
            search_text: Text to search for (case-insensitive)
            
        Returns:
            True if text is found, False otherwise
        """
        cache_key = self._get_cache_key(image_url)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}_text.json")
        
        # Check cache first
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_texts = json.load(f)
                    search_text_lower = search_text.lower().strip()
                    for cached_text in cached_texts:
                        if search_text_lower in cached_text.lower():
                            return True
                    return False
            except Exception as e:
                print(f"Error reading text cache: {e}")
        
        # Load image
        image_array = self._load_image_from_url(image_url)
        if image_array is None:
            return False
        
        try:
            # Run OCR with lower confidence threshold for higher recall
            results = self.ocr_reader.readtext(image_array)
            
            # Extract all detected text
            detected_texts = []
            for (bbox, text, confidence) in results:
                if confidence >= self.ocr_confidence_threshold:
                    detected_texts.append(text)
            
            # Cache the results
            try:
                with open(cache_file, 'w') as f:
                    json.dump(detected_texts, f)
            except Exception as e:
                print(f"Error caching OCR results: {e}")
            
            # Check if search text is in any detected text
            search_text_lower = search_text.lower().strip()
            search_text_clean = re.sub(r'[^\w\s]', '', search_text_lower)  # Remove punctuation
            
            for detected_text in detected_texts:
                detected_lower = detected_text.lower()
                detected_clean = re.sub(r'[^\w\s]', '', detected_lower)
                
                # Direct match
                if search_text_lower in detected_lower:
                    return True
                
                # Clean match (without punctuation)
                if search_text_clean in detected_clean:
                    return True
                
                # For numbers, also check if the number appears as standalone or in context
                if search_text_clean.isdigit():
                    # Look for the number as a word or standalone
                    number_pattern = r'\b' + re.escape(search_text_clean) + r'\b'
                    if re.search(number_pattern, detected_clean):
                        return True
            
            return False
        except Exception as e:
            print(f"Error processing text in {image_url}: {e}")
            return False

    def process_images(
        self,
        image_urls_by_album: Dict[str, List[str]],
        face_encodings: Optional[List[np.ndarray]] = None,
        search_text: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Process multiple images and return matches.
        
        Args:
            image_urls_by_album: Dictionary mapping album URLs to lists of image URLs
            face_encodings: Optional list of face encodings to search for
            search_text: Optional text to search for
            
        Returns:
            Dictionary mapping album URLs to lists of matching image URLs
        """
        results = {}
        
        for album_url, image_urls in image_urls_by_album.items():
            matching_images = []
            
            for image_url in image_urls:
                match_found = False
                
                # Check face match if face encodings provided
                if face_encodings:
                    if self.find_faces_in_image(image_url, face_encodings):
                        match_found = True
                
                # Check text match if search text provided
                if search_text and not match_found:
                    if self.find_text_in_image(image_url, search_text):
                        match_found = True
                
                if match_found:
                    matching_images.append(image_url)
            
            results[album_url] = matching_images
        
        return results

    def _bytes_to_rgb_np(self, image_bytes: bytes) -> np.ndarray:
        """Convert image bytes to RGB numpy array."""
        img = Image.open(BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        return np.array(img)

    def find_faces_in_uploaded_bytes(self, image_bytes: bytes, target_encodings: List[np.ndarray]) -> bool:
        """
        Check if any target faces are found in an image from bytes.
        Uses high recall tolerance to minimize false negatives.
        
        Args:
            image_bytes: Image data as bytes
            target_encodings: List of face encodings to search for
            
        Returns:
            True if a match is found, False otherwise
        """
        try:
            image_array = self._bytes_to_rgb_np(image_bytes)
            
            # Find faces in the image
            face_locations = face_recognition.face_locations(image_array)
            
            if not face_locations:
                return False
            
            # Get encodings for all faces found
            face_encodings = face_recognition.face_encodings(image_array, face_locations)
            
            # Compare with target encodings using high recall tolerance
            for target_enc in target_encodings:
                matches = face_recognition.compare_faces(
                    face_encodings,
                    target_enc,
                    tolerance=self.face_tolerance  # More permissive = higher recall
                )
                if any(matches):
                    return True
            
            return False
        except Exception as e:
            print(f"Error processing faces from bytes: {e}")
            return False

    def find_text_in_uploaded_bytes(self, image_bytes: bytes, search_text: str) -> bool:
        """
        Search for text (jersey number or other text) in an image from bytes using OCR.
        Uses lower confidence threshold for higher recall.
        
        Args:
            image_bytes: Image data as bytes
            search_text: Text to search for (case-insensitive)
            
        Returns:
            True if text is found, False otherwise
        """
        try:
            image_array = self._bytes_to_rgb_np(image_bytes)
            
            # Run OCR with lower confidence threshold for higher recall
            results = self.ocr_reader.readtext(image_array)
            
            # Extract all detected text
            detected_texts = []
            for (bbox, text, confidence) in results:
                if confidence >= self.ocr_confidence_threshold:
                    detected_texts.append(text)
            
            # Check if search text is in any detected text
            search_text_lower = search_text.lower().strip()
            search_text_clean = re.sub(r'[^\w\s]', '', search_text_lower)  # Remove punctuation
            
            for detected_text in detected_texts:
                detected_lower = detected_text.lower()
                detected_clean = re.sub(r'[^\w\s]', '', detected_lower)
                
                # Direct match
                if search_text_lower in detected_lower:
                    return True
                
                # Clean match (without punctuation)
                if search_text_clean in detected_clean:
                    return True
                
                # For numbers, also check if the number appears as standalone or in context
                if search_text_clean.isdigit():
                    # Look for the number as a word or standalone
                    number_pattern = r'\b' + re.escape(search_text_clean) + r'\b'
                    if re.search(number_pattern, detected_clean):
                        return True
            
            return False
        except Exception as e:
            print(f"Error processing text from bytes: {e}")
            return False


# Global processor instance (will be initialized in main.py)
processor: Optional[ImageProcessor] = None

def get_processor() -> ImageProcessor:
    """Get or create the global processor instance."""
    global processor
    if processor is None:
        processor = ImageProcessor()
    return processor
