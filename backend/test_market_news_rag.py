"""
Test script for Market News RAG endpoints
Run this to verify the RAG system is working correctly
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.market_news_rag import MarketNewsRAG
import config
import json


def test_retrieval():
    """Test basic retrieval functionality"""
    print("=" * 60)
    print("TEST 1: Retrieve Market News for Mumbai")
    print("=" * 60)
    
    rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
    
    articles = rag.retrieve_relevant_news(
        location="Mumbai",
        n_results=5
    )
    
    print(f"\nFound {len(articles)} articles for Mumbai:\n")
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Impact Score: {article['impact_score']}")
        print(f"   Relevance: {article['relevance_score']:.2f}")
        print(f"   Date: {article['date']}")
        print()
    
    return articles


def test_specific_query():
    """Test retrieval with specific query"""
    print("=" * 60)
    print("TEST 2: Search for Metro News in Andheri")
    print("=" * 60)
    
    rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
    
    articles = rag.retrieve_relevant_news(
        location="Andheri",
        query="metro",
        n_results=3
    )
    
    print(f"\nFound {len(articles)} articles about metro in Andheri:\n")
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   Impact Score: {article['impact_score']}")
        print()
    
    return articles


def test_alert_generation():
    """Test alert generation"""
    print("=" * 60)
    print("TEST 3: Generate Market Alert for Bangalore")
    print("=" * 60)
    
    rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
    
    # Get articles
    articles = rag.retrieve_relevant_news(
        location="Bangalore",
        n_results=5
    )
    
    # Generate alert
    alert = rag.generate_alert(
        location="Bangalore",
        articles=articles
    )
    
    print(f"\nAlert Summary:\n{alert['alert_summary']}\n")
    print(f"Impact Level: {alert['impact_level']}")
    print(f"Average Impact Score: {alert['avg_impact_score']}")
    print(f"\nRecommendation:\n{alert['recommendation']}\n")
    
    return alert


def test_trending_locations():
    """Test trending locations"""
    print("=" * 60)
    print("TEST 4: Get Trending Locations")
    print("=" * 60)
    
    rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
    
    trending = rag.get_trending_locations(top_n=10)
    
    print(f"\nTop {len(trending)} Trending Locations:\n")
    for i, loc in enumerate(trending, 1):
        print(f"{i}. {loc['location']}")
        print(f"   News Count: {loc['news_count']}")
        print(f"   Avg Impact: {loc['avg_impact']:.2f}")
        print(f"   Trend Score: {loc['trend_score']:.2f}")
        print()
    
    return trending


def test_property_impact():
    """Test property impact analysis"""
    print("=" * 60)
    print("TEST 5: Analyze Property Impact")
    print("=" * 60)
    
    rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)
    
    # Sample properties
    properties = [
        {"id": "prop_1", "location": "Andheri West"},
        {"id": "prop_2", "location": "Whitefield, Bangalore"},
        {"id": "prop_3", "location": "Hinjewadi, Pune"}
    ]
    
    print(f"\nAnalyzing impact for {len(properties)} properties:\n")
    
    results = []
    for prop in properties:
        location = prop["location"]
        articles = rag.retrieve_relevant_news(location=location, n_results=3)
        alert = rag.generate_alert(location=location, articles=articles)
        
        results.append({
            "property_id": prop["id"],
            "location": location,
            "alert": alert
        })
        
        print(f"Property: {prop['id']} ({location})")
        print(f"  Impact Level: {alert['impact_level']}")
        print(f"  News Articles: {len(alert['articles'])}")
        print(f"  {alert['recommendation'][:100]}...")
        print()
    
    return results


def test_all():
    """Run all tests"""
    try:
        print("\n[*] Starting Market News RAG Tests\n")
        
        # Test 1: Basic retrieval
        test_retrieval()
        
        # Test 2: Specific query
        test_specific_query()
        
        # Test 3: Alert generation
        test_alert_generation()
        
        # Test 4: Trending locations
        test_trending_locations()
        
        # Test 5: Property impact
        test_property_impact()
        
        print("=" * 60)
        print("[SUCCESS] ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nThe RAG system is working correctly!")
        print("\nYou can now:")
        print("1. Start the FastAPI server: uvicorn main:app --reload")
        print("2. Access endpoints at http://localhost:8000/api/genai/market-alerts/{location}")
        print("3. View API docs at http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_all()
