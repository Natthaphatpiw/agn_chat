# 🐳 Docker Deployment - AGN Health Chat

## 📦 ไฟล์ที่เกี่ยวข้อง

- `Dockerfile.simple` - Dockerfile แบบง่าย ใช้ `requirements-docker.txt` **(แนะนำ)**
- `Dockerfile.minimal` - Dockerfile ที่ระบุ version แน่นอน
- `Dockerfile` - Dockerfile แบบมาตรฐาน
- `requirements-docker.txt` - Dependencies แบบง่าย ไม่ระบุ version
- `requirements-minimal.txt` - Dependencies ที่ระบุ version range
- `docker-compose.yml` - ใช้ `Dockerfile.simple`
- `deploy.sh` - Script สำหรับ deployment

## 🚀 วิธีรันบน Server

### ขั้นตอนที่ 1: อัปโหลดไฟล์

```bash
# Upload ไปยัง server
scp -r /path/to/agn_chat user@server-ip:/home/user/
```

### ขั้นตอนที่ 2: ติดตั้ง Docker (ถ้ายังไม่มี)

```bash
# บน server
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# logout และ login ใหม่
```

### ขั้นตอนที่ 3: ตั้งค่า Environment Variables

```bash
cd /home/user/agn_chat
cp env.docker .env
nano .env  # แก้ไข OPENAI_API_KEY ถ้ามี
```

### ขั้นตอนที่ 4: รัน Application

**วิธีที่ 1: ใช้ deploy script (ง่ายที่สุด)**
```bash
chmod +x deploy.sh
./deploy.sh start
```

**วิธีที่ 2: ใช้ docker compose**
```bash
docker compose up -d
```

**วิธีที่ 3: Build และรันแยก**
```bash
# Build image
docker compose build

# Run container
docker compose up -d

# ดู logs
docker compose logs -f
```

## 🔍 ตรวจสอบการทำงาน

```bash
# Check health
curl http://localhost:8001/health

# ทดสอบ chat
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "ปวดหัวทำไง", "top_k": 5}'
```

## 🛠️ คำสั่งที่ใช้บ่อย

```bash
# ดู logs
docker compose logs -f agn-chat

# หยุด application
docker compose down

# รีสตาร์ท
docker compose restart

# ดู status
docker compose ps

# Rebuild (หลังแก้ไขโค้ด)
docker compose build --no-cache
docker compose up -d
```

## 🐛 แก้ปัญหา

### ปัญหา: Dependency conflicts

**แนะนำ: ใช้ `Dockerfile.simple` + `requirements-docker.txt`**

```bash
# ใช้ไฟล์ docker-compose.yml ที่มี Dockerfile.simple อยู่แล้ว
docker compose build --no-cache
docker compose up -d
```

หากยังมีปัญหา ลองใช้ Dockerfile อื่น:

```bash
# แก้ไข docker-compose.yml เปลี่ยน dockerfile: เป็น
# - Dockerfile.minimal (ระบุ version range)
# - Dockerfile (version ปกติ)

docker compose build --no-cache
docker compose up -d
```

### ปัญหา: Container ไม่เริ่ม

```bash
# ดู logs เพื่อหาสาเหตุ
docker compose logs agn-chat

# ตรวจสอบ port ว่าถูกใช้งานหรือไม่
netstat -tulpn | grep 8001

# เข้าไปใน container เพื่อ debug
docker compose run --rm agn-chat bash
```

### ปัญหา: Out of memory

```bash
# เช็ค memory
free -h
docker stats

# ลด context window ใน .env
nano .env
# แก้เป็น
LOCAL_LLM_CONTEXT=2048
LOCAL_LLM_MAX_TOKENS=512

# Restart
docker compose restart
```

### ปัญหา: Model ดาวน์โหลดช้า

```bash
# Model จะถูกดาวน์โหลดครั้งแรกที่รัน (ประมาณ 4GB)
# ใช้เวลา 5-15 นาที ขึ้นกับ internet

# ตรวจสอบ progress
docker compose logs -f agn-chat
```

## 🌐 Production Setup

### 1. ใช้ Nginx Reverse Proxy

```bash
sudo apt install nginx

# สร้างไฟล์ config
sudo nano /etc/nginx/sites-available/agn-chat
```

เนื้อหา:
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

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/agn-chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. ใช้ SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Auto-start on boot

สร้างไฟล์ `/etc/systemd/system/agn-chat.service`:

```ini
[Unit]
Description=AGN Chat Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/agn_chat
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable agn-chat
sudo systemctl start agn-chat
```

## 📊 Monitoring

```bash
# ดู resource usage
docker stats agn-chat-app

# ดู logs แบบ real-time
docker compose logs -f

# ดู disk usage
docker system df
```

## 💾 Backup

```bash
# Backup models
tar -czf models-backup-$(date +%Y%m%d).tar.gz models/

# Backup .env
cp .env .env.backup
```

## 🔄 Update Application

```bash
# Pull โค้ดใหม่
git pull

# Rebuild และ restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 📝 หมายเหตุ

- Application จะดาวน์โหลด model ครั้งแรก (4GB, ใช้เวลา 5-15 นาที)
- แนะนำ RAM อย่างน้อย 8GB
- MongoDB ใช้ cloud database ไม่ต้องติดตั้งแยก
- Port 8001 ต้องเปิดใน firewall

## 🆘 ติดปัญหา?

ดูรายละเอียดเพิ่มเติมใน:
- `DOCKER_DEPLOYMENT.md` - คู่มือแบบละเอียด
- `QUICK_START.md` - คู่มือแบบสั้น
