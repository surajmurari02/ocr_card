#!/usr/bin/env python3
"""
OCR Card - Standalone Processing Script

This script provides a command-line interface for processing business cards
using the new improved architecture with proper error handling and configuration.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add app directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import config
from app.services.ocr_service import OCRService, OCRServiceError
from app.services.image_processor import ImageProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_business_card(image_path: str, output_format: str = 'json') -> None:
    """
    Process a business card image from command line
    
    Args:
        image_path: Path to the business card image
        output_format: Output format (json, pretty)
    """
    try:
        # Validate image path
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return
        
        # Read and process image
        import cv2
        img = cv2.imread(image_path)
        
        if img is None:
            logger.error(f"Failed to read image: {image_path}")
            return
        
        logger.info(f"Processing image: {image_path}")
        
        # Apply preprocessing
        img_processor = ImageProcessor()
        processed_img = img_processor.preprocess_image(img)
        
        # Encode for API
        image_bytes = img_processor.encode_image_for_api(processed_img)
        
        if image_bytes is None:
            logger.error("Failed to encode image")
            return
        
        # Process through OCR service
        ocr_service = OCRService()
        result = ocr_service.process_image(image_bytes)
        
        # Output results
        print("\n" + "="*50)
        print("BUSINESS CARD ANALYSIS RESULTS")
        print("="*50)
        
        if output_format == 'pretty':
            print(f"Name: {result.name or 'Not found'}")
            print(f"Designation: {result.designation or 'Not found'}")
            print(f"Company: {result.company or 'Not found'}")
            print(f"Mobile: {result.mobile or 'Not found'}")
            print(f"Email: {result.email or 'Not found'}")
            print(f"Address: {result.address or 'Not found'}")
            print(f"Processing Time: {result.processing_time:.2f}s")
        else:
            print(result.to_json())
        
        print("="*50)
        logger.info(f"Processing completed in {result.processing_time:.2f} seconds")
        
    except OCRServiceError as e:
        logger.error(f"OCR service error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

def main():
    """Main function for command line interface"""
    parser = argparse.ArgumentParser(description='Process business card images using OCR')
    parser.add_argument('image_path', help='Path to the business card image')
    parser.add_argument('-f', '--format', choices=['json', 'pretty'], default='pretty',
                        help='Output format (default: pretty)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Process the image
    process_business_card(args.image_path, args.format)

if __name__ == '__main__':
    main()