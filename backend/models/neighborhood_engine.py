import os
import json
from typing import List, Dict, Optional
from .genai_handler import GenAIHandler


class NeighborhoodEngine:
    """
    Parses landmark_details from MagicBricks dataset and generates
    AI-style neighborhood reports for Indian real estate properties.

    Landmark codes observed in the dataset:
      19201 - Supermarkets / General Stores
      19202 - Schools & Education
      19203 - Hospitals & Healthcare
      19204 - Banks & ATMs
      19205 - Restaurants & Food
      19206 - Malls & Shopping Centers
      19207 - Parks & Recreation
      19208 - Religious Places
      19209 - Hotels & Hospitality
      19210 - Transit (Metro / Bus Stops)
      19211 - Petrol Stations
      19212 - Gyms & Fitness
    """

    LANDMARK_CATEGORIES = {
        "19201": {"name": "Supermarkets & Stores",   "icon": "🛒"},
        "19202": {"name": "Schools & Education",      "icon": "🏫"},
        "19203": {"name": "Hospitals & Healthcare",   "icon": "🏥"},
        "19204": {"name": "Banks & ATMs",             "icon": "🏦"},
        "19205": {"name": "Restaurants & Food",       "icon": "🍽️"},
        "19206": {"name": "Malls & Shopping",         "icon": "🏬"},
        "19207": {"name": "Parks & Recreation",       "icon": "🌳"},
        "19208": {"name": "Religious Places",         "icon": "🕌"},
        "19209": {"name": "Hotels & Hospitality",     "icon": "🏨"},
        "19210": {"name": "Transit & Connectivity",   "icon": "🚇"},
        "19211": {"name": "Petrol Stations",          "icon": "⛽"},
        "19212": {"name": "Gyms & Fitness",           "icon": "💪"},
    }

    # Dataset filename (relative to the Datasets/ folder)
    DATASET_FILE = "dataset_magicbricks-property-search-scraper_2026-02-16_14-32-19-208.json"

    def __init__(self):
        self.data: List[dict] = []
        self.genai_handler = GenAIHandler()
        self._load_data()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self):
        """Load MagicBricks JSON dataset from disk."""
        # backend/models/neighborhood_engine.py  →  go up two levels to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dataset_path = os.path.join(base_dir, "Datasets", self.DATASET_FILE)

        if not os.path.exists(dataset_path):
            # Fallback: search CWD-relative path (useful when running from backend/)
            cwd_path = os.path.join("..", "Datasets", self.DATASET_FILE)
            if os.path.exists(cwd_path):
                dataset_path = cwd_path
            else:
                # Gracefully continue with empty data
                return

        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = []

    # ------------------------------------------------------------------
    # Landmark parsing helpers
    # ------------------------------------------------------------------

    def _parse_landmarks(self, landmark_list: Optional[List]) -> Dict[str, List[str]]:
        """Parse a list of 'CODE|Name' strings into {code: [names]} dict."""
        categorized: Dict[str, List[str]] = {}
        for item in (landmark_list or []):
            text = str(item)
            if "|" in text:
                code, name = text.split("|", 1)
                code = code.strip()
                name = name.strip()
                if code not in categorized:
                    categorized[code] = []
                categorized[code].append(name)
        return categorized

    def _find_properties_for_location(self, location: str) -> List[dict]:
        """Return all dataset entries whose address/city matches the queried location."""
        query = location.lower().replace(" ", "")
        # Use only the first segment before a comma for fuzzy matching
        query_short = query.split(",")[0]

        matched = []
        for prop in self.data:
            address = str(prop.get("address", "")).lower().replace(" ", "")
            city    = str(prop.get("city_name", "")).lower().replace(" ", "")
            name    = str(prop.get("name", "")).lower().replace(" ", "")

            if (query_short in address or query_short in city
                    or query in address  or query in city
                    or query_short in name):
                matched.append(prop)

        return matched

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(self, location: str) -> Dict:
        """
        Generate a structured neighborhood report for a given location.
        Now includes GenAI-powered insights for family suitability, connectivity,
        commute estimates, and lifestyle matching.

        Returns a dict with:
          - location            : queried location string
          - properties_analyzed : number of dataset rows matched
          - landmark_categories : categorized landmark dict
          - report              : narrative text
          - suitability_tags    : list of suitability labels
          - genai_insights      : GenAI-powered analysis with scores and commute data
        """
        matched_props = self._find_properties_for_location(location)

        # Aggregate landmarks across all matched properties
        aggregated: Dict[str, set] = {}
        for prop in matched_props:
            parsed = self._parse_landmarks(prop.get("landmark_details", []))
            for code, names in parsed.items():
                if code not in aggregated:
                    aggregated[code] = set()
                aggregated[code].update(names)

        # Build categorized display (max 6 places per category)
        landmark_categories: Dict = {}
        for code, names in aggregated.items():
            cat = self.LANDMARK_CATEGORIES.get(
                code, {"name": f"Other (Code {code})", "icon": "📍"}
            )
            cat_name = cat["name"]
            if cat_name not in landmark_categories:
                landmark_categories[cat_name] = {"icon": cat["icon"], "places": []}
            landmark_categories[cat_name]["places"].extend(list(names)[:6])

        suitability_tags = self._compute_suitability(landmark_categories)

        report_text = (
            self._generate_narrative(location, landmark_categories, len(matched_props))
            if matched_props
            else self._generate_fallback_report(location)
        )

        # Generate GenAI-powered insights (family score, connectivity, commute estimates, etc.)
        genai_insights = self.genai_handler.generate_landmark_insights(
            location=location,
            landmark_categories=landmark_categories,
            properties_count=len(matched_props)
        )

        return {
            "location": location,
            "properties_analyzed": len(matched_props),
            "landmark_categories": landmark_categories,
            "report": report_text,
            "suitability_tags": suitability_tags,
            "genai_insights": genai_insights,
        }

    # ------------------------------------------------------------------
    # Report generation helpers
    # ------------------------------------------------------------------

    def _generate_narrative(
        self, location: str, categories: Dict, num_properties: int
    ) -> str:
        """Compose a human-readable narrative from categorised landmark data."""
        schools   = categories.get("Schools & Education",    {}).get("places", [])
        hospitals = categories.get("Hospitals & Healthcare", {}).get("places", [])
        malls     = categories.get("Malls & Shopping",       {}).get("places", [])
        transit   = categories.get("Transit & Connectivity", {}).get("places", [])
        stores    = categories.get("Supermarkets & Stores",  {}).get("places", [])

        paras = [f"Neighborhood Report — {location}", ""]

        if schools:
            names = ", ".join(schools[:2])
            paras.append(
                f"Education: {names} are in close proximity, making this area an excellent choice for families with school-going children."
            )

        if hospitals:
            names = ", ".join(hospitals[:2])
            paras.append(
                f"Healthcare: {names} ensure reliable medical support is never far away."
            )

        if transit:
            names = ", ".join(transit[:3])
            paras.append(
                f"Connectivity: {names} provide seamless public transport links across the city and beyond."
            )

        if malls:
            names = ", ".join(malls[:2])
            paras.append(
                f"Shopping & Lifestyle: {names} offer premium retail, dining, and entertainment options close by."
            )

        if stores:
            names = ", ".join(stores[:2])
            paras.append(
                f"Daily Needs: {names} keep everyday grocery and household shopping convenient."
            )

        tags = self._compute_suitability(categories)
        paras.append("")
        paras.append(f"Verdict: Ideal for {', '.join(tags).lower()} residents.")
        paras.append(
            f"(Data aggregated from {num_properties} property listing(s) in this area.)"
        )

        return "\n".join(paras)

    def _generate_fallback_report(self, location: str) -> str:
        """Fallback report when the queried location has no dataset coverage."""
        return (
            f"Neighborhood Report — {location}\n\n"
            f"Based on general knowledge of {location}:\n\n"
            "This area typically offers good access to essential urban services, "
            "including schools, hospitals, local markets, and public transport. "
            "Properties here benefit from established residential infrastructure.\n\n"
            "Connectivity: Regular bus routes and auto-rickshaw services connect the locality to major hubs.\n"
            "Education: Multiple schools and coaching centres within a short distance.\n"
            "Healthcare: Clinics and hospitals reachable within the area.\n"
            "Shopping: Local markets and supermarkets cater to daily requirements.\n\n"
            "Note: Precise landmark data for this location is not yet in our dataset. "
            "The report above is based on general area knowledge. Try nearby areas like "
            f"Central {location.split()[0]} or a pin-code-level search for richer results."
        )

    def _compute_suitability(self, categories: Dict) -> List[str]:
        """Derive suitability tags from available landmark categories."""
        tags = []
        if categories.get("Schools & Education", {}).get("places"):
            tags.append("Family-Friendly")
        if categories.get("Transit & Connectivity", {}).get("places"):
            tags.append("Well-Connected")
        if categories.get("Hospitals & Healthcare", {}).get("places"):
            tags.append("Healthcare Access")
        if categories.get("Malls & Shopping", {}).get("places"):
            tags.append("Lifestyle Hub")
        if categories.get("Supermarkets & Stores", {}).get("places"):
            tags.append("Convenient Daily Needs")
        if not tags:
            tags.append("Residential Area")
        return tags
