import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiCompass, FiMapPin, FiCheckCircle, FiAlertCircle, FiInfo, FiSun } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { checkVastuCompliance } from '../utils/api'

// Direction options
const DIRECTIONS = [
  { value: 'North', label: 'North (उत्तर)', icon: '⬆️', color: 'text-blue-400' },
  { value: 'Northeast', label: 'Northeast (ईशान)', icon: '↗️', color: 'text-cyan-400' },
  { value: 'East', label: 'East (पूर्व)', icon: '➡️', color: 'text-yellow-400' },
  { value: 'Southeast', label: 'Southeast (आग्नेय)', icon: '↘️', color: 'text-orange-400' },
  { value: 'South', label: 'South (दक्षिण)', icon: '⬇️', color: 'text-red-400' },
  { value: 'Southwest', label: 'Southwest (नैऋत्य)', icon: '↙️', color: 'text-pink-400' },
  { value: 'West', label: 'West (पश्चिम)', icon: '⬅️', color: 'text-purple-400' },
  { value: 'Northwest', label: 'Northwest (वायव्य)', icon: '↖️', color: 'text-indigo-400' },
]

// Popular Indian cities
const POPULAR_LOCATIONS = [
  'Andheri West, Mumbai',
  'Bandra, Mumbai',
  'Worli, Mumbai',
  'Koramangala, Bangalore',
  'Whitefield, Bangalore',
  'Gachibowli, Hyderabad',
]

const DIRECTION_NOTES = {
  North: 'North invites growth and financial stability when kept open and light.',
  Northeast: 'Northeast is the most auspicious for clarity, prayer, and wellbeing.',
  East: 'East favors health and vitality, especially with morning light.',
  Southeast: 'Southeast suits fire zones like kitchens and active spaces.',
  South: 'South requires balance and strong thresholds for harmony.',
  Southwest: 'Southwest benefits from heavier furniture for stability.',
  West: 'West is ideal for rest and quiet zones in the home.',
  Northwest: 'Northwest supports movement and guest-friendly spaces.'
}

const getVerdict = (score) => {
  if (score >= 70) return 'Excellent compliance with strong energy alignment.'
  if (score >= 50) return 'Good compliance with a few actionable improvements.'
  if (score >= 30) return 'Fair compliance; remedies will noticeably help.'
  return 'Low compliance; consider structural or directional adjustments.'
}

// Score visualization component
function VastuScoreGauge({ score, level, levelEmoji }) {
  const percentage = score
  const rotation = (percentage / 100) * 180 - 90 // -90 to 90 degrees
  
  // Color based on score
  const getColor = () => {
    if (score >= 70) return 'text-green-400'
    if (score >= 50) return 'text-yellow-400'
    if (score >= 30) return 'text-orange-400'
    return 'text-red-400'
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-effect p-8 rounded-2xl text-center"
    >
      <h3 className="text-lg text-slate-400 mb-4">Vastu Compliance Score</h3>
      
      {/* Circular gauge */}
      <div className="relative w-48 h-48 mx-auto mb-6">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
          {/* Background arc */}
          <path
            d="M 40 100 A 60 60 0 0 1 160 100"
            fill="none"
            stroke="rgba(100, 116, 139, 0.3)"
            strokeWidth="20"
            strokeLinecap="round"
          />
          {/* Score arc */}
          <motion.path
            d="M 40 100 A 60 60 0 0 1 160 100"
            fill="none"
            stroke={score >= 70 ? '#4ade80' : score >= 50 ? '#facc15' : score >= 30 ? '#fb923c' : '#f87171'}
            strokeWidth="20"
            strokeLinecap="round"
            strokeDasharray={`${(percentage / 100) * 188} 188`}
            initial={{ strokeDasharray: '0 188' }}
            animate={{ strokeDasharray: `${(percentage / 100) * 188} 188` }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
          />
        </svg>
        
        {/* Score display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.5, type: 'spring' }}
            className={`text-6xl font-bold ${getColor()}`}
          >
            {score}
          </motion.div>
          <div className="text-slate-400 text-sm mt-1">out of 100</div>
        </div>
      </div>
      
      {/* Level badge */}
      <div className={`inline-flex items-center gap-2 px-6 py-3 rounded-full text-lg font-bold ${
        score >= 70 ? 'bg-green-500/20 text-green-300 border-2 border-green-500/40' :
        score >= 50 ? 'bg-yellow-500/20 text-yellow-300 border-2 border-yellow-500/40' :
        score >= 30 ? 'bg-orange-500/20 text-orange-300 border-2 border-orange-500/40' :
        'bg-red-500/20 text-red-300 border-2 border-red-500/40'
      }`}>
        <span className="text-2xl">{levelEmoji}</span>
        <span>{level} Compliance</span>
      </div>
    </motion.div>
  )
}

// Factor card component
function FactorCard({ title, factors, isPositive }) {
  if (!factors || factors.length === 0) return null
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-effect p-5 rounded-xl border ${
        isPositive 
          ? 'border-green-500/30 bg-green-500/5' 
          : 'border-orange-500/30 bg-orange-500/5'
      }`}
    >
      <div className="flex items-center gap-2 mb-4">
        {isPositive ? (
          <FiCheckCircle className="text-green-400 text-xl" />
        ) : (
          <FiAlertCircle className="text-orange-400 text-xl" />
        )}
        <h3 className={`font-bold text-lg ${isPositive ? 'text-green-300' : 'text-orange-300'}`}>
          {title}
        </h3>
      </div>
      <ul className="space-y-2">
        {factors.map((factor, idx) => (
          <li key={idx} className="text-slate-300 text-sm flex items-start gap-2">
            <span className={isPositive ? 'text-green-400' : 'text-orange-400'}>•</span>
            <span>{factor}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  )
}

// Remedy card component
function RemedyCard({ remedy, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="flex items-start gap-3 p-4 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 rounded-lg border border-indigo-500/30"
    >
      <span className="text-2xl">{remedy.split(' ')[0]}</span>
      <p className="text-slate-200 text-sm flex-1">{remedy.substring(remedy.indexOf(' ') + 1)}</p>
    </motion.div>
  )
}

export default function VastuChecker() {
  const [facing, setFacing] = useState('')
  const [location, setLocation] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleCheck = async () => {
    if (!facing || !location) {
      toast.error('Please select facing direction and enter location')
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const response = await checkVastuCompliance({
        facing,
        location: location.trim()
      })
      setResult(response.data)
      toast.success('Vastu analysis complete!')
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to analyze Vastu compliance'
      toast.error(`Error: ${errorMsg}`)
      console.error('Vastu check error:', error.response?.data || error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-7xl mx-auto px-4">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10 text-center"
        >
          <h1 className="text-5xl font-bold gradient-text mb-3">
            🧭 Vastu & Feng Shui Checker
          </h1>
          <p className="text-xl text-slate-300 max-w-3xl mx-auto">
            Check your property's Vastu compliance based on facing direction and real surroundings.
            Get personalized remedies for better energy flow.
          </p>
        </motion.div>

        {/* Input Form */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-effect p-8 rounded-2xl mb-8"
        >
          {/* Direction Selection */}
          <div className="mb-6">
            <label className="block text-slate-300 font-semibold mb-3 flex items-center gap-2">
              <FiCompass className="text-indigo-400" />
              Property Facing Direction
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {DIRECTIONS.map((dir) => (
                <button
                  key={dir.value}
                  onClick={() => setFacing(dir.value)}
                  className={`p-4 rounded-xl border-2 transition-all ${
                    facing === dir.value
                      ? 'border-indigo-500 bg-indigo-500/20 scale-105'
                      : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
                  }`}
                >
                  <div className="text-3xl mb-1">{dir.icon}</div>
                  <div className={`text-sm font-semibold ${facing === dir.value ? dir.color : 'text-slate-300'}`}>
                    {dir.label}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Location Input */}
          <div className="mb-6">
            <label className="block text-slate-300 font-semibold mb-3 flex items-center gap-2">
              <FiMapPin className="text-indigo-400" />
              Property Location
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="e.g., Andheri West, Mumbai"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
                className="input-field w-full"
              />
            </div>
            
            {/* Quick location chips */}
            <div className="flex flex-wrap gap-2 mt-3">
              <span className="text-xs text-slate-500 self-center">Quick select:</span>
              {POPULAR_LOCATIONS.map((loc) => (
                <button
                  key={loc}
                  onClick={() => setLocation(loc)}
                  className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-700 text-slate-300 hover:bg-indigo-600 hover:text-white transition"
                >
                  {loc}
                </button>
              ))}
            </div>
          </div>

          {/* Check Button */}
          <button
            onClick={handleCheck}
            disabled={loading || !facing || !location}
            className="btn-primary w-full py-4 text-lg flex items-center justify-center gap-3"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Analyzing Vastu...
              </>
            ) : (
              <>
                <FiSun /> Check Vastu Compliance
              </>
            )}
          </button>

          {/* Info note */}
          {result && !result.using_serpapi && (
            <div className="mt-4 flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <FiInfo className="text-blue-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-blue-200">
                Using simulated surroundings data. Configure live maps access in the backend to enable real-time Google Maps analysis.
              </p>
            </div>
          )}
        </motion.div>

        {/* Results */}
        <AnimatePresence>
          {result && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              {/* Score Gauge */}
              <VastuScoreGauge 
                score={result.score} 
                level={result.level} 
                levelEmoji={result.level_emoji} 
              />

              {/* Summary */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-effect p-6 rounded-2xl"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <p className="text-slate-400 text-sm uppercase tracking-wide">Property Summary</p>
                    <h2 className="text-2xl font-bold text-white mt-1">
                      {result.facing} Facing • {result.location}
                    </h2>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{result.level_emoji}</span>
                    <div>
                      <p className="text-slate-400 text-xs uppercase tracking-wide">Verdict</p>
                      <p className="text-white font-semibold">{getVerdict(result.score)}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Score</p>
                    <p className="text-3xl font-bold text-white">{result.score}<span className="text-slate-400 text-base">/100</span></p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Direction Insight</p>
                    <p className="text-slate-200 text-sm leading-relaxed">
                      {DIRECTION_NOTES[result.facing] || 'Balanced orientation with mindful zoning.'}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <p className="text-slate-400 text-xs uppercase tracking-wide">Context</p>
                    <p className="text-slate-200 text-sm leading-relaxed">
                      {result.using_serpapi
                        ? 'Based on real nearby landmarks and surroundings.'
                        : 'Based on simulated surroundings data for this area.'}
                    </p>
                  </div>
                </div>
              </motion.div>

              {/* Factors Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <FactorCard 
                  title="Positive Vastu Factors" 
                  factors={result.positive_factors} 
                  isPositive={true} 
                />
                <FactorCard 
                  title="Vastu Concerns" 
                  factors={result.negative_factors} 
                  isPositive={false} 
                />
              </div>

              {/* Remedies */}
              {result.remedies && result.remedies.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="glass-effect p-6 rounded-2xl"
                >
                  <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    💎 Vastu Remedies & Recommendations
                  </h2>
                  <div className="space-y-3">
                    {result.remedies.map((remedy, idx) => (
                      <RemedyCard key={idx} remedy={remedy} index={idx} />
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Surroundings Summary */}
              {result.surroundings && Object.keys(result.surroundings).some(key => result.surroundings[key]?.length > 0) && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="glass-effect p-6 rounded-2xl"
                >
                  <h2 className="text-2xl font-bold text-white mb-4">
                    🗺️ Nearby Surroundings
                  </h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(result.surroundings).map(([category, places]) => (
                      places && places.length > 0 && (
                        <div key={category} className="bg-slate-700/30 p-3 rounded-lg">
                          <h4 className="text-slate-400 text-xs uppercase font-semibold mb-2">
                            {category.replace('_', ' ')}
                          </h4>
                          <p className="text-slate-200 text-sm">
                            {places.slice(0, 2).join(', ')}
                            {places.length > 2 && ` +${places.length - 2} more`}
                          </p>
                        </div>
                      )
                    ))}
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty State */}
        {!result && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-effect p-14 rounded-2xl text-center"
          >
            <p className="text-6xl mb-4">🏡</p>
            <p className="text-2xl text-slate-300 font-semibold mb-2">
              Discover Your Property's Vastu Harmony
            </p>
            <p className="text-slate-500">
              Select your property's facing direction and location above to get a detailed Vastu compliance report
              with personalized remedies based on real surroundings.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  )
}
