"""
Recreate the Reddit posts dataset with proper location tags based on subreddit
"""
import json
from datetime import datetime, timedelta
import random

# Sample real estate discussions by subreddit
reddit_posts = {
    "mumbai": [
        {"title": "Bandra rent hike", "text": "Rent in Bandra has increased by 40% in the last year. Looking to move to Andheri or Powai for savings."},
        {"title": "Andheri vs Bandra", "text": "Thinking of Andheri - it's quiet, close to office, good schools. Bandra is too crowded and expensive now."},
        {"title": "Powai infrastructure", "text": "Powai is developing rapidly. New metro station coming. Good for future investment."},
        {"title": "Borivali safety concerns", "text": "Anyone live in Borivali? How's the safety situation? Considering moving there for affordability."},
        {"title": "Worli luxury living", "text": "Worli is premium but offers great waterfront properties and lifestyle. Best if budget allows."},
        {"title": "Chembur underrated area", "text": "Chembur doesn't get enough attention. Good connectivity, less crowded than Bandra, cleaner."},
    ],
    "delhi": [
        {"title": "Gurugram traffic nightmare", "text": "Gurugram is drowning in traffic. Commute times are unbearable even for short distances."},
        {"title": "Noida affordable option", "text": "Noida prices are reasonable but pollution levels are concerning according to AQI reports."},
        {"title": "Delhi pricing", "text": "Property prices in Delhi are skyrocketing. Everyone recommending satellite cities like Gurugram."},
    ],
    "bangalore": [
        {"title": "Whitefield tech hub", "text": "Whitefield is the IT hub. Great for tech professionals. Good cafes and nightlife."},
        {"title": "Koramangala expensive", "text": "Koramangala is the coolest area but prices reflect that. Premium for lifestyle and connectivity."},
        {"title": "Bangalore weather", "text": "Bangalore's weather is excellent year-round, making it ideal for living. Unlike Delhi's extremes."},
        {"title": "Electronics City commute", "text": "Electronics City traffic is terrible during peak hours. Need good time management."},
    ],
    "hyderabad": [
        {"title": "Gachibowli growing", "text": "Gachibowli is booming with tech companies. Infrastructure and amenities are improving."},
        {"title": "Hitech City lifestyle", "text": "Hitech City offers modern living with good restaurants, shopping, and connectivity."},
        {"title": "Kondapur budget option", "text": "Kondapur is affordable compared to other IT hubs. Good emerging area."},
        {"title": "Hyderabad affordability", "text": "Hyderabad offers best value for money among major Indian cities. High living standards at lower cost."},
    ],
    "pune": [
        {"title": "Hinjawadi IT corridor", "text": "Hinjawadi is the IT hub of Pune. Good for professionals, but traffic during rush hours."},
        {"title": "Kharadi residential", "text": "Kharadi is more residential and peaceful. Good for families than Hinjawadi."},
        {"title": "Wakad development", "text": "Wakad is developing rapidly. New malls and restaurants are opening monthly."},
        {"title": "Viman Nagar lifestyle", "text": "Viman Nagar offers a good balance of affordability and lifestyle. Underrated gem."},
    ],
    "gurgaon": [
        {"title": "DLF Phase 2 premium", "text": "DLF Phase 2 is one of the priciest areas in Gurugram but offers excellent security and amenities."},
        {"title": "Gurugram expansion", "text": "Gurugram is expanding rapidly. New sectors developing but traffic remains a concern."},
    ],
    "noida": [
        {"title": "Sector 137 value", "text": "Sector 137 offers good value for money with improving infrastructure."},
        {"title": "Noida pollution", "text": "Pollution is a major concern in Noida. Air quality often goes into the 'hazardous' category."},
    ],
    "india": [
        {"title": "Metro expansion impact", "text": "Metro expansion across Indian cities is changing property valuations positively."},
        {"title": "NRI housing demand", "text": "NRIs showing increased interest in tier-2 cities for property investment."},
    ]
}

# Subreddit to location mapping
subreddit_locations = {
    "mumbai": ["Bandra West Mumbai", "Andheri West Mumbai", "Powai Mumbai"],
    "delhi": ["Gurugram", "Noida"],
    "bangalore": ["Whitefield Bengaluru", "Koramangala Bengaluru"],
    "hyderabad": ["Gachibowli Hyderabad", "Hitech City Hyderabad"],
    "pune": ["Hinjawadi Pune", "Kharadi Pune"],
    "gurgaon": ["DLF Phase 2 Gurugram", "Gurugram"],
    "noida": ["Sector 137 Noida"],
    "india": ["Bandra West Mumbai"],
}

# Generate dataset
posts = []
post_id = 0

for subreddit, discussions in reddit_posts.items():
    for discussion in discussions:
        post_id += 1
        
        # Create a post
        post = {
            "id": f"post_{post_id}",
            "text": f"{discussion['title']}\n\n{discussion['text']}",
            "subreddit": subreddit,
            "timestamp": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
            "location_tags": subreddit_locations.get(subreddit, ["India"]),
            "upvotes": random.randint(5, 500),
            "url": f"https://reddit.com/r/{subreddit}/comments/{post_id}",
            "source_type": "generated_sample"
        }
        posts.append(post)

# Save
output_path = "Datasets/reddit_social_posts.json"
with open(output_path, "w", encoding='utf-8') as f:
    json.dump(posts, f, indent=2, ensure_ascii=False)

print(f"Created {len(posts)} posts across {len(reddit_posts)} subreddits")
print(f"Saved to {output_path}")

# Verify locations are diverse
from collections import Counter
location_counter = Counter()
for post in posts:
    tags = tuple(sorted(post.get("location_tags", [])))
    location_counter[tags] += 1

print(f"\nLocation diversity: {len(location_counter)} unique combinations")
for tags, count in location_counter.most_common():
    print(f"  {tags}: {count} posts")

