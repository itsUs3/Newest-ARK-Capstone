import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart, Line,
  BarChart, Bar,
  PieChart, Pie, Cell,
  AreaChart, Area,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'

export default function ROIDashboard({ forecast, propertyDetails }) {
  const [activeTab, setActiveTab] = useState('overview')

  if (!forecast) {
    return <div className="p-6 text-center text-slate-400">No forecast data available</div>
  }

  const roi = forecast.base_roi_analysis
  const scenarios = forecast.scenario_analysis?.scenarios || {}
  const property = forecast.property || propertyDetails || {}
  const holdPeriod = roi?.hold_period || forecast.scenario_analysis?.horizon_years || 5
  const longHorizon = forecast.scenario_analysis?.long_horizon_years || 10
  const annualRateDecimal = roi?.capital_appreciation?.annual_rate_decimal ?? roi?.capital_appreciation?.annual_rate ?? 0
  const annualRatePercent = roi?.capital_appreciation?.annual_rate_percent ?? (annualRateDecimal * 100)

  // Prepare chart data - Capital Appreciation Over Years
  const appreciationData = roi?.capital_appreciation ? [
    { year: 0, value: property.price },
    { year: 1, value: property.price * (1 + annualRateDecimal) },
    { year: 3, value: property.price * Math.pow(1 + annualRateDecimal, 3) },
    { year: holdPeriod, value: property.price * Math.pow(1 + annualRateDecimal, holdPeriod) },
    { year: Math.max(holdPeriod + 2, 7), value: property.price * Math.pow(1 + annualRateDecimal, Math.max(holdPeriod + 2, 7)) },
    { year: longHorizon, value: property.price * Math.pow(1 + annualRateDecimal, longHorizon) }
  ] : []

  // Scenario Comparison Data
  const scenarioData = scenarios ? [
    {
      name: 'Bearish',
      roi_base_horizon: scenarios.bearish?.roi_base_horizon ?? scenarios.bearish?.roi_5yr ?? 0,
      roi_long_horizon: scenarios.bearish?.roi_long_horizon ?? scenarios.bearish?.roi_10yr ?? 0,
      color: '#ef4444'
    },
    {
      name: 'Moderate',
      roi_base_horizon: scenarios.moderate?.roi_base_horizon ?? scenarios.moderate?.roi_5yr ?? 0,
      roi_long_horizon: scenarios.moderate?.roi_long_horizon ?? scenarios.moderate?.roi_10yr ?? 0,
      color: '#eab308'
    },
    {
      name: 'Bullish',
      roi_base_horizon: scenarios.bullish?.roi_base_horizon ?? scenarios.bullish?.roi_5yr ?? 0,
      roi_long_horizon: scenarios.bullish?.roi_long_horizon ?? scenarios.bullish?.roi_10yr ?? 0,
      color: '#22c55e'
    }
  ] : []

  // Return Composition Data
  const returnComposition = roi?.rental_income ? [
    {
      name: 'Capital Appreciation',
      value: roi.capital_appreciation?.gain_percentage || 0,
      color: '#6366f1'
    },
    {
      name: 'Rental Income',
      value: roi.rental_income?.yield_percentage * holdPeriod || 0,
      color: '#ec4899'
    }
  ] : []

  // Format currency
  const formatCurrency = (value) => {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
    return `₹${value.toFixed(0)}`
  }

  return (
    <div className="w-full bg-gradient-to-b from-slate-900 to-slate-800 rounded-2xl p-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-3xl font-bold gradient-text">📊 Investment ROI Dashboard</h2>
            <p className="text-slate-400 mt-1">{property.bhk} BHK in {property.location}</p>
          </div>
          <div className="text-right">
            <p className="text-slate-400 text-sm">Investment Amount</p>
            <p className="text-2xl font-bold text-green-400">{formatCurrency(property.price)}</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 flex-wrap">
          {['overview', 'appreciation', 'scenarios', 'returns', 'details'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                activeTab === tab
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </motion.div>

      {/* TAB: Overview */}
      {activeTab === 'overview' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <p className="text-slate-400 text-sm mb-1">Annualized ROI</p>
              <p className="text-3xl font-bold text-green-400">
                {roi?.total_return?.net_annualized_roi?.toFixed(1) || roi?.total_return?.annualized_roi?.toFixed(1) || '0'}%
              </p>
              <p className="text-xs text-slate-500 mt-2">Net per year</p>
            </div>

            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <p className="text-slate-400 text-sm mb-1">{holdPeriod}-Year ROI</p>
              <p className="text-3xl font-bold text-blue-400">
                {roi?.total_return?.net_percentage?.toFixed(1) || roi?.total_return?.percentage?.toFixed(1) || '0'}%
              </p>
              <p className="text-xs text-slate-500 mt-2">Net total return</p>
            </div>

            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <p className="text-slate-400 text-sm mb-1">Capital Gain</p>
              <p className="text-3xl font-bold text-yellow-400">
                {roi?.capital_appreciation?.gain_percentage?.toFixed(1) || '0'}%
              </p>
              <p className="text-xs text-slate-500 mt-2">Appreciation</p>
            </div>

            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <p className="text-slate-400 text-sm mb-1">Annual Rental Yield</p>
              <p className="text-3xl font-bold text-pink-400">
                {roi?.rental_income?.yield_percentage?.toFixed(1) || '0'}%
              </p>
              <p className="text-xs text-slate-500 mt-2">Passive income</p>
            </div>
          </div>

          {/* Market Trend Indicator */}
          {roi?.market_context && (
            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <h3 className="font-bold text-slate-200 mb-3">Market Context</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-slate-400 text-sm">Market Trend</p>
                  <p className="font-bold text-lg capitalize">
                    {roi.market_context.trend?.replace('_', ' ')}
                  </p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Volatility</p>
                  <p className="font-bold text-lg capitalize">
                    {roi.market_context.volatility}
                  </p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Demand/Supply</p>
                  <p className="font-bold text-lg">
                    {roi.market_context.demand_supply?.imbalance_factor?.toFixed(2)}x
                  </p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Annual Growth</p>
                  <p className="font-bold text-lg">
                    {annualRatePercent?.toFixed(2)}%
                  </p>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* TAB: Capital Appreciation */}
      {activeTab === 'appreciation' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <h3 className="font-bold text-slate-200 mb-4">Property Value Growth Projection</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={appreciationData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#666" />
                <XAxis dataKey="year" label={{ value: 'Years', position: 'insideBottomRight', offset: -5 }} stroke="#999" />
                <YAxis stroke="#999" tickFormatter={(value) => `₹${(value / 10000000).toFixed(0)}Cr`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #666' }}
                  formatter={(value) => formatCurrency(value)}
                />
                <Area type="monotone" dataKey="value" stroke="#6366f1" fillOpacity={1} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Value Milestones */}
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <h3 className="font-bold text-slate-200 mb-3">Value Milestones</h3>
            <div className="space-y-2">
              {appreciationData.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center p-2 bg-slate-800 rounded">
                  <span className="text-slate-400">Year {item.year}</span>
                  <span className="font-bold text-indigo-400">{formatCurrency(item.value)}</span>
                  <span className="text-xs text-slate-500">
                    +{((item.value - property.price) / property.price * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* TAB: Scenarios */}
      {activeTab === 'scenarios' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <h3 className="font-bold text-slate-200 mb-4">ROI Under Different Market Scenarios</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={scenarioData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#666" />
                <XAxis dataKey="name" stroke="#999" />
                <YAxis stroke="#999" label={{ value: 'ROI %', angle: -90, position: 'insideLeft' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #666' }}
                  formatter={(value) => `${value.toFixed(1)}%`}
                />
                <Legend />
                <Bar dataKey="roi_base_horizon" fill="#818cf8" name={`${holdPeriod}-Year ROI %`} />
                <Bar dataKey="roi_long_horizon" fill="#ec4899" name={`${longHorizon}-Year ROI %`} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Scenario Details */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {scenarios && Object.entries(scenarios).map(([key, scenario]) => (
              <div key={key} className="bg-slate-700 rounded-lg p-4 border border-slate-600">
                <h4 className="font-bold text-lg mb-2 capitalize">
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </h4>
                <p className="text-slate-400 text-sm mb-3">{scenario?.description}</p>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Probability</span>
                    <span className="font-bold">{scenario?.probability}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">{holdPeriod}-Year ROI</span>
                    <span className="font-bold text-indigo-400">{(scenario?.roi_base_horizon ?? scenario?.roi_5yr ?? 0).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">{longHorizon}-Year ROI</span>
                    <span className="font-bold text-pink-400">{(scenario?.roi_long_horizon ?? scenario?.roi_10yr ?? 0).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Growth Rate</span>
                    <span className="font-bold text-green-400">
                      {(scenario?.appreciation_rate * 100)?.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* TAB: Returns Composition */}
      {activeTab === 'returns' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Pie Chart */}
            {returnComposition.length > 0 && (
              <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
                <h3 className="font-bold text-slate-200 mb-4">Return Sources ({holdPeriod}-Year)</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={returnComposition}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {returnComposition.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #666' }}
                      formatter={(value) => `${value.toFixed(1)}%`}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Return Breakdown */}
            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
              <h3 className="font-bold text-slate-200 mb-4">Return Breakdown</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-slate-400">Capital Appreciation</span>
                    <span className="font-bold text-indigo-400">
                      {roi?.capital_appreciation?.gain_percentage?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full rounded-full"
                      style={{
                        width: `${Math.min(100, (roi?.capital_appreciation?.gain_percentage || 0) / 2)}%`
                      }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {formatCurrency(roi?.capital_appreciation?.total_gain)}
                  </p>
                </div>

                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-slate-400">Rental Income ({holdPeriod} Years)</span>
                    <span className="font-bold text-pink-400">
                      {(roi?.rental_income?.yield_percentage * holdPeriod)?.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-pink-600 h-full rounded-full"
                      style={{
                        width: `${Math.min(100, (roi?.rental_income?.yield_percentage * holdPeriod || 0) / 2)}%`
                      }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {formatCurrency(roi?.rental_income?.total_income)}
                  </p>
                </div>

                <div className="border-t border-slate-600 pt-4">
                  <div className="flex justify-between">
                    <span className="text-slate-300 font-bold">Total Return</span>
                    <span className="font-bold text-green-400">
                      {(roi?.total_return?.net_percentage ?? roi?.total_return?.percentage ?? 0).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    {formatCurrency(roi?.total_return?.net_amount ?? roi?.total_return?.amount)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* TAB: Detailed Analysis */}
      {activeTab === 'details' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {/* Investment Thesis */}
          {forecast.investment_thesis && (
            <div className="bg-slate-700 rounded-lg p-4 border border-slate-600 whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">
              {forecast.investment_thesis}
            </div>
          )}

          {/* Risk Factors */}
          <div className="bg-slate-700 rounded-lg p-4 border border-yellow-600">
            <h3 className="font-bold text-yellow-400 mb-3">⚠️ Risk Factors</h3>
            <ul className="space-y-2 text-sm text-slate-300">
              <li>• Market liquidity: Properties typically take 3-6 months to sell</li>
              <li>• Interest rate fluctuations may impact rental yields</li>
              <li>• News impact is directional and should not be treated as guaranteed price movement</li>
              <li>• Location-specific risks: Infrastructure changes, neighborhood deterioration</li>
              <li>• Regulatory risks: Tax law changes, rental regulations</li>
            </ul>
          </div>

          {/* Data Sources */}
          <div className="bg-slate-700 rounded-lg p-4 border border-slate-600">
            <h3 className="font-bold text-slate-200 mb-3">📚 Data Sources</h3>
            <ul className="space-y-2 text-sm text-slate-300">
              <li>• Historical property transaction data (Housing.csv, 99acres.csv)</li>
              <li>• Market reports and location-level growth priors</li>
              <li>• {forecast.retrieval_method || forecast.market_context?.retrieval_method || 'RAG semantic search'} for market context</li>
              <li>• Real-time market-news impact (bounded adjustment)</li>
            </ul>
          </div>
        </motion.div>
      )}
    </div>
  )
}
