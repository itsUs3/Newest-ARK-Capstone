import os
import requests
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


class VastuChecker:
    """
    Vastu/Feng Shui Compliance Checker using SerpApi for real surroundings.
    
    Uses rule-based logic (no LLMs) to score properties based on:
    - Facing direction (North, South, East, West, Northeast, etc.)
    - Nearby surroundings from Google Maps (roads, parks, water, hospitals)
    - Traditional Vastu principles
    - Basic Feng Shui concepts
    
    Output: Score (0-100) + detailed explanation + remedies
    """
    
    # Vastu Scoring Rules
    FACING_SCORES = {
        'North': 20,
        'Northeast': 25,
        'East': 20,
        'Southeast': 10,
        'South': 5,
        'Southwest': 8,
        'West': 12,
        'Northwest': 15,
    }
    
    # Place type scoring for different directions
    VASTU_RULES = {
        'North': {
            'positive': ['water', 'park', 'garden', 'open_space', 'lake', 'river'],
            'negative': ['cemetery', 'graveyard', 'hospital', 't_junction'],
            'points': 10
        },
        'Northeast': {
            'positive': ['temple', 'park', 'water', 'open_space', 'garden'],
            'negative': ['toilet', 'kitchen', 'staircase', 't_junction'],
            'points': 15
        },
        'East': {
            'positive': ['park', 'garden', 'open_space', 'playground'],
            'negative': ['cemetery', 'crematorium', 't_junction', 'garbage_dump'],
            'points': 10
        },
        'Southeast': {
            'positive': ['kitchen_area', 'electrical_installations'],
            'negative': ['water', 'well', 'boring'],
            'points': 5
        },
        'South': {
            'positive': ['heavy_structure', 'warehouse', 'storage'],
            'negative': ['entrance', 'main_door', 't_junction'],
            'points': 5
        },
        'Southwest': {
            'positive': ['heavy_furniture', 'master_bedroom', 'safe'],
            'negative': ['water', 'toilet', 'entrance'],
            'points': 8
        },
        'West': {
            'positive': ['bedroom', 'study_room'],
            'negative': ['kitchen', 't_junction'],
            'points': 7
        },
        'Northwest': {
            'positive': ['guest_room', 'garage'],
            'negative': ['heavy_storage', 'master_bedroom'],
            'points': 8
        }
    }
    
    def __init__(self):
        self.serpapi_key = os.getenv('SERPAPI_KEY', '')
        self.use_serpapi = bool(self.serpapi_key)
    
    def _normalize_facing(self, facing: str) -> str:
        """Normalize facing direction to standard format."""
        if not facing:
            return 'Unknown'
        
        facing_map = {
            'N': 'North', 'NORTH': 'North',
            'NE': 'Northeast', 'NORTHEAST': 'Northeast', 'NORTH-EAST': 'Northeast',
            'E': 'East', 'EAST': 'East',
            'SE': 'Southeast', 'SOUTHEAST': 'Southeast', 'SOUTH-EAST': 'Southeast',
            'S': 'South', 'SOUTH': 'South',
            'SW': 'Southwest', 'SOUTHWEST': 'Southwest', 'SOUTH-WEST': 'Southwest',
            'W': 'West', 'WEST': 'West',
            'NW': 'Northwest', 'NORTHWEST': 'Northwest', 'NORTH-WEST': 'Northwest',
        }
        
        facing_upper = facing.upper().strip()
        return facing_map.get(facing_upper, facing.title())
    
    def _fetch_nearby_places(self, location: str, lat: float = None, lng: float = None) -> Dict:
        """
        Fetch nearby places using SerpApi Google Maps API.
        
        Args:
            location: Location name (e.g., "Andheri West, Mumbai")
            lat: Latitude (optional)
            lng: Longitude (optional)
        
        Returns:
            Dict with categorized nearby places
        """
        if not self.use_serpapi:
            # Return mock data when no API key
            return self._get_mock_surroundings(location)
        
        try:
            # Use SerpApi Google Maps API
            base_url = "https://serpapi.com/search"
            
            # Build query
            query = f"{location}" if not (lat and lng) else f"@{lat},{lng}"
            
            params = {
                'engine': 'google_maps',
                'q': query,
                'type': 'search',
                'api_key': self.serpapi_key
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract nearby places
            nearby = {
                'parks': [],
                'water': [],
                'temples': [],
                'hospitals': [],
                'roads': [],
                't_junctions': [],
                'cemeteries': [],
                'open_spaces': []
            }
            
            # Parse local results
            local_results = data.get('local_results', [])
            for place in local_results[:20]:  # Limit to 20 places
                place_type = place.get('type', '').lower()
                place_name = place.get('title', '')
                
                # Categorize based on type and name
                if any(word in place_type or word in place_name.lower() 
                       for word in ['park', 'garden', 'playground']):
                    nearby['parks'].append(place_name)
                elif any(word in place_type or word in place_name.lower() 
                         for word in ['lake', 'river', 'water', 'pond']):
                    nearby['water'].append(place_name)
                elif any(word in place_type or word in place_name.lower() 
                         for word in ['temple', 'church', 'mosque', 'gurudwara']):
                    nearby['temples'].append(place_name)
                elif any(word in place_type or word in place_name.lower() 
                         for word in ['hospital', 'clinic', 'medical']):
                    nearby['hospitals'].append(place_name)
                elif any(word in place_type or word in place_name.lower() 
                         for word in ['cemetery', 'graveyard', 'crematorium']):
                    nearby['cemeteries'].append(place_name)
            
            return nearby
        
        except Exception as e:
            print(f"SerpApi error: {e}")
            return self._get_mock_surroundings(location)
    
    def _get_mock_surroundings(self, location: str) -> Dict:
        """
        Mock surroundings data when SerpApi is unavailable.
        Uses common patterns for Indian cities.
        """
        location_lower = location.lower()
        
        # Common patterns for different areas
        mock_data = {
            'parks': [],
            'water': [],
            'temples': [],
            'hospitals': [],
            'roads': [],
            't_junctions': [],
            'cemeteries': [],
            'open_spaces': []
        }
        
        # Add some generic nearby places based on typical Indian neighborhoods
        if 'andheri' in location_lower or 'bandra' in location_lower:
            mock_data['parks'] = ['Municipal Garden', 'Children Park']
            mock_data['temples'] = ['Local Temple']
            mock_data['hospitals'] = ['Kokilaben Hospital']
            mock_data['roads'] = ['Western Express Highway', 'Link Road']
            mock_data['t_junctions'] = ['SV Road Junction']
        elif 'worli' in location_lower or 'powai' in location_lower:
            mock_data['parks'] = ['Community Garden']
            mock_data['water'] = ['Powai Lake'] if 'powai' in location_lower else []
            mock_data['hospitals'] = ['Lilavati Hospital']
            mock_data['roads'] = ['Eastern Express Highway']
        elif 'pune' in location_lower or 'hinjewadi' in location_lower or 'baner' in location_lower:
            mock_data['parks'] = ['Aundh Garden']
            mock_data['temples'] = ['Dagdusheth Temple']
            mock_data['hospitals'] = ['Ruby Hall Clinic']
            mock_data['roads'] = ['Mumbai Pune Highway']
            mock_data['open_spaces'] = ['Community Ground']
        elif 'chennai' in location_lower or 'velachery' in location_lower or 'omr' in location_lower:
            mock_data['water'] = ['Pallikaranai Marsh']
            mock_data['hospitals'] = ['Apollo Hospital']
            mock_data['roads'] = ['OMR Road']
            mock_data['t_junctions'] = ['OMR Signal Junction']
        elif 'bangalore' in location_lower or 'bengaluru' in location_lower or 'whitefield' in location_lower:
            mock_data['parks'] = ['Cubbon Park']
            mock_data['temples'] = ['ISKCON Temple']
            mock_data['hospitals'] = ['Manipal Hospital']
            mock_data['roads'] = ['Outer Ring Road']
            mock_data['open_spaces'] = ['Lake View Ground']
        elif 'hyderabad' in location_lower or 'gachibowli' in location_lower:
            mock_data['parks'] = ['KBR Park']
            mock_data['water'] = ['Durgam Cheruvu']
            mock_data['hospitals'] = ['AIG Hospital']
            mock_data['roads'] = ['Outer Ring Road Hyderabad']
        else:
            # Generic
            mock_data['parks'] = ['Nearby Park']
            mock_data['open_spaces'] = ['Open Ground']
            mock_data['roads'] = ['Main Road']
        
        return mock_data

    def _location_context_adjustment(self, location: str, surroundings: Dict, facing: str) -> Tuple[int, List[str], List[str]]:
        """Apply location-specific adjustments so same facing can yield different city/locality scores."""
        bonus = 0
        positives: List[str] = []
        negatives: List[str] = []

        location_lower = location.lower()
        roads = surroundings.get('roads', [])
        parks = surroundings.get('parks', [])
        water = surroundings.get('water', [])
        t_junctions = surroundings.get('t_junctions', [])

        if len(parks) >= 2:
            bonus += 4
            positives.append('Multiple green zones nearby (+4 points)')
        elif len(parks) == 1:
            bonus += 2
            positives.append('At least one park nearby (+2 points)')

        if water:
            bonus += 3
            positives.append('Water body proximity supports positive flow (+3 points)')

        if len(t_junctions) > 0:
            bonus -= 5
            negatives.append('Nearby major junction may disturb energy stability (-5 points)')

        # City contextual effects
        if any(x in location_lower for x in ['mumbai', 'andheri', 'bandra', 'worli']):
            bonus -= 1
            negatives.append('High-density urban pocket can increase energetic turbulence (-1 point)')
        elif any(x in location_lower for x in ['pune', 'baner', 'hinjewadi']):
            bonus += 1
            positives.append('Balanced urban layout favors residential harmony (+1 point)')
        elif any(x in location_lower for x in ['chennai', 'omr', 'velachery']):
            bonus += 1
            positives.append('Coastal airflow and broader plots support positive orientation (+1 point)')

        if facing == 'Northeast' and roads:
            bonus += 1
            positives.append('Northeast frontage with good access roads is beneficial (+1 point)')

        return bonus, positives, negatives
    
    def _calculate_vastu_score(self, facing: str, surroundings: Dict) -> Tuple[int, List[str], List[str]]:
        """
        Calculate Vastu compliance score based on facing and surroundings.
        
        Returns:
            (score, positive_factors, negative_factors)
        """
        score = 0
        positive_factors = []
        negative_factors = []
        
        # Base score from facing direction
        normalized_facing = self._normalize_facing(facing)
        base_score = self.FACING_SCORES.get(normalized_facing, 10)
        score += base_score
        positive_factors.append(f"{normalized_facing} facing property (Base: +{base_score} points)")
        
        # Check Vastu rules for the facing direction
        if normalized_facing in self.VASTU_RULES:
            rules = self.VASTU_RULES[normalized_facing]
            
            # Check positive features
            for feature in rules['positive']:
                if feature == 'water' and surroundings.get('water'):
                    score += rules['points']
                    positive_factors.append(
                        f"Water body in {normalized_facing} direction: {', '.join(surroundings['water'][:2])} (+{rules['points']} points)"
                    )
                elif feature in ['park', 'garden'] and surroundings.get('parks'):
                    score += rules['points']
                    positive_factors.append(
                        f"Green space in {normalized_facing}: {', '.join(surroundings['parks'][:2])} (+{rules['points']} points)"
                    )
                elif feature == 'temple' and surroundings.get('temples'):
                    score += rules['points']
                    positive_factors.append(
                        f"Religious place nearby: {', '.join(surroundings['temples'][:1])} (+{rules['points']} points)"
                    )
                elif feature == 'open_space' and surroundings.get('open_spaces'):
                    score += rules['points']
                    positive_factors.append(
                        f"Open space in {normalized_facing} (+{rules['points']} points)"
                    )
            
            # Check negative features
            for feature in rules['negative']:
                if feature == 't_junction' and surroundings.get('t_junctions'):
                    score -= 15
                    negative_factors.append(
                        f"T-junction in {normalized_facing} direction (-15 points) - Causes instability"
                    )
                elif feature in ['cemetery', 'graveyard', 'crematorium'] and surroundings.get('cemeteries'):
                    score -= 20
                    negative_factors.append(
                        f"Cemetery/crematorium nearby: {', '.join(surroundings['cemeteries'][:1])} (-20 points)"
                    )
                elif feature == 'hospital' and normalized_facing in ['North', 'Northeast']:
                    if surroundings.get('hospitals'):
                        score -= 10
                        negative_factors.append(
                            f"Hospital in {normalized_facing} (-10 points) - Not ideal for residential"
                        )
        
        # General positive factors
        if surroundings.get('parks') and not any('park' in str(pf).lower() for pf in positive_factors):
            score += 5
            positive_factors.append(f"Parks nearby: {', '.join(surroundings['parks'][:2])} (+5 points)")
        
        # Feng Shui consideration: Avoid clutter in South
        if normalized_facing == 'South':
            negative_factors.append("South facing - Keep entrance clutter-free (Feng Shui principle)")
        
        # Cap score between 0 and 100
        score = max(0, min(100, score))
        
        return score, positive_factors, negative_factors
    
    def _generate_remedies(self, facing: str, negative_factors: List[str], score: int) -> List[str]:
        """Generate Vastu remedies based on negative factors."""
        remedies = []
        
        if score < 40:
            remedies.append("🔮 Overall low score - Consider Vastu consultant for major renovations")
        
        for factor in negative_factors:
            if 't-junction' in factor.lower():
                remedies.append("🪞 Install convex mirror or wind chime at entrance to deflect negative energy")
                remedies.append("🌿 Plant tall trees or shrubs to block direct road impact")
            
            if 'cemetery' in factor.lower() or 'crematorium' in factor.lower():
                remedies.append("🕉️ Place religious symbols (Om, Swastik) at main entrance")
                remedies.append("💡 Keep bright lights on at entrance and corners")
            
            if 'hospital' in factor.lower():
                remedies.append("🧘 Create a meditation/prayer space to maintain positive energy")
                remedies.append("🌸 Use salt lamps or incense to purify the environment")
            
            if 'south' in factor.lower() and 'clutter' in factor.lower():
                remedies.append("🧹 Keep South area clean and organized (Feng Shui)")
                remedies.append("🔴 Use red/orange colors in South for energy balance")
        
        # General remedies for low scores
        if score < 50 and not remedies:
            remedies.append("🌱 Place indoor plants in Northeast corner for positive energy")
            remedies.append("💧 Keep water features in North or Northeast")
            remedies.append("🕯️ Light a lamp daily in Northeast corner (morning)")
        
        # Good score acknowledgment
        if score >= 70:
            remedies.append("✅ Excellent Vastu compliance - Maintain cleanliness and positive energy")
        
        return remedies
    
    def check_compliance(self, facing: str, location: str, 
                        lat: float = None, lng: float = None) -> Dict:
        """
        Main method to check Vastu/Feng Shui compliance.
        
        Args:
            facing: Property facing direction (e.g., "East", "North-East")
            location: Location name or address
            lat: Latitude (optional)
            lng: Longitude (optional)
        
        Returns:
            Dict with score, explanation, factors, and remedies
        """
        # Normalize facing
        normalized_facing = self._normalize_facing(facing)
        
        # Fetch nearby surroundings
        surroundings = self._fetch_nearby_places(location, lat, lng)
        
        # Calculate Vastu score
        score, positive_factors, negative_factors = self._calculate_vastu_score(
            normalized_facing, surroundings
        )

        # Add location-context adjustment to avoid identical scores across cities/localities
        loc_adjust, loc_positive, loc_negative = self._location_context_adjustment(
            location=location,
            surroundings=surroundings,
            facing=normalized_facing,
        )
        score = max(0, min(100, score + loc_adjust))
        positive_factors.extend(loc_positive)
        negative_factors.extend(loc_negative)
        
        # Generate remedies
        remedies = self._generate_remedies(normalized_facing, negative_factors, score)
        
        # Determine compliance level
        if score >= 70:
            level = "Excellent"
            level_emoji = "🟢"
        elif score >= 50:
            level = "Good"
            level_emoji = "🟡"
        elif score >= 30:
            level = "Fair"
            level_emoji = "🟠"
        else:
            level = "Poor"
            level_emoji = "🔴"
        
        # Generate explanation
        explanation = self._generate_explanation(
            normalized_facing, score, level, positive_factors, negative_factors
        )
        
        return {
            'score': score,
            'level': level,
            'level_emoji': level_emoji,
            'facing': normalized_facing,
            'location': location,
            'explanation': explanation,
            'positive_factors': positive_factors,
            'negative_factors': negative_factors,
            'remedies': remedies,
            'surroundings': surroundings,
            'using_serpapi': self.use_serpapi
        }
    
    def _generate_explanation(self, facing: str, score: int, level: str,
                             positive_factors: List[str], negative_factors: List[str]) -> str:
        """Generate detailed explanation of the Vastu score."""
        
        explanation = f"""🏠 Vastu/Feng Shui Compliance Report

**Property Facing**: {facing}
**Compliance Score**: {score}/100 ({level})

"""
        
        if positive_factors:
            explanation += "**✅ Positive Vastu Factors:**\n"
            for factor in positive_factors:
                explanation += f"• {factor}\n"
            explanation += "\n"
        
        if negative_factors:
            explanation += "**⚠️ Vastu Concerns:**\n"
            for factor in negative_factors:
                explanation += f"• {factor}\n"
            explanation += "\n"
        
        # Add Vastu wisdom
        if facing in ['North', 'Northeast', 'East']:
            explanation += f"**💡 Vastu Insight**: {facing} is considered auspicious in Vastu Shastra. "
            explanation += "These directions are associated with prosperity, health, and positive energy flow.\n\n"
        elif facing == 'South':
            explanation += "**💡 Vastu Insight**: South facing requires careful planning. "
            explanation += "Ensure the main entrance is not directly South-facing for best results.\n\n"
        
        # Overall verdict
        if score >= 70:
            explanation += "**🎯 Verdict**: This property shows excellent Vastu compliance! "
            explanation += "The surroundings and orientation support positive energy flow.\n"
        elif score >= 50:
            explanation += "**🎯 Verdict**: Good Vastu compliance with minor areas for improvement. "
            explanation += "Consider the suggested remedies to enhance the energy.\n"
        else:
            explanation += "**🎯 Verdict**: Moderate Vastu compliance. "
            explanation += "implementing the suggested remedies is highly recommended for better harmony.\n"
        
        return explanation
