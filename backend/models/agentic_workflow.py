import asyncio
import importlib
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, cast

LANGGRAPH_AVAILABLE = False
END: Any = "__end__"
StateGraph: Any = None

try:
    _graph_module = importlib.import_module("langgraph.graph")
    END = getattr(_graph_module, "END")
    StateGraph = getattr(_graph_module, "StateGraph")
    LANGGRAPH_AVAILABLE = True
except Exception:
    LANGGRAPH_AVAILABLE = False

logger = logging.getLogger(__name__)


class AgenticState(TypedDict, total=False):
    request_id: str
    timestamp: str
    location: str
    bhk: int
    size: float
    amenities: List[str]

    predicted_price: Optional[float]
    fraud_score: Optional[float]
    market_summary: str
    final_advice: str

    valuation_result: Dict[str, Any]
    fraud_result: Dict[str, Any]
    market_result: Dict[str, Any]

    errors: List[str]


class AgenticWorkflow:
    """LangGraph orchestration for valuation, fraud, market intelligence, and advisory."""

    def __init__(
        self,
        price_predictor: Any,
        fraud_detector: Any,
        market_news_rag: Any,
        genai_handler: Any,
    ) -> None:
        if not LANGGRAPH_AVAILABLE or StateGraph is None:
            raise RuntimeError("LangGraph is not available. Install 'langgraph' to use agentic orchestration.")

        self.price_predictor = price_predictor
        self.fraud_detector = fraud_detector
        self.market_news_rag = market_news_rag
        self.genai_handler = genai_handler
        self.graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            raise RuntimeError("StateGraph is unavailable")

        workflow = StateGraph(AgenticState)

        workflow.add_node("valuation", self.valuation_agent)
        workflow.add_node("fraud", self.fraud_agent)
        workflow.add_node("rag", self.market_intelligence_agent)
        workflow.add_node("advisory", self.advisory_agent)

        workflow.set_entry_point("valuation")
        workflow.add_edge("valuation", "fraud")
        workflow.add_edge("fraud", "rag")
        workflow.add_edge("rag", "advisory")
        workflow.add_edge("advisory", END)

        return workflow.compile()

    @staticmethod
    def _safe_errors(state: Dict[str, Any]) -> List[str]:
        errors = state.get("errors")
        if isinstance(errors, list):
            return errors
        return []

    async def valuation_agent(self, state: AgenticState) -> AgenticState:
        updated_state: Dict[str, Any] = dict(state)
        errors = self._safe_errors(updated_state)

        try:
            features = {
                "location": updated_state.get("location", ""),
                "bhk": int(updated_state.get("bhk", 2)),
                "size": float(updated_state.get("size", 1000.0)),
                "amenities": updated_state.get("amenities", []),
                "furnishing": "Semi-Furnished",
                "construction_status": "Ready to Move",
            }

            valuation_result = await asyncio.to_thread(self.price_predictor.predict, features)
            predicted_price = valuation_result.get("predicted_price")

            updated_state["valuation_result"] = valuation_result
            updated_state["predicted_price"] = float(predicted_price) if predicted_price is not None else None

        except Exception as exc:
            msg = f"valuation_agent_failed: {exc}"
            logger.exception(msg)
            errors.append(msg)
            updated_state["valuation_result"] = {"error": str(exc)}
            updated_state["predicted_price"] = None

        updated_state["errors"] = errors
        return cast(AgenticState, updated_state)

    async def fraud_agent(self, state: AgenticState) -> AgenticState:
        updated_state: Dict[str, Any] = dict(state)
        errors = self._safe_errors(updated_state)

        try:
            location = updated_state.get("location", "Unknown location")
            bhk = int(updated_state.get("bhk", 2))
            size = float(updated_state.get("size", 1000.0))
            predicted_price = updated_state.get("predicted_price")

            title = f"{bhk} BHK property in {location}"
            description = (
                f"Estimated size: {size} sq ft. "
                f"Predicted price: {predicted_price if predicted_price is not None else 'NA'}."
            )

            fraud_result = await asyncio.to_thread(
                self.fraud_detector.analyze,
                str(updated_state.get("request_id", uuid.uuid4())),
                title,
                description,
            )

            trust_score = fraud_result.get("trust_score")
            updated_state["fraud_result"] = fraud_result
            updated_state["fraud_score"] = float(trust_score) if trust_score is not None else None

        except Exception as exc:
            msg = f"fraud_agent_failed: {exc}"
            logger.exception(msg)
            errors.append(msg)
            updated_state["fraud_result"] = {"error": str(exc)}
            updated_state["fraud_score"] = None

        updated_state["errors"] = errors
        return cast(AgenticState, updated_state)

    async def market_intelligence_agent(self, state: AgenticState) -> AgenticState:
        updated_state: Dict[str, Any] = dict(state)
        errors = self._safe_errors(updated_state)

        try:
            location = updated_state.get("location", "")
            query = f"{location} real estate trend"

            articles = await asyncio.to_thread(
                self.market_news_rag.retrieve_relevant_news,
                location,
                query,
                5,
                365,
            )

            market_result = await asyncio.to_thread(
                self.market_news_rag.generate_alert,
                location,
                articles,
                None,
            )

            updated_state["market_result"] = market_result
            updated_state["market_summary"] = market_result.get(
                "alert_summary", f"No market summary available for {location}."
            )

        except Exception as exc:
            msg = f"market_intelligence_agent_failed: {exc}"
            logger.exception(msg)
            errors.append(msg)
            updated_state["market_result"] = {"error": str(exc)}
            updated_state["market_summary"] = "Market intelligence unavailable at the moment."

        updated_state["errors"] = errors
        return cast(AgenticState, updated_state)

    async def advisory_agent(self, state: AgenticState) -> AgenticState:
        updated_state: Dict[str, Any] = dict(state)
        errors = self._safe_errors(updated_state)

        try:
            location = updated_state.get("location", "Unknown")
            bhk = updated_state.get("bhk", 2)
            size = updated_state.get("size", 1000)
            predicted_price = updated_state.get("predicted_price")
            fraud_score = updated_state.get("fraud_score")
            market_summary = updated_state.get("market_summary", "")

            instruction = (
                "Provide a concise real-estate recommendation for the user based only on context. "
                "Include: valuation confidence, trust/risk interpretation, and market outlook. "
                "Be explicit when data is missing and avoid guarantees."
            )

            context_chunks = [
                f"Location: {location}",
                f"BHK: {bhk}",
                f"Size: {size}",
                f"Predicted price: {predicted_price}",
                f"Fraud trust score: {fraud_score}",
                f"Market summary: {market_summary}",
            ]

            fallback_advice = (
                f"For {bhk} BHK in {location}, the estimated price is {predicted_price}. "
                f"Trust score is {fraud_score}. Market signal: {market_summary}. "
                "Recommendation: verify legal docs, compare with 3-5 nearby listings, "
                "and negotiate based on comparable sales before finalizing."
            )

            final_advice = await asyncio.to_thread(
                self.genai_handler._generate_with_guardrails,
                "chat",
                instruction,
                fallback_advice,
                context_chunks,
                True,
            )

            updated_state["final_advice"] = final_advice

        except Exception as exc:
            msg = f"advisory_agent_failed: {exc}"
            logger.exception(msg)
            errors.append(msg)
            updated_state["final_advice"] = (
                "Advisory generation failed. Please review valuation, fraud score, and market summary manually."
            )

        updated_state["errors"] = errors
        return cast(AgenticState, updated_state)

    async def run(self, initial_state: AgenticState) -> AgenticState:
        state: Dict[str, Any] = dict(initial_state)
        state.setdefault("request_id", str(uuid.uuid4()))
        state.setdefault("timestamp", datetime.now().isoformat())
        state.setdefault("amenities", [])
        state.setdefault("errors", [])
        state.setdefault("market_summary", "")
        state.setdefault("final_advice", "")

        result = await self.graph.ainvoke(state)
        return cast(AgenticState, result)
