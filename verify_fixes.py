"""Verify that location extraction fixes are working"""
import json
from pathlib import Path
from collections import Counter

reddit_path = Path("Datasets/reddit_social_posts.json")
data = json.loads(reddit_path.read_text(encoding='utf-8'))

print("=" * 80)
print("VERIFYING LOCATION EXTRACTION FIXES")
print("=" * 80)

# Check current state
location_counter = Counter()
subreddit_to_locations = {}

for record in data:
    tags = tuple(sorted(record.get("location_tags", [])))
    location_counter[tags] += 1
    
    sub = record.get("subreddit", "unknown")
    if sub not in subreddit_to_locations:
        subreddit_to_locations[sub] = tags

print(f"\n[CURRENT STATE]")
print(f"Total records: {len(data)}")
print(f"Unique location combinations: {len(location_counter)}")

if len(location_counter) == 1:
    print("\n❌ PROBLEM STILL EXISTS: All records have identical location tags!")
    print(f"   All tagged as: {list(location_counter.keys())[0]}")
else:
    print(f"\n✅ FIXED: Found {len(location_counter)} different location combinations!")
    print(f"\nLocation distribution:")
    for tags, count in location_counter.most_common():
        print(f"  {tags}: {count} records")

print(f"\n" + "=" * 80)
print("SUBREDDIT -> LOCATION MAPPING")
print("=" * 80)

for sub in sorted(subreddit_to_locations.keys()):
    tags = subreddit_to_locations[sub]
    count = sum(1 for r in data if r.get("subreddit") == sub)
    print(f"r/{sub:15} ({count:3} records) -> {tags}")

# Show expected vs actual
print(f"\n" + "=" * 80)
print("EXPECTED vs ACTUAL")
print("=" * 80)

expected_map = {
    "mumbai": ("Andheri West Mumbai", "Bandra West Mumbai", "Powai Mumbai"),
    "delhi": ("Gurugram", "Noida"),
    "bangalore": ("Koramangala Bengaluru", "Whitefield Bengaluru"),
    "hyderabad": ("Gachibowli Hyderabad", "Hitech City Hyderabad"),
    "pune": ("Hinjawadi Pune", "Kharadi Pune"),
    "gurgaon": ("DLF Phase 2 Gurugram", "Gurugram"),
    "noida": ("Sector 137 Noida",),
    "india": ("Bandra West Mumbai",),
}

all_correct = True
for sub, expected in expected_map.items():
    actual = subreddit_to_locations.get(sub, ())
    expected_sorted = tuple(sorted(expected))
    actual_sorted = tuple(sorted(actual)) if actual else ()
    
    match = "✅" if expected_sorted == actual_sorted else "❌"
    print(f"{match} r/{sub:12} Expected: {expected_sorted}")
    print(f"                   Actual:   {actual_sorted}")
    
    if expected_sorted != actual_sorted:
        all_correct = False

print(f"\n" + "=" * 80)
if all_correct:
    print("✅ ALL FIXES VERIFIED - Location extraction is working correctly!")
else:
    print("❌ MISMATCH FOUND - Some locations don't match expected mapping")
print("=" * 80)

