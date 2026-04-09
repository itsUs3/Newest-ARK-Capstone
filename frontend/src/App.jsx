import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { Toaster } from 'react-hot-toast'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import Home from './pages/Home'
import Search from './pages/Search'
import PropertyDetail from './pages/PropertyDetail'
import PriceAnalyzer from './pages/PriceAnalyzer'
import FraudDetector from './pages/FraudDetector'
import AdvisorChat from './pages/AdvisorChat'
import LocationBooster from './pages/LocationBooster'
import AmenityMatcher from './pages/AmenityMatcher'
import VastuChecker from './pages/VastuChecker'
import InvestmentAnalyzer from './pages/InvestmentAnalyzer'
import MarketNews from './pages/MarketNews'
import ContractAnalyzer from './pages/ContractAnalyzer'
import Social from './pages/Social'

class RouteErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || 'Unknown error' }
  }

  componentDidCatch(error) {
    console.error('Route render error:', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 text-slate-200">
          <h3 className="text-lg font-semibold mb-2">Unable to load this page</h3>
          <p className="text-sm text-slate-400 mb-2">A runtime error occurred in this module.</p>
          <p className="text-xs text-slate-500">{this.state.message}</p>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-900 flex flex-col">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<Search />} />
            <Route path="/property/:id" element={<PropertyDetail />} />
            <Route path="/price-analyzer" element={<PriceAnalyzer />} />
            <Route path="/fraud-detector" element={<FraudDetector />} />
            <Route path="/advisor" element={<AdvisorChat />} />
            <Route path="/investment-analyzer" element={<InvestmentAnalyzer />} />
            <Route path="/location-booster" element={<LocationBooster />} />
            <Route path="/amenity-matcher" element={<AmenityMatcher />} />
            <Route path="/vastu-checker" element={<VastuChecker />} />
            <Route path="/social" element={<Social />} />
            <Route path="/market-news" element={<MarketNews />} />
            <Route path="/contract-analyzer" element={<ContractAnalyzer />} />
          </Routes>
        </main>
        <Footer />
        <Toaster position="top-right" />
      </div>
    </Router>
  )
}

export default App
