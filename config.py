import os
import secrets
from dataclasses import dataclass
from typing import Set
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Configuration class for CardScan Pro application"""
    
    # Core Application Settings
    APP_NAME: str = "CardScan Pro"
    VERSION: str = "1.0.0"
    
    # Flask Configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', secrets.token_hex(32))
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'development')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Server Configuration
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '8080'))
    
    # OCR API Configuration
    OCR_API_URL: str = os.getenv('OCR_API_URL', 'http://3.108.164.82:1428/upload')
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY: float = float(os.getenv('RETRY_DELAY', '1.0'))
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    MAX_CONTENT_LENGTH: int = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    ALLOWED_EXTENSIONS: Set[str] = frozenset({'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'})
    UPLOAD_FOLDER: str = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/cardscan-pro.log')
    
    # Security Configuration
    SECURITY_HEADERS_ENABLED: bool = os.getenv('SECURITY_HEADERS_ENABLED', 'True').lower() == 'true'
    CORS_ORIGINS: str = os.getenv('CORS_ORIGINS', '*')
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_DEFAULT: str = os.getenv('RATE_LIMIT_DEFAULT', '100 per hour')
    
    # Analytics (Optional)
    ANALYTICS_ENABLED: bool = os.getenv('ANALYTICS_ENABLED', 'False').lower() == 'true'
    ANALYTICS_TRACKING_ID: str = os.getenv('ANALYTICS_TRACKING_ID', '')
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.FLASK_ENV == 'production'
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.FLASK_ENV == 'development'
    
    def validate(self) -> bool:
        """Validate critical configuration settings"""
        if self.is_production and 'dev-key' in self.SECRET_KEY:
            raise ValueError("Production deployment requires a secure SECRET_KEY")
        
        if not self.OCR_API_URL:
            raise ValueError("OCR_API_URL is required")
            
        return True

# Create global config instance
config = Config()

# Validate configuration on import
if __name__ != '__main__':
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")