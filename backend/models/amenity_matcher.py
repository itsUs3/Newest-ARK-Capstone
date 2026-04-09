import os
import json
import re
from typing import List, Dict, Optional, Tuple
import logging

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class AmenityMatcher:
    """
    Matches user lifestyle preferences to property amenities using
    TF-IDF cosine similarity, then generates a personalised pitch.

    Data sources:
      - MagicBricks JSON  : amenities as comma-separated string
      - Housing.com JSON  : amenities as JSON array of strings
      - 99acres JSON      : no amenities field (skipped)
    """

    # ------------------------------------------------------------------ #
    # Lifestyle profiles — keywords drive the TF-IDF matching             #
    # ------------------------------------------------------------------ #
    LIFESTYLE_PROFILES = {
        "Family with Kids": {
            "icon": "👨‍👩‍👧‍👦",
            "keywords": [
                "kids play area", "children play", "swimming pool", "garden",
                "park", "jogging track", "security", "gated community",
                "cctv", "school nearby", "creche", "basketball court",
                "badminton", "indoor games", "visitor parking"
            ],
            "color": "blue",
        },
        "Young Professional": {
            "icon": "💼",
            "keywords": [
                "gym", "wifi", "internet", "parking", "concierge",
                "conference room", "co-working", "rooftop", "cafeteria",
                "lift", "air conditioned", "intercom", "smart home",
                "fingerprint access", "metro", "clubhouse"
            ],
            "color": "indigo",
        },
        "Fitness Enthusiast": {
            "icon": "🏋️",
            "keywords": [
                "gym", "jogging track", "jogging and strolling", "swimming pool",
                "tennis court", "outdoor tennis", "health club", "steam",
                "jacuzzi", "yoga", "basketball", "badminton", "squash",
                "cycling track", "sports facility"
            ],
            "color": "green",
        },
        "Luxury Living": {
            "icon": "✨",
            "keywords": [
                "smart home", "skydeck", "bar lounge", "concierge", "sea facing",
                "water front", "skyline view", "jacuzzi", "private jacuzzi",
                "air conditioned", "fingerprint access", "full glass wall",
                "island kitchen", "house help accommodation", "laundry service",
                "golf course", "banquet hall", "downtown"
            ],
            "color": "amber",
        },
        "Work From Home": {
            "icon": "🏠💻",
            "keywords": [
                "wifi", "internet", "conference room", "smart home",
                "air conditioned", "quiet", "power backup", "24x7 security",
                "intercom", "parking", "lift", "concierge"
            ],
            "color": "violet",
        },
        "Retired Couple": {
            "icon": "🌿",
            "keywords": [
                "garden", "park", "jogging track", "security", "lift",
                "hospital nearby", "quiet", "gated community", "cctv",
                "intercom", "visitor parking", "banquet hall", "temple",
                "community hall", "senior citizen"
            ],
            "color": "teal",
        },
    }

    # Files relative to Datasets/ folder
    MAGICBRICKS_FILE = "dataset_magicbricks-property-search-scraper_2026-02-16_14-32-19-208.json"
    HOUSING_FILE     = "dataset_housing-com-scraper_2026-02-16_14-07-08-729.json"

    def __init__(self):
        self.properties: List[Dict] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._property_matrix = None
        self._cross_modal_available: Optional[bool] = None
        self._load_data()
        self._build_index()

    # ------------------------------------------------------------------ #
    # Data loading                                                         #
    # ------------------------------------------------------------------ #

    def _dataset_path(self, filename: str) -> Optional[str]:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        p = os.path.join(base, "Datasets", filename)
        if os.path.exists(p):
            return p
        fallback = os.path.join("..", "Datasets", filename)
        return fallback if os.path.exists(fallback) else None

    def _parse_amenities(self, raw, source: str) -> List[str]:
        """Normalise amenities from different source formats."""
        if not raw:
            return []
        if source == "magicbricks":
            if isinstance(raw, str):
                return [a.strip().lower() for a in raw.split(",") if a.strip()]
            if isinstance(raw, list):
                return [str(a).strip().lower() for a in raw if a]
        if source == "housing":
            if isinstance(raw, list):
                return [str(a).strip().lower() for a in raw if a]
            if isinstance(raw, str):
                return [a.strip().lower() for a in raw.split(",") if a.strip()]
        return []

    def _load_json(self, filename: str, source: str):
        path = self._dataset_path(filename)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        for item in (data if isinstance(data, list) else []):
            amenities = self._parse_amenities(item.get("amenities"), source)
            if not amenities:
                continue
            self.properties.append({
                "source":    source,
                "name":      item.get("name") or item.get("title") or "Unknown Property",
                "address":   str(item.get("address") or item.get("locality") or ""),
                "city":      str(item.get("city_name") or item.get("city") or ""),
                "price":     item.get("price") or item.get("minValue"),
                "amenities": amenities,
                "amenity_text": " ".join(amenities),
            })

    def _load_data(self):
        self._load_json(self.MAGICBRICKS_FILE, "magicbricks")
        self._load_json(self.HOUSING_FILE,     "housing")

    # ------------------------------------------------------------------ #
    # TF-IDF index                                                         #
    # ------------------------------------------------------------------ #

    def _build_index(self):
        if not self.properties:
            return
        corpus = [p["amenity_text"] for p in self.properties]
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        self._property_matrix = self._vectorizer.fit_transform(corpus)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def match(self, lifestyle: str, location: str = "") -> Dict:
        """
        Given a user lifestyle string (preset name or free text) and an
        optional location filter, return:
          - lifestyle_profile : matched preset name (or "Custom")
          - matched_amenities : list of top amenity strings
          - pitch             : personalised narrative
          - similar_count     : number of properties with high match score
          - top_properties    : up to 5 best-matching property summaries
        """
        # Resolve to a profile or treat as free text
        profile_name, profile_keywords = self._resolve_profile(lifestyle)

        query_text = " ".join(profile_keywords) if profile_keywords else lifestyle

        # Filter by location if provided
        candidates = self._filter_by_location(location) if location.strip() else self.properties

        if location.strip() and not candidates:
            return {
                "lifestyle_profile": profile_name,
                "matched_amenities": [],
                "pitch": f"No matching properties found in '{location}'. Try a nearby micro-market or clear the location filter.",
                "similar_count": 0,
                "top_properties": [],
                "total_indexed": len(self.properties),
            }

        if not candidates or self._vectorizer is None:
            return self._fallback_response(lifestyle, profile_name)

        # Score candidates
        scored = self._score_candidates(query_text, candidates)

        # Top amenities aggregated from best matches
        threshold  = 0.15
        good_props = [(p, s) for p, s in scored if s >= threshold]
        similar_count = len(good_props)

        top5 = good_props[:5]
        matched_amenities = self._top_amenities(top5, profile_keywords, query_text)

        pitch = self._generate_pitch(
            lifestyle=lifestyle,
            profile_name=profile_name,
            location=location,
            matched_amenities=matched_amenities,
            similar_count=similar_count,
            top5=top5,
        )

        top_properties_out = []
        for prop, score in top5:
            top_properties_out.append({
                "name":      prop["name"],
                "address":   prop["address"],
                "city":      prop["city"],
                "source":    prop["source"],
                "amenities": prop["amenities"][:8],
                "score":     round(float(score), 3),
            })

        return {
            "lifestyle_profile":  profile_name,
            "matched_amenities":  matched_amenities,
            "pitch":              pitch,
            "similar_count":      similar_count,
            "top_properties":     top_properties_out,
            "total_indexed":      len(self.properties),
        }

    # ================================================================== #
    # Cross-Modal Search Integration                                      #
    # ================================================================== #

    def get_cross_modal_recommendations(
        self, 
        query: str, 
        lifestyle: Optional[str] = None,
        top_k: int = 6,
        use_cross_modal: bool = True
    ) -> Dict:
        """
        Get property recommendations using cross-modal retrieval.
        
        Bridges amenity matcher lifestyle profiles with cross-modal semantic search.
        If lifestyle is provided, optimizes the query with lifestyle keywords.
        
        Args:
            query: Text query (e.g., "affordable sea-view flat")
            lifestyle: Optional lifestyle profile name (e.g., "Family with Kids")
            top_k: Number of top results to return (default 6)
            use_cross_modal: If True, use CrossModalMatcher; if False, fallback to amenity matching
            
        Returns:
            Dict with: matches, montage (base64), search_type, lifestyle_optimized
        """
        try:
            # Optimize query if lifestyle provided
            optimized_query = query
            lifestyle_matched = None
            
            if lifestyle:
                profile_name, keywords = self._resolve_profile(lifestyle)
                lifestyle_matched = profile_name
                # Append profile keywords to query for better semantic matching
                kw_str = " ".join(keywords[:3])  # Top 3 keywords
                optimized_query = f"{query} {kw_str}".strip()
            
            # Use cross-modal matcher
            if use_cross_modal:
                if self._cross_modal_available is False:
                    raise RuntimeError("Cross-modal matcher unavailable in current environment")
                from .cross_modal_matcher import CrossModalMatcher
                matcher = CrossModalMatcher()
                self._cross_modal_available = True
                results = matcher.search_text(optimized_query, top_k=top_k)
                
                return {
                    "success": True,
                    "search_type": "cross_modal",
                    "original_query": query,
                    "optimized_query": optimized_query,
                    "lifestyle_profile": lifestyle_matched,
                    "matches": results.get("matches", []),
                    "montage": results.get("montage", None),
                    "stats": results.get("stats", {}),
                    "integration_source": "cross_modal_matcher"
                }

            fallback_result = self.match(
                lifestyle=lifestyle or query or "Custom",
                location=""
            )
            fallback_result["search_type"] = "fallback_amenity"
            fallback_result["original_query"] = query
            fallback_result["optimized_query"] = optimized_query
            fallback_result["lifestyle_profile"] = lifestyle_matched or fallback_result.get("lifestyle_profile")
            return fallback_result
                
        except ImportError as e:
            self._cross_modal_available = False
            logger.warning(f"CrossModalMatcher not available: {e}. Falling back to amenity matching.")
            fallback_result = self.match(
                lifestyle=lifestyle or query or "Custom",
                location=""
            )
            fallback_result["search_type"] = "fallback_amenity"
            fallback_result["original_query"] = query
            fallback_result["optimized_query"] = query
            return fallback_result
        except Exception as e:
            self._cross_modal_available = False
            logger.error(f"Error in cross-modal recommendations: {e}")
            fallback_result = self.match(
                lifestyle=lifestyle or query or "Custom",
                location=""
            )
            fallback_result["search_type"] = "fallback_amenity"
            fallback_result["original_query"] = query
            fallback_result["optimized_query"] = query
            fallback_result["fallback_reason"] = str(e)
            return fallback_result

    def optimize_search_query(self, lifestyle: str) -> str:
        """
        Convert lifestyle profile to optimized search query for semantic search.
        
        Useful for transforming "Family with Kids" to 
        "family friendly property, kids play area, swimming pool, schools nearby".
        
        Args:
            lifestyle: Lifestyle profile name
            
        Returns:
            Optimized search query string
        """
        profile_name, keywords = self._resolve_profile(lifestyle)
        
        # Map lifestyle to detailed query
        lifestyle_queries = {
            "Family with Kids": "family friendly property kids play area swimming pool school nearby safe gated",
            "Young Professional": "modern apartment gym fitness near office workplace commute metro",
            "Fitness Enthusiast": "gym sports facility yoga swimming pool fitness center active lifestyle",
            "Luxury Living": "luxury apartment premium amenities high-end finishes concierge service",
            "Work From Home": "quiet space independent workspace internet speed studying office room",
            "Retired Couple": "peaceful community senior friendly healthcare accessibility easy maintenance",
        }
        
        base_query = lifestyle_queries.get(profile_name, " ".join(keywords))
        return base_query

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _resolve_profile(self, lifestyle: str) -> Tuple[str, List[str]]:
        """Return the best matching preset profile name and its keywords."""
        lower = lifestyle.lower().strip()
        # Direct name match
        for name, info in self.LIFESTYLE_PROFILES.items():
            if name.lower() == lower:
                return name, info["keywords"]
        # Partial / fuzzy match
        for name, info in self.LIFESTYLE_PROFILES.items():
            if any(word in lower for word in name.lower().split()):
                return name, info["keywords"]
        # Keyword match against profile keywords
        best_name, best_count = "Custom", 0
        best_kw: List[str] = []
        for name, info in self.LIFESTYLE_PROFILES.items():
            hits = sum(1 for kw in info["keywords"] if kw.split()[0] in lower)
            if hits > best_count:
                best_count, best_name, best_kw = hits, name, info["keywords"]
        if best_count > 0:
            return best_name, best_kw
        return "Custom", []

    def _filter_by_location(self, location: str) -> List[Dict]:
        q = location.lower().replace(" ", "")
        q_short = q.split(",")[0]
        return [
            p for p in self.properties
            if q_short in p["address"].lower().replace(" ", "")
            or q_short in p["city"].lower().replace(" ", "")
            or q_short in p["name"].lower().replace(" ", "")
        ]

    def _score_candidates(self, query_text: str, candidates: List[Dict]) -> List[Tuple[Dict, float]]:
        """Vectorise query and compute cosine similarity against candidates."""
        # Build a local index for the candidates subset
        corpus = [p["amenity_text"] for p in candidates]
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            matrix = vectorizer.fit_transform(corpus)
            q_vec = vectorizer.transform([query_text])
            scores = cosine_similarity(q_vec, matrix).flatten()
        except Exception:
            scores = np.zeros(len(candidates))

        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return ranked

    def _top_amenities(
        self, top5: List[Tuple[Dict, float]], profile_kw: List[str], query_text: str
    ) -> List[str]:
        """Pick the most relevant amenities from top matching properties."""
        freq: Dict[str, int] = {}
        for prop, _ in top5:
            for a in prop["amenities"]:
                freq[a] = freq.get(a, 0) + 1

        # Prefer amenities that appear in profile keywords
        def priority(amenity: str) -> Tuple[int, int]:
            in_profile = int(any(kw in amenity or amenity in kw for kw in profile_kw))
            return (-in_profile, -freq[amenity])

        return sorted(freq.keys(), key=priority)[:12]

    # ------------------------------------------------------------------ #
    # Pitch generation                                                     #
    # ------------------------------------------------------------------ #

    def _generate_pitch(
        self,
        lifestyle: str,
        profile_name: str,
        location: str,
        matched_amenities: List[str],
        similar_count: int,
        top5: List[Tuple[Dict, float]],
    ) -> str:
        loc_str = f" in {location}" if location.strip() else ""
        profile = self.LIFESTYLE_PROFILES.get(profile_name, {})
        icon = profile.get("icon", "🏠")

        lines = [f"Personalized Amenity Report {icon}", f"Lifestyle: {profile_name}", ""]

        if not matched_amenities:
            lines.append(
                f"We couldn't find strong amenity matches for '{lifestyle}'{loc_str} "
                "in our current dataset. Try a broader location or a different lifestyle profile."
            )
            return "\n".join(lines)

        # Opening sentence
        top_amenity_names = ", ".join(
            a.title() for a in matched_amenities[:3]
        )
        lines.append(
            f"Based on your '{lifestyle}' lifestyle, we found properties{loc_str} "
            f"featuring {top_amenity_names} — and more."
        )

        # Profile-specific paragraphs
        if profile_name == "Family with Kids":
            play = next((a for a in matched_amenities if "play" in a or "kids" in a), None)
            pool = next((a for a in matched_amenities if "pool" in a or "swimming" in a), None)
            garden = next((a for a in matched_amenities if "garden" in a or "park" in a), None)
            parts = []
            if play:
                parts.append(f"a {play.title()}")
            if pool:
                parts.append(f"a {pool.title()}")
            if garden:
                parts.append(f"a {garden.title()}")
            if parts:
                lines.append(
                    f"These properties offer {', '.join(parts)}, making them ideal for "
                    "raising children in a safe, activity-rich environment."
                )

        elif profile_name == "Fitness Enthusiast":
            fitness = [a for a in matched_amenities if any(
                w in a for w in ["gym", "jogging", "tennis", "pool", "health", "yoga", "court"]
            )]
            if fitness:
                lines.append(
                    f"Your fitness routine is covered: {', '.join(a.title() for a in fitness[:4])} "
                    "are all available within the complex."
                )

        elif profile_name == "Luxury Living":
            luxury = [a for a in matched_amenities if any(
                w in a for w in ["sky", "bar", "concierge", "smart", "sea", "jacuzzi", "golf", "glass"]
            )]
            if luxury:
                lines.append(
                    f"Premium touches include: {', '.join(a.title() for a in luxury[:4])} — "
                    "crafted for discerning residents who expect the best."
                )

        elif profile_name == "Young Professional":
            work = [a for a in matched_amenities if any(
                w in a for w in ["wifi", "internet", "conference", "concierge", "smart", "parking"]
            )]
            if work:
                lines.append(
                    f"Built for your hustling lifestyle: {', '.join(a.title() for a in work[:4])} "
                    "keep you productive and connected."
                )

        elif profile_name == "Work From Home":
            wfh = [a for a in matched_amenities if any(
                w in a for w in ["wifi", "internet", "conference", "air", "power", "smart"]
            )]
            if wfh:
                lines.append(
                    f"Work-from-home ready with: {', '.join(a.title() for a in wfh[:4])} — "
                    "no more café-hopping for a reliable connection."
                )

        elif profile_name == "Retired Couple":
            peaceful = [a for a in matched_amenities if any(
                w in a for w in ["garden", "park", "jogging", "security", "lift", "intercom"]
            )]
            if peaceful:
                lines.append(
                    f"Designed for peaceful living: {', '.join(a.title() for a in peaceful[:4])} "
                    "ensure comfort, safety, and a healthy daily routine."
                )

        # Similar listings line
        if similar_count > 0:
            first_prop = top5[0][0] if top5 else None
            prop_area = first_prop["address"].split(",")[0] if first_prop else location or "this area"
            lines.append(
                f"Similar to {similar_count} other listing(s) in our dataset that match your profile"
                + (f" near {prop_area}." if prop_area.strip() else ".")
            )

        return "\n".join(lines)

    def _fallback_response(self, lifestyle: str, profile_name: str) -> Dict:
        return {
            "lifestyle_profile":  profile_name,
            "matched_amenities":  [],
            "pitch":              f"No amenity data available to match '{lifestyle}'. Try running the backend with both MagicBricks and Housing.com datasets present.",
            "similar_count":      0,
            "top_properties":     [],
            "total_indexed":      0,
        }
