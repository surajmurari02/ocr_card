import cv2
import numpy as np
from typing import BinaryIO, Tuple, Optional
import io
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Service for image processing operations"""
    
    @staticmethod
    def read_image_from_upload(file: BinaryIO) -> Optional[np.ndarray]:
        """Read image from uploaded file"""
        try:
            # Read file into memory
            in_memory_file = io.BytesIO()
            file.save(in_memory_file)
            data = np.frombuffer(in_memory_file.getvalue(), dtype=np.uint8)
            
            # Decode image
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Failed to decode image")
                return None
                
            logger.info(f"Image loaded successfully with shape: {img.shape}")
            return img
            
        except Exception as e:
            logger.error(f"Error reading image from upload: {str(e)}")
            return None
    
    @staticmethod
    def encode_image_for_api(img: np.ndarray, format: str = '.jpg', quality: int = 85) -> Optional[bytes]:
        """Encode image for API transmission"""
        try:
            # Set compression parameters
            encode_params = []
            if format.lower() in ['.jpg', '.jpeg']:
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            elif format.lower() == '.png':
                encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
            
            # Encode image
            success, encoded_image = cv2.imencode(format, img, encode_params)
            
            if not success:
                logger.error(f"Failed to encode image as {format}")
                return None
                
            image_bytes = encoded_image.tobytes()
            logger.info(f"Image encoded successfully as {format}, size: {len(image_bytes)} bytes")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Error encoding image: {str(e)}")
            return None
    
    @staticmethod
    def preprocess_image(img: np.ndarray) -> np.ndarray:
        """Apply preprocessing to improve OCR accuracy"""
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Auto-rotate if needed (detect text orientation)
            # This is a simplified version - more sophisticated methods exist
            processed_img = img.copy()
            
            # Enhance contrast if image is too dark/bright
            mean_intensity = np.mean(gray)
            if mean_intensity < 100:  # Too dark
                processed_img = cv2.convertScaleAbs(processed_img, alpha=1.2, beta=20)
                logger.info("Applied brightness enhancement")
            elif mean_intensity > 200:  # Too bright
                processed_img = cv2.convertScaleAbs(processed_img, alpha=0.8, beta=-10)
                logger.info("Applied brightness reduction")
            
            # Noise reduction
            processed_img = cv2.bilateralFilter(processed_img, 9, 75, 75)
            logger.info("Applied noise reduction")
            
            return processed_img
            
        except Exception as e:
            logger.error(f"Error in image preprocessing: {str(e)}")
            return img  # Return original image if preprocessing fails