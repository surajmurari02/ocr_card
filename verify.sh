#!/bin/bash
# CardScan Pro - Deployment Verification Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

echo "🎯 CardScan Pro - Deployment Verification"
echo "========================================"
echo

# Check Python version
print_info "Checking Python version..."
python_version=$(python --version 2>&1 | cut -d' ' -f2)
if [[ "$python_version" < "3.11" ]]; then
    print_warning "Python $python_version found. Python 3.11+ recommended for optimal performance."
else
    print_status "Python $python_version ✓"
fi

# Check virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Virtual environment active ✓"
else
    print_warning "No virtual environment detected. Consider using: python -m venv venv"
fi

# Check dependencies
print_info "Checking dependencies..."
if python -c "import flask, requests, cv2, numpy, PIL" 2>/dev/null; then
    print_status "Core dependencies installed ✓"
else
    print_error "Missing dependencies. Run: pip install -r requirements.txt"
    exit 1
fi

# Check .env file
if [ -f ".env" ]; then
    print_status "Environment configuration found ✓"
    
    # Source .env file
    source .env 2>/dev/null || true
    
    # Check OCR API URL
    if [ -n "$OCR_API_URL" ]; then
        print_info "Testing OCR API connectivity..."
        if curl -I -m 10 "$OCR_API_URL" 2>/dev/null | grep -q "HTTP"; then
            print_status "OCR API reachable ✓"
        else
            print_warning "OCR API not reachable. Check OCR_API_URL in .env"
        fi
    else
        print_warning "OCR_API_URL not set in .env file"
    fi
    
    # Check SECRET_KEY
    if [ -n "$SECRET_KEY" ] && [ "$SECRET_KEY" != "dev-key-change-in-production" ]; then
        print_status "Secure SECRET_KEY configured ✓"
    else
        print_warning "Using default SECRET_KEY. Change for production!"
    fi
else
    print_warning "No .env file found. Copy from .env.example"
fi

# Check directories
print_info "Checking directory structure..."
required_dirs=("app" "static" "templates" "logs")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_status "$dir/ directory exists ✓"
    else
        if [ "$dir" == "logs" ]; then
            mkdir -p logs
            print_status "$dir/ directory created ✓"
        else
            print_error "$dir/ directory missing!"
            exit 1
        fi
    fi
done

# Check key files
print_info "Checking key files..."
key_files=("run.py" "config.py" "requirements.txt" "Dockerfile" "docker-compose.yml" "vercel.json")
for file in "${key_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "$file exists ✓"
    else
        print_error "$file missing!"
    fi
done

# Test import
print_info "Testing application import..."
if python -c "from app import create_app; app = create_app(); print('✓ Application imports successfully')" 2>/dev/null; then
    print_status "Application imports successfully ✓"
else
    print_error "Application import failed!"
    exit 1
fi

# Port availability check
print_info "Checking port availability..."
if ! netstat -tuln 2>/dev/null | grep -q ":8080 "; then
    print_status "Port 8080 available ✓"
else
    print_warning "Port 8080 already in use"
fi

# Docker availability (if docker is installed)
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        print_status "Docker available and running ✓"
        
        # Test Docker build
        print_info "Testing Docker build..."
        if docker build -t cardscan-pro-test . >/dev/null 2>&1; then
            print_status "Docker build successful ✓"
            docker rmi cardscan-pro-test >/dev/null 2>&1 || true
        else
            print_warning "Docker build failed. Check Dockerfile"
        fi
    else
        print_warning "Docker installed but not running"
    fi
else
    print_info "Docker not installed (optional)"
fi

# Deployment readiness score
echo
echo "📊 Deployment Readiness Summary"
echo "================================"

readiness_score=0
total_checks=10

# Core checks
[[ "$python_version" > "3.11" ]] && ((readiness_score++))
[[ "$VIRTUAL_ENV" != "" ]] && ((readiness_score++))
[ -f ".env" ] && ((readiness_score++))
[[ -n "$OCR_API_URL" ]] && ((readiness_score++))
[[ -n "$SECRET_KEY" && "$SECRET_KEY" != "dev-key-change-in-production" ]] && ((readiness_score++))
[ -f "run.py" ] && ((readiness_score++))
[ -f "Dockerfile" ] && ((readiness_score++))
[ -f "docker-compose.yml" ] && ((readiness_score++))
[ -f "vercel.json" ] && ((readiness_score++))
[ -d "logs" ] && ((readiness_score++))

percentage=$((readiness_score * 100 / total_checks))

if [ $percentage -ge 90 ]; then
    print_status "Deployment Readiness: ${percentage}% - Production Ready! 🚀"
elif [ $percentage -ge 70 ]; then
    print_warning "Deployment Readiness: ${percentage}% - Almost Ready ⚡"
else
    print_error "Deployment Readiness: ${percentage}% - Needs Attention 🔧"
fi

echo
echo "🎯 CardScan Pro - Ready for Deployment!"
echo
echo "Quick Deploy Commands:"
echo "• Docker:     ./deploy.sh docker"
echo "• Vercel:     ./deploy.sh vercel"  
echo "• Local:      ./deploy.sh local"
echo
echo "Visit: http://localhost:8080 after deployment"