import os
import re
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
import requests
import config

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

logger = logging.getLogger(__name__)

class GenAIHandler:
    """
    Generative AI components using LLM APIs
    Handles descriptions, price explanations, and chatbot interactions
    """
    
    def __init__(self):
        self.model = os.getenv("GENAI_MODEL", os.getenv("OPENAI_MODEL", config.GENAI_MODEL))
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()

        self.use_llm = os.getenv("GENAI_USE_LLM", str(config.GENAI_USE_LLM).lower()).lower() == "true"
        self.primary_provider = os.getenv("GENAI_PRIMARY_PROVIDER", config.GENAI_PRIMARY_PROVIDER).lower()

        self.ollama_enabled = os.getenv("OLLAMA_ENABLED", str(config.OLLAMA_ENABLED).lower()).lower() == "true"
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", config.OLLAMA_BASE_URL).rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", config.OLLAMA_MODEL)
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", str(config.OLLAMA_TIMEOUT_SECONDS)))

        self.temperature_default = float(os.getenv("GENAI_TEMPERATURE", str(config.GENAI_TEMPERATURE)))
        self.temperature_by_task = {
            "description": float(os.getenv("GENAI_TEMPERATURE_DESCRIPTION", str(config.GENAI_TEMPERATURE_DESCRIPTION))),
            "explain": float(os.getenv("GENAI_TEMPERATURE_EXPLAIN", str(config.GENAI_TEMPERATURE_EXPLAIN))),
            "explain_price": float(os.getenv("GENAI_TEMPERATURE_EXPLAIN", str(config.GENAI_TEMPERATURE_EXPLAIN))),
            "chat": float(os.getenv("GENAI_TEMPERATURE_CHAT", str(config.GENAI_TEMPERATURE_CHAT))),
            "landmark": float(os.getenv("GENAI_TEMPERATURE_LANDMARK", str(config.GENAI_TEMPERATURE_LANDMARK))),
            "landmark_report": float(os.getenv("GENAI_TEMPERATURE_LANDMARK", str(config.GENAI_TEMPERATURE_LANDMARK))),
        }

        self.max_input_tokens = int(os.getenv("GENAI_MAX_INPUT_TOKENS", str(config.GENAI_MAX_INPUT_TOKENS)))
        self.max_output_tokens = int(os.getenv("GENAI_MAX_OUTPUT_TOKENS", str(config.GENAI_MAX_OUTPUT_TOKENS)))
        self.max_response_chars = int(os.getenv("GENAI_MAX_RESPONSE_CHARS", str(config.GENAI_MAX_RESPONSE_CHARS)))

        self.client = None
        self.investment_advisor = None
        if self.use_llm:
            if self.api_key and OpenAI is not None:
                try:
                    self.client = OpenAI(api_key=self.api_key)
                except Exception as exc:
                    logger.warning(f"Failed to initialize OpenAI backup client: {exc}")

            if not self.ollama_enabled and not self.client:
                logger.warning("No LLM provider available (Ollama disabled and OpenAI unavailable). Falling back to rule-based outputs.")
                self.use_llm = False

        try:
            from models.investment_advisor import InvestmentAdvisor
            self.investment_advisor = InvestmentAdvisor()
        except Exception as exc:
            logger.warning(f"Investment advisor initialization failed: {exc}")

    def _clamp_temperature(self, value: float) -> float:
        return max(0.0, min(1.5, float(value)))

    def _get_temperature(self, task: str) -> float:
        configured = self.temperature_by_task.get(task, self.temperature_default)
        return self._clamp_temperature(configured)

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _truncate_to_token_budget(self, text: str, token_budget: int) -> str:
        if token_budget <= 0:
            return ""

        if self._estimate_tokens(text) <= token_budget:
            return text

        words = text.split()
        if not words:
            return text

        approx_words = max(1, token_budget * 3 // 4)
        truncated = " ".join(words[:approx_words]).strip()
        if truncated and not truncated.endswith("..."):
            truncated += " ..."
        return truncated

    def _normalize_output(self, text: str) -> str:
        normalized = (text or "").strip()
        if len(normalized) <= self.max_response_chars:
            return normalized
        return normalized[: self.max_response_chars - 4].rstrip() + " ..."

    def _build_grounded_prompt(self, instruction: str, context_chunks: Optional[List[str]] = None) -> str:
        context_chunks = context_chunks or []

        context_header = (
            "Use only the facts from CONTEXT. If information is missing, explicitly say data is unavailable. "
            "Do not invent numbers, legal claims, or guarantees."
        )

        context_text = "\n\n".join(
            f"- {chunk.strip()}" for chunk in context_chunks if chunk and chunk.strip()
        )
        full_prompt = (
            f"{context_header}\n\n"
            f"CONTEXT:\n{context_text if context_text else '- No structured context provided'}\n\n"
            f"TASK:\n{instruction.strip()}"
        )

        return self._truncate_to_token_budget(full_prompt, self.max_input_tokens)

    def _is_grounded_response(self, response: str, context_chunks: Optional[List[str]]) -> bool:
        if not context_chunks:
            return True

        response_tokens = set(re.findall(r"[a-zA-Z]{4,}", (response or "").lower()))
        context_tokens = set(re.findall(r"[a-zA-Z]{4,}", " ".join(context_chunks).lower()))

        if not response_tokens or not context_tokens:
            return False

        overlap = len(response_tokens.intersection(context_tokens)) / max(1, len(response_tokens))
        risky_phrases = ["guaranteed", "always", "definitely", "100%", "assured return"]
        has_risky_phrase = any(phrase in (response or "").lower() for phrase in risky_phrases)

        if has_risky_phrase and overlap < 0.20:
            return False

        return overlap >= 0.08

    def _generate_with_guardrails(
        self,
        task: str,
        instruction: str,
        fallback_text: str,
        context_chunks: Optional[List[str]] = None,
        verify_grounding: bool = True,
    ) -> str:
        if not self.use_llm:
            return self._normalize_output(fallback_text)

        prompt = self._build_grounded_prompt(instruction, context_chunks)
        system_prompt = (
            "You are a careful Indian real-estate assistant. "
            "Stay factual, concise, and transparent about uncertainty."
        )

        providers = [self.primary_provider, "openai" if self.primary_provider == "ollama" else "ollama"]

        for provider in providers:
            try:
                if provider == "ollama":
                    if not self.ollama_enabled:
                        continue

                    content = self._call_ollama(system_prompt, prompt, self._get_temperature(task))
                else:
                    if not self.client:
                        continue

                    content = self._call_openai(system_prompt, prompt, self._get_temperature(task))

                if not content:
                    continue

                if verify_grounding and not self._is_grounded_response(content, context_chunks):
                    logger.warning("Grounding check failed for provider %s", provider)
                    continue

                return self._normalize_output(content)

            except Exception as exc:
                logger.warning("Provider %s failed, trying fallback: %s", provider, exc)

        return self._normalize_output(fallback_text)

    def _call_openai(self, system_prompt: str, prompt: str, temperature: float) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=self.max_output_tokens,
        )
        if response and response.choices:
            return (response.choices[0].message.content or "").strip()
        return ""

    def _call_ollama(self, system_prompt: str, prompt: str, temperature: float) -> str:
        payload = {
            "model": self.ollama_model,
            "prompt": f"{system_prompt}\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": self.max_output_tokens,
            },
        }
        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=self.ollama_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return (data.get("response") or "").strip()
    
    def generate_description(self, title: str, location: str, bhk: int = None, 
                            size: float = None, amenities: List[str] = None) -> str:
        """
        Generate an improved property listing description
        
        Returns:
            Enhanced description string
        """
        try:
            amenities_str = ", ".join(amenities) if amenities else "basic amenities"
            fallback_description = f"""🏡 Stunning {bhk} BHK Property in {location}
            
Experience luxury living in this {size:.0f} sq ft spacious apartment. Perfect blend of modern architecture and premium amenities.

✨ Features:
• Spacious {bhk} bedrooms with natural light
• {size:.0f} sq ft well-designed layout
• {amenities_str}
• Prime {location} location
• High security with 24/7 surveillance

📍 Location Advantages:
• Near metro stations and shopping centers
• Excellent schools and hospitals nearby
• Good connectivity to business districts
• Green surroundings

Perfect for families and professionals looking for comfort and convenience!"""

            instruction = (
                f"Generate a compelling listing description for a {bhk} BHK property in {location}. "
                f"Size: {size} sq ft. Amenities: {amenities_str}. "
                "Use only provided details. Keep under 150 words and avoid unverifiable claims."
            )

            context = [
                f"Title: {title}",
                f"Location: {location}",
                f"BHK: {bhk}",
                f"Size sq ft: {size}",
                f"Amenities: {amenities_str}",
            ]

            return self._generate_with_guardrails(
                task="description",
                instruction=instruction,
                fallback_text=fallback_description,
                context_chunks=context,
                verify_grounding=True,
            )
        
        except Exception as e:
            amenities_str = ", ".join(amenities) if amenities else "basic amenities"
            return f"Well-located {bhk} BHK property in {location} with {amenities_str}. {size:.0f} sq ft. Prime location with excellent connectivity."
    
    def explain_price(self, features: Dict) -> str:
        """
        Explain why a property is priced at a certain level
        
        Args:
            features: Dict with property features
        
        Returns:
            Simple explanation of price factors
        """
        try:
            location = features.get('location', 'this area')
            bhk = features.get('bhk', 2)
            size = features.get('size', 1000)
            amenities = features.get('amenities', [])
            
            explanation = f"""💰 Here's why the price makes sense:

• **Location**: {location} is 🔥 - great connectivity and vibe
• **Size**: {size:.0f} sq ft = plenty of space to flex 
• **{bhk} BHK**: More bedrooms = more value
• **Amenities**: {', '.join(amenities) if amenities else 'Basic but solid'}

The market rate for similar properties is pretty consistent. This one's fairly priced! 🎯"""

            instruction = (
                f"Explain pricing in simple language for a {bhk} BHK property in {location}, "
                f"size {size} sq ft, amenities {amenities}. Keep it under 100 words. "
                "Do not fabricate exact market numbers beyond provided context."
            )

            context = [
                f"Location: {location}",
                f"BHK: {bhk}",
                f"Size sq ft: {size}",
                f"Amenities: {', '.join(amenities) if amenities else 'Basic amenities'}",
            ]

            return self._generate_with_guardrails(
                task="explain_price",
                instruction=instruction,
                fallback_text=explanation,
                context_chunks=context,
                verify_grounding=True,
            )
        
        except Exception as e:
            return "This property is competitively priced based on current market trends in the location."
    
    def chat(self, message: str) -> str:
        """
        Chat with property advisor AI
        
        Args:
            message: User's question or message
        
        Returns:
            AI response about properties/real estate
        """
        try:
            message_lower = message.lower()
            
            # Simple intent matching for demo
            if any(word in message_lower for word in ['price', 'cost', 'expensive']):
                return """💡 Price Questions:
- Properties in Mumbai average ₹1.5-3 Cr depending on location
- Bangalore: ₹50-200L for decent 2-3 BHK
- Delhi NCR: ₹60-250L range is common
- Pro tip: Check 3-5 similar properties to gauge fair value! 📊"""
            
            elif any(word in message_lower for word in ['location', 'area', 'neighborhood']):
                return """🌍 Location Insights:
- Mumbai: Premium pricing, great connectivity
- Bangalore: Tech hub, growing rapidly
- Pune: Emerging hotspot, good value
- Hyderabad: Up-and-coming, affordable

Want recommendations for a specific area? 🏙️"""
            
            elif any(word in message_lower for word in ['buy', 'purchase', 'invest']):
                return """🏠 Buying Guide:
1. Check multiple platforms (MagicBricks, 99acres, Housing.com)
2. Verify RERA registration
3. Get property inspected
4. Check for duplicates/fraud listings
5. Negotiate 10-15% below asking price
6. Use our price predictor tool! 🔍

Need help with anything specific?"""
            
            elif any(word in message_lower for word in ['fraud', 'fake', 'scam', 'duplicate']):
                return """🚨 Fraud Detection Tips:
- Check trust score on our platform
- Verify seller details
- Avoid payment methods like Western Union/Crypto
- Look for inconsistencies in photos
- Check if property appears on multiple sites with different prices

Our AI analyzes listings for fraud indicators! 🛡️"""
            
            else:
                fallback_chat = """👋 Hey! I'm your property advisor. Ask me about:
- 💰 Prices & fair value estimates
- 🏠 Location recommendations
- 🔍 Fraud detection & duplicates  
- 📊 Market trends & analysis
- 🎯 Finding the perfect property

What would you like to know? 🤔"""

                instruction = (
                    f"User asked: {message}. Provide concise property-advisor guidance for India. "
                    "If exact local data is unavailable, be explicit and suggest next steps."
                )

                return self._generate_with_guardrails(
                    task="chat",
                    instruction=instruction,
                    fallback_text=fallback_chat,
                    context_chunks=[],
                    verify_grounding=False,
                )
        
        except Exception as e:
            return "Let me help you with real estate questions! What would you like to know?"
    
    def summarize_listing(self, listing_details: Dict) -> str:
        """
        Create a concise summary of a property listing
        """
        title = listing_details.get('title', 'Property')
        location = listing_details.get('location', 'Unknown')
        price = listing_details.get('price', 0)
        bhk = listing_details.get('bhk', '1-2')
        size = listing_details.get('size', 'Unknown')
        
        price_in_cr = price / 10000000 if price > 100 else price / 100000
        price_format = f"₹{price_in_cr:.1f} Cr" if price > 10000000 else f"₹{price_in_cr:.1f} L"
        
        return f"""📍 {title}
Location: {location}
💰 Price: {price_format}
🛏️ {bhk} BHK | 📐 {size:.0f} sq ft

Quick view summary! 👆"""
    
    def generate_landmark_insights(self, location: str, landmark_categories: Dict, 
                                  properties_count: int = 0) -> Dict:
        """
        Generate GenAI-powered insights for landmarks and neighborhood suitability.
        Uses Claude API for enriched analysis; falls back to rule-based generation.
        
        Args:
            location: The neighborhood/location being analyzed
            landmark_categories: Dict of {category_name: {"places": [...]}}
            properties_count: Number of properties analyzed from dataset
        
        Returns:
            Dict with 'insights', 'commute_estimates', 'family_score', 'connectivity_score'
        """
        try:
            # Extract key landmarks
            schools = landmark_categories.get('Schools & Education', {}).get('places', [])
            hospitals = landmark_categories.get('Hospitals & Healthcare', {}).get('places', [])
            transit = landmark_categories.get('Transit & Connectivity', {}).get('places', [])
            malls = landmark_categories.get('Malls & Shopping', {}).get('places', [])
            restaurants = landmark_categories.get('Restaurants & Food', {}).get('places', [])
            
            # Build a concise landmark list for the prompt
            landmarks_text = f"""Location: {location}
Dataset Coverage: {properties_count} properties analyzed

Nearby Schools: {', '.join(schools[:3]) if schools else 'Not available in dataset'}
Hospitals: {', '.join(hospitals[:3]) if hospitals else 'Not available in dataset'}
Transit (Metro/Bus): {', '.join(transit[:3]) if transit else 'Not available in dataset'}
Shopping Malls: {', '.join(malls[:2]) if malls else 'Not available in dataset'}
Restaurants/Food: {', '.join(restaurants[:3]) if restaurants else 'Not available in dataset'}"""

            # Build intelligent prompt for GenAI
            prompt = f"""You are an expert Indian real estate advisor. Analyze this neighborhood and provide insights:

{landmarks_text}

Generate a brief but insightful neighborhood analysis covering:
1. **Family Suitability** (score 1-10): Based on schools, hospitals, parks, safety perception
2. **Connectivity Score** (score 1-10): Based on transit options, proximity to major hubs
3. **Lifestyle Analysis**: What type of residents would thrive here?
4. **Commute Estimates**: Approximate times to common Mumbai/Bangalore/Pune hubs (e.g., airport, business district)
5. **Key Strengths**: 2-3 standout features of this neighborhood

Keep the tone conversational and India-specific. Be honest about any gaps in the data."""

            insights = self._generate_landmark_insights_rule_based(
                location, landmark_categories, schools, hospitals, transit, malls
            )

            llm_insights = self._generate_with_guardrails(
                task="landmark_report",
                instruction=prompt,
                fallback_text=insights.get("insights", ""),
                context_chunks=[landmarks_text],
                verify_grounding=True,
            )
            if llm_insights:
                insights["insights"] = llm_insights
            
            return insights
        
        except Exception as e:
            # Fallback to basic insights
            return self._generate_landmark_insights_rule_based(
                location, landmark_categories, None, None, None, None
            )
    
    def _generate_landmark_insights_rule_based(self, location: str, categories: Dict,
                                               schools: List = None, hospitals: List = None,
                                               transit: List = None, malls: List = None) -> Dict:
        """
        Rule-based fallback for landmark insights when GenAI API is unavailable.
        Provides structured analysis without external API calls.
        """
        schools = schools or categories.get('Schools & Education', {}).get('places', [])
        hospitals = hospitals or categories.get('Hospitals & Healthcare', {}).get('places', [])
        transit = transit or categories.get('Transit & Connectivity', {}).get('places', [])
        malls = malls or categories.get('Malls & Shopping', {}).get('places', [])
        stores = categories.get('Supermarkets & Stores', {}).get('places', [])
        parks = categories.get('Parks & Recreation', {}).get('places', [])
        
        # Enhanced scoring algorithm with stronger differentiation:
        # - diminishing returns for very high counts
        # - category-balance penalties when a critical category is missing
        # - city-specific priors for practical realism
        import math
        
        def calculate_amenity_score(count, max_score, saturation_point=10):
            """Calculate score with diminishing returns - more realistic differentiation"""
            if count == 0:
                return 0
            # Logarithmic curve: score = max_score * log(1 + count) / log(1 + saturation_point)
            normalized = min(count, saturation_point * 2)  # Cap at 2x saturation
            return max_score * (math.log(1 + normalized) / math.log(1 + saturation_point))
        
        # Family suitability score (weighted by importance)
        school_score = calculate_amenity_score(len(schools), 3.5, saturation_point=8)
        hospital_score = calculate_amenity_score(len(hospitals), 3.5, saturation_point=6)
        park_score = calculate_amenity_score(len(parks), 2.0, saturation_point=5)
        store_score = calculate_amenity_score(len(stores), 1.0, saturation_point=10)

        family_score = school_score + hospital_score + park_score + store_score

        # Penalize missing critical family infra
        if len(schools) == 0:
            family_score -= 1.1
        if len(hospitals) == 0:
            family_score -= 1.1
        if len(parks) == 0:
            family_score -= 0.6

        # Coverage bonus for balanced infra
        family_coverage = sum([len(schools) > 0, len(hospitals) > 0, len(parks) > 0, len(stores) > 0])
        family_score += (family_coverage - 2) * 0.35

        family_score = min(10, max(1, family_score))
        
        # Connectivity score (weighted by importance)
        transit_score = calculate_amenity_score(len(transit), 5.0, saturation_point=8)
        mall_score = calculate_amenity_score(len(malls), 3.0, saturation_point=4)
        
        # Diversity bonus - more category types = better connectivity
        diversity_bonus = min(2.0, len([c for c in categories.values() if c.get('places')]) * 0.3)
        
        connectivity_score = transit_score + mall_score + diversity_bonus

        # Penalize weak transit heavily
        if len(transit) == 0:
            connectivity_score -= 1.4
        elif len(transit) <= 2:
            connectivity_score -= 0.6

        # City priors to avoid clustered near-identical scores
        loc = location.lower()
        city_prior = 0.0
        if any(x in loc for x in ["mumbai", "andheri", "bandra", "powai", "worli", "thane", "navi mumbai"]):
            city_prior += 0.45
        elif any(x in loc for x in ["pune", "hinjewadi", "baner", "wakad"]):
            city_prior += 0.25
        elif any(x in loc for x in ["bangalore", "bengaluru", "whitefield", "koramangala", "electronic city"]):
            city_prior += 0.30
        elif any(x in loc for x in ["chennai", "omr", "velachery"]):
            city_prior += 0.15

        connectivity_score += city_prior
        connectivity_score = min(10, max(1, connectivity_score))
        
        # Commute estimates (dynamic by connectivity score)
        if connectivity_score >= 8.5:
            commute_estimates = {
                "airport": "15-25 mins (metro/cab)",
                "business_district": "10-20 mins (off-peak)",
                "railway_station": "8-15 mins",
                "highway": "10-20 mins"
            }
        elif connectivity_score >= 7:
            commute_estimates = {
                "airport": "20-35 mins (metro/cab)",
                "business_district": "15-30 mins (traffic-dependent)",
                "railway_station": "10-20 mins",
                "highway": "15-30 mins"
            }
        else:
            commute_estimates = {
                "airport": "30-50 mins (cab)",
                "business_district": "25-45 mins (traffic-dependent)",
                "railway_station": "20-35 mins",
                "highway": "25-40 mins"
            }
        
        # Family suitability verdict
        if family_score >= 8:
            family_verdict = "🟢 Excellent for families with schools, healthcare, and recreational facilities nearby"
        elif family_score >= 6:
            family_verdict = "🟡 Good for families with reasonable access to schools and hospitals"
        else:
            family_verdict = "🔵 Moderate family-friendliness; some amenities may require travel"
        
        # Connectivity verdict
        if connectivity_score >= 8:
            connectivity_verdict = "🟢 Highly connected with excellent public transport options"
        elif connectivity_score >= 6:
            connectivity_verdict = "🟡 Well-connected with decent transport and amenities"
        else:
            connectivity_verdict = "🔵 Moderate connectivity; personal transport recommended"
        
        # Lifestyle recommendations
        if family_score >= 7 and connectivity_score >= 7:
            lifestyle = "Perfect for young families seeking balance between suburban calm and urban connectivity"
        elif connectivity_score >= 8:
            lifestyle = "Ideal for working professionals who prioritize easy commutes and lifestyle amenities"
        elif family_score >= 7:
            lifestyle = "Great for families who value education and healthcare access over nightlife"
        else:
            lifestyle = "Suitable for those looking for a quieter residential experience"
        
        # Format amenity counts for transparency
        school_count = len(schools)
        hospital_count = len(hospitals)
        park_count = len(parks)
        transit_count = len(transit)
        mall_count = len(malls)
        store_count = len(stores)
        
        insights_text = f"""🏘️ **Neighborhood Deep Dive: {location}**

👨‍👩‍👧‍👦 **Family Suitability: {family_score:.1f}/10**
{family_verdict}
- Schools nearby: {school_count} found {('(Excellent access)' if school_count >= 8 else '(Good options)' if school_count >= 4 else '(Limited options)' if school_count > 0 else '(Not found)')}
- Healthcare access: {hospital_count} facilities {('(Comprehensive care)' if hospital_count >= 6 else '(Adequate coverage)' if hospital_count >= 3 else '(Basic access)' if hospital_count > 0 else '(Limited)')}
- Parks/Recreation: {park_count} locations {('(Great outdoor access)' if park_count >= 4 else '(Some options)' if park_count > 0 else '(Not identified)')}

🚇 **Connectivity & Transport: {connectivity_score:.1f}/10**
{connectivity_verdict}
- Metro/Transit: {transit_count} options {('(Excellent connectivity)' if transit_count >= 6 else '(Well-connected)' if transit_count >= 3 else '(Basic access)' if transit_count > 0 else '(Limited)')}
- Shopping/Malls: {mall_count} centers {('(Premium shopping)' if mall_count >= 3 else '(Available nearby)' if mall_count > 0 else '(Need to travel)')}
- Daily essentials: {store_count} stores {('(Highly convenient)' if store_count >= 8 else '(Good access)' if store_count >= 4 else '(Available)' if store_count > 0 else '(May require travel)')}

🚕 **Estimated Commute Times:**
- To Airport: {commute_estimates['airport']}
- To Business Hub: {commute_estimates['business_district']}
- To Railway Station: {commute_estimates['railway_station']}
(Note: Actual times vary by traffic and specific destination within {location})

😊 **Lifestyle Match:**
{lifestyle}

📊 **Bottom Line:**
This neighborhood offers a balanced lifestyle with {('strong family orientation' if family_score >= 7 else 'good urban connectivity' if connectivity_score >= 7 else 'moderate amenities')}. 
Based on {school_count + hospital_count + park_count + transit_count + mall_count + store_count} nearby amenities analyzed, it's {'particularly suited for families' if family_score > connectivity_score else 'ideal for professionals and young couples'} looking to settle in {location}."""

        return {
            "insights": insights_text,
            "family_score": round(family_score, 1),
            "connectivity_score": round(connectivity_score, 1),
            "commute_estimates": commute_estimates,
            "lifestyle_match": lifestyle,
            "family_verdict": family_verdict,
            "connectivity_verdict": connectivity_verdict
        }    
    def generate_investment_forecast(self, property_details: Dict, 
                                     investor_profile: Dict = None) -> Dict:
        """
        RAG-Enhanced investment forecast with ROI projections
        
        Args:
            property_details: {price, location, bhk, size, amenities}
            investor_profile: {investment_horizon, risk_tolerance, preferences}
        
        Returns:
            Investment forecast with market context, ROI analysis, and recommendations
        """
        try:
            if self.investment_advisor is None:
                return {
                    'error': 'Investment advisor not available',
                    'message': 'Investment advisor failed to initialize at startup.'
                }

            forecast = self.investment_advisor.generate_investment_forecast(property_details, investor_profile)
            
            # Format investment thesis with GenAI flair
            forecast['formatted_thesis'] = self._format_investment_thesis(forecast)
            
            return forecast
        
        except ImportError:
            return {
                'error': 'Investment advisor not available',
                'message': 'Please install RAG dependencies: pip install langchain chromadb sentence-transformers'
            }
        except Exception as e:
            return {
                'error': str(e),
                'fallback': self._generate_fallback_investment_forecast(property_details)
            }
    
    def _format_investment_thesis(self, forecast: Dict) -> str:
        """Format investment forecast with engaging language"""
        roi_analysis = forecast.get('base_roi_analysis', {})
        hold_period = roi_analysis.get('hold_period', 5)
        location = forecast.get('property', {}).get('location', 'selected location')
        price = forecast.get('property', {}).get('price', 0)
        roi_pct = roi_analysis.get('total_return', {}).get('net_annualized_roi', 0)
        growth = roi_analysis.get('capital_appreciation', {}).get('annual_rate_percent', 0)
        
        format_thesis = f"""
📈 RAG-Enhanced Investment Forecast for {location}

🎯 Quick Summary:
    Your ₹{price/10000000:.1f} Cr investment could yield {roi_pct:.1f}% net annualized returns over {hold_period} years.

📊 Why This Works:
    • Market context uses semantic retrieval and bounded real-time news signal
• Semantic matching with similar properties in the dataset
    • Scenario model adapts to volatility (bullish/moderate/bearish)
    • Net-return view includes vacancy, maintenance, taxes, and transaction costs

💡 Key Insight:
    Growth assumption used is {growth:.2f}% annually for the base case, adjusted with recent market conditions.
        """
        
        return format_thesis.strip()
    
    def _generate_fallback_investment_forecast(self, property_details: Dict) -> Dict:
        """Fallback forecast when RAG unavailable"""
        location = property_details.get('location', 'Mumbai')
        price = max(float(property_details.get('price', 5000000) or 5000000), 100000.0)
        bhk = property_details.get('bhk', 2)
        hold_period = int(property_details.get('investment_horizon', 5) or 5)
        hold_period = max(1, min(20, hold_period))
        
        # Hardcoded market data for fallback
        market_rates = {
            'Mumbai': 0.15,
            'Bangalore': 0.12,
            'Delhi': 0.10,
            'Pune': 0.18,
            'Hyderabad': 0.14
        }
        
        appreciation_rate = market_rates.get(location, 0.12)
        projected_value = price * ((1 + appreciation_rate) ** hold_period)
        rental_yield = price * 0.065
        
        return {
            'location': location,
            'price': price,
            'bhk': bhk,
            'estimated_appreciation': appreciation_rate * 100,
            'projected_value': projected_value,
            'estimated_capital_gain': projected_value - price,
            'annual_rental_income': rental_yield,
            'estimated_roi': (((projected_value + rental_yield * hold_period) / price) - 1) * 100,
            'confidence': 'Medium (rule-based estimate)',
            'data_source': 'Historical market averages'
        }
    
    def analyze_investment_fit(self, property_details: Dict, investor_profile: Dict) -> str:
        """
        Analyze if property matches investor's profile using GenAI reasoning
        
        Args:
            property_details: {price, location, bhk, size, amenities}
            investor_profile: {investment_horizon, risk_tolerance, budget, goals}
        
        Returns:
            Personalized analysis and recommendation
        """
        try:
            investment_horizon = investor_profile.get('investment_horizon', 5)
            risk_tolerance = investor_profile.get('risk_tolerance', 'moderate')
            budget = investor_profile.get('budget', 0)
            goals = investor_profile.get('goals', [])
            
            price = property_details.get('price', 0)
            location = property_details.get('location', 'Unknown')
            bhk = property_details.get('bhk', 2)
            
            # Check budget fit
            budget_fit = "✓ Within budget" if budget >= price else "✗ Exceeds budget"
            
            # Match with investment horizon
            horizon_match = self._match_horizon(investment_horizon, location)
            
            # Risk profile match
            risk_match = self._match_risk_profile(risk_tolerance, location)
            
            # Generate personalized analysis
            analysis = f"""
🎯 Investment Fit Analysis for {investor_profile.get('investor_name', 'You')}

📋 Profile Match Summary:
• Budget Fit: {budget_fit}
• Time Horizon: {horizon_match}
• Risk Profile: {risk_match}

🏠 Property-Profile Alignment:
{bhk} BHK in {location} {'aligns well with' if budget >= price else 'exceeds'} your investment parameters.

💼 Goal Alignment:
{self._align_with_goals(location, goals)}

✅ Recommendation:
{'This property is a good fit for your profile.' if budget >= price else 'Consider looking at properties in a lower price range.'} 
The {location} market {'shows' if location in ['Mumbai', 'Bangalore', 'Pune'] else 'has'} strong fundamentals for a {investment_horizon}-year hold.
            """
            
            return analysis.strip()
        
        except Exception as e:
            return f"Unable to complete fit analysis: {str(e)}"
    
    def _match_horizon(self, horizon: int, location: str) -> str:
        """Match time horizon with location maturity"""
        if horizon <= 3:
            return "Short-term (3yr) - Focus on appreciation hotspots" if location in ['Pune', 'Bangalore'] else "Short-term (3yr) - Established markets preferred"
        elif horizon <= 7:
            return f"Medium-term (5-7yr) - {location} offers balanced growth opportunities"
        else:
            return f"Long-term (10yr+) - {location} will transform, compounding gains over time"
    
    def _match_risk_profile(self, tolerance: str, location: str) -> str:
        """Match risk tolerance with location volatility"""
        risk_map = {
            'low': 'Conservative',
            'moderate': 'Balanced',
            'high': 'Growth-oriented'
        }
        
        volatility_map = {
            'Mumbai': 'Moderate volatility',
            'Bangalore': 'Low-moderate volatility',
            'Delhi': 'Moderate volatility',
            'Pune': 'Moderate-high volatility (emerging)',
            'Hyderabad': 'Low-moderate volatility'
        }
        
        return f"{risk_map.get(tolerance, 'Balanced')} investor in a {volatility_map.get(location, 'moderate')} market"
    
    def _align_with_goals(self, location: str, goals: List) -> str:
        """Align property with investor goals"""
        if not goals:
            return "No specific goals mentioned - property serves as investment diversification"
        
        goal_match = []
        for goal in goals:
            if goal == 'rental_income':
                goal_match.append(f"✓ Rental Income: {location} shows {6.5}%-7% yields")
            elif goal == 'capital_appreciation':
                goal_match.append(f"✓ Capital Appreciation: {location} has consistent appreciation trends")
            elif goal == 'tax_benefit':
                goal_match.append("✓ Tax Benefits: Property ownership offers LTCG benefits after 2 years")
            elif goal == 'inflation_hedge':
                goal_match.append("✓ Inflation Hedge: Real estate outpaces inflation in India")
        
        return "\n".join(goal_match) if goal_match else "Property supports standard investment goals"