# myNivas - API Reference

Complete API documentation for backend endpoints.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently no authentication required. Add JWT in future versions.

---

## 📍 General Endpoints

### Health Check
```
GET /api/health
Response: { "status": "healthy", "timestamp": "2026-02-06T..." }
```

### Root Info
```
GET /
Response: { "name": "myNivas", "version": "1.0.0", "endpoints": {...} }
```

---

## 💰 Price Prediction Endpoints

### Predict Price
```
POST /api/price/predict

Request:
{
  "location": "Mumbai",
  "bhk": 2,
  "size": 850,
  "amenities": ["gym", "pool", "parking"]
}

Response:
{
  "predicted_price": 8500000,
  "price_range": {
    "min": 7225000,
    "max": 9775000
  },
  "confidence": 0.75,
  "factors": {
    "bhk_impact": "2 BHK increases price by ~40%",
    "size_impact": "850 sq ft is above average",
    "location_multiplier": "Premium location factor: 1.2x",
    "amenities_bonus": "+5% per amenity, total: 3 added"
  }
}
```

### Market Analysis
```
GET /api/price/market-analysis/{location}

Example: /api/price/market-analysis/Mumbai

Response:
{
  "location": "Mumbai",
  "average_price": 5500000,
  "price_range": {
    "low": 2500000,
    "high": 12000000
  },
  "market_trend": "bullish",
  "price_change_3m": "+5.2%",
  "inventory": 234
}
```

---

## 🛡️ Fraud Detection Endpoints

### Detect Fraud in Single Listing
```
POST /api/fraud/detect

Request:
{
  "property_id": "prop_12345",
  "title": "2 BHK Flat in Mumbai",
  "description": "Beautiful apartment with amenities..."
}

Response:
{
  "trust_score": 85.5,
  "risk_level": "LOW",
  "flags": [
    "Some minor concern detected"
  ],
  "confidence": 0.85
}
```

Trust Score Breakdown:
- **85-100**: LOW RISK ✅
- **50-85**: MEDIUM RISK ⚠️
- **0-50**: HIGH RISK 🚨

### Batch Fraud Detection
```
POST /api/fraud/batch-detect
Content-Type: multipart/form-data

Body: CSV file

Response:
{
  "results": [
    {
      "listing_index": 0,
      "trust_score": 85.5,
      "risk_level": "LOW",
      "flags": []
    },
    ...
  ],
  "total": 59
}
```

---

## 🎯 Recommendation Endpoints

### Get Recommendations
```
POST /api/recommendations

Request:
{
  "budget_min": 5000000,
  "budget_max": 20000000,
  "location": "Mumbai",
  "bhk": 2,
  "amenities": ["gym", "security"]
}

Response:
{
  "listings": [
    {
      "id": "property_0",
      "title": "Premium 2 BHK Property",
      "location": "Mumbai, Ghatkopar",
      "price": 8500000,
      "bhk": 2,
      "size": 850,
      "amenities": ["gym", "parking", "security"],
      "match_score": 92.5,
      "match_reasons": [
        "Within budget",
        "Exact location match",
        "2 BHK as requested",
        "3/2 amenities match"
      ]
    },
    ...
  ],
  "count": 15
}
```

### Get Trending Properties
```
GET /api/recommendations/trending

Response:
{
  "listings": [
    {
      "id": "property_5",
      "title": "Luxury Apartment",
      "location": "Mumbai",
      "price": 12000000,
      "views": 4500,
      "rating": 4.8
    },
    ...
  ]
}
```

---

## 🤖 GenAI Endpoints

### Generate Description
```
POST /api/genai/describe

Request:
{
  "title": "2 BHK Apartment",
  "location": "Mumbai",
  "bhk": 2,
  "size": 850,
  "amenities": ["gym", "pool", "parking"]
}

Response:
{
  "description": "🏡 Stunning 2 BHK Property in Mumbai\n\nExperience luxury living in this 850 sq ft spacious apartment...[enhanced description]"
}
```

### Explain Price
```
POST /api/genai/explain-price

Request:
{
  "location": "Mumbai",
  "bhk": 2,
  "size": 850,
  "amenities": ["gym", "pool"]
}

Response:
{
  "explanation": "💰 Here's why the price makes sense:\n\n• **Location**: Mumbai is 🔥 - great connectivity\n• **Size**: 850 sq ft = plenty of space\n• **2 BHK**: More value\n• **Amenities**: Great bonus features"
}
```

### Chat with Advisor
```
POST /api/genai/chat

Request:
{
  "message": "What's a fair price for 2BHK in Mumbai?"
}

Response:
{
  "response": "💡 Price Questions:\n- Properties in Mumbai average ₹1.5-3 Cr...[detailed response]"
}
```

---

## 📊 Data Management Endpoints

### Upload Listings
```
POST /api/data/upload-listings
Content-Type: multipart/form-data

Body: CSV file

Response:
{
  "message": "Listings uploaded successfully",
  "count": 59,
  "data": [
    {
      "id": "h1_0",
      "title": "Property Title",
      "location": "Mumbai",
      ...
    },
    ...
  ]
}
```

### Get All Listings
```
GET /api/data/listings?location=Mumbai&limit=20

Response:
{
  "listings": [...],
  "count": 20
}
```

### Get All Locations
```
GET /api/data/locations

Response:
{
  "locations": ["Mumbai", "Bangalore", "Delhi", "Pune", ...]
}
```

---

## 📊 Error Responses

### Bad Request (400)
```json
{
  "detail": "Invalid input parameters"
}
```

### Not Found (404)
```json
{
  "detail": "Resource not found"
}
```

### Internal Server Error (500)
```json
{
  "detail": "Internal server error"
}
```

---

## 🔑 Request Headers

All POST requests should include:
```
Content-Type: application/json
```

For file uploads:
```
Content-Type: multipart/form-data
```

---

## 📝 Query Parameters

### Pagination (planned)
```
GET /api/data/listings?limit=20&offset=0
```

### Filtering
```
GET /api/data/listings?location=Mumbai&bhk=2
```

---

## 🧱 Floorplan Generator Endpoint

Constraint-based floorplan generation using room sequencing and adjacency constraints.

### Generate Floorplans
```
POST /api/floorplan/generate

Content-Type: application/json

Request:
{
  "total_area": 2000,
  "max_plans": 20,
  "rooms": [
    {"name": "Lounge Area", "size": 600, "quantity": 1},
    {"name": "Kitchen", "size": 120, "quantity": 1},
    {"name": "Master Bedroom (with bathroom)", "size": 220, "quantity": 1}
  ],
  "constraints": [
    {"room1": "Kitchen", "room2": "Master Bedroom (with bathroom)"}
  ]
}

Response:
{
  "success": true,
  "total_area": 2000,
  "selected_area": 940,
  "unused_area": 1060,
  "generated_plans": 20,
  "constraints_used": 1,
  "plans": [
    {
      "room_order": ["Lounge Area", "Kitchen", "Master Bedroom (with bathroom)"],
      "room_count": 3
    }
  ],
  "message": "Floorplans generated successfully",
  "error": null
}
```

### cURL
```bash
curl -X POST http://localhost:8000/api/floorplan/generate \
  -H "Content-Type: application/json" \
  -d '{
    "total_area": 2000,
    "max_plans": 20,
    "rooms": [
      {"name": "Lounge Area", "size": 600, "quantity": 1},
      {"name": "Kitchen", "size": 120, "quantity": 1}
    ],
    "constraints": [
      {"room1": "Kitchen", "room2": "Master Bedroom (with bathroom)"}
    ]
  }'
```

---

## 💡 Example Usage (Original)

### Python (requests)
```python
import requests

# Price prediction
response = requests.post(
  'http://localhost:8000/api/price/predict',
  json={
    'location': 'Mumbai',
    'bhk': 2,
    'size': 850,
    'amenities': ['gym', 'pool']
  }
)
print(response.json())
```

### JavaScript (fetch)
```javascript
const response = await fetch('http://localhost:8000/api/price/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    location: 'Mumbai',
    bhk: 2,
    size: 850,
    amenities: ['gym', 'pool']
  })
});
const data = await response.json();
```

### cURL
```bash
curl -X POST http://localhost:8000/api/price/predict \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Mumbai",
    "bhk": 2,
    "size": 850,
    "amenities": ["gym", "pool"]
  }'
```

---

## 📈 Rate Limiting (Future)

Currently unlimited. Will implement:
- 100 requests/minute per IP
- 1000 requests/hour per API key
- Burst limit: 10 requests/second

---

## 🔒 Security (Future)

- [ ] API key authentication
- [ ] JWT tokens
- [ ] HTTPS enforcement
- [ ] Input validation
- [ ] CORS security
- [ ] Rate limiting
- [ ] DDoS protection

---

**API Version**: 1.0.0
**Last Updated**: February 6, 2026
**Status**: MVP Complete
