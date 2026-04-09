"""
RAG-Driven Market News Aggregator for Trend Alerts
Uses ChromaDB for vector storage and sentence-transformers for embeddings
Retrieves relevant news articles about locations and generates insights
Now with fine-tuned domain-specific embeddings and vocabulary optimization
"""

import os
import json
import gc
from collections import Counter, defaultdict
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import logging
import shutil
import requests

os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    RAG_AVAILABLE = True
except Exception as e:
    SentenceTransformer = None
    chromadb = None
    Settings = None
    RAG_AVAILABLE = False

# Import domain optimization modules (graceful fallback if not available)
try:
    from .domain_optimization import DomainOptimizer, ArticleReranker, RealEstateVocabulary
    DOMAIN_OPT_AVAILABLE = True
except ImportError:
    try:
        from models.domain_optimization import DomainOptimizer, ArticleReranker, RealEstateVocabulary
        DOMAIN_OPT_AVAILABLE = True
    except ImportError:
        try:
            from domain_optimization import DomainOptimizer, ArticleReranker, RealEstateVocabulary
            DOMAIN_OPT_AVAILABLE = True
        except ImportError:
            DOMAIN_OPT_AVAILABLE = False

logger = logging.getLogger(__name__)


class MarketNewsRAG:
    """
    RAG system for real estate market news and trend alerts
    """

    SOURCE_WEIGHTS = {
        "Economic Times": 1.0,
        "The Economic Times": 1.0,
        "ET Realty": 1.0,
        "Business Standard": 0.95,
        "Hindustan Times": 0.9,
        "MoneyControl": 0.9,
        "Moneycontrol": 0.9,
        "LiveMint": 0.9,
        "Mint": 0.9,
        "Financial Express": 0.85,
        "Housing.com": 0.8,
        "MagicBricks": 0.75,
        "Google News": 0.7,
    }

    SIGNAL_BUCKETS = {
        "Infrastructure": (
            "metro",
            "airport",
            "expressway",
            "road",
            "corridor",
            "rail",
            "station",
            "line",
            "interchange",
            "link road",
            "ring road",
            "infrastructure",
            "connectivity",
        ),
        "Demand & Prices": (
            "price",
            "prices",
            "appreciation",
            "demand",
            "sales",
            "booking",
            "absorption",
            "rental",
            "yield",
            "homebuyer",
            "inventory",
        ),
        "Office & Jobs": (
            "office",
            "leasing",
            "workspace",
            "gcc",
            "global capability centre",
            "tech park",
            "business park",
            "employment",
            "hiring",
            "it corridor",
        ),
        "Supply & Launches": (
            "launch",
            "launched",
            "project",
            "township",
            "phase",
            "units",
            "supply",
            "construction",
            "developer",
            "residential",
            "luxury",
            "premium",
        ),
        "Policy & Regulation": (
            "rera",
            "policy",
            "approval",
            "stamp duty",
            "budget",
            "tax",
            "fsi",
            "zoning",
            "regulation",
            "guideline value",
        ),
        "Caution": (
            "delay",
            "delayed",
            "litigation",
            "legal",
            "dispute",
            "slowdown",
            "slump",
            "decline",
            "stalled",
            "fraud",
            "probe",
            "oversupply",
            "unsold",
            "debt",
        ),
    }

    POSITIVE_TERMS = {
        "growth": 0.08,
        "surge": 0.1,
        "rise": 0.07,
        "record": 0.06,
        "boost": 0.08,
        "improve": 0.05,
        "launch": 0.05,
        "premium": 0.05,
        "luxury": 0.05,
        "metro": 0.08,
        "airport": 0.08,
        "leasing": 0.07,
        "demand": 0.05,
    }

    NEGATIVE_TERMS = {
        "delay": -0.12,
        "dispute": -0.12,
        "litigation": -0.15,
        "slowdown": -0.1,
        "slump": -0.12,
        "decline": -0.1,
        "fraud": -0.2,
        "stalled": -0.15,
        "unsold": -0.08,
        "debt": -0.08,
        "caution": -0.05,
    }

    LOCATION_ALIASES = {
        "bangalore": "Bengaluru",
        "bengaluru": "Bengaluru",
        "mumbai": "Mumbai",
        "mmr": "Mumbai",
        "delhi ncr": "Delhi NCR",
        "ncr": "Delhi NCR",
        "new delhi": "Delhi",
        "delhi": "Delhi",
        "noida": "Noida",
        "gurugram": "Gurugram",
        "gurgaon": "Gurugram",
        "hyderabad": "Hyderabad",
        "pune": "Pune",
        "chennai": "Chennai",
        "kolkata": "Kolkata",
        "goa": "Goa",
    }

    # Chunking defaults: keep chunks compact enough for precise retrieval while
    # preserving context through overlap.
    CHUNK_SIZE_WORDS = 170
    CHUNK_OVERLAP_WORDS = 30
    
    def __init__(self, persist_directory: str = "chroma_db"):
        """
        Initialize the RAG system with ChromaDB and embeddings model
        Automatically loads fine-tuned embeddings if available, falls back to generic model

        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = str(self._preferred_persist_directory(persist_directory))
        self.rag_enabled = RAG_AVAILABLE
        self.collection_name = "market_news"
        self.embedding_model = None
        self.chroma_client = None
        self.model_type = "unknown"  # Track which model is loaded
        self.domain_opt_enabled = DOMAIN_OPT_AVAILABLE
        self.base_dir = Path(__file__).resolve().parents[2]
        self.seed_csv_path = self.base_dir / "Datasets" / "real_estate_news_live.csv"
        self.serpapi_key = os.getenv("SERPAPI_KEY", "").strip()

        if not self.rag_enabled:
            logger.warning("MarketNewsRAG running in fallback mode: embedding/vector dependencies unavailable")
            return

        # Initialize embedding model with fine-tuned preference
        logger.info("Loading embedding model...")
        self._load_embedding_model()

        # Initialize ChromaDB client
        logger.info("Initializing ChromaDB...")
        self.collection_name = "market_news"
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=self._chroma_settings(),
            )
            self._ensure_collection_exists()
            try:
                self._bootstrap_collection_from_csv_if_empty()
            except Exception as bootstrap_error:
                logger.warning(
                    f"MarketNewsRAG bootstrap skipped due to non-fatal CSV load issue: {bootstrap_error}"
                )
        except Exception as e:
            if self._is_schema_mismatch_error(e):
                logger.warning(f"Detected incompatible ChromaDB schema. Reinitializing store at {self.persist_directory}")
                self._reinitialize_persist_store()
                try:
                    self.persist_directory = str(self._runtime_persist_directory())
                    self.chroma_client = chromadb.PersistentClient(
                        path=self.persist_directory,
                        settings=self._chroma_settings(),
                    )
                    self._ensure_collection_exists()
                    try:
                        self._bootstrap_collection_from_csv_if_empty()
                    except Exception as bootstrap_error:
                        logger.warning(
                            f"MarketNewsRAG bootstrap skipped due to non-fatal CSV load issue: {bootstrap_error}"
                        )
                except Exception as retry_error:
                    logger.warning(
                        f"MarketNewsRAG falling back to CSV mode after Chroma reinit failure: {retry_error}"
                    )
                    self._disable_rag_mode()
            else:
                logger.warning(f"MarketNewsRAG falling back to CSV mode after init failure: {e}")
                self._disable_rag_mode()

    def _disable_rag_mode(self):
        """Switch to CSV fallback mode without taking down backend startup."""
        self.rag_enabled = False
        self.embedding_model = None
        self.chroma_client = None
        self.model_type = "fallback"

    def _preferred_persist_directory(self, persist_directory: str) -> Path:
        persist_path = Path(persist_directory)
        runtime_path = self._runtime_persist_directory_for(persist_path)
        if persist_path.name.endswith("_runtime"):
            return runtime_path
        if runtime_path.exists():
            return runtime_path
        return persist_path

    def _chroma_settings(self):
        if Settings is None:
            return None
        return Settings(anonymized_telemetry=False)

    def _runtime_persist_directory(self) -> Path:
        return self._runtime_persist_directory_for(Path(self.persist_directory))

    def _runtime_persist_directory_for(self, persist_path: Path) -> Path:
        name = persist_path.name
        while name.endswith("_runtime"):
            name = name[:-len("_runtime")]
        normalized_name = f"{name}_runtime"
        return persist_path.parent / normalized_name

    def _chunk_text(self, title: str, content: str) -> List[str]:
        """
        Chunk news text into overlapping word windows for better retrieval quality.
        """
        title = (title or "").strip()
        content = (content or "").strip()
        if not content:
            return [title] if title else []

        words = content.split()
        if not words:
            return [f"{title}\n\n{content}".strip()]

        chunk_size = max(50, self.CHUNK_SIZE_WORDS)
        overlap = max(0, min(self.CHUNK_OVERLAP_WORDS, chunk_size - 1))
        step = max(1, chunk_size - overlap)

        chunks = []
        for start in range(0, len(words), step):
            window = words[start:start + chunk_size]
            if not window:
                break
            chunk_text = " ".join(window)
            chunks.append(f"{title}\n\n{chunk_text}".strip())
            if start + chunk_size >= len(words):
                break

        return chunks

    def _candidate_csv_paths(self) -> List[Path]:
        return [
            self.seed_csv_path,
            Path("Datasets/real_estate_news_live.csv"),
            Path("../Datasets/real_estate_news_live.csv"),
            Path("../../Datasets/real_estate_news_live.csv"),
        ]

    def _resolve_local_embedding_model(self) -> Optional[Path]:
        candidate_paths = [
            self.base_dir / "backend" / "models" / "real_estate_embeddings",
            self.base_dir / "backend" / "models" / "backend" / "models" / "real_estate_embeddings",
            Path("models/real_estate_embeddings"),
            Path("backend/models/real_estate_embeddings"),
            Path("backend/models/backend/models/real_estate_embeddings"),
        ]
        for candidate in candidate_paths:
            if candidate.exists():
                return candidate
        return None

    def _normalize_location(self, location: str) -> str:
        normalized = (location or "").strip()
        if not normalized:
            return ""
        alias_key = normalized.lower()
        return self.LOCATION_ALIASES.get(alias_key, normalized.title())

    def _safe_text(self, value, default: str = "") -> str:
        """Normalize scalar values to safe strings for ingestion and metadata."""
        if value is None:
            return default
        if isinstance(value, str):
            text = value.strip()
            return text if text else default
        try:
            if pd.isna(value):
                return default
        except Exception:
            pass
        text = str(value).strip()
        if text.lower() in {"nan", "none", "null"}:
            return default
        return text if text else default

    def _safe_float(self, value, default: float = 0.5) -> float:
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except Exception:
            pass
        try:
            return float(value)
        except Exception:
            return default

    def _safe_parse_datetime(self, value) -> Optional[datetime]:
        if value in (None, "", "nan"):
            return None
        if isinstance(value, datetime):
            return value
        try:
            parsed = pd.to_datetime(value, errors="coerce", utc=True)
            if pd.isna(parsed):
                return None
            return parsed.to_pydatetime()
        except Exception:
            return None

    def _source_weight(self, source: str) -> float:
        if not source:
            return 0.7
        for known_source, weight in self.SOURCE_WEIGHTS.items():
            if known_source.lower() in source.lower():
                return weight
        return 0.72

    def _extract_signals(self, article: Dict) -> Dict[str, int]:
        text = f"{article.get('title', '')} {article.get('content', '')}".lower()
        scores = {}
        for bucket, keywords in self.SIGNAL_BUCKETS.items():
            scores[bucket] = sum(1 for keyword in keywords if keyword in text)
        return scores

    def _estimate_impact_score(self, article: Dict) -> float:
        text = f"{article.get('title', '')} {article.get('content', '')}".lower()
        score = 0.5
        for term, delta in self.POSITIVE_TERMS.items():
            if term in text:
                score += delta
        for term, delta in self.NEGATIVE_TERMS.items():
            if term in text:
                score += delta

        signal_scores = self._extract_signals(article)
        score += min(signal_scores.get("Infrastructure", 0) * 0.03, 0.09)
        score += min(signal_scores.get("Office & Jobs", 0) * 0.025, 0.08)
        score += min(signal_scores.get("Demand & Prices", 0) * 0.02, 0.06)
        score -= min(signal_scores.get("Caution", 0) * 0.06, 0.2)
        score *= self._source_weight(article.get("source", ""))
        return round(max(0.18, min(score, 0.95)), 2)

    def _recency_weight(self, article_date: Optional[datetime]) -> float:
        if not article_date:
            return 0.75
        age_days = max((datetime.now(article_date.tzinfo) - article_date).days, 0)
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.9
        if age_days <= 90:
            return 0.8
        return 0.65

    def _article_rank_score(self, article: Dict) -> float:
        impact = float(article.get("impact_score", 0.5) or 0.5)
        relevance = float(article.get("relevance_score", 0.65) or 0.65)
        recency = self._recency_weight(self._safe_parse_datetime(article.get("date")))
        source_weight = self._source_weight(article.get("source", ""))
        return round((impact * 0.45) + (relevance * 0.25) + (recency * 0.2) + (source_weight * 0.1), 3)

    def _dedupe_articles(self, articles: List[Dict]) -> List[Dict]:
        seen = set()
        deduped = []
        for article in articles:
            unique_key = (
                (article.get("url") or "").strip().lower()
                or (article.get("title") or "").strip().lower()
            )
            if not unique_key or unique_key in seen:
                continue
            seen.add(unique_key)
            deduped.append(article)
        return deduped

    def _parse_relative_date(self, value: str) -> str:
        if not value:
            return datetime.now().isoformat()
        text = value.strip().lower()
        now = datetime.now()
        if "hour" in text:
            digits = "".join(ch for ch in text if ch.isdigit())
            delta_hours = int(digits or 1)
            return (now - timedelta(hours=delta_hours)).isoformat()
        if "minute" in text:
            digits = "".join(ch for ch in text if ch.isdigit())
            delta_minutes = int(digits or 1)
            return (now - timedelta(minutes=delta_minutes)).isoformat()
        if "day" in text:
            digits = "".join(ch for ch in text if ch.isdigit())
            delta_days = int(digits or 1)
            return (now - timedelta(days=delta_days)).isoformat()
        if "week" in text:
            digits = "".join(ch for ch in text if ch.isdigit())
            delta_weeks = int(digits or 1)
            return (now - timedelta(weeks=delta_weeks)).isoformat()
        return value

    def _location_terms(self, location: str) -> List[str]:
        normalized = self._normalize_location(location)
        terms = {normalized.lower()}
        for alias, canonical in self.LOCATION_ALIASES.items():
            if canonical.lower() == normalized.lower():
                terms.add(alias.lower())
        for part in normalized.lower().replace("-", " ").split():
            if len(part) > 2:
                terms.add(part)
        return sorted(terms)

    def _query_terms(self, query: Optional[str]) -> List[str]:
        if not query:
            return []
        tokens = []
        for token in query.lower().replace(",", " ").split():
            cleaned = token.strip()
            if len(cleaned) > 2:
                tokens.append(cleaned)
        return tokens

    def _is_relevant_article(self, article: Dict, location: str, query: Optional[str] = None) -> bool:
        text = f"{article.get('title', '')} {article.get('content', '')}".lower()
        location_terms = self._location_terms(location)
        has_location_match = any(term in text for term in location_terms)
        article_location = self._normalize_location(article.get("location", ""))
        article_location_match = article_location and article_location.lower() == self._normalize_location(location).lower()
        if not has_location_match and not article_location_match:
            return False

        query_terms = self._query_terms(query)
        if query_terms and not any(term in text for term in query_terms):
            relevance_score = float(article.get("relevance_score", 0) or 0)
            rank_score = float(article.get("rank_score", 0) or 0)
            if relevance_score < 0.72 and rank_score < 0.7:
                return False

        if article_location and article_location.lower() not in ("", self._normalize_location(location).lower()):
            if article_location.lower() not in text:
                return False

        return True

    def _fetch_live_news(
        self,
        location: str,
        query: Optional[str] = None,
        limit: int = 8
    ) -> List[Dict]:
        if not self.serpapi_key:
            return []

        location_name = self._normalize_location(location)
        news_query = (
            f"{location_name} real estate market property prices infrastructure"
            if not query
            else f"{location_name} real estate {query}"
        )

        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_news",
                    "q": news_query,
                    "gl": "in",
                    "hl": "en",
                    "api_key": self.serpapi_key,
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning(f"SerpApi live news fetch failed for {location_name}: {exc}")
            return []

        news_results = payload.get("news_results", [])[:limit]
        articles = []
        for index, item in enumerate(news_results):
            source_value = item.get("source")
            if isinstance(source_value, dict):
                source_name = source_value.get("name", "Google News")
            else:
                source_name = source_value or "Google News"

            article = {
                "id": f"live_{location_name.lower().replace(' ', '_')}_{index}",
                "title": item.get("title", ""),
                "content": item.get("snippet", ""),
                "location": "",
                "date": self._parse_relative_date(item.get("date", "")),
                "source": source_name,
                "url": item.get("link", ""),
                "live": True,
                "relevance_score": 0.88,
            }
            article["impact_score"] = self._estimate_impact_score(article)
            articles.append(article)

        return articles

    def _compute_signal_breakdown(self, articles: List[Dict]) -> List[Dict]:
        weighted_scores = defaultdict(float)
        total = 0.0
        for article in articles:
            signal_scores = self._extract_signals(article)
            article_weight = self._article_rank_score(article)
            for bucket, count in signal_scores.items():
                if count > 0:
                    weighted_scores[bucket] += count * article_weight
                    total += count * article_weight

        if total == 0:
            return []

        breakdown = []
        for bucket, weighted_value in weighted_scores.items():
            breakdown.append({
                "name": bucket,
                "value": round(weighted_value, 2),
                "share": round((weighted_value / total) * 100, 1),
            })

        breakdown.sort(key=lambda item: item["value"], reverse=True)
        return breakdown

    def _build_timeline(self, articles: List[Dict], periods: int = 6) -> List[Dict]:
        if not articles:
            return []

        daily_counts = defaultdict(int)
        daily_impact = defaultdict(float)
        undated_articles: List[float] = []
        for article in articles:
            article_date = self._safe_parse_datetime(article.get("date"))
            article_impact = self._safe_float(article.get("impact_score"), 0.5)
            if not article_date:
                undated_articles.append(article_impact)
                continue
            day_key = article_date.date().isoformat()
            daily_counts[day_key] += 1
            daily_impact[day_key] += article_impact

        if not daily_counts:
            # Fallback: synthesize a short recent timeline when article dates are unavailable.
            if not undated_articles:
                return []

            span = min(periods, max(2, len(undated_articles)))
            bucket_counts = [0] * span
            avg_impact = sum(undated_articles) / max(len(undated_articles), 1)

            for idx in range(len(undated_articles)):
                bucket_index = min(span - 1, int((idx * span) / max(len(undated_articles), 1)))
                bucket_counts[bucket_index] += 1

            start_day = datetime.now().date() - timedelta(days=span - 1)
            return [
                {
                    "date": (start_day + timedelta(days=offset)).isoformat(),
                    "articles": count,
                    "impact": round(avg_impact * 100, 1),
                }
                for offset, count in enumerate(bucket_counts)
            ]

        sorted_days = sorted(daily_counts.keys())[-periods:]
        timeline = []
        for day in sorted_days:
            count = daily_counts[day]
            avg_impact = daily_impact[day] / count if count else 0
            timeline.append({
                "date": day,
                "articles": count,
                "impact": round(avg_impact * 100, 1),
            })
        return timeline

    def _build_source_mix(self, articles: List[Dict]) -> List[Dict]:
        if not articles:
            return []
        source_counts = Counter(article.get("source", "Unknown") for article in articles)
        return [
            {"name": source, "value": count}
            for source, count in source_counts.most_common(5)
        ]

    def _calculate_confidence_score(self, articles: List[Dict]) -> float:
        if not articles:
            return 0.0

        unique_sources = len({article.get("source", "") for article in articles if article.get("source")})
        recent_articles = sum(
            1 for article in articles
            if self._recency_weight(self._safe_parse_datetime(article.get("date"))) >= 0.9
        )
        confidence = (
            min(len(articles) / 8, 1.0) * 0.45
            + min(unique_sources / 5, 1.0) * 0.35
            + min(recent_articles / max(len(articles), 1), 1.0) * 0.2
        )
        return round(confidence * 100, 1)

    def _build_market_summary(
        self,
        location: str,
        articles: List[Dict],
        signal_breakdown: List[Dict],
        impact_level: str,
    ) -> str:
        if not articles:
            return f"No recent market-moving articles were found for {location}."

        dominant_signals = ", ".join(item["name"] for item in signal_breakdown[:3]) or "mixed signals"
        recent_count = sum(
            1 for article in articles
            if self._recency_weight(self._safe_parse_datetime(article.get("date"))) >= 0.9
        )
        state_label = {
            "high_positive": "bullish",
            "moderate_positive": "improving",
            "neutral": "balanced",
            "negative": "cautious",
        }.get(impact_level, "mixed")
        return (
            f"{location} is currently showing a {state_label} market signal driven mainly by "
            f"{dominant_signals.lower()}. "
            f"{recent_count} of the retrieved articles are from the last 30 days, which makes this a fresher read than a simple headline count."
        )

    def _load_embedding_model(self):
        """
        Load embedding model with priority:
        1. Fine-tuned real estate embeddings (if available)
        2. Fall back to generic all-MiniLM-L6-v2
        """
        try:
            # Try to load fine-tuned model first
            fine_tuned_path = self._resolve_local_embedding_model()

            if fine_tuned_path is not None:
                logger.info(f"✅ Loading FINE-TUNED real estate embeddings from {fine_tuned_path}")
                self.embedding_model = SentenceTransformer(str(fine_tuned_path))
                self.model_type = "fine_tuned"
                logger.info("✅ Fine-tuned model loaded successfully")
                return
        except Exception as e:
            logger.warning(f"Could not load fine-tuned model: {str(e)}")

        # Fallback to generic model
        try:
            logger.info("📌 Loading generic all-MiniLM-L6-v2 embeddings...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.model_type = "generic"
            logger.info("✅ Generic model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load any embedding model: {str(e)}")
            raise

    def _is_schema_mismatch_error(self, error: Exception) -> bool:
        msg = str(error).lower()
        return (
            "no such column" in msg
            or "schema" in msg
            or "mismatch" in msg
            or "collections.topic" in msg
        )

    def _reinitialize_persist_store(self):
        """Backup and recreate Chroma persist directory when schema is incompatible."""
        self._release_chroma_client()
        persist_path = Path(self.persist_directory)
        if not persist_path.exists():
            return

        backup_path = persist_path.parent / f"{persist_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        try:
            shutil.move(str(persist_path), str(backup_path))
            logger.warning(f"Moved incompatible Chroma store to: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not backup old Chroma store ({e}). Attempting delete and recreate.")
            shutil.rmtree(persist_path, ignore_errors=True)

    def _release_chroma_client(self):
        """Best-effort release of Chroma resources before touching on-disk files."""
        client = self.chroma_client
        self.chroma_client = None
        if client is None:
            return
        del client
        gc.collect()

    def _recover_with_runtime_store(self):
        """Recover from schema mismatch by switching to a clean normalized runtime path."""
        self._reinitialize_persist_store()
        runtime_dir = self._runtime_persist_directory()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self.persist_directory = str(runtime_dir)
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=self._chroma_settings(),
        )

    def _bootstrap_collection_from_csv_if_empty(self):
        """Seed a fresh Chroma collection from the bundled news CSV."""
        if not self.rag_enabled or not self.chroma_client:
            return

        collection = self.collection
        if collection is None:
            return

        try:
            if collection.count() > 0:
                return
        except Exception as e:
            logger.warning(f"Could not inspect market news collection count: {e}")
            return

        if not self.seed_csv_path.exists():
            logger.warning(f"Market news seed CSV not found at {self.seed_csv_path}")
            return

        logger.info(f"Bootstrapping market news collection from {self.seed_csv_path}")
        self.load_news_from_csv(str(self.seed_csv_path))
    
    def _ensure_collection_exists(self):
        """Ensure the collection exists, create if it doesn't"""
        if not self.rag_enabled or not self.chroma_client:
            return
        try:
            self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing {self.collection_name} collection")
        except Exception as e:
            if self._is_schema_mismatch_error(e):
                logger.warning(
                    f"Detected Chroma schema mismatch while ensuring collection. Recovering store: {e}"
                )
                self._recover_with_runtime_store()
            try:
                self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Created new {self.collection_name} collection")
    
    @property
    def collection(self):
        """Get collection dynamically to handle collection refreshes"""
        if not self.rag_enabled or not self.chroma_client:
            return None
        try:
            return self.chroma_client.get_collection(name=self.collection_name)
        except Exception as e:
            logger.warning(f"Collection not found, recreating: {e}")
            self._ensure_collection_exists()
            return self.chroma_client.get_collection(name=self.collection_name)
    
    def add_news_articles(self, articles: List[Dict]):
        """
        Add news articles to the vector database
        
        Args:
            articles: List of dicts with keys: id, title, content, location, 
                     date, source, url, impact_score
        """
        try:
            if not self.rag_enabled:
                logger.warning("RAG disabled: skipping add_news_articles")
                return

            if not articles:
                logger.warning("No articles to add")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            for article in articles:
                title = self._safe_text(article.get("title", ""))
                content = self._safe_text(article.get("content", ""))
                article_id = self._safe_text(article.get("id", ""), default="") or f"news_{datetime.now().timestamp()}"
                location_text = self._safe_text(article.get("location", ""), default="unknown").lower()
                date_text = self._safe_text(article.get("date", ""), default=datetime.now().isoformat())
                source_text = self._safe_text(article.get("source", ""), default="unknown")
                url_text = self._safe_text(article.get("url", ""), default="")
                impact_score = self._safe_float(article.get("impact_score", 0.5), default=0.5)

                text_chunks = self._chunk_text(title, content)
                if not text_chunks:
                    continue

                for chunk_index, text in enumerate(text_chunks):
                    documents.append(text)

                    # Metadata for filtering and traceability back to source article
                    metadatas.append({
                        "location": location_text,
                        "date": date_text,
                        "source": source_text,
                        "url": url_text,
                        "impact_score": impact_score,
                        "title": title,
                        "article_id": article_id,
                        "chunk_index": chunk_index,
                    })

                    ids.append(f"{article_id}__chunk_{chunk_index}")

            if not documents:
                logger.warning("No valid article content chunks to add")
                return
            
            # Generate embeddings and add to collection
            embeddings = self.embedding_model.encode(documents).tolist()
            
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(articles)} source articles as {len(documents)} chunks to the database")
            
        except Exception as e:
            logger.error(f"Error adding articles: {str(e)}")
            raise
    
    def _search_csv_fallback(
        self, 
        location: str, 
        query: Optional[str] = None,
        n_results: int = 5,
        days_back: int = 365
    ) -> List[Dict]:
        """
        Fallback method to search CSV file when RAG is unavailable
        """
        try:
            df = None
            for csv_path in self._candidate_csv_paths():
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    break
            
            if df is None:
                logger.warning("No CSV file found in fallback mode")
                return []
            
            # Filter by location (case-insensitive)
            location_lower = location.lower()
            df_filtered = df[df['location'].str.lower().str.contains(location_lower, na=False)]
            
            # Additional query filter if provided
            if query:
                query_lower = query.lower()
                df_filtered = df_filtered[
                    df_filtered['title'].str.lower().str.contains(query_lower, na=False) |
                    df_filtered['content'].str.lower().str.contains(query_lower, na=False)
                ]
            
            # Filter by date if date column exists
            if 'date' in df_filtered.columns:
                try:
                    df_filtered = df_filtered.copy()
                    df_filtered['date_parsed'] = pd.to_datetime(df_filtered['date'], errors='coerce')
                    date_threshold = datetime.now() - timedelta(days=days_back)
                    df_filtered = df_filtered[df_filtered['date_parsed'] > date_threshold]
                except Exception:
                    pass
            
            # Sort by impact_score if available, otherwise by date
            if 'impact_score' in df_filtered.columns:
                df_filtered = df_filtered.sort_values('impact_score', ascending=False)
            elif 'date' in df_filtered.columns:
                df_filtered = df_filtered.sort_values('date', ascending=False)
            
            # Limit results
            df_filtered = df_filtered.head(n_results)
            
            # Convert to list of dicts
            articles = []
            for _, row in df_filtered.iterrows():
                articles.append({
                    "id": row.get('id', ''),
                    "title": row.get('title', ''),
                    "content": row.get('content', '')[:500],  # Truncate content
                    "location": row.get('location', ''),
                    "date": row.get('date', ''),
                    "source": row.get('source', ''),
                    "url": row.get('url', ''),
                    "impact_score": float(row.get('impact_score', 0.5)),
                    "relevance_score": 0.88,
                    "rank_score": 0.0,
                    "live": False,
                })
            
            logger.info(f"CSV fallback found {len(articles)} articles for {location}")
            return articles
            
        except Exception as e:
            logger.error(f"CSV fallback failed: {str(e)}")
            return []
    
    def retrieve_relevant_news(
        self,
        location: str,
        query: Optional[str] = None,
        n_results: int = 5,
        days_back: int = 365
    ) -> List[Dict]:
        """
        Retrieve relevant news articles for a location
        Now with optional domain-specific re-ranking and deduplication

        Args:
            location: Location to search for (e.g., "Mumbai", "Andheri")
            query: Optional specific query (e.g., "metro construction")
            n_results: Number of results to return
            days_back: Only return news from last N days

        Returns:
            List of relevant news articles with metadata
        """
        try:
            location = self._normalize_location(location)
            live_articles = self._fetch_live_news(location, query=query, limit=max(4, n_results * 2))
            local_articles = []

            if not self.rag_enabled:
                logger.info("RAG disabled: using CSV fallback for news search")
                local_articles = self._search_csv_fallback(location, query, n_results * 2, days_back)
            else:
                # Build query text - prioritize user's specific query
                if query:
                    query_text = f"{query} in {location} real estate property development"
                else:
                    query_text = f"{location} real estate infrastructure development news"

                # Generate query embedding
                query_embedding = self.embedding_model.encode([query_text]).tolist()

                # Query the collection without date filter (ChromaDB has limited filtering)
                # We'll filter by date in post-processing
                results = self.collection.query(
                    query_embeddings=query_embedding,
                    n_results=n_results * 4
                )

                # Calculate date threshold for filtering
                date_threshold = datetime.now() - timedelta(days=days_back)

                # Format results and filter by date
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        metadata = results['metadatas'][0][i]
                        article_date = self._safe_parse_datetime(metadata.get("date", ""))
                        if article_date and article_date.replace(tzinfo=None) < date_threshold:
                            continue

                        article = {
                            "content": doc,
                            "title": metadata.get("title", ""),
                            "location": self._normalize_location(metadata.get("location", "")),
                            "date": metadata.get("date", ""),
                            "source": metadata.get("source", ""),
                            "url": metadata.get("url", ""),
                            "impact_score": float(metadata.get("impact_score", 0.5) or 0.5),
                            "relevance_score": 1 - results['distances'][0][i] if results.get('distances') else 0.6,
                            "live": False,
                        }
                        if not article["impact_score"]:
                            article["impact_score"] = self._estimate_impact_score(article)
                        local_articles.append(article)

                        if len(local_articles) >= n_results * 3:
                            break

            merged_articles = self._dedupe_articles(live_articles + local_articles)

            if DOMAIN_OPT_AVAILABLE and merged_articles:
                logger.debug(f"Applying domain-specific optimization to {len(merged_articles)} articles")
                merged_articles = DomainOptimizer.optimize_retrieval(
                    articles=merged_articles,
                    location=location,
                    query=query,
                    apply_dedup=True
                )

            for article in merged_articles:
                if "impact_score" not in article or article.get("impact_score") is None:
                    article["impact_score"] = self._estimate_impact_score(article)
                article["rank_score"] = self._article_rank_score(article)

            merged_articles = [
                article for article in merged_articles
                if self._is_relevant_article(article, location, query=query)
            ]
            merged_articles.sort(key=lambda item: item.get("rank_score", 0), reverse=True)
            return merged_articles[:n_results]

        except Exception as e:
            logger.error(f"Error retrieving news: {str(e)}")
            return []
    
    def generate_alert(
        self,
        location: str,
        articles: List[Dict],
        user_properties: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Generate a market alert summary from retrieved articles
        Now with optional domain-specific indicators (fraud flags, market sentiment)

        Args:
            location: Location being analyzed
            articles: Retrieved relevant articles
            user_properties: Optional list of user's shortlisted properties

        Returns:
            Dict with alert summary and insights
        """
        location = self._normalize_location(location)
        try:
            if not articles:
                return {
                    "location": location,
                    "alert_summary": f"No recent market news found for {location}.",
                    "articles": [],
                    "impact_level": "neutral",
                    "recommendation": f"No relevant news was found in or around {location} right now.",
                    "confidence_score": 0,
                    "signal_breakdown": [],
                    "timeline": [],
                    "source_mix": [],
                    "market_summary": f"No relevant market-moving news was found in or around {location}. Try a nearby micro-market or a broader city search.",
                    "live_news_count": 0,
                    "retrieval_mode": "empty",
                }

            # Calculate average impact
            avg_impact = sum(a.get("impact_score", 0.5) for a in articles) / len(articles)

            # Determine impact level
            if avg_impact >= 0.7:
                impact_level = "high_positive"
                prefix = "Uptrend"
            elif avg_impact >= 0.5:
                impact_level = "moderate_positive"
                prefix = "Positive"
            elif avg_impact >= 0.3:
                impact_level = "neutral"
                prefix = "Balanced"
            else:
                impact_level = "negative"
                prefix = "Caution"

            signal_breakdown = self._compute_signal_breakdown(articles)
            timeline = self._build_timeline(articles)
            source_mix = self._build_source_mix(articles)
            confidence_score = self._calculate_confidence_score(articles)
            market_summary = self._build_market_summary(location, articles, signal_breakdown, impact_level)

            # Generate summary
            key_points = []
            for article in articles[:3]:  # Top 3 articles
                title = article.get("title", "")
                if title:
                    key_points.append(title)

            alert_summary = f"{prefix} market update for {location}:\n\n"
            alert_summary += "\n".join(f"- {point}" for point in key_points)

            # Generate recommendation
            if impact_level in ["high_positive", "moderate_positive"]:
                top_drivers = ", ".join(item["name"].lower() for item in signal_breakdown[:2]) or "recent positive signals"
                recommendation = (
                    f"Signals are supportive for {location}. Prioritize sub-markets where {top_drivers} are strongest, "
                    f"and validate asking prices against the newest launches and infra-led premiums."
                )
            elif impact_level == "neutral":
                recommendation = (
                    f"{location} looks balanced right now. Compare live pricing, delivery timelines, and inventory depth before committing."
                )
            else:
                recommendation = (
                    f"There are cautionary signals around {location}. Verify approvals, project timelines, and downside risks before acting."
                )

            # Property-specific impact
            property_impact = []
            if user_properties:
                for prop in user_properties:
                    if location.lower() in prop.get("location", "").lower():
                        property_impact.append({
                            "property_id": prop.get("id"),
                            "impact": f"This property may see {impact_level.replace('_', ' ')} impact based on recent developments."
                        })

            # Domain-specific insights (if available)
            domain_insights = {
                "fraud_warnings": [],
                "positive_signals": []
            }

            if DOMAIN_OPT_AVAILABLE and articles:
                # Extract fraud indicators and positive signals from articles
                for article in articles[:5]:  # From top 5 articles
                    if article.get('fraud_indicators'):
                        for flag in article['fraud_indicators'][:1]:  # Top 1 per article
                            domain_insights['fraud_warnings'].append(flag['detected'])

                    if article.get('positive_indicators'):
                        for indicator in article['positive_indicators'][:1]:  # Top 1 per article
                            domain_insights['positive_signals'].append(indicator['detected'])

            return {
                "location": location,
                "alert_summary": alert_summary,
                "articles": articles,
                "impact_level": impact_level,
                "avg_impact_score": round(avg_impact, 2),
                "recommendation": recommendation,
                "property_impact": property_impact,
                "domain_insights": domain_insights if DOMAIN_OPT_AVAILABLE else {},
                "model_type": self.model_type,  # Show which embedding model was used
                "confidence_score": confidence_score,
                "signal_breakdown": signal_breakdown,
                "timeline": timeline,
                "source_mix": source_mix,
                "market_summary": market_summary,
                "live_news_count": sum(1 for article in articles if article.get("live")),
                "retrieval_mode": "live_plus_rag" if any(article.get("live") for article in articles) else ("rag" if self.rag_enabled else "csv"),
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating alert: {str(e)}")
            return {
                "location": location,
                "alert_summary": f"Error generating alert for {location}",
                "articles": [],
                "impact_level": "unknown",
                "recommendation": "Unable to generate recommendation at this time.",
                "confidence_score": 0,
                "signal_breakdown": [],
                "timeline": [],
                "source_mix": [],
                "market_summary": f"Unable to generate a market summary for {location}.",
                "live_news_count": 0,
                "retrieval_mode": "error",
            }

    def _finalize_trending_stats(self, df: pd.DataFrame, top_n: int) -> List[Dict]:
        if df.empty:
            return []

        working_df = df.copy()
        working_df["location"] = working_df["location"].fillna("").map(self._normalize_location)
        working_df = working_df[~working_df["location"].str.lower().isin(["", "india"])]
        working_df = working_df[working_df["location"] != ""]
        if "impact_score" not in working_df.columns:
            working_df["impact_score"] = 0.5
        working_df["impact_score"] = pd.to_numeric(working_df["impact_score"], errors="coerce").fillna(0.5)
        if "source" not in working_df.columns:
            working_df["source"] = "Unknown"
        working_df["source"] = working_df["source"].fillna("Unknown")
        if "date" not in working_df.columns:
            working_df["date"] = None
        working_df["date_parsed"] = pd.to_datetime(working_df["date"], errors="coerce", utc=True)

        grouped_records = []
        fallback_records = []
        for location, group in working_df.groupby("location"):
            valid_dates = group["date_parsed"].dropna()
            if valid_dates.empty:
                recent_group = group
            else:
                recent_group = group[group["date_parsed"] >= (datetime.now(valid_dates.dt.tz) - timedelta(days=60))]
                if recent_group.empty:
                    recent_group = group

            signal_breakdown = self._compute_signal_breakdown(recent_group.to_dict("records"))
            source_mix = Counter(recent_group["source"].fillna("Unknown")).most_common(3)

            weekly_series = []
            if not valid_dates.empty:
                series_group = recent_group.copy()
                series_group["week_label"] = series_group["date_parsed"].dt.strftime("%d %b")
                weekly_counts = series_group.groupby("week_label").size().tail(4)
                weekly_series = [
                    {"label": label, "articles": int(count)}
                    for label, count in weekly_counts.items()
                ]

            news_count = int(len(recent_group))
            avg_impact = float(recent_group["impact_score"].mean())
            source_diversity = len(set(recent_group["source"].fillna("Unknown")))
            trend_score = (news_count * avg_impact) + (source_diversity * 0.6)

            record = {
                "location": location,
                "news_count": news_count,
                "avg_impact": round(avg_impact, 2),
                "trend_score": round(trend_score, 2),
                "momentum_series": weekly_series,
                "top_signals": [item["name"] for item in signal_breakdown[:2]],
                "source_diversity": source_diversity,
                "confidence_score": self._calculate_confidence_score(recent_group.to_dict("records")),
                "latest_date": valid_dates.max().isoformat() if not valid_dates.empty else None,
                "source_mix": [{"name": source, "value": count} for source, count in source_mix],
            }

            if len(group) >= 2:
                grouped_records.append(record)
            else:
                fallback_records.append(record)

        grouped_records.sort(key=lambda item: item["trend_score"], reverse=True)
        if len(grouped_records) < top_n:
            fallback_records.sort(key=lambda item: item["trend_score"], reverse=True)
            grouped_records.extend(fallback_records[: top_n - len(grouped_records)])
        return grouped_records[:top_n]
    
    def _trending_csv_fallback(self, top_n: int = 5) -> List[Dict]:
        """
        Fallback method to get trending locations from CSV
        """
        try:
            df = None
            for csv_path in self._candidate_csv_paths():
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    break
            
            if df is None:
                logger.warning("No CSV file found for trending locations")
                return []
            
            if 'date' in df.columns:
                try:
                    df = df.copy()
                    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
                    date_threshold = datetime.now(df['date_parsed'].dt.tz) - timedelta(days=120)
                    df = df[df['date_parsed'] > date_threshold]
                except Exception:
                    pass

            trending = self._finalize_trending_stats(df, top_n)
            
            logger.info(f"CSV fallback found {len(trending)} trending locations")
            return trending
            
        except Exception as e:
            logger.error(f"Trending CSV fallback failed: {str(e)}")
            return []
    
    def get_trending_locations(self, top_n: int = 5) -> List[Dict]:
        """
        Get trending locations based on recent news volume and impact
        
        Args:
            top_n: Number of top locations to return
        
        Returns:
            List of trending locations with stats
        """
        try:
            if not self.rag_enabled:
                logger.info("RAG disabled: using CSV fallback for trending locations")
                return self._trending_csv_fallback(top_n)

            # Get all documents (ChromaDB filtering is limited)
            results = self.collection.get(
                include=["metadatas"]
            )
            
            if not results['metadatas']:
                return []
            
            df = pd.DataFrame(results["metadatas"])
            if "date" in df.columns:
                df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
                date_threshold = datetime.now(df["date_parsed"].dt.tz) - timedelta(days=120)
                df = df[df["date_parsed"] > date_threshold]

            return self._finalize_trending_stats(df, top_n)
            
        except Exception as e:
            logger.error(f"Error getting trending locations: {str(e)}")
            return []
    
    def load_news_from_csv(self, csv_path: str):
        """
        Load news articles from a CSV file
        
        Expected columns: id, title, content, location, date, source, url, impact_score
        """
        try:
            df = pd.read_csv(csv_path)

            # Replace NaN/None at source so downstream article dicts are stable.
            df = df.where(pd.notna(df), None)
            
            # Ensure required columns
            required_cols = ['title', 'content', 'location']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Add default values for optional columns
            if 'id' not in df.columns:
                df['id'] = [f"news_{i}" for i in range(len(df))]
            if 'date' not in df.columns:
                df['date'] = datetime.now().isoformat()
            if 'source' not in df.columns:
                df['source'] = 'unknown'
            if 'url' not in df.columns:
                df['url'] = ''
            if 'impact_score' not in df.columns:
                df['impact_score'] = 0.5
            
            # Convert to list of dicts
            articles = df.to_dict('records')
            
            # Add to database
            self.add_news_articles(articles)
            
            logger.info(f"Loaded {len(articles)} articles from {csv_path}")
            
        except Exception as e:
            logger.error(f"Error loading news from CSV: {str(e)}")
            raise
