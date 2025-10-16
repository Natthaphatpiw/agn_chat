# Quick Start Guide - AGN Health Chat Docker

## 🚀 รัน Application บน Server

### 1. อัปโหลดไฟล์ไป Server
```bash
scp -r /Users/piw/Downloads/agn_chat user@your-server:/home/user/
```

### 2. เข้าไปในโฟลเดอร์และตั้งค่า
```bash
cd /home/user/agn_chat
cp env.docker .env
nano .env  # แก้ไขค่าตามต้องการ
```

### 3. รัน Application
```bash
# วิธีที่ 1: ใช้ deploy script (แนะนำ)
chmod +x deploy.sh
./deploy.sh start

# วิธีที่ 2: ใช้ docker compose
docker compose up -d
```

### 4. ตรวจสอบการทำงาน
```bash
curl http://localhost:8001/health
```

## 🔧 คำสั่งที่มีประโยชน์

```bash
# ดู logs
./deploy.sh logs
# หรือ
docker compose logs -f

# หยุด application
./deploy.sh stop
# หรือ
docker compose down

# รีสตาร์ท
./deploy.sh restart

# ดู status
./deploy.sh status
```

## 🐛 แก้ปัญหา Dependency Conflicts

หากเจอ error dependency conflicts:

```bash
# ใช้ minimal Dockerfile (แนะนำ)
./deploy.sh build
./deploy.sh start

# หรือใช้ standard Dockerfile
docker compose -f docker-compose.standard.yml up -d
```

## 📝 API Usage

```bash
# ส่งคำถาม
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "อาการปวดหัวเกิดจากอะไร", "top_k": 5}'
```

## 🌐 Production Setup

1. ตั้งค่า Nginx reverse proxy
2. ใช้ SSL certificate (Let's Encrypt)
3. ตั้งค่า systemd service สำหรับ auto-restart

ดูรายละเอียดใน `DOCKER_DEPLOYMENT.md`
