"""
Configuration and constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "Housing1.csv"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

# GenAI runtime controls
GENAI_USE_LLM = os.getenv("GENAI_USE_LLM", "false").lower() == "true"
GENAI_MODEL = os.getenv("GENAI_MODEL", "gpt-4o-mini")

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
RAG_PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", str(BASE_DIR / "backend" / "chroma_db_news"))
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_NEWS_CSV_PATH = BASE_DIR / "Datasets" / "market_news_sample.csv"

# Market news refresh schedule
NEWS_REFRESH_ENABLED = os.getenv("NEWS_REFRESH_ENABLED", "true").lower() == "true"
NEWS_REFRESH_INTERVAL_HOURS = int(os.getenv("NEWS_REFRESH_INTERVAL_HOURS", "6"))

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
