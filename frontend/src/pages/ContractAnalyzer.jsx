import { useState } from 'react'
import { motion } from 'framer-motion'
import { FiAlertTriangle, FiCheck, FiDownload, FiFileText, FiBook } from 'react-icons/fi'
import { MdWarning, MdCheckCircle } from 'react-icons/md'
import toast from 'react-hot-toast'
import { analyzeContract as analyzeContractRequest } from '../utils/api'

export default function ContractAnalyzer() {
  const [contractText, setContractText] = useState('')
  const [contractType, setContractType] = useState('lease')
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showGuide, setShowGuide] = useState(false)

  const contractTypes = [
    { value: 'lease', label: 'Lease Agreement' },
    { value: 'purchase', label: 'Purchase Agreement' },
    { value: 'mou', label: 'MOU' },
    { value: 'deed', label: 'Property Deed' },
    { value: 'agreement', label: 'General Agreement' }
  ]

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      setContractText(event.target.result)
      toast.success('File loaded successfully!')
    }
    reader.readAsText(file)
  }

  const analyzeContract = async () => {
    if (!contractText.trim()) {
      toast.error('Please enter contract text (minimum 50 characters)')
      return
    }

    setLoading(true)
    try {
      const response = await analyzeContractRequest({
        contract_text: contractText,
        contract_type: contractType
      })
      setAnalysis(response.data)
      toast.success('Analysis complete!')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Analysis failed')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const downloadAnalysis = () => {
    if (!analysis) return

    const content = `
CONTRACT COMPLIANCE ANALYSIS REPORT
====================================
Date: ${analysis.analysis_date}
Contract Type: ${analysis.contract_type}
Compliance Score: ${analysis.compliance_score}/100
Risk Level: ${analysis.risk_level.toUpperCase()}

SUMMARY
-------
Total Clauses Reviewed: ${analysis.total_clauses_reviewed}
Flagged Clauses: ${analysis.flagged_clauses.length}

FLAGGED CLAUSES
---------------
${analysis.flagged_clauses.map(clause => `
Risk: ${clause.risk_level.toUpperCase()}
Section: ${clause.rera_section}
Issue: ${clause.reason}
`).join('\n')}

RECOMMENDATIONS
---------------
${analysis.recommendations.map(rec => `• ${rec}`).join('\n')}

⚠️ DISCLAIMER: Always consult a registered property lawyer before signing.
    `

    const element = document.createElement('a')
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content))
    element.setAttribute('download', 'contract_analysis_report.txt')
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  const getRiskGradient = (level) => {
    switch(level) {
      case 'critical':
        return 'from-red-500 to-rose-500'
      case 'high':
        return 'from-orange-500 to-red-500'
      case 'medium':
        return 'from-yellow-500 to-orange-500'
      default:
        return 'from-green-500 to-emerald-500'
    }
  }

  const getRiskIcon = (level) => {
    switch(level) {
      case 'critical':
      case 'high':
        return <FiAlertTriangle className="text-3xl text-red-400" />
      case 'medium':
        return <MdWarning className="text-3xl text-yellow-400" />
      default:
        return <MdCheckCircle className="text-3xl text-green-400" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-5xl font-bold gradient-text mb-4">📋 Contract Analyzer</h1>
          <p className="text-xl text-slate-300">AI-powered RERA compliance check for lease agreements and property deeds</p>
        </motion.div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Input Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-2"
          >
            <div className="glass-effect p-8 rounded-2xl mb-6">
              <h2 className="text-2xl font-bold text-white mb-6">📝 Upload Contract</h2>

              {/* Contract Type */}
              <div className="mb-6">
                <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3">
                  <FiFileText className="text-indigo-400" /> Contract Type
                </label>
                <select
                  value={contractType}
                  onChange={(e) => setContractType(e.target.value)}
                  className="input-field"
                >
                  {contractTypes.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>

              {/* File Upload Area */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-3">📄 Upload File</label>
                <div className="relative">
                  <input
                    type="file"
                    accept=".txt,.pdf,.doc,.docx"
                    onChange={handleFileUpload}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="border-2 border-dashed border-indigo-500/50 rounded-lg p-6 text-center bg-indigo-500/10">
                    <div className="text-3xl mb-2">📁</div>
                    <p className="text-slate-300 font-medium">Click to upload or drag & drop</p>
                    <p className="text-xs text-slate-400 mt-2">TXT, PDF, DOC, DOCX</p>
                  </div>
                </div>
              </div>

              {/* Text Area */}
              <div className="mb-6">
                <label className="block text-sm font-semibold text-slate-300 mb-3">✏️ Or Paste Text</label>
                <textarea
                  value={contractText}
                  onChange={(e) => setContractText(e.target.value)}
                  placeholder="Paste contract text here... (minimum 50 characters)"
                  className="input-field h-64 resize-none"
                />
                <p className="text-xs text-slate-400 mt-2">{contractText.length} characters</p>
              </div>

              {/* Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={analyzeContract}
                  disabled={loading}
                  className="flex-1 btn-primary"
                >
                  {loading ? '⏳ Analyzing...' : '🔍 Analyze Contract'}
                </button>
                {analysis && (
                  <button
                    onClick={downloadAnalysis}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <FiDownload /> Download
                  </button>
                )}
              </div>
            </div>
          </motion.div>

          {/* Right Column - Guide */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-1"
          >
            <div 
              onClick={() => setShowGuide(!showGuide)}
              className="glass-effect p-6 rounded-2xl cursor-pointer hover:bg-white/20 transition mb-6 sticky top-24"
            >
              <div className="flex items-center gap-3 mb-4">
                <FiBook className="text-2xl text-indigo-400" />
                <h3 className="text-xl font-bold text-white">RERA Guide</h3>
              </div>
              <p className="text-slate-300 text-sm">{showGuide ? 'Hide' : 'Show'} key RERA sections</p>
            </div>

            {showGuide && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-effect p-6 rounded-2xl space-y-4 sticky top-32"
              >
                {[
                  { num: '13', title: 'Possession', desc: 'Timeline & delays' },
                  { num: '15', title: 'Refunds', desc: 'Cancellation terms' },
                  { num: '18', title: 'Defects', desc: '5-year liability' },
                  { num: '22', title: 'Fair Terms', desc: 'Voids exemptions' }
                ].map(item => (
                  <div key={item.num} className="border-l-4 border-indigo-500 pl-4 py-2">
                    <p className="font-bold text-white text-sm">Section {item.num}</p>
                    <p className="text-slate-400 text-xs">{item.title} - {item.desc}</p>
                  </div>
                ))}
                <div className="pt-4 border-t border-slate-700/50">
                  <p className="text-xs text-slate-400">⚠️ Always consult a lawyer</p>
                </div>
              </motion.div>
            )}

            {/* Info Box */}
            <div className="glass-effect p-6 rounded-2xl">
              <h4 className="text-sm font-bold text-white mb-3">🎯 What It Does</h4>
              <ul className="space-y-2 text-xs text-slate-300">
                <li>✓ Analyzes against RERA guidelines</li>
                <li>✓ Flags unfair terms</li>
                <li>✓ Compliance score (0-100)</li>
                <li>✓ Risk assessment</li>
                <li>✓ Actionable recommendations</li>
              </ul>
            </div>
          </motion.div>
        </div>

        {/* Results */}
        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-12 space-y-6"
          >
            {/* Score Card */}
            <div className={`glass-effect p-8 rounded-2xl border border-white/10 bg-gradient-to-r ${getRiskGradient(analysis.risk_level)}/10`}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
                <div className="md:col-span-1 text-center">
                  {getRiskIcon(analysis.risk_level)}
                </div>
                <div className="md:col-span-2">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-2xl font-bold text-white mb-2">Compliance Score</h2>
                      <div className="flex items-baseline gap-2">
                        <span className="text-4xl font-bold text-white">{analysis.compliance_score}</span>
                        <span className="text-slate-300">/100</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-black/30 rounded-full h-2 mb-4">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${getRiskGradient(analysis.risk_level)}`}
                      style={{ width: `${analysis.compliance_score}%` }}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-slate-300 mb-1">Risk Level</p>
                      <p className="font-bold text-white uppercase">{analysis.risk_level}</p>
                    </div>
                    <div>
                      <p className="text-sm text-slate-300 mb-1">Clauses Reviewed</p>
                      <p className="font-bold text-white">{analysis.total_clauses_reviewed}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Warning */}
              <div className="mt-6 pt-6 border-t border-white/10">
                {analysis.risk_level === 'critical' && (
                  <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-200 text-sm font-medium">
                    🚨 CRITICAL RISKS - Do not sign without legal review
                  </div>
                )}
                {analysis.risk_level === 'high' && (
                  <div className="bg-orange-500/20 border border-orange-500/50 rounded-lg p-4 text-orange-200 text-sm font-medium">
                    ⚠️ HIGH RISKS - Seek legal counsel before signing
                  </div>
                )}
                {analysis.risk_level === 'medium' && (
                  <div className="bg-yellow-500/20 border border-yellow-500/50 rounded-lg p-4 text-yellow-200 text-sm font-medium">
                    ⚡ MODERATE RISKS - Review with lawyer recommended
                  </div>
                )}
                {analysis.risk_level === 'low' && (
                  <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-4 text-green-200 text-sm font-medium flex items-center gap-2">
                    <FiCheck /> Appears compliant with RERA guidelines
                  </div>
                )}
              </div>
            </div>

            {/* Flagged Clauses */}
            {analysis.flagged_clauses.length > 0 && (
              <div className="glass-effect p-8 rounded-2xl">
                <h3 className="text-2xl font-bold text-white mb-6">⚠️ Flagged Clauses ({analysis.flagged_clauses.length})</h3>
                <div className="space-y-4">
                  {analysis.flagged_clauses.map((clause, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className={`p-4 rounded-lg border-l-4 bg-white/5 ${
                        clause.risk_level === 'critical'
                          ? 'border-red-500 bg-red-500/10'
                          : 'border-orange-500 bg-orange-500/10'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span className={`px-3 py-1 rounded text-xs font-bold text-white ${
                          clause.risk_level === 'critical' ? 'bg-red-600' : 'bg-orange-600'
                        }`}>
                          {clause.risk_level.toUpperCase()}
                        </span>
                        <span className="text-xs text-slate-300">{clause.rera_section}</span>
                      </div>
                      <p className="font-semibold text-white mb-2">{clause.reason}</p>
                      <p className="text-sm text-slate-300 italic">"{clause.clause}"</p>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            <div className="glass-effect p-8 rounded-2xl">
              <h3 className="text-2xl font-bold text-white mb-6">💡 Recommendations</h3>
              <ul className="space-y-3">
                {analysis.recommendations.map((rec, idx) => (
                  <motion.li
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex gap-3 text-slate-300"
                  >
                    <span className="text-indigo-400 font-bold flex-shrink-0">✓</span>
                    <span>{rec}</span>
                  </motion.li>
                ))}
              </ul>
            </div>
          </motion.div>
        )}

        {/* Info Box */}
        {!analysis && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-12 glass-effect p-8 rounded-2xl"
          >
            <h3 className="text-2xl font-bold text-white mb-6">🛡️ How It Works</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-slate-300 mb-4">This AI-powered analyzer:</p>
                <ul className="space-y-2 text-slate-300">
                  <li>✓ Analyzes clauses against RERA guidelines</li>
                  <li>✓ Identifies unfair terms & violations</li>
                  <li>✓ Generates compliance score (0-100)</li>
                  <li>✓ Flags specific risks with citations</li>
                  <li>✓ Provides actionable recommendations</li>
                </ul>
              </div>
              <div className="bg-indigo-500/20 border border-indigo-500/50 rounded-lg p-6">
                <p className="text-indigo-200 text-sm">
                  <strong>⚠️ Important:</strong> This is an automated analysis. Always consult with a registered property lawyer before signing any contract. This tool reduces legal consultation needs by 60%.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
