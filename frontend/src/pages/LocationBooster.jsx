import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiMapPin, FiChevronDown, FiChevronUp, FiSearch, FiCheckCircle, FiHeart, FiTrendingUp, FiClock } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { getNeighborhoodReport } from '../utils/api'

// Quick-select chips for popular locations in the dataset
const POPULAR_LOCATIONS = [
  'Worli', 'Andheri West', 'Bandra', 'Malad', 'Goregaon',
  'Powai', 'Thane', 'Navi Mumbai', 'Pune', 'Bangalore',
]

// Colour mapping per category for visual differentiation
const CATEGORY_COLORS = {
  'Schools & Education':      'from-blue-500/20   to-cyan-500/20   border-blue-500/40   text-blue-400',
  'Hospitals & Healthcare':   'from-red-500/20    to-rose-500/20   border-red-500/40    text-red-400',
  'Transit & Connectivity':   'from-violet-500/20 to-purple-500/20 border-violet-500/40 text-violet-400',
  'Malls & Shopping':         'from-pink-500/20   to-fuchsia-500/20 border-pink-500/40  text-pink-400',
  'Supermarkets & Stores':    'from-amber-500/20  to-yellow-500/20 border-amber-500/40  text-amber-400',
  'Restaurants & Food':       'from-orange-500/20 to-amber-500/20  border-orange-500/40 text-orange-400',
  'Banks & ATMs':             'from-green-500/20  to-emerald-500/20 border-green-500/40 text-green-400',
  'Parks & Recreation':       'from-teal-500/20   to-green-500/20  border-teal-500/40   text-teal-400',
  'Religious Places':         'from-indigo-500/20 to-blue-500/20   border-indigo-500/40 text-indigo-400',
  'Hotels & Hospitality':     'from-sky-500/20    to-cyan-500/20   border-sky-500/40    text-sky-400',
  'Petrol Stations':          'from-slate-500/20  to-gray-500/20   border-slate-500/40  text-slate-400',
  'Gyms & Fitness':           'from-lime-500/20   to-green-500/20  border-lime-500/40   text-lime-400',
}

// Suitability tag colours
const TAG_COLORS = {
  'Family-Friendly':          'bg-blue-500/20   text-blue-300   border-blue-500/40',
  'Well-Connected':           'bg-violet-500/20 text-violet-300 border-violet-500/40',
  'Healthcare Access':        'bg-red-500/20    text-red-300    border-red-500/40',
  'Lifestyle Hub':            'bg-pink-500/20   text-pink-300   border-pink-500/40',
  'Convenient Daily Needs':   'bg-amber-500/20  text-amber-300  border-amber-500/40',
  'Residential Area':         'bg-slate-500/20  text-slate-300  border-slate-500/40',
}

function LandmarkCard({ categoryName, info }) {
  const [expanded, setExpanded] = useState(true)
  const colorClass = CATEGORY_COLORS[categoryName] || 'from-slate-500/20 to-slate-400/20 border-slate-500/40 text-slate-400'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gradient-to-br ${colorClass.split(' ').slice(0, 2).join(' ')} border ${colorClass.split(' ')[2]} rounded-xl overflow-hidden`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{info.icon}</span>
          <div>
            <p className={`font-bold text-base ${colorClass.split(' ')[3]}`}>{categoryName}</p>
            <p className="text-slate-400 text-xs">{info.places.length} place{info.places.length !== 1 ? 's' : ''} found</p>
          </div>
        </div>
        <span className="text-slate-400">
          {expanded ? <FiChevronUp /> : <FiChevronDown />}
        </span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <ul className="px-4 pb-4 space-y-1">
              {info.places.map((place, idx) => (
                <li key={idx} className="flex items-center gap-2 text-sm text-slate-300">
                  <FiCheckCircle className={`shrink-0 ${colorClass.split(' ')[3]}`} />
                  {place}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// Score visualization component
function ScoreCard({ label, score, maxScore = 10, icon, color }) {
  const percentage = (score / maxScore) * 100
  const scoreColor = score >= 8 ? 'text-green-400' : score >= 6 ? 'text-yellow-400' : 'text-orange-400'
  
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-effect p-5 rounded-xl"
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <p className="text-slate-300 font-semibold">{label}</p>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between items-end">
          <span className={`text-2xl font-bold ${scoreColor}`}>{typeof score === 'number' ? score.toFixed(1) : score}/{maxScore}</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className={`h-full rounded-full ${score >= 8 ? 'bg-green-500' : score >= 6 ? 'bg-yellow-500' : 'bg-orange-500'}`}
          />
        </div>
      </div>
    </motion.div>
  )
}

// Commute time card
function CommuteCard({ estimation, title }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-lg border border-slate-600/50"
    >
      <FiClock className="text-indigo-400 mt-1 flex-shrink-0" />
      <div>
        <p className="text-slate-400 text-xs font-semibold uppercase">{title}</p>
        <p className="text-slate-200 text-sm font-medium">{estimation}</p>
      </div>
    </motion.div>
  )
}

export default function LocationBooster() {
  const [location, setLocation] = useState('')
  const [loading, setLoading]   = useState(false)
  const [report, setReport]     = useState(null)

  const handleGenerate = async (loc) => {
    const query = loc || location
    if (!query.trim()) {
      toast.error('Please enter a location first')
      return
    }
    setLoading(true)
    setReport(null)
    try {
      const res = await getNeighborhoodReport(query.trim())
      setReport(res.data)
      toast.success('Neighborhood report generated!')
    } catch (err) {
      toast.error('Failed to generate report. Is the backend running?')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleChip = (loc) => {
    setLocation(loc)
    handleGenerate(loc)
  }

  const hasLandmarks =
    report && Object.keys(report.landmark_categories || {}).length > 0

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-7xl mx-auto px-4">

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10"
        >
          <h1 className="text-5xl font-bold gradient-text mb-3">
            📍 Location Booster
          </h1>
          <p className="text-xl text-slate-300">
            GenAI-powered neighborhood insights — landmarks, connectivity, and family suitability at a glance.
          </p>
        </motion.div>

        {/* Search Card */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-effect p-6 rounded-2xl mb-8"
        >
          {/* Input row */}
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <FiMapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-indigo-400 text-lg" />
              <input
                type="text"
                placeholder="Enter a location — e.g. Andheri West, Worli, Bandra…"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                className="input-field pl-10"
              />
            </div>
            <button
              onClick={() => handleGenerate()}
              disabled={loading}
              className="btn-primary px-6 flex items-center gap-2 whitespace-nowrap"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Generating…
                </>
              ) : (
                <>
                  <FiSearch /> Generate Report
                </>
              )}
            </button>
          </div>

          {/* Quick-select chips */}
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-slate-500 self-center">Popular:</span>
            {POPULAR_LOCATIONS.map((loc) => (
              <button
                key={loc}
                onClick={() => handleChip(loc)}
                className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-700 text-slate-300 hover:bg-indigo-600 hover:text-white transition"
              >
                {loc}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Results */}
        <AnimatePresence>
          {report && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              {/* Summary bar */}
              <div className="glass-effect p-5 rounded-2xl flex flex-wrap items-center gap-4">
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Location</p>
                  <p className="text-white font-bold text-lg">{report.location}</p>
                </div>
                <div className="h-8 w-px bg-slate-700 hidden sm:block" />
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Listings Analysed</p>
                  <p className="text-indigo-400 font-bold text-lg">{report.properties_analyzed}</p>
                </div>
                <div className="h-8 w-px bg-slate-700 hidden sm:block" />
                <div className="flex flex-wrap gap-2">
                  {(report.suitability_tags || []).map((tag) => (
                    <span
                      key={tag}
                      className={`px-3 py-1 rounded-full text-xs font-semibold border ${TAG_COLORS[tag] || 'bg-slate-500/20 text-slate-300 border-slate-500/40'}`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* GenAI Insights Scores */}
              {report.genai_insights && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <ScoreCard
                    label="Family Suitability"
                    score={report.genai_insights.family_score}
                    maxScore={10}
                    icon="👨‍👩‍👧‍👦"
                    color="text-blue-400"
                  />
                  <ScoreCard
                    label="Connectivity Score"
                    score={report.genai_insights.connectivity_score}
                    maxScore={10}
                    icon="🚇"
                    color="text-violet-400"
                  />
                </div>
              )}

              {/* Commute Estimates */}
              {report.genai_insights?.commute_estimates && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="glass-effect p-6 rounded-2xl"
                >
                  <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    ⏱️ Estimated Commute Times
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <CommuteCard
                      title="To Airport"
                      estimation={report.genai_insights.commute_estimates.airport}
                    />
                    <CommuteCard
                      title="To Business Hub"
                      estimation={report.genai_insights.commute_estimates.business_district}
                    />
                    <CommuteCard
                      title="To Railway Station"
                      estimation={report.genai_insights.commute_estimates.railway_station}
                    />
                    <CommuteCard
                      title="To Highway"
                      estimation={report.genai_insights.commute_estimates.highway}
                    />
                  </div>
                  <p className="text-slate-400 text-xs mt-4 italic">
                    Note: Times are approximate and vary based on traffic conditions and specific destination.
                  </p>
                </motion.div>
              )}

              {/* Two-column layout: left = narrative + insights, right = landmark cards */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Combined narrative and insights */}
                <div className="space-y-4">
                  {/* Original narrative report */}
                  <div className="glass-effect p-6 rounded-2xl">
                    <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                      🤖 AI Neighborhood Summary
                    </h2>
                    <pre className="whitespace-pre-wrap text-slate-300 text-sm leading-relaxed font-sans">
                      {report.report}
                    </pre>
                  </div>

                  {/* GenAI Insights text */}
                  {report.genai_insights?.insights && (
                    <div className="glass-effect p-6 rounded-2xl border border-indigo-500/20">
                      <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                        ✨ Deep Dive Analysis
                      </h2>
                      <pre className="whitespace-pre-wrap text-slate-300 text-sm leading-relaxed font-sans">
                        {report.genai_insights.insights}
                      </pre>
                    </div>
                  )}
                </div>

                {/* Landmark category cards */}
                <div>
                  {hasLandmarks ? (
                    <div className="space-y-3">
                      <h2 className="text-xl font-bold text-white mb-1">
                        🗺️ Nearby Landmarks
                      </h2>
                      {Object.entries(report.landmark_categories).map(([cat, info]) => (
                        <LandmarkCard key={cat} categoryName={cat} info={info} />
                      ))}
                    </div>
                  ) : (
                    <div className="glass-effect p-8 rounded-2xl text-center h-full flex flex-col items-center justify-center">
                      <p className="text-4xl mb-3">🔍</p>
                      <p className="text-slate-300 text-lg font-semibold">No landmark data found</p>
                      <p className="text-slate-500 text-sm mt-1">
                        The dataset does not have landmark entries for this location yet.
                        The narrative report above is based on general area knowledge.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        {!report && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-effect p-14 rounded-2xl text-center"
          >
            <p className="text-5xl mb-4">🏙️</p>
            <p className="text-2xl text-slate-300 font-semibold mb-2">
              Discover your neighborhood
            </p>
            <p className="text-slate-500">
              Enter a Mumbai, Bangalore, or Pune location above and get an instant AI report
              on schools, hospitals, metro access, malls, and more.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  )
}
