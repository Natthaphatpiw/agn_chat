#!/bin/bash
# Quick fix for .env configuration on server
# Usage: ./fix-server-env.sh

SERVER_USER="azureuser"
SERVER_IP="40.81.244.202"
SSH_KEY="piw_key.pem"

echo "🔧 Fixing .env configuration on server..."
echo ""

ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP "bash -s" << 'ENDSSH'
cd ~/agn_chat

echo "Current .env file:"
echo "=================="
cat .env
echo "=================="
echo ""

# Backup current .env
echo "📋 Backing up current .env..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Remove old OPENAI_MODEL if exists
echo "🔧 Removing old OPENAI_MODEL..."
sed -i '/OPENAI_MODEL/d' .env

# Add correct OPENAI_MODEL
echo "➕ Adding correct OPENAI_MODEL..."
echo "" >> .env
echo "# OpenAI Model Configuration (Updated)" >> .env
echo "OPENAI_MODEL=gpt-4o-mini" >> .env

echo ""
echo "✅ Updated .env file:"
echo "=================="
cat .env
echo "=================="

ENDSSH

echo ""
echo "✅ .env fixed!"
echo ""
echo "Next: Run deployment script"
echo "  ./deploy-server.sh"
