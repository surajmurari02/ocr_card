import pytest
import io
from unittest.mock import Mock
from app.utils.validators import (
    allowed_file, 
    validate_file_size, 
    validate_image_file, 
    sanitize_filename,
    ValidationError
)

def test_allowed_file():
    """Test file extension validation"""
    assert allowed_file('test.jpg') == True
    assert allowed_file('test.jpeg') == True
    assert allowed_file('test.png') == True
    assert allowed_file('test.gif') == True
    assert allowed_file('test.JPG') == True  # Case insensitive
    
    assert allowed_file('test.exe') == False
    assert allowed_file('test.txt') == False
    assert allowed_file('test') == False
    assert allowed_file('') == False

def test_validate_file_size():
    """Test file size validation"""
    # Mock file with size under limit
    small_file = io.BytesIO(b'small content')
    assert validate_file_size(small_file) == True
    
    # Mock file with size over limit (mock large file)
    large_content = b'x' * (11 * 1024 * 1024)  # 11MB
    large_file = io.BytesIO(large_content)
    assert validate_file_size(large_file) == False

def test_sanitize_filename():
    """Test filename sanitization"""
    assert sanitize_filename('normal.jpg') == 'normal.jpg'
    assert sanitize_filename('file with spaces.png') == 'file with spaces.png'
    
    # Test dangerous characters
    assert '../../../etc/passwd' not in sanitize_filename('../../../etc/passwd.jpg')
    assert sanitize_filename('file<>*.jpg') == 'file___.jpg'
    assert sanitize_filename('file:with|chars.png') == 'file_with_chars.png'
    
    # Test empty filename
    result = sanitize_filename('')
    assert result.startswith('upload')
    
    # Test hidden files
    result = sanitize_filename('.hidden')
    assert result.startswith('upload_')

def test_validate_image_file_invalid_extension():
    """Test image validation with invalid file extension"""
    file_mock = Mock()
    file_mock.filename = 'test.txt'
    
    is_valid, error = validate_image_file(file_mock, 'test.txt')
    assert not is_valid
    assert 'not allowed' in error.lower()

def test_validate_image_file_too_large():
    """Test image validation with file too large"""
    # Create a large file mock
    large_content = b'x' * (11 * 1024 * 1024)  # 11MB
    file_mock = io.BytesIO(large_content)
    
    is_valid, error = validate_image_file(file_mock, 'test.jpg')
    assert not is_valid
    assert 'size exceeds' in error.lower()