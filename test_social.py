#!/usr/bin/env python3
"""Test script for Social Intelligence feature"""
import sys
import os
import traceback

# Add backend to path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

print("=" * 60)
print("SOCIAL INTELLIGENCE FEATURE TEST")
print("=" * 60)

# Test 1: Import modules
print("\n[TEST 1] Importing modules...")
try:
    import config
    print(f"  Config loaded: BASE_DIR={config.BASE_DIR}")
    print(f"  Reddit store path: {config.SOCIAL_REDDIT_STORE_PATH}")
    print(f"  FAISS dir: {config.SOCIAL_FAISS_DIR}")
except Exception as e:
    print(f"  ERROR importing config: {e}")
    traceback.print_exc()

# Test 2: Check data file
print("\n[TEST 2] Checking data files...")
try:
    from pathlib import Path
    reddit_path = Path(config.SOCIAL_REDDIT_STORE_PATH)
    print(f"  Reddit store exists: {reddit_path.exists()}")
    if reddit_path.exists():
        import json
        data = json.loads(reddit_path.read_text(encoding='utf-8'))
        print(f"  Records count: {len(data)}")
        if data:
            print(f"  Sample record keys: {list(data[0].keys())}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 3: Location normalizer
print("\n[TEST 3] Testing location normalizer...")
try:
    from models.social.location_normalizer import LocationNormalizer, KNOWN_AREA_MAP
    normalizer = LocationNormalizer(KNOWN_AREA_MAP)
    result = normalizer.normalize_location("bandra")
    print(f"  'bandra' normalized to: {result}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

# Test 4: Sentence Transformers
print("\n[TEST 4] Testing sentence-transformers...")
try:
    from sentence_transformers import SentenceTransformer
    print("  SentenceTransformer imported successfully")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 5: FAISS
print("\n[TEST 5] Testing FAISS...")
try:
    import faiss
    print("  FAISS imported successfully")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 6: Full engine test
print("\n[TEST 6] Testing SocialIntelligenceEngine...")
try:
    from models.social.social_intelligence import SocialIntelligenceEngine
    print("  Creating engine...")
    engine = SocialIntelligenceEngine()
    print("  Engine created successfully")
    
    print("  Running analyze_area('bandra')...")
    result = engine.analyze_area('bandra', top_k=3)
    
    print(f"  Result keys: {list(result.keys())}")
    print(f"  Area: {result.get('area')}")
    print(f"  Data availability: {result.get('data_availability')}")
    print(f"  Summary: {result.get('summary', 'N/A')[:100]}...")
    print(f"  Aspect analysis: {result.get('aspect_analysis')}")
    print(f"  Top discussions count: {len(result.get('top_discussions', []))}")
except Exception as e:
    print(f"  ERROR: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
