import numpy as np
import pandas as pd
from typing import Dict, List
from difflib import SequenceMatcher
from config import DATA_PATH

class RecommendationEngine:
    """
    Content-based recommendation system
    Matches user preferences with properties
    """
    
    def __init__(self):
        self.listings = self._load_sample_listings()
    
    def _load_sample_listings(self) -> List[Dict]:
        """Load sample listings from Housing1.csv"""
        try:
            df = pd.read_csv(DATA_PATH)
            listings = []
            
            for idx, row in df.iterrows():
                # Extract data from web scraper columns
                title = row.get('title2', 'Unknown Property')
                location = str(title).split('in ')[-1] if 'in' in str(title) else 'Mumbai'
                bhk = self._extract_bhk(str(title))
                
                listing = {
                    'id': f"property_{idx}",
                    'title': row.get('title', 'Property'),
                    'description': title,
                    'location': location,
                    'bhk': bhk,
                    'size': np.random.uniform(400, 2500),
                    'price': np.random.uniform(30, 500) * 100000,  # 30L to 500L
                    'seller': row.get('name', 'Developer'),
                    'amenities': self._extract_amenities(str(title)),
                    'images': [url for url in [row.get('image'), row.get('image2'), row.get('image3')] if pd.notna(url)],
                    'rating': np.random.uniform(3.5, 5.0),
                    'views': np.random.randint(100, 5000),
                    'posted_date': '2026-02-03'
                }
                listings.append(listing)
            
            return listings if listings else self._get_default_listings()
        except Exception as e:
            print(f"Error loading listings: {e}")
            return self._get_default_listings()
    
    def _extract_bhk(self, text: str) -> int:
        """Extract BHK count from text"""
        if '3 BHK' in text:
            return 3
        elif '2 BHK' in text:
            return 2
        elif '1 BHK' in text:
            return 1
        return 2  # Default
    
    def _extract_amenities(self, text: str) -> List[str]:
        """Extract amenities from description"""
        amenities = []
        amenity_keywords = {
            'gym': ['gym', 'fitness'],
            'pool': ['swimming', 'pool'],
            'parking': ['parking', 'garage'],
            'garden': ['garden', 'landscaped'],
            'security': ['24/7 security', 'gated'],
            'lift': ['elevator', 'lift'],
            'playground': ['playground', 'play area'],
            'clubhouse': ['clubhouse', 'club']
        }
        
        text_lower = text.lower()
        for amenity, keywords in amenity_keywords.items():
            if any(kw in text_lower for kw in keywords):
                amenities.append(amenity)
        
        return amenities if amenities else ['basic']
    
    def _get_default_listings(self) -> List[Dict]:
        """Return default listings if data loading fails"""
        locations = ['Mumbai', 'Bangalore', 'Delhi', 'Pune', 'Hyderabad']
        amenities_pool = [
            ['gym', 'pool', 'parking'],
            ['parking', 'garden'],
            ['gym', 'security'],
            ['pool', 'clubhouse'],
            ['parking', 'lift']
        ]
        
        listings = []
        for i in range(20):
            listings.append({
                'id': f'property_{i}',
                'title': f'Premium {(i%3)+1} BHK Property {i}',
                'description': f'Beautiful {(i%3)+1} BHK apartment in {locations[i%5]}',
                'location': locations[i % 5],
                'bhk': (i % 3) + 1,
                'size': np.random.uniform(600, 2000),
                'price': np.random.uniform(30, 500) * 100000,
                'seller': f'Builder {i%5}',
                'amenities': amenities_pool[i % len(amenities_pool)],
                'images': [],
                'rating': np.random.uniform(3.5, 5.0),
                'views': np.random.randint(100, 5000),
                'posted_date': '2026-02-03'
            })
        return listings
    
    def get_recommendations(self, preferences: Dict) -> List[Dict]:
        """
        Get personalized recommendations based on user preferences
        
        Args:
            preferences: Dict with 'budget_min', 'budget_max', 'location', 'bhk', 'amenities'
        
        Returns:
            List of recommended properties sorted by match score
        """
        budget_min = preferences.get('budget_min', 0)
        budget_max = preferences.get('budget_max', float('inf'))
        location = preferences.get('location', '')
        bhk = preferences.get('bhk', 0)
        amenities = preferences.get('amenities', [])
        location_query = str(location or '').strip().lower()
        enforce_bhk = int(bhk) if bhk not in [None, '', 0] else 0
        
        scored_listings = []
        
        for listing in self.listings:
            # Strict location filtering for search expectations
            if location_query and location_query != 'all':
                if location_query not in str(listing['location']).lower():
                    continue

            # Strict BHK filtering (4 means 4+)
            if enforce_bhk:
                listing_bhk = int(listing.get('bhk', 0) or 0)
                if enforce_bhk >= 4:
                    if listing_bhk < 4:
                        continue
                elif listing_bhk != enforce_bhk:
                    continue

            score = 100
            reasons = []
            
            # Budget match (40% weight)
            if budget_min <= listing['price'] <= budget_max:
                budget_match = 100
                reasons.append("Within budget")
            else:
                distance = min(
                    abs(listing['price'] - budget_min) if listing['price'] < budget_min else 0,
                    abs(listing['price'] - budget_max) if listing['price'] > budget_max else 0
                )
                budget_match = max(0, 100 - (distance / max(budget_max, 1000000)) * 50)
                reasons.append(f"Price slightly {'above' if listing['price'] > budget_max else 'below'} budget")
            
            score += budget_match * 0.4
            
            # Location match (25% weight)
            if location_query and location_query in listing['location'].lower():
                score += 100 * 0.25
                reasons.append("Exact location match")
            else:
                score += 40 * 0.25  # Partial credit
            
            # BHK match (20% weight)
            if listing['bhk'] == bhk:
                score += 100 * 0.2
                reasons.append(f"{bhk} BHK as requested")
            elif abs(listing['bhk'] - bhk) == 1:
                score += 70 * 0.2
            else:
                score += 30 * 0.2
            
            # Amenities match (15% weight)
            if amenities:
                matching_amenities = len(set(listing['amenities']) & set(amenities))
                amenity_match = (matching_amenities / len(amenities)) * 100
                score += amenity_match * 0.15
                reasons.append(f"{matching_amenities}/{len(amenities)} amenities match")
            else:
                score += 50 * 0.15
            
            # Add listing rating as tiebreaker
            score += listing['rating'] * 2
            
            scored_listings.append({
                **listing,
                'match_score': min(100, score),
                'match_reasons': reasons
            })
        
        # Sort by match score descending
        scored_listings.sort(key=lambda x: x['match_score'], reverse=True)
        
        return scored_listings
    
    def get_trending(self) -> List[Dict]:
        """Get trending properties (highest views/ratings)"""
        trending = sorted(
            self.listings,
            key=lambda x: (x['views'] * 0.6 + x['rating'] * 100 * 0.4),
            reverse=True
        )[:10]
        
        return trending
    
    def get_similar_properties(self, property_id: str, count: int = 5) -> List[Dict]:
        """Get properties similar to a given property"""
        # Find the property
        target = None
        for listing in self.listings:
            if listing['id'] == property_id:
                target = listing
                break
        
        if not target:
            return []
        
        # Score similarity
        similar = []
        for listing in self.listings:
            if listing['id'] == property_id:
                continue
            
            similarity = 0
            # Location similarity
            if listing['location'].lower() == target['location'].lower():
                similarity += 30
            
            # BHK similarity
            if listing['bhk'] == target['bhk']:
                similarity += 25
            elif abs(listing['bhk'] - target['bhk']) == 1:
                similarity += 15
            
            # Price similarity (within 20%)
            price_diff = abs(listing['price'] - target['price']) / target['price']
            if price_diff < 0.2:
                similarity += 25
            
            # Amenities overlap
            overlap = len(set(listing['amenities']) & set(target['amenities']))
            similarity += overlap * 5
            
            similar.append({**listing, 'similarity_score': similarity})
        
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar[:count]
