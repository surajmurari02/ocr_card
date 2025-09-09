# CardScan Pro - Deployment Guide

## 🚀 Quick Deployment Options

CardScan Pro supports multiple deployment methods. Choose the one that best fits your needs:

### 1. Docker Deployment (Recommended)

**Prerequisites:**
- Docker & Docker Compose installed
- 2GB RAM minimum, 4GB recommended

**Quick Start:**
```bash
# Clone and setup
git clone <repository-url>
cd ocr_card

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Deploy
./deploy.sh docker
```

**Access:** http://localhost:8080

### 2. Vercel Deployment (Serverless)

**Prerequisites:**
- Vercel CLI installed: `npm i -g vercel`
- Vercel account

**Quick Start:**
```bash
# Configure environment in Vercel dashboard
vercel env add OCR_API_URL
vercel env add SECRET_KEY

# Deploy
./deploy.sh vercel
```

### 3. Local Development

**Prerequisites:**
- Python 3.11+
- pip

**Quick Start:**
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install and run
./deploy.sh local
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file from `.env.example` and configure:

```env
# OCR API Configuration (REQUIRED)
OCR_API_URL=http://your-ocr-api-endpoint/upload

# Security (REQUIRED for production)
SECRET_KEY=your-super-secret-key-here

# Server Configuration
HOST=0.0.0.0
PORT=8080
FLASK_ENV=production

# Upload limits
MAX_CONTENT_LENGTH=16777216  # 16MB
MAX_FILE_SIZE=10485760       # 10MB

# Timeouts and retries
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=1

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/cardscan-pro.log

# Security Headers
SECURITY_HEADERS_ENABLED=True
CORS_ORIGINS=*

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=100 per hour
```

### OCR API Endpoint

**Current Default:** `http://3.108.164.82:1428/upload`

To change the OCR endpoint:
1. Update `OCR_API_URL` in your `.env` file
2. Restart the application

**API Requirements:**
- Accepts POST requests with `image` file and `query` text
- Returns JSON response with extracted fields
- Should respond within configured timeout

## 🐳 Docker Configuration

### Basic Docker Compose
```yaml
version: '3.8'
services:
  cardscan-pro:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OCR_API_URL=${OCR_API_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./logs:/app/logs
```

### Production with Nginx
```bash
# Enable nginx profile
docker-compose --profile production up -d
```

## ☁️ Cloud Deployment

### Vercel Environment Variables

Set these in your Vercel dashboard:
- `OCR_API_URL`
- `SECRET_KEY`
- `FLASK_ENV=production`

### AWS/GCP/Azure

For cloud deployment:
1. Use the Docker image
2. Configure environment variables
3. Setup load balancer
4. Configure SSL certificates

## 📊 Monitoring & Health Checks

### Health Endpoints

- **Basic:** `/health`
- **Detailed:** `/api/health`
- **App Info:** `/api/info`

### Log Monitoring

Logs are written to:
- Console (stdout)
- File: `logs/cardscan-pro.log`

### Metrics

Monitor these endpoints:
- Response time
- Error rates
- OCR API connectivity
- Upload success rates

## 🔒 Security Considerations

### Production Security

1. **Environment Variables:**
   - Never commit `.env` files
   - Use strong `SECRET_KEY`
   - Restrict `CORS_ORIGINS` in production

2. **Network Security:**
   - Use HTTPS in production
   - Configure firewall rules
   - Limit access to admin endpoints

3. **File Upload Security:**
   - Built-in file type validation
   - File size limits
   - Temporary file cleanup

### SSL/TLS Setup

For production with SSL:
```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Place certificates in ssl/ directory
mkdir ssl
mv cert.pem key.pem ssl/
```

## 🐛 Troubleshooting

### Common Issues

1. **OCR API Connection Failed**
   - Check `OCR_API_URL` is correct
   - Verify network connectivity
   - Check API endpoint is running

2. **File Upload Errors**
   - Check file size limits
   - Verify file format support
   - Check disk space

3. **Docker Issues**
   - Ensure Docker daemon is running
   - Check port 8080 is available
   - Verify environment variables

### Debug Mode

Enable debug mode for development:
```env
FLASK_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG
```

### API Testing

Test OCR API connectivity:
```bash
curl -X POST http://your-ocr-endpoint/upload \
  -F "image=@test-card.jpg" \
  -F "query=Extract business card information"
```

## 📈 Performance Optimization

### Production Settings

1. **Resource Allocation:**
   - 2GB RAM minimum
   - 1 CPU core minimum
   - SSD storage recommended

2. **Caching:**
   - Enable browser caching for static files
   - Consider Redis for session storage

3. **Load Balancing:**
   - Use multiple instances behind load balancer
   - Configure health checks

### Scaling

For high-traffic deployments:
1. Use container orchestration (Kubernetes)
2. Implement horizontal scaling
3. Add caching layer
4. Monitor performance metrics

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup & Recovery

Important files to backup:
- Environment configuration (`.env`)
- Log files (`logs/`)
- SSL certificates (`ssl/`)
- Custom configurations

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs cardscan-pro`
2. Verify health endpoints
3. Review configuration settings
4. Test OCR API connectivity

---

**CardScan Pro v1.0.0** - Professional Business Card Digitization Platform