# 🎯 CardScan Pro - AI Business Card Scanner

> **Professional AI-powered business card digitization platform with instant text extraction and smart data export**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)]()
[![Vercel](https://img.shields.io/badge/vercel-deployable-black.svg)]()

## 🚀 Features

- **Web Interface**: Easy-to-use upload and scan functionality
- **Command Line Tool**: Batch processing and automation support
- **Advanced OCR**: Powered by external OCR API with preprocessing
- **Security**: Input validation, file size limits, and sanitization
- **Error Handling**: Comprehensive logging and retry mechanisms
- **Configuration**: Environment-based configuration management
- **Modular Architecture**: Clean, maintainable code structure

## 📁 Project Structure

```
ocr_card/
├── app/                    # Flask application package
│   ├── __init__.py        # App factory
│   ├── models/            # Data models
│   │   └── ocr_result.py  # OCR result structure
│   ├── services/          # Business logic
│   │   ├── ocr_service.py # OCR API integration
│   │   └── image_processor.py # Image processing
│   ├── routes/            # API endpoints
│   │   └── main.py        # Main routes
│   └── utils/             # Utilities
│       └── validators.py  # Input validation
├── static/                # Static web assets
│   ├── css/
│   ├── js/
│   └── images/
├── templates/             # HTML templates
│   └── index.html        # Main interface
├── tests/                # Test files
├── assets/               # Sample images
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── run.py               # Web application entry point
└── main.py              # Command line tool
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ocr_card
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env .env.local
   # Edit .env.local with your settings
   ```

## 🖥️ Usage

### Web Application

Start the Flask web server:
```bash
python run.py
```

Visit `http://localhost:9999` in your browser to access the web interface.

### Command Line Tool

Process a single image:
```bash
python main.py path/to/business_card.jpg
```

With options:
```bash
python main.py path/to/card.jpg --format json --verbose
```

## ⚙️ Configuration

Environment variables (set in `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OCR_API_URL` | `http://3.108.164.82:1337/upload` | OCR service endpoint |
| `MAX_FILE_SIZE` | `10485760` | Maximum upload size (10MB) |
| `REQUEST_TIMEOUT` | `30` | API request timeout (seconds) |
| `MAX_RETRIES` | `3` | Number of retry attempts |
| `FLASK_ENV` | `development` | Flask environment |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SECRET_KEY` | `dev-key-change-in-production` | Flask secret key |

## 🔒 Security Features

- **File Validation**: Type and size checking
- **Input Sanitization**: Filename sanitization and validation
- **Error Handling**: Secure error messages without sensitive data exposure
- **Request Limits**: File size and timeout limits
- **Path Safety**: Protection against path traversal attacks

## 📊 API Endpoints

### `GET /`
Main web interface

### `POST /process_image`
Process uploaded business card image

**Request**: `multipart/form-data` with `image` field  
**Response**: JSON with extracted information

```json
{
  "name": "John Smith",
  "designation": "Senior Developer",
  "company": "Tech Corp",
  "mobile": "+1-555-123-4567",
  "email": "john@techcorp.com",
  "address": "123 Tech Street, City, State",
  "processing_time": 2.34,
  "status": "success"
}
```

### `GET /health`
Health check endpoint

**Response**: Service status and connectivity information

## 🧪 Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## 📝 Logging

Logs are written to:
- Console (stdout)
- File: `ocr_card.log`

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🔄 Development

### Adding New Features

1. **Models**: Add data structures in `app/models/`
2. **Services**: Add business logic in `app/services/`
3. **Routes**: Add API endpoints in `app/routes/`
4. **Tests**: Add tests in `tests/`

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add comprehensive docstrings
- Include error handling and logging

## 🚨 Troubleshooting

### Common Issues

1. **OCR API Connection Failed**
   - Check `OCR_API_URL` in `.env`
   - Verify network connectivity
   - Check API service status

2. **File Upload Fails**
   - Verify file size < 10MB
   - Check file format (jpg, png, gif, bmp, tiff)
   - Ensure sufficient disk space

3. **Import Errors**
   - Verify virtual environment is activated
   - Install missing dependencies: `pip install -r requirements.txt`

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python run.py
```

## 📈 Performance

- **Image Processing**: Optimized with OpenCV
- **API Calls**: Connection pooling and retry logic
- **Memory Usage**: Streaming file processing
- **Response Times**: < 3 seconds for standard business cards

## 🔮 Future Enhancements

- [ ] Batch processing support
- [ ] Result export (CSV, vCard, Excel)
- [ ] OCR confidence scoring
- [ ] Image preprocessing options
- [ ] Database storage for results
- [ ] User authentication
- [ ] API rate limiting
- [ ] Docker containerization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Create an issue on GitHub