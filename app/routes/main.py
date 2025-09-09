from flask import Blueprint, render_template, request, jsonify, current_app
import logging
import time
from typing import Dict, Any

from app.utils.validators import validate_image_file, sanitize_filename
from app.services.image_processor import ImageProcessor
from app.services.ocr_service import OCRService, OCRServiceError

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    """Home page with file upload interface"""
    return render_template('index.html')

@main_bp.route('/process_image', methods=['POST'])
def process_image():
    """
    Process uploaded business card image
    
    Returns:
        JSON response with extracted information or error message
    """
    try:
        # Validate request
        if 'image' not in request.files:
            logger.warning("No image file in request")
            return jsonify({'error': 'No image file uploaded'}), 400

        file = request.files['image']
        
        if file.filename == '':
            logger.warning("Empty filename in request")
            return jsonify({'error': 'No file selected'}), 400

        # Sanitize filename
        filename = sanitize_filename(file.filename)
        logger.info(f"Processing upload: {filename}")

        # Validate file
        is_valid, error_message = validate_image_file(file, filename)
        if not is_valid:
            logger.warning(f"File validation failed: {error_message}")
            return jsonify({'error': error_message}), 400

        # Process image
        img_processor = ImageProcessor()
        img = img_processor.read_image_from_upload(file)
        
        if img is None:
            logger.error("Failed to read uploaded image")
            return jsonify({'error': 'Failed to process uploaded image'}), 400

        # Apply preprocessing
        processed_img = img_processor.preprocess_image(img)
        
        # Encode image for API
        image_bytes = img_processor.encode_image_for_api(processed_img)
        
        if image_bytes is None:
            logger.error("Failed to encode image")
            return jsonify({'error': 'Failed to process image'}), 500

        # Process through OCR service
        ocr_service = OCRService()
        
        try:
            result = ocr_service.process_image(image_bytes)
            
            logger.info(f"OCR processing completed successfully in {result.processing_time:.2f}s")
            
            # Return structured response
            response_data = result.to_dict()
            
            # Add metadata
            response_data['status'] = 'success'
            response_data['filename'] = filename
            
            return jsonify(response_data)
            
        except OCRServiceError as e:
            logger.error(f"OCR service error: {str(e)}")
            return jsonify({
                'error': 'Failed to process image through OCR service',
                'details': str(e)
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in process_image: {str(e)}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e) if current_app.debug else 'Please try again later'
        }), 500

@main_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check OCR service connectivity
        ocr_service = OCRService()
        ocr_healthy = ocr_service.health_check()
        
        return jsonify({
            'status': 'healthy' if ocr_healthy else 'degraded',
            'ocr_service': 'up' if ocr_healthy else 'down',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@main_bp.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        'error': 'File size too large',
        'max_size': f"{current_app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB"
    }), 413

@main_bp.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@main_bp.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        'error': 'Internal server error',
        'details': str(e) if current_app.debug else 'Please try again later'
    }), 500