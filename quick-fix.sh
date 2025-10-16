#!/bin/bash
# Quick fix - Just rebuild Docker with fresh pip install
# Faster than full rebuild

SERVER_USER="azureuser"
SERVER_IP="40.81.244.202"
SSH_KEY="piw_key.pem"

echo "⚡ Quick Fix: Fresh Docker Build"
echo "================================"
echo ""

# Sync files
echo "📦 Syncing code..."
rsync -avz \
  --exclude='venv' --exclude='models' --exclude='logs' --exclude='.git' \
  -e "ssh -i $SSH_KEY" \
  . $SERVER_USER@$SERVER_IP:~/agn_chat/

echo ""
echo "🔧 Rebuilding on server..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd ~/agn_chat

# Fix .env if needed
if ! grep -q "OPENAI_MODEL" .env 2>/dev/null; then
    echo "OPENAI_MODEL=gpt-4o-mini" >> .env
fi

# Stop
docker-compose down

# Remove old images to force fresh pip install
docker rmi $(docker images | grep agn_chat | awk '{print $3}') 2>/dev/null || true

# Prune
docker system prune -f

# Build fresh (--pull ensures base image is latest)
docker-compose build --no-cache --pull

# Start
docker-compose up -d

# Wait and show logs
sleep 20
docker-compose logs --tail=100

ENDSSH

echo ""
echo "✅ Done! Check logs above for any errors."
