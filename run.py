#!/usr/bin/env python3
"""
CardScan Pro - Professional Business Card Scanner
Entry point for the Flask application
"""

import os
import sys
from app import create_app
from config import config

# Create Flask application
app = create_app()

# Vercel compatibility
if os.environ.get('VERCEL'):
    # For Vercel serverless deployment
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False

def main():
    """Main application entry point"""
    try:
        app.logger.info(f"Starting {config.APP_NAME} v{config.VERSION}...")
        app.logger.info(f"Environment: {config.FLASK_ENV}")
        app.logger.info(f"OCR API URL: {config.OCR_API_URL}")
        app.logger.info(f"Server: {config.HOST}:{config.PORT}")
        
        # Run the application
        if config.is_production:
            # Production mode - use gunicorn or similar
            app.logger.info("Running in production mode")
            app.run(
                host=config.HOST,
                port=config.PORT,
                debug=False,
                threaded=True
            )
        else:
            # Development mode
            app.logger.info("Running in development mode")
            app.run(
                host=config.HOST,
                port=config.PORT,
                debug=config.DEBUG,
                threaded=True
            )
            
    except KeyboardInterrupt:
        app.logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

# For WSGI servers (gunicorn, uwsgi, etc.)
# gunicorn run:app
application = app