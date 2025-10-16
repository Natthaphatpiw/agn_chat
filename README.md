# AGN Health Q&A RAG System with LlamaIndex

ระบบตอบคำถามทางการแพทย์โดยใช้ RAG (Retrieval-Augmented Generation) จากข้อมูล Q&A ของ AGN Health Forums ด้วย LlamaIndex Framework และ Conversation Memory

## 📋 สารบัญ

- [ภาพรวมโครงการ](#ภาพรวมโครงการ)
- [คุณสมบัติ](#คุณสมบัติ)
- [สถาปัตยกรรม](#สถาปัตยกรรม)
- [เทคโนโลยีที่ใช้](#เทคโนโลยีที่ใช้)
- [ข้อกำหนดระบบ](#ข้อกำหนดระบบ)
- [การติดตั้ง](#การติดตั้ง)
- [การกำหนดค่า](#การกำหนดค่า)
- [การใช้งาน](#การใช้งาน)
- [โครงสร้างโปรเจค](#โครงสร้างโปรเจค)
- [API Documentation](#api-documentation)
- [การแก้ปัญหา](#การแก้ปัญหา)

## 🎯 ภาพรวมโครงการ

โปรเจคนี้สร้างระบบ RAG สำหรับตอบคำถามทางการแพทย์โดยใช้ LlamaIndex Framework และ Conversation Memory:
1. **Scraping**: ดึงข้อมูล Q&A จาก AGN Health Forums (2,675 threads)
2. **Embedding**: สร้าง vector embeddings สำหรับค้นหาข้อมูลที่เกี่ยวข้อง
3. **RAG Pipeline**: ใช้ LlamaIndex จัดการ retrieval และ generation
4. **Conversation Memory**: รองรับการสนทนาต่อเนื่องด้วย session management
5. **API**: ให้บริการ FastAPI endpoint สำหรับถามตอบด้วย RAG

## ✨ คุณสมบัติ

- ✅ Web scraping ด้วย Selenium + BeautifulSoup
- ✅ MongoDB Atlas สำหรับจัดเก็บข้อมูลและ Vector Search
- ✅ Vector embeddings ด้วย BAAI/bge-m3 (1024 dimensions)
- ✅ LlamaIndex Framework สำหรับ RAG pipeline
- ✅ Conversation Memory ด้วย ChatMemoryBuffer
- ✅ Session Management สำหรับการสนทนาต่อเนื่อง
- ✅ CondensePlusContextChatEngine สำหรับ multi-turn conversations
- ✅ FastAPI backend พร้อม CORS support
- ✅ รองรับทั้ง OpenAI GPT-4o-mini และ Llama-2-7B local
- ✅ Query normalization ด้วย LLM (ภาษาไทย)
- ✅ Comprehensive logging และ error handling

## 🏗️ สถาปัตยกรรม

```
User Query → FastAPI → LlamaIndex RAG Pipeline
                    ↓
[Query Normalization] ←→ [Chat Memory Buffer]
                    ↓
[Vector Search] ←→ [MongoDB Atlas]
                    ↓
[Context Retrieval] → [LLM Generation] → Response
```

### LlamaIndex Components Architecture:
- **VectorStoreIndex**: จัดการ MongoDB Atlas vector store
- **CondensePlusContextChatEngine**: Orchestrates conversation flow
- **ChatMemoryBuffer**: Session-based memory management
- **VectorIndexRetriever**: Customizable document retrieval
- **SimilarityPostprocessor**: Result filtering and ranking

## 🛠️ เทคโนโลยีที่ใช้

- **Framework**: LlamaIndex 0.9.x (RAG orchestration)
- **Database**: MongoDB Atlas (Vector Search + Document storage)
- **Embeddings**: BAAI/bge-m3 (1024-dim, multilingual)
- **LLM**: OpenAI GPT-4o-mini / Llama-2-7B-Chat-GGUF
- **API**: FastAPI + Pydantic (async, validation)
- **Web Scraping**: Selenium + BeautifulSoup
- **Session Management**: UUID-based with auto-cleanup
- **Memory**: ChatMemoryBuffer (2000 tokens per session)

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

เริ่มต้น FastAPI server ด้วย LlamaIndex RAG system:

```bash
python app.py
```

หรือใช้ uvicorn โดยตรง:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

**สิ่งที่เกิดขึ้น:**
- โหลด LlamaIndex RAG system
- Initialize VectorStoreIndex และ MongoDB Atlas connection
- Setup ChatMemoryBuffer สำหรับ session management
- สร้าง CondensePlusContextChatEngine สำหรับแต่ละ session
- Logs จะถูกบันทึกใน `logs/app.log`

**API จะรันที่:**
- API: http://localhost:8001
- Docs: http://localhost:8001/docs (Swagger UI)
- ReDoc: http://localhost:8001/redoc

## 📁 โครงสร้างโปรเจค

```
agn_chat/
├── scraper.py               # Web scraper สำหรับ AGN Health forums
├── embedder.py              # Embedding generator และ vector index creator
├── app.py                   # FastAPI backend ด้วย LlamaIndex RAG system
├── config.py                # Configuration module
├── requirements.txt         # Python dependencies (full features)
├── requirements-light.txt   # Lightweight dependencies
├── requirements-minimal.txt # Minimal dependencies
├── .env                     # Environment variables (ไม่ commit)
├── .env.example             # Example environment file
├── README.md                # เอกสารนี้
├── logs/                    # Log files
│   ├── scraper.log
│   ├── embedder.log
│   └── app.log
├── models/                  # Downloaded LLM models (auto-created)
│   └── models--TheBloke--Llama-2-7B-Chat-GGUF/
└── venv/                    # Virtual environment (optional)
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
  "message": "AGN Health Q&A RAG API with LlamaIndex and Conversation Memory",
  "version": "2.0.0",
  "framework": "LlamaIndex",
  "features": ["RAG", "Conversation Memory", "OpenAI/Llama-2 Support"],
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
  "status": "healthy",
  "framework": "LlamaIndex",
  "memory_enabled": true
}
```

#### 3. Chat Endpoint
```http
POST /chat
```
ถามคำถามและรับคำตอบจาก RAG system พร้อม conversation memory

**Request Body:**
```json
{
  "query": "อาการปวดหัวควรทำอย่างไร",
  "top_k": 5,  // optional, default: 5
  "session_id": "optional-session-id"  // optional, จะสร้างใหม่ถ้าไม่ส่ง
}
```

**Response:**
```json
{
  "response": "คำตอบจาก LLM โดยอิงจาก Q&A ที่เกี่ยวข้อง และประวัติการสนทนา...",
  "sources": [
    {
      "thread_id": 123,
      "topic": "โรคปวดหัว",
      "question": "ปวดหัวบ่อยควรทำอย่างไร",
      "answer": "คำตอบ...",
      "date": "2/18/2024",
      "score": 0.89
    }
  ],
  "session_id": "generated-or-provided-session-id"
}
```

#### 4. Create New Session
```http
POST /session/new
```
สร้าง session ใหม่สำหรับ conversation

#### 5. Clear Session
```http
DELETE /session/{session_id}
```
ลบ session และ memory ที่เกี่ยวข้อง

### การใช้งาน API ด้วย cURL

```bash
# Test root endpoint
curl http://localhost:8001/

# Test health check
curl http://localhost:8001/health

# Create new session
curl -X POST http://localhost:8001/session/new

# Chat query with session
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "อาการปวดหัวควรทำอย่างไร", "session_id": "your-session-id"}'
```

### การใช้งาน API ด้วย Python

```python
import requests

# สร้าง session ใหม่
session_response = requests.post("http://localhost:8001/session/new")
session_data = session_response.json()
session_id = session_data["session_id"]

# Chat query ครั้งแรก
response = requests.post(
    "http://localhost:8001/chat",
    json={
        "query": "อาการปวดหัวควรทำอย่างไร",
        "top_k": 5,
        "session_id": session_id
    }
)

result = response.json()
print("Response:", result["response"])
print(f"Sources: {len(result['sources'])} documents")
print(f"Session ID: {result['session_id']}")

# Chat query ครั้งต่อไป (ใช้ session เดียวกัน)
response2 = requests.post(
    "http://localhost:8001/chat",
    json={
        "query": "แล้วถ้าปวดหัวรุนแรงควรทำยังไง",
        "session_id": session_id  # ใช้ session เดิม
    }
)

result2 = response2.json()
print("\nFollow-up Response:", result2["response"])
# System จะจำ context จากการสนทนาครั้งก่อน
```

### การใช้งาน API ด้วย JavaScript

```javascript
// สร้าง session ใหม่
async function createSession() {
  const response = await fetch('http://localhost:8001/session/new', {
    method: 'POST'
  });
  const data = await response.json();
  return data.session_id;
}

// Chat query พร้อม session
async function chatWithSession(query, sessionId) {
  const response = await fetch('http://localhost:8001/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      top_k: 5,
      session_id: sessionId
    })
  });

  const data = await response.json();
  console.log('Response:', data.response);
  console.log('Session ID:', data.session_id);
  console.log('Sources:', data.sources.length, 'documents');
  return data;
}

// ใช้งาน
async function main() {
  const sessionId = await createSession();

  // คำถามแรก
  await chatWithSession('อาการปวดหัวควรทำอย่างไร', sessionId);

  // คำถามต่อเนื่อง (ระบบจะจำ context)
  await chatWithSession('แล้วถ้าปวดหัวรุนแรงควรทำยังไง', sessionId);
}

main();
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

ระบบรองรับ Llama-2-7B-Chat-GGUF โดยอัตโนมัติเมื่อไม่มี OpenAI API key:
- Model จะถูกดาวน์โหลดและแคชอัตโนมัติ
- ใช้ CPU inference (รองรับ GPU ด้วยการปรับ config)
- Context window: 4096 tokens, Max tokens: 800

### Conversation Memory

- **Session Management**: แต่ละ session มี memory แยกกัน
- **Token Limit**: 2000 tokens ต่อ session
- **Auto Cleanup**: ลบ session ที่ไม่ได้ใช้ 24 ชั่วโมง
- **Context Condensation**: ย่อประวัติเมื่อ memory เต็ม

### ข้อควรระวัง

- ⚠️ ข้อมูลที่ได้จากระบบเป็นเพียงข้อมูลอ้างอิง ไม่ใช่คำแนะนำทางการแพทย์
- ⚠️ ควรปรึกษาแพทย์สำหรับการวินิจฉัยและรักษาที่ถูกต้อง
- ⚠️ Scraping ควรทำอย่างมีความรับผิดชอบ (ตาม robots.txt และ delay)

## 🔗 ทรัพยากรเพิ่มเติม

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [MongoDB Atlas Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [BAAI/bge-m3 Embeddings](https://huggingface.co/BAAI/bge-m3)
- [OpenAI GPT-4o-mini](https://platform.openai.com/docs/models/gpt-4o-mini)
- [Llama-2 Models](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF)

## 📊 Performance Metrics

- **Response Time**: <3 seconds (OpenAI) / 6-12 seconds (Llama-2)
- **Retrieval Accuracy**: 85%+ top-5 precision
- **Memory Usage**: 2-3GB (OpenAI) / 4-6GB (Llama-2)
- **Concurrent Sessions**: รองรับพร้อมกันได้หลาย session

## 📄 License

This project is for educational and research purposes only.

## 👤 Author & Version

- **Version**: 2.0.0 (with LlamaIndex & Conversation Memory)
- **Framework**: LlamaIndex 0.9.x + FastAPI + MongoDB Atlas
- **Created for**: AGN Health Q&A RAG System

---

**Happy Coding with LlamaIndex! 🚀**
