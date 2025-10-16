"""
Configuration module for the AGN Health Q&A RAG system.
Loads environment variables and provides shared configuration.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://natthapiw_db_user:afOJe2MrgMDsmm6k@cluster0.skadipr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "agn")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "qa")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")  # Default to gpt-4o-mini (fast & cheap)

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

# Vector Index Configuration
VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "vector_index")

# Scraper Configuration
SCRAPER_START_ID = int(os.getenv("SCRAPER_START_ID", "1"))
SCRAPER_END_ID = int(os.getenv("SCRAPER_END_ID", "2675"))
SCRAPER_MIN_DELAY = int(os.getenv("SCRAPER_MIN_DELAY", "2"))
SCRAPER_MAX_DELAY = int(os.getenv("SCRAPER_MAX_DELAY", "5"))

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))

# Local LLM Configuration
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "TheBloke/Llama-2-7B-Chat-GGUF")
LOCAL_LLM_FILE = os.getenv("LOCAL_LLM_FILE", "llama-2-7b-chat.Q4_K_M.gguf")
LOCAL_LLM_CONTEXT = int(os.getenv("LOCAL_LLM_CONTEXT", "4096"))
LOCAL_LLM_MAX_TOKENS = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "800"))

# Base URL for scraping
BASE_URL = "https://www.agnoshealth.com/forums"
