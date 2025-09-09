import pytest
import json
from app.models.ocr_result import OCRResult

def test_ocr_result_creation():
    """Test OCR result object creation"""
    result = OCRResult(
        name="John Doe",
        company="Tech Corp",
        email="john@techcorp.com",
        processing_time=1.5
    )
    
    assert result.name == "John Doe"
    assert result.company == "Tech Corp"
    assert result.email == "john@techcorp.com"
    assert result.processing_time == 1.5

def test_ocr_result_to_dict():
    """Test converting OCR result to dictionary"""
    result = OCRResult(
        name="Jane Smith",
        designation="Developer",
        company="StartupX",
        mobile="555-1234",
        email="jane@startupx.com"
    )
    
    result_dict = result.to_dict()
    
    assert isinstance(result_dict, dict)
    assert result_dict['name'] == "Jane Smith"
    assert result_dict['designation'] == "Developer"
    assert result_dict['company'] == "StartupX"
    assert result_dict['mobile'] == "555-1234"
    assert result_dict['email'] == "jane@startupx.com"

def test_ocr_result_to_json():
    """Test converting OCR result to JSON"""
    result = OCRResult(name="Test User", company="Test Corp")
    json_str = result.to_json()
    
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed['name'] == "Test User"
    assert parsed['company'] == "Test Corp"

def test_ocr_result_from_api_response():
    """Test creating OCR result from API response"""
    api_response = {
        'name': 'API User',
        'company_name': 'API Corp',  # Different key name
        'phone': '555-9999',  # Different key name
        'email': 'api@corp.com',
        'designation': 'CEO'
    }
    
    result = OCRResult.from_api_response(api_response, processing_time=2.0)
    
    assert result.name == 'API User'
    assert result.company == 'API Corp'  # Mapped from company_name
    assert result.mobile == '555-9999'  # Mapped from phone
    assert result.email == 'api@corp.com'
    assert result.designation == 'CEO'
    assert result.processing_time == 2.0
    assert result.raw_response == api_response

def test_ocr_result_defaults():
    """Test OCR result with default values"""
    result = OCRResult()
    
    assert result.name is None
    assert result.company is None
    assert result.email is None
    assert result.mobile is None
    assert result.designation is None
    assert result.address is None
    assert result.confidence is None
    assert result.processing_time is None
    assert result.raw_response is None