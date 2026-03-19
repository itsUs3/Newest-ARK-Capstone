import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiTrendingUp, FiMapPin, FiCalendar, FiExternalLink, FiSearch, FiAlertCircle, FiBarChart2, FiActivity, FiChevronDown, FiChevronUp } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, Legend, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, AreaChart, Area } from 'recharts'

export default function MarketNews() {
  const [trendingLocations, setTrendingLocations] = useState([])
  const [selectedLocation, setSelectedLocation] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [marketAlert, setMarketAlert] = useState(null)
  const [loading, setLoading] = useState(false)
  const [trendingLoading, setTrendingLoading] = useState(true)
  const [expandedArticles, setExpandedArticles] = useState({})
  const [viewMode, setViewMode] = useState('grid') // 'grid' or 'chart'

  // Fetch trending locations on mount
  useEffect(() => {
    fetchTrendingLocations()
  }, [])

  const fetchTrendingLocations = async () => {
    try {
      setTrendingLoading(true)
      const response = await fetch('http://localhost:8000/api/genai/trending-locations?top_n=10')
      const data = await response.json()
      setTrendingLocations(data.trending_locations || [])
    } catch (error) {
      console.error('Error fetching trending locations:', error)
      toast.error('Failed to load trending locations')
    } finally {
      setTrendingLoading(false)
    }
  }

  const fetchMarketAlert = async (location, query = '') => {
    if (!location) return

    try {
      setLoading(true)
      const url = query 
        ? `http://localhost:8000/api/genai/market-alerts/${encodeURIComponent(location)}?query=${encodeURIComponent(query)}&n_results=5`
        : `http://localhost:8000/api/genai/market-alerts/${encodeURIComponent(location)}?n_results=5`
      
      const response = await fetch(url)
      const data = await response.json()
      setMarketAlert(data)
      setSelectedLocation(location)
    } catch (error) {
      console.error('Error fetching market alert:', error)
      toast.error('Failed to load market news')
    } finally {
      setLoading(false)
    }
  }

  const toggleArticle = (index) => {
    setExpandedArticles(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (selectedLocation) {
      fetchMarketAlert(selectedLocation, searchQuery)
    } else {
      toast.error('Please select or enter a location')
    }
  }

  const getImpactColor = (level) => {
    switch (level) {
      case 'high_positive':
        return 'from-green-500 to-emerald-500'
      case 'moderate_positive':
        return 'from-blue-500 to-cyan-500'
      case 'neutral':
        return 'from-slate-500 to-gray-500'
      case 'negative':
        return 'from-red-500 to-rose-500'
      default:
        return 'from-purple-500 to-pink-500'
    }
  }

  const getImpactBadge = (level) => {
    switch (level) {
      case 'high_positive':
        return { text: 'High Growth', color: 'bg-green-500' }
      case 'moderate_positive':
        return { text: 'Moderate Growth', color: 'bg-blue-500' }
      case 'neutral':
        return { text: 'Stable', color: 'bg-slate-500' }
      case 'negative':
        return {text: 'Caution', color: 'bg-red-500' }
      default:
        return { text: 'Unknown', color: 'bg-purple-500' }
    }
  }

  const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#14b8a6']

  // Prepare data for charts
  const trendingChartData = trendingLocations.map(loc => ({
    name: loc.location.length > 10 ? loc.location.substring(0, 10) + '...' : loc.location,
    fullName: loc.location,
    news: loc.news_count,
    impact: (loc.avg_impact * 100).toFixed(0),
    score: loc.trend_score
  }))

  const impactDistribution = marketAlert?.articles?.reduce((acc, article) => {
    const range = article.impact_score >= 0.7 ? 'High (70-100%)' :
                  article.impact_score >= 0.5 ? 'Moderate (50-70%)' :
                  article.impact_score >= 0.3 ? 'Low (30-50%)' : 'Very Low (0-30%)'
    acc[range] = (acc[range] || 0) + 1
    return acc
  }, {})

  const impactChartData = impactDistribution ? Object.entries(impactDistribution).map(([name, value]) => ({
    name, value
  })) : []

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl font-bold gradient-text mb-4">
            📰 Market News & Trends
          </h1>
          <p className="text-xl text-slate-300 max-w-3xl mx-auto">
            AI-powered market insights using RAG technology. Get real-time alerts about infrastructure developments, 
            metro projects, and market trends affecting property values.
          </p>
        </motion.div>

        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-12"
        >
          <form onSubmit={handleSearch} className="glass-effect p-6 rounded-2xl">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <FiMapPin className="inline mr-2" />
                  Location
                </label>
                <input
                  type="text"
                  value={selectedLocation}
                  onChange={(e) => setSelectedLocation(e.target.value)}
                  placeholder="e.g., Mumbai, Andheri, Bangalore"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  <FiSearch className="inline mr-2" />
                  Specific Query (Optional)
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g., metro, airport, infrastructure"
                  className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={loading || !selectedLocation}
                  className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '⏳ Loading...' : '🔍 Get Market Insights'}
                </button>
              </div>
            </div>
          </form>
        </motion.div>

        {/* Trending Locations */}
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ delay: 0.2 }}
            className="mb-12"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-white flex items-center gap-2">
                <FiTrendingUp className="text-indigo-400" />
                Trending Locations
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`px-4 py-2 rounded-lg transition-all ${
                    viewMode === 'grid' 
                      ? 'bg-indigo-600 text-white' 
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  Grid View
                </button>
                <button
                  onClick={() => setViewMode('chart')}
                  className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${
                    viewMode === 'chart' 
                      ? 'bg-indigo-600 text-white' 
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  <FiBarChart2 /> Chart View
                </button>
              </div>
            </div>

            {trendingLoading ? (
              <div className="glass-effect p-8 rounded-2xl text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
                <p className="text-slate-400">Loading trending locations...</p>
              </div>
            ) : viewMode === 'chart' ? (
              <div className="glass-effect p-6 rounded-2xl">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Bar Chart */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">News Volume by Location</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={trendingChartData.slice(0, 8)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                        <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                          labelStyle={{ color: '#f1f5f9' }}
                        />
                        <Bar dataKey="news" fill="#6366f1" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Impact Score Chart */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Impact Score Distribution</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={trendingChartData.slice(0, 8)}>
                        <defs>
                          <linearGradient id="colorImpact" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                        <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                          labelStyle={{ color: '#f1f5f9' }}
                        />
                        <Area type="monotone" dataKey="impact" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorImpact)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Pie Chart */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Market Share</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={trendingChartData.slice(0, 5)}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                          outerRadius={100}
                          fill="#8884d8"
                          dataKey="news"
                        >
                          {trendingChartData.slice(0, 5).map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Trend Score Radar */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Trend Score Analysis</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <RadarChart data={trendingChartData.slice(0, 6)}>
                        <PolarGrid stroke="#475569" />
                        <PolarAngleAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                        <PolarRadiusAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                        <Radar name="Trend Score" dataKey="score" stroke="#ec4899" fill="#ec4899" fillOpacity={0.6} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {trendingLocations.map((loc, index) => (
                  <motion.button
                    key={index}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => fetchMarketAlert(loc.location)}
                    className="glass-effect p-4 rounded-xl hover:bg-slate-700 hover:scale-105 transition-all duration-300 text-left relative overflow-hidden group"
                  >
                    {/* Animated background gradient */}
                    <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    
                    <div className="relative z-10">
                      <div className="text-2xl font-bold gradient-text mb-1">
                        #{index + 1}
                      </div>
                      <div className="text-lg font-semibold text-white mb-2">
                        {loc.location}
                      </div>
                      
                      {/* Mini sparkline chart */}
                      <div className="h-8 mb-2">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={[
                            { value: Math.random() * loc.news_count },
                            { value: Math.random() * loc.news_count },
                            { value: loc.news_count }
                          ]}>
                            <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-300 font-medium">{loc.news_count} news</span>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          loc.avg_impact >= 0.7 ? 'bg-green-500' : 
                          loc.avg_impact >= 0.5 ? 'bg-blue-500' : 'bg-slate-500'
                        }`}>
                          {(loc.avg_impact * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Market Alert Results */}
        {marketAlert && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Alert Summary Card */}
            <div className={`glass-effect p-8 rounded-2xl bg-gradient-to-r ${getImpactColor(marketAlert.impact_level)} bg-opacity-10 border-2 border-opacity-20 ${
              marketAlert.impact_level === 'high_positive' ? 'border-green-500' :
              marketAlert.impact_level === 'moderate_positive' ? 'border-blue-500' :
              marketAlert.impact_level === 'neutral' ? 'border-slate-500' : 'border-red-500'
            }`}>
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h3 className="text-3xl font-bold text-white mb-2">
                    {marketAlert.location}
                  </h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getImpactBadge(marketAlert.impact_level).color}`}>
                      {getImpactBadge(marketAlert.impact_level).text}
                    </span>
                    <span className="text-slate-400 text-sm">
                      Impact Score: <span className="text-white font-bold">{(marketAlert.avg_impact_score * 100).toFixed(0)}%</span>
                    </span>
                    <span className="text-slate-400 text-sm flex items-center gap-1">
                      <FiActivity className="text-indigo-400" />
                      {marketAlert.articles?.length || 0} Articles
                    </span>
                  </div>
                </div>
                <motion.div
                  animate={{ rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
                >
                  <FiAlertCircle className="text-5xl text-indigo-400" />
                </motion.div>
              </div>
              
              {/* Impact Distribution Chart (if articles exist) */}
              {impactChartData.length > 0 && (
                <div className="mb-6 glass-effect p-4 rounded-xl bg-slate-800 bg-opacity-30">
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <FiBarChart2 className="text-indigo-400" />
                    Impact Distribution
                  </h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={impactChartData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis type="number" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                      <YAxis type="category" dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                      />
                      <Bar dataKey="value" fill="#6366f1" radius={[0, 8, 8, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              
              <div className="bg-slate-800 bg-opacity-50 p-4 rounded-lg mb-4">
                <pre className="text-slate-200 whitespace-pre-wrap font-sans">
                  {marketAlert.alert_summary}
                </pre>
              </div>

              <div className="bg-indigo-900 bg-opacity-30 p-4 rounded-lg border border-indigo-500 border-opacity-30">
                <h4 className="text-sm font-semibold text-indigo-300 mb-2">💡 AI Recommendation</h4>
                <p className="text-white">{marketAlert.recommendation}</p>
              </div>
            </div>

            {/* News Articles */}
            {marketAlert.articles && marketAlert.articles.length > 0 ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                    📄 Latest News Articles ({marketAlert.articles.length})
                    {searchQuery && (
                      <span className="text-sm text-slate-400 font-normal">
                        matching "{searchQuery}"
                      </span>
                    )}
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {marketAlert.articles.map((article, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="glass-effect p-6 rounded-xl hover:shadow-2xl hover:shadow-indigo-500/20 transition-all duration-300 cursor-pointer border border-slate-700 hover:border-indigo-500"
                      onClick={() => toggleArticle(index)}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex gap-2 flex-wrap">
                          <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            article.impact_score >= 0.7 ? 'bg-green-500' :
                            article.impact_score >= 0.5 ? 'bg-blue-500' :
                            article.impact_score >= 0.3 ? 'bg-slate-500' : 'bg-red-500'
                          }`}>
                            Impact: {(article.impact_score * 100).toFixed(0)}%
                          </div>
                        </div>
                        <motion.div
                          animate={{ rotate: expandedArticles[index] ? 180 : 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          {expandedArticles[index] ? <FiChevronUp className="text-indigo-400" /> : <FiChevronDown className="text-slate-400" />}
                        </motion.div>
                      </div>

                      <h4 className="text-lg font-semibold text-white mb-3 line-clamp-2">
                        {article.title}
                      </h4>

                      <AnimatePresence>
                        {expandedArticles[index] ? (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3 }}
                          >
                            <p className="text-slate-300 text-sm mb-4">
                              {article.content}
                            </p>
                          </motion.div>
                        ) : (
                          <p className="text-slate-300 text-sm mb-4 line-clamp-3">
                            {article.content}
                          </p>
                        )}
                      </AnimatePresence>

                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="flex items-center gap-1">
                            <FiCalendar />
                            {new Date(article.date).toLocaleDateString()}
                          </span>
                          <span className="text-indigo-400">{article.source}</span>
                        </div>
                        {article.url && (
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Read <FiExternalLink />
                          </a>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            ) : marketAlert && (
              <div className="glass-effect p-12 rounded-2xl text-center border-2 border-yellow-500/30">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-xl font-bold text-white mb-2">
                  No Articles Found
                </h3>
                <p className="text-slate-400 mb-4">
                  {searchQuery 
                    ? `No news articles found matching "${searchQuery}" in ${selectedLocation}`
                    : `No recent news articles found for ${selectedLocation}`}
                </p>
                <p className="text-sm text-slate-500">
                  Try a different location or search query, or remove the specific query to see general news.
                </p>
              </div>
            )}
          </motion.div>
        )}

        {/* Empty State */}
        {!marketAlert && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-effect p-16 rounded-2xl text-center"
          >
            <motion.div 
              className="text-8xl mb-6"
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              📍
            </motion.div>
            <h3 className="text-2xl font-bold text-white mb-2">
              Select a Location to Get Started
            </h3>
            <p className="text-slate-400 mb-6">
              Click on a trending location or search for any city/area to see market news and insights
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {['Mumbai', 'Bangalore', 'Pune', 'Delhi', 'Hyderabad'].map((city) => (
                <motion.button
                  key={city}
                  onClick={() => fetchMarketAlert(city)}
                  className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 rounded-lg text-white font-semibold transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {city}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
