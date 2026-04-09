"""Generate Mumbai property datasets using Firecrawl within a strict page budget.

Outputs:
1) Datasets/firecrawl_mumbai_properties.json (for map and cross-modal features)
2) Datasets/firecrawl_mumbai_housing1.csv (for recommendation engine fallback compatibility)

Usage:
  python generate_firecrawl_mumbai_dataset.py --max-pages 300
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"

KEYWORD_AMENITIES = [
    "gym",
    "pool",
    "swimming",
    "clubhouse",
    "lift",
    "elevator",
    "parking",
    "security",
    "gated",
    "garden",
    "park",
    "play area",
    "power backup",
    "internet",
    "wifi",
    "metro",
    "school",
    "hospital",
]


def _extract_bhk(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*bhk", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _extract_size_sqft(text: str) -> Optional[float]:
    patterns = [
        r"(\d{2,5}(?:,\d{3})?(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|square\s*feet)",
        r"(\d{2,5}(?:,\d{3})?(?:\.\d+)?)\s*(?:sq\.?\s*m|sqm|square\s*meter)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            value = float(m.group(1).replace(",", ""))
            if "sq" in pattern and "m" in pattern:
                return round(value * 10.7639, 2)
            return value
    return None


def _extract_price_inr(text: str) -> Optional[float]:
    m = re.search(r"₹\s*([\d,.]+)\s*(cr|crore|l|lac|lakh)?", text, flags=re.IGNORECASE)
    if not m:
        m = re.search(r"([\d,.]+)\s*(cr|crore|l|lac|lakh)", text, flags=re.IGNORECASE)
        if not m:
            return None
    value = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit in {"cr", "crore"}:
        return value * 10000000
    if unit in {"l", "lac", "lakh"}:
        return value * 100000
    return value


def _extract_amenities(text: str) -> List[str]:
    text_l = text.lower()
    hits = [a for a in KEYWORD_AMENITIES if a in text_l]
    # Normalize a few variants.
    normalized = []
    for item in hits:
        if item == "swimming":
            item = "pool"
        if item == "elevator":
            item = "lift"
        normalized.append(item)
    return sorted(set(normalized))


def _extract_images(html: str, metadata: Dict) -> List[str]:
    images: List[str] = []
    for k in ["ogImage", "twitterImage", "image"]:
        v = metadata.get(k)
        if isinstance(v, str) and v.startswith("http"):
            images.append(v)

    if html:
        srcs = re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE)
        for src in srcs:
            if src.startswith("http"):
                images.append(src)

    dedup: List[str] = []
    seen = set()
    for url in images:
        if url in seen:
            continue
        seen.add(url)
        dedup.append(url)
        if len(dedup) >= 3:
            break
    return dedup


class FirecrawlClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def map_links(self, url: str, limit: int = 100, search: str = "") -> List[str]:
        payload = {"url": url, "limit": limit}
        if search:
            payload["search"] = search
        r = self.session.post(f"{FIRECRAWL_BASE_URL}/map", json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        links = data.get("links") or data.get("data") or []
        if isinstance(links, dict):
            links = links.get("links", [])
        return [x for x in links if isinstance(x, str)]

    def scrape(self, url: str) -> Dict:
        payload = {"url": url, "formats": ["markdown", "html"]}
        r = self.session.post(f"{FIRECRAWL_BASE_URL}/scrape", json=payload, timeout=90)
        r.raise_for_status()
        data = r.json().get("data") or r.json()
        return data if isinstance(data, dict) else {}


def _seed_sources() -> List[str]:
    return [
        "https://www.housing.com/in/buy/mumbai",
        "https://www.magicbricks.com/property-for-sale/residential-real-estate?cityName=Mumbai",
        "https://www.99acres.com/property-in-mumbai-ffid",
        "https://www.nobroker.in/property/sale/mumbai/Mumbai",
    ]


def _is_mumbai_listing_url(url: str) -> bool:
    u = url.lower()
    if "mumbai" not in u:
        return False
    return any(k in u for k in ["property", "buy", "sale", "residential", "flat", "apartment", "listing"])


def _to_listing(url: str, data: Dict) -> Optional[Dict]:
    markdown = str(data.get("markdown") or "")
    html = str(data.get("html") or "")
    metadata = data.get("metadata") or {}

    title = str(metadata.get("title") or "").strip()
    description = str(metadata.get("description") or "").strip()
    text = " ".join([title, description, markdown])

    if "mumbai" not in text.lower() and "mumbai" not in url.lower():
        return None

    bhk = _extract_bhk(text)
    size_sqft = _extract_size_sqft(text)
    price_inr = _extract_price_inr(text)
    amenities = _extract_amenities(text)
    images = _extract_images(html, metadata)

    if not title:
        title = urlparse(url).path.strip("/") or "Mumbai Property"

    listing = {
        "id": f"firecrawl_{abs(hash(url))}",
        "name": title,
        "title": title,
        "description": description,
        "location": "Mumbai",
        "city": "Mumbai",
        "locality": "Mumbai",
        "source": "firecrawl",
        "source_url": url,
        "bhk": bhk,
        "size_sqft": size_sqft,
        "price_numeric": price_inr,
        "price": {
            "raw": price_inr,
            "numeric": price_inr,
            "label": f"₹{price_inr:,.0f}" if price_inr else "Price on request",
        },
        "amenities": amenities,
        "images": images,
        "latitude": None,
        "longitude": None,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
    }
    return listing


def _write_outputs(project_root: Path, listings: List[Dict]) -> None:
    datasets_dir = project_root / "Datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    json_path = datasets_dir / "firecrawl_mumbai_properties.json"
    json_path.write_text(json.dumps(listings, indent=2, ensure_ascii=True), encoding="utf-8")

    csv_path = datasets_dir / "firecrawl_mumbai_housing1.csv"
    fieldnames = [
        "title",
        "title2",
        "name",
        "location",
        "bhk",
        "size_sqft",
        "price_numeric",
        "amenities",
        "image",
        "image2",
        "image3",
        "source_url",
        "scraped_at",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in listings:
            imgs = item.get("images") or []
            bhk = item.get("bhk")
            size_sqft = item.get("size_sqft")
            writer.writerow(
                {
                    "title": item.get("title") or "Mumbai Property",
                    "title2": f"{bhk or ''} BHK in Mumbai".strip(),
                    "name": "Firecrawl",
                    "location": item.get("location") or "Mumbai",
                    "bhk": bhk,
                    "size_sqft": size_sqft,
                    "price_numeric": item.get("price_numeric"),
                    "amenities": ",".join(item.get("amenities") or []),
                    "image": imgs[0] if len(imgs) > 0 else "",
                    "image2": imgs[1] if len(imgs) > 1 else "",
                    "image3": imgs[2] if len(imgs) > 2 else "",
                    "source_url": item.get("source_url"),
                    "scraped_at": item.get("scraped_at"),
                }
            )

    print(f"Saved JSON dataset: {json_path}")
    print(f"Saved CSV dataset: {csv_path}")
    print(f"Total listings: {len(listings)}")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    load_dotenv(Path(__file__).resolve().parent / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, default="")
    parser.add_argument("--max-pages", type=int, default=300)
    parser.add_argument("--map-limit-per-source", type=int, default=120)
    parser.add_argument("--sleep-ms", type=int, default=350)
    args = parser.parse_args()

    api_key = (args.api_key or "").strip()
    if not api_key:
        api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        try:
            # Optional fallback to project config if present.
            from config import FIRECRAWL_API_KEY as CONFIG_FIRECRAWL_API_KEY  # type: ignore

            api_key = str(CONFIG_FIRECRAWL_API_KEY or "").strip()
        except Exception:
            api_key = ""

    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY is not set (env/.env/--api-key)")

    max_pages = max(1, min(300, int(args.max_pages)))
    sleep_seconds = max(0, args.sleep_ms) / 1000.0
    client = FirecrawlClient(api_key=api_key)

    candidate_links: List[str] = []
    for src in _seed_sources():
        try:
            discovered = client.map_links(
                src,
                limit=max(10, args.map_limit_per_source),
                search="mumbai apartment flat property buy sale bhk",
            )
            filtered = [u for u in discovered if _is_mumbai_listing_url(u)]
            candidate_links.extend(filtered)
            print(f"Discovered {len(filtered)} candidate links from {src}")
        except Exception as exc:
            print(f"Map failed for {src}: {exc}")

    # Deterministic dedupe preserving order.
    dedup_links: List[str] = []
    seen_links: Set[str] = set()
    for link in candidate_links:
        if link in seen_links:
            continue
        seen_links.add(link)
        dedup_links.append(link)

    links_to_scrape = dedup_links[:max_pages]
    print(f"Scraping {len(links_to_scrape)} pages (cap={max_pages})")

    listings: List[Dict] = []
    seen_listing_keys: Set[str] = set()

    for i, link in enumerate(links_to_scrape, start=1):
        try:
            data = client.scrape(link)
            listing = _to_listing(link, data)
            if not listing:
                continue
            dedupe_key = "|".join(
                [
                    str(listing.get("title", "")).strip().lower(),
                    str(listing.get("price_numeric") or ""),
                    str(listing.get("source_url", "")),
                ]
            )
            if dedupe_key in seen_listing_keys:
                continue
            seen_listing_keys.add(dedupe_key)
            listings.append(listing)
            if i % 20 == 0:
                print(f"Processed {i}/{len(links_to_scrape)} pages, listings={len(listings)}")
        except Exception as exc:
            print(f"Scrape failed [{i}/{len(links_to_scrape)}] {link}: {exc}")
        time.sleep(sleep_seconds)

    _write_outputs(project_root, listings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
