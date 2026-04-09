import random
from typing import Dict, List
from urllib.parse import quote_plus
from urllib.parse import urlparse

import requests

class ComparisonEngine:
    """
    Mock price comparison engine for cross-platform offers
    """

    def __init__(self):
        self.platforms = [
            {
                "key": "99acres",
                "name": "99acres",
                "base_url": "https://www.99acres.com",
                "domain": "99acres.com",
            },
            {
                "key": "nobroker",
                "name": "NoBroker",
                "base_url": "https://www.nobroker.in",
                "domain": "nobroker.in",
            },
            {
                "key": "housing",
                "name": "Housing.com",
                "base_url": "https://housing.com",
                "domain": "housing.com",
            },
            {
                "key": "magicbricks",
                "name": "MagicBricks",
                "base_url": "https://www.magicbricks.com",
                "domain": "magicbricks.com",
            }
        ]

    def _is_working_platform_link(self, url: str, expected_domain: str) -> bool:
        if not url:
            return False
        try:
            response = requests.get(url, timeout=4, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code >= 400:
                return False
            final_host = (urlparse(response.url).netloc or "").lower()
            return expected_domain.lower() in final_host
        except Exception:
            return False

    def _build_offer_url(self, platform: Dict, title: str, location: str, bhk: int | None) -> str:
        query_parts = [str(bhk) + " BHK" if bhk else "", title, location]
        query = " ".join(part for part in query_parts if part).strip()
        encoded_query = quote_plus(query)
        base = platform.get("base_url", "")
        domain = platform.get("domain", "")

        # Candidate direct website search URLs (no Google wrapper).
        candidates = [
            f"{base}/search?query={encoded_query}",
            f"{base}/property-for-sale?q={encoded_query}",
            f"{base}/property/sale/{encoded_query}",
            base,
        ]

        for candidate in candidates:
            if self._is_working_platform_link(candidate, domain):
                return candidate
        return ""

    def compare(self, property_data: Dict) -> Dict:
        title = property_data.get("title", "Property")
        location = property_data.get("location", "Unknown")
        base_price = float(property_data.get("price", 8000000))
        bhk = property_data.get("bhk")

        offers: List[Dict] = []

        for platform in self.platforms:
            seed = hash(f"{title}:{location}:{platform['key']}") % 10_000
            rng = random.Random(seed)

            variance = rng.uniform(-0.08, 0.08)
            price = max(500000, base_price * (1 + variance))
            total_cost = price * rng.uniform(1.0, 1.02)

            offers.append({
                "platform": platform["name"],
                "price": round(price),
                "total_cost": round(total_cost),
                "includes": rng.choice(["Registration included", "Brokerage included", "Zero brokerage", "Best deal"]),
                "match_score": round(rng.uniform(0.82, 0.98), 2),
                "url": self._build_offer_url(platform, title, location, bhk)
            })

        offers = sorted(offers, key=lambda x: x["price"])
        best_price = offers[0]["price"] if offers else base_price
        avg_price = round(sum(o["price"] for o in offers) / len(offers), 2) if offers else base_price

        return {
            "property_title": title,
            "location": location,
            "offers": offers,
            "best_price": best_price,
            "avg_price": avg_price
        }
