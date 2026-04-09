"""
Extract and infer location tags from Reddit post text and subreddit.
Fixes the issue where all posts had the same location tag.
"""

import re
from typing import List, Set, Dict
from .location_normalizer import LocationNormalizer, KNOWN_AREA_MAP


class LocationExtractor:
    """Extract location information from post text and subreddit."""

    def __init__(self):
        self.normalizer = LocationNormalizer(KNOWN_AREA_MAP)
        self.location_aliases = self._build_aliases()

    def _build_aliases(self) -> Dict[str, List[str]]:
        """Build mapping of subreddit to areas and additional aliases."""
        aliases = {
            "mumbai": ["Bandra", "Andheri", "Powai", "Worli", "Chembur", "Borivali", "Banjara Hills"],
            "delhi": ["Gurgaon", "Noida", "Delhi"],
            "bangalore": ["Whitefield", "Koramangala", "Indiranagar", "Electronic City"],
            "hyderabad": ["Gachibowli", "Hitech City", "Kondapur", "Banjara Hills"],
            "pune": ["Hinjawadi", "Kharadi", "Wakad", "Viman Nagar"],
            "gurgaon": ["Gurugram", "DLF Phase 2"],
            "noida": ["Noida", "Sector 137", "Sector 150"],
            "india": []  # Generic subreddit
        }
        return aliases

    def extract_locations_from_text(self, text: str) -> Set[str]:
        """Extract location mentions from post text."""
        if not text:
            return set()

        text_lower = text.lower()
        found_locations = set()

        # Search for exact area names and aliases
        for canonical, variants in KNOWN_AREA_MAP.items():
            # Check canonical name
            if re.search(r'\b' + re.escape(canonical) + r'\b', text_lower):
                found_locations.update(variants)
            # Check variants
            for variant in variants:
                if re.search(r'\b' + re.escape(variant.lower()) + r'\b', text_lower):
                    found_locations.add(variant)

        return found_locations

    def extract_from_subreddit(self, subreddit: str) -> List[str]:
        """Get typical locations for a subreddit."""
        subreddit_clean = subreddit.lower().replace("r/", "").strip()

        # Direct match
        if subreddit_clean in self.location_aliases:
            candidates = self.location_aliases[subreddit_clean]
            if candidates:
                return candidates

        # Try to normalize the subreddit name itself
        normalized = self.normalizer.normalize_location(subreddit_clean)
        if normalized:
            return normalized

        return []

    def extract_locations(self, post: Dict) -> List[str]:
        """
        Extract locations from a post - prefer subreddit over text for accuracy.

        Tries in order:
        1. Subreddit hints (most reliable indicator of post's location context)
        2. Text content analysis
        3. Fallback defaults
        """
        subreddit = post.get("subreddit", "").lower().replace("r/", "").strip()

        # Map subreddits to normalized/full location names
        subreddit_location_map = {
            "mumbai": ["Bandra West Mumbai", "Andheri West Mumbai", "Powai Mumbai"],
            "delhi": ["Gurugram", "Noida"],
            "bangalore": ["Whitefield Bengaluru", "Koramangala Bengaluru"],
            "hyderabad": ["Gachibowli Hyderabad", "Hitech City Hyderabad"],
            "pune": ["Hinjawadi Pune", "Kharadi Pune"],
            "gurgaon": ["DLF Phase 2 Gurugram", "Gurugram"],
            "noida": ["Sector 137 Noida"],
            "india": ["Bandra West Mumbai"],  # Generic fallback
        }

        # Try subreddit first (most accurate)
        if subreddit in subreddit_location_map:
            return subreddit_location_map[subreddit]

        # Try extracting from text
        text = post.get("text", "")
        text_locations = self.extract_locations_from_text(text)
        if text_locations:
            return list(text_locations)

        # Last resort fallback
        return ["India"]

    def rebuild_location_tags(self, records: List[Dict]) -> List[Dict]:
        """Rebuild location tags for all records, fixing the batch default issue."""
        updated = []
        for record in records:
            updated_record = dict(record)
            new_locations = self.extract_locations(record)
            updated_record["location_tags"] = new_locations
            updated.append(updated_record)
        return updated
