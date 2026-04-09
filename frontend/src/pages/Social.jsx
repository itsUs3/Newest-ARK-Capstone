import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts'
import {
  FiAlertCircle,
  FiBarChart2,
  FiClock,
  FiMapPin,
  FiMessageCircle,
  FiSearch,
  FiUsers,
} from 'react-icons/fi'
import { getSocialAnalysis } from '../utils/api'

const ASPECT_COLOR = {
  positive: '#22c55e',
  mixed: '#f59e0b',
  negative: '#ef4444',
  limited_data: '#64748b',
}

const ASPECT_SCORE = {
  positive: 8.5,
  mixed: 5.5,
  negative: 2.5,
  limited_data: 0,
}

function prettyAspectName(name) {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

function formatDate(value) {
  if (!value) return 'Unknown date'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function Social() {
  const [area, setArea] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)

  const aspectChartData = useMemo(() => {
    if (!analysis?.aspect_analysis) return []
    return Object.entries(analysis.aspect_analysis).map(([aspect, data]) => ({
      aspect: prettyAspectName(aspect),
      label: data.label || 'limited_data',
      score: ASPECT_SCORE[data.label] ?? 0,
      mentions: data.mentions || 0,
    }))
  }, [analysis])

  const handleSubmit = async (event) => {
    console.log('[Social] handleSubmit called')
    event.preventDefault()
    const trimmedArea = area.trim()
    console.log('[Social] trimmedArea:', trimmedArea)
    if (!trimmedArea) {
      toast.error('Enter an area first')
      return
    }

    try {
      setLoading(true)
      console.log('[Social] Calling API with area:', trimmedArea)
      const response = await getSocialAnalysis(trimmedArea)
      console.log('[Social] API response:', response)
      const { data } = response
      console.log('[Social] Setting analysis data:', data)
      setAnalysis(data)
    } catch (error) {
      console.error('[Social] Analysis failed:', error)
      console.error('[Social] Error response:', error.response?.data)
      console.error('[Social] Error status:', error.response?.status)
      toast.error(error.response?.data?.detail || 'Failed to load social analysis')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#081120] py-10 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_30%),linear-gradient(180deg,_rgba(15,23,42,0.96),_rgba(8,17,32,0.96))] p-8 shadow-[0_30px_80px_rgba(2,12,27,0.45)]"
        >
          <div className="max-w-4xl">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-sky-400/20 bg-sky-400/10 px-4 py-1.5 text-sm font-semibold text-sky-50">
              <FiUsers />
              Social Intelligence Layer
            </p>
            <h1 className="max-w-4xl text-3xl font-semibold leading-tight tracking-tight text-slate-50 md:text-[2.7rem]">
              Social perception for real-estate decisions
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-slate-300 md:text-lg md:leading-8">
              Search an area to see what stored Reddit discussions say about safety, traffic, cost, lifestyle, and cleanliness,
              then turn that into a structured decision-ready report.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 grid grid-cols-1 gap-4 rounded-[28px] border border-white/10 bg-slate-950/35 p-5 lg:grid-cols-[1.4fr_auto]">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300">
                <FiMapPin className="text-sky-300" />
                Area name
              </span>
              <input
                type="text"
                value={area}
                onChange={(event) => setArea(event.target.value)}
                placeholder="Bandra, Andheri West, Whitefield, Gachibowli..."
                className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 text-white outline-none transition focus:border-sky-400/50 focus:ring-2 focus:ring-sky-400/20"
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-2xl bg-sky-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <FiSearch />
              {loading ? 'Analyzing...' : 'Run social analysis'}
            </button>
          </form>
        </motion.section>

        {analysis ? (
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 space-y-6"
          >
            <div className="rounded-[30px] border border-white/10 bg-slate-900/75 p-6">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="mb-3 flex flex-wrap items-center gap-3">
                    <span className={`rounded-full px-4 py-1.5 text-sm font-semibold ${
                      analysis.data_availability?.status === 'ok'
                        ? 'border border-emerald-400/30 bg-emerald-500/15 text-emerald-100'
                        : 'border border-slate-400/30 bg-slate-500/15 text-slate-100'
                    }`}>
                      {analysis.data_availability?.status === 'ok' ? 'Social data available' : 'Limited social data'}
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300">
                      {analysis.data_availability?.post_count || 0} relevant posts
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-slate-300">
                      {analysis.overall_sentiment?.replace('_', ' ') || 'unknown'} sentiment
                    </span>
                  </div>

                  <h2 className="text-3xl font-bold text-white">{analysis.area}</h2>
                  <p className="mt-3 max-w-3xl text-base leading-7 text-slate-300">{analysis.summary}</p>

                  {!!analysis.normalized_locations?.length && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {analysis.normalized_locations.map((location) => (
                        <span key={location} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                          {location}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="grid min-w-[260px] gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Social score</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{analysis.social_score ?? 0}/10</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Data source</div>
                    <div className="mt-2 text-base font-semibold text-white">{analysis.data_availability?.source || 'stored_reddit_db'}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4 sm:col-span-2">
                    <div className="text-xs uppercase tracking-[0.22em] text-slate-500">Verdict</div>
                    <div className="mt-2 text-sm leading-6 text-slate-200">{analysis.verdict?.text || 'No verdict available'}</div>
                  </div>
                </div>
              </div>
            </div>

            {analysis.data_availability?.status !== 'ok' ? (
              <div className="rounded-[28px] border border-dashed border-white/10 bg-slate-900/75 p-10 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-500/10 text-slate-100">
                  <FiAlertCircle className="text-2xl" />
                </div>
                <h3 className="text-2xl font-semibold text-white">Limited social data available for this area</h3>
                <p className="mx-auto mt-3 max-w-2xl text-base leading-7 text-slate-300">
                  {analysis.summary}
                </p>
                {!!analysis.nearby_suggestions?.length && (
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    {analysis.nearby_suggestions.map((suggestion) => (
                      <span key={suggestion} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-slate-300">
                        {suggestion}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <>
                <div className="grid gap-6 xl:grid-cols-[1.1fr_1.25fr]">
                  <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                      <FiBarChart2 className="text-sky-300" />
                      Aspect analysis
                    </div>
                    <p className="mb-4 text-sm text-slate-400">Each aspect is scored from the tone of the most relevant stored discussions.</p>
                    <ResponsiveContainer width="100%" height={320}>
                      <BarChart data={aspectChartData} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" horizontal vertical={false} />
                        <XAxis type="number" domain={[0, 10]} stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                        <YAxis type="category" width={110} dataKey="aspect" stroke="#94a3b8" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(148, 163, 184, 0.25)', borderRadius: '14px', color: '#e2e8f0' }}
                          formatter={(value, name, item) => [`${item.payload.label} (${item.payload.mentions} mentions)`, item.payload.aspect]}
                        />
                        <Bar dataKey="score" radius={[0, 12, 12, 0]}>
                          {aspectChartData.map((entry) => (
                            <Cell key={entry.aspect} fill={ASPECT_COLOR[entry.label] || '#64748b'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                      <FiMessageCircle className="text-sky-300" />
                      Key insights
                    </div>
                    <div className="space-y-3">
                      {analysis.key_insights?.map((insight, index) => (
                        <div key={`${insight}-${index}`} className="rounded-2xl border border-white/10 bg-slate-950/35 px-4 py-3 text-slate-200">
                          {insight}
                        </div>
                      ))}
                    </div>
                    {!!analysis.verdict?.pros?.length && (
                      <div className="mt-5">
                        <div className="mb-2 text-sm font-semibold text-emerald-200">Pros</div>
                        <div className="flex flex-wrap gap-2">
                          {analysis.verdict.pros.map((item) => (
                            <span key={item} className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-100">
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {!!analysis.verdict?.cons?.length && (
                      <div className="mt-4">
                        <div className="mb-2 text-sm font-semibold text-rose-200">Cons</div>
                        <div className="flex flex-wrap gap-2">
                          {analysis.verdict.cons.map((item) => (
                            <span key={item} className="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-1 text-sm text-rose-100">
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid gap-6 xl:grid-cols-[1.15fr_1fr]">
                  <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                      <FiUsers className="text-sky-300" />
                      Top discussions
                    </div>
                    <div className="space-y-4">
                      {analysis.top_discussions?.map((post) => (
                        <div key={post.id} className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                              r/{post.subreddit}
                            </span>
                            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                              {post.sentiment?.label || 'neutral'}
                            </span>
                            {!!post.upvotes && (
                              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
                                {post.upvotes} upvotes
                              </span>
                            )}
                          </div>
                          <p className="text-sm leading-6 text-slate-200">{post.text}</p>
                          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                            <span className="inline-flex items-center gap-1">
                              <FiClock />
                              {formatDate(post.timestamp)}
                            </span>
                            {!!post.location_tags?.length && (
                              <span>{post.location_tags.join(', ')}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-[28px] border border-white/10 bg-slate-900/75 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                      <FiAlertCircle className="text-sky-300" />
                      Structured report
                    </div>
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-7 text-slate-200">
                      {analysis.structured_report}
                    </pre>
                  </div>
                </div>
              </>
            )}
          </motion.section>
        ) : (
          <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-8 rounded-[30px] border border-dashed border-white/10 bg-slate-900/50 p-12 text-center"
          >
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-sky-500/10 text-sky-200">
              <FiUsers className="text-2xl" />
            </div>
            <h2 className="text-2xl font-semibold text-white">Search an area to load social perception</h2>
            <p className="mx-auto mt-3 max-w-2xl text-slate-400">
              This layer works on stored Reddit discussions, not live scraping during user requests, so the response stays fast and repeatable.
            </p>
          </motion.section>
        )}
      </div>
    </div>
  )
}
