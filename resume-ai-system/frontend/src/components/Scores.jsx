/**
 * Score visualization components.
 *
 * Includes:
 *   <ScoreRadar/>      — recharts radar of the 4 dimensions
 *   <ScoreDimensionCard/> — expandable card with reasoning + evidence
 *   <TierBadge/>       — color-coded tier indicator
 *   <SkillMatchTable/> — JD-skill-by-JD-skill match breakdown
 *   <OverallScore/>    — large editorial number with breakdown ring
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Target, Sparkles, Award, Compass, CheckCircle2, AlertCircle, MinusCircle } from 'lucide-react'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts'

const DIM_META = {
  exact_match: {
    label: 'Exact Match',
    icon: Target,
    description: 'Verbatim presence of JD-required skills.',
  },
  similarity: {
    label: 'Similarity',
    icon: Sparkles,
    description: 'Embedding-based kinship across the resume corpus.',
  },
  achievement: {
    label: 'Achievement',
    icon: Award,
    description: 'Quality and quantification of accomplishments.',
  },
  ownership: {
    label: 'Ownership',
    icon: Compass,
    description: 'Leadership signal in language and scope.',
  },
}

export function ScoreRadar({ score }) {
  const data = [
    { dim: 'Exact', value: score.exact_match.value, full: 100 },
    { dim: 'Similar', value: score.similarity.value, full: 100 },
    { dim: 'Achieve', value: score.achievement.value, full: 100 },
    { dim: 'Ownership', value: score.ownership.value, full: 100 },
  ]
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 16, right: 28, bottom: 16, left: 28 }}>
          <PolarGrid stroke="#c8c0b3" strokeDasharray="2 4" />
          <PolarAngleAxis
            dataKey="dim"
            tick={{ fontSize: 11, fill: '#6b6357', fontFamily: '"Inter", sans-serif' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fontSize: 9, fill: '#9b9387' }}
            stroke="#c8c0b3"
          />
          <Radar
            name="score"
            dataKey="value"
            stroke="#e25822"
            fill="#e25822"
            fillOpacity={0.25}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ScoreDimensionCard({ dimensionKey, dimension, idx = 0 }) {
  const [open, setOpen] = useState(false)
  const meta = DIM_META[dimensionKey]
  const Icon = meta.icon
  const valueColor =
    dimension.value >= 75 ? 'text-moss' : dimension.value >= 50 ? 'text-ink-700' : 'text-flame'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.06, ease: [0.16, 1, 0.3, 1] }}
      className="paper-card p-5 hover:shadow-lg transition-shadow"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-ink-100">
            <Icon className="h-4 w-4 text-ink-700" />
          </div>
          <div>
            <div className="label-overline">{meta.label}</div>
            <div className="text-[11px] text-ink-500 mt-0.5">{meta.description}</div>
          </div>
        </div>
        <div className={`stat-num text-3xl ${valueColor}`}>
          {Math.round(dimension.value)}
          <span className="text-base text-ink-400">/100</span>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-ink-700">{dimension.reasoning}</p>

      {dimension.evidence?.length > 0 && (
        <button
          onClick={() => setOpen(!open)}
          className="mt-3 flex items-center gap-1.5 text-xs text-ink-500 hover:text-ink-900 transition-colors"
        >
          <span>{dimension.evidence.length} evidence quote{dimension.evidence.length === 1 ? '' : 's'}</span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      )}

      <AnimatePresence>
        {open && dimension.evidence?.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="mt-3 space-y-1.5 overflow-hidden"
          >
            {dimension.evidence.map((ev, i) => (
              <li
                key={i}
                className="text-xs text-ink-600 pl-3 border-l-2 border-flame leading-relaxed"
              >
                "{ev}"
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function TierBadge({ tier, label, size = 'md' }) {
  const colors = {
    A: 'bg-moss text-ink-50 border-moss',
    B: 'bg-ink-700 text-ink-50 border-ink-700',
    C: 'bg-flame text-ink-50 border-flame',
  }
  const sizes = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-10 px-4 text-sm',
    lg: 'h-14 px-5 text-base',
  }
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border ${colors[tier]} ${sizes[size]} font-medium`}>
      <span className="font-display font-bold">Tier {tier}</span>
      <span className="opacity-75">·</span>
      <span>{label}</span>
    </div>
  )
}

const matchIcon = {
  exact: { Icon: CheckCircle2, color: 'text-moss', bg: 'bg-moss/10' },
  semantic: { Icon: Sparkles, color: 'text-flame', bg: 'bg-flame/10' },
  missing: { Icon: MinusCircle, color: 'text-ink-400', bg: 'bg-ink-100' },
}

export function SkillMatchTable({ matches }) {
  if (!matches?.length) return null
  return (
    <div className="paper-card overflow-hidden">
      <div className="px-5 py-3 border-b border-ink-200 bg-ink-100/40">
        <div className="label-overline">Skill-by-skill match</div>
      </div>
      <ul className="divide-y divide-ink-100">
        {matches.map((m, i) => {
          const meta = matchIcon[m.match_type] || matchIcon.missing
          const Icon = meta.Icon
          return (
            <li key={i} className="px-5 py-3 flex items-start gap-4">
              <div className={`mt-0.5 p-1.5 rounded-md ${meta.bg}`}>
                <Icon className={`h-3.5 w-3.5 ${meta.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-medium text-ink-900 font-mono text-sm">
                    {m.jd_skill}
                  </span>
                  <span className="text-xs text-ink-500 tabular-nums">
                    {m.match_type === 'missing'
                      ? 'not found'
                      : `${Math.round(m.similarity * 100)}% similar`}
                  </span>
                </div>
                {m.matched_resume_skill && m.match_type !== 'exact' && (
                  <div className="text-xs text-ink-600 mt-1 font-mono">
                    ≈ {m.matched_resume_skill}
                  </div>
                )}
                {m.rationale && (
                  <div className="text-xs text-ink-500 italic mt-1.5 leading-relaxed">
                    {m.rationale}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export function OverallScore({ value, tier }) {
  const tierBg = { A: 'from-moss/20', B: 'from-ink-300/40', C: 'from-flame/20' }[tier?.tier || 'B']
  return (
    <div className={`relative paper-card p-8 bg-gradient-to-br ${tierBg} to-transparent`}>
      <div className="label-overline">Overall</div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="stat-num text-7xl text-ink-900">
          {Math.round(value)}
        </span>
        <span className="text-2xl text-ink-400 stat-num">/100</span>
      </div>
      {tier && (
        <div className="mt-4">
          <TierBadge tier={tier.tier} label={tier.label} size="md" />
        </div>
      )}
    </div>
  )
}
