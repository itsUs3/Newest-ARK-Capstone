"""
RAG-Driven Market News Aggregator for Trend Alerts
Uses ChromaDB for vector storage and sentence-transformers for embeddings
Retrieves relevant news articles about locations and generates insights
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import logging
import shutil

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    RAG_AVAILABLE = True
except Exception as e:
    SentenceTransformer = None
    chromadb = None
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


class MarketNewsRAG:
    """
    RAG system for real estate market news and trend alerts
    """
    
    def __init__(self, persist_directory: str = "chroma_db"):
        """
        Initialize the RAG system with ChromaDB and embeddings model
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        self.rag_enabled = RAG_AVAILABLE
        self.collection_name = "market_news"
        self.embedding_model = None
        self.chroma_client = None

        if not self.rag_enabled:
            logger.warning("MarketNewsRAG running in fallback mode: embedding/vector dependencies unavailable")
            return
        
        # Initialize embedding model
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize ChromaDB client
        logger.info("Initializing ChromaDB...")
        self.collection_name = "market_news"
        try:
            self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            self._ensure_collection_exists()
        except Exception as e:
            if self._is_schema_mismatch_error(e):
                logger.warning(f"Detected incompatible ChromaDB schema. Reinitializing store at {persist_directory}")
                self._reinitialize_persist_store()
                self.chroma_client = chromadb.PersistentClient(path=persist_directory)
                self._ensure_collection_exists()
            else:
                raise

    def _is_schema_mismatch_error(self, error: Exception) -> bool:
        msg = str(error).lower()
        return (
            "no such column" in msg
            or "schema" in msg
            or "mismatch" in msg
            or "collections.topic" in msg
        )

    def _reinitialize_persist_store(self):
        """Backup and recreate Chroma persist directory when schema is incompatible."""
        persist_path = Path(self.persist_directory)
        if not persist_path.exists():
            return

        backup_path = persist_path.parent / f"{persist_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.move(str(persist_path), str(backup_path))
            logger.warning(f"Moved incompatible Chroma store to: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not backup old Chroma store ({e}). Attempting delete and recreate.")
            shutil.rmtree(persist_path, ignore_errors=True)
    
    def _ensure_collection_exists(self):
        """Ensure the collection exists, create if it doesn't"""
        if not self.rag_enabled or not self.chroma_client:
            return
        try:
            self.chroma_client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing {self.collection_name} collection")
        except Exception:
            self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new {self.collection_name} collection")
    
    @property
    def collection(self):
        """Get collection dynamically to handle collection refreshes"""
        if not self.rag_enabled or not self.chroma_client:
            return None
        try:
            return self.chroma_client.get_collection(name=self.collection_name)
        except Exception as e:
            logger.warning(f"Collection not found, recreating: {e}")
            self._ensure_collection_exists()
            return self.chroma_client.get_collection(name=self.collection_name)
    
    def add_news_articles(self, articles: List[Dict]):
        """
        Add news articles to the vector database
        
        Args:
            articles: List of dicts with keys: id, title, content, location, 
                     date, source, url, impact_score
        """
        try:
            if not self.rag_enabled:
                logger.warning("RAG disabled: skipping add_news_articles")
                return

            if not articles:
                logger.warning("No articles to add")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            for article in articles:
                # Combine title and content for better context
                text = f"{article['title']}\n\n{article['content']}"
                documents.append(text)
                
                # Metadata for filtering
                metadatas.append({
                    "location": article.get("location", "").lower(),
                    "date": article.get("date", datetime.now().isoformat()),
                    "source": article.get("source", "unknown"),
                    "url": article.get("url", ""),
                    "impact_score": article.get("impact_score", 0.5),
                    "title": article.get("title", "")
                })
                
                ids.append(article["id"])
            
            # Generate embeddings and add to collection
            embeddings = self.embedding_model.encode(documents).tolist()
            
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(articles)} articles to the database")
            
        except Exception as e:
            logger.error(f"Error adding articles: {str(e)}")
            raise
    
    def _search_csv_fallback(
        self, 
        location: str, 
        query: Optional[str] = None,
        n_results: int = 5,
        days_back: int = 365
    ) -> List[Dict]:
        """
        Fallback method to search CSV file when RAG is unavailable
        """
        try:
            # Try to load CSV from known locations
            csv_paths = [
                "Datasets/real_estate_news_live.csv",
                "../Datasets/real_estate_news_live.csv",
                "../../Datasets/real_estate_news_live.csv"
            ]
            
            df = None
            for csv_path in csv_paths:
                if Path(csv_path).exists():
                    df = pd.read_csv(csv_path)
                    break
            
            if df is None:
                logger.warning("No CSV file found in fallback mode")
                return []
            
            # Filter by location (case-insensitive)
            location_lower = location.lower()
            df_filtered = df[df['location'].str.lower().str.contains(location_lower, na=False)]
            
            # Additional query filter if provided
            if query:
                query_lower = query.lower()
                df_filtered = df_filtered[
                    df_filtered['title'].str.lower().str.contains(query_lower, na=False) |
                    df_filtered['content'].str.lower().str.contains(query_lower, na=False)
                ]
            
            # Filter by date if date column exists
            if 'date' in df_filtered.columns:
                try:
                    df_filtered['date_parsed'] = pd.to_datetime(df_filtered['date'], errors='coerce')
                    date_threshold = datetime.now() - timedelta(days=days_back)
                    df_filtered = df_filtered[df_filtered['date_parsed'] > date_threshold]
                except Exception:
                    pass
            
            # Sort by impact_score if available, otherwise by date
            if 'impact_score' in df_filtered.columns:
                df_filtered = df_filtered.sort_values('impact_score', ascending=False)
            elif 'date' in df_filtered.columns:
                df_filtered = df_filtered.sort_values('date', ascending=False)
            
            # Limit results
            df_filtered = df_filtered.head(n_results)
            
            # Convert to list of dicts
            articles = []
            for _, row in df_filtered.iterrows():
                articles.append({
                    "id": row.get('id', ''),
                    "title": row.get('title', ''),
                    "content": row.get('content', '')[:500],  # Truncate content
                    "location": row.get('location', ''),
                    "date": row.get('date', ''),
                    "source": row.get('source', ''),
                    "url": row.get('url', ''),
                    "impact_score": float(row.get('impact_score', 0.5))
                })
            
            logger.info(f"CSV fallback found {len(articles)} articles for {location}")
            return articles
            
        except Exception as e:
            logger.error(f"CSV fallback failed: {str(e)}")
            return []
    
    def retrieve_relevant_news(
        self, 
        location: str, 
        query: Optional[str] = None,
        n_results: int = 5,
        days_back: int = 365
    ) -> List[Dict]:
        """
        Retrieve relevant news articles for a location
        
        Args:
            location: Location to search for (e.g., "Mumbai", "Andheri")
            query: Optional specific query (e.g., "metro construction")
            n_results: Number of results to return
            days_back: Only return news from last N days
        
        Returns:
            List of relevant news articles with metadata
        """
        try:
            if not self.rag_enabled:
                logger.info("RAG disabled: using CSV fallback for news search")
                return self._search_csv_fallback(location, query, n_results, days_back)

            # Build query text - prioritize user's specific query
            if query:
                # When user provides specific query, focus on that with location context
                query_text = f"{query} in {location} real estate property development"
            else:
                query_text = f"{location} real estate infrastructure development news"
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text]).tolist()
            
            # Query the collection without date filter (ChromaDB has limited filtering)
            # We'll filter by date in post-processing
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results * 3  # Get more results to filter
            )
            
            # Calculate date threshold for filtering
            date_threshold = datetime.now() - timedelta(days=days_back)
            
            # Format results and filter by date
            articles = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    
                    # Check date if available
                    article_date_str = metadata.get("date", "")
                    try:
                        article_date = datetime.fromisoformat(article_date_str.replace('Z', '+00:00'))
                        if article_date < date_threshold:
                            continue
                    except (ValueError, AttributeError):
                        # If date parsing fails, include the article
                        pass
                    
                    articles.append({
                        "content": doc,
                        "title": metadata.get("title", ""),
                        "location": metadata.get("location", ""),
                        "date": metadata.get("date", ""),
                        "source": metadata.get("source", ""),
                        "url": metadata.get("url", ""),
                        "impact_score": metadata.get("impact_score", 0.5),
                        "relevance_score": 1 - results['distances'][0][i] if results.get('distances') else 0.5
                    })
                    
                    # Stop if we have enough results
                    if len(articles) >= n_results:
                        break
            
            return articles[:n_results]
            
        except Exception as e:
            logger.error(f"Error retrieving news: {str(e)}")
            return []
    
    def generate_alert(
        self, 
        location: str, 
        articles: List[Dict],
        user_properties: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Generate a market alert summary from retrieved articles
        
        Args:
            location: Location being analyzed
            articles: Retrieved relevant articles
            user_properties: Optional list of user's shortlisted properties
        
        Returns:
            Dict with alert summary and insights
        """
        try:
            if not articles:
                return {
                    "location": location,
                    "alert_summary": f"No recent market news found for {location}.",
                    "articles": [],
                    "impact_level": "neutral",
                    "recommendation": "Monitor the market for updates."
                }
            
            # Calculate average impact
            avg_impact = sum(a.get("impact_score", 0.5) for a in articles) / len(articles)
            
            # Determine impact level
            if avg_impact >= 0.7:
                impact_level = "high_positive"
                emoji = "📈"
            elif avg_impact >= 0.5:
                impact_level = "moderate_positive"
                emoji = "📊"
            elif avg_impact >= 0.3:
                impact_level = "neutral"
                emoji = "➡️"
            else:
                impact_level = "negative"
                emoji = "📉"
            
            # Generate summary
            key_points = []
            for article in articles[:3]:  # Top 3 articles
                title = article.get("title", "")
                if title:
                    key_points.append(title)
            
            alert_summary = f"{emoji} Market Update for {location}:\n\n"
            alert_summary += "\n".join(f"• {point}" for point in key_points)
            
            # Generate recommendation
            if impact_level in ["high_positive", "moderate_positive"]:
                recommendation = f"Strong market activity detected! {location} is showing positive trends. Consider prioritizing properties in this area."
            elif impact_level == "neutral":
                recommendation = f"Stable market conditions in {location}. Good time for balanced investment."
            else:
                recommendation = f"Market showing some challenges in {location}. Proceed with caution and thorough research."
            
            # Property-specific impact
            property_impact = []
            if user_properties:
                for prop in user_properties:
                    if location.lower() in prop.get("location", "").lower():
                        property_impact.append({
                            "property_id": prop.get("id"),
                            "impact": f"This property may see {impact_level.replace('_', ' ')} impact based on recent developments."
                        })
            
            return {
                "location": location,
                "alert_summary": alert_summary,
                "articles": articles,
                "impact_level": impact_level,
                "avg_impact_score": round(avg_impact, 2),
                "recommendation": recommendation,
                "property_impact": property_impact,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating alert: {str(e)}")
            return {
                "location": location,
                "alert_summary": f"Error generating alert for {location}",
                "articles": [],
                "impact_level": "unknown",
                "recommendation": "Unable to generate recommendation at this time."
            }
    
    def _trending_csv_fallback(self, top_n: int = 5) -> List[Dict]:
        """
        Fallback method to get trending locations from CSV
        """
        try:
            # Try to load CSV from known locations
            csv_paths = [
                "Datasets/real_estate_news_live.csv",
                "../Datasets/real_estate_news_live.csv",
                "../../Datasets/real_estate_news_live.csv"
            ]
            
            df = None
            for csv_path in csv_paths:
                if Path(csv_path).exists():
                    df = pd.read_csv(csv_path)
                    break
            
            if df is None:
                logger.warning("No CSV file found for trending locations")
                return []
            
            # Filter by date if available
            if 'date' in df.columns:
                try:
                    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
                    date_threshold = datetime.now() - timedelta(days=120)
                    df = df[df['date_parsed'] > date_threshold]
                except Exception:
                    pass
            
            # Filter out generic "India" entries before grouping
            df = df[~df['location'].str.lower().isin(['india', ''])]
            
            # Group by location and calculate stats
            location_stats = df.groupby('location').agg({
                'id': 'count',  # news count
                'impact_score': 'mean'  # average impact
            }).reset_index()
            
            location_stats.columns = ['location', 'news_count', 'avg_impact']
            location_stats['trend_score'] = location_stats['news_count'] * location_stats['avg_impact']
            
            # Sort by trend score
            location_stats = location_stats.sort_values('trend_score', ascending=False)
            location_stats = location_stats.head(top_n)
            
            # Convert to list of dicts
            trending = location_stats.to_dict('records')
            for item in trending:
                item['avg_impact'] = round(item['avg_impact'], 2)
                item['trend_score'] = round(item['trend_score'], 2)
            
            logger.info(f"CSV fallback found {len(trending)} trending locations")
            return trending
            
        except Exception as e:
            logger.error(f"Trending CSV fallback failed: {str(e)}")
            return []
    
    def get_trending_locations(self, top_n: int = 5) -> List[Dict]:
        """
        Get trending locations based on recent news volume and impact
        
        Args:
            top_n: Number of top locations to return
        
        Returns:
            List of trending locations with stats
        """
        try:
            if not self.rag_enabled:
                logger.info("RAG disabled: using CSV fallback for trending locations")
                return self._trending_csv_fallback(top_n)

            # Get all documents (ChromaDB filtering is limited)
            results = self.collection.get(
                include=["metadatas"]
            )
            
            if not results['metadatas']:
                return []
            
            # Calculate date threshold for filtering
            date_threshold = datetime.now() - timedelta(days=120)
            
            # Count by location and calculate average impact
            location_stats = {}
            for metadata in results['metadatas']:
                # Filter by date manually
                article_date_str = metadata.get("date", "")
                try:
                    article_date = datetime.fromisoformat(article_date_str.replace('Z', '+00:00'))
                    if article_date < date_threshold:
                        continue
                except (ValueError, AttributeError):
                    # If date parsing fails, skip
                    continue
                
                loc = metadata.get("location", "").title()
                # Filter out generic "India" entries - we want specific cities only
                if loc and loc.lower() not in ['india', '']:
                    if loc not in location_stats:
                        location_stats[loc] = {
                            "count": 0,
                            "total_impact": 0
                        }
                    location_stats[loc]["count"] += 1
                    location_stats[loc]["total_impact"] += metadata.get("impact_score", 0.5)
            
            # Calculate scores (weighted by count and average impact)
            trending = []
            for loc, stats in location_stats.items():
                avg_impact = stats["total_impact"] / stats["count"]
                trend_score = stats["count"] * avg_impact
                
                trending.append({
                    "location": loc,
                    "news_count": stats["count"],
                    "avg_impact": round(avg_impact, 2),
                    "trend_score": round(trend_score, 2)
                })
            
            # Sort by trend score
            trending.sort(key=lambda x: x["trend_score"], reverse=True)
            
            return trending[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting trending locations: {str(e)}")
            return []
    
    def load_news_from_csv(self, csv_path: str):
        """
        Load news articles from a CSV file
        
        Expected columns: id, title, content, location, date, source, url, impact_score
        """
        try:
            df = pd.read_csv(csv_path)
            
            # Ensure required columns
            required_cols = ['title', 'content', 'location']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain columns: {required_cols}")
            
            # Add default values for optional columns
            if 'id' not in df.columns:
                df['id'] = [f"news_{i}" for i in range(len(df))]
            if 'date' not in df.columns:
                df['date'] = datetime.now().isoformat()
            if 'source' not in df.columns:
                df['source'] = 'unknown'
            if 'url' not in df.columns:
                df['url'] = ''
            if 'impact_score' not in df.columns:
                df['impact_score'] = 0.5
            
            # Convert to list of dicts
            articles = df.to_dict('records')
            
            # Add to database
            self.add_news_articles(articles)
            
            logger.info(f"Loaded {len(articles)} articles from {csv_path}")
            
        except Exception as e:
            logger.error(f"Error loading news from CSV: {str(e)}")
            raise
