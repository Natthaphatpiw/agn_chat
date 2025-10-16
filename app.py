"""
FastAPI backend for AGN Health Q&A RAG system using LlamaIndex.
Provides chat endpoint for querying medical Q&A using vector search and LLM.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from llama_index.core import VectorStoreIndex, Settings, Document
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.mongodb import MongoDBAtlasVectorSearch
from llama_index.llms.openai import OpenAI as OpenAI
from llama_index.llms.llama_cpp import LlamaCPP
from pymongo import MongoClient
from huggingface_hub import hf_hub_download
import os

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
    description="Medical Q&A system using RAG with LlamaIndex and vector search",
    version="2.0.0"
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
    session_id: Optional[str] = Field(None, description="Session ID for conversation memory. If not provided, a new session will be created")


class SourceDocument(BaseModel):
    """Source document model."""
    thread_id: int
    topic: str
    question: str
    answer: str
    date: str
    score: Optional[float] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Generated response")
    sources: Optional[List[SourceDocument]] = Field(None, description="Source documents used")
    session_id: str = Field(..., description="Session ID for continuing the conversation")


class LlamaIndexRAGSystem:
    """RAG system using LlamaIndex for question answering with conversation memory.

    This system supports both OpenAI and Llama-2 models, and includes conversation memory
    to maintain context across multiple queries within the same session.
    """

    def __init__(self):
        """Initialize RAG system with LlamaIndex components."""
        self.mongo_client = None
        self.vector_store = None
        self.index = None
        self.query_engine = None
        self.embed_model = None
        self.llm = None
        self.chat_engines = {}  # เก็บ chat engines แยกตาม session
        self.session_cleanup_time = {}  # เก็บเวลาที่ใช้ล่าสุดของแต่ละ session

        self._setup_mongodb()
        self._setup_embeddings()
        self._setup_llm()
        self._setup_vector_store()
        # Note: Chat engines are created per session, not globally

    def _setup_mongodb(self):
        """Set up MongoDB connection."""
        try:
            self.mongo_client = MongoClient(config.MONGODB_URL)
            # Test connection
            self.mongo_client.admin.command('ping')
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _setup_embeddings(self):
        """Set up embedding model using LlamaIndex."""
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.embed_model = HuggingFaceEmbedding(
                model_name=config.EMBEDDING_MODEL,
                embed_batch_size=32
            )

            # Set as global default
            Settings.embed_model = self.embed_model
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _setup_llm(self):
        """Set up the LLM using LlamaIndex."""
        try:
            if config.OPENAI_API_KEY:
                logger.info(f"Using OpenAI for LLM via LlamaIndex (model: {config.OPENAI_MODEL})")
                self.llm = OpenAI(
                    model="gpt-4o-mini",
                    api_key=config.OPENAI_API_KEY,
                    temperature=0.7
                )
                Settings.llm = self.llm
                self.llm_type = "openai"
            else:
                logger.info("No OpenAI API key found. Loading local Llama-2 model...")
                self.llm = self._setup_local_llm()
                if self.llm:
                    Settings.llm = self.llm
                    self.llm_type = "llama2"
                else:
                    self.llm_type = "fallback"

            logger.info(f"LLM setup completed: {self.llm_type}")
        except Exception as e:
            logger.error(f"Failed to setup LLM: {e}")
            self.llm = None
            self.llm_type = "fallback"

    def _setup_local_llm(self):
        """Set up local Llama-2 model using llama-cpp."""
        try:
            # Download model from HuggingFace
            logger.info(f"Downloading {config.LOCAL_LLM_MODEL}/{config.LOCAL_LLM_FILE}...")
            model_path = hf_hub_download(
                repo_id=config.LOCAL_LLM_MODEL,
                filename=config.LOCAL_LLM_FILE,
                cache_dir="./models"
            )
            logger.info(f"Model downloaded to: {model_path}")

            # Initialize LlamaCPP
            llm = LlamaCPP(
                model_path=model_path,
                temperature=0.7,
                max_new_tokens=config.LOCAL_LLM_MAX_TOKENS,
                context_window=config.LOCAL_LLM_CONTEXT,
                generate_kwargs={},
                model_kwargs={"n_gpu_layers": 0},  # Use CPU (set to -1 for GPU)
                verbose=False
            )

            logger.info("Local Llama-2 model loaded successfully")
            return llm

        except Exception as e:
            logger.error(f"Failed to load local LLM: {e}")
            logger.warning("Falling back to response without LLM generation")
            return None

    def _setup_vector_store(self):
        """Set up MongoDB Atlas Vector Store with LlamaIndex."""
        try:
            logger.info("Setting up MongoDB Atlas Vector Store")

            self.vector_store = MongoDBAtlasVectorSearch(
                mongodb_client=self.mongo_client,
                db_name=config.MONGODB_DATABASE,
                collection_name=config.MONGODB_COLLECTION,
                vector_index_name=config.VECTOR_INDEX_NAME,
                embedding_key="contentVector",
                text_key="question",  # Use existing field instead of combined_text
                metadata_key="metadata"
            )

            # Create index from vector store
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                embed_model=self.embed_model
            )

            logger.info("Vector store and index initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup vector store: {e}")
            raise

    def _create_chat_engine(self, session_id: str):
        """Create a new chat engine for the given session."""
        try:
            if self.llm_type in ["openai", "llama2"] and self.llm:
                # Create retriever for context retrieval
                retriever = VectorIndexRetriever(
                    index=self.index,
                    similarity_top_k=10,  # Retrieve more for post-processing
                )

                # Create memory for this session
                memory = ChatMemoryBuffer.from_defaults(llm=self.llm, token_limit=2000)

                # Create CondensePlusContextChatEngine with memory
                chat_engine = CondensePlusContextChatEngine.from_defaults(
                    retriever=retriever,
                    memory=memory,
                    node_postprocessors=[
                        SimilarityPostprocessor(similarity_cutoff=0.5)
                    ],
                    verbose=True
                )

                self.chat_engines[session_id] = chat_engine
                self.session_cleanup_time[session_id] = datetime.now()

                logger.info(f"Chat engine created for session {session_id}")
                return chat_engine
            else:
                logger.warning("Cannot create chat engine: LLM not available")
                return None
        except Exception as e:
            logger.error(f"Failed to create chat engine: {e}")
            return None

    def normalize_query(self, query: str) -> str:
        """Normalize user query using LLM if available."""
        # Skip normalization for Llama-2 (not good with Thai)
        # Only use for OpenAI
        if self.llm_type == "openai" and self.llm:
            try:
                from llama_index.core.llms import ChatMessage

                system_prompt = """คุณเป็นผู้ช่วยที่ช่วยปรับแก้คำถามให้ชัดเจนและเหมาะสมสำหรับการค้นหาข้อมูลทางการแพทย์
ให้คุณปรับแก้คำถามให้สมบูรณ์ ชัดเจน และแก้ไขคำผิดหากมี แต่คงความหมายเดิม ตอบเป็นภาษาไทย"""

                messages = [
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(role="user", content=f"ปรับแก้คำถามนี้ให้ชัดเจนและเหมาะสมสำหรับการค้นหา: {query}")
                ]

                response = self.llm.chat(messages)
                normalized = response.message.content.strip()
                logger.info(f"Query normalized: '{query}' -> '{normalized}'")
                return normalized

            except Exception as e:
                logger.error(f"Error normalizing query: {e}")
                return query
        else:
            # Return original query for Llama-2 or fallback
            return query

    def retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant documents using direct MongoDB vector search."""
        try:
            # Use direct MongoDB Atlas Vector Search instead of LlamaIndex retriever
            # to avoid metadata issues

            # Get query embedding
            query_embedding = self.embed_model.get_query_embedding(query)

            # MongoDB Atlas Vector Search pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": config.VECTOR_INDEX_NAME,
                        "path": "contentVector",
                        "queryVector": query_embedding,
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

            collection = self.mongo_client[config.MONGODB_DATABASE][config.MONGODB_COLLECTION]
            results = list(collection.aggregate(pipeline))

            logger.info(f"Retrieved {len(results)} documents")
            return results

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return self._fallback_retrieve(top_k)

    def _fallback_retrieve(self, top_k: int = 5) -> List[Dict]:
        """Fallback retrieval method using direct MongoDB query."""
        try:
            db = self.mongo_client[config.MONGODB_DATABASE]
            collection = db[config.MONGODB_COLLECTION]

            results = list(
                collection.find(
                    {"question": {"$exists": True, "$ne": ""}},
                    {"_id": 0, "thread_id": 1, "topic": 1, "question": 1, "answer": 1, "date": 1}
                ).limit(top_k)
            )
            return results
        except Exception as e:
            logger.error(f"Error in fallback retrieval: {e}")
            return []

    def generate_response(self, query: str, contexts: List[Dict]) -> str:
        """Generate response using LlamaIndex query engine or fallback."""
        if not contexts:
            return "ขออภัย ไม่พบข้อมูลที่เกี่ยวข้องกับคำถามของคุณ กรุณาลองถามคำถามอื่นหรือติดต่อแพทย์โดยตรง"

        if self.llm_type in ["openai", "llama2"] and self.llm:
            try:
                # Format contexts for LLM
                context_text = self._format_contexts(contexts)

                if self.llm_type == "openai":
                    # OpenAI chat format using LlamaIndex ChatMessage
                    from llama_index.core.llms import ChatMessage

                    system_prompt = """คุณเป็นผู้ช่วยทางการแพทย์ที่ให้คำตอบจากข้อมูล Q&A ที่มีอยู่
ให้คุณตอบคำถามโดยอิงจากบริบทที่ให้มาเท่านั้น ตอบเป็นภาษาไทยที่เป็นธรรมชาติและเข้าใจง่าย
หากข้อมูลไม่เพียงพอ ให้แนะนำให้ปรึกษาแพทย์"""

                    user_prompt = f"""บริบทจาก Q&A:
{context_text}

คำถาม: {query}

กรุณาตอบคำถามโดยอิงจากบริบทข้างต้น:"""

                    messages = [
                        ChatMessage(role="system", content=system_prompt),
                        ChatMessage(role="user", content=user_prompt)
                    ]

                    response = self.llm.chat(messages)
                    answer = response.message.content.strip()
                else:
                    # Llama-2 complete format (without leading <s> to avoid duplicate warning)
                    prompt = f"""[INST] <<SYS>>
คุณเป็นผู้ช่วยทางการแพทย์ที่ให้คำตอบจากข้อมูล Q&A ที่มีอยู่
ให้คุณตอบคำถามโดยอิงจากบริบทที่ให้มาเท่านั้น ตอบเป็นภาษาไทยที่เป็นธรรมชาติและเข้าใจง่าย
หากข้อมูลไม่เพียงพอ ให้แนะนำให้ปรึกษาแพทย์
<</SYS>>

บริบทจาก Q&A:
{context_text}

คำถาม: {query}

กรุณาตอบคำถามโดยอิงจากบริบทข้างต้น: [/INST]"""

                    response = self.llm.complete(prompt)
                    answer = response.text.strip()

                return answer

            except Exception as e:
                logger.error(f"Error generating response with LlamaIndex: {e}")
                return self._fallback_response(query, contexts)
        else:
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

        for i, ctx in enumerate(contexts[:3], 1):
            topic = ctx.get('topic', '')
            question = ctx.get('question', '')
            answer = ctx.get('answer', '')

            response_parts.append(f"\n{i}. {topic if topic else question}")
            if answer:
                answer_preview = answer[:300] + "..." if len(answer) > 300 else answer
                response_parts.append(f"   {answer_preview}")

        response_parts.append("\n\nหมายเหตุ: นี่คือข้อมูลจากฐานข้อมูล Q&A สำหรับคำตอบที่ละเอียดกว่านี้ ควรปรึกษาแพทย์โดยตรง")

        return "\n".join(response_parts)

    def process_query(self, query: str, session_id: str, top_k: int = 5) -> tuple[str, List[Dict]]:
        """
        Process a user query through the RAG pipeline using LlamaIndex chat engine.

        Args:
            query: User's question
            session_id: Session ID for conversation memory
            top_k: Number of documents to retrieve

        Returns:
            Tuple of (response, source_documents)
        """
        try:
            # Get or create chat engine for this session
            chat_engine = self.chat_engines.get(session_id)
            if not chat_engine:
                chat_engine = self._create_chat_engine(session_id)
                if not chat_engine:
                    # Fallback to old method if chat engine creation fails
                    return self._fallback_process_query(query, top_k)

            # Update session timestamp
            self.session_cleanup_time[session_id] = datetime.now()

            # Step 1: Normalize query (optional, using LLM)
            normalized_query = self.normalize_query(query)

            # Step 2: Use chat engine to process query with context and memory
            response_obj = chat_engine.chat(normalized_query)

            # Extract response text
            response = str(response_obj)

            # Step 3: Retrieve source documents (for backward compatibility with frontend)
            # Note: Chat engine handles context retrieval internally
            contexts = self.retrieve_documents(normalized_query, top_k)

            return response, contexts

        except Exception as e:
            logger.error(f"Error processing query with chat engine: {e}")
            # Fallback to old method
            return self._fallback_process_query(query, top_k)

    def _fallback_process_query(self, query: str, top_k: int = 5) -> tuple[str, List[Dict]]:
        """Fallback processing method when chat engine is not available."""
        try:
            # Step 1: Normalize query (optional, using LLM)
            normalized_query = self.normalize_query(query)

            # Step 2: Retrieve relevant documents
            contexts = self.retrieve_documents(normalized_query, top_k)

            # Step 3: Generate response
            response = self.generate_response(normalized_query, contexts)

            return response, contexts

        except Exception as e:
            logger.error(f"Error in fallback processing: {e}")
            raise

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up sessions that haven't been used for more than max_age_hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            sessions_to_remove = []

            for session_id, last_used in self.session_cleanup_time.items():
                if last_used < cutoff_time:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                if session_id in self.chat_engines:
                    del self.chat_engines[session_id]
                if session_id in self.session_cleanup_time:
                    del self.session_cleanup_time[session_id]
                logger.info(f"Cleaned up session: {session_id}")

            if sessions_to_remove:
                logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")


# Initialize RAG system
rag_system = None


@app.on_event("startup")
async def startup_event():
    """Initialize RAG system on startup."""
    global rag_system
    try:
        logger.info("Initializing LlamaIndex RAG system...")
        rag_system = LlamaIndexRAGSystem()
        logger.info("LlamaIndex RAG system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global rag_system
    if rag_system:
        # Clean up old sessions
        rag_system.cleanup_old_sessions()
        # Close MongoDB connection
        if rag_system.mongo_client:
            rag_system.mongo_client.close()
            logger.info("MongoDB connection closed")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AGN Health Q&A RAG API with LlamaIndex and Conversation Memory",
        "version": "2.0.0",
        "framework": "LlamaIndex",
        "features": ["RAG", "Conversation Memory", "OpenAI/Llama-2 Support"],
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "framework": "LlamaIndex", "memory_enabled": True}


@app.post("/session/new")
async def create_new_session():
    """Create a new chat session."""
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")

        session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {session_id}")

        return {"session_id": session_id, "message": "New session created"}

    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session and its memory."""
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")

        if session_id in rag_system.chat_engines:
            del rag_system.chat_engines[session_id]
            del rag_system.session_cleanup_time[session_id]
            logger.info(f"Cleared session: {session_id}")
            return {"message": f"Session {session_id} cleared"}
        else:
            return {"message": f"Session {session_id} not found"}

    except Exception as e:
        logger.error(f"Error clearing session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for querying medical Q&A using LlamaIndex RAG with conversation memory.

    This endpoint supports conversation memory - if you provide a session_id from a previous
    request, the system will remember the conversation history and provide more contextually
    relevant answers. If no session_id is provided, a new session will be created.

    Args:
        request: ChatRequest with query, optional session_id, and optional top_k

    Returns:
        ChatResponse with generated answer, sources, and session_id for continuation
    """
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not initialized")

        # Handle session management
        if not request.session_id:
            # Create new session if not provided
            session_id = str(uuid.uuid4())
            logger.info(f"Created new session: {session_id}")
        else:
            session_id = request.session_id
            logger.info(f"Using existing session: {session_id}")

        logger.info(f"Received query: {request.query}")

        # Process query through LlamaIndex RAG pipeline with session
        response, sources = rag_system.process_query(request.query, session_id, request.top_k)

        logger.info(f"Generated response for query: {request.query} in session: {session_id}")

        # Convert sources to SourceDocument models
        source_docs = [
            SourceDocument(
                thread_id=src.get('thread_id', 0),
                topic=src.get('topic', ''),
                question=src.get('question', ''),
                answer=src.get('answer', ''),
                date=src.get('date', ''),
                score=src.get('score')
            )
            for src in sources
        ]

        return ChatResponse(
            response=response,
            sources=source_docs,
            session_id=session_id
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
