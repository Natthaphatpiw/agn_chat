#!/bin/bash
# Cleanup script for server disk space

echo "🧹 Starting cleanup..."

# Clean Docker
echo "Cleaning Docker..."
docker system prune -a -f
docker volume prune -f

# Clean caches
echo "Cleaning caches..."
rm -rf ~/.cache/huggingface/*
rm -rf ~/.cache/torch/*
rm -rf ~/.cache/pip/*

# Clean temp files
echo "Cleaning temp files..."
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# Clean apt
echo "Cleaning apt..."
sudo apt-get clean
sudo apt-get autoremove -y

# Clean logs (keep last 1000 lines only)
echo "Cleaning logs..."
if [ -f ~/agn_chat/logs/app.log ]; then
    tail -1000 ~/agn_chat/logs/app.log > ~/agn_chat/logs/app.log.tmp
    mv ~/agn_chat/logs/app.log.tmp ~/agn_chat/logs/app.log
fi

# Show disk space
echo ""
echo "📊 Disk space after cleanup:"
df -h

echo ""
echo "✅ Cleanup completed!"
