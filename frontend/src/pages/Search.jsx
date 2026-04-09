import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FiSearch, FiFilter, FiMapPin, FiHome, FiSquare } from 'react-icons/fi'
import { MdCheckCircle, MdWarning } from 'react-icons/md'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { searchListings } from '../utils/api'

export default function Search() {
  const navigate = useNavigate()
  const [listings, setListings] = useState([])
  const [mapData, setMapData] = useState(null)
  const [selectedMapListing, setSelectedMapListing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    location: '',
    bhk: 'all',
    minPrice: 0,
    maxPrice: 50000000,
  })

  const cities = ['Mumbai', 'Bangalore', 'Delhi', 'Pune', 'Hyderabad', 'Ahmedabad', 'Chennai']

  useEffect(() => {
    fetchListings()
  }, [])

  const fetchListings = async (appliedFilters = filters) => {
    setLoading(true)
    try {
      const response = await searchListings({
        location: appliedFilters.location || '',
        bhk: appliedFilters.bhk === 'all' ? null : parseInt(appliedFilters.bhk),
        budget_min: appliedFilters.minPrice,
        budget_max: appliedFilters.maxPrice,
        amenities: []
      })
      setListings(response.data.listings)
      setMapData(response.data.map || null)
      setSelectedMapListing(null)
      toast.success(`Found ${response.data.listings.length} properties!`)
    } catch (error) {
      const message = error?.response?.data?.detail || 'Failed to fetch listings. Make sure the backend is running on port 8000.'
      toast.error(message)
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    fetchListings()
  }

  const formatPrice = (price) => {
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(1)} Cr`
    return `₹${(price / 100000).toFixed(0)} L`
  }

  const getVerifiedImage = (images = []) => {
    const blocked = ['logo', 'icon', 'svg', 'sprite', 'placeholder', 'fallback', 'nophotos', 'banner']
    return (images || []).find((img) => {
      if (typeof img !== 'string') return false
      const value = img.trim().toLowerCase()
      return value.startsWith('http') && !blocked.some((token) => value.includes(token))
    })
  }

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

  const mapCenter = mapData?.center
  const mapListings = listings.filter((item) => item?.latitude != null && item?.longitude != null)
  const activeMapCenter = selectedMapListing
    ? {
        latitude: selectedMapListing.latitude,
        longitude: selectedMapListing.longitude,
        label: selectedMapListing.title,
        source: selectedMapListing.source,
      }
    : mapCenter

  const mapEmbedUrl = activeMapCenter?.latitude && activeMapCenter?.longitude
    ? `https://www.google.com/maps?q=${activeMapCenter.latitude},${activeMapCenter.longitude}&z=13&output=embed`
    : null

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-7xl mx-auto px-4">
        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-effect p-8 rounded-2xl mb-12"
        >
          <h1 className="text-3xl font-bold gradient-text mb-8">Find Your Dream Home 🔍</h1>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
            {/* Location Filter */}
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">Location</label>
              <select
                value={filters.location}
                onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                className="input-field"
              >
                <option value="">All Cities</option>
                {cities.map(city => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </select>
            </div>

            {/* BHK Filter */}
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">BHK</label>
              <select
                value={filters.bhk}
                onChange={(e) => setFilters({ ...filters, bhk: e.target.value })}
                className="input-field"
              >
                <option value="all">All BHK</option>
                <option value="1">1 BHK</option>
                <option value="2">2 BHK</option>
                <option value="3">3 BHK</option>
                <option value="4">4+ BHK</option>
              </select>
            </div>

            {/* Min Price */}
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">Min Price</label>
              <select
                value={filters.minPrice}
                onChange={(e) => setFilters({ ...filters, minPrice: parseInt(e.target.value) })}
                className="input-field"
              >
                <option value="0">No Limit</option>
                <option value="2000000">₹20 L</option>
                <option value="5000000">₹50 L</option>
                <option value="10000000">₹1 Cr</option>
              </select>
            </div>

            {/* Max Price */}
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">Max Price</label>
              <select
                value={filters.maxPrice}
                onChange={(e) => setFilters({ ...filters, maxPrice: parseInt(e.target.value) })}
                className="input-field"
              >
                <option value="50000000">₹5 Cr</option>
                <option value="100000000">₹10 Cr</option>
                <option value="200000000">₹20 Cr</option>
                <option value="500000000">₹50 Cr+</option>
              </select>
            </div>

            {/* Search Button */}
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading}
                className="btn-primary w-full"
              >
                {loading ? 'Searching...' : '🔍 Search'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Map Panel */}
        {mapCenter && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-effect p-6 rounded-2xl mb-8"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <FiMapPin className="text-indigo-400" />
                Search Map
              </h2>
              <span className="text-xs text-slate-400">
                Center: {activeMapCenter?.label || 'Search area'} • Source: {activeMapCenter?.source || 'mixed'}
              </span>
            </div>
            {mapEmbedUrl ? (
              <>
                <iframe
                  title="Property Search Map"
                  src={mapEmbedUrl}
                  className="w-full h-80 rounded-xl border border-slate-700"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
                {mapListings.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs text-slate-400 mb-2">Click a listing to focus map:</p>
                    <div className="flex flex-wrap gap-2">
                      {mapListings.slice(0, 12).map((item) => {
                        const isSelected = selectedMapListing?.id === item.id
                        return (
                          <button
                            key={`map_${item.id}`}
                            onClick={() => setSelectedMapListing(item)}
                            className={`text-xs px-3 py-1.5 rounded-full border transition ${
                              isSelected
                                ? 'bg-indigo-500/40 text-indigo-100 border-indigo-300/70'
                                : 'bg-slate-700/40 text-slate-200 border-slate-600 hover:bg-slate-700/70'
                            }`}
                          >
                            {item.title}
                          </button>
                        )
                      })}
                      <button
                        onClick={() => setSelectedMapListing(null)}
                        className="text-xs px-3 py-1.5 rounded-full border bg-slate-800/60 text-slate-300 border-slate-600 hover:bg-slate-700/70"
                      >
                        Reset Center
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-slate-400 text-sm">Map center unavailable for this search.</div>
            )}
          </motion.div>
        )}

        {/* Listings Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin text-4xl">⏳</div>
            <p className="text-slate-400 mt-4">Finding perfect properties...</p>
          </div>
        ) : listings.length === 0 ? (
          <div className="glass-effect p-12 rounded-2xl text-center">
            <p className="text-2xl text-slate-300">No properties found. Try adjusting your filters! 🏠</p>
          </div>
        ) : (
          <motion.div
            layout
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {listings.map((property, i) => (
              <motion.div
                key={property.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="glass-effect rounded-2xl overflow-hidden card-hover group"
              >
                {/* Image */}
                <div className="relative h-40 bg-gradient-to-br from-indigo-500 to-pink-500 overflow-hidden">
                  {(() => {
                    const verifiedImage = getVerifiedImage(property.images)
                    return verifiedImage ? (
                    <img
                      src={verifiedImage}
                      alt={property.title}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                    />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-5xl">🏢</div>
                    )
                  })()}

                  {/* Trust Badge */}
                  <div className="absolute top-4 right-4">
                    <div className={`px-3 py-1 rounded-full font-bold text-sm flex items-center gap-2 ${
                      property.match_score > 80
                        ? 'bg-green-500/80 text-white'
                        : property.match_score > 60
                        ? 'bg-yellow-500/80 text-white'
                        : 'bg-red-500/80 text-white'
                    }`}>
                      {property.match_score > 80 ? <MdCheckCircle /> : <MdWarning />}
                      {property.match_score?.toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] uppercase tracking-wide px-2 py-1 rounded bg-slate-700/60 text-slate-200">
                      {(property.source || 'dataset').toUpperCase()}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2 line-clamp-2">{property.title}</h3>

                  <div className="space-y-3 mb-4 text-slate-300 text-sm">
                    <div className="flex items-center gap-2">
                      <FiMapPin className="text-indigo-400" />
                      <span>{property.location}</span>
                    </div>
                    {property.bhk && (
                      <div className="flex items-center gap-2">
                        <FiHome className="text-pink-400" />
                        <span>{property.bhk} BHK</span>
                      </div>
                    )}
                    {property.size && (
                      <div className="flex items-center gap-2">
                        <FiSquare className="text-teal-400" />
                        <span>{property.size.toFixed(0)} sq ft</span>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-slate-700 pt-4">
                    <p className="text-2xl font-bold gradient-text mb-4">
                      {formatPrice(property.price)}
                    </p>

                    {property.match_reasons && property.match_reasons.length > 0 && (
                      <div className="mb-4">
                        <p className="text-xs text-slate-400 mb-2">Why it matches:</p>
                        <div className="flex flex-wrap gap-2">
                          {property.match_reasons.slice(0, 2).map((reason, i) => (
                            <span key={i} className="text-xs bg-indigo-500/30 text-indigo-200 px-2 py-1 rounded">
                              ✓ {reason}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {(property.latitude && property.longitude) && (
                      <div className="flex items-center gap-3 mb-4">
                        <button
                          onClick={() => setSelectedMapListing(property)}
                          className="inline-flex text-xs text-indigo-300 hover:text-indigo-200"
                        >
                          Focus on map
                        </button>
                        <a
                          href={`https://www.google.com/maps?q=${property.latitude},${property.longitude}`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex text-xs text-indigo-300 hover:text-indigo-200"
                        >
                          Open in Google Maps
                        </a>
                      </div>
                    )}

                    <button
                      className="btn-primary w-full text-sm"
                      onClick={() => handleOpenProperty(property)}
                    >
                      View Details →
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}
