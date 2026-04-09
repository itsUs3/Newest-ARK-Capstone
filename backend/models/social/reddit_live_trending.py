"""
Fetch real-time trending posts from area-specific Reddit subreddits.
This replaces the static "top discussions" with actual live trending topics.
"""

import logging
import os
import requests
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RedditLiveClient:
    """Fetch trending posts from Reddit using the API with provided credentials."""

    # Area -> List of subreddit community names
    AREA_SUBREDDIT_MAP = {
        "bandra": ["mumbai", "india"],
        "andheri": ["mumbai", "india"],
        "powai": ["mumbai", "india"],
        "borivali": ["mumbai", "india"],
        "worli": ["mumbai", "india"],
        "chembur": ["mumbai", "india"],
        "whitefield": ["bangalore", "india"],
        "koramangala": ["bangalore", "india"],
        "indiranagar": ["bangalore", "india"],
        "gachibowli": ["hyderabad", "india"],
        "hitech city": ["hyderabad", "india"],
        "kondapur": ["hyderabad", "india"],
        "hinjawadi": ["pune", "india"],
        "kharadi": ["pune", "india"],
        "wakad": ["pune", "india"],
        "gurugram": ["gurgaon", "india"],
        "gurgaon": ["gurgaon", "india"],
        "noida": ["delhi", "india"],
        "delhi": ["delhi", "india"],
    }

    def __init__(self):
        self.client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
        self.access_token = None
        self.token_expiry = None

        if self.client_id and self.client_secret:
            self._refresh_token()

    def _refresh_token(self) -> bool:
        """Get or refresh OAuth token from Reddit API."""
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit API credentials not configured. Live trending disabled.")
            return False

        try:
            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": "myNivasSocialIntelligence/1.0"},
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.token_expiry = datetime.now().timestamp() + token_data.get("expires_in", 3600)
            logger.info("Reddit API token refreshed successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to get Reddit API token: {e}")
            self.access_token = None
            return False

    def _ensure_token(self) -> bool:
        """Ensure we have a valid token."""
        if not self.access_token:
            return self._refresh_token()

        # Refresh if expiring soon (within 5 min)
        if self.token_expiry and datetime.now().timestamp() > self.token_expiry - 300:
            return self._refresh_token()

        return True

    def get_trending_posts(
        self, subreddits: List[str], area_keyword: str = "", limit: int = 5
    ) -> List[Dict]:
        """
        Fetch trending/hot posts from subreddits.

        Args:
            subreddits: List of subreddit names to search
            area_keyword: Keyword to filter posts (optional - lenient matching)
            limit: Number of posts to return

        Returns:
            List of trending post dicts with title, selftext, subreddit, score, url
        """
        if not self._ensure_token():
            logger.warning("No Reddit API token available. Trending posts unavailable.")
            return []

        headers = {
            "Authorization": f"bearer {self.access_token}",
            "User-Agent": "myNivasSocialIntelligence/1.0",
        }

        all_posts = []

        for subreddit in subreddits:
            try:
                # Fetch hot posts from subreddit
                url = f"https://oauth.reddit.com/r/{subreddit}/hot"
                response = requests.get(
                    url,
                    params={"limit": limit * 4},  # Get more to filter
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()

                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    text = post_data.get("selftext", "")

                    # Lenient filtering: if area_keyword and subreddit is not generic (like 'india'),
                    # try to find keyword. But allow area-subreddit posts anyway.
                    # e.g., posts from r/mumbai are relevant to Bandra, Borivali, etc.
                    content = f"{title} {text}".lower()

                    # Skip if keyword filtering is too important
                    # Only skip if subreddit is generic AND keyword not found
                    if area_keyword and subreddit != area_keyword and subreddit in ["india"]:
                        if area_keyword.lower() not in content:
                            continue

                    all_posts.append({
                        "id": post_data.get("id"),
                        "title": title,
                        "text": text,
                        "selftext": text,
                        "subreddit": subreddit,
                        "score": post_data.get("score", 0),
                        "upvotes": post_data.get("score", 0),
                        "url": f"https://reddit.com{post_data.get('permalink', '')}",
                        "timestamp": datetime.utcfromtimestamp(post_data.get("created_utc", 0)).isoformat(),
                        "source": "reddit_live_trending",
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch posts from r/{subreddit}: {e}")
                continue

        # Sort by score and return top N
        all_posts.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_posts[:limit]

    def get_trending_for_area(self, area: str, limit: int = 5) -> List[Dict]:
        """
        Get trending posts for a specific area.

        Args:
            area: Area name (e.g., "Bandra", "Powai")
            limit: Number of posts to return

        Returns:
            List of trending posts relevant to the area
        """
        area_lower = area.lower().strip()

        # Find matching subreddits
        subreddits = self.AREA_SUBREDDIT_MAP.get(area_lower, ["india"])

        logger.info(f"Fetching trending posts for area '{area}' from subreddits: {subreddits}")

        return self.get_trending_posts(subreddits, area_keyword=area, limit=limit)


# Global client instance
_reddit_client = None


def get_reddit_client() -> RedditLiveClient:
    """Get or create the Redis client singleton."""
    global _reddit_client
    if _reddit_client is None:
        _reddit_client = RedditLiveClient()
    return _reddit_client
