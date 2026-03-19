#!/usr/bin/env python3
"""
Test script for Cross-Modal Property Matching Integration
Verifies:
1. CrossModalMatcher loads correctly
2. FAISS indexing works
3. Amenity Matcher cross-modal methods work
4. API endpoint structure is correct
5. Results format is valid
"""

import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_cross_modal_matcher():
    """Test CrossModalMatcher class initialization and basic search"""
    logger.info("=" * 60)
    logger.info("TEST 1: CrossModalMatcher Initialization")
    logger.info("=" * 60)
    
    try:
        from models.cross_modal_matcher import CrossModalMatcher
        logger.info("✅ Successfully imported CrossModalMatcher")
        
        logger.info("Initializing CrossModalMatcher...")
        matcher = CrossModalMatcher()
        logger.info("✅ CrossModalMatcher initialized successfully")
        
        # Check stats
        stats = matcher.get_stats()
        logger.info(f"✅ Index stats: {stats}")
        
        if stats['total_properties'] > 0:
            logger.info(f"✅ Loaded {stats['total_properties']} properties")
        else:
            logger.warning("⚠️ No properties loaded!")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in CrossModalMatcher test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cross_modal_search():
    """Test actual cross-modal search functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Cross-Modal Search")
    logger.info("=" * 60)
    
    try:
        from models.cross_modal_matcher import CrossModalMatcher
        
        matcher = CrossModalMatcher()
        
        # Test text search
        logger.info("Testing text search with query: 'affordable flat'...")
        results = matcher.search_text("affordable flat", top_k=3)
        
        if results and 'matches' in results:
            logger.info(f"✅ Text search returned {len(results['matches'])} results")
            for i, match in enumerate(results['matches'], 1):
                logger.info(f"  [{i}] {match.get('name', 'Unknown')} - Score: {match.get('similarity_score', 0):.3f}")
            return True
        else:
            logger.error("❌ Text search returned invalid results")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in search test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_amenity_matcher_integration():
    """Test AmenityMatcher cross-modal integration"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: AmenityMatcher Cross-Modal Integration")
    logger.info("=" * 60)
    
    try:
        from models.amenity_matcher import AmenityMatcher
        
        logger.info("Initializing AmenityMatcher...")
        matcher = AmenityMatcher()
        logger.info("✅ AmenityMatcher initialized")
        
        # Test query optimization
        logger.info("Testing query optimization for 'Family with Kids'...")
        optimized = matcher.optimize_search_query("Family with Kids")
        logger.info(f"✅ Optimized query: {optimized[:80]}...")
        
        # Test cross-modal recommendations
        logger.info("Testing cross-modal recommendations...")
        results = matcher.get_cross_modal_recommendations(
            query="affordable apartment",
            lifestyle="Family with Kids",
            top_k=3,
            use_cross_modal=True
        )
        
        if results and results.get('success', True):
            logger.info(f"✅ Got {len(results.get('matches', []))} matches")
            logger.info(f"✅ Search type: {results.get('search_type', 'unknown')}")
            if results.get('montage'):
                logger.info(f"✅ Montage generated (size: {len(results['montage'])} chars base64)")
            return True
        else:
            logger.error(f"❌ Cross-modal recommendations failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in AmenityMatcher integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_request_models():
    """Test that API request models are properly defined"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: API Request Models")
    logger.info("=" * 60)
    
    try:
        # We can't import directly, but we can check the main.py file
        main_file = Path(__file__).parent / "main.py"
        
        if main_file.exists():
            content = main_file.read_text()
            
            # Check if CrossModalSearchRequest is defined
            if "class CrossModalSearchRequest" in content:
                logger.info("✅ CrossModalSearchRequest model found in main.py")
            else:
                logger.error("❌ CrossModalSearchRequest model NOT found in main.py")
                return False
            
            # Check if endpoint is defined
            if '@app.post("/api/genai/cross-modal-match")' in content:
                logger.info("✅ Cross-modal API endpoint found in main.py")
            else:
                logger.error("❌ Cross-modal API endpoint NOT found in main.py")
                return False
                
            return True
        else:
            logger.error(f"❌ Could not find main.py at {main_file}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking API models: {e}")
        return False


def test_frontend_integration():
    """Test that frontend has been updated"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Frontend Integration")
    logger.info("=" * 60)
    
    try:
        frontend_home = Path(__file__).parent.parent / "frontend" / "src" / "pages" / "Home.jsx"
        
        if frontend_home.exists():
            content = frontend_home.read_text()
            
            # Check if cross-modal search is in Home.jsx
            if "cross-modal-match" in content:
                logger.info("✅ Cross-modal API call found in Home.jsx")
            else:
                logger.error("❌ Cross-modal API call NOT found in Home.jsx")
                return False
            
            if "handleCrossModalSearch" in content:
                logger.info("✅ Cross-modal search handler found in Home.jsx")
            else:
                logger.error("❌ Cross-modal search handler NOT found in Home.jsx")
                return False
                
            if "lifestyleOptions" in content:
                logger.info("✅ Lifestyle options found in Home.jsx")
            else:
                logger.error("❌ Lifestyle options NOT found in Home.jsx")
                return False
                
            return True
        else:
            logger.error(f"❌ Could not find Home.jsx at {frontend_home}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking frontend: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("🚀 Starting Cross-Modal Integration Test Suite\n")
    
    tests = [
        ("CrossModalMatcher", test_cross_modal_matcher),
        ("Cross-Modal Search", test_cross_modal_search),
        ("AmenityMatcher Integration", test_amenity_matcher_integration),
        ("API Request Models", test_api_request_models),
        ("Frontend Integration", test_frontend_integration),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status:10} | {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All integration tests passed! Cross-modal search is ready.")
        return 0
    else:
        logger.error("⚠️ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
