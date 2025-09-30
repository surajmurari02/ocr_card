# CLAUDE.md - CardScan Pro

## Project Overview
CardScan Pro is an AI-powered business card scanner that extracts text from business card images using OCR technology. It features both a web interface and command-line tool for processing business cards.

## Key Components
- **Flask Web Application** (`run.py`, `app.py`) - Main web interface on port 9999
- **Command Line Tool** (`main.py`) - Batch processing capability
- **OCR Service Integration** - External API at `http://3.108.164.82:1337/upload`
- **Docker Support** - Containerized deployment ready
- **Vercel Deployment** - Cloud deployment configuration

## Development Commands

### Local Development
```bash
# Start web server
python run.py

# Run command line tool
python main.py path/to/card.jpg

# Verify deployment readiness
./verify.sh

# Deploy with script
./deploy.sh local|docker|vercel
```

### Testing & Quality Assurance
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Lint check (if available)
flake8 .
```

### Dependencies
- Flask 2.3.3
- OpenCV (opencv-python-headless)
- Pillow for image processing
- Requests for API calls
- python-dotenv for configuration

## Configuration
Environment variables in `.env`:
- `OCR_API_URL` - External OCR service endpoint
- `MAX_FILE_SIZE` - Upload limit (default 10MB)
- `REQUEST_TIMEOUT` - API timeout (default 30s)
- `FLASK_ENV` - Environment setting
- `SECRET_KEY` - Flask security key

## Architecture Notes
- Modular Flask application structure in `app/` directory
- Services layer for OCR processing
- Input validation and security measures
- Comprehensive error handling and logging
- Docker and Vercel deployment ready

## Common Tasks
- **Add new OCR features**: Modify `app/services/ocr_service.py`
- **Update web interface**: Edit `templates/index.html` and static assets
- **Configuration changes**: Update `config.py` and `.env`
- **API endpoints**: Add routes in `app/routes/`
- **Testing**: Add tests in `tests/` directory

## Deployment Status
The project includes deployment automation for:
- Local development server
- Docker containerization
- Vercel cloud deployment
- NGINX reverse proxy configuration