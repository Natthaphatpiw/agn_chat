# 💾 แก้ปัญหา Disk Space - No Space Left on Device

## 🔴 ปัญหา

เจอ error: `[Errno 28] No space left on device` เวลา build Docker image

**สาเหตุ:** PyTorch พยายามติดตั้ง CUDA version ที่มีขนาดใหญ่มาก (หลาย GB)

## ✅ วิธีแก้ (เลือก 1 วิธี)

### วิธีที่ 1: ใช้ Dockerfile.light (แนะนำ) ⭐

**Dockerfile.light ใช้ PyTorch CPU-only ขนาดเล็กกว่ามาก**

ไฟล์ `docker-compose.yml` ถูกตั้งค่าให้ใช้ `Dockerfile.light` แล้ว

```bash
# ก่อนอื่นให้ทำความสะอาด Docker
docker system prune -a --volumes -f

# จากนั้นลอง build ใหม่
docker compose build --no-cache
docker compose up -d
```

### วิธีที่ 2: เพิ่มพื้นที่บน Server

```bash
# ตรวจสอบพื้นที่ว่าง
df -h

# ลบ Docker images/containers เก่า
docker system prune -a --volumes

# ลบ package cache
sudo apt clean
sudo apt autoremove

# ลบ logs เก่า
sudo journalctl --vacuum-time=3d
```

### วิธีที่ 3: ติดตั้ง Dependencies แบบแยกส่วน

ใช้ไฟล์ที่ติดตั้งทีละขั้นตอน:

```bash
# แก้ไข docker-compose.yml เปลี่ยนเป็น
dockerfile: Dockerfile.staged
```

จากนั้นสร้างไฟล์ `Dockerfile.staged`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make curl && \
    rm -rf /var/lib/apt/lists/*

# Install packages in stages to manage disk usage
RUN pip install --no-cache-dir fastapi uvicorn pydantic\<2.0 pymongo && \
    rm -rf /root/.cache/pip

RUN pip install --no-cache-dir python-dotenv requests numpy && \
    rm -rf /root/.cache/pip

# Install torch CPU-only
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    rm -rf /root/.cache/pip

RUN pip install --no-cache-dir transformers sentence-transformers && \
    rm -rf /root/.cache/pip

RUN pip install --no-cache-dir llama-index huggingface-hub && \
    rm -rf /root/.cache/pip

RUN pip install --no-cache-dir \
    llama-index-vector-stores-mongodb \
    llama-index-embeddings-huggingface \
    llama-index-llms-openai \
    llama-index-llms-llama-cpp \
    llama-cpp-python \
    colorlog && \
    rm -rf /root/.cache/pip

RUN mkdir -p logs models
COPY app.py config.py ./

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 📊 เปรียบเทียบขนาด

| Package | CUDA Version | CPU Version |
|---------|--------------|-------------|
| PyTorch | ~2-3 GB | ~200 MB |
| Total | ~5-6 GB | ~1-2 GB |

**ใช้ CPU version ประหยัดพื้นที่ได้ 4-5 GB!**

## 🔍 ตรวจสอบพื้นที่ก่อน Build

```bash
# เช็คพื้นที่ว่าง (ควรมีอย่างน้อย 10GB)
df -h

# เช็คขนาด Docker
docker system df

# ทำความสะอาด Docker ก่อน build
docker system prune -a --volumes
```

## 🚀 ขั้นตอนที่แนะนำ

```bash
# 1. ทำความสะอาด
docker system prune -a --volumes -f
sudo apt clean
sudo apt autoremove

# 2. ตรวจสอบพื้นที่
df -h

# 3. Build ด้วย Dockerfile.light (ใช้ CPU-only torch)
docker compose build --no-cache

# 4. รัน
docker compose up -d

# 5. ดู logs
docker compose logs -f
```

## 💡 Tips เพิ่มเติม

1. **ใช้ CPU-only PyTorch** - เร็วพอสำหรับ production และประหยัดพื้นที่
2. **ทำความสะอาดเป็นประจำ** - `docker system prune` ทุกสัปดาห์
3. **Monitor disk usage** - `df -h` และ `docker system df`
4. **ใช้ .dockerignore** - อยู่ในโปรเจคแล้ว ป้องกันไฟล์ไม่จำเป็นเข้า build

## 🆘 ยังแก้ไม่ได้?

ถ้ายังมีปัญหา:

1. **เพิ่ม disk space ของ server** (แนะนำอย่างน้อย 20GB)
2. **ใช้ external volume** สำหรับ Docker
3. **พิจารณาใช้ OpenAI API แทน local model** (ไม่ต้องดาวน์โหลด model 4GB)

## 📝 หมายเหตุ

- `Dockerfile.light` ใช้ PyTorch CPU-only
- Application จะยังทำงานได้ปกติ แต่ใช้ CPU แทน GPU
- สำหรับ chatbot ทั่วไป CPU เพียงพอแล้ว
- ถ้ามี OpenAI API key จะเร็วกว่าและใช้ resource น้อยกว่า
