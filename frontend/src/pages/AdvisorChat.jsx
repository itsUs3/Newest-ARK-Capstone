import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FiSend } from 'react-icons/fi'
import axios from 'axios'
import toast from 'react-hot-toast'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

export default function AdvisorChat() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hey! 👋 I'm your real estate advisor. Ask me anything about properties, prices, locations, investments, or how to avoid scams! What's on your mind?",
      sender: 'bot'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [investmentData, setInvestmentData] = useState(null)
  const [showROIDashboard, setShowROIDashboard] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const isInvestmentQuery = (msg) => {
    const investmentKeywords = ['roi', 'investment', 'return', 'profit', 'forecast', 'scenario', 'appreciation', 'yield', 'hold', 'bullish', 'bearish', 'moderate']
    return investmentKeywords.some(keyword => msg.toLowerCase().includes(keyword))
  }

  const extractPropertyDetails = (msg) => {
    // Basic extraction of property details from natural language
    const priceMatch = msg.match(/₹\s*([\d.]+)\s*(cr|crore|lakh|l)?/i)
    const bhkMatch = msg.match(/(\d+)\s*bhk/i)
    const sizeMatch = msg.match(/(\d+)\s*(?:sq|sq\.?ft|sqft)/i)
    
    const locationMatch = msg.match(/in\s+([A-Za-z\s]+)(?:\.|,|$)/i)
    
    return {
      price: priceMatch ? parseFloat(priceMatch[1]) * (priceMatch[2]?.toLowerCase().includes('cr') ? 10000000 : 100000) : 5000000,
      location: locationMatch ? locationMatch[1].trim() : 'Mumbai',
      bhk: bhkMatch ? parseInt(bhkMatch[1]) : 2,
      size: sizeMatch ? parseInt(sizeMatch[1]) : 1000
    }
  }

  const generateROIChartData = (forecast) => {
    if (!forecast?.scenario_analysis) return []
    
    const scenarios = forecast.scenario_analysis.scenarios
    return [
      {
        name: 'Bearish',
        roi_5yr: scenarios.bearish.roi_5yr,
        roi_10yr: scenarios.bearish.roi_10yr
      },
      {
        name: 'Moderate',
        roi_5yr: scenarios.moderate.roi_5yr,
        roi_10yr: scenarios.moderate.roi_10yr
      },
      {
        name: 'Bullish',
        roi_5yr: scenarios.bullish.roi_5yr,
        roi_10yr: scenarios.bullish.roi_10yr
      }
    ]
  }

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = {
      id: messages.length + 1,
      text: input,
      sender: 'user'
    }
    setMessages([...messages, userMessage])
    setInput('')
    setLoading(true)

    try {
      // Check if this is an investment query
      if (isInvestmentQuery(input)) {
        // Extract property details from query
        const propertyDetails = extractPropertyDetails(input)
        
        // Call investment forecast endpoint
        const response = await axios.post('/api/genai/investment-forecast', {
          ...propertyDetails,
          investment_horizon: 5,
          risk_tolerance: 'moderate'
        })

        setInvestmentData(response.data)
        setShowROIDashboard(true)

        // Add investment analysis message
        const investmentMessage = {
          id: messages.length + 2,
          text: response.data.investment_thesis || response.data.formatted_thesis,
          sender: 'bot',
          type: 'investment',
          data: response.data
        }
        setMessages(prev => [...prev, investmentMessage])
      } else {
        // Regular chat query
        const response = await axios.post('/api/genai/chat', {
          message: input
        })

        const botMessage = {
          id: messages.length + 2,
          text: response.data.response,
          sender: 'bot'
        }
        setMessages(prev => [...prev, botMessage])
      }
    } catch (error) {
      toast.error('Failed to get response')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const suggestedQuestions = [
    "What's a fair price for 2BHK in Mumbai?",
    "Tell me ROI for a 1.5Cr property in Bangalore",
    "How do I spot fake listings?",
    "Best investment areas for 5-year hold?"
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 py-12">
      <div className="max-w-4xl mx-auto px-4 h-screen flex flex-col">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <h1 className="text-4xl font-bold gradient-text mb-2">🤖 Real Estate AI Advisor</h1>
          <p className="text-slate-300">Ask about properties, prices, investments & ROI forecasts</p>
        </motion.div>

        {/* Messages Container */}
        <div className="flex-1 glass-effect rounded-2xl p-6 overflow-y-auto mb-6 space-y-4">
          {messages.map((msg, i) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-2xl ${
                  msg.sender === 'user'
                    ? 'bg-gradient-to-r from-indigo-600 to-pink-600 text-white rounded-br-none'
                    : 'bg-slate-700 text-slate-100 rounded-bl-none'
                } px-4 py-3 rounded-2xl`}
              >
                <p className="leading-relaxed">{msg.text}</p>
                
                {/* ROI Dashboard for Investment Messages */}
                {msg.type === 'investment' && msg.data && (
                  <div className="mt-4 space-y-4">
                    {/* ROI Scenarios Chart */}
                    <div className="bg-slate-800 rounded-lg p-4">
                      <h3 className="font-bold mb-3 text-pink-300">📊 ROI Scenarios (5yr vs 10yr)</h3>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={generateROIChartData(msg.data)}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#666" />
                          <XAxis dataKey="name" stroke="#999" />
                          <YAxis stroke="#999" />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #666' }}
                            formatter={(value) => `${value.toFixed(1)}%`}
                          />
                          <Legend />
                          <Bar dataKey="roi_5yr" fill="#818cf8" name="5-Year ROI %" />
                          <Bar dataKey="roi_10yr" fill="#ec4899" name="10-Year ROI %" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Capital Appreciation Timeline */}
                    {msg.data.base_roi_analysis && (
                      <div className="bg-slate-800 rounded-lg p-4">
                        <h3 className="font-bold mb-3 text-indigo-300">💰 Capital Appreciation Over Time</h3>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div className="bg-slate-700 p-3 rounded">
                            <p className="text-slate-400">Initial Investment</p>
                            <p className="text-green-400 font-bold">₹{(msg.data.base_roi_analysis.capital_appreciation.annual_rate * 100).toFixed(0)}%/yr</p>
                          </div>
                          <div className="bg-slate-700 p-3 rounded">
                            <p className="text-slate-400">5-Year Value</p>
                            <p className="text-pink-400 font-bold">₹{(msg.data.base_roi_analysis.capital_appreciation.projected_value / 10000000).toFixed(1)}Cr</p>
                          </div>
                          <div className="bg-slate-700 p-3 rounded">
                            <p className="text-slate-400">Capital Gain</p>
                            <p className="text-yellow-400 font-bold">+{msg.data.base_roi_analysis.capital_appreciation.gain_percentage.toFixed(1)}%</p>
                          </div>
                          <div className="bg-slate-700 p-3 rounded">
                            <p className="text-slate-400">Rental Yield</p>
                            <p className="text-blue-400 font-bold">{msg.data.base_roi_analysis.rental_income.yield_percentage.toFixed(1)}%/yr</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Scenario Probability */}
                    {msg.data.scenario_analysis?.scenarios && (
                      <div className="bg-slate-800 rounded-lg p-4">
                        <h3 className="font-bold mb-3 text-purple-300">📈 Scenario Probabilities</h3>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between items-center bg-slate-700 p-2 rounded">
                            <span>🟢 Bullish Scenario</span>
                            <span className="text-green-400 font-bold">{msg.data.scenario_analysis.scenarios.bullish.probability}</span>
                          </div>
                          <div className="flex justify-between items-center bg-slate-700 p-2 rounded">
                            <span>🟡 Moderate Scenario</span>
                            <span className="text-yellow-400 font-bold">{msg.data.scenario_analysis.scenarios.moderate.probability}</span>
                          </div>
                          <div className="flex justify-between items-center bg-slate-700 p-2 rounded">
                            <span>🔴 Bearish Scenario</span>
                            <span className="text-red-400 font-bold">{msg.data.scenario_analysis.scenarios.bearish.probability}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Action Items */}
                    <div className="bg-slate-800 rounded-lg p-4">
                      <h3 className="font-bold mb-3 text-cyan-300">🎬 Next Steps</h3>
                      <ul className="text-sm space-y-2">
                        <li className="flex gap-2">
                          <span>✓</span>
                          <span>Verify property title & legal documentation</span>
                        </li>
                        <li className="flex gap-2">
                          <span>✓</span>
                          <span>Compare with similar properties in neighborhood</span>
                        </li>
                        <li className="flex gap-2">
                          <span>✓</span>
                          <span>Validate rental income projections locally</span>
                        </li>
                        <li className="flex gap-2">
                          <span>✓</span>
                          <span>Factor in maintenance & property taxes</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-slate-700 text-slate-100 px-4 py-3 rounded-2xl rounded-bl-none">
                <div className="flex gap-2">
                  <span className="animate-bounce">●</span>
                  <span className="animate-bounce delay-100">●</span>
                  <span className="animate-bounce delay-200">●</span>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions */}
        {messages.length === 1 && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-6"
          >
            <p className="text-sm text-slate-400 mb-3">💡 Try asking:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(q)
                  }}
                  className="text-left px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-300 text-sm transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Input */}
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && sendMessage()}
            placeholder="Ask me anything... 🏠"
            disabled={loading}
            className="input-field flex-1"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="btn-primary px-6 flex items-center gap-2 disabled:opacity-50"
          >
            <FiSend />
          </button>
        </div>

        <p className="text-xs text-slate-500 text-center mt-4">
          💬 Powered by GPT-4 + RAG | Always verify information independently
        </p>
      </div>
    </div>
  )
}
