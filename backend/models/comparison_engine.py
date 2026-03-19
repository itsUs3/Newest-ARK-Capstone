import random
from typing import Dict, List

class ComparisonEngine:
    """
    Mock price comparison engine for cross-platform offers
    """

    def __init__(self):
        self.platforms = [
            {
                "key": "99acres",
                "name": "99acres",
                "base_url": "https://www.99acres.com"
            },
            {
                "key": "nobroker",
                "name": "NoBroker",
                "base_url": "https://www.nobroker.in"
            },
            {
                "key": "housing",
                "name": "Housing.com",
                "base_url": "https://housing.com"
            },
            {
                "key": "magicbricks",
                "name": "MagicBricks",
                "base_url": "https://www.magicbricks.com"
            }
        ]

    def compare(self, property_data: Dict) -> Dict:
        title = property_data.get("title", "Property")
        location = property_data.get("location", "Unknown")
        base_price = float(property_data.get("price", 8000000))

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
                "url": f"{platform['base_url']}/search?query={title.replace(' ', '+')}"
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
