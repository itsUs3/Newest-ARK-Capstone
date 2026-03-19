import asyncio

from models.agentic_workflow import AgenticWorkflow, AgenticState


class StubPricePredictor:
    def predict(self, features):
        return {"predicted_price": 8250000.0, "price_range": {"min": 7600000.0, "max": 8900000.0}}


class StubFraudDetector:
    def analyze(self, property_id, title, description=""):
        return {"trust_score": 84.0, "risk_level": "LOW", "flags": []}


class StubMarketNewsRAG:
    def retrieve_relevant_news(self, location, query=None, n_results=5, days_back=365):
        return [
            {
                "title": f"Metro expansion near {location}",
                "content": "Transit and infrastructure growth is improving demand.",
                "impact_score": 0.72,
                "location": location,
            }
        ]

    def generate_alert(self, location, articles, user_properties=None):
        return {
            "location": location,
            "alert_summary": f"Positive momentum in {location} due to infrastructure upgrades.",
            "impact_level": "moderate_positive",
        }


class StubGenAIHandler:
    def _generate_with_guardrails(self, task, instruction, fallback_text, context_chunks=None, verify_grounding=True):
        return "Buy with caution: valuation is fair, trust score is healthy, and market momentum is positive."


def test_agentic_workflow_minimal_example():
    workflow = AgenticWorkflow(
        price_predictor=StubPricePredictor(),
        fraud_detector=StubFraudDetector(),
        market_news_rag=StubMarketNewsRAG(),
        genai_handler=StubGenAIHandler(),
    )

    initial_state: AgenticState = {
        "location": "Mumbai",
        "bhk": 2,
        "size": 900.0,
    }

    result = asyncio.run(workflow.run(initial_state))

    assert result.get("predicted_price") == 8250000.0
    assert result.get("fraud_score") == 84.0
    assert "Positive momentum" in result.get("market_summary", "")
    assert result.get("final_advice", "")
    assert isinstance(result.get("errors"), list)
