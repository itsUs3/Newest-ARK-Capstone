"""
LLM-based Recommendation Engine with Function Calling
Replaces rule-based recommendations with intelligent LLM generation
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import requests

import config

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

logger = logging.getLogger(__name__)


class LLMRecommendationEngine:
    """
    Advanced recommendation system using LLM with function calling
    Generates personalized property recommendations with explanations
    """

    def __init__(self, use_llm: bool = True):
        """
        Initialize LLM-based recommendation engine
        
        Args:
            use_llm: Whether to use LLM (fallback to rule-based if False or API unavailable)
        """
        self.use_llm = use_llm and config.GENAI_USE_LLM
        self.primary_provider = config.GENAI_PRIMARY_PROVIDER

        self.ollama_enabled = config.OLLAMA_ENABLED
        self.ollama_base_url = config.OLLAMA_BASE_URL.rstrip("/")
        self.ollama_model = config.OLLAMA_MODEL
        self.ollama_timeout = config.OLLAMA_TIMEOUT_SECONDS

        self.api_key = config.OPENAI_API_KEY
        self.model = config.GENAI_MODEL or config.OPENAI_MODEL
        self.client = None
        
        # Initialize OpenAI backup client
        if self.use_llm and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI backup client: {e}")

        if self.use_llm and not self.ollama_enabled and not self.client:
            logger.warning("No LLM provider available (Ollama disabled and OpenAI unavailable). Using fallback mode.")
            self.use_llm = False
        
        # Load property data
        self.listings = self._load_listings()
        
        # Define function tools for LLM
        self.tools = self._define_tools()

    def _load_listings(self) -> List[Dict]:
        """Load property listings from CSV"""
        try:
            df = pd.read_csv(config.DATA_PATH)
            listings = []
            
            for idx, row in df.iterrows():
                title = row.get('title2', 'Unknown Property')
                location = str(title).split('in ')[-1] if 'in' in str(title) else 'Mumbai'
                
                listing = {
                    'id': f"property_{idx}",
                    'title': row.get('title', 'Property'),
                    'location': location,
                    'bhk': self._extract_bhk(str(title)),
                    'price': row.get('price', 0) if 'price' in row else None,
                    'size': row.get('size', 0) if 'size' in row else None,
                    'amenities': self._extract_amenities(str(title)),
                    'rating': row.get('rating', 3.5) if 'rating' in row else 3.5,
                    'description': title,
                }
                listings.append(listing)
            
            return listings if listings else self._get_default_listings()
        except Exception as e:
            logger.warning(f"Error loading listings: {e}")
            return self._get_default_listings()

    def _extract_bhk(self, text: str) -> int:
        """Extract BHK from text"""
        if '3 BHK' in text:
            return 3
        elif '2 BHK' in text:
            return 2
        elif '1 BHK' in text:
            return 1
        return 2

    def _extract_amenities(self, text: str) -> List[str]:
        """Extract amenities from text"""
        amenities = []
        amenity_keywords = {
            'gym': ['gym', 'fitness', 'health'],
            'pool': ['swimming', 'pool', 'aqua'],
            'parking': ['parking', 'garage', 'carport'],
            'garden': ['garden', 'landscaped', 'green'],
            'security': ['24/7 security', 'gated', 'secure'],
            'lift': ['elevator', 'lift'],
            'playground': ['playground', 'play area'],
            'clubhouse': ['clubhouse', 'club']
        }
        
        text_lower = text.lower()
        for amenity, keywords in amenity_keywords.items():
            if any(kw in text_lower for kw in keywords):
                amenities.append(amenity)
        
        return amenities if amenities else ['basic']

    def _get_default_listings(self) -> List[Dict]:
        """Return default listings"""
        locations = ['Mumbai', 'Bangalore', 'Delhi', 'Pune', 'Hyderabad']
        
        listings = []
        for i in range(20):
            listings.append({
                'id': f'property_{i}',
                'title': f'Premium {(i%3)+1} BHK Property {i}',
                'location': locations[i % 5],
                'bhk': (i % 3) + 1,
                'price': (30 + i*15) * 100000,
                'size': 600 + i*80,
                'amenities': ['gym', 'parking', 'security'] if i % 2 else ['pool', 'garden'],
                'rating': 3.5 + (i % 15) * 0.1,
                'description': f'Beautiful {(i%3)+1} BHK apartment in {locations[i%5]}'
            })
        return listings

    def _define_tools(self) -> List[Dict]:
        """Define function calling tools for LLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_properties",
                    "description": "Search for properties matching user criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Target location/city"
                            },
                            "min_bhk": {
                                "type": "integer",
                                "description": "Minimum number of bedrooms"
                            },
                            "max_bhk": {
                                "type": "integer",
                                "description": "Maximum number of bedrooms"
                            },
                            "min_price": {
                                "type": "number",
                                "description": "Minimum budget in INR"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum budget in INR"
                            },
                            "required_amenities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of required amenities"
                            }
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_property_details",
                    "description": "Get detailed information about a specific property",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "property_id": {
                                "type": "string",
                                "description": "The property ID"
                            }
                        },
                        "required": ["property_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_location_insights",
                    "description": "Get market insights and trends for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "Target location"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ]

    def _process_tool_call(self, tool_name: str, tool_input: Dict) -> str:
        """Process function calls from LLM"""
        try:
            if tool_name == "search_properties":
                return self._search_properties_impl(tool_input)
            elif tool_name == "get_property_details":
                return self._get_property_details_impl(tool_input)
            elif tool_name == "get_location_insights":
                return self._get_location_insights_impl(tool_input)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return json.dumps({"error": str(e)})

    def _search_properties_impl(self, params: Dict) -> str:
        """Search properties implementation"""
        location = params.get("location", "").lower()
        min_bhk = params.get("min_bhk", 1)
        max_bhk = params.get("max_bhk", 5)
        min_price = params.get("min_price", 0)
        max_price = params.get("max_price", float('inf'))
        required_amenities = params.get("required_amenities", [])
        
        results = []
        for listing in self.listings:
            # Filter by location
            if location and location not in listing['location'].lower():
                continue
            
            # Filter by BHK
            if not (min_bhk <= listing['bhk'] <= max_bhk):
                continue
            
            # Filter by price
            price = listing.get('price', 0) or float('inf')
            if price < min_price or price > max_price:
                continue
            
            # Filter by amenities
            if required_amenities:
                if not any(am in listing['amenities'] for am in required_amenities):
                    continue
            
            results.append({
                'id': listing['id'],
                'location': listing['location'],
                'bhk': listing['bhk'],
                'price': listing['price'],
                'rating': listing['rating']
            })
        
        return json.dumps({
            "count": len(results),
            "properties": results[:10]  # Return top 10
        })

    def _get_property_details_impl(self, params: Dict) -> str:
        """Get property details implementation"""
        property_id = params.get("property_id")
        
        for listing in self.listings:
            if listing['id'] == property_id:
                return json.dumps({
                    "property": listing,
                    "found": True
                })
        
        return json.dumps({"found": False, "error": "Property not found"})

    def _get_location_insights_impl(self, params: Dict) -> str:
        """Get location insights implementation"""
        location = params.get("location", "Unknown")
        
        # Generate insights based on available data
        matching_properties = [p for p in self.listings if location.lower() in p['location'].lower()]
        
        if matching_properties:
            avg_price = sum(p.get('price', 0) for p in matching_properties) / len(matching_properties)
            avg_rating = sum(p.get('rating', 0) for p in matching_properties) / len(matching_properties)
            
            return json.dumps({
                "location": location,
                "property_count": len(matching_properties),
                "avg_price": avg_price,
                "avg_rating": avg_rating,
                "insights": [
                    f"High demand area with {len(matching_properties)} active listings",
                    f"Average price: ₹{avg_price/100000:.1f}L",
                    f"Community rating: {avg_rating:.1f}/5"
                ]
            })
        
        return json.dumps({
            "location": location,
            "property_count": 0,
            "insights": [f"Limited data available for {location}"]
        })

    def generate_recommendations_with_llm(
        self,
        user_preferences: Dict,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized recommendations using LLM with function calling
        
        Args:
            user_preferences: User's preferences (budget, location, bhk, amenities, etc.)
            context: Additional context or conversation history
        
        Returns:
            Dict with recommendations and explanations
        """
        if not self.use_llm:
            return self._fallback_recommendations(user_preferences)
        
        try:
            # Build preference and candidate context for LLM synthesis
            prefs_str = "\n".join([f"- {k}: {v}" for k, v in user_preferences.items()])
            candidates = self._candidate_properties(user_preferences, top_k=10)
            candidates_str = "\n".join(
                [
                    f"- {p['id']}: {p['title']} | {p['location']} | {p['bhk']} BHK | "
                    f"Price: {self._format_price(p.get('price'))} | Amenities: {', '.join(p.get('amenities', []))} | "
                    f"Rating: {p.get('rating', 0):.1f}/5"
                    for p in candidates
                ]
            ) or "- No strong candidates found from structured filters"
            
            system_prompt = """You are an expert Indian real estate consultant.
Use the provided candidate properties and user preferences to produce practical recommendations.
Do not invent properties that are not present in the candidate list."""
            
            user_message = f"""Based on these user preferences:
{prefs_str}

Candidate properties:
{candidates_str}

Please provide top 3 recommendations with short reasons, trade-offs, and one clear final suggestion."""
            
            if context:
                user_message += f"\n\nAdditional context: {context}"

            final_content = self._generate_text(system_prompt, user_message)
            if not final_content:
                return self._fallback_recommendations(user_preferences)

            return {
                "success": True,
                "recommendations": final_content,
                "method": self.primary_provider,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"LLM recommendation error: {e}")
            return self._fallback_recommendations(user_preferences)

    def _candidate_properties(self, preferences: Dict, top_k: int = 10) -> List[Dict]:
        location = str(preferences.get('location', '') or '').lower()
        bhk = int(preferences.get('bhk', 0) or 0)
        budget_min = float(preferences.get('budget_min', 0) or 0)
        budget_max = float(preferences.get('budget_max', float('inf')) or float('inf'))

        filtered = []
        for prop in self.listings:
            if location and location not in str(prop.get('location', '')).lower():
                continue
            if bhk and int(prop.get('bhk', 0) or 0) != bhk:
                continue
            price = float(prop.get('price', 0) or 0)
            if price and (price < budget_min or price > budget_max):
                continue
            filtered.append(prop)

        filtered.sort(key=lambda x: x.get('rating', 0), reverse=True)
        return filtered[:top_k]

    def _format_price(self, price: Optional[float]) -> str:
        if not price:
            return "N/A"
        if price >= 10000000:
            return f"₹{price / 10000000:.2f} Cr"
        return f"₹{price / 100000:.2f} L"

    def _generate_text(self, system_prompt: str, user_message: str) -> str:
        providers = [self.primary_provider, "openai" if self.primary_provider == "ollama" else "ollama"]

        for provider in providers:
            try:
                if provider == "ollama":
                    if not self.ollama_enabled:
                        continue
                    payload = {
                        "model": self.ollama_model,
                        "prompt": f"{system_prompt}\n\n{user_message}",
                        "stream": False,
                        "options": {"temperature": 0.35, "num_predict": 600},
                    }
                    res = requests.post(
                        f"{self.ollama_base_url}/api/generate",
                        json=payload,
                        timeout=self.ollama_timeout,
                    )
                    res.raise_for_status()
                    content = (res.json().get("response") or "").strip()
                else:
                    if not self.client:
                        continue
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        temperature=0.35,
                        max_tokens=600,
                    )
                    content = (response.choices[0].message.content or "").strip() if response and response.choices else ""

                if content:
                    return content
            except Exception as exc:
                logger.warning("Provider %s failed, trying fallback: %s", provider, exc)

        return ""

    def _fallback_recommendations(self, user_preferences: Dict) -> Dict[str, Any]:
        """Fallback to rule-based recommendations"""
        location = user_preferences.get('location', '')
        bhk = user_preferences.get('bhk', 2)
        max_budget = user_preferences.get('budget_max', float('inf'))
        amenities = user_preferences.get('amenities', [])
        
        # Simple rule-based filtering
        filtered = []
        for listing in self.listings:
            if location and location.lower() not in listing['location'].lower():
                continue
            if listing['bhk'] != bhk:
                continue
            if listing.get('price', 0) and listing['price'] > max_budget:
                continue
            filtered.append(listing)
        
        # Score and sort
        scored = []
        for prop in filtered:
            score = prop.get('rating', 3.5) * 20
            if amenities:
                matching = len(set(prop['amenities']) & set(amenities))
                score += matching * 10
            scored.append((prop, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        top_3 = scored[:3]
        
        recommendation_text = "Based on your preferences:\n\n"
        for i, (prop, score) in enumerate(top_3, 1):
            recommendation_text += f"{i}. {prop['title']} in {prop['location']}\n"
            recommendation_text += f"   - BHK: {prop['bhk']}, Price: ₹{prop['price']/100000:.1f}L\n"
            recommendation_text += f"   - Amenities: {', '.join(prop['amenities'])}\n"
            recommendation_text += f"   - Rating: {prop['rating']:.1f}/5\n\n"
        
        return {
            "success": True,
            "recommendations": recommendation_text,
            "method": "fallback_rule_based",
            "timestamp": datetime.now().isoformat()
        }

    def get_recommendations(self, preferences: Dict) -> List[Dict]:
        """
        Public API for getting recommendations
        Returns both LLM-generated insights and structured recommendation list
        """
        # Get LLM recommendations if available
        llm_result = self.generate_recommendations_with_llm(preferences)
        
        # Also get structured list for API compatibility
        location = preferences.get('location', '')
        bhk = preferences.get('bhk', 2)
        max_budget = preferences.get('budget_max', float('inf'))
        
        filtered = [
            prop for prop in self.listings
            if (not location or location.lower() in prop['location'].lower()) and
               prop['bhk'] == bhk and
               (not prop.get('price') or prop['price'] <= max_budget)
        ]
        
        filtered.sort(key=lambda x: x.get('rating', 0), reverse=True)
        
        # Add LLM insight to each recommendation
        for prop in filtered[:5]:
            prop['llm_insight'] = llm_result.get('recommendations', '')
        
        return filtered[:5]
