import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiMapPin, FiSearch, FiChevronDown, FiChevronUp, FiZap } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { getAmenityMatch } from '../utils/api'

// ------------------------------------------------------------------
// Lifestyle presets — mirrors LIFESTYLE_PROFILES in amenity_matcher.py
// ------------------------------------------------------------------
const PRESETS = [
  { name: 'Family with Kids',   icon: '👨‍👩‍👧‍👦', color: 'blue',   desc: 'Play areas, pools, garden, security' },
  { name: 'Young Professional', icon: '💼',        color: 'indigo', desc: 'Gym, Wi-Fi, parking, concierge' },
  { name: 'Fitness Enthusiast', icon: '🏋️',        color: 'green',  desc: 'Jogging track, gym, tennis, health club' },
  { name: 'Luxury Living',      icon: '✨',         color: 'amber',  desc: 'Skydeck, smart home, jacuzzi, bar lounge' },
  { name: 'Work From Home',     icon: '🏠💻',       color: 'violet', desc: 'Wi-Fi, conference room, power backup' },
  { name: 'Retired Couple',     icon: '🌿',         color: 'teal',   desc: 'Garden, lift, security, community hall' },
]

const PRESET_STYLES = {
  blue:   { card: 'border-blue-500/40   bg-blue-500/10   hover:bg-blue-500/20',   active: 'border-blue-400   bg-blue-500/30',   badge: 'bg-blue-500/20   text-blue-300   border-blue-500/40'   },
  indigo: { card: 'border-indigo-500/40 bg-indigo-500/10 hover:bg-indigo-500/20', active: 'border-indigo-400 bg-indigo-500/30', badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' },
  green:  { card: 'border-green-500/40  bg-green-500/10  hover:bg-green-500/20',  active: 'border-green-400  bg-green-500/30',  badge: 'bg-green-500/20  text-green-300  border-green-500/40'  },
  amber:  { card: 'border-amber-500/40  bg-amber-500/10  hover:bg-amber-500/20',  active: 'border-amber-400  bg-amber-500/30',  badge: 'bg-amber-500/20  text-amber-300  border-amber-500/40'  },
  violet: { card: 'border-violet-500/40 bg-violet-500/10 hover:bg-violet-500/20', active: 'border-violet-400 bg-violet-500/30', badge: 'bg-violet-500/20 text-violet-300 border-violet-500/40' },
  teal:   { card: 'border-teal-500/40   bg-teal-500/10   hover:bg-teal-500/20',   active: 'border-teal-400   bg-teal-500/30',   badge: 'bg-teal-500/20   text-teal-300   border-teal-500/40'   },
}

const colorForProfile = (name) =>
  PRESETS.find(p => p.name === name)?.color || 'indigo'

function PropertyCard({ prop, color }) {
  const [open, setOpen] = useState(false)
  const styles = PRESET_STYLES[color] || PRESET_STYLES.indigo
  const scorePercent = Math.round(prop.score * 100)

  return (
    <div className={`border rounded-xl overflow-hidden transition ${open ? styles.active : styles.card}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left"
      >
        <div className="flex-1 min-w-0">
          <p className="text-white font-semibold truncate">{prop.name}</p>
          <p className="text-slate-400 text-xs mt-0.5 truncate">
            {prop.address || prop.city || prop.source}
            {prop.address && prop.city ? `, ${prop.city}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-3 ml-4 shrink-0">
          <div className="text-right">
            <p className="text-xs text-slate-400">Match</p>
            <p className="font-bold text-white">{scorePercent}%</p>
          </div>
          <span className="text-slate-400">{open ? <FiChevronUp /> : <FiChevronDown />}</span>
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">
              <div className="flex flex-wrap gap-1.5">
                {prop.amenities.map((a, i) => (
                  <span key={i} className={`px-2 py-0.5 rounded-full text-xs border ${styles.badge}`}>
                    {a}
                  </span>
                ))}
              </div>
              <p className="text-slate-500 text-xs mt-2">
                Source: {prop.source === 'magicbricks' ? 'MagicBricks' : 'Housing.com'}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function AmenityMatcher() {
  const [selected, setSelected]     = useState(null)  // preset name
  const [customText, setCustomText] = useState('')
  const [location, setLocation]     = useState('')
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState(null)

  const activeLifestyle = selected || customText.trim()

  const handleMatch = async () => {
    if (!activeLifestyle) {
      toast.error('Pick a lifestyle preset or type your own below')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const res = await getAmenityMatch(activeLifestyle, location)
      setResult(res.data)
      toast.success('Amenity report ready!')
    } catch {
      toast.error('Failed to get report. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const activeColor = colorForProfile(selected || result?.lifestyle_profile || 'indigo')
  const activeStyles = PRESET_STYLES[activeColor] || PRESET_STYLES.indigo

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-7xl mx-auto px-4">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-5xl font-bold gradient-text mb-3">🏡 Lifestyle Amenity Matcher</h1>
          <p className="text-xl text-slate-300">
            GenAI matches your lifestyle to property amenities — find homes built for how you actually live.
          </p>
        </motion.div>

        {/* Input Panel */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-effect p-6 rounded-2xl mb-8"
        >
          {/* Preset cards */}
          <p className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Select your lifestyle
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            {PRESETS.map(p => {
              const s = PRESET_STYLES[p.color]
              const isActive = selected === p.name
              return (
                <button
                  key={p.name}
                  onClick={() => { setSelected(isActive ? null : p.name); setCustomText('') }}
                  className={`border rounded-xl p-3 text-left transition cursor-pointer ${isActive ? s.active : s.card}`}
                >
                  <span className="text-2xl block mb-1">{p.icon}</span>
                  <p className="text-white font-semibold text-sm leading-tight">{p.name}</p>
                  <p className="text-slate-400 text-xs mt-1 leading-snug">{p.desc}</p>
                </button>
              )
            })}
          </div>

          {/* OR custom text */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-slate-700" />
            <span className="text-slate-500 text-xs">or describe your lifestyle</span>
            <div className="flex-1 h-px bg-slate-700" />
          </div>
          <input
            type="text"
            placeholder="e.g. active family with teenagers who love sports…"
            value={customText}
            onChange={e => { setCustomText(e.target.value); setSelected(null) }}
            onKeyDown={e => e.key === 'Enter' && handleMatch()}
            className="input-field mb-4"
          />

          {/* Location + button row */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <FiMapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-indigo-400" />
              <input
                type="text"
                placeholder="Filter by location (optional) — e.g. Andheri West"
                value={location}
                onChange={e => setLocation(e.target.value)}
                className="input-field pl-10"
              />
            </div>
            <button
              onClick={handleMatch}
              disabled={loading || !activeLifestyle}
              className="btn-primary px-6 flex items-center gap-2 whitespace-nowrap disabled:opacity-50"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Matching…
                </>
              ) : (
                <><FiZap /> Match Amenities</>
              )}
            </button>
          </div>
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
              {/* Stats bar */}
              <div className="glass-effect p-5 rounded-2xl flex flex-wrap items-center gap-6">
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Lifestyle</p>
                  <p className="text-white font-bold">{result.lifestyle_profile}</p>
                </div>
                <div className="h-8 w-px bg-slate-700 hidden sm:block" />
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Similar Listings</p>
                  <p className="font-bold text-indigo-400 text-lg">{result.similar_count}</p>
                </div>
                <div className="h-8 w-px bg-slate-700 hidden sm:block" />
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Properties Indexed</p>
                  <p className="font-bold text-slate-300">{result.total_indexed}</p>
                </div>
              </div>

              {/* Two-column: pitch + amenity tags */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Pitch */}
                <div className="glass-effect p-6 rounded-2xl">
                  <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    🤖 Your Personalised Pitch
                  </h2>
                  <pre className="whitespace-pre-wrap text-slate-300 text-sm leading-relaxed font-sans">
                    {result.pitch}
                  </pre>
                </div>

                {/* Matched amenity badges */}
                <div className="glass-effect p-6 rounded-2xl">
                  <h2 className="text-xl font-bold text-white mb-4">
                    🏷️ Matched Amenities
                  </h2>
                  {result.matched_amenities.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {result.matched_amenities.map((a, i) => (
                        <span
                          key={i}
                          className={`px-3 py-1.5 rounded-full text-sm font-medium border ${activeStyles.badge}`}
                        >
                          {a.replace(/\b\w/g, c => c.toUpperCase())}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-500">No strong amenity matches found for this combination.</p>
                  )}
                </div>
              </div>

              {/* Top matching properties */}
              {result.top_properties.length > 0 && (
                <div className="glass-effect p-6 rounded-2xl">
                  <h2 className="text-xl font-bold text-white mb-4">
                    🏠 Top Matching Properties
                  </h2>
                  <div className="space-y-3">
                    {result.top_properties.map((prop, i) => (
                      <PropertyCard key={i} prop={prop} color={activeColor} />
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        {!result && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-effect p-14 rounded-2xl text-center"
          >
            <p className="text-5xl mb-4">🎯</p>
            <p className="text-2xl text-slate-300 font-semibold mb-2">Tell us how you live</p>
            <p className="text-slate-500">
              Pick a lifestyle preset above — we'll match it against real amenity data from
              MagicBricks and Housing.com listings and generate a personalised property pitch.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  )
}
