from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, cast

import config

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from .location_normalizer import KNOWN_AREA_MAP, LocationNormalizer
from .location_extractor import LocationExtractor
from .relevance_filter import SocialRelevanceFilter
from .report_generator import SocialReportGenerator
from .sentiment_analysis import SocialSentimentAnalyzer
from .vector_store import SocialVectorStore
from .reddit_live_trending import get_reddit_client

LANGGRAPH_AVAILABLE = False
END: Any = "__end__"
StateGraph: Any = None

try:
    _graph_module = importlib.import_module("langgraph.graph")
    END = getattr(_graph_module, "END")
    StateGraph = getattr(_graph_module, "StateGraph")
    LANGGRAPH_AVAILABLE = True
except Exception:
    LANGGRAPH_AVAILABLE = False


logger = logging.getLogger(__name__)


class SocialState(TypedDict, total=False):
    area: str
    normalized_locations: List[str]
    suggestions: List[str]
    query_variations: List[str]
    candidate_posts: List[Dict]
    retrieved_posts: List[Dict]
    sentiment_analysis: Dict
    report: Dict
    final_result: Dict


class SocialIntelligenceEngine:
    LOCATION_SCORE_PRIORS: Dict[str, float] = {
        "andheri": 7.1,
        "andheri west": 7.2,
        "andheri east": 6.8,
        "bandra": 7.8,
        "bandra west": 8.0,
        "bandra east": 7.1,
        "powai": 7.6,
        "worli": 7.7,
        "chembur": 6.7,
        "borivali": 6.6,
        "whitefield": 6.8,
        "koramangala": 7.4,
        "indiranagar": 7.6,
        "electronic city": 6.3,
        "gachibowli": 7.2,
        "hitech city": 7.1,
        "kondapur": 6.8,
        "banjara hills": 7.5,
        "hinjawadi": 6.4,
        "kharadi": 6.9,
        "wakad": 6.5,
        "viman nagar": 6.8,
        "gurugram": 6.9,
        "noida": 6.6,
        "omr": 6.4,
        "velachery": 6.5,
        "thoraipakkam": 6.3,
    }

    MUMBAI_PREMIUM_TERMS = {
        "bandra", "bandra west", "juhu", "colaba", "malabar hill", "worli", "prabhadevi",
        "powai", "bkc", "lower parel", "cuffe parade", "marine drive"
    }
    MUMBAI_MID_TERMS = {
        "andheri", "andheri west", "andheri east", "chembur", "ghatkopar", "mulund", "vile parle",
        "santacruz", "dadar", "matunga", "goregaon", "malad", "kandivali", "borivali", "kurla"
    }
    MUMBAI_BUDGET_TERMS = {
        "nallasopara", "virar", "mira road", "bhayandar", "dombivli", "kalyan", "panvel"
    }

    def __init__(
        self,
        data_path: Optional[str] = None,
        faiss_dir: Optional[str] = None,
        embedding_model_name: Optional[str] = None,
        genai_handler: Any = None,
    ) -> None:
        self.data_path = Path(data_path or config.SOCIAL_REDDIT_STORE_PATH)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            self.data_path.write_text("[]", encoding="utf-8")

        self.faiss_dir = Path(faiss_dir or config.SOCIAL_FAISS_DIR)
        self.embedding_model_name = embedding_model_name or config.SOCIAL_EMBEDDING_MODEL
        self.local_model_path = Path(config.BASE_DIR) / "backend" / "models" / "real_estate_embeddings"
        self.embedder = self._load_shared_embedder()

        self.normalizer = LocationNormalizer(KNOWN_AREA_MAP)
        self.location_extractor = LocationExtractor()
        self.relevance_filter = SocialRelevanceFilter(self.embedding_model_name, self.local_model_path, embedder=self.embedder)
        self.vector_store = SocialVectorStore(self.faiss_dir, self.embedding_model_name, self.local_model_path, embedder=self.embedder)
        self.sentiment_analyzer = SocialSentimentAnalyzer()
        self.report_generator = SocialReportGenerator(genai_handler=genai_handler)
        self._indexed_record_count = -1
        self.graph = self._build_graph() if LANGGRAPH_AVAILABLE and StateGraph is not None else None

    def _load_shared_embedder(self):
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is required for SocialIntelligenceEngine")
        if self.local_model_path.exists():
            logger.info(f"Loading shared social embedder from local path: {self.local_model_path}")
            return SentenceTransformer(str(self.local_model_path))
        logger.info(f"Loading shared social embedder model: {self.embedding_model_name}")
        return SentenceTransformer(self.embedding_model_name)

    def _build_graph(self):
        workflow = StateGraph(SocialState)
        workflow.add_node("normalize", self._normalize_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("report", self._report_node)
        workflow.set_entry_point("normalize")
        workflow.add_edge("normalize", "retrieve")
        workflow.add_edge("retrieve", "analyze")
        workflow.add_edge("analyze", "report")
        workflow.add_edge("report", END)
        return workflow.compile()

    def _load_records(self) -> List[Dict]:
        try:
            raw_records = json.loads(self.data_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Unable to load social Reddit store from {self.data_path}: {exc}")
            return []

        # Rebuild location tags if they're all the same (legacy data issue)
        if raw_records:
            # Convert to tuples for hashability check
            first_tags = set(tuple(sorted(r.get("location_tags", []))) for r in raw_records)
            # If all records have identical tags, rebuild them
            if len(first_tags) == 1:
                logger.info("Detecting legacy location tags (all identical). Rebuilding from text/subreddit...")
                raw_records = self.location_extractor.rebuild_location_tags(raw_records)

        records: List[Dict] = []
        for raw in raw_records:
            text = (raw.get("text") or raw.get("body") or raw.get("title") or "").strip()
            if not text:
                continue

            location_tags = raw.get("location_tags") or raw.get("detected_location_tags") or []
            if isinstance(location_tags, str):
                location_tags = [location_tags]

            # Extract locations if still not properly set
            if not location_tags or len(set(location_tags)) == 0:
                location_tags = self.location_extractor.extract_locations(raw)

            record = {
                "id": raw.get("id") or raw.get("post_id") or raw.get("url") or str(abs(hash(text))),
                "text": text,
                "subreddit": str(raw.get("subreddit") or "india").replace("r/", ""),
                "timestamp": raw.get("timestamp") or raw.get("created_at") or raw.get("date") or "",
                "location_tags": list(dict.fromkeys(location_tags)),
                "upvotes": int(raw.get("upvotes") or raw.get("score") or 0),
                "url": raw.get("url") or raw.get("permalink") or "",
                "source_type": raw.get("source_type") or "stored_reddit_db",
            }
            records.append(record)
        return records

    def _ensure_index(self) -> List[Dict]:
        records = self._load_records()
        if len(records) != self._indexed_record_count:
            self.vector_store.rebuild(records)
            self._indexed_record_count = len(records)
        return records

    def _build_query_variations(self, area: str, normalized_locations: List[str]) -> List[str]:
        anchors = normalized_locations or [area]
        queries = []
        for anchor in anchors[:3]:
            queries.extend([
                f"living in {anchor}",
                f"is {anchor} good for living",
                f"rent in {anchor}",
                f"buy house in {anchor}",
                f"safety traffic cost in {anchor}",
            ])
        return list(dict.fromkeys(queries))

    def _matches_location(self, post: Dict, normalized_locations: List[str]) -> bool:
        """
        Stricter location matching.
        Only return True if post specifically mentions one of the normalized locations,
        or at least one of the keywords from the location.
        """
        if not normalized_locations:
            return True

        post_text = post.get("text", "").lower()
        post_subreddit = post.get("subreddit", "").lower()
        post_tags = {tag.lower() for tag in post.get("location_tags", [])}

        for location in normalized_locations:
            location_lower = location.lower()

            # Direct match in tags
            if location_lower in post_tags:
                return True

            # Direct substring match in text (more specific)
            if location_lower in post_text:
                return True

            # Check specific words from location
            # e.g., "Bandra West Mumbai" -> check for "bandra", "west", "mumbai"
            words = [w for w in location_lower.split() if len(w) > 2]
            primary_word = words[0] if words else ""  # e.g., "bandra"

            # Match if primary word (main area name) is in text
            if primary_word and primary_word in post_text:
                return True

        return False

    def _time_filter(self, post: Dict, time_window_days: Optional[int]) -> bool:
        if not time_window_days:
            return True
        timestamp = post.get("timestamp")
        if not timestamp:
            return True
        try:
            post_time = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except Exception:
            return True
        return post_time >= datetime.now(post_time.tzinfo) - timedelta(days=time_window_days)

    def _normalize_node(self, state: SocialState) -> SocialState:
        area = state.get("area", "")
        normalized_locations = self.normalizer.normalize_location(area)
        suggestions = self.normalizer.suggest_nearby_locations(area)
        query_variations = self._build_query_variations(area, normalized_locations)
        updated = dict(state)
        updated["normalized_locations"] = normalized_locations
        updated["suggestions"] = suggestions
        updated["query_variations"] = query_variations
        return cast(SocialState, updated)

    def _retrieve_node(self, state: SocialState) -> SocialState:
        area = state.get("area", "")
        normalized_locations = state.get("normalized_locations", [])
        query_variations = state.get("query_variations", []) or [area]
        records = self._ensure_index()

        candidate_posts = [
            record for record in records
            if self._matches_location(record, normalized_locations)
        ]

        filtered_by_time = [
            record for record in candidate_posts
            if self._time_filter(record, state.get("time_window_days"))  # type: ignore[arg-type]
        ]
        candidate_posts = filtered_by_time or candidate_posts

        combined_query = " | ".join(query_variations[:4]) if query_variations else area
        relevant_posts = self.relevance_filter.filter_relevant_posts(
            candidate_posts,
            combined_query,
            top_k=state.get("top_k", 5) * 2,
        )

        vector_hits = self.vector_store.search(
            combined_query,
            top_k=max(6, state.get("top_k", 5) * 2),
            filters={"location_tags": normalized_locations},
        )

        deduped: Dict[str, Dict] = {}
        for post in [*relevant_posts, *vector_hits]:
            key = str(post.get("id") or post.get("url") or hash(post.get("text", "")))
            existing = deduped.get(key)
            if existing is None or post.get("relevance_score", 0) > existing.get("relevance_score", 0):
                deduped[key] = post

        retrieved_posts = sorted(
            deduped.values(),
            key=lambda item: (
                item.get("relevance_score", 0.0),
                item.get("vector_score", 0.0),
                item.get("upvotes", 0),
            ),
            reverse=True,
        )[: max(state.get("top_k", 5), 1)]

        updated = dict(state)
        updated["candidate_posts"] = candidate_posts
        updated["retrieved_posts"] = retrieved_posts
        return cast(SocialState, updated)

    def _analyze_node(self, state: SocialState) -> SocialState:
        posts = state.get("retrieved_posts", [])
        updated = dict(state)
        updated["sentiment_analysis"] = self.sentiment_analyzer.analyze_posts(posts)
        return cast(SocialState, updated)

    def _fetch_live_trending_posts(self, area: str) -> List[Dict]:
        """Fetch live trending posts from Reddit for the given area."""
        try:
            reddit_client = get_reddit_client()
            if not reddit_client.access_token:
                logger.info("Reddit API not configured. Skipping live trending posts.")
                return []

            logger.info(f"Fetching live trending posts for area: {area}")
            trending_posts = reddit_client.get_trending_for_area(area, limit=3)
            logger.info(f"Fetched {len(trending_posts)} trending posts for {area}")
            return trending_posts
        except Exception as e:
            logger.warning(f"Failed to fetch live trending posts: {e}")
            return []

    def _report_node(self, state: SocialState) -> SocialState:
        area = state.get("area", "")
        normalized_locations = state.get("normalized_locations", [])
        posts = state.get("retrieved_posts", [])
        analysis = state.get("sentiment_analysis", {})
        data_source = state.get("data_source", "stored_reddit_db")

        suggestions = state.get("suggestions", [])

        # Try to fetch live trending posts for this area
        live_trending = self._fetch_live_trending_posts(area)

        if not posts:
            final_result = self._limited_data_result(area, normalized_locations, suggestions)
        else:
            report = self.report_generator.generate_report(
                area=area,
                normalized_locations=normalized_locations,
                posts=analysis.get("posts", posts),
                overall_sentiment=analysis.get("overall_sentiment", "neutral"),
                aspect_analysis=analysis.get("aspect_analysis", {}),
            )
            final_result = self._format_result(
                area=area,
                normalized_locations=normalized_locations,
                suggestions=suggestions,
                posts=analysis.get("posts", posts),
                analysis=analysis,
                report=report,
                data_source=data_source,
                live_trending=live_trending,
            )

        updated = dict(state)
        updated["report"] = final_result
        updated["final_result"] = final_result
        return cast(SocialState, updated)

    def _limited_data_result(self, area: str, normalized_locations: List[str], suggestions: List[str]) -> Dict:
        baseline_score = self._get_location_baseline_score(area, normalized_locations)
        return {
            "area": area,
            "normalized_locations": normalized_locations or [area],
            "data_availability": {
                "status": "limited",
                "message": "Limited social data available for this area",
                "post_count": 0,
                "source": "stored_reddit_db",
                "last_refreshed": self._last_refreshed(),
            },
            "summary": f"Limited social data available for {area}. Showing an estimated baseline score until stronger local evidence is available.",
            "key_insights": [],
            "aspect_analysis": {
                "safety": {"label": "N/A", "mentions": 0},
                "traffic": {"label": "N/A", "mentions": 0},
                "cost": {"label": "N/A", "mentions": 0},
                "lifestyle": {"label": "N/A", "mentions": 0},
                "cleanliness": {"label": "N/A", "mentions": 0},
            },
            "overall_sentiment": "N/A",
            "social_score": baseline_score,
            "verdict": {
                "text": "Insufficient area-specific discussion volume. Score shown is a realistic baseline estimate; validate with on-ground checks.",
                "best_for": "Further on-ground verification",
                "pros": ["N/A"],
                "cons": ["N/A"],
            },
            "structured_report": "Limited social data available for this area. Aspect-level details are N/A due to insufficient evidence.",
            "top_discussions": [],
            "nearby_suggestions": suggestions,
        }

    def _get_location_baseline_score(self, area: str, normalized_locations: List[str]) -> float:
        candidates = [area.lower().strip()]
        for loc in normalized_locations:
            normalized = loc.lower().replace(",", " ").strip()
            candidates.append(normalized)
            parts = [p for p in normalized.split() if p and p not in {"mumbai", "bengaluru", "bangalore", "hyderabad", "pune", "gurugram", "noida", "chennai"}]
            if parts:
                candidates.append(" ".join(parts[:2]))
                candidates.append(parts[0])

        for candidate in candidates:
            if candidate in self.LOCATION_SCORE_PRIORS:
                return self.LOCATION_SCORE_PRIORS[candidate]

        is_mumbai_query = (
            "mumbai" in area.lower()
            or any("mumbai" in loc.lower() for loc in normalized_locations)
            or any(token in " ".join(candidates) for token in self.MUMBAI_PREMIUM_TERMS | self.MUMBAI_MID_TERMS | self.MUMBAI_BUDGET_TERMS)
        )

        if is_mumbai_query:
            joined = " ".join(candidates)
            if any(term in joined for term in self.MUMBAI_PREMIUM_TERMS):
                return 7.6
            if any(term in joined for term in self.MUMBAI_MID_TERMS):
                return 6.9
            if any(term in joined for term in self.MUMBAI_BUDGET_TERMS):
                return 6.2
            # Default realistic baseline for unspecified Mumbai localities.
            return 6.7

        return 6.0

    def _discussion_mentions_area(self, post: Dict, area: str, normalized_locations: List[str]) -> bool:
        text = str(post.get("text") or "").lower()
        if not text:
            return False

        area_terms = set()
        clean_area = area.lower().strip()
        if clean_area:
            area_terms.add(clean_area)
            area_terms.update([t for t in clean_area.split() if len(t) > 3])

        for loc in normalized_locations:
            loc_l = loc.lower().replace(",", " ").strip()
            area_terms.add(loc_l)
            parts = [p for p in loc_l.split() if len(p) > 3 and p not in {"mumbai", "bengaluru", "bangalore", "hyderabad", "pune", "gurugram", "noida", "chennai"}]
            if parts:
                area_terms.add(parts[0])
                area_terms.add(" ".join(parts[:2]))

        return any(term and term in text for term in area_terms)

    def _format_result(
        self,
        area: str,
        normalized_locations: List[str],
        suggestions: List[str],
        posts: List[Dict],
        analysis: Dict,
        report: Dict,
        data_source: str = "stored_reddit_db",
        live_trending: Optional[List[Dict]] = None,
    ) -> Dict:
        aspect_analysis = report.get("aspect_analysis", {})

        # Realistic scoring: start from a location prior and nudge with sentiment evidence.
        base_score = self._get_location_baseline_score(area, normalized_locations)
        adjustments = 0.0
        evidence_mentions = 0

        for aspect, data in aspect_analysis.items():
            label = data.get("label")
            mentions = data.get("mentions", 0)

            # Only count aspects with mentions (ignore "limited_data")
            if mentions == 0 or label in {"limited_data", "N/A"}:
                continue

            evidence_mentions += int(mentions)

            # Positive aspect: moderate boost
            if label == "positive":
                adjustments += 0.45
            # Negative aspect: stronger penalty
            elif label == "negative":
                adjustments -= 0.7
            # Mixed: slight penalty
            elif label == "mixed":
                adjustments -= 0.2

        # With sparse evidence, keep score close to baseline instead of overreacting.
        confidence = min(1.0, evidence_mentions / 10.0)
        social_score = base_score + (adjustments * confidence)

        # Keep practical score bounds.
        social_score = max(3.5, min(9.2, social_score))
        social_score = round(social_score, 1)

        # Determine source message based on data source
        if data_source == "reddit_live_search":
            source_message = "Live Reddit discussions retrieved successfully."
            source_label = "reddit_live_search"
        else:
            source_message = "Stored Reddit discussions retrieved successfully."
            source_label = "stored_reddit_db"

        # Combine stored posts with live trending
        top_discussions = []

        # Add live trending posts first (they're more current/relevant)
        if live_trending:
            for post in live_trending[:3]:
                candidate = {
                    "id": post.get("id"),
                    "text": (post.get("text") or post.get("selftext") or "")[:300],
                    "title": post.get("title", ""),
                    "subreddit": post.get("subreddit", "india"),
                    "timestamp": post.get("timestamp", ""),
                    "url": post.get("url", ""),
                    "upvotes": post.get("upvotes") or post.get("score", 0),
                    "sentiment": {"label": "trending", "score": 0.8},
                    "location_tags": post.get("location_tags", []),
                    "relevance_score": 0.95,
                    "source": "reddit_live_trending",
                }
                if self._discussion_mentions_area(candidate, area, normalized_locations):
                    top_discussions.append(candidate)

        # Add stored posts as secondary discussions
        for post in posts[: max(5 - len(top_discussions), 1)]:
            candidate = {
                "id": post.get("id"),
                "text": post.get("text", "")[:300],
                "subreddit": post.get("subreddit", "india"),
                "timestamp": post.get("timestamp", ""),
                "url": post.get("url", ""),
                "upvotes": post.get("upvotes") or post.get("score", 0),
                "sentiment": post.get("sentiment", {}),
                "location_tags": post.get("location_tags", []),
                "relevance_score": post.get("relevance_score", post.get("vector_score", 0)),
                "source": "stored_reddit_db",
            }
            if self._discussion_mentions_area(candidate, area, normalized_locations):
                top_discussions.append(candidate)

        return {
            "area": area,
            "normalized_locations": normalized_locations or [area],
            "query_expansion": self._build_query_variations(area, normalized_locations),
            "data_availability": {
                "status": "ok",
                "message": source_message,
                "post_count": len(posts) + len(live_trending or []),
                "source": source_label,
                "last_refreshed": self._last_refreshed() if data_source != "reddit_live_search" else datetime.now().isoformat(),
            },
            "summary": report.get("summary", ""),
            "key_insights": report.get("key_insights", []),
            "aspect_analysis": aspect_analysis,
            "overall_sentiment": analysis.get("overall_sentiment", "neutral"),
            "sentiment_distribution": analysis.get("sentiment_distribution", {}),
            "social_score": social_score,
            "verdict": report.get("verdict", {}),
            "structured_report": report.get("report_markdown", ""),
            "top_discussions": top_discussions,
            "nearby_suggestions": suggestions,
        }

    def _last_refreshed(self) -> Optional[str]:
        try:
            return datetime.fromtimestamp(self.data_path.stat().st_mtime).isoformat()
        except Exception:
            return None

    def analyze_area(self, area: str, top_k: int = 5, time_window_days: Optional[int] = None) -> Dict:
        logger.info(f"[SocialIntelligenceEngine] analyze_area called: area={area}, top_k={top_k}")
        state: SocialState = {
            "area": area.strip(),
            "top_k": top_k,  # type: ignore[typeddict-item]
            "time_window_days": time_window_days,  # type: ignore[typeddict-item]
        }

        try:
            if self.graph is not None:
                logger.info("[SocialIntelligenceEngine] Using LangGraph workflow")
                result_state = self.graph.invoke(state)
                return result_state.get("final_result", self._limited_data_result(area, [], []))

            logger.info("[SocialIntelligenceEngine] Using sequential node execution")
            logger.info("[SocialIntelligenceEngine] Running normalize_node...")
            normalized_state = self._normalize_node(state)
            logger.info(f"[SocialIntelligenceEngine] Normalized locations: {normalized_state.get('normalized_locations')}")
            
            logger.info("[SocialIntelligenceEngine] Running retrieve_node...")
            retrieved_state = self._retrieve_node(normalized_state)
            logger.info(f"[SocialIntelligenceEngine] Retrieved posts: {len(retrieved_state.get('retrieved_posts', []))}")
            
            logger.info("[SocialIntelligenceEngine] Running analyze_node...")
            analyzed_state = self._analyze_node(retrieved_state)
            
            logger.info("[SocialIntelligenceEngine] Running report_node...")
            final_state = self._report_node(analyzed_state)
            
            result = final_state.get("final_result", self._limited_data_result(area, [], []))
            logger.info(f"[SocialIntelligenceEngine] Analysis complete. Result keys: {list(result.keys())}")
            return result
        except Exception as e:
            logger.error(f"[SocialIntelligenceEngine] Error in analyze_area: {e}", exc_info=True)
            raise

    def rebuild_store(self) -> None:
        self._ensure_index()
