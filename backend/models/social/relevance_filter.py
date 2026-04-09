from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


logger = logging.getLogger(__name__)


REAL_ESTATE_KEYWORDS = {
    "rent",
    "rental",
    "buy",
    "buying",
    "living",
    "live",
    "area",
    "locality",
    "safe",
    "safety",
    "traffic",
    "cost",
    "expensive",
    "budget",
    "price",
    "parking",
    "commute",
    "society",
    "flat",
    "apartment",
    "neighbourhood",
    "locality",
    "broker",
}


class SocialRelevanceFilter:
    def __init__(self, embedding_model_name: str, local_model_path: Optional[Path] = None, embedder=None):
        self.embedding_model_name = embedding_model_name
        self.local_model_path = local_model_path
        self.embedder = embedder or self._load_embedder()

    def _load_embedder(self):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is required for social relevance filtering.")

        candidate_paths = [
            self.local_model_path,
            Path("backend/models/real_estate_embeddings"),
            Path("models/real_estate_embeddings"),
        ]
        for candidate in candidate_paths:
            if candidate and Path(candidate).exists():
                logger.info(f"Loading relevance embeddings from local path: {candidate}")
                return SentenceTransformer(str(candidate))

        return SentenceTransformer(self.embedding_model_name)

    @staticmethod
    def _keyword_matches(text: str) -> int:
        lowered = (text or "").lower()
        return sum(1 for keyword in REAL_ESTATE_KEYWORDS if keyword in lowered)

    def keyword_filter(self, posts: Iterable[Dict]) -> List[Dict]:
        filtered = []
        for post in posts:
            text = post.get("text", "")
            keyword_hits = self._keyword_matches(text)
            if keyword_hits > 0:
                updated = dict(post)
                updated["keyword_hits"] = keyword_hits
                filtered.append(updated)
        return filtered

    def _embed(self, texts: List[str]) -> np.ndarray:
        embeddings = self.embedder.encode(texts, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        return embeddings

    def filter_relevant_posts(self, posts: Iterable[Dict], query: str, top_k: int = 8) -> List[Dict]:
        keyword_pass = self.keyword_filter(posts)
        if not keyword_pass:
            return []

        query_variants = [
            query,
            f"living in {query}",
            f"is {query} good for living",
            f"rent in {query}",
            f"buying a flat in {query}",
        ]
        query_embeddings = self._embed(query_variants)
        post_embeddings = self._embed([post.get("text", "") for post in keyword_pass])
        similarity_matrix = post_embeddings @ query_embeddings.T
        similarity_scores = similarity_matrix.max(axis=1)

        scored_posts = []
        for post, similarity in zip(keyword_pass, similarity_scores):
            updated = dict(post)
            updated["similarity_score"] = float(similarity)
            updated["relevance_score"] = round(
                min(0.99, max(0.0, (updated.get("keyword_hits", 0) * 0.08) + (float(similarity) * 0.92))),
                4,
            )
            scored_posts.append(updated)

        scored_posts.sort(
            key=lambda item: (
                item.get("relevance_score", 0.0),
                item.get("keyword_hits", 0),
                item.get("upvotes", 0),
            ),
            reverse=True,
        )
        return scored_posts[: max(top_k, 1)]
