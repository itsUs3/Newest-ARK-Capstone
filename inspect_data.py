import json
from pathlib import Path
from collections import Counter

reddit_path = Path("Datasets/reddit_social_posts.json")
data = json.loads(reddit_path.read_text(encoding='utf-8'))

print("=" * 80)
print("REDDIT DATA QUALITY REPORT")
print("=" * 80)

print(f"\nTotal records: {len(data)}")

# Check location tags
location_counter = Counter()
for record in data:
    tags = tuple(sorted(record.get("location_tags", [])))
    location_counter[tags] += 1

print(f"\nLocation tag combinations ({len(location_counter)} unique):")
for tags, count in location_counter.most_common(15):
    print(f"  {tags}: {count} records ({100*count//len(data)}%)")

# Check subreddits
subreddit_counter = Counter(r.get("subreddit", "unknown") for r in data)
print(f"\nSubreddit distribution:")
for sub, count in subreddit_counter.most_common(15):
    print(f"  r/{sub}: {count} records")

# Sample records
print(f"\n" + "=" * 80)
print("SAMPLE RECORDS")
print("=" * 80)

for i in range(min(3, len(data))):
    r = data[i]
    print(f"\n[{i}]")
    print(f"  Location tags: {r.get('location_tags', [])}")
    print(f"  Subreddit: r/{r.get('subreddit', 'unknown')}")
    print(f"  Text: {r.get('text', '')[:150]}...")

