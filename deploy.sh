#!/bin/bash
# CardScan Pro - Deployment Script

set -e

echo "🚀 CardScan Pro Deployment Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from example..."
    cp .env.example .env
    print_warning "Please edit .env file with your configuration before deployment!"
    exit 1
fi

# Load environment variables
source .env

print_status "Starting CardScan Pro deployment..."

# Check deployment type
DEPLOYMENT_TYPE=${1:-"docker"}

case $DEPLOYMENT_TYPE in
    "docker")
        print_status "Deploying with Docker..."
        
        # Build and run with Docker Compose
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        
        print_status "Waiting for application to start..."
        sleep 10
        
        # Health check
        if curl -f http://localhost:8080/api/health > /dev/null 2>&1; then
            print_status "✅ Application is healthy!"
            print_status "🌐 Access CardScan Pro at: http://localhost:8080"
        else
            print_error "❌ Application health check failed!"
            exit 1
        fi
        ;;
        
    "vercel")
        print_status "Deploying to Vercel..."
        
        # Check if Vercel CLI is installed
        if ! command -v vercel &> /dev/null; then
            print_error "Vercel CLI not found. Install with: npm i -g vercel"
            exit 1
        fi
        
        # Deploy to Vercel
        vercel --prod
        ;;
        
    "local")
        print_status "Starting local development server..."
        
        # Install dependencies
        pip install -r requirements.txt
        
        # Start Flask app
        python run.py
        ;;
        
    *)
        print_error "Unknown deployment type: $DEPLOYMENT_TYPE"
        echo "Usage: $0 [docker|vercel|local]"
        exit 1
        ;;
esac

print_status "Deployment completed! 🎉"