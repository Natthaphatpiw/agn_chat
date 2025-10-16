# Docker Deployment Guide for AGN Health Q&A Chat Application

## ไฟล์ที่สร้างขึ้น

- `Dockerfile` - ไฟล์สำหรับสร้าง Docker image (ใช้ requirements.txt)
- `Dockerfile.minimal` - ไฟล์สำหรับสร้าง Docker image (ใช้ requirements-minimal.txt) - **แนะนำ**
- `docker-compose.yml` - ไฟล์สำหรับจัดการ container และ network (ใช้ Dockerfile.minimal)
- `docker-compose.standard.yml` - ไฟล์สำหรับใช้ Dockerfile ปกติ
- `.dockerignore` - ไฟล์สำหรับกำหนดว่าอะไรบ้างที่ไม่ต้องส่งไปใน Docker build context
- `env.docker` - ไฟล์ตัวอย่าง environment variables สำหรับ Docker
- `requirements-minimal.txt` - ไฟล์ dependencies ที่แก้ไขปัญหา conflicts แล้ว
- `deploy.sh` - Script สำหรับจัดการ deployment

## การติดตั้งและรันบน Server

### 1. เตรียม Server

```bash
# อัปเดตระบบ
sudo apt update && sudo apt upgrade -y

# ติดตั้ง Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# ติดตั้ง Docker Compose
sudo apt install docker-compose-plugin -y

# เพิ่ม user เข้า Docker group (ไม่ต้องใช้ sudo)
sudo usermod -aG docker $USER
# ต้อง logout และ login ใหม่เพื่อให้มีผล
```

### 2. อัปโหลดโค้ดไปยัง Server

```bash
# ใช้ scp หรือ rsync อัปโหลดไฟล์
scp -r /Users/piw/Downloads/agn_chat user@your-server-ip:/home/user/

# หรือใช้ git clone
git clone <your-repo-url> /home/user/agn_chat
```

### 3. ตั้งค่า Environment Variables

```bash
# เข้าไปในโฟลเดอร์โปรเจค
cd /home/user/agn_chat

# คัดลอกไฟล์ environment variables
cp env.docker .env

# แก้ไขไฟล์ .env ตามต้องการ
nano .env
```

### 4. รัน Application ด้วย Docker Compose

#### วิธีที่ 1: ใช้ Minimal Dockerfile (แนะนำ)

```bash
# สร้างและรัน container ด้วย minimal dependencies
docker compose up -d

# ดู logs
docker compose logs -f

# ดู status
docker compose ps
```

#### วิธีที่ 2: ใช้ Standard Dockerfile

```bash
# หากมีปัญหา dependency conflicts กับ minimal version
docker compose -f docker-compose.standard.yml up -d

# ดู logs
docker compose -f docker-compose.standard.yml logs -f
```

#### วิธีที่ 3: ใช้ Deploy Script

```bash
# ทำให้ script executable
chmod +x deploy.sh

# รัน application
./deploy.sh start

# หรือ build และ start
./deploy.sh build
./deploy.sh start
```

### 5. ตรวจสอบการทำงาน

```bash
# ตรวจสอบ health endpoint
curl http://localhost:8001/health

# ตรวจสอบ root endpoint
curl http://localhost:8001/
```

## คำสั่งที่มีประโยชน์

### จัดการ Container

```bash
# หยุด application
docker compose down

# หยุดและลบ volumes
docker compose down -v

# รีสตาร์ท application
docker compose restart

# ดู logs แบบ real-time
docker compose logs -f agn-chat

# เข้าไปใน container
docker compose exec agn-chat bash
```

### จัดการ Docker Images

```bash
# ดู images ทั้งหมด
docker images

# ลบ image ที่ไม่ใช้
docker image prune

# Rebuild image ใหม่
docker compose build --no-cache
docker compose up -d
```

## การตั้งค่า Production

### 1. ใช้ Reverse Proxy (Nginx)

สร้างไฟล์ `/etc/nginx/sites-available/agn-chat`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. ใช้ SSL Certificate (Let's Encrypt)

```bash
# ติดตั้ง certbot
sudo apt install certbot python3-certbot-nginx -y

# ได้รับ SSL certificate
sudo certbot --nginx -d your-domain.com
```

### 3. ตั้งค่า Auto-restart

สร้างไฟล์ `systemd service`:

```bash
# สร้างไฟล์ service
sudo nano /etc/systemd/system/agn-chat.service
```

เนื้อหาไฟล์:

```ini
[Unit]
Description=AGN Health Chat Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/agn_chat
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

เปิดใช้งาน service:

```bash
sudo systemctl enable agn-chat.service
sudo systemctl start agn-chat.service
```

## การ Monitor และ Logs

### 1. ดู Logs

```bash
# ดู logs ของ application
docker compose logs -f agn-chat

# ดู logs แบบมี timestamp
docker compose logs -t -f agn-chat

# ดู logs ย้อนหลัง 100 บรรทัด
docker compose logs --tail=100 agn-chat
```

### 2. ตรวจสอบ Resource Usage

```bash
# ดูการใช้ resource
docker stats agn-chat-app

# ดู disk usage
docker system df
```

## การ Backup

### 1. Backup Models Directory

```bash
# สร้าง backup
tar -czf models-backup-$(date +%Y%m%d).tar.gz models/

# Restore backup
tar -xzf models-backup-YYYYMMDD.tar.gz
```

### 2. Backup Environment

```bash
# Backup .env file
cp .env .env.backup-$(date +%Y%m%d)
```

## การ Troubleshooting

### 1. Dependency Conflicts Error

หากเจอ error `ResolutionImpossible` หรือ `dependency conflicts`:

```bash
# วิธีที่ 1: ใช้ minimal Dockerfile (แนะนำ)
docker compose build --no-cache
docker compose up -d

# วิธีที่ 2: ใช้ standard Dockerfile
docker compose -f docker-compose.standard.yml build --no-cache
docker compose -f docker-compose.standard.yml up -d

# วิธีที่ 3: ลองใช้ deploy script
./deploy.sh build
./deploy.sh start
```

### 2. Container ไม่สามารถเริ่มได้

```bash
# ดู logs
docker compose logs agn-chat

# ตรวจสอบ environment variables
docker compose config

# ตรวจสอบ port conflicts
netstat -tulpn | grep 8001

# ลองรัน container แบบ interactive เพื่อ debug
docker compose run --rm agn-chat bash
```

### 3. Model ไม่สามารถดาวน์โหลดได้

```bash
# เข้าไปใน container และดาวน์โหลดแบบ manual
docker compose exec agn-chat bash
python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('TheBloke/Llama-2-7B-Chat-GGUF', 'llama-2-7b-chat.Q4_K_M.gguf', cache_dir='./models'))"
```

### 4. Memory Issues

```bash
# ตรวจสอบ memory usage
free -h
docker stats

# ลด context window ใน .env
LOCAL_LLM_CONTEXT=2048
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /chat` - Chat endpoint

### ตัวอย่างการใช้งาน API

```bash
# ส่งคำถาม
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "อาการปวดหัวเกิดจากอะไร",
    "top_k": 5
  }'
```

## หมายเหตุ

- Application จะดาวน์โหลด model ขนาดประมาณ 4GB ครั้งแรกที่รัน
- ใช้เวลาประมาณ 5-10 นาทีในการเริ่มต้นครั้งแรก
- แนะนำให้ใช้ server ที่มี RAM อย่างน้อย 8GB
- MongoDB ใช้ cloud database ที่มีอยู่แล้ว ไม่ต้องติดตั้งแยก
