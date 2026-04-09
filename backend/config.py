"""
Configuration and constants
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Keep Chroma quiet in local/offline development unless explicitly overridden.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
logging.getLogger("chromadb.telemetry.product.posthog").disabled = True

# Base paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "Housing1.csv"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

# GenAI runtime controls
GENAI_USE_LLM = os.getenv("GENAI_USE_LLM", "true").lower() == "true"
GENAI_PRIMARY_PROVIDER = os.getenv("GENAI_PRIMARY_PROVIDER", "ollama").lower()

# Ollama (primary by default)
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

# OpenAI (backup)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GENAI_MODEL = os.getenv("GENAI_MODEL", OPENAI_MODEL)

# Temperature controls
GENAI_TEMPERATURE = float(os.getenv("GENAI_TEMPERATURE", "0.35"))
GENAI_TEMPERATURE_DESCRIPTION = float(os.getenv("GENAI_TEMPERATURE_DESCRIPTION", "0.55"))
GENAI_TEMPERATURE_EXPLAIN = float(os.getenv("GENAI_TEMPERATURE_EXPLAIN", "0.25"))
GENAI_TEMPERATURE_CHAT = float(os.getenv("GENAI_TEMPERATURE_CHAT", "0.45"))
GENAI_TEMPERATURE_LANDMARK = float(os.getenv("GENAI_TEMPERATURE_LANDMARK", "0.30"))

# Token and response limits
GENAI_MAX_INPUT_TOKENS = int(os.getenv("GENAI_MAX_INPUT_TOKENS", "1800"))
GENAI_MAX_OUTPUT_TOKENS = int(os.getenv("GENAI_MAX_OUTPUT_TOKENS", "450"))
GENAI_MAX_RESPONSE_CHARS = int(os.getenv("GENAI_MAX_RESPONSE_CHARS", "3500"))

# RAG Configuration
RAG_PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", str(BASE_DIR / "backend" / "chroma_db_news_runtime"))
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_NEWS_CSV_PATH = BASE_DIR / "Datasets" / "market_news_sample.csv"

# Market news refresh schedule
NEWS_REFRESH_ENABLED = os.getenv("NEWS_REFRESH_ENABLED", "true").lower() == "true"
NEWS_REFRESH_INTERVAL_HOURS = int(os.getenv("NEWS_REFRESH_INTERVAL_HOURS", "6"))

# Social intelligence
SOCIAL_REDDIT_STORE_PATH = os.getenv(
    "SOCIAL_REDDIT_STORE_PATH",
    str(BASE_DIR / "Datasets" / "reddit_social_posts.json"),
)
SOCIAL_FAISS_DIR = os.getenv(
    "SOCIAL_FAISS_DIR",
    str(BASE_DIR / "backend" / "faiss_social"),
)
SOCIAL_EMBEDDING_MODEL = os.getenv("SOCIAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Models
ML_MODELS_DIR = "models"
PRICE_MODEL_PATH = os.path.join(ML_MODELS_DIR, "price_predictor.pkl")

# Real Estate Platforms
PLATFORMS = {
    'housing_com': 'https://housing.com/in',
    '99acres': 'https://www.99acres.com',
    'magicbricks': 'https://www.magicbricks.com',
    'nobroker': 'https://www.nobroker.in'
}

# Price thresholds (in INR)
PRICE_CATEGORIES = {
    'budget': (0, 5000000),  # Up to 50L
    'mid_range': (5000000, 20000000),  # 50L to 2Cr
    'premium': (20000000, 100000000),  # 2Cr to 10Cr
    'luxury': (100000000, float('inf'))  # 10Cr+
}

# Common Indian locations
MAJOR_CITIES = [
    'Mumbai', 'Bangalore', 'Delhi', 'Hyderabad', 'Pune',
    'Ahmedabad', 'Chennai', 'Kolkata', 'Jaipur', 'Surat'
]
