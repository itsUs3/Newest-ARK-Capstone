#!/usr/bin/env python3
"""Quick test of Social Intelligence - location extraction and data diversity"""
import sys
import os
import json
sys.path.insert(0, 'backend')
os.chdir('backend')

from models.social.location_extractor import LocationExtractor
from pathlib import Path

print("=" * 80)
print("TESTING LOCATION EXTRACTION")
print("=" * 80)

# Load Reddit data
reddit_path = Path("../Datasets/reddit_social_posts.json")
data = json.loads(reddit_path.read_text(encoding='utf-8'))

print(f"\nTotal records: {len(data)}")

# Check what locations are currently in the data
location_counter = {}
for record in data[:50]:  # Check first 50
    tags = tuple(sorted(record.get("location_tags", [])))
    location_counter[tags] = location_counter.get(tags, 0) + 1

print(f"\nUnique location tag combinations in first 50 records:")
for tags, count in sorted(location_counter.items(), key=lambda x: x[1], reverse=True):
    print(f"  {tags}: {count} records")

# Try location extractor
extractor = LocationExtractor()
print(f"\n" + "=" * 80)
print("TRYING LOCATION EXTRACTION ON SAMPLE RECORDS")
print("=" * 80)

for i in range(min(5, len(data))):
    record = data[i]
    text = record.get("text", "")[:100]
    subreddit = record.get("subreddit", "unknown")
    
    # Try extracting
    extracted = extractor.extract_locations(record)
    
    print(f"\n[{i}] Subreddit: r/{subreddit}")
    print(f"    Text: {text}...")
    print(f"    Extracted locations: {extracted}")

