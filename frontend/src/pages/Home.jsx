import { motion } from 'framer-motion'
import { FiTrendingUp, FiCheck, FiAlertCircle, FiUsers, FiSearch, FiArrowRight } from 'react-icons/fi'
import { Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'

export default function Home() {
  const navigate = useNavigate()
  const [trendingLocations, setTrendingLocations] = useState([])
  const [crossModalQuery, setCrossModalQuery] = useState('')
  const [crossModalResults, setCrossModalResults] = useState(null)
  const [crossModalLoading, setCrossModalLoading] = useState(false)
  const [selectedLifestyle, setSelectedLifestyle] = useState(null)

  const lifestyleOptions = [
    { name: 'Family with Kids', icon: '👨‍👩‍👧‍👦' },
    { name: 'Young Professional', icon: '💼' },
    { name: 'Fitness Enthusiast', icon: '🏋️' },
    { name: 'Luxury Living', icon: '✨' },
    { name: 'Work From Home', icon: '💻' },
    { name: 'Retired Couple', icon: '🌳' }
  ]

  useEffect(() => {
    // Fetch trending locations
    fetch('http://localhost:8000/api/genai/trending-locations?top_n=5')
      .then(res => res.json())
      .then(data => setTrendingLocations(data.trending_locations || []))
      .catch(err => console.error('Error fetching trending locations:', err))
  }, [])

  const triggerSearch = async (query, lifestyle = null) => {
    setCrossModalLoading(true)
    try {
      const requestBody = {
        query: query,
        lifestyle: lifestyle,
        top_k: 6,
        use_cross_modal: true
      }
      console.log('🔍 Sending search request:', requestBody)
      
      const response = await fetch('http://localhost:8000/api/genai/cross-modal-match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        console.error('API returned status:', response.status)
        throw new Error(`Search failed with status ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ Search response:', data)
      setCrossModalResults(data)
    } catch (error) {
      console.error('❌ Cross-modal search error:', error)
      setCrossModalResults({
        error: error.message || 'Search failed. Please try again.',
        matches: []
      })
    } finally {
      setCrossModalLoading(false)
    }
  }

  const handleCrossModalSearch = async (e) => {
    e.preventDefault()
    
    // If only lifestyle selected but no custom query, auto-generate one
    let finalQuery = crossModalQuery
    if (!finalQuery.trim() && selectedLifestyle) {
      // Use the lifestyle as the query and let backend optimize it
      finalQuery = selectedLifestyle
    }
    
    if (!finalQuery.trim()) {
      alert('Please enter a search query or select a lifestyle')
      return
    }

    await triggerSearch(finalQuery, selectedLifestyle)
  }

  const features = [
    {
      icon: <FiTrendingUp className="text-3xl" />,
      title: 'Smart Price Prediction',
      description: 'ML-powered price analysis to identify fair market value and spot overpriced listings',
      color: 'from-blue-500 to-cyan-500'
    },
    {
      icon: <FiCheck className="text-3xl" />,
      title: 'Fraud Detection',
      description: 'AI detects duplicate listings, fake properties, and scam indicators with trust scoring',
      color: 'from-green-500 to-emerald-500'
    },
    {
      icon: <FiAlertCircle className="text-3xl" />,
      title: 'Unified Search',
      description: 'Search across MagicBricks, 99acres, Housing.com all in one seamless interface',
      color: 'from-purple-500 to-pink-500'
    },
    {
      icon: <FiUsers className="text-3xl" />,
      title: 'AI Advisor',
      description: 'Chat with our Gen Z-friendly AI advisor for real estate guidance and market insights',
      color: 'from-orange-500 to-red-500'
    }
  ]

  const stats = [
    { number: '5000+', label: 'Properties Analyzed' },
    { number: '95%', label: 'Fraud Detection Rate' },
    { number: '10x', label: 'Faster Search' },
    { number: '₹XXL', label: 'Value Identified' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900">
      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h1 className="text-6xl md:text-7xl font-black font-display gradient-text mb-6">
            Real Estate,<br /> Reimagined ✨
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-10">
            Stop searching across 10+ websites. Stop getting scammed. Stop overpaying.<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-pink-400">
              myNivas finds the real deal.
            </span>
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/search" className="btn-primary">
              🔍 Start Searching
            </Link>
            <button className="btn-secondary">
              📚 Learn More
            </button>
          </div>
        </motion.div>

        {/* Cross-Modal Smart Search Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="mb-20"
        >
          <div className="glass-effect p-8 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-cyan-500/10 border border-indigo-500/20">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center">
                <FiSearch className="text-white text-lg" />
              </div>
              <h3 className="text-2xl font-bold text-white">Smart Property Discovery</h3>
              <span className="ml-auto px-3 py-1 bg-indigo-500/30 rounded-full text-xs font-semibold text-indigo-200">NEW</span>
            </div>
            
            <p className="text-slate-300 mb-6">
              Find properties using natural language. Tell us what you're looking for, and our AI will search across all major platforms with stunning visual montages.
            </p>

            <form onSubmit={handleCrossModalSearch} className="space-y-4">
              {/* Lifestyle Quick Filters */}
              <div className="mb-4">
                <p className="text-slate-400 text-sm mb-3">Or choose a lifestyle:</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {lifestyleOptions.map((lifestyle, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        const isSelected = selectedLifestyle === lifestyle.name
                        setSelectedLifestyle(isSelected ? null : lifestyle.name)
                        setCrossModalQuery('')
                        
                        // Auto-trigger search for lifestyle
                        if (!isSelected) {
                          // Defer the search to next event loop
                          setTimeout(() => {
                            triggerSearch(lifestyle.name)
                          }, 0)
                        }
                      }}
                      className={`p-3 rounded-lg font-medium transition-all ${
                        selectedLifestyle === lifestyle.name
                          ? 'bg-indigo-500 text-white'
                          : 'glass-effect text-slate-300 hover:bg-slate-700/50'
                      }`}
                    >
                      {lifestyle.icon} {lifestyle.name.split(' ')[0]}
                    </button>
                  ))}
                </div>
              </div>

              {/* Search Input */}
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder='e.g., "Affordable sea-view flat with gym near Mumbai"'
                  value={crossModalQuery}
                  onChange={(e) => setCrossModalQuery(e.target.value)}
                  className="flex-1 px-4 py-3 w-full bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                <button
                  type="submit"
                  disabled={crossModalLoading}
                  className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-lg font-semibold text-white hover:shadow-lg hover:shadow-indigo-500/50 disabled:opacity-50 transition-all"
                >
                  {crossModalLoading ? '🔄' : '🚀'} Search
                </button>
              </div>
            </form>

            {/* Results Display */}
            {crossModalResults && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8 pt-8 border-t border-slate-700"
              >
                {crossModalResults.error ? (
                  <div className="text-red-400 p-4 bg-red-500/10 rounded-lg">
                    <p>❌ {crossModalResults.error}</p>
                  </div>
                ) : crossModalResults.matches && crossModalResults.matches.length > 0 ? (
                  <>
                    <p className="text-slate-400 text-sm mb-4">
                      Found {crossModalResults.matches.length} matching properties{selectedLifestyle && ` for ${selectedLifestyle}`}
                    </p>

                    {/* Visual Montage */}
                    {crossModalResults.montage && (
                      <div className="mb-6 rounded-xl overflow-hidden border border-slate-700">
                        <img 
                          src={crossModalResults.montage} 
                          alt="Property montage" 
                          className="w-full max-h-96 object-cover"
                        />
                      </div>
                    )}

                    {/* Property Cards Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {crossModalResults.matches.map((prop, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          onClick={() => navigate('/property', { state: { property: prop } })}
                          className="relative glass-effect p-4 rounded-xl card-hover border border-slate-700 cursor-pointer hover:border-indigo-500 hover:shadow-lg hover:shadow-indigo-500/30 transition-all duration-300 overflow-hidden"
                        >
                          {/* Arrow Icon - Top Right */}
                          <div className="absolute top-3 right-3 text-slate-500 group-hover:text-indigo-400 transition-colors duration-300">
                            <FiArrowRight size={20} />
                          </div>
                          
                          <h4 className="font-bold text-white mb-2 line-clamp-2 group-hover:text-indigo-300 pr-6">{prop.name}</h4>
                          <p className="text-sm text-slate-400 mb-3">{prop.address}</p>
                          <div className="flex justify-between items-end">
                            <div>
                              {prop.price && <p className="font-bold text-indigo-200">₹{prop.price}</p>}
                              {prop.similarity_score !== undefined && (
                                <p className="text-xs text-slate-500">Match: {(prop.similarity_score * 100).toFixed(0)}%</p>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-slate-400 p-4 text-center">
                    <p>😕 No properties found for your search</p>
                    <p className="text-sm mt-2">Try adjusting your search query or selecting a different lifestyle</p>
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-20"
        >
          {stats.map((stat, i) => (
            <div key={i} className="glass-effect p-6 text-center rounded-xl card-hover">
              <p className="text-3xl font-bold gradient-text">{stat.number}</p>
              <p className="text-slate-400 text-sm mt-2">{stat.label}</p>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          className="text-4xl font-bold text-center gradient-text mb-16"
        >
          Why myNivas? 🤔
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`glass-effect p-8 rounded-2xl card-hover bg-gradient-to-br ${feature.color}/10`}
            >
              <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center text-white mb-4`}>
                {feature.icon}
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">{feature.title}</h3>
              <p className="text-slate-300">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Trending Locations Section */}
      {trendingLocations.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            className="text-center mb-12"
          >
            <h2 className="text-4xl font-bold gradient-text mb-4 flex items-center justify-center gap-3">
              <FiTrendingUp className="text-indigo-400" />
              📰 Trending Market News
            </h2>
            <p className="text-lg text-slate-300 max-w-2xl mx-auto">
              AI-powered insights on locations with the most market activity and infrastructure developments
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            {trendingLocations.map((loc, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="glass-effect p-6 rounded-xl text-center card-hover"
              >
                <div className="text-3xl font-bold gradient-text mb-2">
                  #{i + 1}
                </div>
                <div className="text-xl font-semibold text-white mb-2">
                  {loc.location}
                </div>
                <div className="text-sm text-slate-400 mb-2">
                  {loc.news_count} articles
                </div>
                <div className={`px-3 py-1 rounded-full text-xs font-semibold inline-block ${
                  loc.avg_impact >= 0.7 ? 'bg-green-500' : 
                  loc.avg_impact >= 0.5 ? 'bg-blue-500' : 'bg-slate-500'
                }`}>
                  {(loc.avg_impact * 100).toFixed(0)}% Impact
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            className="text-center"
          >
            <Link to="/market-news" className="btn-primary inline-block">
              View All Market News →
            </Link>
          </motion.div>
        </section>
      )}

      {/* CTA Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          className="glass-effect p-12 rounded-2xl text-center bg-gradient-to-r from-indigo-500/20 to-pink-500/20"
        >
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to find your dream home? 🏡
          </h2>
          <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
            Join thousands of Indians who've stopped wasting time and money on property searches.
          </p>
          <Link to="/search" className="btn-primary inline-block">
            Search Now →
          </Link>
        </motion.div>
      </section>
    </div>
  )
}
