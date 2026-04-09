import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from config import DATA_PATH, RAG_PERSIST_DIR

os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")

logger = logging.getLogger(__name__)

try:
    from models.market_news_rag import MarketNewsRAG
except Exception:
    MarketNewsRAG = None

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    LANGCHAIN_AVAILABLE = True
except Exception as e:
    LANGCHAIN_AVAILABLE = False
    Settings = None
    logger.warning(f"RAG dependencies unavailable ({e}). Falling back to rule-based mode.")


class InvestmentAdvisor:
    """
    RAG-Enhanced Investment Advisor for ROI Forecasting
    Uses historical property data + market reports to generate personalized investment forecasts
    """
    
    def __init__(self):
        self.index_initialized = False
        self.market_data = {}
        self.historical_returns = {}
        self.embedder = None
        self.chromadb_client = None
        self.market_news_rag = None
        self.base_dir = Path(__file__).resolve().parents[2]
        
        # Initialize RAG components if available
        if LANGCHAIN_AVAILABLE:
            try:
                self.embedder = SentenceTransformer(self._resolve_embedding_model())
                self.chromadb_client = chromadb.Client(settings=self._chroma_settings())
                self._initialize_rag_index()
            except Exception as e:
                logger.warning(f"RAG initialization warning: {e}")
        
        # Load market data
        self._load_market_data()
        self._generate_historical_returns()

        if MarketNewsRAG is not None:
            try:
                self.market_news_rag = MarketNewsRAG(persist_directory=RAG_PERSIST_DIR)
            except Exception as e:
                logger.warning(f"Market news signal unavailable: {e}")

    def _chroma_settings(self):
        if Settings is None:
            return None
        return Settings(anonymized_telemetry=False)

    def _resolve_embedding_model(self) -> str:
        candidate_paths = [
            self.base_dir / "backend" / "models" / "real_estate_embeddings",
            self.base_dir / "backend" / "models" / "backend" / "models" / "real_estate_embeddings",
        ]
        for candidate in candidate_paths:
            if candidate.exists():
                return str(candidate)
        return "all-MiniLM-L6-v2"
    
    def _initialize_rag_index(self):
        """Initialize ChromaDB vector store with property and market data"""
        try:
            # Create collection for properties
            if not self.chromadb_client:
                return
            
            # Clear existing collections
            try:
                self.chromadb_client.delete_collection("properties")
                self.chromadb_client.delete_collection("market_insights")
            except:
                pass
            
            # Create new collections
            self.property_collection = self.chromadb_client.create_collection(
                name="properties",
                metadata={"hnsw:space": "cosine"}
            )
            
            self.market_collection = self.chromadb_client.create_collection(
                name="market_insights",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Load and vectorize property data
            self._vectorize_property_data()
            
            # Load market insights
            self._vectorize_market_insights()
            
            self.index_initialized = True
            logger.info("RAG vector index initialized successfully")
        except Exception as e:
            logger.warning(f"RAG index initialization error: {e}")
    
    def _vectorize_property_data(self):
        """Vectorize property data and store in ChromaDB"""
        try:
            df = pd.read_csv(DATA_PATH)
            
            # Sample properties for vectorization (limit to avoid memory issues)
            sample_df = df.sample(min(100, len(df)))
            
            docs = []
            metadatas = []
            ids = []
            
            for idx, row in sample_df.iterrows():
                # Create document text
                title = str(row.get('title', ''))
                title2 = str(row.get('title2', ''))
                full_doc = f"{title} {title2}".strip()
                
                if full_doc and len(full_doc) > 5:
                    docs.append(full_doc)
                    
                    # Create metadata
                    metadata = {
                        'source': 'property_listing',
                        'index': str(idx)
                    }
                    metadatas.append(metadata)
                    ids.append(f"prop_{idx}")
            
            embeddings = []
            if docs:
                embeddings = self.embedder.encode(docs, show_progress_bar=False).tolist()
            
            # Add to collection
            if docs:
                self.property_collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=docs,
                    metadatas=metadatas
                )
                logger.info(f"Vectorized {len(docs)} property records")
        except Exception as e:
            logger.warning(f"Error vectorizing properties: {e}")
    
    def _vectorize_market_insights(self):
        """Create and vectorize market insights for RAG"""
        market_insights = [
            {
                'text': "Mumbai property market shows 15% YoY growth with strong rental yields 6-8% for residential. Preferred areas: BKC, South Mumbai, Andheri West",
                'location': 'Mumbai',
                'metric': 'growth_15pct'
            },
            {
                'text': "Bangalore tech hub driving 12% annual appreciation. IT corridor properties command premium. Rental yield: 5-7%",
                'location': 'Bangalore',
                'metric': 'growth_12pct'
            },
            {
                'text': "Delhi NCR experiencing 10% growth fueled by infrastructure projects. Dlf, Gurgaon witness strong appreciation",
                'location': 'Delhi',
                'metric': 'growth_10pct'
            },
            {
                'text': "Pune emerging market with 18% YoY growth. Young demographic, IT jobs, affordable prices. Best value proposition",
                'location': 'Pune',
                'metric': 'growth_18pct'
            },
            {
                'text': "Hyderabad shows resilient growth at 14% YoY. Real estate investment in tier-1 tech city. Strong tenant demand",
                'location': 'Hyderabad',
                'metric': 'growth_14pct'
            },
            {
                'text': "Post-COVID market stabilization: Properties in metro areas recovered 2019 levels. Now 8-12% growth YoY sustainable",
                'insight_type': 'macro_trend'
            },
            {
                'text': "2BHK segment most liquid, ROI predictable. 3BHK luxury segment volatile. Commercial real estate premium play",
                'insight_type': 'market_segment'
            },
            {
                'text': "Location multiplier impact: Premium locality adds 1.5-2x base price. Connectivity infrastructure critical",
                'insight_type': 'valuation_factor'
            },
        ]
        
        try:
            docs = []
            metadatas = []
            ids = []
            
            for idx, insight in enumerate(market_insights):
                docs.append(insight['text'])
                metadatas.append({k: str(v) for k, v in insight.items() if k != 'text'})
                ids.append(f"market_{idx}")
            embeddings = self.embedder.encode(docs, show_progress_bar=False).tolist()
            
            self.market_collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=docs,
                metadatas=metadatas
            )
            logger.info(f"Vectorized {len(docs)} market insights")
        except Exception as e:
            logger.warning(f"Error vectorizing market insights: {e}")
    
    def _load_market_data(self):
        """Load market data for different locations"""
        self.market_data = {
            'Mumbai': {
                'yoy_growth': 0.15,
                'avg_rental_yield': 0.068,
                'appreciation_trend': 'bullish',
                'avg_price_per_sqft': 95000,
                'demand_score': 9.5,
                'supply_score': 8.0,
                'inflation_adjusted': True,
                'metro_cities': ['Mumbai', 'Pune', 'Navi Mumbai']
            },
            'Bangalore': {
                'yoy_growth': 0.12,
                'avg_rental_yield': 0.065,
                'appreciation_trend': 'bullish',
                'avg_price_per_sqft': 65000,
                'demand_score': 9.0,
                'supply_score': 7.5,
                'inflation_adjusted': True,
                'metro_cities': ['Bangalore', 'Whitefield']
            },
            'Delhi': {
                'yoy_growth': 0.10,
                'avg_rental_yield': 0.06,
                'appreciation_trend': 'moderate',
                'avg_price_per_sqft': 70000,
                'demand_score': 8.5,
                'supply_score': 8.5,
                'inflation_adjusted': True,
                'metro_cities': ['Delhi', 'Gurgaon', 'Noida']
            },
            'Pune': {
                'yoy_growth': 0.13,
                'avg_rental_yield': 0.07,
                'appreciation_trend': 'bullish',
                'avg_price_per_sqft': 45000,
                'demand_score': 8.8,
                'supply_score': 7.0,
                'inflation_adjusted': True,
                'metro_cities': ['Pune', 'Pimpri-Chinchwad']
            },
            'Hyderabad': {
                'yoy_growth': 0.14,
                'avg_rental_yield': 0.068,
                'appreciation_trend': 'bullish',
                'avg_price_per_sqft': 50000,
                'demand_score': 8.7,
                'supply_score': 7.8,
                'inflation_adjusted': True,
                'metro_cities': ['Hyderabad']
            }
        }

    def _safe_float(self, value: Optional[float], default: float) -> float:
        try:
            parsed = float(value)
            if np.isnan(parsed):
                return default
            return parsed
        except Exception:
            return default

    def _sanitize_horizon(self, years: Optional[int]) -> int:
        try:
            parsed = int(years)
        except Exception:
            parsed = 5
        return max(1, min(20, parsed))

    def _resolve_location(self, location: Optional[str]) -> str:
        if not location:
            return 'Mumbai'
        normalized = str(location).strip().title()
        return normalized if normalized in self.market_data else 'Mumbai'

    def _get_news_signal(self, location: str, days_back: int = 90) -> Dict:
        """Convert recent market news impact into a bounded growth-rate adjustment."""
        if not self.market_news_rag:
            return {
                'enabled': False,
                'articles_count': 0,
                'avg_impact_score': 0.5,
                'growth_adjustment': 0.0,
                'reason': 'market_news_unavailable'
            }

        try:
            articles = self.market_news_rag.retrieve_relevant_news(
                location=location,
                query='property prices infrastructure investment real estate',
                n_results=8,
                days_back=days_back
            )
            if not articles:
                return {
                    'enabled': True,
                    'articles_count': 0,
                    'avg_impact_score': 0.5,
                    'growth_adjustment': 0.0,
                    'reason': 'no_recent_articles'
                }

            avg_impact = float(sum(a.get('impact_score', 0.5) for a in articles) / len(articles))
            # Impact score is in [0, 1]. Convert to bounded adjustment in [-0.02, +0.02].
            growth_adjustment = max(-0.02, min(0.02, (avg_impact - 0.5) * 0.08))

            return {
                'enabled': True,
                'articles_count': len(articles),
                'avg_impact_score': round(avg_impact, 3),
                'growth_adjustment': round(growth_adjustment, 4),
                'reason': 'live_news_signal'
            }
        except Exception as e:
            return {
                'enabled': False,
                'articles_count': 0,
                'avg_impact_score': 0.5,
                'growth_adjustment': 0.0,
                'reason': f'news_signal_error: {e}'
            }

    def _effective_growth_rate(self, location: str) -> Dict:
        market_info = self.market_data[location]
        base_growth = self._safe_float(market_info.get('yoy_growth'), 0.10)
        news_signal = self._get_news_signal(location)
        adjusted_growth = base_growth + news_signal['growth_adjustment']
        adjusted_growth = max(0.02, min(0.20, adjusted_growth))

        return {
            'base_growth_rate': round(base_growth, 4),
            'news_signal': news_signal,
            'effective_growth_rate': round(adjusted_growth, 4)
        }
    
    def _generate_historical_returns(self):
        """Generate historical ROI data patterns"""
        self.historical_returns = {
            'Mumbai': {
                'annual_appreciation': [0.08, 0.12, 0.15, 0.18, 0.15],  # Last 5 years
                'rental_yield_appreciation': [0.05, 0.06, 0.07, 0.08, 0.07],
                'best_performing_times': ['Q3-Q4', 'Post-Elections'],
                'volatility': 'moderate'
            },
            'Bangalore': {
                'annual_appreciation': [0.06, 0.09, 0.11, 0.14, 0.12],
                'rental_yield_appreciation': [0.04, 0.05, 0.065, 0.075, 0.065],
                'best_performing_times': ['Post-Tech Boom', 'Infrastructure-Ready Areas'],
                'volatility': 'low-moderate'
            },
            'Delhi': {
                'annual_appreciation': [0.05, 0.07, 0.08, 0.10, 0.10],
                'rental_yield_appreciation': [0.04, 0.045, 0.05, 0.06, 0.06],
                'best_performing_times': ['Infrastructure-Ready', 'Metro-Connected'],
                'volatility': 'moderate'
            },
            'Pune': {
                'annual_appreciation': [0.08, 0.11, 0.12, 0.13, 0.13],
                'rental_yield_appreciation': [0.05, 0.06, 0.065, 0.07, 0.07],
                'best_performing_times': ['Year-Round', 'Pre-Election'],
                'volatility': 'moderate'
            },
            'Hyderabad': {
                'annual_appreciation': [0.08, 0.11, 0.13, 0.15, 0.14],
                'rental_yield_appreciation': [0.05, 0.06, 0.067, 0.07, 0.068],
                'best_performing_times': ['Tech Sector Boom', 'Infrastructure Projects'],
                'volatility': 'low-moderate'
            }
        }
    
    def retrieve_market_context(self, query: str, location: str = None) -> Dict:
        """Retrieve relevant market data via semantic search"""
        if not LANGCHAIN_AVAILABLE or not self.index_initialized:
            return self._retrieve_market_context_fallback(location)
        
        try:
            # Create query embedding
            query_embedding = self.embedder.encode(query).tolist()
            
            # Search market insights
            market_results = self.market_collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            # Search property data
            property_results = self.property_collection.query(
                query_embeddings=[query_embedding],
                n_results=2
            )
            
            return {
                'market_insights': market_results.get('documents', [[]]),
                'comparable_properties': property_results.get('documents', [[]]),
                'retrieval_method': 'semantic_search'
            }
        except Exception as e:
            logger.warning(f"RAG retrieval error: {e}")
            return self._retrieve_market_context_fallback(location)
    
    def _retrieve_market_context_fallback(self, location: str = None) -> Dict:
        """Fallback retrieval when RAG unavailable"""
        if location and location in self.market_data:
            return {
                'market_insights': [
                    f"{location} market shows {self.market_data[location]['yoy_growth']*100:.0f}% YoY growth with "
                    f"{self.market_data[location]['avg_rental_yield']*100:.1f}% rental yield. "
                    f"Trend: {self.market_data[location]['appreciation_trend']}. "
                    f"Avg price: ₹{self.market_data[location]['avg_price_per_sqft']:.0f}/sqft"
                ],
                'comparable_properties': [],
                'retrieval_method': 'rule_based'
            }
        
        return {
            'market_insights': ['Market data available for major metros'],
            'comparable_properties': [],
            'retrieval_method': 'default'
        }
    
    def calculate_roi(self, investment_amount: float, location: str,
                     hold_period: int = 5, rental_income: float = None) -> Dict:
        """
        Calculate ROI based on historical market data
        
        Args:
            investment_amount: Initial property price
            location: Property location
            hold_period: Years to hold property (default 5)
            rental_income: Annual rental income (optional)
        
        Returns:
            Dict with ROI projections and breakdown
        """
        location = self._resolve_location(location)
        hold_period = self._sanitize_horizon(hold_period)
        investment_amount = max(100000.0, self._safe_float(investment_amount, 5000000.0))

        market_info = self.market_data[location]
        historical = self.historical_returns.get(location, {})

        growth_meta = self._effective_growth_rate(location)
        effective_growth = growth_meta['effective_growth_rate']

        rental_yield_decimal = self._safe_float(market_info.get('avg_rental_yield'), 0.06)

        # Basic ownership economics for more realistic outputs.
        vacancy_rate = 0.06
        rent_escalation = 0.04
        maintenance_rate = 0.015
        property_tax_rate = 0.002
        buy_cost_rate = 0.06
        sell_cost_rate = 0.02

        initial_buy_cost = investment_amount * buy_cost_rate
        total_invested = investment_amount + initial_buy_cost

        appreciation_value = investment_amount * ((1 + effective_growth) ** hold_period)
        sale_cost = appreciation_value * sell_cost_rate
        net_sale_proceeds = appreciation_value - sale_cost
        capital_gain = appreciation_value - investment_amount

        if rental_income is not None and self._safe_float(rental_income, 0) > 0:
            first_year_rent = self._safe_float(rental_income, investment_amount * rental_yield_decimal)
            effective_rental_yield = first_year_rent / investment_amount
        else:
            first_year_rent = investment_amount * rental_yield_decimal
            effective_rental_yield = rental_yield_decimal

        gross_rental_total = 0.0
        net_rental_total = 0.0
        for year in range(hold_period):
            year_rent = first_year_rent * ((1 + rent_escalation) ** year)
            gross_rental_total += year_rent

            occupied_rent = year_rent * (1 - vacancy_rate)
            maintenance_cost = investment_amount * maintenance_rate
            property_tax_cost = investment_amount * property_tax_rate
            net_rental_total += max(0.0, occupied_rent - maintenance_cost - property_tax_cost)

        gross_return_amount = capital_gain + gross_rental_total
        gross_roi_percentage = (gross_return_amount / investment_amount) * 100

        net_return_amount = (net_sale_proceeds + net_rental_total) - total_invested
        net_roi_percentage = (net_return_amount / total_invested) * 100

        gross_annualized_roi = ((((investment_amount + gross_return_amount) / investment_amount) ** (1 / hold_period)) - 1) * 100
        net_annualized_roi = ((((total_invested + net_return_amount) / total_invested) ** (1 / hold_period)) - 1) * 100

        annual_rate_decimal = effective_growth
        annual_rate_percent = annual_rate_decimal * 100
        
        return {
            'location': location,
            'investment_amount': investment_amount,
            'hold_period': hold_period,
            'capital_appreciation': {
                'annual_rate': annual_rate_decimal,
                'annual_rate_decimal': annual_rate_decimal,
                'annual_rate_percent': annual_rate_percent,
                'projected_value': appreciation_value,
                'total_gain': capital_gain,
                'gain_percentage': (capital_gain / investment_amount) * 100
            },
            'rental_income': {
                'annual_income': first_year_rent,
                'total_income': gross_rental_total,
                'net_total_income': net_rental_total,
                'yield_percentage': effective_rental_yield * 100,
                'vacancy_rate': vacancy_rate * 100,
                'rent_escalation': rent_escalation * 100
            },
            'cost_assumptions': {
                'buy_cost_pct': buy_cost_rate * 100,
                'sell_cost_pct': sell_cost_rate * 100,
                'maintenance_pct': maintenance_rate * 100,
                'property_tax_pct': property_tax_rate * 100
            },
            'total_return': {
                'amount': gross_return_amount,
                'percentage': gross_roi_percentage,
                'annualized_roi': gross_annualized_roi,
                'net_amount': net_return_amount,
                'net_percentage': net_roi_percentage,
                'net_annualized_roi': net_annualized_roi
            },
            'market_context': {
                'trend': market_info['appreciation_trend'],
                'demand_supply': {
                    'demand': market_info['demand_score'],
                    'supply': market_info['supply_score'],
                    'imbalance_factor': market_info['demand_score'] / market_info['supply_score']
                },
                'volatility': historical.get('volatility', 'moderate'),
                'growth_inputs': growth_meta
            },
            'sanity_checks': {
                'hold_period_valid': 1 <= hold_period <= 20,
                'net_leq_gross': net_roi_percentage <= gross_roi_percentage,
                'effective_growth_bounded': 0.02 <= annual_rate_decimal <= 0.20
            }
        }
    
    def simulate_scenarios(self, investment_amount: float, location: str,
                          hold_period: int = 5, base_roi_calc: Dict = None) -> Dict:
        """
        Simulate different market scenarios (bullish, moderate, bearish)
        """
        location = self._resolve_location(location)
        hold_period = self._sanitize_horizon(hold_period)

        base_roi = base_roi_calc or self.calculate_roi(investment_amount, location, hold_period=hold_period)
        base_rate = base_roi['capital_appreciation']['annual_rate_decimal']
        volatility = base_roi.get('market_context', {}).get('volatility', 'moderate')
        long_horizon = min(15, max(hold_period + 5, hold_period * 2))

        if 'low' in volatility:
            bullish_mult, bearish_mult = 1.2, 0.85
            probabilities = ('20-30%', '55-65%', '15-20%')
        elif 'high' in volatility:
            bullish_mult, bearish_mult = 1.4, 0.6
            probabilities = ('20-30%', '40-50%', '25-35%')
        else:
            bullish_mult, bearish_mult = 1.3, 0.75
            probabilities = ('25-35%', '45-55%', '20-30%')

        bullish_rate = max(0.02, min(0.24, base_rate * bullish_mult))
        bearish_rate = max(0.01, min(0.18, base_rate * bearish_mult))

        scenarios = {
            'bullish': {
                'probability': probabilities[0],
                'description': 'Strong market growth driven by infrastructure or economic factors',
                'appreciation_rate': bullish_rate,
                'roi_base_horizon': self._project_roi_for_rate(investment_amount, bullish_rate, hold_period, location),
                'roi_long_horizon': self._project_roi_for_rate(investment_amount, bullish_rate, long_horizon, location),
                'roi_5yr': self._project_roi_for_rate(investment_amount, bullish_rate, hold_period, location),
                'roi_10yr': self._project_roi_for_rate(investment_amount, bullish_rate, long_horizon, location),
                'factors': ['Economic boom', 'Infrastructure projects', 'Increased demand']
            },
            'moderate': {
                'probability': probabilities[1],
                'description': 'Normal market growth aligned with historical trends',
                'appreciation_rate': base_rate,
                'roi_base_horizon': self._project_roi_for_rate(investment_amount, base_rate, hold_period, location),
                'roi_long_horizon': self._project_roi_for_rate(investment_amount, base_rate, long_horizon, location),
                'roi_5yr': self._project_roi_for_rate(investment_amount, base_rate, hold_period, location),
                'roi_10yr': self._project_roi_for_rate(investment_amount, base_rate, long_horizon, location),
                'factors': ['Normal inflation', 'Steady demand', 'Standard market cycles']
            },
            'bearish': {
                'probability': probabilities[2],
                'description': 'Slower growth due to market corrections or externalities',
                'appreciation_rate': bearish_rate,
                'roi_base_horizon': self._project_roi_for_rate(investment_amount, bearish_rate, hold_period, location),
                'roi_long_horizon': self._project_roi_for_rate(investment_amount, bearish_rate, long_horizon, location),
                'roi_5yr': self._project_roi_for_rate(investment_amount, bearish_rate, hold_period, location),
                'roi_10yr': self._project_roi_for_rate(investment_amount, bearish_rate, long_horizon, location),
                'factors': ['Market correction', 'Reduced demand', 'External shocks']
            }
        }
        
        return {
            'location': location,
            'investment_amount': investment_amount,
            'horizon_years': hold_period,
            'long_horizon_years': long_horizon,
            'base_scenario': base_roi,
            'scenarios': scenarios,
            'recommendation': self._generate_scenario_recommendation(scenarios, hold_period)
        }
    
    def _project_roi_for_rate(self, investment: float, rate: float, years: int, location: str) -> float:
        """Project net ROI for a given growth rate and holding period."""
        years = self._sanitize_horizon(years)
        location = self._resolve_location(location)
        market_info = self.market_data[location]

        rental_yield = self._safe_float(market_info.get('avg_rental_yield'), 0.06)
        buy_cost_rate = 0.06
        sell_cost_rate = 0.02
        vacancy_rate = 0.06
        maintenance_rate = 0.015
        property_tax_rate = 0.002
        rent_escalation = 0.04

        first_year_rent = investment * rental_yield
        gross_rent = 0.0
        net_rent = 0.0
        for year in range(years):
            year_rent = first_year_rent * ((1 + rent_escalation) ** year)
            gross_rent += year_rent
            net_rent += max(0.0, year_rent * (1 - vacancy_rate) - (investment * (maintenance_rate + property_tax_rate)))

        final_value = investment * ((1 + rate) ** years)
        sale_proceeds = final_value * (1 - sell_cost_rate)
        total_invested = investment * (1 + buy_cost_rate)
        net_return = (sale_proceeds + net_rent) - total_invested

        roi = (net_return / total_invested) * 100
        return round(roi, 1)
    
    def _generate_scenario_recommendation(self, scenarios: Dict, hold_period: int) -> str:
        """Generate recommendation based on scenarios"""
        moderate_roi = scenarios['moderate']['roi_base_horizon']
        bearish_roi = scenarios['bearish']['roi_base_horizon']
        
        if moderate_roi > 40:
            return "Strong investment opportunity with good downside protection even in bearish scenarios"
        elif moderate_roi > 25:
            return "Good investment with reasonable returns across scenarios"
        elif bearish_roi > 10:
            return f"Moderate upside with resilient downside over a {hold_period}-year horizon"
        else:
            return "Conservative play - focus on long-term (10yr+) appreciation"
    
    def generate_investment_forecast(self, 
                                    property_details: Dict,
                                    investor_profile: Dict = None) -> Dict:
        """
        Generate comprehensive investment forecast with RAG context and ROI analysis
        
        Args:
            property_details: {price, location, bhk, size, amenities}
            investor_profile: {investment_horizon, risk_tolerance, preferences}
        
        Returns:
            Investment forecast with RAG context, ROI projections, and recommendations
        """
        location = property_details.get('location', 'Mumbai')
        price = max(100000.0, self._safe_float(property_details.get('price'), 5000000.0))
        bhk = int(self._safe_float(property_details.get('bhk'), 2))
        size = self._safe_float(property_details.get('size'), 1000.0)
        investor_profile = investor_profile or {}
        hold_period = self._sanitize_horizon(investor_profile.get('investment_horizon', 5))
        
        # Get market context via RAG
        query = f"{bhk} BHK property in {location} for investment"
        market_context = self.retrieve_market_context(query, location)
        
        # Calculate base ROI
        base_roi = self.calculate_roi(price, location, hold_period=hold_period)
        
        # Run scenario simulations
        scenarios = self.simulate_scenarios(price, location, hold_period=hold_period, base_roi_calc=base_roi)
        
        # Generate investment thesis
        thesis = self._generate_investment_thesis(
            property_details,
            base_roi,
            market_context,
            investor_profile
        )
        
        return {
            'property': {
                **property_details,
                'price': price,
                'bhk': bhk,
                'size': size
            },
            'market_context': market_context,
            'base_roi_analysis': base_roi,
            'scenario_analysis': scenarios,
            'investment_thesis': thesis,
            'retrieval_method': market_context.get('retrieval_method', 'default'),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_investment_thesis(self, 
                                   property_details: Dict,
                                   roi_analysis: Dict,
                                   market_context: Dict,
                                   investor_profile: Dict = None) -> str:
        """Generate detailed investment thesis"""
        location = property_details.get('location', 'Mumbai')
        bhk = property_details.get('bhk', 2)
        investor_profile = investor_profile or {}
        hold_period = self._sanitize_horizon(investor_profile.get('investment_horizon', roi_analysis.get('hold_period', 5)))
        roi_pct = roi_analysis['total_return']['net_annualized_roi']
        trend = roi_analysis['market_context']['trend']
        demand_supply_ratio = roi_analysis['market_context']['demand_supply']['imbalance_factor']
        growth_inputs = roi_analysis['market_context'].get('growth_inputs', {})
        news_signal = growth_inputs.get('news_signal', {})
        growth_effective = growth_inputs.get('effective_growth_rate', 0.0) * 100
        growth_base = growth_inputs.get('base_growth_rate', 0.0) * 100
        
        thesis = f"""
🎯 Investment Thesis - {bhk} BHK in {location}

Based on historical data and current market conditions:

📊 Market Context:
• Location: {location}
• Market Trend: {trend.replace('_', ' ').title()}
• Demand/Supply Ratio: {demand_supply_ratio:.2f}x
• {'Strong seller favored market' if demand_supply_ratio > 1 else 'Balanced market conditions'}

💰 ROI Forecast:
• Net Annualized ROI: {roi_pct:.1f}%
• {hold_period}-Year Projection: ₹{roi_analysis['capital_appreciation']['projected_value']:,.0f}
• Capital Appreciation: {roi_analysis['capital_appreciation']['gain_percentage']:.1f}%
• Average Rental Yield: {roi_analysis['rental_income']['yield_percentage']:.1f}%
• Growth Rate Used: {growth_effective:.2f}% (base {growth_base:.2f}% + news signal {news_signal.get('growth_adjustment', 0.0)*100:.2f}%)

✅ Key Strengths:
• Located in growing metropolis with consistent appreciation
• Diversified returns from both capital gains and rental income
• Strong fundamentals supported by market demand
• Tier-1 city with sustained economic growth drivers

⚠️ Risk Factors:
• Market volatility: {roi_analysis['market_context']['volatility']}
• Interest rate fluctuations may impact rental yields
• Initial illiquidity - typically 3-6 months to sell
• News signal is directional and bounded; it is not a deterministic predictor

🎬 Action Items:
1. Verify property title and legal documentation
2. Compare with similar properties in neighborhood
3. Validate rental income projections locally
4. Consider holding period of at least {hold_period} years
5. Include buying/selling costs, maintenance, and taxes in decisioning

💡 Bottom Line:
This property offers {'strong' if roi_pct > 25 else 'moderate'} investment potential with grounded projections based on {location} market history and recent market-news activity.
        """
        
        return thesis.strip()
