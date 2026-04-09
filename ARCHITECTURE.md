# 🏗️ myNivas Architecture & System Design

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                   (Desktop / Mobile)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    HTTP/REST API
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
┌──────────────────┐              ┌──────────────────┐
│  Frontend (3000) │              │  Backend (8000)  │
│  React + Vite    │              │  FastAPI+Python  │
├──────────────────┤              ├──────────────────┤
│ Pages:           │              │ API Endpoints:   │
│ • Home           │              │ • /api/price/*   │
│ • Search         │              │ • /api/fraud/*   │
│ • Analyzer       │              │ • /api/recs/*    │
│ • Detector       │              │ • /api/genai/*   │
│ • Chat           │              │ • /api/data/*    │
├──────────────────┤              ├──────────────────┤
│ Libraries:       │              │ Components:      │
│ • React Router   │              │ • Data Loading   │
│ • Tailwind CSS   │              │ • Processing     │
│ • Framer Motion  │              │ • ML Models      │
│ • Axios API      │              │ • GenAI Handler  │
│ • Zustand State  │              │ • Validators     │
│ • Recharts       │              └──────────────────┘
└──────────────────┘                     │
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
        ┌────────────────┐      ┌────────────────┐     ┌──────────────┐
        │   ML Models    │      │     Handlers   │     │   Database   │
        ├────────────────┤      ├────────────────┤     ├──────────────┤
        │ Price Pred:    │      │ GenAI:         │     │ SQLite       │
        │ • RF Regressor │      │ • Chat         │     │ (Local Dev)  │
        │ • LR Baseline  │      │ • Descriptions │     │              │
        │                │      │ • Price Expl.  │     │ PostgreSQL   │
        │ Fraud Detect:  │      │                │     │ (Production) │
        │ • TF-IDF       │      │ Data Process:  │     │              │
        │ • Text Sim     │      │ • CSV Parse    │     │ CSV Files:   │
        │ • Keywords     │      │ • Feature Eng  │     │ • Housing1   │
        │                │      │ • Encoding     │     │ • 99acres    │
        │ Recommend:     │      │                │     │ • MagicBricks│
        │ • Content Filter       │ API Client:    │     │              │
        │ • Matching     │      │ • Validation   │     │ External:    │
        │ • Scoring      │      │ • Error Handle │     │ • OpenAI API │
        └────────────────┘      │ • CORS         │     │ • Claude API │
                                └────────────────┘     └──────────────┘
```

---

## Data Flow Diagram

### Search Flow
```
User Search Request
    ↓
Frontend sends filters (location, BHK, budget)
    ↓
Backend /api/recommendations
    ↓
Recommendation Engine
    • Load properties from dataset
    • Score each property
    • Apply user preferences
    • Rank by match
    ↓
Return top 15 properties with match_score
    ↓
Frontend displays results
    • Shows property cards
    • Match score badge
    • Trust indicator
    • Call to action
```

### Price Prediction Flow
```
User enters: location, BHK, size, amenities
    ↓
Frontend POST /api/price/predict
    ↓
Backend receives data
    ↓
Feature Engineering
    • Encode location
    • Normalize size
    • Extract amenities
    • Create feature vector
    ↓
RandomForest Model.predict(features)
    ↓
Post-Processing
    • Calculate price range (±15%)
    • Analyze factors
    • Compute confidence
    ↓
Return prediction with metadata
    ↓
Frontend displays
    • Main price (₹ format)
    • Range visualization
    • Confidence meter
    • Factor breakdown
    • Trend chart
```

### Fraud Detection Flow
```
User enters property details
    ↓
Frontend POST /api/fraud/detect
    ↓
Text Quality Scoring
    • Check length
    • Check capitalization
    • Check special chars
    ↓
Duplicate Detection
    • TF-IDF vectorization
    • Cosine similarity
    • Compare with database
    ↓
Keyword Analysis
    • Scan for suspicious phrases
    • Check urgency tactics
    • Look for red flags
    ↓
Calculate Trust Score
    • Weight all signals
    • 0-100 score
    • Risk level (LOW/MED/HIGH)
    ↓
Return analysis with flags
    ↓
Frontend displays
    • Big trust score
    • Risk badge
    • Flag list
    • Safety tips
```

---

## Component Architecture

### Frontend Components Tree
```
App
├── Navbar
│   ├── Logo
│   └── Nav Links
│
├── Routes
│   ├── Home
│   │   ├── Hero Section
│   │   ├── Features Grid
│   │   ├── Stats Cards
│   │   └── CTA Section
│   │
│   ├── Search
│   │   ├── Filter Form
│   │   └── Results Grid
│   │       └── Property Cards
│   │           ├── Image
│   │           ├── Details
│   │           ├── Match Score
│   │           └── Actions
│   │
│   ├── PriceAnalyzer
│   │   ├── Input Form
│   │   └── Results Panel
│   │       ├── Price Cards
│   │       ├── Chart
│   │       └── Factors
│   │
│   ├── FraudDetector
│   │   ├── Input Form
│   │   └── Analysis Results
│   │       ├── Trust Score
│   │       ├── Risk Badge
│   │       ├── Flags
│   │       └── Tips
│   │
│   ├── AdvisorChat
│   │   ├── Message List
│   │   ├── Suggestions
│   │   └── Input Box
│   │
│   └── PropertyDetail
│       ├── Gallery
│       ├── Details
│       ├── Amenities
│       ├── Location Map
│       └── Sidebar
│           ├── Price Card
│           ├── Trust Score
│           └── Developer Info
│
└── Footer
    ├── Links
    ├── Company Info
    └── Social
```

### Backend Routes Structure
```
FastAPI App
│
├── GET /
│   └── Root endpoint info
│
├── GET /api/health
│   └── Health check
│
├── POST /api/price/predict
│   └── PricePredictor.predict()
│
├── GET /api/price/market-analysis/{location}
│   └── PricePredictor.analyze_market()
│
├── POST /api/fraud/detect
│   └── FraudDetector.analyze()
│
├── POST /api/fraud/batch-detect
│   └── FraudDetector.batch_analyze()
│
├── POST /api/recommendations
│   └── RecommendationEngine.get_recommendations()
│
├── GET /api/recommendations/trending
│   └── RecommendationEngine.get_trending()
│
├── POST /api/genai/describe
│   └── GenAIHandler.generate_description()
│
├── POST /api/genai/explain-price
│   └── GenAIHandler.explain_price()
│
├── POST /api/genai/chat
│   └── GenAIHandler.chat()
│
├── POST /api/data/upload-listings
│   └── DataProcessor.process_listings()
│
├── GET /api/data/listings
│   └── DataProcessor.get_listings()
│
└── GET /api/data/locations
    └── DataProcessor.get_unique_locations()
```

---

## Data Model

### Property Object
```python
{
    "id": "property_0",
    "title": "2 BHK Apartment",
    "description": "Beautiful apartment...",
    "location": "Mumbai, Ghatkopar",
    "bhk": 2,
    "size": 850.0,
    "price": 8500000,
    "amenities": ["gym", "pool", "parking"],
    "images": ["url1", "url2", "url3"],
    "seller": "Developer Name",
    "rating": 4.5,
    "views": 2300,
    "posted_date": "2026-02-03",
    "source": "Housing.com"
}
```

### Prediction Result
```python
{
    "predicted_price": 8500000,
    "price_range": {
        "min": 7225000,
        "max": 9775000
    },
    "confidence": 0.75,
    "factors": {
        "bhk_impact": "...",
        "size_impact": "...",
        "location_multiplier": "...",
        "amenities_bonus": "..."
    }
}
```

### Fraud Analysis
```python
{
    "trust_score": 85.0,
    "risk_level": "LOW",
    "flags": ["Possible red flag 1", "Possible red flag 2"],
    "confidence": 0.85
}
```

---

## Technology Stack Details

### Frontend Stack
```
React 18          - UI library
Vite              - Build tool (fast dev server)
Tailwind CSS      - Styling framework
Framer Motion     - Animations
Zustand           - State management
Axios             - HTTP client
React Router      - Routing
Recharts          - Chart library
react-hot-toast   - Notifications
```

### Backend Stack
```
FastAPI           - Web framework
Uvicorn           - ASGI server
Pydantic          - Data validation
Pandas            - Data processing
NumPy             - Numerical computing
Scikit-learn      - ML algorithms
Python-dotenv     - Environment config
CORS              - Cross-origin support
```

### ML/AI Libraries
```
Random Forest     - Price prediction model
TF-IDF            - Text similarity
Cosine Similarity - Duplicate detection
LabelEncoder      - Categorical encoding
StandardScaler    - Feature normalization
OpenAI/Claude     - GenAI APIs
```

---

## Database Schema (for PostgreSQL)

```sql
-- Properties Table
CREATE TABLE properties (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    location VARCHAR(255),
    bhk INT,
    size FLOAT,
    price BIGINT,
    amenities TEXT[],
    images TEXT[],
    seller VARCHAR(255),
    rating FLOAT,
    source VARCHAR(255),
    created_at TIMESTAMP
);

-- Predictions Table
CREATE TABLE price_predictions (
    id SERIAL PRIMARY KEY,
    property_id VARCHAR(255),
    predicted_price BIGINT,
    actual_price BIGINT,
    confidence FLOAT,
    created_at TIMESTAMP
);

-- Fraud Scores Table
CREATE TABLE fraud_scores (
    id SERIAL PRIMARY KEY,
    property_id VARCHAR(255),
    trust_score FLOAT,
    risk_level VARCHAR(50),
    flags TEXT[],
    created_at TIMESTAMP
);

-- User Interactions (future)
CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    property_id VARCHAR(255),
    action VARCHAR(50),
    timestamp TIMESTAMP
);
```

---

## Deployment Architecture

### Development
```
Local Machine
├── Frontend (http://localhost:3000)
├── Backend (http://localhost:8000)
├── SQLite DB
└── Models (trained locally)
```

### Production
```
Cloud Infrastructure
├── Frontend
│   ├── Vercel/Netlify
│   ├── CDN
│   └── Static files
├── Backend
│   ├── AWS EC2 / Railway / Render
│   ├── Load Balancer
│   ├── Auto-scaling
│   └── Health checks
├── Database
│   ├── PostgreSQL RDS
│   ├── Backups
│   └── Replication
└── Cache
    ├── Redis
    └── CDN Cache
```

---

## Performance Optimization

### Frontend
- Code splitting with React.lazy
- Image optimization
- CSS minification
- JavaScript minification
- Gzip compression
- Browser caching

### Backend
- Model caching
- Query optimization
- Connection pooling
- Response compression
- Rate limiting
- Request validation

### ML Models
- Model quantization (for size)
- Batch inference
- Feature caching
- Asynchronous predictions

---

## 🧱 Floorplan Generator Architecture

### Feature Overview
The Design Studio stack was retired. Floorplan generation now uses a deterministic CSP-style room-sequencing engine based on room area, quantity, and adjacency constraints.

### Pipeline
```
Client Request
    ↓
POST /api/floorplan/generate
    ↓
Input validation (Pydantic)
    ↓
Room expansion (quantity → flat list)
    ↓
Constraint normalization (bidirectional forbidden pairs)
    ↓
Backtracking search + special rules
    ↓
Plan capping (max_plans)
    ↓
Structured response
```

### Backend Components
```
└── backend/
        ├── models/
        │   └── floorplan_generator.py     # CSP-style generator
        │       ├── _expand_rooms()
        │       ├── _constraints_to_set()
        │       ├── _generate_sequences()
        │       └── generate()
        │
        └── main.py                        # FastAPI endpoint
                └── POST /api/floorplan/generate
```

### Frontend Components
```
└── frontend/src/
        ├── pages/
        │   └── FloorplanGenerator.jsx     # Minimal input + result UI
        └── utils/
                └── api.js                     # generateFloorplan()
```

### Notes
- No PDF upload path in the new floorplan generator.
- No external image design API dependency in this flow.
- Response is deterministic and explainable relative to constraints.

---

## Performance Optimization

### Deployment Architecture
```
Storage:
├── Temp PDF storage (local /temp_pdfs)
├── Generated designs (in-memory dict)
└── Future: S3 for persistence

Caching:
├── PDF analysis results (cache layer planned)
└── Design images (CDN for delivery)

Async Processing:
├── Background PDF processing
└── Async API calls to Luw.ai
```

### Metrics & Monitoring
- Generation latency (target: <10s for initial, <15s for refinement)
- API error rate & fallback frequency
- User satisfaction (design acceptance rate)
- Cost monitoring (Luw.ai token usage)

---

## Deployment Considerations

Security Architecture


```
Internet
    ↓
HTTPS/TLS
    ↓
API Gateway
├── Rate Limiting
├── DDoS Protection
└── Request Validation
    ↓
Authentication Layer (future JWT)
    ↓
Authorization Checks
    ↓
Business Logic
    ↓
Database
├── Encrypted password
├── SQL Injection prevention
└── Input sanitization
```

---

## Scalability Considerations

1. **Horizontal Scaling**: Multiple backend instances
2. **Vertical Scaling**: Larger instance types
3. **Database Scaling**: Read replicas, sharding
4. **Caching**: Redis for hot data
5. **CDN**: Distribute static assets
6. **Async Tasks**: Celery for background jobs
7. **Load Balancing**: Distribute requests

---

**Architecture Version**: 1.0
**Last Updated**: February 6, 2026
**Status**: MVP Complete
