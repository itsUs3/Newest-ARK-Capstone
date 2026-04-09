# GenAI Features Integration Guide

## Overview

This guide explains how to integrate and use the three new GenAI features implemented for the myNivas Capstone project:

1. **LLM-Based Recommendations** - Replace rule-based recommendations with intelligent LLM generation
2. **Multi-Domain RAG** - Expand RAG across all real estate knowledge domains
3. **Function Calling / Tool Use** - Enable LLM to autonomously call tools and functions

---

## Feature 1: LLM-Based Recommendations

### Purpose
Replace the rule-based recommendation engine with an LLM-powered system that uses OpenAI's function calling to generate personalized property recommendations with reasoning.

### Location
- **Main Module**: `backend/models/llm_recommendation_engine.py`
- **Class**: `LLMRecommendationEngine`

### Key Features
- ✅ LLM-generated personalized recommendations with explanations
- ✅ Function calling for autonomous property search and market analysis
- ✅ Fallback to rule-based recommendations if LLM unavailable
- ✅ OpenAI GPT-4o-mini integration
- ✅ Context-aware recommendations based on user preferences

### Usage

```python
from models.llm_recommendation_engine import LLMRecommendationEngine

# Initialize engine
engine = LLMRecommendationEngine(use_llm=True)

# Define user preferences
preferences = {
    'budget_min': 50 * 100000,      # 50 Lakhs
    'budget_max': 150 * 100000,     # 150 Lakhs
    'location': 'Mumbai',
    'bhk': 2,
    'amenities': ['gym', 'parking', 'security'],
    'max_commute_minutes': 30
}

# Get LLM-generated recommendations with function calling
result = engine.generate_recommendations_with_llm(
    preferences,
    context="First-time homebuyer, needs good schools nearby"
)

# Result contains:
# - recommendations: LLM-generated text with reasoning
# - success: Boolean status
# - timestamp: When recommendations were generated
# - method: Either 'llm' or 'fallback_rule_based'

print(result['recommendations'])

# Also get structured list of recommendations
properties = engine.get_recommendations(preferences)
```

### API Integration Example

```python
# In your FastAPI endpoint
from fastapi import FastAPI, HTTPException
from models.llm_recommendation_engine import LLMRecommendationEngine

app = FastAPI()
engine = LLMRecommendationEngine()

@app.post("/api/recommendations/llm")
async def get_llm_recommendations(user_preferences: dict, context: str = None):
    """
    Get LLM-powered personalized recommendations
    """
    try:
        result = engine.generate_recommendations_with_llm(user_preferences, context)
        return {
            "success": result['success'],
            "recommendations": result['recommendations'],
            "timestamp": result['timestamp']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Function Calling Tools Available (for LLM)

The LLM can automatically call:

1. **search_properties** - Find properties matching criteria
2. **get_property_details** - Get detailed info about a property
3. **get_location_insights** - Get market trends and insights for a location

### Configuration

Set in `.env`:
```
OPENAI_API_KEY=your_api_key_here
GENAI_USE_LLM=true
GENAI_MODEL=gpt-4o-mini
GENAI_TEMPERATURE=0.35
```

### Performance & Costs

- **Latency**: ~2-5 seconds per recommendation request (LLM + function calls)
- **Cost**: ~0.10 INR per recommendation call (GPT-4o-mini pricing)
- **Fallback**: Automatic fallback to rule-based if LLM unavailable

---

## Feature 2: Multi-Domain RAG System

### Purpose
Expand RAG coverage from single market_news domain to comprehensive multi-domain system covering all real estate knowledge areas.

### Location
- **Main Module**: `backend/models/multi_domain_rag.py`
- **Class**: `MultiDomainRAG`

### Domains Covered

| Domain | Purpose | Content |
|--------|---------|---------|
| **market_news** | Market trends, price movements, news | Real estate market articles and news |
| **rera_laws** | RERA regulations, legal compliance | Buyer rights, developer obligations, penalties |
| **contracts** | Legal documents, contract templates | Sale deeds, templates, clauses |
| **properties** | Property features, amenities, guides | Property descriptions, amenity benefits |
| **fraud_patterns** | Common fraud schemes, red flags | Scam patterns, warning signs, verification tips |
| **community** | Neighborhood info, social sentiment | Community insights, demographics, lifestyle |

### Usage

```python
from models.multi_domain_rag import MultiDomainRAG

# Initialize
rag = MultiDomainRAG()

# Initialize with default content
rag.initialize_default_content()

# Search specific domain
results = rag.search(
    domain="rera_laws",
    query="What are buyer rights during project delays?",
    top_k=5
)

# Results format: [(document_text, similarity_score, metadata), ...]
for doc, similarity, meta in results:
    print(f"[{similarity:.1%}] {doc}")
    print(f"Source: {meta.get('source', 'Unknown')}")

# Search across all domains
all_results = rag.search_all_domains(
    query="property purchase process",
    top_k_per_domain=3
)

for domain, results in all_results.items():
    print(f"\n{domain.upper()}:")
    for doc, sim, meta in results:
        print(f"  [{sim:.1%}] {doc[:100]}...")

# Add custom documents to a domain
documents = [
    "Custom legal guideline about property registration",
    "Market analysis for premium properties"
]
metadatas = [
    {"source": "Custom", "type": "Legal"},
    {"source": "Market Analysis", "type": "Trend"}
]

rag.add_documents("rera_laws", documents, metadatas)

# Get domain information
summary = rag.get_domain_summary("market_news")
print(f"Total documents in market_news: {summary['document_count']}")

# Get all summaries
summaries = rag.get_all_summaries()
```

### API Integration Example

```python
from fastapi import FastAPI
from models.multi_domain_rag import MultiDomainRAG

app = FastAPI()
rag = MultiDomainRAG()
rag.initialize_default_content()

@app.get("/api/rag/search")
async def search_knowledge(query: str, domain: str = None, top_k: int = 5):
    """
    Search RAG across specific domain or all domains
    """
    if domain:
        results = rag.search(domain, query, top_k)
        return {
            "total": len(results),
            "results": [
                {
                    "text": doc[:500],
                    "similarity": float(sim),
                    "source": meta.get("source", "Unknown")
                }
                for doc, sim, meta in results
            ]
        }
    else:
        all_results = rag.search_all_domains(query, top_k)
        return {
            "domains_searched": list(all_results.keys()),
            "results_by_domain": {
                domain: {
                    "count": len(results),
                    "snippets": [doc[:200] for doc, _, _ in results]
                }
                for domain, results in all_results.items()
            }
        }

@app.get("/api/rag/domains")
async def list_domains():
    """List all available RAG domains"""
    return {
        "domains": rag.get_all_summaries()
    }
```

### Adding Custom Content

```python
# Load data from your CSV or database
import pandas as pd

df = pd.read_csv("your_data.csv")

documents = df['content'].tolist()
metadatas = [
    {
        "source": "Custom Source",
        "title": row['title'],
        "date": row['date']
    }
    for _, row in df.iterrows()
]

rag.add_documents("contracts", documents, metadatas)
```

### Performance

- **Search Latency**: ~200-500ms per query
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (384D)
- **Storage**: SQLite-based ChromaDB (~100MB for full knowledge base)

---

## Feature 3: Function Calling / Tool Use

### Purpose
Enable the LLM to autonomously call external tools and functions, providing agentic capabilities for complex real estate tasks.

### Location
- **Main Module**: `backend/models/function_calling_handler.py`
- **Class**: `FunctionCallingHandler`
- **Convenience Function**: `call_real_estate_agent()`

### Available Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| **search_properties** | location, budget, bhk, amenities | Matching property IDs and details |
| **analyze_market** | location, property_type, timeframe | Market trends, price movement, analysis |
| **check_rera_compliance** | aspect, location | RERA guidelines, compliance checklist |
| **assess_fraud_risk** | property_id, red_flags | Risk level, recommendations, verification steps |
| **get_community_insights** | location, aspects | Community data, livability score, insights |
| **estimate_price** | location, bhk, size, amenities | Price range, per-sqft rate, confidence score |

### Usage

#### Simple Usage (Quick)

```python
from models.function_calling_handler import call_real_estate_agent

# Simple one-line call
response = call_real_estate_agent(
    user_query="Find 2 BHK properties in Banglore with gym, and check market trends"
)

print(response)  # LLM-generated answer with tool results
```

#### Advanced Usage (Custom Functions)

```python
from models.function_calling_handler import FunctionCallingHandler

# Initialize handler
handler = FunctionCallingHandler()

# Register custom function
def my_custom_tool(args: dict) -> dict:
    """Your custom business logic"""
    location = args.get("location")
    # ... your logic ...
    return {"status": "success", "data": "..."}

handler.register_function(
    name="custom_analysis",
    description="Perform custom analysis",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "Target location"}
        },
        "required": ["location"]
    },
    handler=my_custom_tool
)

# Make call with custom function
messages = [{"role": "user", "content": "Analyze Pune for real estate investment"}]
response = handler.call_with_functions(
    messages,
    system_prompt="You are a real estate expert. Use available tools to provide insights."
)

print(response)
```

#### API Integration Example

```python
from fastapi import FastAPI, HTTPException
from models.function_calling_handler import FunctionCallingHandler

app = FastAPI()
handler = FunctionCallingHandler()

@app.post("/api/real-estate-agent")
async def real_estate_agent(user_query: str, context: str = None):
    """
    AI real estate agent endpoint with function calling
    """
    try:
        messages = [{"role": "user", "content": user_query}]
        if context:
            messages.insert(0, {"role": "user", "content": f"Context: {context}"})
        
        response = handler.call_with_functions(
            messages,
            system_prompt="""You are an expert Indian real estate advisor.
Use available tools to search properties, analyze markets, check legal compliance,
assess fraud risks, and provide community insights. Always recommend professional
verification for important decisions."""
        )
        
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### How Function Calling Works

1. **LLM Analysis**: User provides query
2. **Tool Planning**: LLM determines which tool(s) to call
3. **Function Execution**: System executes tools in agentic loop
4. **Result Integration**: LLM incorporates tool results into response
5. **Final Response**: Natural language answer with integrated tool results

Example conversation:

```
User: "I want to invest in Bangalore. Show me options and check market trends."

LLM Plan:
1. Call search_properties(location='Bangalore', ...)
2. Call analyze_market(location='Bangalore', timeframe='1year')
3. Call get_community_insights(location='Bangalore')

Execution:
✓ Found 42 properties matching criteria
✓ Market analysis: 12% appreciation, high demand
✓ Community: Good schools, IT hub, safe

Final Response:
"Bangalore is an excellent investment location... [integrated insights]"
```

### Configuration

Set in `.env`:
```
OPENAI_API_KEY=your_api_key
GENAI_USE_LLM=true
GENAI_MODEL=gpt-4o-mini
```

### Max Iterations

The function calling loop has a maximum of 10 iterations by default to prevent infinite loops.

```python
response = handler.call_with_functions(
    messages,
    system_prompt="...",
    max_iterations=5  # Custom limit
)
```

---

## Integrated Example: Full Workflow

See `backend/models/genai_features_examples.py` for complete working examples combining all three features.

### Running Examples

```bash
cd backend
python models/genai_features_examples.py
```

This will:
1. Generate LLM recommendations for a sample user
2. Demonstrate multi-domain RAG search across all domains
3. Show function calling with various use cases
4. Display an integrated end-to-end workflow

---

## Configuration & Environment Setup

### Required Environment Variables

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...your-key...
GENAI_USE_LLM=true
GENAI_MODEL=gpt-4o-mini

# Temperature settings (0.0-1.5)
GENAI_TEMPERATURE=0.35
GENAI_TEMPERATURE_DESCRIPTION=0.55
GENAI_TEMPERATURE_EXPLAIN=0.25

# Token limits
GENAI_MAX_INPUT_TOKENS=1800
GENAI_MAX_OUTPUT_TOKENS=450
GENAI_MAX_RESPONSE_CHARS=3500

# RAG Configuration
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_PERSIST_DIR=backend/chroma_db_news_runtime
```

### Package Requirements

Add to `backend/requirements.txt`:

```
openai>=1.0.0
sentence-transformers>=2.2.0
chromadb>=0.4.0
python-dotenv>=1.0.0
```

Install:
```bash
pip install -r requirements.txt
```

---

## Integration Points with Existing Code

### 1. Recommendation Engine

**Replace existing endpoint:**

```python
# OLD: backend/routes/recommendations.py
from models.recommendation_engine import RecommendationEngine

# NEW:
from models.llm_recommendation_engine import LLMRecommendationEngine
```

### 2. RAG Search

**Expand existing RAG:**

```python
# OLD (single domain):
from models.market_news_rag import MarketNewsRAG
rag = MarketNewsRAG()

# NEW (multi-domain):
from models.multi_domain_rag import MultiDomainRAG
rag = MultiDomainRAG()
rag.initialize_default_content()
```

### 3. Chatbot/API Responses

**Add agentic capabilities:**

```python
# In your chatbot or API endpoint
from models.function_calling_handler import call_real_estate_agent

response = call_real_estate_agent(user_input, context=conversation_history)
```

---

## Testing & Validation

### Unit Tests

Create test files for each module:

```python
# test_llm_recommendations.py
from models.llm_recommendation_engine import LLMRecommendationEngine

def test_recommendations():
    engine = LLMRecommendationEngine()
    prefs = {'location': 'Mumbai', 'budget_max': 100*100000}
    result = engine.generate_recommendations_with_llm(prefs)
    assert result['success'] == True
    assert len(result['recommendations']) > 0

# test_rag.py
from models.multi_domain_rag import MultiDomainRAG

def test_rag_search():
    rag = MultiDomainRAG()
    rag.initialize_default_content()
    results = rag.search("rera_laws", "buyer rights", top_k=3)
    assert len(results) > 0

# test_function_calling.py
from models.function_calling_handler import FunctionCallingHandler

def test_functions():
    handler = FunctionCallingHandler()
    assert len(handler.functions) >= 6
```

### Example Test Queries

```python
# Test RAG
queries = [
    "What are RERA buyer rights?",
    "How to identify property fraud?",
    "Which neighborhoods are safest?",
    "What market trends exist?"
]

# Test Recommendations
user_prefs = {
    'location': 'Pune',
    'budget_min': 30*100000,
    'budget_max': 60*100000,
    'bhk': 2
}

# Test Function Calling
agent_queries = [
    "Find 2 BHK in Mumbai under 1 Cr",
    "Check fraud risks for this property ID",
    "What's the market trend inBangalore?"
]
```

---

## Performance & Optimization

### Recommendations
- **Latency**: 2-5 seconds (LLM + function calls)
- **Optimization**: Cache function results, batch similar queries

### RAG
- **Search Time**: 100-500ms
- **Optimization**: Limit top_k results, use domain-specific searches

### Function Calling
- **Latency**: 3-10 seconds (depends on tool quantity)
- **Optimization**: Parallel tool execution, caching

---

## Troubleshooting

### LLM Recommendations Not Working

```python
# Check configuration
from models.llm_recommendation_engine import LLMRecommendationEngine
engine = LLMRecommendationEngine()
print(f"LLM Available: {engine.use_llm}")
print(f"Client Initialized: {engine.client is not None}")

# If False, check:
# 1. OPENAI_API_KEY is set
# 2. Package openai is installed
# 3. API key is valid
```

### RAG Not Available

```python
from models.multi_domain_rag import MultiDomainRAG
rag = MultiDomainRAG()
print(f"RAG Available: {rag.available}")

# If False, install:
# pip install chromadb sentence-transformers
```

### Function Calling Errors

```python
from models.function_calling_handler import FunctionCallingHandler
handler = FunctionCallingHandler()
print(f"Functions Registered: {list(handler.functions.keys())}")
print(f"LLM Available: {handler.use_llm}")
```

---

## Cost Analysis

### Estimated Monthly Costs (at 1000 queries/month)

| Feature | Queries/Month | Cost/Query | Monthly Cost |
|---------|--------------|-----------|-------------|
| LLM Recommendations | 1000 | ₹0.10 | ₹100 |
| RAG Search | 5000 | ₹0 (local) | ₹0 |
| Function Calling | 1000 | ₹0.15 | ₹150 |
| **Total** | **7000** | **-** | **~₹250** |

---

## Future Enhancements

1. **Fine-tuned Models**: Train custom embeddings for real estate domain
2. **Streaming Responses**: Stream LLM responses for better UX
3. **Memory Management**: Add conversation history for context
4. **Analytics**: Track which functions/tools are most used
5. **Custom Tools**: Add domain-specific tools for your use cases
6. **Multi-language**: Support Hindi, Marathi, Tamil for local accessibility

---

## Support & Documentation

- OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling
- ChromaDB: https://docs.trychroma.com/
- Sentence Transformers: https://www.sbert.net/

---

**Last Updated**: April 4, 2026
**Version**: 1.0
**Status**: Production Ready ✅
