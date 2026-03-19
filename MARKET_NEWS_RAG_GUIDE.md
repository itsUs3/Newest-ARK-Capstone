# Market News RAG System - Implementation Guide

## Overview
The Market News RAG (Retrieval-Augmented Generation) system provides real-time market alerts and trend analysis for real estate locations across India. It uses ChromaDB for vector storage and sentence-transformers for semantic search of news articles.

## Features

### 1. **Market Alerts by Location**
- Retrieve relevant news articles for any location
- AI-generated summaries and insights
- Impact scoring and recommendations
- **Endpoint**: `GET /api/genai/market-alerts/{location}`

### 2. **Trending Locations**
- Discover locations with high market activity
- Based on news volume and impact scores
- **Endpoint**: `GET /api/genai/trending-locations`

### 3. **Property Impact Analysis**
- Analyze how market news affects specific properties
- Property-specific recommendations
- **Endpoint**: `POST /api/genai/market-alerts/property-impact`

### 4. **Custom News Addition**
- Add new articles to the RAG database
- Supports batch uploads
- **Endpoint**: `POST /api/genai/market-news/add`

## Architecture

```
┌─────────────────┐
│  News Articles  │
│   (CSV/API)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Sentence        │
│ Transformers    │ (Embeddings)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ChromaDB      │ (Vector Store)
│  (Persistent)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RAG Retrieval  │ (Semantic Search)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AI Generation   │ (Insights & Alerts)
│  (GPT/Claude)   │
└─────────────────┘
```

## Installation & Setup

### 1. Install Dependencies
All required packages are already in `requirements.txt`:
```bash
pip install chromadb sentence-transformers langchain
```

### 2. Load Sample Data
Initialize the RAG database with sample news:
```bash
cd backend
python load_market_news.py
```

This will:
- Create a `chroma_db` directory
- Load 30 sample news articles
- Create vector embeddings
- Test retrieval functionality

### 3. Verify Installation
After loading, you should see:
```
✅ Market news data loaded successfully!
You can now use the RAG endpoints:
  - GET /api/genai/market-alerts/{location}
  - GET /api/genai/trending-locations
  - POST /api/genai/market-alerts/property-impact
```

## API Usage

### Get Market Alerts
```bash
# Get news alerts for Mumbai
curl http://localhost:8000/api/genai/market-alerts/Mumbai

# Get alerts with specific query
curl http://localhost:8000/api/genai/market-alerts/Andheri?query=metro

# Get more results
curl http://localhost:8000/api/genai/market-alerts/Bangalore?n_results=10
```

**Response:**
```json
{
  "location": "Mumbai",
  "alert_summary": "📈 Market Update for Mumbai:\n\n• Mumbai Metro Line 3...\n• Coastal Road Project...",
  "articles": [
    {
      "title": "Mumbai Metro Line 3...",
      "content": "...",
      "location": "mumbai",
      "date": "2026-02-15",
      "source": "MagicBricks News",
      "impact_score": 0.85,
      "relevance_score": 0.92
    }
  ],
  "impact_level": "high_positive",
  "avg_impact_score": 0.83,
  "recommendation": "Strong market activity detected!...",
  "generated_at": "2026-02-22T10:30:00"
}
```

### Get Trending Locations
```bash
curl http://localhost:8000/api/genai/trending-locations?top_n=5
```

**Response:**
```json
{
  "trending_locations": [
    {
      "location": "Mumbai",
      "news_count": 15,
      "avg_impact": 0.78,
      "trend_score": 11.7
    },
    {
      "location": "Bangalore",
      "news_count": 12,
      "avg_impact": 0.75,
      "trend_score": 9.0
    }
  ],
  "generated_at": "2026-02-22T10:30:00"
}
```

### Analyze Property Impact
```bash
curl -X POST http://localhost:8000/api/genai/market-alerts/property-impact \
  -H "Content-Type: application/json" \
  -d '[
    {"id": "prop_1", "location": "Andheri West"},
    {"id": "prop_2", "location": "Whitefield"}
  ]'
```

### Add New Articles
```bash
curl -X POST http://localhost:8000/api/genai/market-news/add \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "news_custom_1",
      "title": "New Metro Line Announced",
      "content": "Full article content...",
      "location": "Mumbai",
      "date": "2026-02-22",
      "source": "Times of India",
      "url": "https://example.com/article",
      "impact_score": 0.85
    }
  ]'
```

## Data Format

### News Article Schema
```python
{
    "id": str,              # Unique identifier
    "title": str,           # Article headline
    "content": str,         # Full article text
    "location": str,        # City/area name
    "date": str,            # ISO format date
    "source": str,          # News source
    "url": str,             # Article URL
    "impact_score": float   # 0.0-1.0 (market impact)
}
```

### Impact Score Guidelines
- **0.9-1.0**: Major positive development (new metro, airport, etc.)
- **0.7-0.9**: Significant positive news (infrastructure upgrades)
- **0.5-0.7**: Moderate positive news (new projects, steady growth)
- **0.3-0.5**: Neutral or mixed news
- **0.0-0.3**: Negative news (delays, regulations, problems)

## Integration with Frontend

### Example: Property Search Page
```javascript
// Fetch market alerts when user views a property
async function getPropertyMarketContext(location) {
  const response = await fetch(
    `/api/genai/market-alerts/${encodeURIComponent(location)}?n_results=3`
  );
  const data = await response.json();
  
  // Display alert summary in UI
  displayMarketAlert(data.alert_summary, data.impact_level);
  
  // Show relevant articles
  data.articles.forEach(article => {
    displayArticle(article);
  });
}
```

### Example: Home Dashboard
```javascript
// Show trending locations on home page
async function loadTrendingLocations() {
  const response = await fetch('/api/genai/trending-locations?top_n=5');
  const data = await response.json();
  
  data.trending_locations.forEach(loc => {
    displayTrendingLocation(loc.location, loc.news_count, loc.avg_impact);
  });
}
```

### Example: Advisor Chat Integration
```javascript
// Auto-trigger alerts based on user preferences
async function checkUserPropertiesForAlerts(userProperties) {
  const response = await fetch('/api/genai/market-alerts/property-impact', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(userProperties)
  });
  
  const data = await response.json();
  
  // Show alerts for properties with significant news
  data.property_impacts.forEach(impact => {
    if (impact.alert.impact_level === 'high_positive') {
      notifyUser(`Great news about ${impact.location}!`, impact.alert);
    }
  });
}
```

## Updating News Data

### Method 1: CSV Upload
1. Add articles to `Datasets/market_news_sample.csv`
2. Run `python load_market_news.py`

### Method 2: API Upload
```python
import requests

articles = [
    {
        "id": "news_xyz",
        "title": "...",
        "content": "...",
        "location": "Mumbai",
        "date": "2026-02-22",
        "source": "Economic Times",
        "url": "https://...",
        "impact_score": 0.8
    }
]

response = requests.post(
    "http://localhost:8000/api/genai/market-news/add",
    json=articles
)
```

### Method 3: Web Scraping Integration
```python
# Example: Scrape news and add to RAG
from models.market_news_rag import MarketNewsRAG
import requests
from datetime import datetime

def scrape_and_index_news():
    rag = MarketNewsRAG()
    
    # Scrape news (use Apify or custom scraper)
    scraped_articles = scrape_real_estate_news()
    
    # Format and add to RAG
    formatted_articles = []
    for article in scraped_articles:
        formatted_articles.append({
            "id": f"news_{hash(article['url'])}",
            "title": article['headline'],
            "content": article['body'],
            "location": extract_location(article['body']),
            "date": datetime.now().isoformat(),
            "source": article['source'],
            "url": article['url'],
            "impact_score": calculate_impact_score(article['body'])
        })
    
    rag.add_news_articles(formatted_articles)
```

## Performance Optimization

### 1. Embedding Caching
Embeddings are automatically cached by ChromaDB for fast retrieval.

### 2. Query Optimization
- Use specific location names for better results
- Add query terms for targeted search
- Limit `n_results` to 5-10 for faster response

### 3. Batch Processing
When adding many articles, batch them in groups of 100:
```python
def add_articles_in_batches(articles, batch_size=100):
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        rag.add_news_articles(batch)
```

## Monitoring & Maintenance

### Check Database Stats
```python
from models.market_news_rag import MarketNewsRAG

rag = MarketNewsRAG()
collection = rag.collection

# Get total articles
count = collection.count()
print(f"Total articles: {count}")

# Get sample metadata
sample = collection.get(limit=1, include=["metadatas"])
print(f"Sample article: {sample['metadatas'][0]}")
```

### Clear and Rebuild
```python
# Delete collection and start fresh
rag.chroma_client.delete_collection("market_news")

# Recreate and reload
rag = MarketNewsRAG()
rag.load_news_from_csv("Datasets/market_news_sample.csv")
```

## Troubleshooting

### Issue: "No articles found"
- Ensure `load_market_news.py` was run successfully
- Check if `chroma_db` directory exists
- Verify CSV file path in config

### Issue: Slow retrieval
- Reduce `n_results` parameter
- Use more specific location names
- Consider using a larger embedding model for better accuracy

### Issue: Low relevance scores
- Use location-specific queries
- Add more context to search query
- Ensure articles have proper location metadata

## Future Enhancements

1. **Real-time News Integration**
   - Integrate with Apify for automated scraping
   - Schedule periodic updates
   - Support RSS feeds

2. **Advanced Analytics**
   - Sentiment analysis for impact scoring
   - Trend prediction using time-series
   - Competitor price analysis correlation

3. **Multi-language Support**
   - Hindi and regional language news
   - Translate alerts for vernacular users

4. **Personalization**
   - User-specific alert preferences
   - Location watchlists
   - Custom notification triggers

## Resources

- **ChromaDB Docs**: https://docs.trychroma.com/
- **Sentence Transformers**: https://www.sbert.net/
- **Sample Dataset**: `Datasets/market_news_sample.csv`
- **API Reference**: See Swagger UI at http://localhost:8000/docs

## Support

For issues or questions:
1. Check logs in `backend/` directory
2. Verify all dependencies are installed
3. Ensure ChromaDB is properly initialized
4. Test with sample queries first

---

**Status**: ✅ Fully Implemented and Ready for Production
**Version**: 1.0.0
**Last Updated**: February 22, 2026
