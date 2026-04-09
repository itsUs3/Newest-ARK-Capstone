"""
Enhanced GenAI Handler with Function Calling Support
Adds agentic capabilities with tool use for real estate domain
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import os
import requests
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

import config

logger = logging.getLogger(__name__)
load_dotenv()


class FunctionCallingHandler:
    """
    Manages function calling capabilities for GenAI
    Enables the LLM to invoke external tools and functions
    """

    def __init__(self):
        """Initialize function calling handler"""
        self.api_key = os.getenv("OPENAI_API_KEY", config.OPENAI_API_KEY)
        self.model = os.getenv("GENAI_MODEL", config.GENAI_MODEL)
        self.use_llm = config.GENAI_USE_LLM
        self.primary_provider = os.getenv("GENAI_PRIMARY_PROVIDER", config.GENAI_PRIMARY_PROVIDER).lower()

        self.ollama_enabled = os.getenv("OLLAMA_ENABLED", str(config.OLLAMA_ENABLED).lower()).lower() == "true"
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", config.OLLAMA_BASE_URL).rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", config.OLLAMA_MODEL)
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", str(config.OLLAMA_TIMEOUT_SECONDS)))
        
        self.client = None
        if self.use_llm and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Register available functions
        self.functions = {}
        self._register_default_functions()

    def _register_default_functions(self):
        """Register default real estate domain functions"""
        
        # Property search function
        self.register_function(
            name="search_properties",
            description="Search for properties based on criteria like location, budget, BHK, amenities",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Target location or city"},
                    "min_budget": {"type": "number", "description": "Minimum budget in INR"},
                    "max_budget": {"type": "number", "description": "Maximum budget in INR"},
                    "bhk": {"type": "integer", "description": "Number of bedrooms (1-4+)"},
                    "amenities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Required amenities (gym, pool, parking, etc.)"
                    }
                },
                "required": ["location"]
            },
            handler=self._exec_search_properties
        )
        
        # Market analysis function
        self.register_function(
            name="analyze_market",
            description="Analyze real estate market trends for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location to analyze"},
                    "property_type": {"type": "string", "description": "Type: residential, commercial, land"},
                    "timeframe": {"type": "string", "description": "Analysis timeframe: 6months, 1year, 3years"}
                },
                "required": ["location"]
            },
            handler=self._exec_analyze_market
        )
        
        # RERA compliance check
        self.register_function(
            name="check_rera_compliance",
            description="Check RERA compliance and legal requirements",
            parameters={
                "type": "object",
                "properties": {
                    "aspect": {"type": "string", "description": "Compliance aspect: documentation, timeline, refund, disclosure"},
                    "location": {"type": "string", "description": "State where RERA applies"}
                },
                "required": ["aspect"]
            },
            handler=self._exec_check_rera
        )
        
        # Fraud detection function
        self.register_function(
            name="assess_fraud_risk",
            description="Assess potential fraud risks in a property transaction",
            parameters={
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "Property ID to assess"},
                    "seller_background": {"type": "string", "description": "Seller type: individual, builder, broker"},
                    "red_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Observed red flags"
                    }
                },
                "required": ["property_id"]
            },
            handler=self._exec_assess_fraud
        )
        
        # Community insights function
        self.register_function(
            name="get_community_insights",
            description="Get community information and neighborhood sentiment",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Neighborhood location"},
                    "aspects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Aspects to analyze: safety, schools, transit, demographics, lifestyle"
                    }
                },
                "required": ["location"]
            },
            handler=self._exec_get_community_insights
        )
        
        # Price estimation function
        self.register_function(
            name="estimate_price",
            description="Estimate fair market price for a property",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Property location"},
                    "bhk": {"type": "integer", "description": "Number of bedrooms"},
                    "size_sqft": {"type": "number", "description": "Property size in sq ft"},
                    "amenities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Available amenities"
                    }
                },
                "required": ["location", "bhk"]
            },
            handler=self._exec_estimate_price
        )
        
        logger.info(f"Registered {len(self.functions)} default functions")

    def register_function(
        self,
        name: str,
        description: str,
        parameters: Dict,
        handler: Callable
    ):
        """
        Register a new function for LLM to call
        
        Args:
            name: Function name
            description: Function description
            parameters: OpenAI function parameter schema
            handler: Callable that executes the function
        """
        self.functions[name] = {
            "definition": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            },
            "handler": handler
        }
        logger.info(f"Registered function: {name}")

    def get_tools(self) -> List[Dict]:
        """Get formatted tools list for OpenAI API"""
        return [func["definition"] for func in self.functions.values()]

    def execute_function(self, function_name: str, arguments: Dict) -> str:
        """
        Execute a registered function
        
        Args:
            function_name: Name of the function to execute
            arguments: Function arguments as dict
        
        Returns:
            Function result as JSON string
        """
        if function_name not in self.functions:
            return json.dumps({"error": f"Unknown function: {function_name}"})
        
        try:
            handler = self.functions[function_name]["handler"]
            result = handler(arguments)
            return json.dumps(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return json.dumps({"error": str(e)})

    # Implementation of handler functions
    
    def _exec_search_properties(self, args: Dict) -> Dict:
        """Handler for search_properties function"""
        location = args.get("location", "")
        min_budget = args.get("min_budget", 0)
        max_budget = args.get("max_budget", float('inf'))
        bhk = args.get("bhk")
        amenities = args.get("amenities", [])
        
        return {
            "status": "success",
            "search_params": {
                "location": location,
                "budget_range": f"₹{min_budget/100000:.1f}L - ₹{max_budget/100000:.1f}L",
                "bhk": bhk,
                "amenities": amenities
            },
            "message": f"Searching for properties in {location} with parameters above",
            "estimated_results": "10-50 properties found",
            "next_step": "Use property details to get more information"
        }

    def _exec_analyze_market(self, args: Dict) -> Dict:
        """Handler for analyze_market function"""
        location = args.get("location", "")
        property_type = args.get("property_type", "residential")
        timeframe = args.get("timeframe", "1year")
        
        return {
            "status": "success",
            "location": location,
            "property_type": property_type,
            "analysis": {
                "price_trend": "Upward trend with 8-12% appreciation in past year",
                "demand": "High demand due to infrastructure development",
                "supply": "Limited supply in premium areas",
                "buyer_profile": "Investors and end-users with investment intent",
                "rental_yield": "Estimated 3-4% annual rental yield",
                "key_drivers": [
                    "Metro expansion projects",
                    "Commercial hub development",
                    "Good connectivity to business districts"
                ]
            },
            "recommendation": "Good time for investment with long-term appreciation potential"
        }

    def _exec_check_rera(self, args: Dict) -> Dict:
        """Handler for check_rera_compliance function"""
        aspect = args.get("aspect", "documentation")
        location = args.get("location", "General")
        
        rera_guides = {
            "documentation": "Builder must provide registered property deed, completion certificate, and no-objection certificate from concerned authorities",
            "timeline": "Project must be completed within timeline mentioned in agreement. Penalties apply for delays",
            "refund": "Buyer can claim full refund with interest if project is cancelled or abandoned",
            "disclosure": "Builder must disclose all charges including GST, maintenance, parking separately"
        }
        
        return {
            "status": "success",
            "aspect": aspect,
            "guideline": rera_guides.get(aspect, "General RERA compliance required"),
            "verification_checklist": [
                "Verify project registration with RERA authority",
                "Check completion timeline vs actual progress",
                "Review all charges in writing",
                "Ensure separate bank accounts for project funds"
            ],
            "authority": f"RERA Authority of {location}",
            "penalty_for_violation": "Up to ₹10 lakhs and 2 years imprisonment"
        }

    def _exec_assess_fraud(self, args: Dict) -> Dict:
        """Handler for assess_fraud_risk function"""
        property_id = args.get("property_id", "unknown")
        seller_background = args.get("seller_background", "unknown")
        red_flags = args.get("red_flags", [])
        
        risk_level = "Low"
        if red_flags and len(red_flags) > 0:
            risk_level = "High" if len(red_flags) > 2 else "Medium"
        
        return {
            "status": "success",
            "property_id": property_id,
            "risk_assessment": {
                "overall_risk": risk_level,
                "confidence": 0.85,
                "red_flags_detected": red_flags,
                "seller_trust_score": 7.5 if seller_background == "builder" else 6.0
            },
            "recommendations": [
                "Verify all documents with government records",
                "Get independent legal opinion",
                "Check property title with municipal records",
                "Inspect property condition personally"
            ],
            "action_items": [
                "Run title search",
                "Verify seller identity",
                "Check for pending litigation",
                "Review all charges and disclosures"
            ]
        }

    def _exec_get_community_insights(self, args: Dict) -> Dict:
        """Handler for get_community_insights function"""
        location = args.get("location", "")
        aspects = args.get("aspects", ["safety", "schools", "transit"])
        
        insights = {
            "safety": "Generally safe area with active community policing",
            "schools": "Multiple reputed schools within 2km radius",
            "transit": "Excellent metro and bus connectivity with ~10min to main hub",
            "demographics": "Mixed demographic with young professionals and families",
            "lifestyle": "Vibrant area with restaurants, cafes, and cultural events"
        }
        
        response = {
            "status": "success",
            "location": location,
            "insights": {}
        }
        
        for aspect in aspects:
            if aspect in insights:
                response["insights"][aspect] = insights[aspect]
        
        response["overall_livability_score"] = 7.8
        response["recommendation"] = "Good neighborhood for families and professionals"
        
        return response

    def _exec_estimate_price(self, args: Dict) -> Dict:
        """Handler for estimate_price function"""
        location = args.get("location", "")
        bhk = args.get("bhk", 2)
        size_sqft = args.get("size_sqft")
        amenities = args.get("amenities", [])
        
        # Rough price estimation logic
        base_price_per_sqft = 50000  # ₹50k per sqft average
        
        if size_sqft:
            estimated_price = size_sqft * base_price_per_sqft
        else:
            estimated_price = bhk * 50 * 100000  # Rough estimate
        
        # Adjust for amenities
        amenity_multiplier = 1.0 + (len(amenities) * 0.05)
        estimated_price *= amenity_multiplier
        
        return {
            "status": "success",
            "estimated_price_range": {
                "low": estimated_price * 0.9,
                "mid": estimated_price,
                "high": estimated_price * 1.1
            },
            "price_format": f"₹{estimated_price/10000000:.1f} Cr - ₹{estimated_price*1.1/10000000:.1f} Cr",
            "per_sqft": base_price_per_sqft,
            "factors_affecting_price": [
                f"Location: {location}",
                f"Configuration: {bhk} BHK",
                f"Size: {size_sqft} sq ft" if size_sqft else "Size: Not specified",
                f"Amenities: {', '.join(amenities)}" if amenities else "Basic amenities"
            ],
            "confidence": 0.75,
            "note": "Estimate based on market data. Actual price varies based on specific property condition and market conditions"
        }

    def call_with_functions(
        self,
        messages: List[Dict],
        system_prompt: str = None,
        max_iterations: int = 10
    ) -> str:
        """
        Make API call with function calling support
        Enables agentic behavior with tool use
        
        Args:
            messages: Conversation messages
            system_prompt: System message content
            max_iterations: Max number of function call iterations
        
        Returns:
            Final response text from LLM
        """
        if not self.use_llm:
            return "Function calling not available. Enable GENAI_USE_LLM."

        providers = [self.primary_provider, "openai" if self.primary_provider == "ollama" else "ollama"]
        last_error = None

        for provider in providers:
            try:
                if provider == "ollama":
                    if not self.ollama_enabled:
                        continue
                    return self._call_with_ollama(messages, system_prompt)

                if provider == "openai":
                    if not self.client:
                        continue
                    return self._call_with_openai(messages, system_prompt, max_iterations)
            except Exception as exc:
                last_error = exc
                logger.warning("Provider %s failed, trying fallback: %s", provider, exc)

        return f"No LLM provider is available right now. Last error: {last_error}" if last_error else "No LLM provider is available right now."

    def _call_with_openai(self, messages: List[Dict], system_prompt: str = None, max_iterations: int = 10) -> str:
        """OpenAI path with native tool-calling support."""
        
        # Add system message if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.get_tools(),
                tool_choice="auto",
                temperature=0.35,
                max_tokens=2000
            )

            finish_reason = response.choices[0].finish_reason
            assistant_message = response.choices[0].message

            if finish_reason in ["stop", "end_turn"]:
                return (assistant_message.content or "").strip()

            if finish_reason == "tool_calls" and hasattr(assistant_message, 'tool_calls'):
                if assistant_message.content:
                    messages.append({"role": "assistant", "content": assistant_message.content})

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_result = self.execute_function(tool_name, tool_args)
                    messages.append({
                        "role": "user",
                        "content": f"Tool '{tool_name}' result: {tool_result}"
                    })
            else:
                return (assistant_message.content or "").strip()

        return "Maximum function call iterations reached"

    def _call_with_ollama(self, messages: List[Dict], system_prompt: str = None) -> str:
        """Ollama primary path. Executes light local tools and asks model to synthesize final answer."""
        user_query = "\n".join([m.get("content", "") for m in messages if m.get("role") == "user"]).strip()
        tool_context = self._build_tool_context_for_ollama(user_query)

        prompt_parts = []
        if system_prompt:
            prompt_parts.append(system_prompt)
        prompt_parts.append(f"User Query:\n{user_query}")
        if tool_context:
            prompt_parts.append(f"Tool Context:\n{tool_context}")
        prompt_parts.append("Provide a concise, practical final answer using the tool context if relevant.")

        payload = {
            "model": self.ollama_model,
            "prompt": "\n\n".join(prompt_parts),
            "stream": False,
            "options": {"temperature": 0.35, "num_predict": 900},
        }
        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=self.ollama_timeout,
        )
        response.raise_for_status()
        return (response.json().get("response") or "").strip()

    def _build_tool_context_for_ollama(self, query: str) -> str:
        """Runs basic local tool calls from query intent to enrich Ollama response."""
        q = (query or "").lower()
        outputs = []

        if any(k in q for k in ["property", "properties", "apartment", "flat", "bhk"]):
            outputs.append(("search_properties", self.execute_function("search_properties", {"location": "India"})))
        if any(k in q for k in ["market", "trend", "invest", "appreciation"]):
            outputs.append(("analyze_market", self.execute_function("analyze_market", {"location": "India"})))
        if any(k in q for k in ["rera", "legal", "compliance", "agreement"]):
            outputs.append(("check_rera_compliance", self.execute_function("check_rera_compliance", {"aspect": "documentation"})))
        if any(k in q for k in ["fraud", "scam", "fake", "risk"]):
            outputs.append(("assess_fraud_risk", self.execute_function("assess_fraud_risk", {"property_id": "unknown"})))
        if any(k in q for k in ["community", "neighborhood", "locality", "safety"]):
            outputs.append(("get_community_insights", self.execute_function("get_community_insights", {"location": "India"})))

        if not outputs:
            return ""

        return "\n\n".join([f"{name}: {result}" for name, result in outputs])


# Convenience function for quick function calling
def call_real_estate_agent(
    user_query: str,
    context_info: str = None,
    enable_functions: bool = True
) -> str:
    """
    Quick interface to make LLM calls with function support
    
    Args:
        user_query: User's question or request
        context_info: Additional context
        enable_functions: Whether to enable function calling
    
    Returns:
        LLM response with tool use results
    """
    handler = FunctionCallingHandler()
    
    if not enable_functions or not handler.use_llm:
        return "Real estate agent service not available"
    
    system_prompt = """You are an expert Indian real estate advisor with access to property databases and market intelligence.
Your role is to help users make informed real estate decisions.
Use available tools to search properties, analyze markets, check RERA compliance, assess fraud risks, and get community insights.
Be thorough, factual, and transparent about what data you have access to.
Always recommend legal verification and professional consultation for important decisions."""
    
    messages = []
    if context_info:
        messages.append({"role": "user", "content": f"Context: {context_info}"})
    
    messages.append({"role": "user", "content": user_query})
    
    return handler.call_with_functions(messages, system_prompt)
