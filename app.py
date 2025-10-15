"""
FastAPI backend for AGN Health Q&A RAG system.
Provides chat endpoint for querying medical Q&A using vector search and LLM.
"""
import logging
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AGN Health Q&A RAG API",
    description="Medical Q&A system using RAG with vector search",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., description="User's question", min_length=1)
    top_k: Optional[int] = Field(5, description="Number of similar documents to retrieve", ge=1, le=20)


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Generated response")
    sources: Optional[List[Dict]] = Field(None, description="Source documents used")


class RAGSystem:
    """RAG system for question answering."""

    def __init__(self):
        """Initialize RAG system with MongoDB, embeddings, and LLM."""
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.embedding_model = None
        self.llm = None
        self._setup_mongodb()
        self._setup_embedding_model()
        self._setup_llm()

    def _setup_mongodb(self):
        """Set up MongoDB connection."""
        try:
            self.mongo_client = MongoClient(config.MONGODB_URL)
            self.db = self.mongo_client[config.MONGODB_DATABASE]
            self.collection = self.db[config.MONGODB_COLLECTION]
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _setup_embedding_model(self):
        """Load the embedding model."""
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _setup_llm(self):
        """Set up the LLM for response generation."""
        try:
            if config.OPENAI_API_KEY:
                # Use OpenAI
                logger.info("Using OpenAI for LLM")
                from openai import OpenAI
                self.llm = OpenAI(api_key=config.OPENAI_API_KEY)
                self.llm_type = "openai"
            else:
                # Use local model (placeholder - in production, load actual model)
                logger.warning("No OpenAI API key found. Using fallback response generation.")
                logger.warning("For better results, set OPENAI_API_KEY in .env file")
                self.llm = None
                self.llm_type = "fallback"

            logger.info(f"LLM setup completed: {self.llm_type}")
        except Exception as e:
            logger.error(f"Failed to setup LLM: {e}")
            self.llm = None
            self.llm_type = "fallback"

    def normalize_query(self, query: str) -> str:
        """
        Normalize user query using LLM.

        Args:
            query: Raw user query

        Returns:
            Normalized query
        """
        if self.llm_type == "openai" and self.llm:
            try:
                system_prompt = """คุณเป็นผู้ช่วยที่ช่วยปรับแก้คำถามให้ชัดเจนและเหมาะสมสำหรับการค้นหาข้อมูลทางการแพทย์
ให้คุณปรับแก้คำถามให้สมบูรณ์ ชัดเจน และแก้ไขคำผิดหากมี แต่คงความหมายเดิม ตอบเป็นภาษาไทย"""

                user_prompt = f"ปรับแก้คำถามนี้ให้ชัดเจนและเหมาะสมสำหรับการค้นหา: {query}"

                response = self.llm.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )

                normalized = response.choices[0].message.content.strip()
                logger.info(f"Query normalized: '{query}' -> '{normalized}'")
                return normalized

            except Exception as e:
                logger.error(f"Error normalizing query: {e}")
                return query
        else:
            # Fallback: return original query
            return query

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for the query.

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        try:
            embedding = self.embedding_model.encode(
                query,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise

    def vector_search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        """
        Perform vector search using MongoDB Atlas Vector Search.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of similar documents
        """
        try:
            # MongoDB Atlas Vector Search aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": config.VECTOR_INDEX_NAME,
                        "path": "contentVector",
                        "queryVector": query_vector,
                        "numCandidates": top_k * 10,
                        "limit": top_k
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "thread_id": 1,
                        "topic": 1,
                        "question": 1,
                        "answer": 1,
                        "date": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(self.collection.aggregate(pipeline))
            logger.info(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            logger.warning("Falling back to text search")
            return self._fallback_search(top_k)

    def _fallback_search(self, top_k: int = 5) -> List[Dict]:
        """
        Fallback search when vector search is not available.

        Args:
            top_k: Number of results to return

        Returns:
            List of documents
        """
        try:
            results = list(
                self.collection.find(
                    {"question": {"$exists": True, "$ne": ""}},
                    {"_id": 0, "thread_id": 1, "topic": 1, "question": 1, "answer": 1, "date": 1}
                ).limit(top_k)
            )
            return results
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []

    def generate_response(self, query: str, contexts: List[Dict]) -> str:
        """
        Generate response using LLM and retrieved contexts.

        Args:
            query: User's query
            contexts: List of retrieved documents

        Returns:
            Generated response
        """
        if not contexts:
            return "ขออภัย ไม่พบข้อมูลที่เกี่ยวข้องกับคำถามของคุณ กรุณาลองถามคำถามอื่นหรือติดต่อแพทย์โดยตรง"

        # Format contexts
        context_text = self._format_contexts(contexts)

        if self.llm_type == "openai" and self.llm:
            try:
                system_prompt = """คุณเป็นผู้ช่วยทางการแพทย์ที่ให้คำตอบจากข้อมูล Q&A ที่มีอยู่
ให้คุณตอบคำถามโดยอิงจากบริบทที่ให้มาเท่านั้น ตอบเป็นภาษาไทยที่เป็นธรรมชาติและเข้าใจง่าย
หากข้อมูลไม่เพียงพอ ให้แนะนำให้ปรึกษาแพทย์"""

                user_prompt = f"""บริบทจาก Q&A:
{context_text}

คำถาม: {query}

กรุณาตอบคำถามโดยอิงจากบริบทข้างต้น:"""

                response = self.llm.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )

                answer = response.choices[0].message.content.strip()
                return answer

            except Exception as e:
                logger.error(f"Error generating response with OpenAI: {e}")
                return self._fallback_response(query, contexts)
        else:
            # Fallback: return formatted contexts
            return self._fallback_response(query, contexts)

    def _format_contexts(self, contexts: List[Dict]) -> str:
        """Format retrieved contexts for LLM prompt."""
        formatted = []
        for i, ctx in enumerate(contexts, 1):
            topic = ctx.get('topic', '')
            question = ctx.get('question', '')
            answer = ctx.get('answer', '')

            ctx_text = f"\n--- Q&A {i} ---"
            if topic:
                ctx_text += f"\nหัวข้อ: {topic}"
            if question:
                ctx_text += f"\nคำถาม: {question}"
            if answer:
                ctx_text += f"\nคำตอบ: {answer}"

            formatted.append(ctx_text)

        return "\n".join(formatted)

    def _fallback_response(self, query: str, contexts: List[Dict]) -> str:
        """Generate fallback response when LLM is not available."""
        response_parts = [f"จากข้อมูลที่เกี่ยวข้องกับคำถาม: {query}\n"]

        for i, ctx in enumerate(contexts[:3], 1):  # Show top 3
            topic = ctx.get('topic', '')
            question = ctx.get('question', '')
            answer = ctx.get('answer', '')

            response_parts.append(f"\n{i}. {topic if topic else question}")
            if answer:
                # Truncate long answers
                answer_preview = answer[:300] + "..." if len(answer) > 300 else answer
                response_parts.append(f"   {answer_preview}")

        response_parts.append("\n\nหมายเหตุ: นี่คือข้อมูลจากฐานข้อมูล Q&A สำหรับคำตอบที่ละเอียดกว่านี้ ควรปรึกษาแพทย์โดยตรง")

        return "\n".join(response_parts)

    def process_query(self, query: str, top_k: int = 5) -> tuple[str, List[Dict]]:
        """
        Process a user query through the RAG pipeline.

        Args:
            query: User's question
            top_k: Number of documents to retrieve

        Returns:
            Tuple of (response, source_documents)
        """
        try:
            # Step 1: Normalize query
            normalized_query = self.normalize_query(query)

            # Step 2: Embed query
            query_vector = self.embed_query(normalized_query)

            # Step 3: Vector search
            contexts = self.vector_search(query_vector, top_k)

            # Step 4: Generate response
            response = self.generate_response(normalized_query, contexts)

            return response, contexts

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise


# Initialize RAG system
rag_system = None


@app.on_event("startup")
async def startup_event():
    """Initialize RAG system on startup."""
    global rag_system
    try:
        logger.info("Initializing RAG system...")
        rag_system = RAGSystem()
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global rag_system
    if rag_system and rag_system.mongo_client:
        rag_system.mongo_client.close()
        logger.info("MongoDB connection closed")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AGN Health Q&A RAG API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for querying medical Q&A.

    Args:
        request: ChatRequest with query and optional top_k

    Returns:
        ChatResponse with generated answer and sources
    """
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")

        logger.info(f"Received query: {request.query}")

        # Process query
        response, sources = rag_system.process_query(request.query, request.top_k)

        logger.info(f"Generated response for query: {request.query}")

        return ChatResponse(
            response=response,
            sources=sources
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level="info"
    )
