from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from typing import Dict, List
import re

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    fuzz = None
    process = None
    RAPIDFUZZ_AVAILABLE = False


KNOWN_AREA_MAP: Dict[str, List[str]] = {
    "bandra": ["Bandra West Mumbai", "Bandra East Mumbai"],
    "andheri": ["Andheri West Mumbai", "Andheri East Mumbai"],
    "powai": ["Powai Mumbai"],
    "worli": ["Worli Mumbai"],
    "chembur": ["Chembur Mumbai"],
    "borivali": ["Borivali East Mumbai", "Borivali West Mumbai"],
    "juhu": ["Juhu Mumbai"],
    "colaba": ["Colaba Mumbai"],
    "marine drive": ["Marine Drive Mumbai"],
    "malabar hill": ["Malabar Hill Mumbai"],
    "prabhadevi": ["Prabhadevi Mumbai"],
    "dadar": ["Dadar Mumbai"],
    "matunga": ["Matunga Mumbai"],
    "sion": ["Sion Mumbai"],
    "mahim": ["Mahim Mumbai"],
    "santacruz": ["Santacruz Mumbai"],
    "vile parle": ["Vile Parle Mumbai"],
    "kurla": ["Kurla Mumbai"],
    "ghatkopar": ["Ghatkopar Mumbai"],
    "mulund": ["Mulund Mumbai"],
    "bhandup": ["Bhandup Mumbai"],
    "kandivali": ["Kandivali Mumbai"],
    "malad": ["Malad Mumbai"],
    "goregaon": ["Goregaon Mumbai"],
    "sewri": ["Sewri Mumbai"],
    "wadala": ["Wadala Mumbai"],
    "parel": ["Parel Mumbai"],
    "lower parel": ["Lower Parel Mumbai"],
    "bkc": ["Bandra Kurla Complex Mumbai"],
    "whitefield": ["Whitefield Bengaluru"],
    "koramangala": ["Koramangala Bengaluru"],
    "indiranagar": ["Indiranagar Bengaluru"],
    "electronic city": ["Electronic City Bengaluru"],
    "gachibowli": ["Gachibowli Hyderabad"],
    "hitech city": ["Hitech City Hyderabad"],
    "kondapur": ["Kondapur Hyderabad"],
    "banjara hills": ["Banjara Hills Hyderabad"],
    "hinjawadi": ["Hinjawadi Pune"],
    "kharadi": ["Kharadi Pune"],
    "wakad": ["Wakad Pune"],
    "viman nagar": ["Viman Nagar Pune"],
    "gurgaon": ["Gurugram"],
    "gurugram": ["Gurugram"],
    "dlf phase 2": ["DLF Phase 2 Gurugram"],
    "noida": ["Noida"],
    "sector 137": ["Sector 137 Noida"],
    "sector 150": ["Sector 150 Noida"],
    "omr": ["OMR Chennai"],
    "velachery": ["Velachery Chennai"],
    "thoraipakkam": ["Thoraipakkam Chennai"],
}


@dataclass
class LocationNormalizer:
    known_area_map: Dict[str, List[str]]
    score_cutoff: int = 75

    def __post_init__(self) -> None:
        self._choices = list(self.known_area_map.keys())
        self._alias_lookup = {
            self._normalize_text(alias): canonical
            for canonical, variants in self.known_area_map.items()
            for alias in [canonical, *variants]
        }

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", (value or "").lower())).strip()

    def normalize_location(self, user_input: str) -> List[str]:
        normalized_input = self._normalize_text(user_input)
        if not normalized_input:
            return []

        if normalized_input in self.known_area_map:
            return self.known_area_map[normalized_input]

        if normalized_input in self._alias_lookup:
            return self.known_area_map[self._alias_lookup[normalized_input]]

        if RAPIDFUZZ_AVAILABLE and process is not None and fuzz is not None:
            matches = process.extract(
                normalized_input,
                self._choices,
                scorer=fuzz.WRatio,
                limit=3,
            )
            resolved = [
                match for match, score, _ in matches
                if score >= self.score_cutoff
            ]
        else:
            resolved = get_close_matches(normalized_input, self._choices, n=3, cutoff=0.70)

        expanded_locations: List[str] = []
        for match in resolved:
            expanded_locations.extend(self.known_area_map.get(match, []))

        if expanded_locations:
            return list(dict.fromkeys(expanded_locations))

        title_case = " ".join(part.capitalize() for part in normalized_input.split())
        return [title_case]

    def suggest_nearby_locations(self, user_input: str, limit: int = 4) -> List[str]:
        normalized_input = self._normalize_text(user_input)
        if not normalized_input:
            return []

        if RAPIDFUZZ_AVAILABLE and process is not None and fuzz is not None:
            matches = process.extract(
                normalized_input,
                self._choices,
                scorer=fuzz.partial_ratio,
                limit=limit,
            )
            return [self.known_area_map[match][0] for match, score, _ in matches if score >= 55]

        return [
            self.known_area_map[match][0]
            for match in get_close_matches(normalized_input, self._choices, n=limit, cutoff=0.45)
        ]


_DEFAULT_NORMALIZER = LocationNormalizer(known_area_map=KNOWN_AREA_MAP)


def normalize_location(user_input: str) -> List[str]:
    return _DEFAULT_NORMALIZER.normalize_location(user_input)
