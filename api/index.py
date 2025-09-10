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
        
        # Mock OCR processing (replace with actual OCR service)
        # This is where you'd call your OCR API
        result = {
            'name': 'Sample Name',
            'designation': 'Software Engineer',
            'company': 'Tech Company Ltd.',
            'mobile': '+1-234-567-8900',
            'email': 'sample@techcompany.com',
            'address': '123 Tech Street, Silicon Valley, CA',
            'processing_time': 1.2,
            'confidence': 0.85,
            'status': 'success'
        }
        
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