from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from difflib import SequenceMatcher
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import logging
import base64
import asyncio
import re
import subprocess
import sys
import time
import tempfile
from pathlib import Path
from threading import Thread
from dotenv import load_dotenv
import openai
import requests
import config

# Import our custom modules
from models.price_predictor import PricePredictor
from models.fraud_detector import FraudDetector
from models.recommendation_engine import RecommendationEngine
from models.genai_handler import GenAIHandler
from models.comparison_engine import ComparisonEngine
from models.neighborhood_engine import NeighborhoodEngine
from models.amenity_matcher import AmenityMatcher
from models.vastu_checker import VastuChecker
from models.investment_advisor import InvestmentAdvisor
from models.market_news_rag import MarketNewsRAG
from models.contract_analyzer import ContractAnalyzer
from models.agentic_workflow import AgenticWorkflow
from models.smart_property_map_search import SmartPropertyMapSearch
from models.social import SocialIntelligenceEngine
from utils.data_processor import DataProcessor
from app.api.router import v2_router

load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="myNivas - Real Estate Aggregator",
    description="AI-powered property search and analysis platform",
    version="1.0.0"
)

# Non-breaking v2 layered routes are added alongside existing endpoints.
app.include_router(v2_router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
price_predictor = PricePredictor()
fraud_detector = FraudDetector()
recommendation_engine = RecommendationEngine()
genai_handler = GenAIHandler()
comparison_engine = ComparisonEngine()
neighborhood_engine = NeighborhoodEngine()
amenity_matcher = AmenityMatcher()
vastu_checker = VastuChecker()
investment_advisor = InvestmentAdvisor()
market_news_rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
contract_analyzer = ContractAnalyzer()
smart_property_map_search = SmartPropertyMapSearch()
social_intelligence_engine = None
data_processor = DataProcessor()
agentic_workflow = None
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
FIRECRAWL_SEED_URLS = [
    "https://www.housing.com/in/buy/mumbai",
    "https://www.magicbricks.com/property-for-sale/residential-real-estate?cityName=Mumbai",
    "https://www.99acres.com/property-in-mumbai-ffid",
    "https://www.nobroker.in/property/sale/mumbai/Mumbai",
]
_FIRECRAWL_REFERENCE_CACHE: Optional[List[Dict]] = None


def _normalize_lookup_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _is_verified_image(url: Optional[str]) -> bool:
    if not isinstance(url, str):
        return False
    cleaned = url.strip().lower()
    if not cleaned.startswith("http"):
        return False
    blocked = ("logo", "icon", "svg", "sprite", "placeholder", "fallback", "nophotos", "badge", "banner")
    return not any(token in cleaned for token in blocked)


def _clean_image_list(images: List) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for image in images or []:
        if not _is_verified_image(image):
            continue
        image_str = str(image).strip()
        if image_str in seen:
            continue
        seen.add(image_str)
        cleaned.append(image_str)
        if len(cleaned) == 3:
            break
    return cleaned


def _load_firecrawl_reference_listings() -> List[Dict]:
    global _FIRECRAWL_REFERENCE_CACHE
    if _FIRECRAWL_REFERENCE_CACHE is not None:
        return _FIRECRAWL_REFERENCE_CACHE

    dataset_path = Path(__file__).resolve().parents[1] / "Datasets" / "firecrawl_mumbai_properties.json"
    if not dataset_path.exists():
        _FIRECRAWL_REFERENCE_CACHE = []
        return _FIRECRAWL_REFERENCE_CACHE

    try:
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        _FIRECRAWL_REFERENCE_CACHE = data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning(f"Could not load Firecrawl reference dataset: {exc}")
        _FIRECRAWL_REFERENCE_CACHE = []
    return _FIRECRAWL_REFERENCE_CACHE


def _score_property_match(raw_property: Dict, candidate: Dict) -> float:
    raw_title = _normalize_lookup_text(raw_property.get("title") or raw_property.get("name"))
    raw_location = _normalize_lookup_text(raw_property.get("location") or raw_property.get("address") or raw_property.get("city"))
    cand_title = _normalize_lookup_text(candidate.get("title") or candidate.get("name"))
    cand_location = _normalize_lookup_text(candidate.get("location") or candidate.get("city") or candidate.get("locality"))

    title_score = SequenceMatcher(None, raw_title, cand_title).ratio() if raw_title and cand_title else 0.0
    location_score = SequenceMatcher(None, raw_location, cand_location).ratio() if raw_location and cand_location else 0.0
    exact_bonus = 0.2 if raw_title and cand_title and raw_title == cand_title else 0.0
    location_bonus = 0.15 if raw_location and cand_location and raw_location == cand_location else 0.0
    return title_score * 0.7 + location_score * 0.3 + exact_bonus + location_bonus


def _find_firecrawl_reference_match(raw_property: Dict) -> Optional[Dict]:
    candidates = _load_firecrawl_reference_listings()
    if not candidates:
        return None

    best_match = None
    best_score = 0.0
    for candidate in candidates:
        score = _score_property_match(raw_property, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    return best_match if best_score >= 0.55 else None


def _firecrawl_scrape_listing(raw_property: Dict) -> Optional[Dict]:
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        return None

    title = str(raw_property.get("title") or raw_property.get("name") or "property").strip()
    location = str(raw_property.get("location") or raw_property.get("address") or raw_property.get("city") or "Mumbai").strip()
    query = f"{title} {location} Mumbai real estate"
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    def _discover_links(seed_url: str) -> List[str]:
        try:
            response = session.post(
                f"{FIRECRAWL_BASE_URL}/map",
                json={"url": seed_url, "limit": 25, "search": query},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            links = payload.get("links") or payload.get("data") or []
            if isinstance(links, dict):
                links = links.get("links", [])
            return [link for link in links if isinstance(link, str)]
        except Exception as exc:
            logger.debug(f"Firecrawl map discovery failed for {seed_url}: {exc}")
            return []

    def _scrape(url: str) -> Optional[Dict]:
        try:
            response = session.post(
                f"{FIRECRAWL_BASE_URL}/scrape",
                json={"url": url, "formats": ["markdown", "html"]},
                timeout=90,
            )
            response.raise_for_status()
            return response.json().get("data") or response.json()
        except Exception as exc:
            logger.debug(f"Firecrawl scrape failed for {url}: {exc}")
            return None

    for seed_url in FIRECRAWL_SEED_URLS:
        for candidate_url in _discover_links(seed_url)[:5]:
            scraped = _scrape(candidate_url)
            if not isinstance(scraped, dict):
                continue

            metadata = scraped.get("metadata") or {}
            markdown = str(scraped.get("markdown") or "")
            html = str(scraped.get("html") or "")
            text = _normalize_lookup_text(" ".join([
                metadata.get("title") or "",
                metadata.get("description") or "",
                markdown,
            ]))
            if _normalize_lookup_text(title) not in text and _normalize_lookup_text(location) not in text:
                continue

            images = _clean_image_list([
                metadata.get("ogImage"),
                metadata.get("twitterImage"),
                metadata.get("image"),
                *re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE),
            ])

            return {
                "title": metadata.get("title") or title,
                "name": metadata.get("title") or title,
                "description": metadata.get("description") or scraped.get("markdown") or "",
                "location": location,
                "city": "Mumbai",
                "locality": location,
                "source": "firecrawl",
                "source_url": candidate_url,
                "bhk": raw_property.get("bhk"),
                "size": raw_property.get("size"),
                "price": raw_property.get("price"),
                "pricePerSqft": raw_property.get("pricePerSqft"),
                "amenities": raw_property.get("amenities") or [],
                "images": images,
                "latitude": None,
                "longitude": None,
            }

    return None
try:
    agentic_workflow = AgenticWorkflow(
        price_predictor=price_predictor,
        fraud_detector=fraud_detector,
        market_news_rag=market_news_rag,
        genai_handler=genai_handler,
    )
except Exception as e:
    logger.warning(f"Agentic workflow unavailable at startup: {e}")


def _refresh_market_news_on_interval():
    if not config.NEWS_REFRESH_ENABLED:
        logger.info("Market news refresh disabled")
        return

    backend_dir = Path(__file__).parent
    interval_seconds = max(1, config.NEWS_REFRESH_INTERVAL_HOURS) * 3600

    while True:
        try:
            logger.info("Refreshing market news dataset...")
            subprocess.run(
                [sys.executable, "scrape_real_estate_news.py"],
                cwd=str(backend_dir),
                check=False
            )
            subprocess.run(
                [sys.executable, "load_market_news.py"],
                cwd=str(backend_dir),
                check=False
            )
            logger.info("Market news refresh completed")
        except Exception as e:
            logger.error(f"Market news refresh failed: {str(e)}")

        time.sleep(interval_seconds)


@app.on_event("startup")
def start_market_news_refresh():
    Thread(target=_refresh_market_news_on_interval, daemon=True).start()

def encode_file_to_base64(file_bytes: bytes) -> str:
    """Encode file bytes to base64 string."""
    return base64.b64encode(file_bytes).decode("utf-8")


def get_social_intelligence_engine():
    global social_intelligence_engine
    if social_intelligence_engine is None:
        social_intelligence_engine = SocialIntelligenceEngine(genai_handler=genai_handler)
    return social_intelligence_engine

# Pydantic models
class Property(BaseModel):
    title: str
    description: str
    location: str
    bhk: Optional[int] = None
    size: Optional[float] = None
    price: Optional[float] = None
    amenities: Optional[List[str]] = []
    images: Optional[List[str]] = []
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None

class PriceRequest(BaseModel):
    location: str
    bhk: int
    size: float
    amenities: List[str] = []
    furnishing: Optional[str] = 'Semi-Furnished'
    construction_status: Optional[str] = 'Ready to Move'


class AgenticAnalyzeRequest(BaseModel):
    location: str
    bhk: int
    size: float
    amenities: Optional[List[str]] = []

class PriceResponse(BaseModel):
    predicted_price: float
    price_range: dict
    confidence: float
    factors: dict
    comparables: Optional[List[dict]] = []
    market_trend: Optional[str] = ''

class DuplicateRequest(BaseModel):
    property_id: str
    title: str
    description: str
    broker_name: Optional[str] = ""
    phone_number: Optional[str] = ""
    image_hash: Optional[str] = ""

class FraudResponse(BaseModel):
    trust_score: float
    risk_level: str
    flags: List[str]

class RecommendationRequest(BaseModel):
    budget_min: float
    budget_max: float
    location: str
    bhk: Optional[int] = None
    amenities: List[str] = []

class RecommendationResponse(BaseModel):
    listings: List[dict]
    count: int
    map: Optional[Dict] = None

class CompareRequest(BaseModel):
    title: str
    location: str
    price: Optional[float] = None
    bhk: Optional[int] = None
    size: Optional[float] = None

class CompareResponse(BaseModel):
    property_title: str
    location: str
    offers: List[dict]
    best_price: float
    avg_price: float

class PropertyDetailRequest(BaseModel):
    property: Dict


class PropertyDetailResponse(BaseModel):
    property: Dict
    map: Optional[Dict] = None
    comparison: Optional[Dict] = None
    similar: List[Dict] = []

class NeighborhoodRequest(BaseModel):
    location: str

class LifestyleMatchRequest(BaseModel):
    lifestyle: str
    location: Optional[str] = ""

class CrossModalSearchRequest(BaseModel):
    query: str
    lifestyle: Optional[str] = None
    top_k: int = 6
    use_cross_modal: bool = True

class VastuRequest(BaseModel):
    facing: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class InvestmentForecastRequest(BaseModel):
    price: float
    location: str
    bhk: Optional[int] = None
    size: Optional[float] = None
    amenities: Optional[List[str]] = []
    investment_horizon: Optional[int] = 5
    risk_tolerance: Optional[str] = "moderate"
    developer_name: Optional[str] = None
    property_type: Optional[str] = "residential"

class InvestorProfileRequest(BaseModel):
    investment_horizon: int
    risk_tolerance: str
    budget: float
    goals: Optional[List[str]] = []
    investor_name: Optional[str] = None

class InvestmentForecastResponse(BaseModel):
    property: dict
    market_context: dict
    base_roi_analysis: dict
    scenario_analysis: dict
    investment_thesis: str
    formatted_thesis: Optional[str] = None
    timestamp: str

# ==================== CONTRACT ANALYZER MODELS ====================

class ContractAnalysisRequest(BaseModel):
    contract_text: str
    contract_type: Optional[str] = "lease"  # lease, purchase, mou, agreement
    property_details: Optional[Dict] = {}

class FlaggedClause(BaseModel):
    clause: str
    risk_level: str
    reason: str
    rera_section: str

class ContractFinding(BaseModel):
    clause_snippet: str
    risk_level: str
    reason: str
    rera_section: str
    deduction: int

class ContractAnalysisResponse(BaseModel):
    success: bool
    contract_type: str
    compliance_score: int
    risk_level: str
    total_clauses_reviewed: int
    flagged_clauses: List[FlaggedClause]
    findings: List[Dict]
    recommendations: List[str]
    analysis_date: str
    message: Optional[str] = ""

class WhatIfRequest(BaseModel):
    clause_text: str
    scenario: str

class WhatIfResponse(BaseModel):
    scenario: str
    consequence: str
    rera_citation: str
    details: Dict

class TrustScoreRequest(BaseModel):
    contract_data: Dict

@app.get("/")
async def root():
    return {
        "name": "myNivas",
        "version": "1.0.0",
        "description": "AI-powered Real Estate Aggregator for India",
        "endpoints": {
            "price_prediction": "/api/price/predict",
            "fraud_detection": "/api/fraud/detect",
            "recommendations": "/api/recommendations",
            "genai": "/api/genai/describe"
        }
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# VASTU/FENG SHUI CHECKER ENDPOINT
@app.post("/api/vastu/check")
async def check_vastu_compliance(request: VastuRequest):
    """
    Check Vastu/Feng Shui compliance for a property.
    Uses SerpApi to fetch real surroundings and applies rule-based Vastu logic.
    """
    try:
        result = vastu_checker.check_compliance(
            facing=request.facing,
            location=request.location,
            lat=request.latitude,
            lng=request.longitude
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== PRICE PREDICTION ENDPOINTS ====================

@app.post("/api/price/predict", response_model=PriceResponse)
async def predict_price(request: Request, image: Optional[UploadFile] = File(default=None)):
    """
    Smart price prediction with real market data, trends, and optional image signal.
    Supports both:
    - application/json payload
    - multipart/form-data with optional `image` file
    """
    temp_image_path = None
    try:
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            payload = await request.json()
            location = payload.get("location")
            bhk = payload.get("bhk")
            size = payload.get("size")
            amenities = payload.get("amenities", [])
            furnishing = payload.get("furnishing", "Semi-Furnished")
            construction_status = payload.get("construction_status", "Ready to Move")
        else:
            form = await request.form()
            location = form.get("location")
            bhk = form.get("bhk")
            size = form.get("size")
            furnishing = form.get("furnishing", "Semi-Furnished")
            construction_status = form.get("construction_status", "Ready to Move")

            amenities_raw = form.get("amenities", "[]")
            if isinstance(amenities_raw, str):
                try:
                    parsed = json.loads(amenities_raw)
                    if isinstance(parsed, list):
                        amenities = [str(x) for x in parsed]
                    else:
                        amenities = [item.strip() for item in amenities_raw.split(",") if item.strip()]
                except Exception:
                    amenities = [item.strip() for item in amenities_raw.split(",") if item.strip()]
            elif isinstance(amenities_raw, list):
                amenities = [str(x) for x in amenities_raw]
            else:
                amenities = []

        if location is None or bhk is None or size is None:
            raise HTTPException(status_code=400, detail="location, bhk, and size are required")

        if image is not None and image.filename:
            suffix = Path(image.filename).suffix or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(await image.read())
                temp_image_path = temp_file.name

        features = {
            'location': str(location),
            'bhk': int(bhk),
            'size': float(size),
            'amenities': amenities,
            'furnishing': str(furnishing),
            'construction_status': str(construction_status)
        }

        prediction = await asyncio.to_thread(
            price_predictor.predict,
            features,
            temp_image_path,
        )
        
        return PriceResponse(
            predicted_price=prediction['predicted_price'],
            price_range=prediction['price_range'],
            confidence=prediction['confidence'],
            factors=prediction['factors'],
            comparables=prediction.get('comparables', []),
            market_trend=prediction.get('market_trend', '')
        )
    except Exception as e:
        logger.error(f"Price prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except Exception:
                pass

@app.get("/api/price/market-analysis/{location}")
async def market_analysis(location: str):
    """
    Get market analysis for a specific location
    """
    try:
        analysis = price_predictor.analyze_market(location)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== FRAUD DETECTION ENDPOINTS ====================

@app.post("/api/fraud/detect", response_model=FraudResponse)
async def detect_fraud(request: DuplicateRequest):
    """
    Detect fraud/duplicate/suspicious listings
    """
    try:
        fraud_result = fraud_detector.analyze(
            property_id=request.property_id,
            title=request.title,
            description=request.description,
            broker_name=request.broker_name or "",
            phone_number=request.phone_number or "",
            image_hash=request.image_hash or "",
        )
        
        return FraudResponse(
            trust_score=fraud_result['trust_score'],
            risk_level=fraud_result['risk_level'],
            flags=fraud_result['flags']
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/fraud/graph-analysis/{property_id}")
async def fraud_graph_analysis(property_id: str):
    """
    Run Neo4j-backed relational fraud analysis for a specific property.
    Returns graph score, suspicious duplicate clusters, and sample Cypher queries.
    """
    try:
        return fraud_detector.get_graph_analysis(property_id)
    except Exception as e:
        logger.error(f"Graph fraud analysis error for {property_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fraud/batch-detect")
async def batch_detect_fraud(file: UploadFile = File(...)):
    """
    Detect fraud in batch of listings from CSV
    """
    try:
        df = pd.read_csv(file.file)
        results = fraud_detector.batch_analyze(df)
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== RECOMMENDATION ENDPOINTS ====================

@app.post("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Get personalized property recommendations
    """
    try:
        preferences = {
            'budget_min': request.budget_min,
            'budget_max': request.budget_max,
            'location': request.location,
            'bhk': request.bhk,
            'amenities': request.amenities
        }

        # 1) Dataset-driven recommendations (existing behavior)
        dataset_recommendations = recommendation_engine.get_recommendations(preferences)

        # 2) SERP API map-aware recommendations (new behavior)
        serp_matches: List[Dict] = []
        map_payload: Optional[Dict] = None
        try:
            if request.location and getattr(smart_property_map_search, "serpapi_key", ""):
                budget_hint = ""
                if request.budget_max and request.budget_max > 0:
                    budget_hint = f" under {int(request.budget_max / 10000000)} crore"
                bhk_hint = f"{request.bhk} bhk " if request.bhk else ""
                query = f"{bhk_hint}apartment in {request.location}{budget_hint}".strip()

                serp_result = smart_property_map_search.search(
                    query=query,
                    lifestyle=None,
                    top_k=12,
                )
                serp_matches = serp_result.get("matches", []) or []
                map_payload = serp_result.get("map")
        except Exception as serp_exc:
            logger.warning(f"SERP map search fallback to dataset-only: {serp_exc}")

        # Normalize SERP matches into the same listing contract used by the Search page.
        normalized_serp = []
        for idx, item in enumerate(serp_matches):
            price_numeric = item.get("priceNumeric")
            if price_numeric is None:
                if request.budget_min and request.budget_max and request.budget_max > request.budget_min:
                    price_numeric = (request.budget_min + request.budget_max) / 2.0
                elif request.budget_max and request.budget_max > 0:
                    price_numeric = request.budget_max * 0.85
                else:
                    price_numeric = 7500000.0

            normalized_serp.append(
                {
                    "id": f"serp_{item.get('id') or idx}",
                    "title": item.get("name") or "SERP Property",
                    "description": item.get("address") or "",
                    "location": item.get("city") or item.get("locality") or request.location or "",
                    "bhk": item.get("bhk") or request.bhk,
                    "size": None,
                    "price": float(price_numeric),
                    "seller": "SERP API",
                    "amenities": item.get("amenities", []),
                    "images": [],
                    "rating": 4.0,
                    "views": 0,
                    "posted_date": datetime.now().strftime("%Y-%m-%d"),
                    "match_score": round(float(item.get("similarity_score", 0.6)) * 100, 2),
                    "match_reasons": item.get("match_reasons", ["Matched from live map search"]),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "source": "serpapi",
                }
            )

        # Merge SERP + dataset, de-duplicate by title+location, and keep ranking by match score.
        merged: List[Dict] = []
        seen_keys = set()
        for listing in (normalized_serp + dataset_recommendations):
            key = f"{str(listing.get('title', '')).strip().lower()}|{str(listing.get('location', '')).strip().lower()}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            if "source" not in listing:
                listing["source"] = "dataset"
            merged.append(listing)

        merged.sort(key=lambda item: float(item.get("match_score", 0) or 0), reverse=True)
        top_listings = merged[:15]

        # Fallback map center from first coordinate-rich listing if SERP center unavailable.
        if not map_payload:
            with_coords = [x for x in top_listings if x.get("latitude") is not None and x.get("longitude") is not None]
            if with_coords:
                map_payload = {
                    "center": {
                        "latitude": float(with_coords[0]["latitude"]),
                        "longitude": float(with_coords[0]["longitude"]),
                        "label": request.location or "Search area",
                        "source": "listings",
                    },
                    "marker_count": len(with_coords),
                }

        return RecommendationResponse(
            listings=top_listings,
            count=len(top_listings),
            map=map_payload,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/recommendations/trending")
async def get_trending():
    """
    Get trending/most viewed properties
    """
    try:
        trending = recommendation_engine.get_trending()
        return {"listings": trending}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== PRICE COMPARISON ENDPOINTS ====================

@app.post("/api/compare", response_model=CompareResponse)
async def compare_listings(request: CompareRequest):
    """
    Compare the same property across multiple platforms (mocked data)
    """
    try:
        comparison = comparison_engine.compare(request.dict())
        return CompareResponse(**comparison)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/properties/enrich", response_model=PropertyDetailResponse)
async def enrich_property_detail(request: PropertyDetailRequest):
    """Return property-specific details, comparison data, and a live map center."""
    try:
        raw_property = request.property or {}

        listing = None
        property_id = str(raw_property.get("id") or "").strip()
        property_title = str(raw_property.get("title") or raw_property.get("name") or "Property").strip()
        property_location = str(raw_property.get("location") or raw_property.get("address") or raw_property.get("city") or "").strip()

        for item in getattr(recommendation_engine, "listings", []):
            item_id = str(item.get("id") or "")
            item_title = str(item.get("title") or item.get("name") or "")
            if property_id and item_id == property_id and _normalize_lookup_text(item_title) == _normalize_lookup_text(property_title):
                listing = item
                break
            if property_title and item_title.lower() == property_title.lower():
                listing = item
                break

        if listing is None:
            listing = _find_firecrawl_reference_match(raw_property) or _firecrawl_scrape_listing(raw_property) or raw_property

        images = _clean_image_list(listing.get("images") or [listing.get("image"), listing.get("image2"), listing.get("image3")])

        normalized_property = {
            "id": str(listing.get("id") or property_id or property_title),
            "title": listing.get("title") or property_title,
            "location": listing.get("location") or property_location,
            "city": listing.get("city") or raw_property.get("city") or "Mumbai",
            "bhk": listing.get("bhk") or raw_property.get("bhk"),
            "size": float(listing.get("size") or raw_property.get("size") or 0),
            "price": float(listing.get("price") or raw_property.get("price") or 0),
            "priceLabel": raw_property.get("priceLabel") or raw_property.get("price") or listing.get("priceLabel"),
            "description": listing.get("description") or raw_property.get("description") or "",
            "amenities": [a for a in (listing.get("amenities") or raw_property.get("amenities") or []) if str(a).strip().lower() != "nan"],
            "images": images,
            "source": listing.get("source") or raw_property.get("source") or "dataset",
            "seller": listing.get("seller") or raw_property.get("seller") or raw_property.get("developer") or "Unknown",
            "pricePerSqft": raw_property.get("pricePerSqft") or raw_property.get("price_per_sqft") or None,
            "trustScore": raw_property.get("trustScore") or 75,
            "latitude": raw_property.get("latitude") or listing.get("latitude"),
            "longitude": raw_property.get("longitude") or listing.get("longitude"),
        }

        if normalized_property["pricePerSqft"] is None and normalized_property["price"] and normalized_property["size"]:
            try:
                normalized_property["pricePerSqft"] = round(float(normalized_property["price"]) / float(normalized_property["size"]))
            except Exception:
                normalized_property["pricePerSqft"] = None

        if normalized_property["size"]:
            try:
                normalized_property["size"] = round(float(normalized_property["size"]), 1)
            except Exception:
                pass

        if (normalized_property["latitude"] is None or normalized_property["longitude"] is None) and property_location:
            try:
                serp_result = smart_property_map_search.search(
                    query=f"{property_title} {property_location}",
                    lifestyle=None,
                    top_k=1,
                )
                serp_map = serp_result.get("map") or {}
                center = serp_map.get("center") or {}
                normalized_property["latitude"] = center.get("latitude")
                normalized_property["longitude"] = center.get("longitude")
            except Exception as serp_exc:
                logger.warning(f"Could not enrich map for {property_title}: {serp_exc}")

        comparison = comparison_engine.compare({
            "title": normalized_property["title"],
            "location": normalized_property["location"],
            "price": normalized_property["price"],
            "bhk": normalized_property["bhk"],
            "size": normalized_property["size"],
        })

        similar = recommendation_engine.get_recommendations({
            "budget_min": max(0, normalized_property["price"] * 0.7 if normalized_property["price"] else 0),
            "budget_max": normalized_property["price"] * 1.3 if normalized_property["price"] else float("inf"),
            "location": normalized_property["location"],
            "bhk": normalized_property["bhk"],
            "amenities": normalized_property["amenities"][:3],
        })[:6]

        map_payload = None
        if normalized_property["latitude"] is not None and normalized_property["longitude"] is not None:
            map_payload = {
                "center": {
                    "latitude": float(normalized_property["latitude"]),
                    "longitude": float(normalized_property["longitude"]),
                    "label": normalized_property["location"] or normalized_property["title"],
                    "source": "serpapi" if getattr(smart_property_map_search, "serpapi_key", "") else "dataset",
                },
                "marker_count": 1,
            }

        return PropertyDetailResponse(
            property=normalized_property,
            map=map_payload,
            comparison=comparison,
            similar=similar,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== GENAI ENDPOINTS ====================

@app.post("/api/genai/describe")
async def generate_description(property: Property):
    """
    Generate improved listing description using AI
    """
    try:
        description = genai_handler.generate_description(
            title=property.title,
            location=property.location,
            bhk=property.bhk or 2,
            size=property.size or 800,
            amenities=property.amenities or []
        )
        return {"description": description}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/genai/explain-price")
async def explain_price(request: PriceRequest):
    """
    Explain price differences in simple language
    """
    try:
        explanation = genai_handler.explain_price(request.dict())
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/genai/chat")
async def chat_with_property_advisor(message: dict):
    """
    Chat with AI property advisor
    """
    try:
        response = genai_handler.chat(message.get('message', ''))
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agentic/analyze")
async def agentic_analyze(request: AgenticAnalyzeRequest):
    """
    Orchestrate valuation, fraud analysis, market intelligence, and final advisory
    using a LangGraph sequential workflow.
    """
    try:
        if agentic_workflow is None:
            raise HTTPException(
                status_code=503,
                detail="Agentic workflow is unavailable. Install langgraph and restart backend.",
            )

        initial_state = {
            "location": request.location,
            "bhk": request.bhk,
            "size": request.size,
            "amenities": request.amenities or [],
        }

        final_state = await agentic_workflow.run(initial_state)

        return {
            "predicted_price": final_state.get("predicted_price"),
            "fraud_score": final_state.get("fraud_score"),
            "market_summary": final_state.get("market_summary", ""),
            "final_advice": final_state.get("final_advice", ""),
            "errors": final_state.get("errors", []),
            "request_id": final_state.get("request_id"),
            "timestamp": final_state.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Agentic analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Agentic analysis failed")

@app.post("/api/genai/neighborhood-report")
async def get_neighborhood_report(request: NeighborhoodRequest):
    """
    Generate a GenAI-powered neighborhood report with landmark insights,
    connectivity analysis, and family suitability for a given location.
    """
    try:
        report = neighborhood_engine.generate_report(request.location)
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/genai/amenity-match")
async def match_amenities(request: LifestyleMatchRequest):
    """
    Match user lifestyle preferences to property amenities using TF-IDF
    cosine similarity and generate a personalised pitch.
    """
    try:
        result = amenity_matcher.match(
            lifestyle=request.lifestyle,
            location=request.location or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/genai/cross-modal-match")
async def cross_modal_property_search(request: CrossModalSearchRequest):
    """
    Natural-language smart property discovery with map-ready results.

    Breaks the user sentence into structured requirements, scores local
    property inventory against those requirements, and returns matches
    with coordinates and price labels for the Home-page map panel.
    """
    try:
        result = smart_property_map_search.search(
            query=request.query,
            lifestyle=request.lifestyle,
            top_k=request.top_k,
        )
        return result
    except Exception as e:
        logger.error(f"Cross-modal search error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/genai/lifestyle-profiles")
async def get_lifestyle_profiles():
    """
    Return the available lifestyle preset profiles for the Amenity Matcher.
    """
    return {
        "profiles": [
            {"name": name, "icon": info["icon"], "color": info["color"]}
            for name, info in amenity_matcher.LIFESTYLE_PROFILES.items()
        ]
    }

# ==================== VASTU/FENG SHUI CHECKER ====================

@app.get("/api/vastu/test")
async def test_vastu():
    """Simple test endpoint to verify vastu section is working"""
    return {"status": "ok", "message": "Vastu section is active"}

@app.post("/api/vastu/check")
async def check_vastu_compliance(request: VastuRequest):
    """
    Check Vastu/Feng Shui compliance for a property.
    Uses SerpApi to fetch real surroundings and applies rule-based Vastu logic.
    
    Args:
        facing: Property facing direction (North, South, East, etc.)
        location: Property location/address
        latitude: Optional latitude for precise location
        longitude: Optional longitude for precise location
    
    Returns:
        Score (0-100), compliance level, factors, and remedies
    """
    try:
        result = vastu_checker.check_compliance(
            facing=request.facing,
            location=request.location,
            lat=request.latitude,
            lng=request.longitude
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== DATA MANAGEMENT ENDPOINTS ====================

@app.post("/api/data/upload-listings")
async def upload_listings(file: UploadFile = File(...)):
    """
    Upload and process listings CSV
    """
    try:
        df = pd.read_csv(file.file)
        processed = data_processor.process_listings(df)
        return {
            "message": "Listings uploaded successfully",
            "count": len(processed),
            "data": processed[:10]  # Return first 10
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/data/listings")
async def get_listings(location: Optional[str] = None, limit: int = 20):
    """
    Get all listings with optional filter
    """
    try:
        listings = data_processor.get_listings(location=location, limit=limit)
        return {"listings": listings, "count": len(listings)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/test-before-locations")
async def test_before_locations():
    return {"test": "before locations endpoint"}

@app.get("/api/data/locations")
async def get_locations():
    """
    Get all unique locations in database
    """
    try:
        locations = data_processor.get_unique_locations()
        return {"locations": locations}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/test-simple")
async def test_simple():
    return {"test": "works"}

# ==================== INVESTMENT ADVISOR ENDPOINTS ====================

@app.post("/api/genai/investment-forecast")
async def generate_investment_forecast(request: InvestmentForecastRequest):
    """
    Generate RAG-enhanced investment forecast with ROI projections.
    
    Uses historical market data, scenario analysis, and GenAI reasoning
    to provide personalized investment forecasts for properties.
    """
    try:
        if request.price <= 0:
            raise HTTPException(status_code=400, detail="price must be greater than 0")
        if (request.bhk or 1) <= 0:
            raise HTTPException(status_code=400, detail="bhk must be greater than 0")
        if (request.size or 1) <= 0:
            raise HTTPException(status_code=400, detail="size must be greater than 0")
        if request.investment_horizon is not None and not (1 <= request.investment_horizon <= 20):
            raise HTTPException(status_code=400, detail="investment_horizon must be between 1 and 20 years")

        risk_tolerance = (request.risk_tolerance or 'moderate').lower().strip()
        if risk_tolerance not in {'low', 'moderate', 'high'}:
            risk_tolerance = 'moderate'

        property_details = {
            'price': request.price,
            'location': request.location,
            'bhk': request.bhk or 2,
            'size': request.size or 1000,
            'amenities': request.amenities or []
        }
        
        investor_profile = {
            'investment_horizon': request.investment_horizon or 5,
            'risk_tolerance': risk_tolerance,
            'goals': ['capital_appreciation', 'rental_income']
        }
        
        # Get investment forecast via GenAI + RAG
        forecast = genai_handler.generate_investment_forecast(
            property_details,
            investor_profile
        )
        
        return forecast
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/genai/analyze-investment-fit")
async def analyze_investment_fit(
    property_request: InvestmentForecastRequest,
    profile_request: InvestorProfileRequest
):
    """
    Analyze if a property matches investor's profile using GenAI reasoning.
    
    Provides personalized suitability analysis based on investment horizon,
    risk tolerance, budget, and investment goals.
    """
    try:
        property_details = {
            'price': property_request.price,
            'location': property_request.location,
            'bhk': property_request.bhk or 2,
            'size': property_request.size or 1000
        }
        
        investor_profile = {
            'investment_horizon': profile_request.investment_horizon,
            'risk_tolerance': profile_request.risk_tolerance,
            'budget': profile_request.budget,
            'goals': profile_request.goals or [],
            'investor_name': profile_request.investor_name
        }
        
        analysis = genai_handler.analyze_investment_fit(
            property_details,
            investor_profile
        )
        
        return {
            'analysis': analysis,
            'property_location': property_request.location,
            'investor_profile': investor_profile
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/genai/market-insights/{location}")
async def get_market_insights(location: str):
    """
    Retrieve market insights for a specific location using RAG.
    
    Includes growth trends, rental yields, volatility analysis,
    and investment suitability for the location.
    """
    try:
        # Query market data via investment advisor
        market_context = investment_advisor.retrieve_market_context(
            f"Investment opportunities in {location}",
            location
        )
        
        # Get market metrics
        market_data = investment_advisor.market_data.get(location, {})
        historical = investment_advisor.historical_returns.get(location, {})
        
        return {
            'location': location,
            'market_metrics': market_data,
            'historical_performance': historical,
            'rag_context': market_context,
            'recommendation': f"{location} shows {market_data.get('yoy_growth', 0)*100:.0f}% YoY growth with {market_data.get('avg_rental_yield', 0)*100:.1f}% rental yields"
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/social-analysis")
async def get_social_analysis(
    area: str,
    top_k: int = 5,
    time_window_days: Optional[int] = None,
):
    """
    Analyze stored Reddit-style social discussions for an area.

    Uses location normalization, relevance filtering, FAISS retrieval,
    sentiment/aspect extraction, and a structured report generator.
    """
    logger.info(f"[Social Analysis] Received request for area: {area}")
    try:
        cleaned_area = (area or "").strip()
        if not cleaned_area:
            raise HTTPException(status_code=400, detail="area is required")

        logger.info(f"[Social Analysis] Getting engine and analyzing area: {cleaned_area}")
        engine = get_social_intelligence_engine()
        logger.info(f"[Social Analysis] Engine retrieved: {engine}")
        
        result = engine.analyze_area(
            area=cleaned_area,
            top_k=max(1, min(top_k, 10)),
            time_window_days=time_window_days,
        )
        logger.info(f"[Social Analysis] Analysis complete. Keys: {list(result.keys()) if result else 'None'}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Social Analysis] Error running social analysis for {area}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MARKET NEWS RAG ENDPOINTS ====================

@app.get("/api/genai/market-alerts/{location}")
async def get_market_alerts(
    location: str,
    query: Optional[str] = None,
    n_results: int = 5
):
    """
    Get real-time market news alerts for a location using RAG.
    
    Retrieves relevant news articles about infrastructure, development,
    and market trends for the specified location.
    
    Args:
        location: Location to query (e.g., "Mumbai", "Andheri West")
        query: Optional specific query (e.g., "metro construction")
        n_results: Number of news articles to retrieve (default: 5)
    
    Returns:
        Market alert with news articles and AI-generated insights
    """
    try:
        # Retrieve relevant news articles
        articles = market_news_rag.retrieve_relevant_news(
            location=location,
            query=query,
            n_results=n_results
        )
        
        # Generate alert summary
        alert = market_news_rag.generate_alert(
            location=location,
            articles=articles
        )
        
        return alert
    
    except Exception as e:
        logger.error(f"Error getting market alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/genai/trending-locations")
async def get_trending_locations(top_n: int = 5):
    """
    Get trending locations based on recent news activity.
    
    Args:
        top_n: Number of top locations to return (default: 5)
    
    Returns:
        List of trending locations with news count and impact scores
    """
    try:
        trending = market_news_rag.get_trending_locations(top_n=top_n)
        
        return {
            "trending_locations": trending,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting trending locations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/genai/market-alerts/property-impact")
async def get_property_market_impact(properties: List[Dict]):
    """
    Analyze market news impact on specific properties.
    
    Args:
        properties: List of property dicts with at least 'id' and 'location'
    
    Returns:
        Impact analysis for each property based on recent news
    """
    try:
        results = []
        
        for prop in properties:
            location = prop.get("location", "")
            if not location:
                continue
            
            # Get relevant news
            articles = market_news_rag.retrieve_relevant_news(
                location=location,
                n_results=3
            )
            
            # Generate alert with property context
            alert = market_news_rag.generate_alert(
                location=location,
                articles=articles,
                user_properties=[prop]
            )
            
            results.append({
                "property_id": prop.get("id"),
                "location": location,
                "alert": alert
            })
        
        return {
            "property_impacts": results,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error analyzing property impact: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/genai/market-news/add")
async def add_market_news(articles: List[Dict]):
    """
    Add new market news articles to the RAG database.
    
    Expected format for each article:
    {
        "id": "unique_id",
        "title": "Article title",
        "content": "Article content",
        "location": "Location name",
        "date": "ISO date string",
        "source": "Source name",
        "url": "Article URL",
        "impact_score": 0.0-1.0
    }
    """
    try:
        market_news_rag.add_news_articles(articles)
        
        return {
            "success": True,
            "message": f"Added {len(articles)} articles to the database",
            "count": len(articles)
        }
    
    except Exception as e:
        logger.error(f"Error adding news articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# VASTU ENDPOINT - ADDED AT END FOR TESTING
@app.post("/api/vastu-check-v2")
async def vastu_check_v2(request: VastuRequest):
    """Vastu compliance checker v2"""
    try:
        result = vastu_checker.check_compliance(
            facing=request.facing,
            location=request.location,
            lat=request.latitude,
            lng=request.longitude
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== CONTRACT ANALYZER ENDPOINTS ====================

@app.post("/api/genai/contract-analyze", response_model=ContractAnalysisResponse)
async def analyze_contract(request: ContractAnalysisRequest):
    """
    Analyze lease/contract for RERA compliance and legal risks
    
    Features:
    - Extracts clauses and analyzes against RERA guidelines
    - Identifies unfair terms, exemptions, and risk clauses
    - Flags violations of statutory rights
    - Generates compliance score (0-100)
    - Provides actionable recommendations
    
    Args:
        request: ContractAnalysisRequest with contract text and type
    
    Returns:
        ContractAnalysisResponse with risk assessment and recommendations
    """
    try:
        if not request.contract_text or len(request.contract_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Contract text too short for analysis")
        
        # Analyze contract
        analysis = contract_analyzer.analyze_contract(
            contract_text=request.contract_text,
            contract_type=request.contract_type
        )
        
        if not analysis.get('success'):
            raise HTTPException(status_code=400, detail=analysis.get('error', 'Analysis failed'))
        
        # Convert to response model
        return ContractAnalysisResponse(
            success=True,
            contract_type=analysis['contract_type'],
            compliance_score=analysis['compliance_score'],
            risk_level=analysis['risk_level'],
            total_clauses_reviewed=analysis['total_clauses_reviewed'],
            flagged_clauses=[FlaggedClause(**clause) for clause in analysis['flagged_clauses']],
            findings=analysis['findings'],
            recommendations=analysis['recommendations'],
            analysis_date=analysis['analysis_date'],
            message=f"Analysis complete. Compliance score: {analysis['compliance_score']}/100"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing contract: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Contract analysis failed: {str(e)}")


@app.post("/api/genai/contract/what-if")
async def contract_what_if(request: WhatIfRequest) -> Dict:
    """
    Analyze what-if scenarios for contract clauses
    
    Provides RERA section citations and consequences of different scenarios
    
    Args:
        request: Clause text and hypothetical scenario
    
    Returns:
        Analysis with RERA citations and consequences
    """
    try:
        if not request.scenario or len(request.scenario) < 10:
            raise HTTPException(status_code=400, detail="Scenario must be at least 10 characters")
        
        analysis = contract_analyzer.get_what_if_analysis(
            clause_text=request.clause_text,
            scenario=request.scenario
        )
        
        return {
            "success": True,
            "analysis": analysis
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in what-if analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/genai/contract/trust-score")
async def calculate_trust_score(request: TrustScoreRequest) -> Dict:
    """
    Calculate trust score for a property deal (0-100)
    
    Considers:
    - Document registration status
    - Title clarity
    - Legal compliance
    - Fair contract terms
    
    Args:
        request: Contract data with various legal factors
    
    Returns:
        Trust score and risk assessment
    """
    try:
        score = contract_analyzer.get_trust_score(request.contract_data)
        
        if score >= 80:
            risk_level = "low"
            advice = "✅ Safe to proceed with legal review"
        elif score >= 60:
            risk_level = "medium"
            advice = "⚠️ Moderate risks. Consult lawyer before signing."
        else:
            risk_level = "high"
            advice = "🚨 CRITICAL: Do not sign. Seek legal counsel immediately."
        
        return {
            "success": True,
            "trust_score": score,
            "risk_level": risk_level,
            "advice": advice,
            "details": {
                "registered": request.contract_data.get('is_registered', False),
                "title_clear": request.contract_data.get('title_clear', False),
                "stamp_duty_paid": request.contract_data.get('stamp_duty_paid', False),
                "has_fair_terms": not request.contract_data.get('has_unfair_clauses', False)
            }
        }
    
    except Exception as e:
        logger.error(f"Error calculating trust score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/genai/contract/compliance-guide")
async def get_compliance_guide() -> Dict:
    """
    Get RERA compliance guide and important sections
    
    Returns:
        Guide with key RERA sections, rights, and obligations
    """
    return {
        "success": True,
        "guide": {
            "critical_sections": [
                {
                    "section": "RERA Section 13",
                    "title": "Possession Timeline",
                    "buyer_right": "Compensation for delay (8-12% p.a. on purchase price)",
                    "action": "Can terminate if possession delayed 18+ months"
                },
                {
                    "section": "RERA Section 15",
                    "title": "Refund Policy",
                    "buyer_right": "Full refund + 10.35% interest if project stalled 1+ year",
                    "action": "Retain 10% only if >30% constructed"
                },
                {
                    "section": "RERA Section 18",
                    "title": "Structural Defects",
                    "buyer_right": "Builder liable for 5 years (structural), 2 years (non-structural)",
                    "action": "Defects must be fixed within 30 days at builder cost"
                },
                {
                    "section": "RERA Section 22",
                    "title": "Unfair Terms",
                    "buyer_right": "Any exemption clause is automatically void",
                    "action": "Clauses cannot shift undue risk to buyer"
                }
            ],
            "red_flags": [
                "Non-refundable deposit clause",
                "Builder exemption from liability",
                "No mention of possession timeline",
                "Unregistered document",
                "Unclear title or encumbrances",
                "Hidden costs or charges",
                "Exclusive jurisdiction forcing litigation in unfavorable location"
            ],
            "checklist": [
                "✓ Is agreement registered with proper stamp duty?",
                "✓ Is builder's RERA registration valid?",
                "✓ Does contract specify possession deadline?",
                "✓ Are defect liability periods clearly mentioned (5+2 years)?",
                "✓ Is title clear and free from encumbrances?",
                "✓ Are escalation and maintenance charges reasonable?",
                "✓ Does contract follow RERA mandated format?"
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
 
