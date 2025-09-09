from dataclasses import dataclass
from typing import Optional, Dict, Any
import json

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'designation': self.designation,
            'company': self.company,
            'mobile': self.mobile,
            'email': self.email,
            'address': self.address,
            'confidence': self.confidence,
            'processing_time': self.processing_time
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
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