import json
from pathlib import Path

# Manual test without imports
reddit_path = Path("Datasets/reddit_social_posts.json")
data = json.loads(reddit_path.read_text(encoding='utf-8'))

# Define the subreddit -> location mapping
subreddit_location_map = {
    "mumbai": ["Bandra West Mumbai", "Andheri West Mumbai", "Powai Mumbai"],
    "delhi": ["Gurugram", "Noida"],
    "bangalore": ["Whitefield Bengaluru", "Koramangala Bengaluru"],
    "hyderabad": ["Gachibowli Hyderabad", "Hitech City Hyderabad"],
    "pune": ["Hinjawadi Pune", "Kharadi Pune"],
    "gurgaon": ["DLF Phase 2 Gurugram", "Gurugram"],
    "noida": ["Sector 137 Noida"],
    "india": ["Bandra West Mumbai"],
}

# Simulate the rebuild
print("=" * 80)
print("TESTING LOCATION EXTRACTION LOGIC")
print("=" * 80)

rebuilt_data = []
for record in data:
    subreddit = record.get("subreddit", "").lower().replace("r/", "").strip()
    new_locations = subreddit_location_map.get(subreddit, ["India"])
    
    updated_record = dict(record)
    updated_record["location_tags"] = new_locations
    rebuilt_data.append(updated_record)

# Check results
from collections import Counter

location_counter = Counter()
for record in rebuilt_data:
    tags = tuple(sorted(record.get("location_tags", [])))
    location_counter[tags] += 1

subreddit_counter = Counter()
for record in rebuilt_data:
    sub = record.get("subreddit", "india")
    locations = tuple(sorted(record.get("location_tags", [])))
    subreddit_counter[(sub, locations)] += 1

print(f"\nTotal records: {len(rebuilt_data)}")
print(f"\nUnique location combinations: {len(location_counter)}")
print(f"\nLocation tag distribution:")
for tags, count in location_counter.most_common(10):
    print(f"  {tags}: {count} records")

print(f"\n" + "=" * 80)
print("SUBREDDIT -> LOCATION MAPPING")
print("=" * 80)

for (sub, locs), count in sorted(subreddit_counter.items(), key=lambda x: -x[1])[:15]:
    print(f"r/{sub}: {locs} ({count} records)")

