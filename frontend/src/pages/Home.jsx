import { motion } from 'framer-motion'
import { FiAlertCircle, FiCheck, FiSearch, FiTrendingUp, FiUsers } from 'react-icons/fi'
import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { getCrossModalMatches, getTrendingLocations } from '../utils/api'
import PropertyDiscoveryMap from '../components/PropertyDiscoveryMap'

const lifestyleOptions = [
  { name: 'Family with Kids', icon: 'Family' },
  { name: 'Young Professional', icon: 'Young' },
  { name: 'Fitness Enthusiast', icon: 'Fitness' },
  { name: 'Luxury Living', icon: 'Luxury' },
  { name: 'Work From Home', icon: 'Work' },
  { name: 'Retired Couple', icon: 'Retired' },
]

const featureCards = [
  {
    icon: <FiTrendingUp className="text-3xl" />,
    title: 'Smart Price Prediction',
    description: 'ML-powered price analysis to identify fair market value and spot overpriced listings',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    icon: <FiCheck className="text-3xl" />,
    title: 'Fraud Detection',
    description: 'AI detects duplicate listings, fake properties, and scam indicators with trust scoring',
    color: 'from-green-500 to-emerald-500',
  },
  {
    icon: <FiAlertCircle className="text-3xl" />,
    title: 'Unified Search',
    description: 'Search across major property platforms in one interface',
    color: 'from-purple-500 to-pink-500',
  },
  {
    icon: <FiUsers className="text-3xl" />,
    title: 'AI Advisor',
    description: 'Chat with the AI advisor for location, pricing, and investment guidance',
    color: 'from-orange-500 to-red-500',
  },
]

function formatDisplayPrice(price) {
  if (price == null) return 'Price on request'
  if (typeof price === 'object') {
    if (price.range) return price.range
    if (typeof price.minValue === 'number' && typeof price.maxValue === 'number') {
      return `Rs ${(price.minValue / 10000000).toFixed(2)} Cr - Rs ${(price.maxValue / 10000000).toFixed(2)} Cr`
    }
    if (typeof price.minValue === 'number') {
      return `Rs ${(price.minValue / 10000000).toFixed(2)} Cr`
    }
  }
  if (typeof price === 'number') {
    if (price >= 10000000) return `Rs ${(price / 10000000).toFixed(2)} Cr`
    return `Rs ${(price / 100000).toFixed(2)} L`
  }
  return String(price)
}

export default function Home() {
  const navigate = useNavigate()
  const [trendingLocations, setTrendingLocations] = useState([])
  const [crossModalQuery, setCrossModalQuery] = useState('')
  const [crossModalResults, setCrossModalResults] = useState(null)
  const [crossModalLoading, setCrossModalLoading] = useState(false)
  const [selectedLifestyle, setSelectedLifestyle] = useState(null)
  const [selectedPropertyId, setSelectedPropertyId] = useState(null)

  useEffect(() => {
    getTrendingLocations(5)
      .then(({ data }) => setTrendingLocations(data.trending_locations || []))
      .catch((error) => console.error('Error fetching trending locations:', error))
  }, [])

  const normalizedMatches = useMemo(() => {
    return (crossModalResults?.matches || []).map((property) => ({
      ...property,
      price: formatDisplayPrice(property.rawPrice ?? property.price),
    }))
  }, [crossModalResults])

  useEffect(() => {
    if (normalizedMatches.length > 0) {
      setSelectedPropertyId(normalizedMatches[0].id)
    }
  }, [normalizedMatches])

  const handleOpenProperty = (property) => {
    try {
      sessionStorage.setItem('mynivas:lastProperty', JSON.stringify(property))
    } catch (error) {
      console.warn('Unable to persist selected property:', error)
    }
    navigate(`/property/${encodeURIComponent(String(property.id || property.name || 'property'))}`, {
      state: { property },
    })
  }

  const triggerSearch = async (query, lifestyle = null) => {
    setCrossModalLoading(true)
    try {
      const { data } = await getCrossModalMatches({
        query,
        lifestyle,
        top_k: 6,
        use_cross_modal: true,
      })
      setCrossModalResults(data)
    } catch (error) {
      setCrossModalResults({
        error: error?.response?.data?.detail || error.message || 'Search failed. Please try again.',
        matches: [],
      })
    } finally {
      setCrossModalLoading(false)
    }
  }

  const handleCrossModalSearch = async (event) => {
    event.preventDefault()

    let finalQuery = crossModalQuery
    if (!finalQuery.trim() && selectedLifestyle) {
      finalQuery = selectedLifestyle
    }

    if (!finalQuery.trim()) {
      alert('Please enter a search query or select a lifestyle')
      return
    }

    await triggerSearch(finalQuery, selectedLifestyle)
  }

  const selectedProperty = normalizedMatches.find((property) => property.id === selectedPropertyId) || normalizedMatches[0]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900">
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h1 className="text-6xl md:text-7xl font-black font-display gradient-text mb-6">
            Real Estate,<br /> Reimagined
          </h1>
          <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-10">
            Stop searching across multiple websites. Stop getting scammed. Stop overpaying.
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-pink-400">
              myNivas helps you find the right property faster.
            </span>
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/search" className="btn-primary">
              Start Searching
            </Link>
            <button className="btn-secondary">
              Learn More
            </button>
          </div>
        </motion.div>

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
              Type what you want in natural language. We break your sentence into location, budget, type,
              lifestyle, and feature requirements, then plot the best matches directly on the map.
            </p>

            <form onSubmit={handleCrossModalSearch} className="space-y-4">
              <div className="mb-4">
                <p className="text-slate-400 text-sm mb-3">Or choose a lifestyle:</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {lifestyleOptions.map((lifestyle) => (
                    <button
                      key={lifestyle.name}
                      type="button"
                      onClick={() => {
                        const isSelected = selectedLifestyle === lifestyle.name
                        setSelectedLifestyle(isSelected ? null : lifestyle.name)
                        setCrossModalQuery('')
                        if (!isSelected) {
                          setTimeout(() => {
                            triggerSearch(lifestyle.name, lifestyle.name)
                          }, 0)
                        }
                      }}
                      className={`p-3 rounded-lg font-medium transition-all ${
                        selectedLifestyle === lifestyle.name
                          ? 'bg-indigo-500 text-white'
                          : 'glass-effect text-slate-300 hover:bg-slate-700/50'
                      }`}
                    >
                      {lifestyle.icon}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder='e.g., "affordable sea view flat in mumbai with good work environment"'
                  value={crossModalQuery}
                  onChange={(event) => setCrossModalQuery(event.target.value)}
                  className="flex-1 px-4 py-3 w-full bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
                <button
                  type="submit"
                  disabled={crossModalLoading}
                  className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-lg font-semibold text-white hover:shadow-lg hover:shadow-indigo-500/50 disabled:opacity-50 transition-all"
                >
                  {crossModalLoading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </form>

            {crossModalResults && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8 pt-8 border-t border-slate-700"
              >
                {crossModalResults.error ? (
                  <div className="text-red-400 p-4 bg-red-500/10 rounded-lg">
                    {crossModalResults.error}
                  </div>
                ) : normalizedMatches.length > 0 ? (
                  <div className="space-y-5">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <p className="text-slate-300 text-sm">
                          Found {normalizedMatches.length} matching properties{selectedLifestyle ? ` for ${selectedLifestyle}` : ''}
                        </p>
                        {selectedProperty ? (
                          <p className="text-xs text-slate-500 mt-1">
                            Highlighted: {selectedProperty.name} in {selectedProperty.locality || selectedProperty.city}
                          </p>
                        ) : null}
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {(crossModalResults.parsed_requirements?.location ? [`Location: ${crossModalResults.parsed_requirements.location}`] : [])
                          .concat(crossModalResults.parsed_requirements?.property_type ? [`Type: ${crossModalResults.parsed_requirements.property_type}`] : [])
                          .concat(crossModalResults.parsed_requirements?.bhk ? [`${crossModalResults.parsed_requirements.bhk} BHK`] : [])
                          .concat(crossModalResults.parsed_requirements?.budget_label ? [crossModalResults.parsed_requirements.budget_label] : [])
                          .concat((crossModalResults.parsed_requirements?.features || []).map((feature) => feature.replace(/_/g, ' ')))
                          .slice(0, 6)
                          .map((chip) => (
                            <span key={chip} className="px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs">
                              {chip}
                            </span>
                          ))}
                      </div>
                    </div>

                    <PropertyDiscoveryMap
                      properties={normalizedMatches}
                      center={crossModalResults.map?.center}
                      selectedId={selectedPropertyId}
                      onSelect={(property) => setSelectedPropertyId(property.id)}
                      onOpenProperty={handleOpenProperty}
                    />
                  </div>
                ) : (
                  <div className="text-slate-400 p-6 text-center rounded-xl bg-slate-900/40">
                    No properties found for this search. Try adjusting the location, budget, or lifestyle cues.
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </motion.div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.h2
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          className="text-4xl font-bold text-center gradient-text mb-16"
        >
          Why myNivas?
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {featureCards.map((feature) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
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

      {trendingLocations.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            className="text-center mb-12"
          >
            <h2 className="text-4xl font-bold gradient-text mb-4 flex items-center justify-center gap-3">
              <FiTrendingUp className="text-indigo-400" />
              Trending Market News
            </h2>
            <p className="text-lg text-slate-300 max-w-2xl mx-auto">
              AI-powered insights on locations with the most market activity and infrastructure developments
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
            {trendingLocations.map((location, index) => (
              <motion.div
                key={`${location.location}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                className="glass-effect p-6 rounded-xl text-center card-hover"
              >
                <div className="text-3xl font-bold gradient-text mb-2">#{index + 1}</div>
                <div className="text-xl font-semibold text-white mb-2">{location.location}</div>
                <div className="text-sm text-slate-400 mb-2">{location.news_count} articles</div>
                <div className={`px-3 py-1 rounded-full text-xs font-semibold inline-block ${
                  location.avg_impact >= 0.7 ? 'bg-green-500' :
                  location.avg_impact >= 0.5 ? 'bg-blue-500' : 'bg-slate-500'
                }`}>
                  {(location.avg_impact * 100).toFixed(0)}% Impact
                </div>
              </motion.div>
            ))}
          </div>

          <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="text-center">
            <Link to="/market-news" className="btn-primary inline-block">
              View All Market News
            </Link>
          </motion.div>
        </section>
      )}

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          className="glass-effect p-12 rounded-2xl text-center bg-gradient-to-r from-indigo-500/20 to-pink-500/20"
        >
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to find your dream home?
          </h2>
          <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
            Search faster, compare smarter, and explore properties directly on the map.
          </p>
          <Link to="/search" className="btn-primary inline-block">
            Search Now
          </Link>
        </motion.div>
      </section>
    </div>
  )
}
