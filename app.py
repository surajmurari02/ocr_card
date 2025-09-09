#!/usr/bin/env python3
"""
LEGACY FILE - DEPRECATED

This file has been replaced by the new modular architecture.
Please use 'run.py' to start the application.

The new architecture provides:
- Better error handling and logging
- Configuration management
- Input validation and security
- Modular service layer
- Comprehensive testing support
"""

from app import create_app
import warnings

warnings.warn(
    "app.py is deprecated. Please use 'python run.py' to start the application.",
    DeprecationWarning,
    stacklevel=2
)

# For backward compatibility
app = create_app()

if __name__ == '__main__':
    print("⚠️  DEPRECATION WARNING: app.py is deprecated.")
    print("📘 Please use 'python run.py' to start the new improved application.")
    print("🚀 Starting application with legacy compatibility...\n")
    
    app.run(debug=True, port=9999)
