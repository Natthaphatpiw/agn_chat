#!/bin/bash
# Complete deployment script for server
# Usage: ./deploy-server.sh

set -e  # Exit on error

SERVER_USER="azureuser"
SERVER_IP="40.81.244.202"
SSH_KEY="piw_key.pem"
REMOTE_DIR="~/agn_chat"

echo "🚀 AGN Chat Deployment Script"
echo "================================"
echo ""

# Step 1: Sync files to server
echo "📦 Step 1/5: Syncing files to server..."
rsync -avz --progress \
  --exclude='__pycache__' \
  --exclude='venv' \
  --exclude='models' \
  --exclude='logs' \
  --exclude='.git' \
  --exclude='*.pem' \
  --exclude='node_modules' \
  -e "ssh -i $SSH_KEY" \
  . $SERVER_USER@$SERVER_IP:$REMOTE_DIR/

echo "✅ Files synced successfully"
echo ""

# Step 2: Check .env file
echo "📝 Step 2/5: Checking .env configuration..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP "bash -s" << 'ENDSSH'
cd ~/agn_chat

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env not found. Creating from .env.example..."
    cp .env.example .env
    echo "❗ Please edit .env and add your OPENAI_API_KEY"
    exit 1
fi

# Check if OPENAI_MODEL is set
if ! grep -q "OPENAI_MODEL" .env; then
    echo "⚠️  OPENAI_MODEL not found in .env. Adding it..."
    echo "" >> .env
    echo "# OpenAI Model Configuration" >> .env
    echo "OPENAI_MODEL=gpt-4o-mini" >> .env
fi

# Show current configuration
echo "Current .env configuration:"
echo "=========================="
grep -E "OPENAI_API_KEY|OPENAI_MODEL|MONGODB_URL" .env | sed 's/OPENAI_API_KEY=sk-.*/OPENAI_API_KEY=sk-***hidden***/'
echo "=========================="

ENDSSH

echo ""

# Step 3: Clean up old Docker resources
echo "🧹 Step 3/5: Cleaning up Docker..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

# Stop and remove old containers
echo "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Clean up Docker system
echo "Cleaning Docker system..."
docker system prune -f
docker volume prune -f

echo "✅ Docker cleaned"
ENDSSH

echo ""

# Step 4: Build and start
echo "🏗️  Step 4/5: Building and starting services..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

# Build with no cache to ensure fresh build
echo "Building Docker image (this may take a few minutes)..."
docker-compose build --no-cache

# Start services
echo "Starting services..."
docker-compose up -d

echo "✅ Services started"
ENDSSH

echo ""

# Step 5: Verify deployment
echo "🔍 Step 5/5: Verifying deployment..."
echo "Waiting for service to start (30 seconds)..."
sleep 30

ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

# Check container status
echo "Container status:"
docker-compose ps

# Show logs
echo ""
echo "Recent logs:"
echo "============"
docker-compose logs --tail=50 agn-chat

# Test health endpoint
echo ""
echo "Testing health endpoint..."
HEALTH_STATUS=$(curl -s http://localhost:8001/health || echo "Failed")
if [[ $HEALTH_STATUS == *"healthy"* ]]; then
    echo "✅ Health check passed!"
    echo "Response: $HEALTH_STATUS"
else
    echo "❌ Health check failed!"
    echo "Response: $HEALTH_STATUS"
fi

ENDSSH

echo ""
echo "================================"
echo "🎉 Deployment completed!"
echo ""
echo "Next steps:"
echo "1. Check logs: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'cd ~/agn_chat && docker-compose logs -f'"
echo "2. Test API: curl http://$SERVER_IP:8001/health"
echo "3. View docs: http://$SERVER_IP:8001/docs"
echo ""
