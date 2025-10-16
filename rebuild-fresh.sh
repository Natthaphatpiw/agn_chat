#!/bin/bash
# Complete fresh rebuild on server
# This will:
# 1. Remove ALL Docker cache
# 2. Reinstall all pip packages with latest versions
# 3. Rebuild from scratch

SERVER_USER="azureuser"
SERVER_IP="40.81.244.202"
SSH_KEY="piw_key.pem"
REMOTE_DIR="~/agn_chat"

echo "🧹 Complete Fresh Rebuild on Server"
echo "===================================="
echo ""
echo "⚠️  WARNING: This will:"
echo "  - Remove ALL Docker images, containers, and volumes"
echo "  - Reinstall all Python packages"
echo "  - Take 10-20 minutes to complete"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "📦 Step 1/6: Syncing latest code to server..."
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

echo "✅ Code synced"
echo ""

echo "🛑 Step 2/6: Stopping all containers..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat
docker-compose down -v 2>/dev/null || true
echo "✅ Containers stopped"
ENDSSH

echo ""

echo "🧹 Step 3/6: Removing ALL Docker cache..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
# Stop all containers
docker stop $(docker ps -aq) 2>/dev/null || true

# Remove all containers
docker rm $(docker ps -aq) 2>/dev/null || true

# Remove all images
docker rmi $(docker images -q) -f 2>/dev/null || true

# Remove all volumes
docker volume rm $(docker volume ls -q) 2>/dev/null || true

# System prune (removes everything)
docker system prune -a -f --volumes

echo "✅ Docker completely cleaned"
ENDSSH

echo ""

echo "📝 Step 4/6: Updating .env configuration..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

# Backup .env
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create fresh .env from example
cp .env.example .env

echo ""
echo "⚠️  IMPORTANT: Edit .env and add your OPENAI_API_KEY"
echo "Current .env (you need to add OPENAI_API_KEY):"
cat .env
echo ""
ENDSSH

echo ""
echo "⏸️  Paused for .env configuration"
echo "Please complete these steps on the server:"
echo ""
echo "  ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP"
echo "  cd ~/agn_chat"
echo "  nano .env"
echo "  # Add your OPENAI_API_KEY=sk-..."
echo "  # Save and exit (Ctrl+O, Enter, Ctrl+X)"
echo ""
read -p "Press Enter when you've updated .env on the server..."

echo ""
echo "🏗️  Step 5/6: Building fresh Docker image (this will take 5-10 minutes)..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

echo "Building Docker image with fresh pip install..."
docker-compose build --no-cache --pull

echo "✅ Build completed"
ENDSSH

echo ""

echo "🚀 Step 6/6: Starting services..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

docker-compose up -d

echo "✅ Services started"
echo ""
echo "Waiting 30 seconds for startup..."
sleep 30

echo ""
echo "📊 Container status:"
docker-compose ps

echo ""
echo "📋 Recent logs:"
docker-compose logs --tail=100

ENDSSH

echo ""
echo "===================================="
echo "🎉 Fresh rebuild completed!"
echo ""
echo "Next steps:"
echo "1. Check logs: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'cd ~/agn_chat && docker-compose logs -f'"
echo "2. Test: curl http://$SERVER_IP:8001/health"
echo ""
