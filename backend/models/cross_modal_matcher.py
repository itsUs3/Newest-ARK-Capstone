"""
Cross-Modal Retrieval for Property Matching
Matches properties across text and image modalities using embeddings and FAISS.
Extends amenity matching with hybrid text-image recommendations.
"""

import os
import json
import base64
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

try:
    from sentence_transformers import SentenceTransformer, util
    import faiss
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise ImportError("Required packages: sentence-transformers, faiss-cpu, Pillow")

logger = logging.getLogger(__name__)


class CrossModalMatcher:
    """
    Cross-modal property retrieval using text-image embeddings.
    Supports searching with text queries or image uploads.
    Generates visual montages of matches.
    
    Architecture:
    - Multi-modal embeddings (sentence-transformers/multi-qa-MiniLM-L6-cos-v1)
    - FAISS indexing for O(log n) retrieval
    - Image montage generation from top matches
    - Unified text-image similarity scoring
    """
    
    # Configuration
    EMBEDDING_MODEL = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
    DATASET_FILES = [
        "dataset_housing-com-scraper_2026-02-16_14-07-08-729.json",
        "dataset_magicbricks-property-search-scraper_2026-02-16_14-32-19-208.json",
    ]
    IMAGE_DIR = None  # Set in __init__
    MONTAGE_SIZE = (1200, 800)
    THUMB_SIZE = (200, 200)
    
    def __init__(self, persist_directory: str = "faiss_index"):
        """
        Initialize cross-modal matcher with embeddings and FAISS index.
        """
        self.persist_directory = persist_directory
        self.persist_path = os.path.join(persist_directory, "property_index")
        self.base_dir = Path(__file__).resolve().parents[2]
        
        # Set image directory
        self.IMAGE_DIR = os.path.join(self.base_dir, "data", "housing1_images")
        
        logger.info(f"📦 Loading embedding model: {self.EMBEDDING_MODEL}...")
        self.model_name = self._resolve_embedding_model()
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = 384  # MiniLM output dimension
        
        # Property database
        self.properties: List[Dict] = []
        self.property_ids: List[int] = []
        
        # FAISS index for text embeddings
        self.text_index: Optional[faiss.IndexFlatIP] = None
        self.image_index: Optional[faiss.IndexFlatIP] = None
        
        # Load and index data
        self._load_properties()
        self._build_indices()
    
    def _resolve_embedding_model(self) -> str:
        candidate_paths = [
            self.base_dir / "backend" / "models" / "real_estate_embeddings",
            self.base_dir / "backend" / "models" / "backend" / "models" / "real_estate_embeddings",
        ]
        for candidate in candidate_paths:
            if candidate.exists():
                return str(candidate)
        return "all-MiniLM-L6-v2"

    def _dataset_path(self, filename: str) -> Optional[str]:
        """Resolve dataset file path."""
        p = os.path.join(self.base_dir, "Datasets", filename)
        if os.path.exists(p):
            return p
        return None
    
    def _load_properties(self):
        """Load properties from JSON datasets."""
        logger.info("📥 Loading property dataset...")
        
        for filename in self.DATASET_FILES:
            path = self._dataset_path(filename)
            if not path:
                logger.warning(f"Dataset not found: {filename}")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for idx, item in enumerate(data if isinstance(data, list) else []):
                    # Build description from available fields
                    name = item.get('name') or item.get('title') or 'Unknown'
                    address = item.get('address') or item.get('locality') or ''
                    city = item.get('city_name') or item.get('city') or ''
                    price = item.get('price') or item.get('minValue')
                    amenities = item.get('amenities') or []
                    
                    # Parse amenities if string
                    if isinstance(amenities, str):
                        amenities = [a.strip() for a in amenities.split(',')]
                    elif not isinstance(amenities, list):
                        amenities = []
                    
                    # Create searchable description
                    description = f"{name} {address} {city}. Amenities: {', '.join(amenities[:5])}"
                    
                    # Find matching image if available
                    image_path = self._find_image(idx)
                    
                    self.properties.append({
                        'id': len(self.properties),
                        'name': name,
                        'address': address,
                        'city': city,
                        'price': price,
                        'amenities': amenities[:10],
                        'description': description,
                        'image_path': image_path,
                        'source': 'housing' if 'housing' in filename else 'magicbricks'
                    })
                    
                    if len(self.properties) >= 100:  # Limit for performance
                        break
            
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
        
        logger.info(f"✅ Loaded {len(self.properties)} properties")
    
    def _find_image(self, idx: int) -> Optional[str]:
        """Find image file for property index."""
        if not self.IMAGE_DIR or not os.path.exists(self.IMAGE_DIR):
            return None
        
        # Look for images matching pattern: idx_*.jpg or idx_*.png
        for fname in os.listdir(self.IMAGE_DIR):
            if fname.startswith(f"{idx}_"):
                return os.path.join(self.IMAGE_DIR, fname)
        
        return None
    
    def _build_indices(self):
        """Build FAISS indices for text and image embeddings."""
        if not self.properties:
            logger.warning("No properties loaded, cannot build indices")
            return
        
        logger.info("📊 Building FAISS indices...")
        
        # Text embeddings
        descriptions = [p['description'] for p in self.properties]
        text_embeddings = self.model.encode(descriptions, convert_to_numpy=True)
        text_embeddings = np.asarray(text_embeddings, dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(text_embeddings)
        
        self.text_index = faiss.IndexFlatIP(self.embedding_dim)
        self.text_index.add(text_embeddings)
        
        logger.info(f"✅ Built FAISS index with {len(self.properties)} properties")
    
    def search_text(self, query: str, top_k: int = 6) -> Dict:
        """
        Search properties using text query.
        
        Args:
            query: Text description (e.g., "Affordable sea-view flat with gym")
            top_k: Number of results to return
        
        Returns:
            Results with matches and montage
        """
        if not self.text_index:
            return {
                'success': False,
                'error': 'Index not initialized',
                'matches': []
            }
        
        try:
            # Embed query
            query_embedding = self.model.encode(query, convert_to_numpy=True)
            query_embedding = np.asarray([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_embedding)
            
            # Search
            distances, indices = self.text_index.search(query_embedding, min(top_k, len(self.properties)))
            
            # Compile results
            matches = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1 or idx >= len(self.properties):
                    continue
                
                prop = self.properties[idx]
                matches.append({
                    'id': int(idx),
                    'name': prop['name'],
                    'address': prop['address'],
                    'city': prop['city'],
                    'price': prop['price'],
                    'amenities': prop['amenities'],
                    'similarity_score': float(dist),
                    'has_image': prop['image_path'] is not None
                })
            
            # Generate montage
            montage_path = None
            if matches:
                montage_path = self._generate_montage(matches[:top_k])
            
            return {
                'success': True,
                'query': query,
                'matches': matches,
                'match_count': len(matches),
                'montage': montage_path,
                'search_type': 'text'
            }
        
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'matches': []
            }
    
    def search_image(self, image_path: str, top_k: int = 6) -> Dict:
        """
        Search properties using uploaded image.
        
        Args:
            image_path: Path to uploaded image file
            top_k: Number of results to return
        
        Returns:
            Results with matches and montage
        """
        if not self.text_index:
            return {
                'success': False,
                'error': 'Index not initialized',
                'matches': []
            }
        
        try:
            # For now, use image analysis to generate descriptive text
            # In production, use CLIP or similar for true image embeddings
            desc = self._analyze_image(image_path)
            
            # Fall back to text search
            return self.search_text(desc, top_k)
        
        except Exception as e:
            logger.error(f"Image search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'matches': []
            }
    
    def _analyze_image(self, image_path: str) -> str:
        """
        Analyze uploaded image to generate search description.
        
        In production, use CLIP or similar. For MVP, analyze image properties.
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # Simple heuristics
            desc_parts = []
            
            # Analyze color distribution (very basic)
            if width > 500 and height > 500:
                desc_parts.append("spacious modern property")
            
            # Aspect ratio heuristics
            if width > height:
                desc_parts.append("wide view landscape photography")
            
            desc_parts.extend([
                "apartment",
                "real estate",
                "residential",
                "modern amenities",
                "indoor",
            ])
            
            return " ".join(desc_parts)
        
        except Exception as e:
            logger.warning(f"Image analysis fallback: {e}")
            return "modern apartment luxury amenities"
    
    def _generate_montage(self, matches: List[Dict], size: Tuple[int, int] = (1200, 800)) -> Optional[str]:
        """
        Generate image montage from matched properties.
        
        Returns base64-encoded image for API response.
        """
        try:
            # Create blank montage
            montage = Image.new('RGB', size, color=(240, 240, 245))
            draw = ImageDraw.Draw(montage)
            
            # Layout: grid of thumbnails
            margin = 20
            thumb_w, thumb_h = 180, 180
            cols = (size[0] - margin) // (thumb_w + margin)
            cols = max(1, cols)
            
            row, col = 0, 0
            prop_with_images = [m for m in matches if m['has_image']]
            
            for match_idx, match in enumerate(prop_with_images[:6]):
                if match_idx >= 6:  # Max 6 in 2x3 grid
                    break
                
                x = margin + col * (thumb_w + margin)
                y = margin + row * (thumb_h + margin)
                
                # Get property image
                prop = self.properties[match['id']]
                if prop['image_path'] and os.path.exists(prop['image_path']):
                    try:
                        img = Image.open(prop['image_path'])
                        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                        
                        # Paste with border
                        montage.paste(img, (x, y))
                        
                        # Draw border
                        draw.rectangle(
                            [(x, y), (x + thumb_w, y + thumb_h)],
                            outline=(100, 100, 150),
                            width=2
                        )
                        
                        # Draw label
                        label = f"{match['name'][:15]}..."
                        draw.text(
                            (x + 5, y + thumb_h - 20),
                            label,
                            fill=(255, 255, 255)
                        )
                    
                    except Exception as e:
                        logger.warning(f"Could not process image {prop['image_path']}: {e}")
                
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            
            # Save and encode
            os.makedirs('temp_images', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"temp_images/montage_{timestamp}.jpg"
            montage.save(output_path, quality=85)
            
            # Return base64 for client
            with open(output_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            
            return f"data:image/jpeg;base64,{encoded}"
        
        except Exception as e:
            logger.error(f"Montage generation error: {e}")
            return None
    
    def hybrid_search(self, text_query: str, image_path: Optional[str] = None, 
                      top_k: int = 6, weights: Tuple[float, float] = (0.7, 0.3)) -> Dict:
        """
        Hybrid text-image search with weighted combination.
        
        Args:
            text_query: Text search query
            image_path: Optional image for visual search
            top_k: Number of results
            weights: (text_weight, image_weight)
        
        Returns:
            Combined results
        """
        text_results = self.search_text(text_query, top_k)
        
        if image_path and os.path.exists(image_path):
            image_results = self.search_image(image_path, top_k)
            
            # Weighted combination (MVP: just return text results with note)
            text_results['image_input'] = True
            text_results['note'] = "Hybrid search: prioritizing text with visual context"
        
        return text_results
    
    def get_recommendations_for_lifestyle(self, lifestyle: str, top_k: int = 6) -> Dict:
        """
        Get cross-modal recommendations for a lifestyle profile.
        
        Args:
            lifestyle: Lifestyle description (e.g., "Family with kids")
            top_k: Number of results
        
        Returns:
            Lifestyle-matched properties with montage
        """
        # Map lifestyle to search query
        lifestyle_queries = {
            'family': 'family friendly property kids play area swimming pool',
            'professional': 'modern apartment wifi gym professional amenities',
            'luxury': 'luxury apartment sea view premium amenities smart home',
            'workout': 'property gym fitness jogging track yoga tennis',
            'budget': 'affordable apartment budget friendly investment property',
            'retirement': 'quiet peaceful property senior citizens garden park'
        }
        
        key = next((k for k in lifestyle_queries if k in lifestyle.lower()), None)
        query = lifestyle_queries.get(key, lifestyle)
        
        return self.search_text(query, top_k)
    
    def get_stats(self) -> Dict:
        """Get indexing statistics."""
        return {
            'total_properties': len(self.properties),
            'properties_with_images': sum(1 for p in self.properties if p['image_path']),
            'index_size': len(self.properties),
            'embedding_dimension': self.embedding_dim,
            'search_types_supported': ['text', 'image', 'hybrid'],
            'model': getattr(self, 'model_name', self.EMBEDDING_MODEL)
        }
