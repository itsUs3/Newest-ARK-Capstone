import { useState } from 'react'
import { motion } from 'framer-motion'
import { FiAlertTriangle, FiCheck } from 'react-icons/fi'
import { MdWarning, MdCheckCircle } from 'react-icons/md'
import toast from 'react-hot-toast'
import { detectFraud as detectFraudRequest } from '../utils/api'

export default function FraudDetector() {
  const [formData, setFormData] = useState({
    propertyId: '',
    title: '',
    description: ''
  })
  
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const detectFraud = async () => {
    if (!formData.title.trim()) {
      toast.error('Please enter property title')
      return
    }

    setLoading(true)
    try {
      const response = await detectFraudRequest({
        property_id: formData.propertyId || `prop_${Date.now()}`,
        title: formData.title,
        description: formData.description
      })
      setResult(response.data)
      toast.success('Analysis complete!')
    } catch (error) {
      toast.error('Failed to analyze property')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (level) => {
    switch(level) {
      case 'LOW':
        return 'from-green-500 to-emerald-500'
      case 'MEDIUM':
        return 'from-yellow-500 to-orange-500'
      case 'HIGH':
        return 'from-red-500 to-rose-500'
      default:
        return 'from-slate-500 to-slate-600'
    }
  }

  const getRiskIcon = (level) => {
    switch(level) {
      case 'LOW':
        return <MdCheckCircle className="text-2xl text-green-400" />
      case 'MEDIUM':
        return <MdWarning className="text-2xl text-yellow-400" />
      case 'HIGH':
        return <FiAlertTriangle className="text-2xl text-red-400" />
      default:
        return <MdWarning className="text-2xl text-slate-400" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-6xl mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-5xl font-bold gradient-text mb-4">🛡️ Fraud Detector</h1>
          <p className="text-xl text-slate-300">Identify scams, duplicates, and red flags instantly</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-1"
          >
            <div className="glass-effect p-8 rounded-2xl sticky top-24">
              <h2 className="text-2xl font-bold text-white mb-6">Analyze Listing</h2>

              {/* Property ID (optional) */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-2">Property ID (Optional)</label>
                <input
                  type="text"
                  value={formData.propertyId}
                  onChange={(e) => setFormData({ ...formData, propertyId: e.target.value })}
                  placeholder="e.g., prop_12345"
                  className="input-field text-sm"
                />
              </div>

              {/* Title */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-2">📝 Property Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., 2 BHK Flat in Mumbai"
                  className="input-field"
                />
              </div>

              {/* Description */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-2">📄 Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Paste listing description here..."
                  rows={5}
                  className="input-field resize-none"
                />
              </div>

              <button
                onClick={detectFraud}
                disabled={loading}
                className="btn-primary w-full"
              >
                {loading ? '⏳ Analyzing...' : '🔍 Check Listing'}
              </button>

              <p className="text-xs text-slate-400 mt-4 text-center">
                Analyzes for scams, duplicates, and suspicious patterns
              </p>
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
                {/* Trust Score */}
                <div className={`glass-effect p-8 rounded-2xl bg-gradient-to-br ${getRiskColor(result.risk_level)}/10`}>
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <p className="text-slate-400 text-sm mb-2">TRUST SCORE</p>
                      <p className="text-5xl font-black gradient-text">{result.trust_score.toFixed(0)}</p>
                      <p className="text-slate-300 mt-2">Out of 100</p>
                    </div>
                    <div className="text-center">
                      {getRiskIcon(result.risk_level)}
                      <p className={`text-2xl font-bold mt-3 bg-gradient-to-r ${getRiskColor(result.risk_level)} bg-clip-text text-transparent`}>
                        {result.risk_level} RISK
                      </p>
                    </div>
                  </div>

                  {/* Trust Score Gauge */}
                  <div className="mt-8">
                    <div className="w-full h-4 bg-slate-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${result.trust_score}%` }}
                        transition={{ duration: 1 }}
                        className={`h-full bg-gradient-to-r ${getRiskColor(result.risk_level)}`}
                      />
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-slate-400">
                      <span>Suspicious</span>
                      <span>Trustworthy</span>
                    </div>
                  </div>

                  {/* Verdict */}
                  <div className="mt-6 pt-6 border-t border-slate-700">
                    <div className="flex items-center gap-3">
                      {result.risk_level === 'LOW' && (!result.flags || result.flags.length === 0) && (
                        <>
                          <MdCheckCircle className="text-3xl text-green-400" />
                          <div>
                            <p className="font-bold text-white">This looks legitimate! ✅</p>
                            <p className="text-slate-300 text-sm">No major red flags detected</p>
                          </div>
                        </>
                      )}
                      {result.risk_level === 'LOW' && result.flags && result.flags.length > 0 && (
                        <>
                          <MdWarning className="text-3xl text-yellow-400" />
                          <div>
                            <p className="font-bold text-white">Issues detected ⚠️</p>
                            <p className="text-slate-300 text-sm">Red flags found — review the flagged concerns below</p>
                          </div>
                        </>
                      )}
                      {result.risk_level === 'MEDIUM' && (
                        <>
                          <MdWarning className="text-3xl text-yellow-400" />
                          <div>
                            <p className="font-bold text-white">Proceed with caution ⚠️</p>
                            <p className="text-slate-300 text-sm">Some concerns detected, verify further</p>
                          </div>
                        </>
                      )}
                      {result.risk_level === 'HIGH' && (
                        <>
                          <FiAlertTriangle className="text-3xl text-red-400" />
                          <div>
                            <p className="font-bold text-white">High risk detected! 🚨</p>
                            <p className="text-slate-300 text-sm">Consider alternative listings</p>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Red Flags */}
                {result.flags && result.flags.length > 0 && (
                  <div className="glass-effect p-8 rounded-2xl">
                    <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                      <FiAlertTriangle className="text-yellow-400" /> Detected Issues
                    </h3>
                    <div className="space-y-3">
                      {result.flags.map((flag, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.1 }}
                          className="bg-red-500/10 border border-red-500/30 p-4 rounded-lg flex items-start gap-3"
                        >
                          <MdWarning className="text-red-400 text-xl mt-1 flex-shrink-0" />
                          <span className="text-red-200">{flag}</span>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tips */}
                <div className="glass-effect p-8 rounded-2xl">
                  <h3 className="text-xl font-bold text-white mb-4">💡 Safety Tips</h3>
                  <div className="space-y-3 text-slate-300">
                    <div className="flex items-start gap-3">
                      <span className="text-green-400 font-bold">✓</span>
                      <span>Always verify property with RERA registration</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="text-green-400 font-bold">✓</span>
                      <span>Check on multiple platforms - compare prices and photos</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="text-green-400 font-bold">✓</span>
                      <span>Never transfer money via Western Union or Crypto</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="text-green-400 font-bold">✓</span>
                      <span>Visit property in person before making decisions</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="text-green-400 font-bold">✓</span>
                      <span>Check our price analyzer to ensure fair pricing</span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {!result && (
              <div className="glass-effect p-12 rounded-2xl text-center">
                <FiAlertTriangle className="text-6xl text-slate-500 mx-auto mb-4 opacity-50" />
                <p className="text-2xl text-slate-300">Enter property details to analyze ☝️</p>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  )
}
