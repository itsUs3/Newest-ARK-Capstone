"""
Integration examples and usage guide for GenAI features:
1. LLM-based Recommendations
2. Multi-Domain RAG
3. Function Calling / Tool Use
"""

import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# FEATURE 1: LLM-Based Recommendations with Function Calling
# ============================================================================

def example_llm_recommendations():
    """
    Example: Generate personalized property recommendations using LLM
    Uses OpenAI's function calling to fetch and analyze properties
    """
    print("\n" + "="*80)
    print("FEATURE 1: LLM-Based Recommendations with Function Calling")
    print("="*80)
    
    from models.llm_recommendation_engine import LLMRecommendationEngine
    
    # Initialize the LLM recommendation engine
    engine = LLMRecommendationEngine(use_llm=True)
    
    # Define user preferences
    user_preferences = {
        'budget_min': 50 * 100000,         # 50 Lakhs
        'budget_max': 150 * 100000,        # 150 Lakhs
        'location': 'Mumbai',
        'bhk': 2,
        'amenities': ['gym', 'parking', 'security'],
        'max_commute_minutes': 30,
        'family_size': 4,
        'work_location': 'Bandra'
    }
    
    print("\nUser Preferences:")
    print(json.dumps(user_preferences, indent=2))
    
    # Generate recommendations with LLM + function calling
    print("\nGenerating personalized recommendations...")
    result = engine.generate_recommendations_with_llm(
        user_preferences,
        context="First-time homebuyer, needs good schools nearby"
    )
    
    print("\n📋 LLM-Generated Recommendation:")
    print("-" * 60)
    print(result.get('recommendations', 'No recommendations generated'))
    print("-" * 60)
    
    # Also get structured recommendations
    recommendations = engine.get_recommendations(user_preferences)
    print(f"\n✅ Found {len(recommendations)} top matching properties:")
    for i, prop in enumerate(recommendations[:3], 1):
        print(f"\n{i}. {prop['title']}")
        print(f"   Location: {prop['location']}")
        print(f"   BHK: {prop['bhk']}, Price: ₹{prop.get('price', 0)/100000:.1f}L")
        print(f"   Rating: {prop.get('rating', 0):.1f}/5")


# ============================================================================
# FEATURE 2: Multi-Domain RAG System
# ============================================================================

def example_multi_domain_rag():
    """
    Example: Use multi-domain RAG to search across all knowledge domains
    Covers: Market News, RERA Laws, Fraud Patterns, Community Insights, etc.
    """
    print("\n" + "="*80)
    print("FEATURE 2: Multi-Domain RAG System")
    print("="*80)
    
    from models.multi_domain_rag import MultiDomainRAG
    
    # Initialize multi-domain RAG
    rag = MultiDomainRAG()
    
    if not rag.available:
        print("✗ RAG system not available (ChromaDB/embeddings not installed)")
        return
    
    # Initialize with default content
    print("\nInitializing RAG with default domain content...")
    rag.initialize_default_content()
    
    # Show domain summaries
    print("\n📊 Domain Collections Overview:")
    summaries = rag.get_all_summaries()
    for domain, summary in summaries.items():
        print(f"\n{domain.upper()}:")
        print(f"  - Description: {summary.get('description', 'N/A')}")
        print(f"  - Documents: {summary.get('document_count', 0)}")
    
    # Example 1: Search for RERA compliance information
    print("\n\n" + "-"*80)
    print("EXAMPLE 1: RERA Compliance Query")
    print("-"*80)
    
    rera_results = rag.search(
        domain="rera_laws",
        query="What are buyer rights and developer obligations?",
        top_k=3
    )
    
    print("\nTop RERA Law Results:")
    for i, (doc, similarity, meta) in enumerate(rera_results, 1):
        print(f"\n{i}. [Relevance: {similarity:.2%}]")
        print(f"   {doc[:150]}...")
        print(f"   (Category: {meta.get('category', 'General')})")
    
    
    # Example 2: Search for fraud patterns
    print("\n\n" + "-"*80)
    print("EXAMPLE 2: Fraud Detection Query")
    print("-"*80)
    
    fraud_results = rag.search(
        domain="fraud_patterns",
        query="How to identify property title fraud and fake documents?",
        top_k=3
    )
    
    print("\nFraud Pattern Warning Signs:")
    for i, (doc, similarity, meta) in enumerate(fraud_results, 1):
        print(f"\n⚠️  {i}. {doc[:100]}...")
        print(f"   Risk Level: {meta.get('risk_level', 'Unknown')}")
    
    
    # Example 3: Community insights
    print("\n\n" + "-"*80)
    print("EXAMPLE 3: Community Insights Query")
    print("-"*80)
    
    community_results = rag.search(
        domain="community",
        query="Which are the best neighborhoods for families in Mumbai?",
        top_k=3
    )
    
    print("\nTop Neighborhood Insights:")
    for i, (doc, similarity, meta) in enumerate(community_results, 1):
        print(f"\n{i}. {doc[:120]}...")
    
    
    # Example 4: Cross-domain search
    print("\n\n" + "-"*80)
    print("EXAMPLE 4: Cross-Domain Search")
    print("-"*80)
    
    query = "property purchase process and legal requirements"
    print(f"\nSearching across all domains for: '{query}'")
    
    all_results = rag.search_all_domains(query, top_k_per_domain=2)
    
    for domain, results in all_results.items():
        print(f"\n{domain.upper()}: {len(results)} results")
        for doc, sim, meta in results:
            print(f"  - [{sim:.1%}] {doc[:80]}...")


# ============================================================================
# FEATURE 3: Function Calling / Tool Use
# ============================================================================

def example_function_calling():
    """
    Example: Use function calling to enable LLM to take agentic actions
    The LLM can call tools like property search, market analysis, fraud assessment
    """
    print("\n" + "="*80)
    print("FEATURE 3: Function Calling & Tool Use")
    print("="*80)
    
    from models.function_calling_handler import call_real_estate_agent, FunctionCallingHandler
    
    print("\nAvailable Tools for LLM:")
    handler = FunctionCallingHandler()
    
    for func_name, func_info in handler.functions.items():
        func_def = func_info["definition"]["function"]
        print(f"\n🔧 {func_name}")
        print(f"   Description: {func_def['description']}")
        params = func_def.get("parameters", {}).get("properties", {})
        if params:
            print(f"   Parameters: {', '.join(params.keys())}")
    
    # Example 1: Property Search with Function Calling
    print("\n\n" + "-"*80)
    print("EXAMPLE 1: AI Agent Searches for Properties")
    print("-"*80)
    
    query = """
    I need to find a 2 BHK apartment in Bangalore with gym and parking facilities.
    My budget is ₹50 lakhs to ₹80 lakhs. Please search for suitable properties
    and analyze the current market trends in that location.
    """
    
    print(f"\nUser Query: {query.strip()}")
    print("\nAI Agent is thinking and using tools...")
    
    # This would call the LLM with function calling enabled
    # The LLM can autonomously call search_properties, analyze_market, etc.
    response = call_real_estate_agent(query)
    print(f"\n🤖 AI Agent Response:\n{response}")
    
    
    # Example 2: Fraud Risk Assessment
    print("\n\n" + "-"*80)
    print("EXAMPLE 2: Fraud Risk Assessment with Tools")
    print("-"*80)
    
    fraud_query = """
    I found a property in Delhi at ₹1 crore. The seller is asking for 
    full payment upfront before any documentation. The property is 
    not registered online. What are the risks?
    """
    
    print(f"\nUser Query: {fraud_query.strip()}")
    print("\nAI Agent is analyzing fraud risks...")
    
    response = call_real_estate_agent(
        fraud_query,
        context_info="Property discovered through online marketplace, seller unknown"
    )
    print(f"\n🤖 AI Agent Response:\n{response}")


# ============================================================================
# INTEGRATED EXAMPLE: Full Workflow
# ============================================================================

def example_integrated_workflow():
    """
    Complete workflow combining all three features:
    1. User searches for properties using LLM recommendations
    2. LLM uses function calling to search properties and analyze market
    3. RAG system provides RERA compliance and fraud pattern information
    4. Final recommendation includes all insights
    """
    print("\n" + "="*80)
    print("INTEGRATED EXAMPLE: Complete Real Estate Advisory Workflow")
    print("="*80)
    
    print("""
    SCENARIO: First-time homebuyer looking for an apartment in Pune
    
    WORKFLOW:
    1. User provides preferences
    2. LLM Recommendation Engine analyzes preferences
    3. Function Calling tools search properties, analyze market
    4. Multi-Domain RAG retrieves relevant RERA laws and fraud alerts
    5. Integrated response provides comprehensive recommendation
    """)
    
    print("\n" + "-"*80)
    print("STEP 1: User Input")
    print("-"*80)
    
    user_input = {
        "location": "Pune",
        "budget": "₹50L - ₹75L",
        "bhk": "2 BHK",
        "priorities": ["good schools", "safety", "low traffic"],
        "family_status": "married with 1 child"
    }
    
    print(json.dumps(user_input, indent=2))
    
    print("\n" + "-"*80)
    print("STEP 2: LLM Analysis & Function Calling")
    print("-"*80)
    
    print("""
    LLM is calling tools:
    ✓ search_properties(location='Pune', budget_range=[50L, 75L], bhk=2, amenities=['schools', 'security'])
    ✓ analyze_market(location='Pune', timeframe='1year')
    ✓ get_community_insights(location='Pune', aspects=['safety', 'schools', 'transit'])
    """)
    
    print("\n" + "-"*80)
    print("STEP 3: RAG System Retrieves Relevant Information")
    print("-"*80)
    
    print("""
    From RERA Laws Domain:
    - Buyer rights regarding possession timelines
    - Documentation requirements for property registration
    - Penalty clauses for builder delays
    
    From Fraud Patterns Domain:
    - Common fraud schemes in residential properties
    - Documents to verify independently
    - Red flags to watch for
    
    From Community Domain:
    - School quality and proximity
    - Safety ratings and demographics
    - Infrastructure and connectivity
    """)
    
    print("\n" + "-"*80)
    print("STEP 4: Integrated Recommendation")
    print("-"*80)
    
    final_recommendation = """
    🏠 RECOMMENDED PROPERTY:
    Location: Vadgaon Sheri, Pune
    Configuration: 2 BHK, 950 sq ft
    Price: ₹62 Lakhs
    
    ✅ WHY THIS PROPERTY:
    • Within budget and meets space requirements
    • Top-rated school (Vidyapith) within 1.5 km
    • Safe neighborhood with low traffic
    • Good metro connectivity (under planning)
    
    ⚖️ LEGAL CHECKLIST (from RERA):
    □ Verify builder registration with MAHA-RERA
    □ Check possession timeline in agreement
    □ Review GST and maintenance charges
    □ Confirm separate bank accounts for project funds
    
    ⚠️ FRAUD RISK ASSESSMENT:
    • Risk Level: LOW
    • Builder: Reputed developer (verified)
    • Documentation: All standard papers present
    • No red flags detected
    
    💡 NEXT STEPS:
    1. Get legal opinion on sales deed
    2. Conduct site inspection personally
    3. Negotiate maintenance charges
    4. Check neighbor feedback on community app
    """
    
    print(final_recommendation)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "█"*80)
    print("█ GENAI FEATURES INTEGRATION EXAMPLES ".ljust(79) + "█")
    print("█"*80)
    
    # Enable/disable examples based on what you want to run
    EXAMPLES_TO_RUN = {
        'llm_recommendations': True,      # Feature 1
        'multi_domain_rag': True,         # Feature 2
        'function_calling': True,         # Feature 3
        'integrated_workflow': True       # Combined example
    }
    
    try:
        if EXAMPLES_TO_RUN['llm_recommendations']:
            example_llm_recommendations()
    except Exception as e:
        print(f"✗ LLM Recommendations example failed: {e}")
    
    try:
        if EXAMPLES_TO_RUN['multi_domain_rag']:
            example_multi_domain_rag()
    except Exception as e:
        print(f"✗ Multi-Domain RAG example failed: {e}")
    
    try:
        if EXAMPLES_TO_RUN['function_calling']:
            example_function_calling()
    except Exception as e:
        print(f"✗ Function Calling example failed: {e}")
    
    try:
        if EXAMPLES_TO_RUN['integrated_workflow']:
            example_integrated_workflow()
    except Exception as e:
        print(f"✗ Integrated Workflow example failed: {e}")
    
    print("\n" + "█"*80)
    print("█ END OF EXAMPLES ".ljust(79) + "█")
    print("█"*80 + "\n")
