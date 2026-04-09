import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  FiActivity,
  FiAlertCircle,
  FiBarChart2,
  FiClock,
  FiExternalLink,
  FiGlobe,
  FiMapPin,
  FiSearch,
  FiTrendingUp,
} from 'react-icons/fi'
import toast from 'react-hot-toast'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getMarketAlerts, getTrendingLocations } from '../utils/api'

const CHART_COLORS = ['#06b6d4', '#38bdf8', '#22c55e', '#f59e0b', '#f97316', '#ef4444']

const impactToneMap = {
  high_positive: {
    label: 'High Growth',
    badge: 'bg-emerald-500/20 text-emerald-200 border border-emerald-400/30',
    accent: '#22c55e',
  },
  moderate_positive: {
    label: 'Constructive',
    badge: 'bg-cyan-500/20 text-cyan-100 border border-cyan-400/30',
    accent: '#06b6d4',
  },
  neutral: {
    label: 'Balanced',
    badge: 'bg-slate-500/20 text-slate-200 border border-slate-400/30',
    accent: '#94a3b8',
  },
  negative: {
    label: 'Watchlist',
    badge: 'bg-rose-500/20 text-rose-100 border border-rose-400/30',
    accent: '#ef4444',
  },
}

function shortDate(value) {
  if (!value) return 'Unknown date'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function chartTooltipStyle() {
  return {
    backgroundColor: '#0f172a',
    border: '1px solid rgba(148, 163, 184, 0.25)',
    borderRadius: '14px',
    color: '#e2e8f0',
  }
}

function normalizeTimelineData(timeline = [], articles = []) {
  const parsedTimeline = (Array.isArray(timeline) ? timeline : [])
    .map((point) => {
      const pointDate = point?.date || point?.label || point?.period || ''
      const parsedDate = pointDate ? new Date(pointDate) : null
      const articleCount = Number(point?.articles ?? point?.count ?? point?.value ?? 0)
      const impactValue = Number(point?.impact ?? 0)

      if (!parsedDate || Number.isNaN(parsedDate.getTime()) || !Number.isFinite(articleCount)) {
        return null
      }

      return {
        date: parsedDate.toISOString().slice(0, 10),
        articles: Math.max(0, articleCount),
        impact: Number.isFinite(impactValue) ? impactValue : 0,
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.date.localeCompare(b.date))

  if (parsedTimeline.length > 0) {
    return parsedTimeline
  }

  const bucket = new Map()
  ;(Array.isArray(articles) ? articles : []).forEach((article) => {
    const parsedDate = article?.date ? new Date(article.date) : null
    if (!parsedDate || Number.isNaN(parsedDate.getTime())) {
      return
    }
    const dayKey = parsedDate.toISOString().slice(0, 10)
    const current = bucket.get(dayKey) || { date: dayKey, articles: 0, impact: 0 }
    current.articles += 1
    const articleImpact = Number(article?.impact_score ?? 0)
    current.impact += Number.isFinite(articleImpact) ? articleImpact : 0
    bucket.set(dayKey, current)
  })

  return Array.from(bucket.values())
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((point) => ({
      ...point,
      impact: point.articles > 0 ? Number(((point.impact / point.articles) * 100).toFixed(1)) : 0,
    }))
}

export default function MarketNews() {
  const [trendingLocations, setTrendingLocations] = useState([])
  const [selectedLocation, setSelectedLocation] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [marketAlert, setMarketAlert] = useState(null)
  const [loading, setLoading] = useState(false)
  const [trendingLoading, setTrendingLoading] = useState(true)
  const [viewMode, setViewMode] = useState('cards')

  useEffect(() => {
    fetchTrendingLocations()
  }, [])

  const fetchTrendingLocations = async () => {
    try {
      setTrendingLoading(true)
      const { data } = await getTrendingLocations(8)
      setTrendingLocations(data.trending_locations || [])
    } catch (error) {
      console.error('Error fetching trending locations:', error)
      toast.error('Failed to load trending locations')
    } finally {
      setTrendingLoading(false)
    }
  }

  const fetchMarketAlert = async (location, query = '') => {
    if (!location) return

    try {
      setLoading(true)
      const { data } = await getMarketAlerts(location, query ? { query, n_results: 6 } : { n_results: 6 })
      setMarketAlert(data)
      setSelectedLocation(location)
    } catch (error) {
      console.error('Error fetching market alert:', error)
      toast.error('Failed to load market news')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (event) => {
    event.preventDefault()
    if (!selectedLocation.trim()) {
      toast.error('Enter a city or micro-market first')
      return
    }
    fetchMarketAlert(selectedLocation.trim(), searchQuery.trim())
  }

  const trendingChartData = useMemo(
    () => trendingLocations.map((location) => ({
      name: location.location,
      news: location.news_count,
      confidence: location.confidence_score || 0,
      impact: Math.round((location.avg_impact || 0) * 100),
    })),
    [trendingLocations]
  )

  const selectedTone = impactToneMap[marketAlert?.impact_level] || impactToneMap.neutral
  const timelineData = useMemo(() => {
    const normalized = normalizeTimelineData(marketAlert?.timeline || [], marketAlert?.articles || [])
    if (normalized.length !== 1) {
      return normalized
    }

    const onlyPoint = normalized[0]
    const pointDate = new Date(onlyPoint.date)
    const fallbackDate = Number.isNaN(pointDate.getTime())
      ? new Date(Date.now() - 24 * 60 * 60 * 1000)
      : new Date(pointDate.getTime() - 24 * 60 * 60 * 1000)

    return [
      {
        date: fallbackDate.toISOString().slice(0, 10),
        articles: 0,
        impact: 0,
      },
      onlyPoint,
    ]
  }, [marketAlert?.timeline, marketAlert?.articles])
  const signalData = marketAlert?.signal_breakdown || []
  const sourceMix = marketAlert?.source_mix || []
  const hasArticles = (marketAlert?.articles?.length || 0) > 0

  return (
    <div className="min-h-screen bg-[#081120] py-10 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10 rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(8,145,178,0.22),_transparent_32%),linear-gradient(180deg,_rgba(15,23,42,0.96),_rgba(8,17,32,0.96))] p-8 shadow-[0_30px_80px_rgba(2,12,27,0.45)]"
        >
          <div className="mb-6">
            <div className="max-w-4xl">
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-1.5 text-sm font-semibold text-cyan-50">
                <FiTrendingUp />
                Market News Intelligence
              </p>
              <h1 className="max-w-4xl text-3xl font-semibold leading-tight tracking-tight text-slate-50 md:text-[2.7rem]">
                Real signals, cleaner charts, better city-level reads
              </h1>
              <p className="mt-4 max-w-4xl text-base leading-7 text-slate-300 md:text-lg md:leading-8">
                This dashboard now prioritizes live, location-specific headlines and groups them into market drivers like infrastructure,
                pricing, office demand, supply, policy, and caution.
              </p>
            </div>
          </div>

          <form onSubmit={handleSearch} className="grid grid-cols-1 gap-4 rounded-[28px] border border-white/10 bg-slate-950/35 p-5 lg:grid-cols-[1.2fr_1fr_auto]">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300">
                <FiMapPin className="text-cyan-300" />
                Location
              </span>
              <input
                type="text"
                value={selectedLocation}
                onChange={(event) => setSelectedLocation(event.target.value)}
                placeholder="Mumbai, Bengaluru, Noida, Hyderabad..."
                className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-white outline-none transition focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-400/20"
              />
            </label>

            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300">
                <FiSearch className="text-cyan-300" />
                Focus
              </span>
              <input
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="metro, office demand, launches, rental..."
                className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-white outline-none transition focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-400/20"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-2xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <FiSearch />
              {loading ? 'Loading...' : 'Analyze location'}
            </button>
          </form>
        </motion.div>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mb-10 rounded-[28px] border border-white/10 bg-slate-900/70 p-6"
        >
          <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-white">Trending cities</h2>
              <p className="mt-1 text-sm text-slate-400">Ranked by recent article volume, source diversity, and weighted market impact.</p>
            </div>
            <div className="inline-flex rounded-2xl border border-white/10 bg-slate-950/40 p-1">
              <button
                onClick={() => setViewMode('cards')}
                className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${viewMode === 'cards' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
              >
                Cards
              </button>
              <button
                onClick={() => setViewMode('chart')}
                className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${viewMode === 'chart' ? 'bg-cyan-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
              >
                Chart
              </button>
            </div>
          </div>

          {trendingLoading ? (
            <div className="rounded-3xl border border-white/10 bg-slate-950/30 px-6 py-16 text-center text-slate-400">
              Loading trending locations...
            </div>
          ) : viewMode === 'chart' ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-slate-950/35 p-5">
                <div className="mb-4 text-sm font-medium text-slate-300">Weighted momentum</div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={trendingChartData}>
                    <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip contentStyle={chartTooltipStyle()} itemStyle={{ color: '#e2e8f0' }} labelStyle={{ color: '#cbd5e1' }} />
                    <Bar dataKey="impact" radius={[10, 10, 0, 0]} fill="#06b6d4" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="rounded-3xl border border-white/10 bg-slate-950/35 p-5">
                <div className="mb-4 text-sm font-medium text-slate-300">Coverage confidence</div>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={trendingChartData}>
                    <defs>
                      <linearGradient id="confidenceFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
                    <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip contentStyle={chartTooltipStyle()} itemStyle={{ color: '#e2e8f0' }} labelStyle={{ color: '#cbd5e1' }} />
                    <Area type="monotone" dataKey="confidence" stroke="#38bdf8" fill="url(#confidenceFill)" strokeWidth={2.5} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {trendingLocations.map((location, index) => {
                const sparklineData = location.momentum_series?.length
                  ? location.momentum_series
                  : [{ label: 'Now', articles: location.news_count }]

                return (
                  <button
                    key={location.location}
                    onClick={() => fetchMarketAlert(location.location)}
                    className="group rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.88),rgba(15,23,42,0.68))] p-5 text-left transition hover:-translate-y-1 hover:border-cyan-400/40 hover:bg-slate-900"
                  >
                    <div className="mb-4 flex items-start justify-between">
                      <div>
                        <div className="text-sm font-medium text-cyan-300">#{index + 1}</div>
                        <div className="mt-1 text-2xl font-semibold text-white">{location.location}</div>
                      </div>
                      <div className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
                        {location.confidence_score || 0}% confident
                      </div>
                    </div>

                    <div className="mb-4 h-16">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={sparklineData}>
                          <defs>
                            <linearGradient id={`spark-${location.location}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.35} />
                              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <Area type="monotone" dataKey="articles" stroke="#06b6d4" fill={`url(#spark-${location.location})`} strokeWidth={2.4} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="flex items-center justify-between text-sm text-slate-300">
                      <span>{location.news_count} recent articles</span>
                      <span>{Math.round((location.avg_impact || 0) * 100)}% impact</span>
                    </div>
                    {!!location.top_signals?.length && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {location.top_signals.map((signal) => (
                          <span key={signal} className="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300">
                            {signal}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </motion.section>

        {marketAlert ? (
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="rounded-[30px] border border-white/10 bg-slate-900/75 p-6">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="mb-3 flex flex-wrap items-center gap-3">
                    <span className={`rounded-full px-4 py-1.5 text-sm font-semibold ${selectedTone.badge}`}>
                      {selectedTone.label}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300">
                      {marketAlert.live_news_count > 0 ? 'Live news enabled' : 'Archive-backed view'}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300">
                      {marketAlert.retrieval_mode?.replaceAll('_', ' ') || 'analysis'}
                    </span>
                  </div>
                  <h2 className="text-3xl font-bold text-white">{marketAlert.location}</h2>
                  <p className="mt-3 max-w-3xl text-base leading-7 text-slate-300">{marketAlert.market_summary}</p>
                </div>

                <div className="grid min-w-[260px] gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Impact score</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{Math.round((marketAlert.avg_impact_score || 0) * 100)}%</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Confidence</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{Math.round(marketAlert.confidence_score || 0)}%</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Articles</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{marketAlert.articles?.length || 0}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Sources</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{sourceMix.length || 0}</div>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-[26px] border border-cyan-400/15 bg-cyan-400/5 p-5">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-cyan-100">
                  <FiAlertCircle />
                  Recommendation
                </div>
                <p className="text-slate-100">{marketAlert.recommendation}</p>
              </div>
            </div>

            {hasArticles ? (
              <>
            <div className="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
              <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <FiActivity className="text-cyan-300" />
                  News momentum over time
                </div>
                <p className="mb-4 text-sm text-slate-400">Freshness and article density are now visualized directly from the retrieved article dates.</p>
                <ResponsiveContainer width="100%" height={320}>
                  <AreaChart data={timelineData}>
                    <defs>
                      <linearGradient id="timelineFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={selectedTone.accent} stopOpacity={0.35} />
                        <stop offset="95%" stopColor={selectedTone.accent} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={shortDate} stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={chartTooltipStyle()}
                      itemStyle={{ color: '#e2e8f0' }}
                      labelStyle={{ color: '#cbd5e1' }}
                      labelFormatter={(value) => shortDate(value)}
                    />
                    <Area type="monotone" dataKey="articles" stroke={selectedTone.accent} fill="url(#timelineFill)" strokeWidth={2.8} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <FiBarChart2 className="text-cyan-300" />
                  What is driving the market
                </div>
                <p className="mb-4 text-sm text-slate-400">Each bar shows how often a market-moving theme appears across the retrieved coverage.</p>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={signalData} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" horizontal vertical={false} />
                    <XAxis type="number" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis type="category" width={120} dataKey="name" stroke="#94a3b8" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={chartTooltipStyle()}
                      itemStyle={{ color: '#e2e8f0' }}
                      labelStyle={{ color: '#cbd5e1' }}
                      formatter={(value, name, item) => [`${item.payload.share}% share`, item.payload.name]}
                    />
                    <Bar dataKey="value" radius={[0, 12, 12, 0]}>
                      {signalData.map((entry, index) => (
                        <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1fr_1.25fr]">
              <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <FiGlobe className="text-cyan-300" />
                  Source mix
                </div>
                <p className="mb-4 text-sm text-slate-400">Confidence improves when a location is covered by multiple credible sources, not just one burst of headlines.</p>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={sourceMix}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      innerRadius={50}
                      paddingAngle={4}
                    >
                      {sourceMix.map((source, index) => (
                        <Cell key={source.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle()} itemStyle={{ color: '#e2e8f0' }} labelStyle={{ color: '#cbd5e1' }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-4 flex flex-wrap gap-2">
                  {sourceMix.map((source, index) => (
                    <span key={source.name} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                      <span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }} />
                      {source.name} ({source.value})
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                  <FiClock className="text-cyan-300" />
                  Evidence from recent articles
                </div>
                <p className="mb-4 text-sm text-slate-400">{marketAlert.alert_summary}</p>
                <div className="space-y-4">
                  {marketAlert.articles?.map((article, index) => (
                    <div key={`${article.url || article.title}-${index}`} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300">
                          Impact {Math.round((article.impact_score || 0) * 100)}%
                        </span>
                        {article.live ? (
                          <span className="rounded-full bg-cyan-500/15 px-3 py-1 text-xs text-cyan-100">Live</span>
                        ) : (
                          <span className="rounded-full bg-slate-500/20 px-3 py-1 text-xs text-slate-200">Archive</span>
                        )}
                      </div>
                      <h3 className="text-lg font-semibold text-white">{article.title}</h3>
                      <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-300">{article.content}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                        <span>{article.source || 'Unknown source'}</span>
                        <span>{shortDate(article.date)}</span>
                        {article.url && (
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-cyan-300 hover:text-cyan-200"
                          >
                            Read source
                            <FiExternalLink />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
              </>
            ) : (
              <div className="rounded-[28px] border border-dashed border-white/10 bg-slate-900/75 p-10 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-100">
                  <FiAlertCircle className="text-2xl" />
                </div>
                <h3 className="text-2xl font-semibold text-white">No relevant news in this area</h3>
                <p className="mx-auto mt-3 max-w-2xl text-base leading-7 text-slate-300">
                  {marketAlert.market_summary || `No relevant market news was found in or around ${marketAlert.location}. Try a nearby micro-market or broaden the search.`}
                </p>
              </div>
            )}
          </motion.section>
        ) : (
          <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-[30px] border border-dashed border-white/10 bg-slate-900/50 p-12 text-center"
          >
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-cyan-500/10 text-cyan-200">
              <FiMapPin className="text-2xl" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Choose a city to inspect the market</h2>
            <p className="mx-auto mt-3 max-w-2xl text-slate-400">
              Search a city or tap one of the trending locations above to see the live news mix, confidence score, signal breakdown, and the specific articles shaping the read.
            </p>
          </motion.section>
        )}
      </div>
    </div>
  )
}
