# AGN Health Q&A RAG System

ระบบตอบคำถามทางการแพทย์โดยใช้ RAG (Retrieval-Augmented Generation) จากข้อมูล Q&A ของ AGN Health Forums

## 📋 สารบัญ

- [ภาพรวมโครงการ](#ภาพรวมโครงการ)
- [คุณสมบัติ](#คุณสมบัติ)
- [สถาปัตยกรรม](#สถาปัตยกรรม)
- [ข้อกำหนดระบบ](#ข้อกำหนดระบบ)
- [การติดตั้ง](#การติดตั้ง)
- [การกำหนดค่า](#การกำหนดค่า)
- [การใช้งาน](#การใช้งาน)
- [โครงสร้างโปรเจค](#โครงสร้างโปรเจค)
- [API Documentation](#api-documentation)
- [การแก้ปัญหา](#การแก้ปัญหา)

## 🎯 ภาพรวมโครงการ

โปรเจคนี้สร้างระบบ RAG สำหรับตอบคำถามทางการแพทย์โดย:
1. **Scraping**: ดึงข้อมูล Q&A จาก AGN Health Forums (2,675 threads)
2. **Embedding**: สร้าง vector embeddings สำหรับค้นหาข้อมูลที่เกี่ยวข้อง
3. **API**: ให้บริการ FastAPI endpoint สำหรับถามตอบด้วย RAG

## ✨ คุณสมบัติ

- ✅ Web scraping ด้วย Selenium + BeautifulSoup
- ✅ MongoDB Atlas สำหรับจัดเก็บข้อมูล
- ✅ Vector embeddings ด้วย BAAI/bge-m3 (1024 dimensions)
- ✅ MongoDB Atlas Vector Search
- ✅ FastAPI backend พร้อม CORS support
- ✅ รองรับทั้ง OpenAI และ local LLM
- ✅ Query normalization ด้วย LLM
- ✅ Logging และ error handling ที่สมบูรณ์

## 🏗️ สถาปัตยกรรม

```
User Query → Query Normalization (LLM) → Vector Embedding →
Vector Search (MongoDB Atlas) → Context Retrieval →
Response Generation (LLM) → Response to User
```

## 📦 ข้อกำหนดระบบ

- Python 3.8+
- Chrome/Chromium browser (สำหรับ Selenium)
- MongoDB Atlas M10+ cluster (สำหรับ Vector Search)
- 4GB+ RAM
- Internet connection

## 🚀 การติดตั้ง

### 1. Clone หรือดาวน์โหลดโปรเจค

```bash
cd /Users/piw/Downloads/agn_chat
```

### 2. สร้าง Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # สำหรับ macOS/Linux
# หรือ
venv\Scripts\activate  # สำหรับ Windows
```

### 3. ติดตั้ง Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. ตรวจสอบ ChromeDriver

Selenium จะติดตั้ง ChromeDriver อัตโนมัติผ่าน webdriver-manager แต่ต้องมี Chrome หรือ Chromium ติดตั้งในเครื่อง

## ⚙️ การกำหนดค่า

### 1. สร้างไฟล์ .env

คัดลอกจาก `.env.example`:

```bash
cp .env.example .env
```

### 2. แก้ไขไฟล์ .env

```bash
# MongoDB Configuration (ใช้ค่าเริ่มต้นที่ให้มา)
MONGODB_URL=mongodb+srv://natthapiw_db_user:afOJe2MrgMDsmm6k@cluster0.skadipr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DATABASE=agn
MONGODB_COLLECTION=qa

# OpenAI API Key (ไม่บังคับ - สำหรับคำตอบที่ดีกว่า)
OPENAI_API_KEY=sk-your-api-key-here

# Embedding Model (ค่าเริ่มต้น)
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# Vector Index (ค่าเริ่มต้น)
VECTOR_INDEX_NAME=vector_index

# Scraper Configuration
SCRAPER_START_ID=1
SCRAPER_END_ID=2675
SCRAPER_MIN_DELAY=2
SCRAPER_MAX_DELAY=5

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

**หมายเหตุ**:
- ถ้าไม่มี `OPENAI_API_KEY` ระบบจะใช้ fallback response (แสดงข้อมูลจาก context โดยตรง)
- สำหรับผลลัพธ์ที่ดีที่สุด แนะนำให้ใส่ OpenAI API key

### 3. สร้างโฟลเดอร์ logs

```bash
mkdir -p logs
```

## 💻 การใช้งาน

### ขั้นตอนที่ 1: Web Scraping

ดึงข้อมูล Q&A จากเว็บไซต์ (ใช้เวลา 2-4 ชั่วโมง สำหรับ 2,675 threads):

```bash
python scraper.py
```

**สิ่งที่เกิดขึ้น:**
- เปิด Chrome headless browser
- Scrape ทีละ thread จาก ID 1-2675
- เก็บข้อมูล: date, topic, question, answer
- บันทึกลง MongoDB collection `agn.qa`
- Skip threads ที่มีอยู่แล้ว (idempotent)
- Logs จะถูกบันทึกใน `logs/scraper.log`

**เคล็ดลับ:**
- สามารถหยุดและเริ่มใหม่ได้ (จะไม่ scrape ซ้ำ)
- ถ้าต้องการ scrape เฉพาะช่วงใด แก้ไขใน `.env`:
  ```
  SCRAPER_START_ID=1
  SCRAPER_END_ID=100
  ```

### ขั้นตอนที่ 2: Generate Embeddings

สร้าง vector embeddings สำหรับทุก document (ใช้เวลา 10-30 นาที):

```bash
python embedder.py
```

**สิ่งที่เกิดขึ้น:**
- โหลด embedding model (BAAI/bge-m3)
- รวม topic + question เป็น text
- Generate embeddings (1024 dimensions)
- บันทึก embeddings ลง field `contentVector`
- สร้าง MongoDB Atlas Vector Search index
- Logs จะถูกบันทึกใน `logs/embedder.log`

**หมายเหตุ:**
- การสร้าง Vector Search index ใน MongoDB Atlas อาจใช้เวลา 5-10 นาที
- ถ้า index ไม่สร้างอัตโนมัติ ให้สร้างใน MongoDB Atlas UI:
  - Database: `agn`
  - Collection: `qa`
  - Index Type: Vector Search
  - Index Name: `vector_index`
  - Vector Field: `contentVector`
  - Dimensions: 1024
  - Similarity: cosine

### ขั้นตอนที่ 3: เริ่ม API Server

เริ่มต้น FastAPI server:

```bash
python app.py
```

หรือใช้ uvicorn โดยตรง:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**API จะรันที่:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

## 📁 โครงสร้างโปรเจค

```
agn_chat/
├── scraper.py          # Web scraper สำหรับ AGN Health forums
├── embedder.py         # Embedding generator และ vector index creator
├── app.py              # FastAPI backend สำหรับ RAG system
├── config.py           # Configuration module
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (ไม่ commit)
├── .env.example        # Example environment file
├── README.md           # เอกสารนี้
├── logs/               # Log files
│   ├── scraper.log
│   ├── embedder.log
│   └── app.log
└── models/             # Downloaded models (auto-created)
```

## 📚 API Documentation

### Endpoints

#### 1. Root Endpoint
```http
GET /
```
ตรวจสอบสถานะ API

**Response:**
```json
{
  "message": "AGN Health Q&A RAG API",
  "version": "1.0.0",
  "status": "running"
}
```

#### 2. Health Check
```http
GET /health
```
ตรวจสอบสุขภาพของระบบ

**Response:**
```json
{
  "status": "healthy"
}
```

#### 3. Chat Endpoint
```http
POST /chat
```
ถามคำถามและรับคำตอบจาก RAG system

**Request Body:**
```json
{
  "query": "อาการปวดหัวควรทำอย่างไร",
  "top_k": 5  // optional, default: 5
}
```

**Response:**
```json
{
  "response": "คำตอบจาก LLM โดยอิงจาก Q&A ที่เกี่ยวข้อง...",
  "sources": [
    {
      "thread_id": 123,
      "topic": "โรคปวดหัว",
      "question": "ปวดหัวบ่อยควรทำอย่างไร",
      "answer": "คำตอบ...",
      "date": "2/18/2024",
      "score": 0.89
    },
    // ... อีก 4 sources
  ]
}
```

### การใช้งาน API ด้วย cURL

```bash
# Test root endpoint
curl http://localhost:8000/

# Test health check
curl http://localhost:8000/health

# Chat query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "อาการปวดหัวควรทำอย่างไร"}'
```

### การใช้งาน API ด้วย Python

```python
import requests

# Chat query
response = requests.post(
    "http://localhost:8000/chat",
    json={"query": "อาการปวดหัวควรทำอย่างไร", "top_k": 5}
)

result = response.json()
print(result["response"])
print(f"\nSources: {len(result['sources'])} documents")
```

### การใช้งาน API ด้วย JavaScript

```javascript
// Chat query
fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'อาการปวดหัวควรทำอย่างไร',
    top_k: 5
  })
})
.then(response => response.json())
.then(data => {
  console.log('Response:', data.response);
  console.log('Sources:', data.sources);
});
```

## 🐛 การแก้ปัญหา

### ปัญหา: Selenium ไม่สามารถหา ChromeDriver

**แก้ไข:**
```bash
# ติดตั้ง Chrome browser
# macOS
brew install --cask google-chrome

# Ubuntu
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb

# ตรวจสอบว่าติดตั้งสำเร็จ
google-chrome --version
```

### ปัญหา: MongoDB connection timeout

**แก้ไข:**
1. ตรวจสอบว่า MongoDB URL ถูกต้อง
2. ตรวจสอบว่าเครื่องเชื่อมต่อ Internet ได้
3. ตรวจสอบว่า IP ของคุณอยู่ใน MongoDB Atlas whitelist

### ปัญหา: Vector Search ไม่ทำงาน

**แก้ไข:**
1. ตรวจสอบว่า MongoDB Atlas cluster เป็น M10+ (ไม่ใช่ M0/M2/M5)
2. สร้าง Vector Search index ใน Atlas UI:
   - ไปที่ Atlas Console > Database > Search
   - สร้าง Search Index ใหม่:
   ```json
   {
     "fields": [
       {
         "type": "vector",
         "path": "contentVector",
         "numDimensions": 1024,
         "similarity": "cosine"
       }
     ]
   }
   ```
3. รอ 5-10 นาทีให้ index build เสร็จ

### ปัญหา: Out of Memory

**แก้ไข:**
1. ลด batch size ใน `embedder.py`:
   ```python
   embedder.embed_documents(batch_size=16)  # แทน 32
   ```
2. ปิดโปรแกรมอื่นที่ใช้ RAM มาก

### ปัญหา: Rate limiting จาก website

**แก้ไข:**
1. เพิ่มความล่าช้าใน `.env`:
   ```
   SCRAPER_MIN_DELAY=5
   SCRAPER_MAX_DELAY=10
   ```

## 📝 หมายเหตุ

### การใช้ OpenAI API

- ถ้าไม่ใส่ `OPENAI_API_KEY` ระบบจะทำงานได้ แต่จะแสดงข้อมูลจาก context โดยตรง
- สำหรับผลลัพธ์ที่ดีที่สุด ควรใช้ OpenAI API
- ค่าใช้จ่ายโดยประมาณ: ~$0.002 ต่อ query (gpt-3.5-turbo)

### การใช้ Local LLM

ถ้าต้องการใช้ local LLM แทน OpenAI:
1. ดาวน์โหลด model (เช่น Llama-2)
2. แก้ไข `app.py` ใน `_setup_llm()`:
   ```python
   from llama_cpp import Llama
   self.llm = Llama(model_path="path/to/model.gguf")
   ```

### ข้อควรระวัง

- ⚠️ ข้อมูลที่ได้จากระบบเป็นเพียงข้อมูลอ้างอิง ไม่ใช่คำแนะนำทางการแพทย์
- ⚠️ ควรปรึกษาแพทย์สำหรับการวินิจฉัยและรักษาที่ถูกต้อง
- ⚠️ Scraping ควรทำอย่างมีความรับผิดชอบ (ตาม robots.txt และ delay)

## 🔗 ทรัพยากรเพิ่มเติม

- [MongoDB Atlas Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [LlamaIndex](https://docs.llamaindex.ai/)

## 📄 License

This project is for educational purposes only.

## 👤 Author

Created for AGN Health Q&A RAG System

---

**Happy Coding! 🚀**
