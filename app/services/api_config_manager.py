"""
API Configuration Manager
Handles dynamic API endpoint management and configuration
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    """Data class for API endpoint configuration"""
    name: str
    url: str
    timeout: int = 30
    max_retries: int = 3
    description: str = ""
    headers: Dict[str, str] = None
    auth_required: bool = False
    auth_token: str = ""
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

class APIConfigManager:
    """Manager for API endpoint configurations"""
    
    def __init__(self, config_file: str = "api_endpoints.json"):
        self.config_file = config_file
        self.endpoints: Dict[str, APIEndpoint] = {}
        self.active_endpoint: str = "default"
        self.load_config()
    
    def load_config(self):
        """Load API configurations from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                self.active_endpoint = config_data.get('active_endpoint', 'default')
                
                for name, endpoint_data in config_data.get('endpoints', {}).items():
                    self.endpoints[name] = APIEndpoint(**endpoint_data)
                
                logger.info(f"Loaded {len(self.endpoints)} API endpoints from {self.config_file}")
            else:
                # Create default configuration
                self.create_default_config()
                
        except Exception as e:
            logger.error(f"Error loading API config: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """Create default API configuration"""
        from config import config
        
        default_endpoint = APIEndpoint(
            name="default",
            url=config.OCR_API_URL,
            timeout=config.REQUEST_TIMEOUT,
            max_retries=config.MAX_RETRIES,
            description="Default OCR API endpoint"
        )
        
        # Add some example alternative endpoints
        alternative_endpoints = {
            "google_vision": APIEndpoint(
                name="google_vision",
                url="https://vision.googleapis.com/v1/images:annotate",
                timeout=45,
                description="Google Cloud Vision API",
                auth_required=True,
                headers={"Content-Type": "application/json"}
            ),
            "azure_ocr": APIEndpoint(
                name="azure_ocr",
                url="https://westus.api.cognitive.microsoft.com/vision/v3.2/ocr",
                timeout=30,
                description="Microsoft Azure Computer Vision OCR",
                auth_required=True,
                headers={"Content-Type": "application/octet-stream"}
            ),
            "custom_endpoint": APIEndpoint(
                name="custom_endpoint",
                url="http://localhost:8000/api/ocr",
                timeout=30,
                description="Custom local OCR endpoint"
            )
        }
        
        self.endpoints = {"default": default_endpoint, **alternative_endpoints}
        self.active_endpoint = "default"
        self.save_config()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            config_data = {
                "active_endpoint": self.active_endpoint,
                "endpoints": {
                    name: asdict(endpoint) 
                    for name, endpoint in self.endpoints.items()
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            logger.info(f"Saved API configuration to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving API config: {e}")
    
    def get_active_endpoint(self) -> APIEndpoint:
        """Get the currently active API endpoint"""
        return self.endpoints.get(self.active_endpoint, self.endpoints.get("default"))
    
    def set_active_endpoint(self, endpoint_name: str) -> bool:
        """Set the active API endpoint"""
        if endpoint_name in self.endpoints:
            self.active_endpoint = endpoint_name
            self.save_config()
            logger.info(f"Switched to API endpoint: {endpoint_name}")
            return True
        else:
            logger.warning(f"Endpoint '{endpoint_name}' not found")
            return False
    
    def add_endpoint(self, endpoint: APIEndpoint) -> bool:
        """Add a new API endpoint"""
        try:
            self.endpoints[endpoint.name] = endpoint
            self.save_config()
            logger.info(f"Added new API endpoint: {endpoint.name}")
            return True
        except Exception as e:
            logger.error(f"Error adding endpoint: {e}")
            return False
    
    def remove_endpoint(self, endpoint_name: str) -> bool:
        """Remove an API endpoint"""
        if endpoint_name == "default":
            logger.warning("Cannot remove default endpoint")
            return False
        
        if endpoint_name in self.endpoints:
            del self.endpoints[endpoint_name]
            
            # Switch to default if we're removing the active endpoint
            if self.active_endpoint == endpoint_name:
                self.active_endpoint = "default"
            
            self.save_config()
            logger.info(f"Removed API endpoint: {endpoint_name}")
            return True
        else:
            logger.warning(f"Endpoint '{endpoint_name}' not found")
            return False
    
    def update_endpoint(self, endpoint_name: str, **updates) -> bool:
        """Update an existing API endpoint"""
        if endpoint_name in self.endpoints:
            endpoint = self.endpoints[endpoint_name]
            
            for key, value in updates.items():
                if hasattr(endpoint, key):
                    setattr(endpoint, key, value)
            
            self.save_config()
            logger.info(f"Updated API endpoint: {endpoint_name}")
            return True
        else:
            logger.warning(f"Endpoint '{endpoint_name}' not found")
            return False
    
    def list_endpoints(self) -> List[Dict[str, Any]]:
        """List all available endpoints"""
        return [
            {
                "name": name,
                "url": endpoint.url,
                "description": endpoint.description,
                "active": name == self.active_endpoint,
                "timeout": endpoint.timeout,
                "auth_required": endpoint.auth_required
            }
            for name, endpoint in self.endpoints.items()
        ]
    
    def test_endpoint(self, endpoint_name: str = None) -> Dict[str, Any]:
        """Test connectivity to an endpoint"""
        import requests
        
        endpoint = self.endpoints.get(endpoint_name or self.active_endpoint)
        if not endpoint:
            return {"success": False, "error": "Endpoint not found"}
        
        try:
            # Simple connectivity test
            test_url = endpoint.url.rsplit('/', 1)[0] + '/health'
            
            response = requests.get(
                test_url,
                timeout=min(endpoint.timeout, 10),
                headers=endpoint.headers
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
            
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection failed"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global instance
api_config_manager = APIConfigManager()