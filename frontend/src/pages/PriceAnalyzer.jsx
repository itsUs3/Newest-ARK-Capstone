import { useState } from 'react'
import { motion } from 'framer-motion'
import { FiTrendingUp, FiMapPin, FiHome, FiSquare } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { predictPrice } from '../utils/api'

const BHK_SIZE_BANDS = {
  1: { min: 450, max: 900 },
  2: { min: 750, max: 1400 },
  3: { min: 1100, max: 2000 },
  4: { min: 1600, max: 3000 },
  5: { min: 2200, max: 4200 }
}

function getBhkSizeValidation(bhk, sizeValue) {
  const size = Number(sizeValue) || 0
  const safeBhk = Math.max(1, Math.min(5, Number(bhk) || 1))
  const band = BHK_SIZE_BANDS[safeBhk]

  if (!band || size <= 0) {
    return {
      level: 'warn',
      message: 'Enter a valid size to get a realistic estimate.',
      suggestedMin: BHK_SIZE_BANDS[safeBhk]?.min || 500
    }
  }

  if (size < Math.round(band.min * 0.8)) {
    return {
      level: 'error',
      message: `${safeBhk} BHK at ${size} sq ft is too cramped for realistic market pricing. Use at least ${band.min} sq ft.`,
      suggestedMin: band.min
    }
  }

  if (size < band.min) {
    return {
      level: 'warn',
      message: `${safeBhk} BHK is usually ${band.min}+ sq ft. Your estimate may be penalized for compact layout.`,
      suggestedMin: band.min
    }
  }

  if (size > band.max) {
    return {
      level: 'warn',
      message: `${safeBhk} BHK above ${band.max} sq ft is uncommon. Expect premium variance.`,
      suggestedMin: band.min
    }
  }

  return {
    level: 'ok',
    message: `${safeBhk} BHK and ${size} sq ft look like a realistic match.`,
    suggestedMin: band.min
  }
}

export default function PriceAnalyzer() {
  const [formData, setFormData] = useState({
    location: 'Mumbai',
    bhk: 2,
    size: 1000,
    amenities: ['gym', 'parking'],
    furnishing: 'Semi-Furnished',
    construction_status: 'Ready to Move'
  })
  
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const cities = ['Mumbai', 'Bangalore', 'Delhi', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Ahmedabad']
  const amenitiesList = ['gym', 'pool', 'parking', 'garden', 'security', 'lift', 'clubhouse', 'playground']
  const furnishingOptions = ['Fully Furnished', 'Semi-Furnished', 'Unfurnished']
  const statusOptions = ['Ready to Move', 'Under Construction']
  const bhkSizeValidation = getBhkSizeValidation(formData.bhk, formData.size)
  const isSizeHardBlocked = bhkSizeValidation.level === 'error'

  const analyzPrice = async () => {
    if (isSizeHardBlocked) {
      toast.error(`Please increase size for ${formData.bhk} BHK (recommended: ${bhkSizeValidation.suggestedMin}+ sq ft).`)
      return
    }

    setLoading(true)
    try {
      const response = await predictPrice({
        location: formData.location,
        bhk: formData.bhk,
        size: formData.size,
        amenities: formData.amenities,
        furnishing: formData.furnishing,
        construction_status: formData.construction_status
      })
      setResult(response.data)
      toast.success('Price analysis complete!')
    } catch (error) {
      toast.error('Failed to analyze price')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (price) => {
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(2)} Cr`
    return `₹${(price / 100000).toFixed(1)} L`
  }

  // Mock chart data
  const chartData = [
    { month: 'Jan', price: 2800000, market: 2600000 },
    { month: 'Feb', price: 2900000, market: 2700000 },
    { month: 'Mar', price: 3000000, market: 2800000 },
    { month: 'Apr', price: 3100000, market: 2900000 },
    { month: 'May', price: 3200000, market: 3000000 },
    { month: 'Jun', price: 3300000, market: 3100000 },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-7xl mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-5xl font-bold gradient-text mb-4">💰 Smart Price Analyzer</h1>
          <p className="text-xl text-slate-300">Know the fair market value instantly</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-1"
          >
            <div className="glass-effect p-8 rounded-2xl sticky top-24">
              <h2 className="text-2xl font-bold text-white mb-6">Enter Details</h2>

              {/* Location */}
              <div className="mb-6">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-2">
                  <FiMapPin className="text-indigo-400" /> Location
                </label>
                <select
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="input-field"
                >
                  {cities.map(city => (
                    <option key={city} value={city}>{city}</option>
                  ))}
                </select>
              </div>

              {/* BHK */}
              <div className="mb-6">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-2">
                  <FiHome className="text-pink-400" /> BHK
                </label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map(bhk => (
                    <button
                      key={bhk}
                      onClick={() => setFormData({ ...formData, bhk })}
                      className={`flex-1 py-2 rounded-lg font-bold transition ${
                        formData.bhk === bhk
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {bhk}
                    </button>
                  ))}
                </div>
              </div>

              {/* Size */}
              <div className="mb-6">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-2">
                  <FiSquare className="text-teal-400" /> Size (sq ft)
                </label>
                <input
                  type="number"
                  value={formData.size}
                  onChange={(e) => setFormData({ ...formData, size: parseInt(e.target.value, 10) || 0 })}
                  className="input-field"
                  min={250}
                />
                <div className={`mt-2 rounded-lg border px-3 py-2 text-xs ${
                  bhkSizeValidation.level === 'ok'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : bhkSizeValidation.level === 'warn'
                      ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                }`}>
                  {bhkSizeValidation.message}
                </div>
                {(formData.size || 0) < (bhkSizeValidation.suggestedMin || 0) && (
                  <button
                    onClick={() => setFormData({ ...formData, size: bhkSizeValidation.suggestedMin })}
                    className="mt-2 text-xs font-semibold text-cyan-300 hover:text-cyan-200"
                  >
                    Use recommended minimum: {bhkSizeValidation.suggestedMin} sq ft
                  </button>
                )}
              </div>

              {/* Amenities */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-3">✨ Amenities</label>
                <div className="grid grid-cols-2 gap-2">
                  {amenitiesList.map(amenity => (
                    <button
                      key={amenity}
                      onClick={() => {
                        const updated = formData.amenities.includes(amenity)
                          ? formData.amenities.filter(a => a !== amenity)
                          : [...formData.amenities, amenity]
                        setFormData({ ...formData, amenities: updated })
                      }}
                      className={`px-3 py-2 rounded-lg text-sm font-semibold transition capitalize ${
                        formData.amenities.includes(amenity)
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {amenity}
                    </button>
                  ))}
                </div>
              </div>

              {/* Furnishing */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-2">🛋️ Furnishing</label>
                <select
                  value={formData.furnishing}
                  onChange={(e) => setFormData({ ...formData, furnishing: e.target.value })}
                  className="input-field"
                >
                  {furnishingOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </div>

              {/* Construction Status */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-2">🏗️ Construction Status</label>
                <div className="grid grid-cols-2 gap-2">
                  {statusOptions.map(status => (
                    <button
                      key={status}
                      onClick={() => setFormData({ ...formData, construction_status: status })}
                      className={`px-3 py-2 rounded-lg text-sm font-semibold transition ${
                        formData.construction_status === status
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {status}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={analyzPrice}
                disabled={loading || isSizeHardBlocked || (formData.size || 0) < 250}
                className="btn-primary w-full"
              >
                {loading ? '⏳ Analyzing...' : '🔍 Analyze Price'}
              </button>
            </div>
          </motion.div>

          {/* Results */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-2 space-y-6"
          >
            {result && (
              <>
                {/* Main Price Card */}
                <div className="glass-effect p-8 rounded-2xl">
                  <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                    <FiTrendingUp className="text-green-400" /> Fair Market Price
                  </h2>

                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 p-6 rounded-xl">
                      <p className="text-slate-400 text-sm mb-2">Predicted Price</p>
                      <p className="text-3xl font-bold text-green-400">
                        {formatPrice(result.predicted_price)}
                      </p>
                    </div>

                    <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 p-6 rounded-xl">
                      <p className="text-slate-400 text-sm mb-2">Min Range</p>
                      <p className="text-3xl font-bold text-blue-400">
                        {formatPrice(result.price_range.min)}
                      </p>
                    </div>

                    <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 p-6 rounded-xl">
                      <p className="text-slate-400 text-sm mb-2">Max Range</p>
                      <p className="text-3xl font-bold text-purple-400">
                        {formatPrice(result.price_range.max)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 pt-6 border-t border-slate-700">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-slate-400">Model Confidence</span>
                      <div className="flex items-center gap-3">
                        <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-pink-500"
                            style={{ width: `${result.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-white font-bold">{(result.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    
                    {result.market_trend && (
                      <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 p-4 rounded-lg border border-blue-500/20">
                        <p className="text-sm text-blue-300 font-medium">{result.market_trend}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Price Factors */}
                <div className="glass-effect p-8 rounded-2xl">
                  <h3 className="text-xl font-bold text-white mb-4">📊 Price Factors Analysis</h3>
                  <div className="space-y-3">
                    {Object.entries(result.factors).map(([key, value]) => (
                      <div key={key} className="bg-slate-800/50 p-4 rounded-lg hover:bg-slate-800/70 transition">
                        <div className="flex justify-between items-start mb-2">
                          <p className="text-slate-400 text-sm capitalize font-medium">{key.replace(/_/g, ' ')}</p>
                          {value.impact && (
                            <span className="text-indigo-400 text-sm font-bold">{value.impact}</span>
                          )}
                        </div>
                        <p className="text-white text-sm">{value.description || value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Comparable Properties */}
                {result.comparables && result.comparables.length > 0 && (
                  <div className="glass-effect p-8 rounded-2xl">
                    <h3 className="text-xl font-bold text-white mb-4">🏘️ Comparable Properties</h3>
                    <div className="space-y-3">
                      {result.comparables.map((comp, idx) => (
                        <div key={idx} className="bg-slate-800/50 p-4 rounded-lg flex justify-between items-center">
                          <div>
                            <p className="text-white font-semibold">{comp.bhk} BHK · {comp.size} sq ft</p>
                            <p className="text-slate-400 text-sm">{comp.location}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-green-400 font-bold">{formatPrice(comp.price)}</p>
                            <p className="text-slate-500 text-xs">{comp.days_ago} days ago</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Price Trend Chart */}
                <div className="glass-effect p-8 rounded-2xl">
                  <h3 className="text-xl font-bold text-white mb-4">📈 Price Trend</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid stroke="#475569" />
                      <XAxis stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1e293b',
                          border: '1px solid #475569',
                          borderRadius: '8px'
                        }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="#6366f1"
                        strokeWidth={2}
                        name="Your Property"
                        dot={{ fill: '#6366f1' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="market"
                        stroke="#ec4899"
                        strokeWidth={2}
                        name="Market Average"
                        dot={{ fill: '#ec4899' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}

            {!result && (
              <div className="glass-effect p-12 rounded-2xl text-center">
                <p className="text-2xl text-slate-300">Enter property details to see price analysis ☝️</p>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
