"""
Utility script to load market news data into the RAG database
Run this to initialize or update the news database
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.market_news_rag import MarketNewsRAG
import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_sample_data():
    """Load sample market news data into ChromaDB"""
    try:
        logger.info("Initializing MarketNewsRAG...")
        rag = MarketNewsRAG(persist_directory=config.RAG_PERSIST_DIR)

        # Clear existing data without deleting collection
        try:
            collection = rag.collection
            existing_ids = collection.get()['ids']
            if existing_ids:
                collection.delete(ids=existing_ids)
                logger.info(f"Cleared {len(existing_ids)} existing articles from collection")
        except Exception as e:
            logger.warning(f"Could not clear collection: {str(e)}")
        
        live_csv_path = backend_dir.parent / "Datasets" / "real_estate_news_live.csv"
        news_csv_path = live_csv_path if live_csv_path.exists() else config.RAG_NEWS_CSV_PATH

        logger.info(f"Loading news from {news_csv_path}...")
        if not news_csv_path.exists():
            logger.error(f"News CSV file not found at {news_csv_path}")
            return False
        
        rag.load_news_from_csv(str(news_csv_path))
        
        logger.info("Successfully loaded market news data!")
        
        # Test retrieval
        logger.info("\nTesting retrieval for Mumbai...")
        articles = rag.retrieve_relevant_news("Mumbai", n_results=3)
        logger.info(f"Found {len(articles)} relevant articles for Mumbai")
        
        if articles:
            logger.info(f"\nTop article: {articles[0]['title']}")
        
        # Get trending locations
        logger.info("\nGetting trending locations...")
        trending = rag.get_trending_locations(top_n=5)
        logger.info(f"Trending locations: {[loc['location'] for loc in trending]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return False


if __name__ == "__main__":
    success = load_sample_data()
    if success:
        print("\n✅ Market news data loaded successfully!")
        print("You can now use the RAG endpoints:")
        print("  - GET /api/genai/market-alerts/{location}")
        print("  - GET /api/genai/trending-locations")
        print("  - POST /api/genai/market-alerts/property-impact")
    else:
        print("\n❌ Failed to load market news data")
        sys.exit(1)
