from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """Application factory pattern for CardScan Pro"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Import config after loading env vars
    from config import config
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['DEBUG'] = config.DEBUG
    
    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Setup CORS if needed
    if config.CORS_ORIGINS != 'none':
        CORS(app, origins=config.CORS_ORIGINS.split(',') if config.CORS_ORIGINS != '*' else '*')
    
    # Setup enhanced logging
    setup_logging(app, config)
    
    # Add security headers
    if config.SECURITY_HEADERS_ENABLED:
        setup_security_headers(app)
    
    # Add application info endpoint
    @app.route('/api/info')
    def app_info():
        """Application information endpoint"""
        return jsonify({
            'name': config.APP_NAME,
            'version': config.VERSION,
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': config.FLASK_ENV
        })
    
    # Enhanced health check
    @app.route('/api/health')
    def health_check_detailed():
        """Detailed health check endpoint"""
        from app.services.ocr_service import OCRService
        
        try:
            ocr_service = OCRService()
            ocr_healthy = ocr_service.health_check()
            
            return jsonify({
                'status': 'healthy' if ocr_healthy else 'degraded',
                'services': {
                    'ocr_api': 'up' if ocr_healthy else 'down',
                    'web_server': 'up'
                },
                'timestamp': datetime.utcnow().isoformat(),
                'version': config.VERSION
            }), 200 if ocr_healthy else 503
            
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # Register blueprints
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
    
    return app

def setup_logging(app, config):
    """Setup enhanced logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    # Set Flask app logger
    app.logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
    
    # Log application startup
    app.logger.info(f"Starting {config.APP_NAME} v{config.VERSION} in {config.FLASK_ENV} mode")
    app.logger.info(f"OCR API URL: {config.OCR_API_URL}")

def setup_security_headers(app):
    """Setup security headers for production"""
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"
        return response