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

# Professional HTML template matching local UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CardScan Pro - AI Business Card Scanner</title>
    <meta name="description" content="Professional AI-powered business card scanner with instant text extraction and smart data export">
    <meta name="keywords" content="CardScan Pro, business card scanner, AI OCR, contact extraction, digital business cards">
    
    <!-- Favicon -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            100: '#e0f2fe',
                            500: '#0ea5e9',
                            600: '#0284c7',
                            700: '#0369a1',
                            800: '#075985',
                            900: '#0c4a6e'
                        }
                    }
                }
            }
        }
    </script>
    
    <!-- Custom styles -->
    <style>
        .bg-gradient-primary { 
            background: linear-gradient(135deg, #1e40af 0%, #0f766e 100%); 
        }
        .dark .bg-gradient-primary { 
            background: linear-gradient(135deg, #1e3a8a 0%, #134e4a 100%); 
        }
        
        .shadow-elegant { 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .shadow-elegant-lg { 
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        
        .backdrop-blur-glass { 
            backdrop-filter: blur(16px) saturate(180%);
            background: rgba(255,255,255,0.85);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .dark .backdrop-blur-glass { 
            backdrop-filter: blur(16px) saturate(180%);
            background: rgba(17,24,39,0.85);
            border: 1px solid rgba(55,65,81,0.3);
        }
        
        .card-glass {
            backdrop-filter: blur(12px) saturate(150%);
            background: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.3);
        }
        .dark .card-glass {
            backdrop-filter: blur(12px) saturate(150%);
            background: rgba(31,41,55,0.7);
            border: 1px solid rgba(75,85,99,0.4);
        }
        
        .upload-zone {
            background: linear-gradient(135deg, rgba(59,130,246,0.05) 0%, rgba(14,165,233,0.05) 100%);
            border: 2px dashed rgba(59,130,246,0.3);
        }
        .dark .upload-zone {
            background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(14,165,233,0.08) 100%);
            border: 2px dashed rgba(59,130,246,0.4);
        }
        
        .upload-zone:hover {
            background: linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(14,165,233,0.1) 100%);
            border-color: rgba(59,130,246,0.5);
            transform: translateY(-2px);
        }
        
        * {
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .animate-fade-in { animation: fadeIn 0.4s ease-out; }
        .animate-slide-up { animation: slideUp 0.4s ease-out; }
        
        @keyframes fadeIn {
            0% { opacity: 0; }
            100% { opacity: 1; }
        }
        
        @keyframes slideUp {
            0% { opacity: 0; transform: translateY(16px); }
            100% { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50 dark:from-gray-900 dark:via-slate-900 dark:to-gray-800 p-4 lg:p-6">
    <!-- Theme Toggle -->
    <div class="fixed top-4 right-4 z-50">
        <button 
            id="themeToggle"
            class="p-2 card-glass rounded-xl shadow-elegant hover:shadow-elegant-lg transition-all duration-200 group"
            title="Toggle theme"
            onclick="toggleTheme()"
        >
            <svg id="sunIcon" class="w-4 h-4 text-amber-600 dark:hidden transition-transform group-hover:rotate-12" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path>
            </svg>
            <svg id="moonIcon" class="w-4 h-4 text-slate-400 hidden dark:block transition-transform group-hover:rotate-12" fill="currentColor" viewBox="0 0 20 20">
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
            </svg>
        </button>
    </div>

    <!-- Main Container -->
    <div class="max-w-4xl mx-auto backdrop-blur-glass rounded-2xl shadow-elegant-lg overflow-hidden animate-fade-in">
        
        <!-- Header -->
        <header class="bg-gradient-primary text-white py-8 px-6 text-center relative overflow-hidden">
            <div class="relative z-10 max-w-3xl mx-auto">
                <div class="mb-4">
                    <div class="inline-flex items-center justify-center w-12 h-12 bg-white/20 rounded-xl mb-4">
                        <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                        </svg>
                    </div>
                </div>
                
                <h1 class="text-3xl md:text-4xl font-bold mb-4 tracking-tight">
                    CardScan Pro
                </h1>
                
                <p class="text-lg opacity-95 font-light mb-6 leading-relaxed max-w-xl mx-auto">
                    Professional AI-powered business card digitization
                </p>
                
                <div class="flex flex-wrap justify-center gap-2">
                    <span class="px-3 py-1 bg-white/15 backdrop-blur-sm rounded-lg text-xs font-medium border border-white/10">
                        ⚡ Instant Scan
                    </span>
                    <span class="px-3 py-1 bg-white/15 backdrop-blur-sm rounded-lg text-xs font-medium border border-white/10">
                        🎯 99% Accuracy
                    </span>
                    <span class="px-3 py-1 bg-white/15 backdrop-blur-sm rounded-lg text-xs font-medium border border-white/10">
                        🔒 Enterprise Secure
                    </span>
                </div>
            </div>
        </header>
        
        <!-- Main Content -->
        <main class="p-4 lg:p-6 bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm min-h-[50vh]">
            <!-- Upload Section -->
            <div class="max-w-3xl mx-auto space-y-6">
                <section 
                    class="upload-zone rounded-2xl p-6 text-center cursor-pointer group shadow-sm hover:shadow-elegant transition-all duration-300"
                    id="uploadSection"
                >
                    <div class="max-w-xl mx-auto">
                        <!-- Upload Icon -->
                        <div class="mb-6">
                            <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-50 dark:bg-blue-900/30 rounded-2xl mb-4 group-hover:scale-110 transition-transform duration-300">
                                <svg class="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                </svg>
                            </div>
                        </div>
                        
                        <!-- Upload Text -->
                        <h2 class="text-xl lg:text-2xl font-bold text-slate-800 dark:text-slate-200 mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300">
                            Digitize Your Business Card
                        </h2>
                        
                        <p class="text-base text-slate-600 dark:text-slate-400 mb-6 leading-relaxed">
                            Drop your business card image here or click to upload
                        </p>
                        
                        <!-- Upload Form -->
                        <form method="POST" enctype="multipart/form-data" action="/process" id="uploadForm">
                            <input type="file" name="image" accept="image/*" id="imageInput" class="hidden" required onchange="previewImage(this)">
                            <button 
                                type="button"
                                class="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-xl font-semibold shadow-elegant hover:shadow-elegant-lg transition-all duration-200 mb-6 group-hover:scale-105"
                                onclick="document.getElementById('imageInput').click()"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                                </svg>
                                <span>Select File</span>
                            </button>
                        </form>
                        
                        <!-- Format Info -->
                        <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                            <div class="text-xs text-slate-600 dark:text-slate-400">
                                <span class="font-medium">Formats:</span> JPEG, PNG, GIF, BMP, TIFF • <span class="font-medium">Max:</span> 10MB
                            </div>
                        </div>
                    </div>
                </section>
                
                <!-- Preview Section -->
                <div class="hidden animate-slide-up" id="previewSection">
                    <div class="card-glass rounded-xl p-4 shadow-elegant">
                        <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center">
                            <svg class="w-4 h-4 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                            </svg>
                            Preview
                        </h3>
                        
                        <div class="grid md:grid-cols-2 gap-4 items-center mb-4">
                            <div class="relative group">
                                <img 
                                    id="imagePreview" 
                                    class="w-full max-h-48 object-contain rounded-lg shadow-sm" 
                                    alt="Business Card Preview"
                                >
                                <div class="absolute top-2 right-2 bg-green-500 text-white px-2 py-1 rounded text-xs font-medium shadow-sm">
                                    Ready
                                </div>
                            </div>
                            
                            <div class="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg" id="imageInfo">
                                <div class="text-sm text-slate-600 dark:text-slate-400">
                                    Ready to extract contact information with precision AI technology.
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex gap-3">
                            <button 
                                type="button"
                                class="flex-1 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white py-3 rounded-xl font-semibold shadow-elegant hover:shadow-elegant-lg transition-all duration-200"
                                onclick="submitForm()"
                                id="processBtn"
                            >
                                <div class="flex items-center justify-center space-x-2">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                    </svg>
                                    <span>Extract Contact Info</span>
                                </div>
                            </button>
                            
                            <button 
                                type="button"
                                class="px-4 py-3 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-xl font-medium transition-all duration-200"
                                onclick="resetForm()"
                            >
                                New Upload
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
    <!-- Result placeholder -->
    <div id="result"></div>

    <script>
        // Theme management
        function toggleTheme() {
            const html = document.documentElement;
            const isDark = html.classList.contains('dark');
            
            if (isDark) {
                html.classList.remove('dark');
                localStorage.setItem('theme', 'light');
            } else {
                html.classList.add('dark');
                localStorage.setItem('theme', 'dark');
            }
        }
        
        // Initialize theme
        function initTheme() {
            const savedTheme = localStorage.getItem('theme');
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            const currentTheme = savedTheme || systemTheme;
            
            if (currentTheme === 'dark') {
                document.documentElement.classList.add('dark');
            }
        }
        
        // Image preview
        function previewImage(input) {
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('imagePreview').src = e.target.result;
                    document.getElementById('previewSection').classList.remove('hidden');
                };
                reader.readAsDataURL(input.files[0]);
            }
        }
        
        // Form submission
        function submitForm() {
            const btn = document.getElementById('processBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="flex items-center justify-center space-x-2"><div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div><span>Processing...</span></div>';
            
            document.getElementById('uploadForm').submit();
        }
        
        // Reset form
        function resetForm() {
            document.getElementById('previewSection').classList.add('hidden');
            document.getElementById('uploadForm').reset();
            document.getElementById('result').innerHTML = '';
        }
        
        // Drag and drop
        function setupDragDrop() {
            const uploadSection = document.getElementById('uploadSection');
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadSection.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            ['dragenter', 'dragover'].forEach(eventName => {
                uploadSection.addEventListener(eventName, () => {
                    uploadSection.classList.add('border-blue-500', 'bg-blue-50');
                }, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                uploadSection.addEventListener(eventName, () => {
                    uploadSection.classList.remove('border-blue-500', 'bg-blue-50');
                }, false);
            });
            
            uploadSection.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    document.getElementById('imageInput').files = files;
                    previewImage(document.getElementById('imageInput'));
                }
            }, false);
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
            setupDragDrop();
        });
    </script>
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
            # Return HTML response for form submission with professional styling
            html_result = f"""
            <div class="max-w-4xl mx-auto backdrop-blur-glass rounded-2xl shadow-elegant-lg overflow-hidden animate-fade-in mt-6">
                <!-- Result Header -->
                <header class="bg-gradient-to-r from-teal-600 to-teal-700 text-white py-6 px-6 text-center">
                    <div class="flex items-center justify-center mb-4">
                        <div class="inline-flex items-center justify-center w-12 h-12 bg-white/20 rounded-xl">
                            <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                            </svg>
                        </div>
                    </div>
                    <h2 class="text-2xl font-bold mb-2">✨ Contact Extracted Successfully!</h2>
                    <p class="text-teal-100 opacity-90">Processing completed in {result['processing_time']:.2f} seconds</p>
                </header>
                
                <!-- Result Body -->
                <div class="p-6 bg-white/70 dark:bg-gray-900/70 backdrop-blur-sm">
                    <div class="grid md:grid-cols-2 gap-6">
                        <!-- Personal Info -->
                        <div class="card-glass rounded-xl p-4 shadow-elegant">
                            <h3 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4 flex items-center">
                                <svg class="w-5 h-5 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                                </svg>
                                Personal Details
                            </h3>
                            <div class="space-y-3">
                                <div class="flex items-center space-x-3">
                                    <span class="text-sm font-medium text-slate-500 dark:text-slate-400 w-20">Name:</span>
                                    <span class="text-sm text-slate-900 dark:text-slate-100 font-semibold">{result['name']}</span>
                                </div>
                                <div class="flex items-center space-x-3">
                                    <span class="text-sm font-medium text-slate-500 dark:text-slate-400 w-20">Title:</span>
                                    <span class="text-sm text-slate-900 dark:text-slate-100">{result['designation']}</span>
                                </div>
                                <div class="flex items-center space-x-3">
                                    <span class="text-sm font-medium text-slate-500 dark:text-slate-400 w-20">Company:</span>
                                    <span class="text-sm text-slate-900 dark:text-slate-100">{result['company']}</span>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Contact Info -->
                        <div class="card-glass rounded-xl p-4 shadow-elegant">
                            <h3 class="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4 flex items-center">
                                <svg class="w-5 h-5 mr-2 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                                </svg>
                                Contact Details
                            </h3>
                            <div class="space-y-3">
                                <div class="flex items-center space-x-3">
                                    <span class="text-sm font-medium text-slate-500 dark:text-slate-400 w-20">Mobile:</span>
                                    <span class="text-sm text-slate-900 dark:text-slate-100">{result['mobile']}</span>
                                </div>
                                <div class="flex items-center space-x-3">
                                    <span class="text-sm font-medium text-slate-500 dark:text-slate-400 w-20">Email:</span>
                                    <span class="text-sm text-slate-900 dark:text-slate-100">{result['email']}</span>
                                </div>
                                <div class="flex items-start space-x-3">
                                    <span class="text-sm font-medium text-slate-500 dark:text-slate-400 w-20 mt-0.5">Address:</span>
                                    <span class="text-sm text-slate-900 dark:text-slate-100 leading-relaxed">{result['address']}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div class="mt-6 flex gap-3 justify-center">
                        <a href="/" class="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-xl font-semibold shadow-elegant hover:shadow-elegant-lg transition-all duration-200">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                            <span>Process Another Card</span>
                        </a>
                    </div>
                </div>
            </div>
            """
            
            # Create a complete page with the result
            result_page = HTML_TEMPLATE.replace('<div id="result"></div>', html_result)
            return result_page
        
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