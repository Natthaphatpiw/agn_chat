#!/bin/bash

# AGN Health Chat Application Deployment Script
# Usage: ./deploy.sh [start|stop|restart|logs|status|build]

set -e

PROJECT_NAME="agn-chat"
COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Function to check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from env.docker..."
        if [ -f "env.docker" ]; then
            cp env.docker .env
            print_success ".env file created from env.docker"
            print_warning "Please review and modify .env file if needed"
        else
            print_error "env.docker file not found. Please create .env file manually."
            exit 1
        fi
    else
        print_success ".env file found"
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p logs
    mkdir -p models
    print_success "Directories created"
}

# Function to start the application
start_app() {
    print_status "Starting $PROJECT_NAME application..."
    docker compose up -d
    print_success "Application started successfully"
    print_status "Application is running on http://localhost:8001"
    print_status "Health check: http://localhost:8001/health"
}

# Function to stop the application
stop_app() {
    print_status "Stopping $PROJECT_NAME application..."
    docker compose down
    print_success "Application stopped successfully"
}

# Function to restart the application
restart_app() {
    print_status "Restarting $PROJECT_NAME application..."
    docker compose restart
    print_success "Application restarted successfully"
}

# Function to show logs
show_logs() {
    print_status "Showing logs for $PROJECT_NAME application..."
    docker compose logs -f
}

# Function to show status
show_status() {
    print_status "Application status:"
    docker compose ps
    echo ""
    print_status "Container resource usage:"
    docker stats --no-stream agn-chat-app 2>/dev/null || print_warning "Container not running"
}

# Function to build the application
build_app() {
    print_status "Building $PROJECT_NAME application..."
    
    # Check if user wants to use standard Dockerfile
    if [ "$2" = "standard" ]; then
        print_status "Using standard Dockerfile..."
        docker compose -f docker-compose.standard.yml build --no-cache
    else
        print_status "Using minimal Dockerfile (recommended)..."
        docker compose build --no-cache
    fi
    
    print_success "Application built successfully"
}

# Function to show help
show_help() {
    echo "AGN Health Chat Application Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start the application"
    echo "  stop      Stop the application"
    echo "  restart   Restart the application"
    echo "  logs      Show application logs"
    echo "  status    Show application status"
    echo "  build     Build the application (minimal Dockerfile)"
    echo "  build standard  Build with standard Dockerfile"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start the application"
    echo "  $0 build     # Build with minimal Dockerfile (recommended)"
    echo "  $0 build standard  # Build with standard Dockerfile"
    echo "  $0 logs      # Show logs in real-time"
    echo "  $0 status    # Check application status"
}

# Main script logic
main() {
    case "${1:-start}" in
        "start")
            check_docker
            check_env
            create_directories
            start_app
            ;;
        "stop")
            check_docker
            stop_app
            ;;
        "restart")
            check_docker
            restart_app
            ;;
        "logs")
            check_docker
            show_logs
            ;;
        "status")
            check_docker
            show_status
            ;;
        "build")
            check_docker
            check_env
            create_directories
            build_app
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
