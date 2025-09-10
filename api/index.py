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
                        
                        <!-- Upload Button -->
                        <button 
                            class="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-xl font-semibold shadow-elegant hover:shadow-elegant-lg transition-all duration-200 mb-6 group-hover:scale-105"
                            id="uploadBtn"
                        >
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                            </svg>
                            <span>Select File</span>
                        </button>
                        
                        <input type="file" id="imageInput" accept="image/*" class="hidden">
                        
                        <!-- Format Info -->
                        <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                            <div class="text-xs text-slate-600 dark:text-slate-400">
                                <span class="font-medium">Formats:</span> JPEG, PNG, GIF, BMP, TIFF • <span class="font-medium">Max:</span> 10MB
                            </div>
                        </div>
                    </div>
                </section>
                
                <!-- Processing Section (shows after upload) -->
                <div class="hidden animate-slide-up" id="processingSection">
                    <div class="space-y-6">
                        <!-- Image Preview -->
                        <div id="imagePreviewContainer">
                            <div class="card-glass rounded-xl p-4 shadow-elegant">
                                <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3 flex items-center">
                                    <svg class="w-4 h-4 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                                    </svg>
                                    Preview
                                </h3>
                                
                                <div class="grid md:grid-cols-2 gap-4 items-center">
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
                                    
                                    <div class="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg" id="imageInfo"></div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Quick Instructions -->
                        <div class="card-glass rounded-xl p-4 shadow-elegant">
                            <div class="flex items-center justify-between mb-3">
                                <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 flex items-center">
                                    <svg class="w-4 h-4 mr-2 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                    </svg>
                                    Ready to Process
                                </h3>
                                <div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-lg">
                                    💡 Tip: Ensure clear, well-lit image
                                </div>
                            </div>
                            
                            <div class="text-sm text-slate-600 dark:text-slate-400 mb-4">
                                Ready to extract contact information with precision AI technology.
                            </div>
                        </div>
                        
                        <!-- Action Buttons -->
                        <div class="flex gap-3">
                            <button 
                                class="flex-1 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white py-3 rounded-xl font-semibold shadow-elegant hover:shadow-elegant-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                                id="scanBtn"
                            >
                                <div class="flex items-center justify-center space-x-2">
                                    <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent hidden" id="loadingSpinner"></div>
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" id="scanIcon">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                    </svg>
                                    <span id="scanBtnText">Extract Contact Info</span>
                                </div>
                            </button>
                            
                            <button 
                                class="px-4 py-3 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-xl font-medium transition-all duration-200"
                                onclick="document.getElementById('processingSection').classList.add('hidden'); document.getElementById('uploadSection').style.display = 'block';"
                            >
                                New Upload
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    
    <!-- Result Modal -->
    <div id="resultModal" class="fixed inset-0 z-50 hidden bg-black/50 backdrop-blur-sm animate-fade-in">
        <div class="flex items-center justify-center min-h-screen p-4">
            <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden animate-slide-up border dark:border-gray-700">
                
                <!-- Modal Header -->
                <div class="bg-gradient-primary text-white p-6 relative overflow-hidden">
                    <div class="relative z-10 flex items-center justify-between">
                        <h2 class="text-2xl font-bold flex items-center">
                            <span class="text-2xl mr-2">✨</span>
                            Contact Extracted
                        </h2>
                        <button 
                            class="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:rotate-90 flex items-center justify-center text-xl font-bold"
                            id="modalClose"
                        >
                            &times;
                        </button>
                    </div>
                </div>
                
                <!-- Modal Body -->
                <div class="p-6 overflow-y-auto max-h-[70vh] bg-white dark:bg-gray-800" id="resultContent">
                    <!-- Results will be populated here -->
                </div>
            </div>
        </div>
    </div>

    <script>
        class OCRCardApp {
            constructor() {
                this.currentFile = null;
                this.apiEndpoint = '/process_image';
                this.isProcessing = false;
                this.lastResult = null;
                
                this.init();
            }
            
            init() {
                this.initTheme();
                this.bindEvents();
                this.setupDragAndDrop();
            }
            
            initTheme() {
                const savedTheme = localStorage.getItem('theme');
                const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                const currentTheme = savedTheme || systemTheme;
                
                this.setTheme(currentTheme);
                
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                    if (!localStorage.getItem('theme')) {
                        this.setTheme(e.matches ? 'dark' : 'light');
                    }
                });
            }
            
            setTheme(theme) {
                const html = document.documentElement;
                if (theme === 'dark') {
                    html.classList.add('dark');
                } else {
                    html.classList.remove('dark');
                }
                localStorage.setItem('theme', theme);
            }
            
            toggleTheme() {
                const html = document.documentElement;
                const currentTheme = html.classList.contains('dark') ? 'dark' : 'light';
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                this.setTheme(newTheme);
                this.showNotification(`Switched to ${newTheme} theme`, 'success');
            }
            
            bindEvents() {
                const imageInput = document.getElementById('imageInput');
                const uploadBtn = document.getElementById('uploadBtn');
                const scanBtn = document.getElementById('scanBtn');
                const modal = document.getElementById('resultModal');
                const modalClose = document.getElementById('modalClose');
                const themeToggle = document.getElementById('themeToggle');
                
                if (imageInput) {
                    imageInput.addEventListener('change', (e) => this.handleFileSelect(e));
                }
                
                if (uploadBtn) {
                    uploadBtn.addEventListener('click', () => imageInput?.click());
                }
                
                if (scanBtn) {
                    scanBtn.addEventListener('click', () => this.scanBusinessCard());
                }
                
                if (modalClose) {
                    modalClose.addEventListener('click', () => this.closeModal());
                }
                
                if (themeToggle) {
                    themeToggle.addEventListener('click', () => this.toggleTheme());
                }
                
                if (modal) {
                    modal.addEventListener('click', (e) => {
                        if (e.target === modal) {
                            this.closeModal();
                        }
                    });
                }
                
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        this.closeModal();
                    }
                });
            }
            
            setupDragAndDrop() {
                const uploadSection = document.getElementById('uploadSection');
                
                if (!uploadSection) return;
                
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                    uploadSection.addEventListener(eventName, this.preventDefaults, false);
                });
                
                ['dragenter', 'dragover'].forEach(eventName => {
                    uploadSection.addEventListener(eventName, () => {
                        uploadSection.classList.add('border-green-500', 'bg-green-50', 'scale-105');
                        uploadSection.classList.remove('border-gray-300');
                    }, false);
                });
                
                ['dragleave', 'drop'].forEach(eventName => {
                    uploadSection.addEventListener(eventName, () => {
                        uploadSection.classList.remove('border-green-500', 'bg-green-50', 'scale-105');
                        uploadSection.classList.add('border-gray-300');
                    }, false);
                });
                
                uploadSection.addEventListener('drop', (e) => {
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        this.handleFile(files[0]);
                    }
                }, false);
            }
            
            preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            handleFileSelect(e) {
                const file = e.target.files[0];
                if (file) {
                    this.handleFile(file);
                }
            }
            
            handleFile(file) {
                const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'];
                
                if (!allowedTypes.includes(file.type)) {
                    this.showNotification('Please select a valid image file (JPEG, PNG, GIF, BMP, TIFF)', 'error');
                    return;
                }
                
                const maxSize = 10 * 1024 * 1024;
                if (file.size > maxSize) {
                    this.showNotification('File size must be less than 10MB', 'error');
                    return;
                }
                
                this.currentFile = file;
                this.displayImagePreview(file);
                this.showScanButton();
            }
            
            displayImagePreview(file) {
                const reader = new FileReader();
                const uploadSection = document.getElementById('uploadSection');
                const processingSection = document.getElementById('processingSection');
                const previewImg = document.getElementById('imagePreview');
                const imageInfo = document.getElementById('imageInfo');
                
                reader.onload = (e) => {
                    if (previewImg) {
                        previewImg.src = e.target.result;
                        
                        uploadSection.style.display = 'none';
                        processingSection.classList.remove('hidden');
                        processingSection.classList.add('animate-slide-up');
                        
                        if (imageInfo) {
                            const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
                            const fileType = file.type.split('/')[1].toUpperCase();
                            
                            imageInfo.innerHTML = `
                                <div class="space-y-2">
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm font-medium text-slate-700 dark:text-slate-300">File Name</span>
                                        <span class="text-sm text-slate-600 dark:text-slate-400 font-mono">${file.name}</span>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Size</span>
                                        <span class="text-sm text-slate-600 dark:text-slate-400">${sizeInMB} MB</span>
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Format</span>
                                        <span class="inline-flex items-center px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs font-medium rounded-lg">${fileType}</span>
                                    </div>
                                </div>
                            `;
                        }
                    }
                };
                
                reader.readAsDataURL(file);
            }
            
            showScanButton() {
                const scanBtn = document.getElementById('scanBtn');
                if (scanBtn) {
                    scanBtn.disabled = false;
                    scanBtn.classList.add('animate-scale-in');
                }
            }
            
            async scanBusinessCard() {
                if (!this.currentFile || this.isProcessing) {
                    return;
                }
                
                this.setLoading(true);
                
                try {
                    const formData = new FormData();
                    formData.append('image', this.currentFile);
                    
                    const response = await fetch(this.apiEndpoint, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (!response.ok) {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    }
                    
                    this.displayResults(data);
                    this.showNotification('Contact information extracted successfully!', 'success');
                    
                } catch (error) {
                    console.error('Error processing image:', error);
                    this.showError('Failed to process image: ' + error.message);
                } finally {
                    this.setLoading(false);
                }
            }
            
            setLoading(loading) {
                this.isProcessing = loading;
                const scanBtn = document.getElementById('scanBtn');
                const spinner = document.getElementById('loadingSpinner');
                const btnText = document.getElementById('scanBtnText');
                const scanIcon = document.getElementById('scanIcon');
                
                if (scanBtn && spinner && btnText) {
                    scanBtn.disabled = loading;
                    
                    if (loading) {
                        spinner.classList.remove('hidden');
                        scanIcon.classList.add('hidden');
                        btnText.textContent = 'Analyzing...';
                        scanBtn.classList.add('opacity-75');
                    } else {
                        spinner.classList.add('hidden');
                        scanIcon.classList.remove('hidden');
                        btnText.textContent = 'Extract Contact Info';
                        scanBtn.classList.remove('opacity-75');
                    }
                }
            }
            
            displayResults(data) {
                const modal = document.getElementById('resultModal');
                const resultContent = document.getElementById('resultContent');
                
                if (!modal || !resultContent) return;
                
                this.lastResult = data;
                
                const resultHTML = this.createResultHTML(data);
                resultContent.innerHTML = resultHTML;
                
                modal.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            }
            
            createResultHTML(data) {
                const fields = [
                    { key: 'name', label: 'Name', icon: '👤', color: 'blue' },
                    { key: 'designation', label: 'Designation', icon: '💼', color: 'teal' },
                    { key: 'company', label: 'Company', icon: '🏢', color: 'cyan' },
                    { key: 'mobile', label: 'Mobile', icon: '📱', color: 'emerald' },
                    { key: 'email', label: 'Email', icon: '📧', color: 'rose' },
                    { key: 'address', label: 'Address', icon: '📍', color: 'amber' }
                ];
                
                let resultCards = fields.map((field, index) => {
                    const value = data[field.key];
                    const displayValue = value && value !== 'null' ? value : 'Not available';
                    const isEmpty = !value || value === 'null';
                    
                    return `
                        <div class="card-glass rounded-xl p-4 border border-slate-200 dark:border-slate-600 transition-all duration-200 hover:shadow-elegant group animate-scale-in" style="animation-delay: ${index * 50}ms">
                            <div class="flex items-start space-x-3">
                                <div class="flex-shrink-0">
                                    <div class="w-8 h-8 bg-gradient-to-br from-${field.color}-100 to-${field.color}-200 dark:from-${field.color}-900/30 dark:to-${field.color}-800/30 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
                                        <span class="text-sm">${field.icon}</span>
                                    </div>
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide mb-1">
                                        ${field.label}
                                    </div>
                                    <div class="text-sm font-medium ${isEmpty ? 'text-slate-400 dark:text-slate-500 italic' : 'text-slate-800 dark:text-slate-200'} break-words leading-relaxed">
                                        ${displayValue}
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
                
                const processingTime = data.processing_time ? `${data.processing_time.toFixed(2)}s` : 'N/A';
                
                return `
                    <div class="space-y-5">
                        <!-- Processing Summary -->
                        <div class="card-glass rounded-xl p-4 border border-slate-200 dark:border-slate-600 mb-6">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center space-x-3">
                                    <div class="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                                        <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                                        </svg>
                                    </div>
                                    <div>
                                        <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200">Extraction Complete</h3>
                                        <p class="text-xs text-slate-600 dark:text-slate-400">Extracted in ${processingTime}</p>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <div class="text-lg font-bold text-green-600 dark:text-green-400">${processingTime}</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Extracted Information -->
                        <div class="space-y-3">
                            <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3">Contact Information</h3>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                ${resultCards}
                            </div>
                        </div>
                        
                        <!-- Export Options -->
                        <div class="border-t border-slate-200 dark:border-slate-600 pt-5">
                            <h3 class="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3">Export Options</h3>
                            <div class="grid grid-cols-3 gap-3">
                                <button 
                                    class="flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-xl font-medium transition-all duration-200 shadow-sm hover:shadow-md group text-sm"
                                    onclick="app.exportResults('json')"
                                >
                                    <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                                    </svg>
                                    <span>JSON</span>
                                </button>
                                <button 
                                    class="flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white p-3 rounded-xl font-medium transition-all duration-200 shadow-sm hover:shadow-md group text-sm"
                                    onclick="app.exportResults('csv')"
                                >
                                    <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                    </svg>
                                    <span>CSV</span>
                                </button>
                                <button 
                                    class="flex items-center justify-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white p-3 rounded-xl font-medium transition-all duration-200 shadow-sm hover:shadow-md group text-sm"
                                    onclick="app.exportResults('vcard')"
                                >
                                    <svg class="w-4 h-4 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                                    </svg>
                                    <span>vCard</span>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            showError(message) {
                const modal = document.getElementById('resultModal');
                const resultContent = document.getElementById('resultContent');
                
                if (!modal || !resultContent) return;
                
                resultContent.innerHTML = `
                    <div class="text-center py-8">
                        <div class="text-6xl mb-4 animate-bounce">⚠️</div>
                        <h3 class="text-2xl font-bold text-red-600 mb-3">Extraction Failed</h3>
                        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 max-w-md mx-auto">
                            <p class="text-red-700 dark:text-red-300">${message}</p>
                        </div>
                        <button 
                            class="mt-6 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-6 py-2 rounded-lg font-semibold transition-all duration-200 shadow-sm hover:shadow-md"
                            onclick="app.closeModal()"
                        >
                            Try Again
                        </button>
                    </div>
                `;
                
                modal.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            }
            
            closeModal() {
                const modal = document.getElementById('resultModal');
                if (modal) {
                    modal.classList.add('hidden');
                    document.body.style.overflow = 'auto';
                }
            }
            
            exportResults(format) {
                if (!this.lastResult) {
                    this.showNotification('No data to export', 'error');
                    return;
                }
                
                let content, filename, mimeType;
                
                switch (format) {
                    case 'json':
                        content = JSON.stringify(this.lastResult, null, 2);
                        filename = 'business_card_data.json';
                        mimeType = 'application/json';
                        break;
                        
                    case 'csv':
                        content = this.convertToCSV(this.lastResult);
                        filename = 'business_card_data.csv';
                        mimeType = 'text/csv';
                        break;
                        
                    case 'vcard':
                        content = this.convertToVCard(this.lastResult);
                        filename = 'business_card.vcf';
                        mimeType = 'text/vcard';
                        break;
                        
                    default:
                        return;
                }
                
                this.downloadFile(content, filename, mimeType);
                this.showNotification(`Contact data exported as ${format.toUpperCase()}!`, 'success');
            }
            
            convertToCSV(data) {
                const headers = ['Field', 'Value'];
                const rows = Object.entries(data)
                    .filter(([key, value]) => !['status', 'filename', 'processing_time'].includes(key))
                    .map(([key, value]) => [key, value || '']);
                
                const csvContent = [headers, ...rows]
                    .map(row => row.map(field => `"${field}"`).join(','))
                    .join('\\n');
                    
                return csvContent;
            }
            
            convertToVCard(data) {
                return `BEGIN:VCARD
VERSION:3.0
FN:${data.name || ''}
TITLE:${data.designation || ''}
ORG:${data.company || ''}
TEL:${data.mobile || ''}
EMAIL:${data.email || ''}
ADR:;;${data.address || ''};;;;
END:VCARD`;
            }
            
            downloadFile(content, filename, mimeType) {
                const blob = new Blob([content], { type: mimeType });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }
            
            showNotification(message, type = 'success') {
                const existing = document.querySelectorAll('.notification');
                existing.forEach(n => n.remove());
                
                const notification = document.createElement('div');
                notification.className = `notification fixed top-4 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-lg shadow-lg z-50 ${type === 'error' ? 'bg-red-500 text-white' : 'bg-green-500 text-white'}`;
                notification.textContent = message;
                
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.remove();
                }, 5000);
            }
        }

        // Initialize app when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            window.app = new OCRCardApp();
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

@app.route('/process_image', methods=['POST'])
def process_image():
    """Process uploaded business card image - matches local app exactly"""
    try:
        # Validate request (matching local app validation)
        if 'image' not in request.files:
            logger.warning("No image file in request")
            return jsonify({'error': 'No image file uploaded'}), 400

        file = request.files['image']
        
        if file.filename == '':
            logger.warning("Empty filename in request")
            return jsonify({'error': 'No file selected'}), 400

        # Sanitize filename (simplified version)
        filename = file.filename
        logger.info(f"Processing upload: {filename}")

        # Validate file type and size (matching local validation)
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff']
        
        if file.content_type not in allowed_types:
            logger.warning(f"Invalid file type: {file.content_type}")
            return jsonify({'error': 'Please select a valid image file (JPEG, PNG, GIF, BMP, TIFF)'}), 400

        # Check file size (10MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Reset to beginning
        
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            logger.warning(f"File too large: {file_size} bytes")
            return jsonify({'error': 'File size must be less than 10MB'}), 400

        # Process image with PIL (matching local preprocessing)
        try:
            image = Image.open(file.stream)
            
            if image is None:
                logger.error("Failed to read uploaded image")
                return jsonify({'error': 'Failed to process uploaded image'}), 400
            
            # Convert to RGB if necessary (preprocessing)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (preprocessing)
            if image.width > 1200 or image.height > 1200:
                image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                logger.info("Applied brightness enhancement")
            
            # Convert to bytes for API
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            image_bytes = buffer.getvalue()
            
            if image_bytes is None:
                logger.error("Failed to encode image")
                return jsonify({'error': 'Failed to process image'}), 500
            
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            return jsonify({'error': 'Failed to process uploaded image'}), 400

        # Process through OCR service (matching local flow)
        try:
            result = call_ocr_api(image_bytes)
            
            logger.info(f"OCR processing completed successfully in {result.processing_time:.2f}s")
            
            # Return structured response (matching local format)
            response_data = {
                'name': result.name,
                'designation': result.designation,
                'company': result.company,
                'mobile': result.mobile,
                'email': result.email,
                'address': result.address,
                'processing_time': result.processing_time,
                'confidence': result.confidence,
                'status': 'success',
                'filename': filename
            }
            
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
            'details': str(e)
        }), 500

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