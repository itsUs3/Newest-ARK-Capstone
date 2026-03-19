from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import logging
import base64
import asyncio
import subprocess
import sys
import time
import tempfile
from pathlib import Path
from threading import Thread
from dotenv import load_dotenv
import openai
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
from models.floorplan_generator import FloorplanGenerator
from models.market_news_rag import MarketNewsRAG
from models.contract_analyzer import ContractAnalyzer
from models.agentic_workflow import AgenticWorkflow
from utils.data_processor import DataProcessor

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
floorplan_generator = FloorplanGenerator()
market_news_rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
contract_analyzer = ContractAnalyzer()
data_processor = DataProcessor()
agentic_workflow = None
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

# ==================== FLOORPLAN GENERATOR MODELS ====================

class FloorplanGenerateRequest(BaseModel):
    boundary_wkt: str
    front_door_wkt: str
    room_centroids: List[List[float]]
    bathroom_centroids: Optional[List[List[float]]] = []
    kitchen_centroids: Optional[List[List[float]]] = []


class FloorplanGraphEdge(BaseModel):
    source: int
    target: int


class FloorplanNodePrediction(BaseModel):
    id: int
    type: str
    centroid: List[float]
    predicted_width: float
    predicted_height: float


class FloorplanGenerateResponse(BaseModel):
    success: bool
    image_base64: Optional[str] = None
    graph: Optional[Dict] = None
    nodes: List[FloorplanNodePrediction] = []
    message: str
    error: Optional[str] = None

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
        
        recommendations = recommendation_engine.get_recommendations(preferences)
        
        return RecommendationResponse(
            listings=recommendations[:15],
            count=len(recommendations[:15])
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
    Advanced cross-modal property search with semantic matching and visual montages.
    
    Bridges lifestyle profiles with semantic text embeddings using FAISS indexing,
    generates visual montages of matching properties.
    
    Args:
        query: Search query (e.g., "Affordable sea-view flat with gym")
        lifestyle: Optional lifestyle profile to optimize query
        top_k: Number of results to return (default 6)
        use_cross_modal: Use cross-modal matcher vs fallback (default True)
    
    Returns:
        Matches with property details, visual montage (base64), search metadata
    """
    try:
        result = amenity_matcher.get_cross_modal_recommendations(
            query=request.query,
            lifestyle=request.lifestyle,
            top_k=request.top_k,
            use_cross_modal=request.use_cross_modal
        )
        
        # Normalize response format for frontend
        # If this is a fallback result (has 'matched_amenities' but not 'matches')
        if 'matched_amenities' in result and 'matches' not in result:
            # Convert from amenity matcher format to cross-modal format
            matches = result.get('top_properties', [])
            
            # Normalize score field (amenity uses 'score', cross-modal uses 'similarity_score')
            for match in matches:
                if 'score' in match and 'similarity_score' not in match:
                    match['similarity_score'] = match.pop('score')
            
            result['matches'] = matches
            result['search_type'] = 'fallback_amenity'
            result['montage'] = None
        
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

# ==================== FLOORPLAN GENERATOR ENDPOINTS ====================

@app.post("/api/floorplan/generate", response_model=FloorplanGenerateResponse)
async def generate_floorplan(request: FloorplanGenerateRequest):
    """
    Generate a floor plan from user constraints using a GNN-style graph pipeline.
    """
    try:
        result = floorplan_generator.generate(
            boundary_wkt=request.boundary_wkt,
            front_door_wkt=request.front_door_wkt,
            room_centroids=request.room_centroids or [],
            bathroom_centroids=request.bathroom_centroids or [],
            kitchen_centroids=request.kitchen_centroids or [],
        )

        if not result.get("success"):
            return FloorplanGenerateResponse(
                success=False,
                image_base64=None,
                graph=None,
                nodes=[],
                message=result.get("message", "Generation failed"),
                error=result.get("error", "Unable to generate floorplans"),
            )

        node_predictions = [FloorplanNodePrediction(**n) for n in result.get("nodes", [])]
        return FloorplanGenerateResponse(
            success=True,
            image_base64=result.get("image_base64"),
            graph=result.get("graph"),
            nodes=node_predictions,
            message=result.get("message", "Floor plan generated successfully"),
            error=None,
        )
    except Exception as e:
        logger.error(f"Error generating floorplans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating floorplans: {str(e)}")


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
 
