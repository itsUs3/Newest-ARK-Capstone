import json
import shutil
from pathlib import Path

from models.social import SocialIntelligenceEngine


def main():
    sample_posts = [
        {
            "id": "bandra_1",
            "text": "Living in Bandra West is fun because the cafes and nightlife are great, but rent is expensive and parking is awful.",
            "subreddit": "mumbai",
            "timestamp": "2026-03-15T10:00:00",
            "location_tags": ["Bandra West Mumbai"],
            "upvotes": 22,
            "url": "https://reddit.com/r/mumbai/bandra_1",
        },
        {
            "id": "bandra_2",
            "text": "Bandra East feels decently connected and mostly safe, though traffic gets bad during office hours.",
            "subreddit": "mumbai",
            "timestamp": "2026-03-12T10:00:00",
            "location_tags": ["Bandra East Mumbai"],
            "upvotes": 13,
            "url": "https://reddit.com/r/mumbai/bandra_2",
        },
        {
            "id": "bandra_3",
            "text": "If you can afford Bandra, lifestyle is great. Safety is decent, but it is definitely not a budget-friendly area.",
            "subreddit": "india",
            "timestamp": "2026-02-20T10:00:00",
            "location_tags": ["Bandra West Mumbai"],
            "upvotes": 9,
            "url": "https://reddit.com/r/india/bandra_3",
        },
    ]

    temp_path = Path(__file__).resolve().parent / "temp_social_smoke"
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)
    temp_path.mkdir(parents=True, exist_ok=True)
    try:
        store_path = temp_path / "reddit_social_posts.json"
        store_path.write_text(json.dumps(sample_posts), encoding="utf-8")

        engine = SocialIntelligenceEngine(
            data_path=str(store_path),
            faiss_dir=str(temp_path / "faiss_social"),
        )
        result = engine.analyze_area("Bandra", top_k=3)

        assert result["data_availability"]["status"] == "ok"
        assert result["area"] == "Bandra"
        assert result["top_discussions"]
        assert result["aspect_analysis"]["cost"]["label"] in {"negative", "mixed"}
        assert result["aspect_analysis"]["lifestyle"]["label"] in {"positive", "mixed"}
        print("SOCIAL_ANALYSIS_SMOKE_OK")
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


if __name__ == "__main__":
    main()
