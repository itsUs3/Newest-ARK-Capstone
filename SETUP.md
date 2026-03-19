# Setup Guide - myNivas

## Complete Installation & Run Instructions

### Step 1: Clone/Setup Project

```bash
cd "c:\Users\adity\Downloads\Aditya\College\Sem 8\Capstone\myNivas"
```

## Backend Setup (Python)

### Step 2A: Virtual Environment

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 2B: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2C: Download Required NLTK Data (for fraud detector)

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

### Step 2D: Run Backend

```bash
python main.py
```

✅ Backend ready at: **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Frontend Setup (React)

### Step 3A: Install Dependencies

Open a new terminal in project root:

```bash
cd frontend
npm install
```

**First time? This takes 2-3 minutes**

### Step 3B: Run Frontend

```bash
npm run dev
```

✅ Frontend ready at: **http://localhost:3000**

---

## 🎉 Both Running?

Open in browser:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000/docs

## ⚡ Features Ready to Test

### 1. Home Page (http://localhost:3000)
- Hero section with gradient text
- Feature cards
- Call-to-action buttons

### 2. Search Properties (http://localhost:3000/search)
- Filter by location, BHK, price
- View recommendations with match scores
- Property cards with trust badges

### 3. Price Analyzer (http://localhost:3000/price-analyzer)
- Predict fair prices
- View price ranges
- See contributing factors
- Market trend charts

### 4. Fraud Detector (http://localhost:3000/fraud-detector)
- Analyze listings for scams
- Trust score calculation
- Red flags detection
- Safety tips

### 5. AI Advisor (http://localhost:3000/advisor)
- Chat with property AI
- Ask about prices, locations, scams
- Gen Z friendly responses
- Suggested questions

## 🔧 Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Kill the process or use different port:
python main.py --port 8001
```

**ModuleNotFoundError:**
```bash
# Make sure virtual environment is activated
# Re-run: pip install -r requirements.txt
```

**CSV not found:**
```bash
# Ensure Housing1.csv is in backend/ folder
# Backend reads from: Housing1.csv (relative path)
```

### Frontend Issues

**npm install errors:**
```bash
# Clear cache and retry
npm cache clean --force
rm -rf node_modules
npm install
```

**Port 3000 in use:**
```bash
# Change in vite.config.js or run on different port
npm run dev -- --port 3001
```

**Blank page/API errors:**
```bash
# Check backend is running on 8000
# Check browser console (F12) for errors
# Verify CORS is enabled in main.py
```

## 📊 Data

Using **Housing1.csv** with 59 properties:
- Primarily Mumbai properties
- Housing.com data source
- Parsed: Location, BHK, Price (synthetic), Amenities

**To use different dataset:**
1. Place CSV in `backend/` folder
2. Update data processor path in `main.py`
3. Models will auto-train on new data

## 🎯 API Testing with Postman

Import base URL: `http://localhost:8000`

**Test Endpoints:**

1. **Get Price Prediction**
   ```
   POST /api/price/predict
   Body: {
     "location": "Mumbai",
     "bhk": 2,
     "size": 850,
     "amenities": ["gym", "pool"]
   }
   ```

2. **Test Fraud Detection**
   ```
   POST /api/fraud/detect
   Body: {
     "property_id": "test_123",
     "title": "2 BHK in Mumbai",
     "description": "Beautiful apartment"
   }
   ```

3. **Get Recommendations**
   ```
   POST /api/recommendations
   Body: {
     "budget_min": 5000000,
     "budget_max": 20000000,
     "location": "Mumbai",
     "bhk": 2,
     "amenities": ["gym"]
   }
   ```

## 🎨 Customization

### Change Colors
Edit `frontend/tailwind.config.js`:
```javascript
colors: {
  primary: '#6366f1',    // Change primary color
  secondary: '#ec4899',  // Change secondary
  accent: '#14b8a6',     // Change accent
}
```

### Modify ML Models
Edit `backend/models/price_predictor.py`:
- Change model type (SVR, GradientBoosting, etc.)
- Adjust hyperparameters
- Add new features

### Add New Features
1. Backend: Add endpoint in `backend/main.py`
2. Frontend: Create page in `frontend/src/pages/`
3. Connect with axios calls from `frontend/src/utils/api.js`

## 📦 Production Build

### Frontend
```bash
cd frontend
npm run build
# Creates optimized build in dist/
```

### Backend
```bash
# Use gunicorn for production
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

## 🚀 Deploy to Heroku

```bash
# Backend
heroku create mynivas-backend
git subtree push --prefix backend heroku main

# Frontend  
npm run build
# Deploy dist/ to Vercel or Netlify
```

## 📚 Key Files to Know

- **Backend Entry**: `backend/main.py` - All endpoints
- **ML Models**: `backend/models/*.py` - AI/ML logic
- **Frontend Root**: `frontend/src/App.jsx` - Routes setup
- **Styles**: `frontend/src/index.css` - Global CSS
- **API Config**: `frontend/src/utils/api.js` - API calls

## ✅ Verification Checklist

- [ ] Backend running (localhost:8000)
- [ ] Frontend running (localhost:3000)
- [ ] API docs accessible (localhost:8000/docs)
- [ ] No console errors
- [ ] Search page loads properties
- [ ] Price analyzer works
- [ ] Fraud detector analyzes
- [ ] Chat works (if OpenAI key set)

## 🎓 Next Steps

1. **Collect More Data**: Add real properties from CSV
2. **Train Better Models**: Use larger datasets
3. **Add Authentication**: User accounts & saved properties
4. **Mobile App**: React Native version
5. **Database**: Migrate to PostgreSQL for production
6. **Real API Keys**: Set OPENAI_API_KEY in `.env`

## 💬 Questions?

Check documentation in:
- `README.md` - Overview
- `backend/main.py` - API documentation
- Individual files - Code comments
- Browser DevTools (F12) - Frontend errors

---

**You're all set! Happy coding! 🚀**

Start with visiting: http://localhost:3000
