"""
Utility modules for data processing and helpers
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import re
from config import DATA_PATH

class DataProcessor:
    """Handle data loading, processing, and storage"""
    
    def __init__(self):
        self.data_file = str(DATA_PATH)
        self.processed_listings = None
    
    def process_listings(self, df: pd.DataFrame) -> List[Dict]:
        """
        Process raw housing data into structured format
        """
        try:
            listings = []
            
            for idx, row in df.iterrows():
                title2 = str(row.get('title2', ''))
                
                # Extract location
                location_match = re.search(r'in\s+([^,]+)', title2)
                location = location_match.group(1) if location_match else 'Unknown'
                
                # Extract BHK
                bhk_match = re.search(r'(\d+)\s*BHK', title2)
                bhk = int(bhk_match.group(1)) if bhk_match else 0
                
                listing = {
                    'id': f"h1_{idx}",
                    'title': row.get('title', 'Property'),
                    'full_description': title2,
                    'location': location.strip(),
                    'bhk': bhk,
                    'developer': row.get('name', 'Unknown'),
                    'possession': row.get('data8', 'N/A'),
                    'property_type': row.get('data14', 'Flat'),
                    'images': [
                        url for url in [row.get('image'), row.get('image2'), row.get('image3')]
                        if pd.notna(url)
                    ],
                    'source': 'Housing.com',
                    'scraped_date': '2026-02-03'
                }
                
                if bhk > 0:  # Only include valid entries
                    listings.append(listing)
            
            self.processed_listings = listings
            return listings
        
        except Exception as e:
            print(f"Error processing listings: {e}")
            return []
    
    def get_listings(self, location: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get processed listings with optional filter"""
        if self.processed_listings is None:
            try:
                df = pd.read_csv(self.data_file)
                self.processed_listings = self.process_listings(df)
            except:
                return []
        
        listings = self.processed_listings
        
        if location:
            listings = [l for l in listings if location.lower() in l['location'].lower()]
        
        return listings[:limit]
    
    def get_unique_locations(self) -> List[str]:
        """Get all unique locations"""
        if self.processed_listings is None:
            try:
                df = pd.read_csv(self.data_file)
                self.processed_listings = self.process_listings(df)
            except:
                return []
        
        locations = sorted(list(set([l['location'] for l in self.processed_listings])))
        return locations
    
    def get_statistics(self) -> Dict:
        """Get data statistics"""
        if self.processed_listings is None:
            try:
                df = pd.read_csv(self.data_file)
                self.processed_listings = self.process_listings(df)
            except:
                return {}
        
        if not self.processed_listings:
            return {}
        
        locations = [l['location'] for l in self.processed_listings]
        bhks = [l['bhk'] for l in self.processed_listings]
        
        return {
            'total_listings': len(self.processed_listings),
            'unique_locations': len(set(locations)),
            'locations': dict(pd.Series(locations).value_counts()),
            'bhk_distribution': dict(pd.Series(bhks).value_counts()),
            'property_types': dict(pd.Series([l['property_type'] for l in self.processed_listings]).value_counts())
        }
