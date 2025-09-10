#!/usr/bin/env python3
"""
Vercel Serverless Function for CardScan Pro
Simplified entry point for Vercel deployment without heavy dependencies
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import base64
from io import BytesIO
from PIL import Image
import time
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OCRResult:
    """Data class for OCR processing results"""
    name: Optional[str] = None
    designation: Optional[str] = None
    company: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    raw_response: Optional[Dict[Any, Any]] = None
    
    @classmethod
    def from_api_response(cls, response_data: Dict[Any, Any], processing_time: float = None) -> 'OCRResult':
        """Create OCRResult from API response"""
        return cls(
            name=response_data.get('name'),
            designation=response_data.get('designation'),
            company=response_data.get('company', response_data.get('company_name')),
            mobile=response_data.get('mobile', response_data.get('phone')),
            email=response_data.get('email'),
            address=response_data.get('address'),
            processing_time=processing_time,
            raw_response=response_data
        )

class OCRServiceError(Exception):
    """Custom exception for OCR service errors"""
    pass

def call_ocr_api(image_bytes: bytes) -> OCRResult:
    """
    Call the OCR API to process business card image
    
    Args:
        image_bytes: Image data as bytes
        
    Returns:
        OCRResult object with extracted information
        
    Raises:
        OCRServiceError: If processing fails
    """
    # Configuration
    OCR_API_URL = os.getenv('OCR_API_URL', 'http://3.108.164.82:1428/upload')
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '1.0'))
    
    query = ("I am providing business cards. I want JSON output with keys like "
            "name, company name, mobile number, email, and address in a structured format.")
    
    files = {'image': ('business_card.jpg', image_bytes, 'image/jpeg')}
    data = {'query': query}
    
    # Setup session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=RETRY_DELAY,
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    start_time = time.perf_counter()
    
    try:
        logger.info(f"Sending OCR request to {OCR_API_URL}")
        
        response = session.post(
            OCR_API_URL,
            files=files,
            data=data,
            timeout=REQUEST_TIMEOUT
        )
        
        processing_time = time.perf_counter() - start_time
        logger.info(f"OCR API response received in {processing_time:.2f} seconds")
        
        # Check response status
        if response.status_code != 200:
            error_msg = f"OCR API returned status {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise OCRServiceError(error_msg)
        
        # Parse response
        try:
            response_text = response.text.strip()
            logger.info(f"OCR API raw response: {repr(response_text[:300])}...")
            
            # Handle multiple JSON objects in response by taking the first one
            if response_text.count('{') > 1:
                logger.warning("Response contains multiple JSON objects, extracting first one")
                brace_count = 0
                json_end = 0
                for i, char in enumerate(response_text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                response_text = response_text[:json_end]
                logger.info(f"Extracted JSON: {repr(response_text)}")
            
            # Clean up the response text
            if response_text.startswith('"') and response_text.endswith('"'):
                response_text = response_text[1:-1]
                logger.info(f"Removed wrapping quotes")
            
            if response_text.endswith('.'):
                response_text = response_text[:-1]
                logger.info(f"Removed trailing period")
            
            # Unescape the JSON
            if '\\' in response_text:
                response_text = response_text.replace('\\"', '"').replace('\\\\', '\\')
                logger.info(f"Unescaped JSON")
            
            # Parse JSON
            try:
                response_data = json.loads(response_text)
                logger.info(f"Successfully parsed JSON response")
            except json.JSONDecodeError as e:
                logger.warning(f"First JSON parse failed: {e}")
                # Try to find just the JSON part
                start_brace = response_text.find('{')
                end_brace = response_text.rfind('}')
                if start_brace != -1 and end_brace != -1:
                    json_part = response_text[start_brace:end_brace + 1]
                    logger.info(f"Trying JSON part: {repr(json_part)}")
                    response_data = json.loads(json_part)
                    logger.info(f"Successfully parsed extracted JSON part")
                else:
                    logger.error(f"Could not find valid JSON braces in: {repr(response_text)}")
                    raise
            
            # Validate response structure
            if not isinstance(response_data, dict):
                logger.warning("OCR API returned non-dict response, attempting to parse")
                if isinstance(response_data, str):
                    response_data = json.loads(response_data.strip())
            
            # Create OCRResult from response
            result = OCRResult.from_api_response(response_data, processing_time)
            
            # Log extracted information
            logger.info(f"OCR extraction completed: name={result.name}, "
                       f"company={result.company}, email={result.email}")
            
            return result
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse OCR API response as JSON: {str(e)}"
            logger.error(error_msg)
            raise OCRServiceError(error_msg)
            
    except requests.exceptions.Timeout:
        error_msg = f"OCR API request timed out after {REQUEST_TIMEOUT} seconds"
        logger.error(error_msg)
        raise OCRServiceError(error_msg)
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Failed to connect to OCR API: {str(e)}"
        logger.error(error_msg)
        raise OCRServiceError(error_msg)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"OCR API request failed: {str(e)}"
        logger.error(error_msg)
        raise OCRServiceError(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error during OCR processing: {str(e)}"
        logger.error(error_msg)
        raise OCRServiceError(error_msg)

# Simple Flask app for Vercel
app = Flask(__name__)
CORS(app)

# Basic HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CardScan Pro</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
        .upload-area:hover { border-color: #007bff; }
        .result { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 4px; }
        .loading { color: #007bff; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🃏 CardScan Pro</h1>
    <p>Professional Business Card Scanner - Upload an image to extract contact information</p>
    
    <form method="POST" enctype="multipart/form-data" action="/process">
        <div class="upload-area">
            <input type="file" name="image" accept="image/*" required>
            <p>Select a business card image</p>
        </div>
        <button type="submit">Process Business Card</button>
    </form>
    
    <div id="result"></div>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'CardScan Pro',
        'version': '2.0.0',
        'timestamp': time.time()
    })

@app.route('/process', methods=['POST'])
def process_image():
    """Process uploaded business card image"""
    try:
        # Check if image was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Process image with PIL (lighter than OpenCV)
        try:
            image = Image.open(file.stream)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (to reduce API payload)
            if image.width > 1200 or image.height > 1200:
                image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            
            # Convert to base64 for API
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            image_bytes = buffer.getvalue()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
        except Exception as e:
            return jsonify({'error': f'Failed to process image: {str(e)}'}), 400
        
        # Call the actual OCR API
        try:
            ocr_result = call_ocr_api(image_bytes)
            
            # Convert OCRResult to dict format
            result = {
                'name': ocr_result.name or 'Not found',
                'designation': ocr_result.designation or 'Not found',
                'company': ocr_result.company or 'Not found',
                'mobile': ocr_result.mobile or 'Not found',
                'email': ocr_result.email or 'Not found',
                'address': ocr_result.address or 'Not found',
                'processing_time': ocr_result.processing_time,
                'confidence': ocr_result.confidence,
                'status': 'success'
            }
        except OCRServiceError as e:
            error_msg = f'OCR processing failed: {str(e)}'
            logger.error(error_msg)
            
            # Return error response
            if request.headers.get('Accept', '').startswith('application/json'):
                return jsonify({'error': error_msg}), 500
            else:
                error_html = f'<div class="error">{error_msg}</div>'
                return render_template_string(HTML_TEMPLATE.replace('<div id="result"></div>', error_html))
        
        # Return JSON for API calls or HTML for form submissions
        if request.headers.get('Accept', '').startswith('application/json'):
            return jsonify(result)
        else:
            # Return HTML response for form submission
            html_result = f"""
            <div class="result">
                <h3>🎉 Processing Complete!</h3>
                <p><strong>Name:</strong> {result['name']}</p>
                <p><strong>Designation:</strong> {result['designation']}</p>
                <p><strong>Company:</strong> {result['company']}</p>
                <p><strong>Mobile:</strong> {result['mobile']}</p>
                <p><strong>Email:</strong> {result['email']}</p>
                <p><strong>Address:</strong> {result['address']}</p>
                <p><strong>Processing Time:</strong> {result['processing_time']:.2f}s</p>
                <p><a href="/">Process Another Card</a></p>
            </div>
            """
            return render_template_string(HTML_TEMPLATE.replace('<div id="result"></div>', html_result))
        
    except Exception as e:
        error_msg = f'Processing failed: {str(e)}'
        if request.headers.get('Accept', '').startswith('application/json'):
            return jsonify({'error': error_msg}), 500
        else:
            error_html = f'<div class="error">{error_msg}</div>'
            return render_template_string(HTML_TEMPLATE.replace('<div id="result"></div>', error_html))

@app.route('/api/process', methods=['POST'])
def api_process():
    """API endpoint for processing images"""
    return process_image()

# Set environment variables for production
if os.environ.get('VERCEL'):
    app.config.update(
        ENV='production',
        DEBUG=False,
        TESTING=False
    )

# Export for Vercel
application = app

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=3000)