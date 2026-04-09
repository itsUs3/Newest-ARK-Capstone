from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
import requests

try:
    from apify_client import ApifyClient
except Exception:
    ApifyClient = None

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.social.location_normalizer import KNOWN_AREA_MAP, LocationNormalizer


load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class RedditIngestionPipeline:
    def __init__(self, store_path: Path):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.write_text("[]", encoding="utf-8")

        self.apify_token = os.getenv("APIFY_TOKEN", "").strip()
        self.actor_id = os.getenv("APIFY_REDDIT_ACTOR_ID", "").strip()
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
        self.normalizer = LocationNormalizer(KNOWN_AREA_MAP)

    def _read_existing(self) -> List[Dict]:
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write_records(self, records: List[Dict]) -> None:
        self.store_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    def _build_queries(self, areas: List[str]) -> List[Dict]:
        subreddits = ["mumbai", "india", "bangalore", "hyderabad", "pune", "delhi", "gurgaon"]
        queries = []
        for area in areas:
            normalized = self.normalizer.normalize_location(area)
            query_seed = normalized or [area]
            for location in query_seed:
                queries.append({
                    "area": area,
                    "location": location,
                    "queries": [
                        f"living in {location}",
                        f"rent in {location}",
                        f"buy flat in {location}",
                        f"is {location} safe",
                    ],
                    "subreddits": subreddits,
                })
        return queries

    def _fetch_from_apify(self, query_jobs: List[Dict]) -> List[Dict]:
        if ApifyClient is None:
            raise RuntimeError("apify-client is not installed. Add it to the backend environment before running ingestion.")
        if not self.apify_token:
            raise RuntimeError("APIFY_TOKEN is missing. Set it in backend/.env before running Reddit ingestion.")
        if not self.actor_id:
            raise RuntimeError("APIFY_REDDIT_ACTOR_ID is missing. Set the Reddit actor id in backend/.env.")

        client = ApifyClient(self.apify_token)
        collected_items: List[Dict] = []
        for job in query_jobs:
            actor_input = {
                "searches": job["queries"],
                "subreddits": job["subreddits"],
                "maxItems": 40,
                "sort": "new",
                "time": "year",
            }
            logger.info(f"Running Apify Reddit actor for {job['location']}")
            run = client.actor(self.actor_id).call(run_input=actor_input)
            dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            for item in dataset_items:
                collected_items.append(self._normalize_item(item, job["location"]))
        return collected_items

    def _normalize_item(self, item: Dict, location_hint: str) -> Dict:
        text_parts = [item.get("title", ""), item.get("body", ""), item.get("text", ""), item.get("comment", "")]
        text = " ".join(part.strip() for part in text_parts if part).strip()
        location_tags = self.normalizer.normalize_location(location_hint)
        return {
            "id": item.get("id") or item.get("postId") or item.get("url") or str(abs(hash(text))),
            "text": text,
            "subreddit": str(item.get("subreddit") or "").replace("r/", ""),
            "timestamp": item.get("createdAt") or item.get("timestamp") or datetime.now().isoformat(),
            "location_tags": location_tags,
            "score": item.get("score") or item.get("upvotes") or 0,
            "url": item.get("url") or item.get("permalink") or "",
            "source_type": "apify_reddit",
        }

    def _fetch_from_reddit_api(self, query_jobs: List[Dict]) -> List[Dict]:
        if not self.reddit_client_id or not self.reddit_client_secret:
            raise RuntimeError("Neither APIFY_TOKEN nor Reddit API credentials are configured for ingestion.")

        token_response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(self.reddit_client_id, self.reddit_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": "myNivasSocialIntelligence/1.0"},
            timeout=20,
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        headers = {
            "Authorization": f"bearer {access_token}",
            "User-Agent": "myNivasSocialIntelligence/1.0",
        }

        collected_items: List[Dict] = []
        for job in query_jobs:
            for subreddit in job["subreddits"]:
                for query in job["queries"]:
                    response = requests.get(
                        f"https://oauth.reddit.com/r/{subreddit}/search",
                        params={
                            "q": query,
                            "restrict_sr": 1,
                            "sort": "new",
                            "t": "year",
                            "limit": 20,
                        },
                        headers=headers,
                        timeout=20,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    for child in payload.get("data", {}).get("children", []):
                        data = child.get("data", {})
                        collected_items.append({
                            "id": data.get("id"),
                            "text": " ".join(filter(None, [data.get("title", ""), data.get("selftext", "")])).strip(),
                            "subreddit": data.get("subreddit", subreddit),
                            "timestamp": datetime.utcfromtimestamp(data.get("created_utc", 0)).isoformat(),
                            "location_tags": self.normalizer.normalize_location(job["location"]),
                            "score": data.get("score", 0),
                            "url": f"https://reddit.com{data.get('permalink', '')}",
                            "source_type": "reddit_api_ingestion",
                        })
        return collected_items

    def ingest(self, areas: List[str]) -> Dict:
        query_jobs = self._build_queries(areas)
        if self.apify_token and self.actor_id:
            fetched_records = self._fetch_from_apify(query_jobs)
        else:
            fetched_records = self._fetch_from_reddit_api(query_jobs)
        existing = self._read_existing()

        deduped: Dict[str, Dict] = {}
        for item in [*existing, *fetched_records]:
            key = str(item.get("id") or item.get("url") or hash(item.get("text", "")))
            deduped[key] = item

        merged_records = list(deduped.values())
        self._write_records(merged_records)
        try:
            from models.social import SocialIntelligenceEngine
            engine = SocialIntelligenceEngine(data_path=str(self.store_path))
            engine.rebuild_store()
        except Exception as exc:
            logger.warning(f"Unable to prebuild social FAISS store after ingestion: {exc}")
        logger.info(f"Stored {len(fetched_records)} new Reddit records. Total store size: {len(merged_records)}")
        return {
            "new_records": len(fetched_records),
            "total_records": len(merged_records),
            "store_path": str(self.store_path),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Reddit ingestion for the Social Intelligence Layer.")
    parser.add_argument("--areas", nargs="+", default=["Bandra", "Andheri", "Powai", "Whitefield", "Gachibowli"])
    parser.add_argument(
        "--store-path",
        default=str(Path(__file__).resolve().parents[2] / "Datasets" / "reddit_social_posts.json"),
    )
    args = parser.parse_args()

    pipeline = RedditIngestionPipeline(Path(args.store_path))
    result = pipeline.ingest(args.areas)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
