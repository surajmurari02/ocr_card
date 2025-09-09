import requests
import time
import logging
from typing import Optional, Dict, Any
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import config
from app.models.ocr_result import OCRResult

logger = logging.getLogger(__name__)

class OCRServiceError(Exception):
    """Custom exception for OCR service errors"""
    pass

class OCRService:
    """Service for handling OCR API interactions"""
    
    def __init__(self, api_url: str = None, timeout: int = None):
        self.api_url = api_url or config.OCR_API_URL
        self.timeout = timeout or config.REQUEST_TIMEOUT
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=self.retry_delay,
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def process_image(self, image_bytes: bytes, query: str = None) -> OCRResult:
        """
        Process image through OCR API with comprehensive error handling
        
        Args:
            image_bytes: Image data as bytes
            query: Custom query for the OCR API
            
        Returns:
            OCRResult object with extracted information
            
        Raises:
            OCRServiceError: If processing fails after retries
        """
        if query is None:
            query = ("I am providing business cards. I want JSON output with keys like "
                    "name, company name, mobile number, email, and address in a structured format.")
        
        files = {'image': ('business_card.jpg', image_bytes, 'image/jpeg')}
        data = {'query': query}
        
        start_time = time.perf_counter()
        
        try:
            logger.info(f"Sending OCR request to {self.api_url}")
            
            response = self.session.post(
                self.api_url,
                files=files,
                data=data,
                timeout=self.timeout
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
                    # Find the first complete JSON object
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
                
                # Clean up the response text - remove wrapping quotes and trailing periods
                if response_text.startswith('"') and response_text.endswith('"'):
                    response_text = response_text[1:-1]
                    logger.info(f"Removed wrapping quotes: {repr(response_text[:100])}...")
                
                if response_text.endswith('.'):
                    response_text = response_text[:-1]
                    logger.info(f"Removed trailing period: {repr(response_text[-50:])}")
                
                # Unescape the JSON - the API returns escaped JSON inside quotes
                if '\\' in response_text:
                    response_text = response_text.replace('\\"', '"').replace('\\\\', '\\')
                    logger.info(f"Unescaped JSON: {repr(response_text[:100])}...")
                
                # Try different parsing approaches
                try:
                    response_data = json.loads(response_text)
                    logger.info(f"Successfully parsed JSON response")
                except json.JSONDecodeError as e:
                    logger.warning(f"First JSON parse failed: {e}")
                    logger.error(f"Full response text causing error: {repr(response_text)}")
                    # Try to find just the JSON part between first { and last }
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
                    # Sometimes the API returns a string that needs to be parsed
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
            error_msg = f"OCR API request timed out after {self.timeout} seconds"
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
    
    def health_check(self) -> bool:
        """Check if OCR API is accessible"""
        try:
            # Use a simple HEAD request to the upload endpoint to check connectivity
            response = requests.head(self.api_url, timeout=5)
            # The API returns 405 for HEAD on /upload, which means it's alive
            return response.status_code in [405, 200]
        except:
            logger.warning("OCR API health check failed")
            return False