import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FiChevronLeft, FiShare2, FiHeart } from 'react-icons/fi'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import axios from 'axios'
import toast from 'react-hot-toast'

export default function PropertyDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [isFavorite, setIsFavorite] = useState(false)
  const [comparison, setComparison] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)

  // Get property from passed state or use mock data
  const passedProperty = location.state?.property
  
  // Mock property data (fallback)
  const mockProperty = {
    id,
    title: 'Premium 2 BHK Apartment',
    location: 'Mumbai, Ghatkopar East',
    price: 8500000,
    bhk: 2,
    size: 850,
    type: 'Flat',
    possession: 'Dec 2025',
    images: ['🏢', '🏠', '🛏️'],
    description: 'Beautiful 2 BHK apartment in prime location with excellent connectivity.',
    amenities: ['Gym', 'Swimming Pool', 'Parking', 'Security', 'Lift'],
    developer: 'Vibes Estate LLP',
    pricePerSqft: 10000,
    trustScore: 85
  }

  // Use passed property or mock data
  const property = passedProperty ? {
    id: passedProperty.id || id,
    title: passedProperty.name || passedProperty.title || 'Property',
    location: passedProperty.address || passedProperty.location || 'Unknown Location',
    city: passedProperty.city,
    price: passedProperty.price,
    bhk: passedProperty.bhk || 2,
    size: passedProperty.size || 850,
    type: passedProperty.type || 'Flat',
    possession: passedProperty.possession || 'Dec 2025',
    images: passedProperty.images || ['🏢', '🏠', '🛏️'],
    description: passedProperty.description || 'Property details',
    amenities: passedProperty.amenities || [],
    source: passedProperty.source,
    developer: passedProperty.developer || 'Unknown',
    pricePerSqft: passedProperty.pricePerSqft,
    trustScore: passedProperty.trustScore || 75,
    similarity_score: passedProperty.similarity_score
  } : mockProperty

  const formatPrice = (price) => {
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(2)} Cr`
    return `₹${(price / 100000).toFixed(1)} L`
  }

  useEffect(() => {
    const fetchComparison = async () => {
      setCompareLoading(true)
      try {
        const response = await axios.post('/api/compare', {
          title: property.title,
          location: property.location,
          price: property.price,
          bhk: property.bhk,
          size: property.size
        })
        setComparison(response.data)
      } catch (error) {
        toast.error('Failed to load price comparison')
        console.error(error)
      } finally {
        setCompareLoading(false)
      }
    }

    fetchComparison()
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800">
      {/* Header */}
      <div className="glass-effect border-b border-slate-700 sticky top-20 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300"
          >
            <FiChevronLeft /> Back
          </button>
          <div className="flex gap-4">
            <button className="text-2xl hover:text-indigo-400 transition">
              <FiShare2 />
            </button>
            <button
              onClick={() => setIsFavorite(!isFavorite)}
              className={`text-2xl transition ${isFavorite ? 'text-red-500' : 'text-slate-400 hover:text-red-500'}`}
            >
              <FiHeart fill={isFavorite ? 'currentColor' : 'none'} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Gallery */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="glass-effect rounded-2xl overflow-hidden"
            >
              <div className="grid grid-cols-3 gap-2 p-2 bg-gradient-to-br from-indigo-600 to-pink-600 h-80">
                {property.images.map((img, i) => (
                  <div key={i} className="text-6xl flex items-center justify-center bg-slate-900 rounded-lg">
                    {img}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Details */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-effect p-8 rounded-2xl"
            >
              <h1 className="text-4xl font-bold text-white mb-4">{property.title}</h1>
              <p className="text-lg text-slate-300 mb-6">📍 {property.location}</p>

              <div className="grid grid-cols-4 gap-4 mb-8">
                <div className="bg-slate-800 p-4 rounded-lg text-center">
                  <p className="text-slate-400 text-sm">BHK</p>
                  <p className="text-2xl font-bold text-white">{property.bhk}</p>
                </div>
                <div className="bg-slate-800 p-4 rounded-lg text-center">
                  <p className="text-slate-400 text-sm">Size</p>
                  <p className="text-2xl font-bold text-white">{property.size} sqft</p>
                </div>
                <div className="bg-slate-800 p-4 rounded-lg text-center">
                  <p className="text-slate-400 text-sm">Price/sqft</p>
                  <p className="text-2xl font-bold text-white">₹{property.pricePerSqft}k</p>
                </div>
                <div className="bg-slate-800 p-4 rounded-lg text-center">
                  <p className="text-slate-400 text-sm">Possession</p>
                  <p className="text-2xl font-bold text-white">{property.possession}</p>
                </div>
              </div>

              <p className="text-slate-300 leading-relaxed">{property.description}</p>
            </motion.div>

            {/* Amenities */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-effect p-8 rounded-2xl"
            >
              <h2 className="text-2xl font-bold text-white mb-6">✨ Amenities</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {property.amenities.map((amenity, i) => (
                  <div key={i} className="bg-gradient-to-r from-indigo-500/20 to-pink-500/20 p-4 rounded-lg text-center">
                    <p className="text-white font-semibold">{amenity}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Location Map */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="glass-effect p-8 rounded-2xl"
            >
              <h2 className="text-2xl font-bold text-white mb-6">📍 Location</h2>
              <div className="w-full h-64 bg-slate-800 rounded-lg flex items-center justify-center text-6xl">
                🗺️
              </div>
              <p className="text-slate-300 mt-4">
                Located in Ghatkopar East, one of Mumbai's premium residential areas. Excellent connectivity with metro stations, shopping centers, and schools nearby.
              </p>
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Price Card */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass-effect p-8 rounded-2xl sticky top-32"
            >
              <p className="text-slate-400 text-sm mb-2">TOTAL PRICE</p>
              <p className="text-4xl font-black gradient-text mb-6">
                {formatPrice(property.price)}
              </p>

              <div className="space-y-3 mb-6">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Price per sqft</span>
                  <span className="text-white font-semibold">₹{property.pricePerSqft}k</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Total area</span>
                  <span className="text-white font-semibold">{property.size} sq ft</span>
                </div>
              </div>

              <button className="btn-primary w-full mb-3">
                Contact Seller
              </button>
              <button className="btn-secondary w-full">
                Schedule Tour
              </button>
            </motion.div>

            {/* Price Comparison */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.05 }}
              className="glass-effect p-8 rounded-2xl"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white">🔎 Price Comparison</h3>
                {comparison && (
                  <span className="text-xs text-slate-400">Best: {formatPrice(comparison.best_price)}</span>
                )}
              </div>

              {compareLoading && (
                <div className="text-slate-300 text-sm">Loading offers...</div>
              )}

              {!compareLoading && comparison && (
                <div className="space-y-3">
                  {comparison.offers.map((offer) => (
                    <div key={offer.platform} className="bg-slate-800/60 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white font-semibold">{offer.platform}</span>
                        <span className="text-white font-bold">{formatPrice(offer.price)}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>{offer.includes}</span>
                        <span>Match {Math.round(offer.match_score * 100)}%</span>
                      </div>
                      <a
                        href={offer.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex mt-3 text-sm text-indigo-400 hover:text-indigo-300"
                      >
                        Visit site →
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Trust Score */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-effect p-8 rounded-2xl"
            >
              <h3 className="text-xl font-bold text-white mb-4">🛡️ Trust Score</h3>
              <div className="text-center mb-4">
                <p className="text-5xl font-black text-green-400">{property.trustScore}%</p>
                <p className="text-slate-300 text-sm mt-2">Verified Listing</p>
              </div>
              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-green-500 to-emerald-500" style={{ width: '85%' }} />
              </div>
            </motion.div>

            {/* Developer */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-effect p-8 rounded-2xl"
            >
              <h3 className="text-xl font-bold text-white mb-4">🏢 Developer</h3>
              <p className="text-white font-semibold mb-4">{property.developer}</p>
              <button className="btn-secondary w-full text-sm">
                View Other Properties
              </button>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  )
}
