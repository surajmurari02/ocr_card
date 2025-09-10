#!/usr/bin/env python3
"""
Vercel Serverless Function for CardScan Pro
Entry point for Vercel deployment
"""

import os
import sys
from pathlib import Path

# Add the parent directory to Python path to import our app
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import the Flask app
from run import app

# Vercel expects the app to be named 'app' or expose a handler function
# For Flask apps, we can use the app directly
def handler(request):
    """
    Vercel serverless function handler
    """
    return app(request.environ, request.start_response)

# Export the Flask app for Vercel
# Vercel will look for 'app' or a function that handles requests
application = app

# Set environment variables for production
if os.environ.get('VERCEL'):
    app.config.update(
        ENV='production',
        DEBUG=False,
        TESTING=False
    )

# For Vercel deployment, the app instance is what gets called
if __name__ == '__main__':
    # This won't run on Vercel, but useful for local testing
    app.run(debug=False, host='0.0.0.0', port=3000)