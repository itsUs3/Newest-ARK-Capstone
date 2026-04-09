"""
Test the full social intelligence pipeline with location extraction
"""
import sys
sys.path.insert(0, 'backend')
import os
os.chdir('backend')

# Suppress TensorFlow warnings
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from models.social.social_intelligence import SocialIntelligenceEngine
from collections import Counter

print("=" * 80)
print("FINAL TEST: Different areas should give different results")
print("=" * 80)

engine = SocialIntelligenceEngine()

test_areas = ["Bandra", "Andheri", "Pune", "Hyderabad", "Bangalore", "Gurgaon"]

results = {}

for area in test_areas:
    print(f"\n[{area}] Analyzing...")
    try:
        result = engine.analyze_area(area, top_k=3)
        results[area] = {
            "score": result.get("social_score"),
            "sentiment": result.get("overall_sentiment"),
            "posts": result.get("data_availability", {}).get("post_count"),
            "aspects": {k: v.get("label") for k, v in result.get("aspect_analysis", {}).items()},
            "sample_subreddit": result.get("top_discussions", [{}])[0].get("subreddit", "N/A") if result.get("top_discussions") else "N/A"
        }
        print(f"  ✓ Score: {results[area]['score']}, Posts: {results[area]['posts']}, Subreddit: r/{results[area]['sample_subreddit']}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results[area] = None

print("\n" + "=" * 80)
print("RESULTS COMPARISON")
print("=" * 80)

if results:
    scores = [results[area]["score"] for area in test_areas if results[area]]
    sentiments = [results[area]["sentiment"] for area in test_areas if results[area]]
    posts_counts = [results[area]["posts"] for area in test_areas if results[area]]
    
    print(f"\nScores: {scores}")
    print(f"  Unique: {len(set(scores))}, All same? {len(set(scores)) == 1}")
    
    print(f"\nSentiments: {sentiments}")
    print(f"  Unique: {len(set(sentiments))}, All same? {len(set(sentiments)) == 1}")
    
    print(f"\nPost counts: {posts_counts}")
    print(f"  Unique: {len(set(posts_counts))}, All same? {len(set(posts_counts)) == 1}")
    
    print("\n" + "=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    
    for area in test_areas:
        if results[area]:
            r = results[area]
            print(f"\n{area}:")
            print(f"  Social Score: {r['score']}/10")
            print(f"  Sentiment: {r['sentiment']}")
            print(f"  Posts retrieved: {r['posts']}")
            print(f"  Sample from: r/{r['sample_subreddit']}")
            print(f"  Aspects: {r['aspects']}")

