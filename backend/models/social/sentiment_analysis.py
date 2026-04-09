from __future__ import annotations

import os
import logging
from collections import Counter, defaultdict
from typing import Dict, Iterable, List

USE_TRANSFORMER_SENTIMENT = os.getenv("SOCIAL_USE_TRANSFORMER_SENTIMENT", "false").lower() == "true"

if USE_TRANSFORMER_SENTIMENT:
    try:
        from transformers import pipeline
    except Exception:
        pipeline = None
else:
    pipeline = None


logger = logging.getLogger(__name__)


POSITIVE_WORDS = {
    "safe", "good", "great", "walkable", "vibrant", "clean", "green", "family", "convenient",
    "connected", "accessible", "peaceful", "lively", "value", "recommended", "nice", "decent",
    "excellent", "wonderful", "beautiful", "love", "best",
}
NEGATIVE_WORDS = {
    "unsafe", "crime", "expensive", "costly", "crowded", "dirty", "traffic", "jam", "flooding",
    "parking", "noisy", "far", "slow", "poor", "bad", "avoid", "complaint", "issue",
    "horrible", "worst", "terrible", "pollution", "congestion", "garbage", "nightmare",
    "risky", "sketchy", "sketchy", "overpriced", "problematic", "disappointing",
}

ASPECT_KEYWORDS = {
    "safety": {"safe", "unsafe", "crime", "security", "police", "women", "night"},
    "traffic": {"traffic", "jam", "parking", "commute", "congestion", "road", "metro"},
    "cost": {"expensive", "cheap", "rent", "budget", "price", "cost", "premium", "affordable"},
    "lifestyle": {"cafes", "restaurants", "nightlife", "family", "vibrant", "walkable", "lifestyle"},
    "cleanliness": {"clean", "dirty", "garbage", "sewage", "flooding", "dust", "drainage"},
}

ASPECT_POSITIVE_WORDS = {
    "safety": {"safe", "secure", "patrolled", "decent"},
    "traffic": {"metro", "connected", "walkable", "manageable"},
    "cost": {"affordable", "reasonable", "value", "worth"},
    "lifestyle": {"vibrant", "lively", "cafes", "restaurants", "family", "nice"},
    "cleanliness": {"clean", "maintained", "green"},
}

ASPECT_NEGATIVE_WORDS = {
    "safety": {"unsafe", "crime", "robbery", "avoid"},
    "traffic": {"traffic", "jam", "parking", "congestion", "slow"},
    "cost": {"expensive", "costly", "premium", "overpriced"},
    "lifestyle": {"boring", "noisy", "isolated"},
    "cleanliness": {"dirty", "garbage", "sewage", "flooding", "dust"},
}


class SocialSentimentAnalyzer:
    def __init__(self) -> None:
        self.sentiment_pipeline = self._load_pipeline()

    def _load_pipeline(self):
        if pipeline is None:
            return None

        try:
            return pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                truncation=True,
                local_files_only=True,
            )
        except Exception as exc:
            logger.warning(f"Pretrained sentiment pipeline unavailable, using rule-based fallback: {exc}")
            return None

    def analyze_sentiment(self, text: str) -> Dict:
        if self.sentiment_pipeline is not None:
            try:
                result = self.sentiment_pipeline(text[:512])[0]
                label = result.get("label", "NEUTRAL").lower()
                mapped = "neutral"
                if "pos" in label:
                    mapped = "positive"
                elif "neg" in label:
                    mapped = "negative"
                return {"label": mapped, "score": round(float(result.get("score", 0.5)), 4)}
            except Exception as exc:
                logger.warning(f"Sentiment pipeline failed, falling back to lexical analysis: {exc}")

        lowered = (text or "").lower()
        positive_hits = sum(1 for word in POSITIVE_WORDS if word in lowered)
        negative_hits = sum(1 for word in NEGATIVE_WORDS if word in lowered)

        if positive_hits > negative_hits:
            return {"label": "positive", "score": round(min(0.95, 0.55 + positive_hits * 0.08), 4)}
        if negative_hits > positive_hits:
            return {"label": "negative", "score": round(min(0.95, 0.55 + negative_hits * 0.08), 4)}
        return {"label": "neutral", "score": 0.5}

    def analyze_aspects(self, posts: Iterable[Dict]) -> Dict[str, Dict]:
        aspect_scores = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "mentions": 0, "evidence": []})

        for post in posts:
            text = (post.get("text") or "").lower()
            excerpt = (post.get("text") or "")[:180].strip()
            for aspect, keywords in ASPECT_KEYWORDS.items():
                if not any(keyword in text for keyword in keywords):
                    continue

                aspect_scores[aspect]["mentions"] += 1
                positive_hits = sum(1 for keyword in ASPECT_POSITIVE_WORDS[aspect] if keyword in text)
                negative_hits = sum(1 for keyword in ASPECT_NEGATIVE_WORDS[aspect] if keyword in text)

                if positive_hits > negative_hits:
                    aspect_scores[aspect]["positive"] += 1
                elif negative_hits > positive_hits:
                    aspect_scores[aspect]["negative"] += 1
                else:
                    aspect_scores[aspect]["neutral"] += 1

                if excerpt:
                    aspect_scores[aspect]["evidence"].append(excerpt)

        output = {}
        for aspect in ASPECT_KEYWORDS:
            data = aspect_scores[aspect]
            if data["mentions"] == 0:
                label = "limited_data"
            # Require stronger consensus for positive (not just slightly more positive)
            elif data["positive"] >= data["negative"] + 1 and data["positive"] >= (data["mentions"] * 0.6):
                label = "positive"
            # Negative is easier to trigger (more pessimistic bias in real discussions)
            elif data["negative"] > data["neutral"] and data["negative"] >= (data["mentions"] * 0.4):
                label = "negative"
            else:
                label = "mixed"

            output[aspect] = {
                "label": label,
                "mentions": data["mentions"],
                "counts": {
                    "positive": data["positive"],
                    "negative": data["negative"],
                    "neutral": data["neutral"],
                },
                "evidence": data["evidence"][:3],
            }
        return output

    def analyze_posts(self, posts: List[Dict]) -> Dict:
        sentiments = []
        enriched_posts: List[Dict] = []
        for post in posts:
            sentiment = self.analyze_sentiment(post.get("text", ""))
            sentiments.append(sentiment["label"])
            enriched = dict(post)
            enriched["sentiment"] = sentiment
            enriched_posts.append(enriched)

        sentiment_counts = Counter(sentiments)
        overall_sentiment = "neutral"
        if sentiment_counts["positive"] > sentiment_counts["negative"]:
            overall_sentiment = "positive"
        elif sentiment_counts["negative"] > sentiment_counts["positive"]:
            overall_sentiment = "negative"

        aspect_analysis = self.analyze_aspects(enriched_posts)

        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_distribution": dict(sentiment_counts),
            "aspect_analysis": aspect_analysis,
            "posts": enriched_posts,
        }
