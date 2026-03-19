# Cross-Modal Property Search - Deployment & Usage Guide

## Quick Start

### 1. Installation (Backend)

```bash
# Navigate to backend directory
cd backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Verify cross-modal integration
python verify_integration.py
```

### 2. Start the Backend

```bash
# Run FastAPI backend (default port 8000)
python main.py

# OR use uvicorn directly
uvicorn main:app --reload --port 8000
```

### 3. Start the Frontend

```bash
# In another terminal, navigate to frontend
cd frontend

# Install dependencies (if needed)
npm install

# Start development server (default port 3000)
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Swagger Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

---

## Usage

### Via Web Interface (Recommended)

1. **Navigate to Home Page** → http://localhost:3000

2. **Search Methods**:

   **Option A: Natural Language Query**
   ```
   Input: "Affordable sea-view flat with gym near Mumbai"
   → Press 🚀 Search
   → See visual montage + 6 matching properties
   ```

   **Option B: Lifestyle Quick Filter**
   ```
   Click: "Family with Kids" or other lifestyle
   → Auto-populates with optimized query
   → System finds family-friendly properties
   ```

3. **View Results**:
   - 📊 Visual montage (1200×800, 6 property images)
   - 🏠 Property cards with details
   - 📈 Match scores (similarity percentage)
   - 💰 Pricing and amenities

### Via API (For Integration)

**Endpoint**: `POST /api/genai/cross-modal-match`

**Request**:
```json
{
  "query": "Affordable apartment with gym",
  "lifestyle": "Family with Kids",
  "top_k": 6,
  "use_cross_modal": true
}
```

**Response**:
```json
{
  "success": true,
  "search_type": "cross_modal",
  "original_query": "Affordable apartment with gym",
  "optimized_query": "Affordable apartment with gym family friendly property kids...",
  "lifestyle_profile": "Family with Kids",
  "matches": [
    {
      "name": "Luxury Vista Apartments",
      "address": "Bandra, Mumbai",
      "city": "Mumbai",
      "price": 5000000,
      "amenities": ["gym", "pool", "school nearby"],
      "similarity_score": 0.87
    },
    // ... 5 more matches
  ],
  "montage": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...",
  "stats": {
    "total_properties": 100,
    "search_time": 1.23,
    "index_size": "23MB"
  }
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/genai/cross-modal-match \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sea view apartment",
    "lifestyle": "Luxury Living",
    "top_k": 6,
    "use_cross_modal": true
  }'
```

**Python Example**:
```python
import requests

response = requests.post(
    'http://localhost:8000/api/genai/cross-modal-match',
    json={
        'query': 'Affordable flat near college',
        'lifestyle': 'Young Professional',
        'top_k': 6,
        'use_cross_modal': True
    }
)

data = response.json()
print(f"Found {len(data['matches'])} properties")
print(f"Montage: {data['montage'][:50]}...")  # Base64 image
```

---

## Lifestyle Profiles & Optimized Queries

The system automatically optimizes searches based on selected lifestyle:

| Lifestyle | Optimized Query | Target Properties |
|-----------|-----------------|-------------------|
| **Family with Kids** | "family friendly property kids play area swimming pool school nearby safe gated" | Kid-safe, schools, pools |
| **Young Professional** | "modern apartment gym fitness near office workplace commute metro" | Metro access, modern, gyms |
| **Fitness Enthusiast** | "gym sports facility yoga swimming pool fitness center active lifestyle" | Gyms, sports facilities, yoga |
| **Luxury Living** | "luxury apartment premium amenities high-end finishes concierge service" | Premium, luxury finishes, services |
| **Work From Home** | "quiet space independent workspace internet speed studying office room" | Quiet, office space, high speed internet |
| **Retired Couple** | "peaceful community senior friendly healthcare accessibility easy maintenance" | Peaceful, accessible, low maintenance |

---

## Configuration

### Backend Environment Variables (`.env`)

```env
# Core Settings
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# LLM Settings
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4

# Database (if using)
DATABASE_URL=postgresql://user:password@localhost/myNivas

# Feature Flags
NEWS_REFRESH_ENABLED=true
NEWS_REFRESH_INTERVAL_HOURS=24

# Cross-Modal Settings
CROSS_MODAL_TOP_K=6
CROSS_MODAL_MAX_PROPERTIES=100
```

### Frontend Configuration

No special configuration needed - automatically detects backend at:
- Development: `http://localhost:8000`
- Production: Configure in `vite.config.js`

---

## Data Management

### Adding More Properties

**Option 1: Load from Datasets Directory**

Place new CSV/JSON files in `Datasets/` folder:
```
Datasets/
├── 99acres.csv
├── Housing1.csv
├── magicbricks-com-2026-02-03.csv
├── your-new-dataset.csv  ← Add here
└── your-new-dataset.json ← Or here
```

CrossModalMatcher will:
1. Auto-detect new files
2. Parse property data
3. Re-index on next initialization
4. No code changes required

**Option 2: Modify Source Directly**

Edit `cross_modal_matcher.py` line 30-35:
```python
DATASETS = [
    {
        'file': 'Datasets/dataset_housing-com-scraper_2026-02-16_14-07-08-729.json',
        'max_properties': 100
    },
    {
        'file': 'Datasets/your-custom-dataset.json',
        'max_properties': 50  # Limit
    }
]
```

### Adding Property Images

1. **Format**: JPG or PNG
2. **Size**: 200×200 px (will be resized to 180×180)
3. **Naming**: `idx_PROPERTY_ID.jpg` (e.g., `idx_123.jpg`)
4. **Location**: `data/housing1_images/`

Auto-linking: If property name contains `idx_123`, image `idx_123.jpg` will be used.

---

## Performance Optimization

### For Small Deployments (<1000 properties)
- ✅ Current FAISS IndexFlatIP is optimal
- ✅ All-in-memory, <1s search time
- ✅ No configuration needed

### For Medium Deployments (1k-100k properties)
1. **Upgrade FAISS Index**:
```python
# In cross_modal_matcher.py, line 90:
import faiss
index = faiss.IndexHNSW_Flat(384, 32)  # Use HNSW instead
index.hnsw.efSearch = 40
instance.index = index
```

2. **Results**:
   - <1s search even with 100k properties
   - Trade: ~500MB RAM per 10k properties
   - Build time: 30-60 seconds

### For Large Deployments (100k+ properties)
1. **Use GPU Acceleration**:
```bash
pip install faiss-gpu
# Requires NVIDIA CUDA 11.x
```

2. **Distributed Architecture**:
   - Shard FAISS across multiple servers
   - Load balance API requests
   - Distributed indexing

3. **Caching Layer**:
   - Add Redis for popular queries
   - Cache montages (heavy operations)
   - TTL: 24 hours

---

## Monitoring & Logging

### View Application Logs

```bash
# Backend logs (if running with --reload)
# Check terminal where `python main.py` was run

# Frontend logs
# Open browser DevTools → Console tab
```

### Performance Monitoring

```python
# Check index statistics
# Visit: http://localhost:8000/api/genai/cross-modal-stats

# Expected output:
{
  "total_properties": 100,
  "index_size_mb": 23,
  "embedding_dim": 384,
  "index_type": "IndexFlatIP",
  "avg_search_time_ms": 450
}
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 500 error on search | Missing faiss | `pip install faiss-cpu` |
| Slow search (>2s) | Too many properties | Reduce dataset or upgrade index |
| No montage shown | Missing images | Place images in `data/housing1_images/` |
| Empty results | Poor query | Use lifestyle filters for optimization |
| CORS errors | Frontend/Backend mismatch | Ensure ports correct (3000/8000) |

---

## Testing

### Run Integration Tests

```bash
cd backend
python test_cross_modal_integration.py
```

### Manual Testing with Postman

1. Import collection from API docs: http://localhost:8000/docs
2. Create request to `/api/genai/cross-modal-match`
3. Body (JSON):
```json
{
  "query": "affordable flat",
  "lifestyle": "Young Professional",
  "top_k": 6,
  "use_cross_modal": true
}
```
4. Send and verify response

### Frontend Testing

```bash
# In browser console:
fetch('http://localhost:8000/api/genai/cross-modal-match', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'affordable apartment',
    lifestyle: 'Family with Kids',
    top_k: 6,
    use_cross_modal: true
  })
})
.then(r => r.json())
.then(d => console.log('Matches:', d.matches.length, 'Montage:', d.montage.slice(0, 50)))
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] All dependencies installed: `pip install -r backend/requirements.txt`
- [ ] Environment variables configured: `.env` file created
- [ ] Tests passing: `python test_cross_modal_integration.py`
- [ ] Frontend build ready: `npm run build`
- [ ] CORS origins configured correctly in `main.py`
- [ ] Database migrations complete (if applicable)
- [ ] Images uploaded to `data/housing1_images/`
- [ ] Dataset CSVs/JSONs in `Datasets/` folder

### Deployment Options

**Option 1: Docker (Recommended)**
```dockerfile
# Dockerfile (backend)
FROM python:3.11
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Option 2: Heroku**
```bash
heroku create mynivas-app
heroku config:set OPENAI_API_KEY=your_key
git push heroku main
```

**Option 3: AWS EC2**
```bash
# SSH into instance
sudo apt-get install python3-pip
pip install -r requirements.txt
nohup python main.py > backend.log 2>&1 &
```

### Monitoring in Production

```bash
# View logs
tail -f backend.log

# Monitor resources
watch -n 1 'ps aux | grep python'

# Set up alerts
# Add to systemd service file or supervisor config
```

---

## Support

### Documentation Files
- [CROSS_MODAL_INTEGRATION.md](./CROSS_MODAL_INTEGRATION.md) - Technical overview
- [API_REFERENCE.md](./API_REFERENCE.md) - API endpoints
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design

### Code Comments
- Backend: See inline comments in `backend/models/cross_modal_matcher.py`
- Frontend: See inline comments in `frontend/src/pages/Home.jsx`
- API: See docstrings in `backend/main.py`

### Contact & Issues
- Report bugs: Check existing issues or create new one
- Feature requests: Discuss in team
- Performance questions: Profile with `cProfile` before optimizing

---

## Summary

✅ **System Ready for Production**

The cross-modal property search system is fully integrated and tested. Deploy with confidence:

1. ✅ 100 properties pre-loaded from datasets
2. ✅ Semantic search via sentence-transformers (384-dim, <1s)
3. ✅ Visual montages via PIL (1200×800, 2×3 grid)
4. ✅ Lifestyle optimization (6 profiles with keywords)
5. ✅ Graceful fallback to traditional matching
6. ✅ Fully responsive React UI
7. ✅ Complete error handling & logging
8. ✅ Backward compatible with amenity matcher

**Next Steps**:
1. Run `python verify_integration.py` to confirm setup
2. Start backend: `python main.py`
3. Start frontend: `npm run dev`
4. Visit http://localhost:3000 and test search
5. Deploy to production when ready

🚀 **Let's go find your perfect home!**
