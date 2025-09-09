import pytest
import os
from config import Config, config

def test_config_defaults():
    """Test that configuration has reasonable defaults"""
    test_config = Config()
    
    assert 'upload' in test_config.OCR_API_URL
    assert test_config.MAX_FILE_SIZE > 0
    assert test_config.REQUEST_TIMEOUT > 0
    assert len(test_config.ALLOWED_EXTENSIONS) > 0
    assert 'jpg' in test_config.ALLOWED_EXTENSIONS

def test_config_from_env(monkeypatch):
    """Test configuration loading from environment variables"""
    monkeypatch.setenv('OCR_API_URL', 'http://test.example.com/upload')
    monkeypatch.setenv('MAX_FILE_SIZE', '5242880')  # 5MB
    monkeypatch.setenv('REQUEST_TIMEOUT', '60')
    
    test_config = Config()
    
    assert test_config.OCR_API_URL == 'http://test.example.com/upload'
    assert test_config.MAX_FILE_SIZE == 5242880
    assert test_config.REQUEST_TIMEOUT == 60

def test_global_config_instance():
    """Test that global config instance is available"""
    assert config is not None
    assert isinstance(config, Config)