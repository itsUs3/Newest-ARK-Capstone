import numpy as np
import pandas as pd
from typing import Dict, List
from difflib import SequenceMatcher
from config import DATA_PATH
from pathlib import Path

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
            frames = []
            if Path(DATA_PATH).exists():
                frames.append(pd.read_csv(DATA_PATH))

            firecrawl_csv = Path(DATA_PATH).parent / "Datasets" / "firecrawl_mumbai_housing1.csv"
            if firecrawl_csv.exists():
                frames.append(pd.read_csv(firecrawl_csv))

            if not frames:
                return self._get_default_listings()

            df = pd.concat(frames, ignore_index=True)
            listings = []
            
            for idx, row in df.iterrows():
                # Extract data from web scraper columns
                title = row.get('title2', 'Unknown Property')
                location = str(title).split('in ')[-1] if 'in' in str(title) else 'Mumbai'
                bhk = self._extract_bhk(str(title))
                if pd.notna(row.get('bhk')):
                    try:
                        bhk = int(row.get('bhk'))
                    except Exception:
                        pass

                size_val = np.random.uniform(400, 2500)
                if pd.notna(row.get('size_sqft')):
                    try:
                        size_val = float(row.get('size_sqft'))
                    except Exception:
                        pass

                price_val = np.random.uniform(30, 500) * 100000
                if pd.notna(row.get('price_numeric')):
                    try:
                        price_val = float(row.get('price_numeric'))
                    except Exception:
                        pass

                amenity_text = str(row.get('amenities', ''))
                parsed_amenities = [a.strip().lower() for a in amenity_text.split(',') if a.strip() and a.strip().lower() != 'nan']

                raw_images = [row.get('image'), row.get('image2'), row.get('image3')]
                cleaned_images = self._normalize_images(raw_images, title, location, idx)
                
                listing = {
                    'id': f"property_{idx}",
                    'title': row.get('title', 'Property'),
                    'description': title,
                    'location': location,
                    'bhk': bhk,
                    'size': size_val,
                    'price': price_val,
                    'seller': row.get('name', 'Developer'),
                    'source': 'firecrawl' if str(row.get('name', '')).strip().lower() == 'firecrawl' else 'dataset',
                    'amenities': parsed_amenities or self._extract_amenities(str(title)),
                    'images': cleaned_images,
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

    def _normalize_images(self, images: List, title: str, location: str, seed: int) -> List[str]:
        blocked = (
            'logo', 'icon', 'svg', 'sprite', 'featuredagent', 'fallback', 'nophotos', 'placeholder',
            'badge', 'banner', 'logo.', 'logo-', 'thumbicon'
        )
        cleaned = []
        for image in images:
            if not isinstance(image, str):
                continue
            image = image.strip()
            if not image or image.lower() == 'nan':
                continue
            lower = image.lower()
            if any(token in lower for token in blocked):
                continue
            if not lower.startswith('http'):
                continue
            cleaned.append(image)

        # Keep only verified unique images. Do not invent placeholders.
        deduped = []
        seen = set()
        for image in cleaned:
            if image in seen:
                continue
            seen.add(image)
            deduped.append(image)
        return deduped
    
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
            listing_price = float(listing.get('price', 0) or 0)

            # Strict budget filtering for search expectations
            if listing_price < budget_min or listing_price > budget_max:
                continue

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
            budget_match = 100
            reasons.append("Within budget")
            score += budget_match * 0.4
            
            # Location match (25% weight)
            if location_query and location_query != 'all' and location_query in listing['location'].lower():
                score += 100 * 0.25
                reasons.append("Exact location match")
            else:
                score += 50 * 0.25
            
            # BHK match (20% weight)
            if enforce_bhk:
                if listing['bhk'] == enforce_bhk:
                    score += 100 * 0.2
                    reasons.append(f"{enforce_bhk} BHK as requested")
                elif abs(listing['bhk'] - enforce_bhk) == 1:
                    score += 70 * 0.2
                else:
                    score += 30 * 0.2
            else:
                score += 50 * 0.2
            
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

        # Keep Search results representative when Firecrawl Mumbai dataset is available.
        if location_query == 'mumbai':
            top_window = scored_listings[:15]
            firecrawl_in_top = [x for x in top_window if x.get('source') == 'firecrawl']
            if not firecrawl_in_top:
                firecrawl_pool = [x for x in scored_listings if x.get('source') == 'firecrawl'][:5]
                if firecrawl_pool:
                    non_firecrawl = [x for x in scored_listings if x.get('source') != 'firecrawl']
                    scored_listings = firecrawl_pool + non_firecrawl
        
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
