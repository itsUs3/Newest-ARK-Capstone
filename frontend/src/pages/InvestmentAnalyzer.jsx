import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { FiAlertCircle, FiExternalLink, FiLoader, FiTrendingUp } from 'react-icons/fi'
import axios from 'axios'
import toast from 'react-hot-toast'
import ROIDashboard from '../components/ROIDashboard'

export default function InvestmentAnalyzer() {
  const [formData, setFormData] = useState({
    price: 50,
    price_unit: 'Lakh',
    location: 'Mumbai',
    bhk: 2,
    size: 1000,
    investment_horizon: 5,
    risk_tolerance: 'moderate'
  })

  const [forecast, setForecast] = useState(null)
  const [marketInsights, setMarketInsights] = useState(null)
  const [marketAlerts, setMarketAlerts] = useState(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('input')

  const presetLocations = ['Mumbai', 'Bangalore', 'Delhi', 'Pune', 'Hyderabad']

  const estimatedINR = useMemo(() => {
    const amount = Number(formData.price) || 0
    const multiplier = formData.price_unit === 'Crore' ? 10000000 : 100000
    return Math.round(amount * multiplier)
  }, [formData.price, formData.price_unit])

  const formatCurrency = (value) => {
    const numeric = Number(value) || 0
    if (numeric >= 10000000) return `Rs ${(numeric / 10000000).toFixed(2)} Cr`
    if (numeric >= 100000) return `Rs ${(numeric / 100000).toFixed(2)} L`
    return `Rs ${numeric.toLocaleString('en-IN')}`
  }

  const loadEvidence = async (location) => {
    setEvidenceLoading(true)
    try {
      const [insightsRes, alertsRes] = await Promise.all([
        axios.get(`/api/genai/market-insights/${encodeURIComponent(location)}`),
        axios.get(`/api/genai/market-alerts/${encodeURIComponent(location)}`, {
          params: { n_results: 4 }
        })
      ])
      setMarketInsights(insightsRes.data)
      setMarketAlerts(alertsRes.data)
    } catch (error) {
      setMarketInsights(null)
      setMarketAlerts(null)
      toast.error('Could not fetch live market evidence')
      console.error(error)
    } finally {
      setEvidenceLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: name === 'price'
        ? Math.max(0, parseFloat(value) || 0)
        : (name === 'bhk' || name === 'size' || name === 'investment_horizon' ? parseInt(value) || 0 : value)
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (estimatedINR <= 0) {
      toast.error('Enter a valid property price')
      return
    }

    if (!formData.location) {
      toast.error('Select a location')
      return
    }

    setLoading(true)

    try {
      const payload = {
        price: estimatedINR,
        location: formData.location,
        bhk: formData.bhk,
        size: formData.size,
        investment_horizon: formData.investment_horizon,
        risk_tolerance: formData.risk_tolerance,
        amenities: []
      }

      const [forecastRes] = await Promise.all([
        axios.post('/api/genai/investment-forecast', payload),
        loadEvidence(formData.location)
      ])

      setForecast(forecastRes.data)
      setActiveTab('results')
      toast.success('Investment forecast generated!')
    } catch (error) {
      const message = error?.response?.data?.detail || 'Failed to generate forecast'
      toast.error(message)
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleLocationQuickView = async (loc) => {
    setFormData(prev => ({ ...prev, location: loc }))
    await loadEvidence(loc)
  }

  return (
    <div className="min-h-screen bg-slate-950 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-7"
        >
          <h1 className="text-3xl sm:text-4xl font-semibold text-white tracking-tight">Investment Analyzer</h1>
          <p className="text-slate-400 mt-2 max-w-3xl">Evidence-backed ROI forecasting with live market metrics, curated news signals, and risk-aware assumptions.</p>
        </motion.div>

        {/* Tab Navigation */}
        <div className="mb-6 inline-flex rounded-xl border border-slate-800 bg-slate-900 p-1">
          {['input', 'results'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              disabled={tab === 'results' && !forecast}
              className={`px-4 sm:px-5 py-2 rounded-lg text-sm font-medium transition ${
                activeTab === tab
                  ? 'bg-slate-100 text-slate-900'
                  : forecast && tab === 'results'
                    ? 'text-slate-300 hover:bg-slate-800'
                    : 'text-slate-500 cursor-not-allowed'
              }`}
            >
              {tab === 'input' ? 'Analysis Input' : 'Results'}
            </button>
          ))}
        </div>

        {/* Input Tab */}
        {activeTab === 'input' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-5"
          >
            {/* Input Form */}
            <div className="lg:col-span-1">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.25)]">
                <div className="mb-5 flex items-center justify-between gap-3">
                  <h2 className="text-xl font-semibold text-white">Property Details</h2>
                  <span className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs text-slate-300">
                    Est. {formatCurrency(estimatedINR)}
                  </span>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Property Price */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Property Price (₹)
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        name="price"
                        value={formData.price}
                        onChange={handleInputChange}
                        className="input-field flex-1"
                        placeholder="e.g., 50"
                      />
                      <select
                        name="price_unit"
                        className="input-field w-24"
                        value={formData.price_unit}
                        onChange={handleInputChange}
                      >
                        <option value="Lakh">Lakh</option>
                        <option value="Crore">Crore</option>
                      </select>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">Amount is converted internally to INR for forecasting.</p>
                  </div>

                  {/* Location */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Location
                    </label>
                    <select
                      name="location"
                      value={formData.location}
                      onChange={handleInputChange}
                      className="input-field w-full"
                    >
                      {presetLocations.map(loc => (
                        <option key={loc} value={loc}>{loc}</option>
                      ))}
                    </select>
                  </div>

                  {/* BHK */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      BHK
                    </label>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4].map(bhk => (
                        <button
                          key={bhk}
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, bhk }))}
                          className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                            formData.bhk === bhk
                              ? 'bg-slate-100 text-slate-900'
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          {bhk}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Size */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Size (sq ft)
                    </label>
                    <input
                      type="number"
                      name="size"
                      value={formData.size}
                      onChange={handleInputChange}
                      className="input-field w-full"
                      placeholder="e.g., 1000"
                    />
                  </div>

                  {/* Investment Horizon */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Investment Horizon (Years)
                    </label>
                    <div className="flex gap-2">
                      {[3, 5, 7, 10].map(years => (
                        <button
                          key={years}
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, investment_horizon: years }))}
                          className={`flex-1 py-2 rounded-lg font-medium transition text-sm ${
                            formData.investment_horizon === years
                              ? 'bg-slate-100 text-slate-900'
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          {years}yr
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Risk Tolerance */}
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Risk Tolerance
                    </label>
                    <div className="flex gap-2">
                      {['low', 'moderate', 'high'].map(risk => (
                        <button
                          key={risk}
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, risk_tolerance: risk }))}
                          className={`flex-1 py-2 rounded-lg font-medium transition text-sm ${
                            formData.risk_tolerance === risk
                              ? 'bg-slate-100 text-slate-900'
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          {risk.charAt(0).toUpperCase() + risk.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-white disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <FiLoader className="animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>Generate Forecast</>
                    )}
                  </button>
                </form>
              </div>

              {/* Information Box */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6 mt-5">
                <h3 className="font-semibold text-slate-100 mb-3">How This Works</h3>
                <div className="text-sm text-slate-400 space-y-2">
                  <p>Includes net ROI after costs, vacancy, and upkeep.</p>
                  <p>Runs scenario analysis based on market volatility.</p>
                  <p>Uses recent local news as a bounded adjustment signal.</p>
                  <p>Shows transparent evidence cards for metrics and sources.</p>
                </div>
              </div>
            </div>

            {/* Right Side - Evidence-backed Panels */}
            <div className="lg:col-span-2 space-y-6">
              {/* Evidence Header */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-semibold text-white mb-1">Live Evidence</h2>
                    <p className="text-slate-400 text-sm">Location: <span className="font-medium text-slate-100">{formData.location}</span></p>
                  </div>
                  <button
                    type="button"
                    onClick={() => loadEvidence(formData.location)}
                    className="px-4 py-2 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm"
                  >
                    Refresh Evidence
                  </button>
                </div>
              </div>

              {/* Market Metrics */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Market Metrics</h2>

                {evidenceLoading ? (
                  <div className="text-slate-300 flex items-center gap-2"><FiLoader className="animate-spin" /> Loading live market evidence...</div>
                ) : marketInsights ? (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">YoY Growth</p>
                        <p className="text-2xl text-slate-100 font-semibold mt-1">{((marketInsights.market_metrics?.yoy_growth || 0) * 100).toFixed(1)}%</p>
                      </div>
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">Avg Rental Yield</p>
                        <p className="text-2xl text-slate-100 font-semibold mt-1">{((marketInsights.market_metrics?.avg_rental_yield || 0) * 100).toFixed(2)}%</p>
                      </div>
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">Demand Score</p>
                        <p className="text-2xl text-slate-100 font-semibold mt-1">{Number(marketInsights.market_metrics?.demand_score || 0).toFixed(1)}</p>
                      </div>
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">Volatility</p>
                        <p className="text-2xl text-slate-100 font-semibold mt-1 capitalize">{marketInsights.historical_performance?.volatility || 'Unknown'}</p>
                      </div>
                    </div>

                    <div className="border border-slate-800 rounded-xl p-4 bg-slate-950/50 space-y-2">
                      <p className="text-sm text-slate-300"><span className="font-medium text-slate-100">Method:</span> {marketInsights.rag_context?.retrieval_method || 'rule_based'} retrieval + cost-aware ROI model + bounded news adjustment.</p>
                      <p className="text-sm text-slate-300"><span className="font-medium text-slate-100">Recommendation:</span> {marketInsights.recommendation}</p>
                    </div>
                  </>
                ) : (
                  <div className="text-slate-300 flex items-center gap-2"><FiAlertCircle /> No live market metrics loaded yet. Select location and refresh evidence.</div>
                )}
              </div>

              {/* News Evidence */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Market News Evidence</h2>
                {evidenceLoading ? (
                  <div className="text-slate-300 flex items-center gap-2"><FiLoader className="animate-spin" /> Fetching latest local market news...</div>
                ) : marketAlerts ? (
                  <>
                    <div className="mb-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">Impact Level</p>
                        <p className="text-lg font-semibold text-white mt-1">{(marketAlerts.impact_level || 'neutral').replace(/_/g, ' ')}</p>
                      </div>
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">Avg Impact Score</p>
                        <p className="text-lg font-semibold text-white mt-1">{Number(marketAlerts.avg_impact_score || 0).toFixed(2)}</p>
                      </div>
                      <div className="bg-slate-950/70 rounded-xl p-4 border border-slate-800">
                        <p className="text-xs text-slate-400">Articles Used</p>
                        <p className="text-lg font-semibold text-white mt-1">{marketAlerts.articles?.length || 0}</p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {(marketAlerts.articles || []).slice(0, 4).map((article, idx) => (
                        <div key={`${article.url || article.title}-${idx}`} className="p-4 rounded-xl bg-slate-950/50 border border-slate-800">
                          <p className="text-sm font-semibold text-white">{article.title}</p>
                          <div className="mt-2 text-xs text-slate-400 flex items-center gap-3 flex-wrap">
                            <span>{article.source || 'Unknown source'}</span>
                            <span>Impact: {Number(article.impact_score || 0).toFixed(2)}</span>
                            {article.url ? (
                              <a href={article.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-slate-200 hover:text-white underline underline-offset-4">
                                Open <FiExternalLink />
                              </a>
                            ) : null}
                          </div>
                        </div>
                      ))}

                      {!(marketAlerts.articles || []).length ? (
                        <p className="text-slate-300 text-sm">No recent location-specific news found. Forecast uses base market metrics with bounded fallback.</p>
                      ) : null}
                    </div>
                  </>
                ) : (
                  <div className="text-slate-300 flex items-center gap-2"><FiAlertCircle /> No news evidence loaded yet. Use Refresh Evidence.</div>
                )}
              </div>

              {/* Quick location evidence grid */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-6">
                <h2 className="text-xl font-semibold text-white mb-4">Quick Location Presets</h2>
                <div className="flex flex-wrap gap-2">
                  {presetLocations.map(loc => (
                    <button
                      type="button"
                      key={loc}
                      onClick={() => handleLocationQuickView(loc)}
                      className={`rounded-lg px-3 py-2 border text-sm transition ${formData.location === loc ? 'border-slate-300 bg-slate-100 text-slate-900' : 'border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
                    >
                      <span className="inline-flex items-center gap-1"><FiTrendingUp /> {loc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Results Tab */}
        {activeTab === 'results' && forecast && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <ROIDashboard forecast={forecast} propertyDetails={formData} />
          </motion.div>
        )}
      </div>
    </div>
  )
}
