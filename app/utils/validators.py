import os
from typing import BinaryIO, Tuple, Optional
from flask import current_app
import cv2
import numpy as np
from config import config

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in config.ALLOWED_EXTENSIONS

def validate_file_size(file: BinaryIO) -> bool:
    """Validate file size without loading entire file into memory"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= config.MAX_FILE_SIZE

def validate_image_file(file: BinaryIO, filename: str) -> Tuple[bool, Optional[str]]:
    """Comprehensive image file validation"""
    
    # Check filename
    if not allowed_file(filename):
        return False, f"File type not allowed. Allowed types: {', '.join(config.ALLOWED_EXTENSIONS)}"
    
    # Check file size
    if not validate_file_size(file):
        max_size_mb = config.MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum allowed size of {max_size_mb}MB"
    
    # Check if file is actually an image by trying to read it
    try:
        file.seek(0)
        file_bytes = file.read()
        file.seek(0)
        
        # Try to decode as image
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return False, "File is not a valid image"
            
        # Check image dimensions (optional - prevent extremely large images)
        height, width = img.shape[:2]
        if height > 10000 or width > 10000:
            return False, "Image dimensions too large"
            
        return True, None
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    if not filename:
        return "upload"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename is not empty after sanitization
    if not filename or filename.startswith('.'):
        filename = f"upload_{filename}"
    
    return filename