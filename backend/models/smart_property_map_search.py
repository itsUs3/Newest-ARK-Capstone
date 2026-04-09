import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from models.amenity_matcher import AmenityMatcher


logger = logging.getLogger(__name__)


class SmartPropertyMapSearch:
    """Natural-language property discovery with map-ready results."""

    DATASET_FILES = [
        ("housing", "dataset_housing-com-scraper_2026-02-16_14-07-08-729.json"),
        ("magicbricks", "dataset_magicbricks-property-search-scraper_2026-02-16_14-32-19-208.json"),
        ("firecrawl", "firecrawl_mumbai_properties.json"),
    ]

    FEATURE_PATTERNS = {
        "sea_view": ["sea view", "sea-view", "sea facing", "waterfront", "ocean view", "sea"],
        "work_friendly": ["work from home", "wfh", "work environment", "workspace", "office", "quiet", "wifi", "internet"],
        "gym": ["gym", "fitness"],
        "parking": ["parking", "garage"],
        "pool": ["pool", "swimming"],
        "security": ["security", "gated", "cctv"],
        "metro_access": ["metro", "station", "connectivity"],
        "schools": ["school", "education"],
        "hospitals": ["hospital", "clinic", "medical"],
        "garden": ["garden", "park", "green"],
        "luxury": ["luxury", "premium", "concierge", "high-end"],
        "affordable": ["affordable", "budget", "value"],
    }

    PROPERTY_TYPE_PATTERNS = {
        "apartment": ["apartment", "flat", "multistorey"],
        "villa": ["villa", "bungalow", "independent house", "house"],
        "plot": ["plot", "land"],
        "project": ["project"],
    }

    STOP_WORDS = {
        "a", "an", "and", "the", "with", "for", "in", "near", "good", "best",
        "looking", "property", "properties", "estate", "real", "home", "homes",
        "need", "want", "me", "show", "find", "search",
    }

    COASTAL_LOCALITIES = {
        "mumbai": {"worli", "bandra", "bandra west", "juhu", "andheri west", "powai", "prabhadevi", "colaba"},
    }

    WORK_LOCALITIES = {
        "mumbai": {"andheri", "andheri west", "powai", "worli", "bkc", "bandra kurla complex", "vikhroli", "ghatkopar"},
        "bangalore": {"whitefield", "electronic city", "koramangala", "indiranagar"},
        "hyderabad": {"gachibowli", "hitech city"},
        "pune": {"hinjewadi", "baner"},
    }

    def __init__(self):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self.properties: List[Dict] = []
        self.location_terms = set()
        self._map_center_cache: Dict[str, Dict] = {}
        self._load_properties()

    def search(self, query: str, lifestyle: Optional[str] = None, top_k: int = 6) -> Dict:
        requirements = self._parse_requirements(query, lifestyle)
        candidates = self._initial_candidates(requirements)

        scored = []
        for prop in candidates:
            score, reasons = self._score_property(prop, requirements)
            if score <= 0:
                continue
            scored.append((prop, score, reasons))

        scored.sort(key=lambda item: item[1], reverse=True)
        top_matches = [self._serialize_match(prop, score, reasons) for prop, score, reasons in scored[:top_k]]
        map_center = self._resolve_map_center(requirements, top_matches)

        return {
            "success": True,
            "search_type": "map_discovery",
            "original_query": query,
            "optimized_query": query,
            "lifestyle_profile": requirements.get("lifestyle"),
            "parsed_requirements": self._public_requirements(requirements),
            "matches": top_matches,
            "map": {
                "center": map_center,
                "marker_count": len(top_matches),
            },
            "montage": None,
        }

    def _load_properties(self):
        for source, filename in self.DATASET_FILES:
            dataset_path = self.base_dir / "Datasets" / filename
            if not dataset_path.exists():
                continue

            try:
                raw_items = json.loads(dataset_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning(f"Could not load property dataset {filename}: {exc}")
                continue

            for item in raw_items if isinstance(raw_items, list) else []:
                normalized = self._normalize_property(item, source)
                if normalized:
                    self.properties.append(normalized)

        for prop in self.properties:
            for term in [prop.get("city"), prop.get("locality")]:
                if term:
                    self.location_terms.add(term.lower())

    def _normalize_property(self, item: Dict, source: str) -> Optional[Dict]:
        if source == "firecrawl":
            price_info = self._normalize_price(item.get("price") or item.get("price_numeric"))
            amenities = [str(x).strip().lower() for x in (item.get("amenities") or []) if x]
            name = str(item.get("name") or item.get("title") or "Property")
            city = str(item.get("city") or item.get("location") or "Mumbai")
            locality = str(item.get("locality") or city)
            address = str(item.get("address") or item.get("description") or "")
            searchable_text = " ".join([
                name,
                address,
                city,
                locality,
                " ".join(amenities),
                str(item.get("description") or ""),
            ]).lower()
            return {
                "id": str(item.get("id") or name or len(self.properties)),
                "name": name,
                "address": address,
                "city": city,
                "locality": locality,
                "source": "firecrawl",
                "latitude": self._coerce_float(item.get("latitude")),
                "longitude": self._coerce_float(item.get("longitude")),
                "price": price_info,
                "property_type": self._infer_property_type(name),
                "amenities": amenities,
                "bhk": item.get("bhk"),
                "searchable_text": searchable_text,
                "description": str(item.get("description") or ""),
            }

        if source == "housing":
            location = item.get("location") or {}
            coordinates = location.get("coordinates") or {}
            latitude = self._coerce_float(coordinates.get("latitude"))
            longitude = self._coerce_float(coordinates.get("longitude"))
            address = str(location.get("address") or "")
            city = str(location.get("city") or "")
            locality = str(location.get("locality") or "")
            amenities = [str(x).strip().lower() for x in (item.get("amenities") or []) if x]
            price_info = self._normalize_price(item.get("price"))
            property_type = self._infer_property_type(
                " ".join([str(item.get("title") or ""), str(item.get("propertyType") or "")])
            )
            searchable_text = " ".join([
                str(item.get("title") or ""),
                str(item.get("description") or ""),
                address,
                city,
                locality,
                " ".join(amenities),
                " ".join(str(x) for x in (item.get("propertyTags") or [])),
            ]).lower()
            bhk = self._extract_bhk(" ".join([str(item.get("title") or ""), str(item.get("configurations") or "")]))
            return {
                "id": str(item.get("propertyId") or item.get("title") or len(self.properties)),
                "name": str(item.get("title") or "Property"),
                "address": address,
                "city": city,
                "locality": locality,
                "source": "housing",
                "latitude": latitude,
                "longitude": longitude,
                "price": price_info,
                "property_type": property_type,
                "amenities": amenities,
                "bhk": bhk,
                "searchable_text": searchable_text,
                "description": str(item.get("description") or ""),
            }

        location_str = str(item.get("location") or "")
        latitude, longitude = self._parse_location_string(location_str)
        name = str(item.get("name") or item.get("title") or "Property")
        address = str(item.get("address") or "")
        city = str(item.get("city_name") or item.get("city") or "")
        locality = self._extract_locality_from_name(name) or city
        amenities_raw = item.get("amenities")
        if isinstance(amenities_raw, str):
            amenities = [x.strip().lower() for x in amenities_raw.split(",") if x.strip()]
        else:
            amenities = [str(x).strip().lower() for x in (amenities_raw or []) if x]
        price_info = self._normalize_price(item.get("price"))
        searchable_text = " ".join([
            name,
            address,
            city,
            locality,
            str(item.get("description") or ""),
            str(item.get("seo_description") or ""),
            " ".join(amenities),
            str(item.get("landmark") or ""),
        ]).lower()
        bhk = self._extract_bhk(" ".join([name, str(item.get("bedrooms") or "")]))
        return {
            "id": str(item.get("id") or name or len(self.properties)),
            "name": name,
            "address": address,
            "city": city,
            "locality": locality,
            "source": "magicbricks",
            "latitude": latitude,
            "longitude": longitude,
            "price": price_info,
            "property_type": self._infer_property_type(name),
            "amenities": amenities,
            "bhk": bhk,
            "searchable_text": searchable_text,
            "description": str(item.get("description") or ""),
        }

    def _parse_requirements(self, query: str, lifestyle: Optional[str]) -> Dict:
        query_lower = (query or "").lower()
        location = self._extract_location(query_lower)
        property_type = self._extract_property_type(query_lower)
        bhk = self._extract_bhk(query_lower)
        min_budget, max_budget, budget_label = self._extract_budget(query_lower, location)
        features = self._extract_features(query_lower, lifestyle)
        free_tokens = self._extract_free_tokens(query_lower, location, property_type, features)

        return {
            "query": query,
            "location": location,
            "property_type": property_type,
            "bhk": bhk,
            "budget_min": min_budget,
            "budget_max": max_budget,
            "budget_label": budget_label,
            "features": features,
            "tokens": free_tokens,
            "lifestyle": lifestyle,
        }

    def _extract_location(self, query_lower: str) -> str:
        candidates = sorted(self.location_terms, key=len, reverse=True)
        for term in candidates:
            if len(term) < 4:
                continue
            if term in query_lower:
                return term.title()
        return ""

    def _extract_property_type(self, query_lower: str) -> str:
        for canonical, patterns in self.PROPERTY_TYPE_PATTERNS.items():
            if any(pattern in query_lower for pattern in patterns):
                return canonical
        return ""

    def _extract_budget(self, query_lower: str, location: str) -> Tuple[Optional[float], Optional[float], str]:
        min_budget = None
        max_budget = None
        label = ""

        under_match = re.search(r"(under|below|less than|up to)\s+(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh)", query_lower)
        above_match = re.search(r"(above|over|more than)\s+(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh)", query_lower)
        between_match = re.search(
            r"between\s+(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh)\s+and\s+(\d+(?:\.\d+)?)\s*(cr|crore|l|lac|lakh)",
            query_lower,
        )

        if between_match:
            min_budget = self._to_inr(float(between_match.group(1)), between_match.group(2))
            max_budget = self._to_inr(float(between_match.group(3)), between_match.group(4))
            label = "Custom budget"
        elif under_match:
            max_budget = self._to_inr(float(under_match.group(2)), under_match.group(3))
            label = "Budget cap"
        elif above_match:
            min_budget = self._to_inr(float(above_match.group(2)), above_match.group(3))
            label = "Premium budget"

        if max_budget is None and any(word in query_lower for word in ["affordable", "budget", "value"]):
            city = (location or "").lower()
            max_budget = 20000000 if city in {"mumbai", "bangalore", "delhi"} else 12000000
            label = "Affordable"
        if min_budget is None and any(word in query_lower for word in ["luxury", "premium"]):
            min_budget = 30000000
            label = "Luxury"

        return min_budget, max_budget, label

    def _extract_features(self, query_lower: str, lifestyle: Optional[str]) -> List[str]:
        features = []
        for canonical, patterns in self.FEATURE_PATTERNS.items():
            if any(pattern in query_lower for pattern in patterns):
                features.append(canonical)

        if lifestyle:
            profile = AmenityMatcher.LIFESTYLE_PROFILES.get(lifestyle)
            if profile:
                if lifestyle == "Work From Home" and "work_friendly" not in features:
                    features.append("work_friendly")
                if lifestyle == "Luxury Living" and "luxury" not in features:
                    features.append("luxury")

        return sorted(set(features))

    def _extract_free_tokens(
        self,
        query_lower: str,
        location: str,
        property_type: str,
        features: List[str],
    ) -> List[str]:
        stripped = query_lower
        for term in [location.lower() if location else "", property_type]:
            if term:
                stripped = stripped.replace(term, " ")
        for feature in features:
            for pattern in self.FEATURE_PATTERNS.get(feature, []):
                stripped = stripped.replace(pattern, " ")

        return [
            token for token in re.findall(r"[a-z]+", stripped)
            if token not in self.STOP_WORDS and len(token) > 2
        ]

    def _initial_candidates(self, requirements: Dict) -> List[Dict]:
        location = (requirements.get("location") or "").lower()
        bhk = requirements.get("bhk")
        property_type = requirements.get("property_type")

        candidates = self.properties

        if location:
            location_hits = [
                prop for prop in candidates
                if location in " ".join([prop.get("address", ""), prop.get("city", ""), prop.get("locality", ""), prop.get("name", "")]).lower()
            ]
            if location_hits:
                candidates = location_hits

        if bhk:
            bhk_hits = [prop for prop in candidates if prop.get("bhk") == bhk]
            if bhk_hits:
                candidates = bhk_hits

        if property_type:
            type_hits = [prop for prop in candidates if prop.get("property_type") == property_type]
            if type_hits:
                candidates = type_hits

        return candidates

    def _score_property(self, prop: Dict, requirements: Dict) -> Tuple[float, List[str]]:
        score = 0.0
        reasons: List[str] = []
        text = prop.get("searchable_text", "")
        price_info = prop.get("price") or {}

        location = (requirements.get("location") or "").lower()
        if location:
            if location in text:
                score += 30
                reasons.append("Matches requested location")
            else:
                score -= 30

        property_type = requirements.get("property_type")
        if property_type:
            if prop.get("property_type") == property_type:
                score += 14
                reasons.append(f"{property_type.title()} style match")
            else:
                score -= 8

        bhk = requirements.get("bhk")
        if bhk:
            if prop.get("bhk") == bhk:
                score += 10
                reasons.append(f"{bhk} BHK match")
            else:
                score -= 10

        numeric_price = price_info.get("numeric")
        budget_min = requirements.get("budget_min")
        budget_max = requirements.get("budget_max")
        if numeric_price is not None:
            if budget_min is not None and numeric_price < budget_min:
                score -= 14
            elif budget_max is not None and numeric_price > budget_max:
                score -= 14
            elif budget_min is not None or budget_max is not None:
                score += 12
                reasons.append("Within budget intent")

        matched_features = 0
        for feature in requirements.get("features", []):
            if self._property_matches_feature(prop, feature):
                matched_features += 1
                reasons.append(self._feature_reason(feature))
        score += matched_features * 9

        for token in requirements.get("tokens", []):
            if token in text:
                score += 3

        if matched_features == 0 and requirements.get("features"):
            score -= 8

        if prop.get("latitude") is not None and prop.get("longitude") is not None:
            score += 4

        return score, reasons[:4]

    def _property_matches_feature(self, prop: Dict, feature: str) -> bool:
        text = prop.get("searchable_text", "")
        city = (prop.get("city") or "").lower()
        locality = (prop.get("locality") or "").lower()

        if feature == "sea_view":
            if any(pattern in text for pattern in self.FEATURE_PATTERNS["sea_view"]):
                return True
            return locality in self.COASTAL_LOCALITIES.get(city, set())

        if feature == "work_friendly":
            if any(pattern in text for pattern in self.FEATURE_PATTERNS["work_friendly"]):
                return True
            return locality in self.WORK_LOCALITIES.get(city, set())

        return any(pattern in text for pattern in self.FEATURE_PATTERNS.get(feature, []))

    def _feature_reason(self, feature: str) -> str:
        return {
            "sea_view": "Sea-facing/coastal context",
            "work_friendly": "Work-friendly area",
            "gym": "Gym/fitness access",
            "parking": "Parking available",
            "pool": "Pool amenity",
            "security": "Security/gated access",
            "metro_access": "Good connectivity",
            "schools": "Schools nearby",
            "hospitals": "Healthcare nearby",
            "garden": "Green surroundings",
            "luxury": "Luxury positioning",
            "affordable": "Affordable pricing",
        }.get(feature, feature.replace("_", " ").title())

    def _serialize_match(self, prop: Dict, score: float, reasons: List[str]) -> Dict:
        price_info = prop.get("price") or {}
        latitude = prop.get("latitude")
        longitude = prop.get("longitude")

        if (latitude is None or longitude is None) and self.serpapi_key:
            latitude, longitude = self._lookup_property_coordinates(prop)

        return {
            "id": prop.get("id"),
            "name": prop.get("name"),
            "address": prop.get("address"),
            "city": prop.get("city"),
            "locality": prop.get("locality"),
            "source": prop.get("source"),
            "price": price_info.get("label") or "Price on request",
            "rawPrice": price_info.get("raw"),
            "priceNumeric": price_info.get("numeric"),
            "property_type": prop.get("property_type"),
            "bhk": prop.get("bhk"),
            "amenities": prop.get("amenities", [])[:8],
            "latitude": latitude,
            "longitude": longitude,
            "similarity_score": round(max(score, 0) / 100, 3),
            "match_reasons": reasons,
        }

    def _resolve_map_center(self, requirements: Dict, matches: List[Dict]) -> Dict:
        location = requirements.get("location")
        if location and self.serpapi_key:
            cached = self._map_center_cache.get(location.lower())
            if cached:
                return cached

            params = {
                "engine": "google_local",
                "q": f"real estate in {location}",
                "hl": "en",
                "gl": "in",
                "api_key": self.serpapi_key,
            }
            try:
                response = requests.get("https://serpapi.com/search.json", params=params, timeout=15)
                response.raise_for_status()
                payload = response.json()
                local_results = payload.get("local_results") or []
                if local_results:
                    gps = (local_results[0].get("gps_coordinates") or {})
                    center = {
                        "latitude": float(gps.get("latitude")),
                        "longitude": float(gps.get("longitude")),
                        "label": location,
                        "source": "serpapi",
                    }
                    self._map_center_cache[location.lower()] = center
                    return center
            except Exception as exc:
                logger.warning(f"Could not resolve live map center for {location}: {exc}")

        coords = [(item.get("latitude"), item.get("longitude")) for item in matches if item.get("latitude") is not None and item.get("longitude") is not None]
        if coords:
            avg_lat = sum(lat for lat, _ in coords) / len(coords)
            avg_lng = sum(lng for _, lng in coords) / len(coords)
            return {
                "latitude": avg_lat,
                "longitude": avg_lng,
                "label": location or "Search area",
                "source": "matches",
            }

        return {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "label": location or "India",
            "source": "default",
        }

    def _lookup_property_coordinates(self, prop: Dict) -> Tuple[Optional[float], Optional[float]]:
        query = ", ".join(filter(None, [prop.get("name"), prop.get("locality"), prop.get("city")]))
        params = {
            "engine": "google_local",
            "q": query,
            "hl": "en",
            "gl": "in",
            "api_key": self.serpapi_key,
        }
        try:
            response = requests.get("https://serpapi.com/search.json", params=params, timeout=15)
            response.raise_for_status()
            payload = response.json()
            local_results = payload.get("local_results") or []
            if not local_results:
                return None, None
            gps = local_results[0].get("gps_coordinates") or {}
            return self._coerce_float(gps.get("latitude")), self._coerce_float(gps.get("longitude"))
        except Exception as exc:
            logger.warning(f"Could not geocode property {query}: {exc}")
            return None, None

    def _normalize_price(self, raw_price) -> Dict:
        if isinstance(raw_price, dict):
            min_value = self._coerce_float(raw_price.get("minValue"))
            max_value = self._coerce_float(raw_price.get("maxValue"))
            numeric = min_value or max_value
            return {
                "raw": raw_price,
                "label": raw_price.get("range") or self._format_price(numeric),
                "numeric": numeric,
            }

        numeric = self._coerce_float(raw_price)
        return {
            "raw": raw_price,
            "label": self._format_price(numeric) if numeric is not None else str(raw_price or "Price on request"),
            "numeric": numeric,
        }

    def _parse_location_string(self, raw: str) -> Tuple[Optional[float], Optional[float]]:
        if not raw or "," not in raw:
            return None, None
        parts = [x.strip() for x in raw.split(",")]
        if len(parts) != 2:
            return None, None
        return self._coerce_float(parts[0]), self._coerce_float(parts[1])

    def _extract_locality_from_name(self, name: str) -> str:
        match = re.search(r"at\s+([A-Za-z\s]+)$", name)
        return match.group(1).strip() if match else ""

    def _extract_bhk(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*bhk", text.lower())
        if match:
            return int(match.group(1))
        bedroom_match = re.search(r"\b(\d+)\s*bed", text.lower())
        if bedroom_match:
            return int(bedroom_match.group(1))
        return None

    def _infer_property_type(self, text: str) -> str:
        text_lower = (text or "").lower()
        for canonical, patterns in self.PROPERTY_TYPE_PATTERNS.items():
            if any(pattern in text_lower for pattern in patterns):
                return canonical
        return "apartment"

    def _format_price(self, value: Optional[float]) -> str:
        if value is None:
            return "Price on request"
        if value >= 10000000:
            return f"₹{value / 10000000:.2f} Cr"
        if value >= 100000:
            return f"₹{value / 100000:.2f} L"
        return f"₹{int(value):,}"

    def _public_requirements(self, requirements: Dict) -> Dict:
        return {
            "location": requirements.get("location"),
            "property_type": requirements.get("property_type"),
            "bhk": requirements.get("bhk"),
            "budget_label": requirements.get("budget_label"),
            "budget_min": requirements.get("budget_min"),
            "budget_max": requirements.get("budget_max"),
            "features": requirements.get("features", []),
            "lifestyle": requirements.get("lifestyle"),
        }

    def _to_inr(self, value: float, unit: str) -> float:
        unit = unit.lower()
        if unit in {"cr", "crore"}:
            return value * 10000000
        return value * 100000

    def _coerce_float(self, value) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None
