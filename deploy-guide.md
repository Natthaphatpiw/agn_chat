# AGN Health Q&A RAG - Production Deployment Guide

## 📋 Prerequisites

- Docker & Docker Compose installed
- MongoDB Atlas M10+ cluster with Vector Search
- OpenAI API key (for production)
- Server with 4GB+ RAM

---

## 🚀 Deployment Steps

### 1. Copy Files to Server

```bash
# From your local machine
scp -r agn_chat/ user@your-server:~/

# Or use git
git clone your-repo
cd agn_chat
```

### 2. Create `.env` File

```bash
# On the server
cd ~/agn_chat

# Copy example and edit
cp .env.production .env
nano .env
```

**Important: Set your OpenAI API key!**

```bash
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

### 3. Build and Deploy

```bash
# Build Docker image
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f agn-chat
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8001/health

# Test query
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "อาการปวดหัวควรทำอย่างไร"}'
```

---

## 🔧 Configuration

### Using OpenAI (Recommended for Production)

```bash
# In .env
OPENAI_API_KEY=sk-xxxxx
```

**Benefits:**
- ✅ No need to download large models (2.5GB + 4GB)
- ✅ Faster response times (1-2 seconds)
- ✅ Better Thai language support
- ✅ Smaller Docker image (~500MB vs 5GB+)

### Using Local Llama-2 (Fallback)

If no OpenAI key:
- Will download models on first run (~6.5GB total)
- Slower response (5-10 seconds)
- Requires more disk space

---

## 📊 Resource Usage

### With OpenAI API:
- **Disk**: ~2GB (app + embedding model)
- **RAM**: ~2-3GB
- **Startup**: 10-30 seconds

### With Local Llama-2:
- **Disk**: ~8GB (app + all models)
- **RAM**: ~4-6GB
- **Startup**: 1-3 minutes (first run longer)

---

## 🔄 Management Commands

```bash
# View logs
docker-compose logs -f

# Restart service
docker-compose restart

# Stop service
docker-compose down

# Rebuild after code changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check status
docker-compose ps

# View resource usage
docker stats agn-chat-app
```

---

## 🌐 Expose to Internet (Optional)

### Option 1: Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 2: Caddy (with auto-SSL)

```
your-domain.com {
    reverse_proxy localhost:8001
}
```

---

## 🔒 Security Best Practices

1. **Never commit `.env` to git**
   ```bash
   # Already in .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use firewall**
   ```bash
   # Only allow specific ports
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw enable
   ```

3. **Restrict MongoDB access**
   - Whitelist server IP in MongoDB Atlas
   - Use strong passwords

4. **Keep API key secure**
   - Store in `.env` only
   - Don't log it
   - Rotate regularly

---

## 📝 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MONGODB_URL` | MongoDB connection string | Yes | - |
| `MONGODB_DATABASE` | Database name | Yes | agn |
| `MONGODB_COLLECTION` | Collection name | Yes | qa |
| `OPENAI_API_KEY` | OpenAI API key | Recommended | - |
| `EMBEDDING_MODEL` | HuggingFace model | Yes | BAAI/bge-m3 |
| `EMBEDDING_DIMENSION` | Embedding dimensions | Yes | 1024 |
| `VECTOR_INDEX_NAME` | MongoDB index name | Yes | vector_index |
| `API_HOST` | API host | Yes | 0.0.0.0 |
| `API_PORT` | API port | Yes | 8001 |

---

## 🐛 Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs agn-chat

# Check if port is in use
sudo netstat -tulpn | grep 8001

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### MongoDB connection fails

```bash
# Test connection
docker-compose exec agn-chat python -c "
from pymongo import MongoClient
client = MongoClient('your-mongodb-url')
client.admin.command('ping')
print('Connected!')
"
```

### Out of disk space

```bash
# Clean old images
docker system prune -a

# Check usage
df -h
docker system df
```

### Slow performance

1. Check if using OpenAI API
2. Check RAM usage: `docker stats`
3. Check logs: `docker-compose logs`
4. Consider upgrading server resources

---

## 📈 Monitoring

### Basic health check

```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8001/health || echo "API down!" | mail -s "Alert" admin@example.com
```

### View metrics

```bash
# Real-time stats
docker stats agn-chat-app

# Logs
tail -f logs/app.log
```

---

## 🔄 Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 📞 Support

For issues:
1. Check logs: `docker-compose logs`
2. Review this guide
3. Check MongoDB Atlas status
4. Verify OpenAI API key

---

**Last Updated:** 2025-10-15
