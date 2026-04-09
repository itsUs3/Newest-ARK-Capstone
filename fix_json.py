import re

# Read the corrupted file
with open("Datasets/reddit_social_posts.json", "r", encoding='utf-8') as f:
    content = f.read()

# Find the first complete JSON array
# Look for pattern: [...complete array...]
match = re.search(r'^\[\s*\{.*?\}\s*\]', content, re.DOTALL)

if match:
    first_array = match.group(0)
    
    # Try to parse it
    import json
    try:
        data = json.loads(first_array)
        print(f"✓ Extracted valid JSON with {len(data)} records")
        
        # Save it back (overwriting the corrupted file)
        with open("Datasets/reddit_social_posts.json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved fixed file")
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON error in extracted array: {e}")
else:
    print("✗ Could not find valid JSON array pattern")

