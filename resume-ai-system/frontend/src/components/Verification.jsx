/**
 * Components for verification + interview plan rendering.
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Github,
  Linkedin,
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  Clock,
  GitCommit,
  Users,
  BookOpen,
  Lightbulb,
  Briefcase,
  Cpu,
  HelpCircle,
} from 'lucide-react'

export function VerificationPanel({ verification }) {
  if (!verification) return null
  const { github, linkedin, cross_reference, overall_authenticity } = verification
  const authColor =
    overall_authenticity >= 75
      ? 'text-moss'
      : overall_authenticity >= 50
      ? 'text-ink-700'
      : 'text-flame'
  const ShieldIcon = overall_authenticity >= 65 ? ShieldCheck : ShieldAlert

  return (
    <div className="paper-card overflow-hidden">
      <div className="px-6 py-4 border-b border-ink-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldIcon className={`h-5 w-5 ${authColor}`} />
          <div>
            <div className="font-display text-lg font-semibold tracking-editorial">
              Verification
            </div>
            <div className="text-xs text-ink-500">Public-claim authenticity check</div>
          </div>
        </div>
        <div className={`stat-num text-3xl ${authColor}`}>
          {Math.round(overall_authenticity)}
          <span className="text-sm text-ink-400">/100</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-ink-100">
        <GitHubBlock github={github} />
        <LinkedInBlock linkedin={linkedin} />
      </div>

      {cross_reference?.length > 0 && (
        <div className="px-6 py-4 border-t border-ink-200 bg-flame/5">
          <div className="label-overline text-flame-dark">Cross-reference flags</div>
          <ul className="mt-2 space-y-1.5">
            {cross_reference.map((flag, i) => (
              <li key={i} className="text-sm text-ink-700 flex items-start gap-2">
                <span className="text-flame mt-1">▸</span>
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function GitHubBlock({ github }) {
  if (!github.found) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 mb-2">
          <Github className="h-4 w-4 text-ink-400" />
          <span className="label-overline">GitHub</span>
        </div>
        <p className="text-sm text-ink-500 italic">
          {github.notes?.[0] || 'GitHub URL not found on resume.'}
        </p>
      </div>
    )
  }
  return (
    <div className="p-6 space-y-3">
      <div className="flex items-center justify-between">
        <a
          href={github.profile_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 hover:text-flame transition-colors"
        >
          <Github className="h-4 w-4" />
          <span className="font-mono text-sm font-medium">@{github.username}</span>
        </a>
        <span className="text-xs text-ink-500 tabular-nums">
          {github.authenticity_score.toFixed(0)}/100
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3">
        <Stat icon={BookOpen} label="repos" value={github.public_repos} />
        <Stat icon={Users} label="followers" value={github.followers.toLocaleString()} />
        <Stat icon={GitCommit} label="commits/90d" value={github.recent_commit_count_90d} />
      </div>

      {github.top_languages?.length > 0 && (
        <div>
          <div className="label-overline mb-1.5">Top languages</div>
          <div className="flex flex-wrap gap-1.5">
            {github.top_languages.map((l) => (
              <span
                key={l}
                className="pill bg-ink-100 text-ink-700 font-mono text-[11px]"
              >
                {l}
              </span>
            ))}
          </div>
        </div>
      )}

      {github.flags?.length > 0 && (
        <div className="pt-2">
          <div className="label-overline text-flame-dark mb-1">Flags</div>
          <div className="flex flex-wrap gap-1.5">
            {github.flags.map((f) => (
              <span
                key={f}
                className="pill bg-flame/10 text-flame-dark font-mono text-[11px]"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function LinkedInBlock({ linkedin }) {
  return (
    <div className="p-6 space-y-3">
      <div className="flex items-center gap-2">
        <Linkedin className="h-4 w-4 text-ocean" />
        <span className="label-overline">LinkedIn</span>
      </div>
      {linkedin.found ? (
        <>
          <a
            href={linkedin.profile_url}
            target="_blank"
            rel="noreferrer"
            className="block font-mono text-sm text-ink-800 hover:text-flame transition-colors break-all"
          >
            {linkedin.profile_url}
          </a>
          <div className="flex items-center gap-2">
            <div
              className={`pill text-[11px] ${
                linkedin.url_valid ? 'bg-moss/15 text-moss' : 'bg-flame/15 text-flame-dark'
              }`}
            >
              {linkedin.url_valid ? 'URL well-formed' : 'URL malformed'}
            </div>
            {linkedin.slug && (
              <span className="text-xs text-ink-500 font-mono">/{linkedin.slug}</span>
            )}
          </div>
          {linkedin.notes?.length > 0 && (
            <p className="text-xs text-ink-500 italic leading-relaxed">
              {linkedin.notes.join(' ')}
            </p>
          )}
        </>
      ) : (
        <p className="text-sm text-ink-500 italic">
          {linkedin.notes?.[0] || 'No LinkedIn URL on resume.'}
        </p>
      )}
    </div>
  )
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="text-center">
      <Icon className="h-3.5 w-3.5 text-ink-400 mx-auto mb-0.5" />
      <div className="stat-num text-base text-ink-900">{value}</div>
      <div className="text-[10px] text-ink-500 uppercase tracking-wider">{label}</div>
    </div>
  )
}

// ----------------------------------------------------------------------

const CATEGORY_META = {
  technical: { Icon: Cpu, color: 'text-ocean', bg: 'bg-ocean/10', label: 'Technical' },
  system_design: { Icon: Briefcase, color: 'text-moss', bg: 'bg-moss/10', label: 'System Design' },
  project_deep_dive: { Icon: BookOpen, color: 'text-ink-700', bg: 'bg-ink-100', label: 'Project Deep-dive' },
  behavioral: { Icon: Lightbulb, color: 'text-flame-dark', bg: 'bg-flame/10', label: 'Behavioral' },
  gap_probe: { Icon: HelpCircle, color: 'text-flame', bg: 'bg-flame/10', label: 'Gap Probe' },
}

const DIFF_META = {
  easy: 'bg-moss/15 text-moss',
  medium: 'bg-ink-200 text-ink-700',
  hard: 'bg-flame/15 text-flame-dark',
}

export function InterviewQuestionCard({ q, idx }) {
  const [open, setOpen] = useState(false)
  const cat = CATEGORY_META[q.category] || CATEGORY_META.technical
  const Icon = cat.Icon
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
      className="paper-card overflow-hidden"
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-5 py-4 flex items-start gap-4 text-left hover:bg-ink-50/50 transition-colors"
      >
        <div className={`mt-0.5 p-2 rounded-lg ${cat.bg} flex-shrink-0`}>
          <Icon className={`h-4 w-4 ${cat.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`pill text-[10px] uppercase tracking-wider ${cat.bg} ${cat.color} font-semibold`}>
              {cat.label}
            </span>
            <span className={`pill text-[10px] uppercase tracking-wider ${DIFF_META[q.difficulty]}`}>
              {q.difficulty}
            </span>
            <span className="text-[11px] text-ink-400 ml-auto">Q{idx + 1}</span>
          </div>
          <p className="font-display text-lg leading-snug text-ink-900 tracking-editorial">
            {q.question}
          </p>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-ink-400 mt-2 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden border-t border-ink-100 bg-ink-50/40"
          >
            <div className="px-5 py-4 space-y-3">
              <div>
                <div className="label-overline mb-1">Why this question</div>
                <p className="text-sm text-ink-700 leading-relaxed">{q.rationale}</p>
              </div>
              {q.targets?.length > 0 && (
                <div>
                  <div className="label-overline mb-1.5">Probes</div>
                  <div className="flex flex-wrap gap-1.5">
                    {q.targets.map((t) => (
                      <span
                        key={t}
                        className="pill text-[11px] bg-ink-200/70 text-ink-700 font-mono"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function InterviewPlanHeader({ plan }) {
  return (
    <div className="paper-card p-6 bg-gradient-to-br from-ink-100/60 to-transparent">
      <div className="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <div className="label-overline">Interview plan</div>
          <h2 className="mt-1 font-display text-3xl font-semibold tracking-editorial leading-tight">
            {plan.questions.length} tailored questions
          </h2>
          <div className="mt-1 flex items-center gap-2 text-sm text-ink-500">
            <Clock className="h-3.5 w-3.5" />
            <span>~{plan.estimated_duration_minutes} minutes</span>
          </div>
        </div>
        {plan.focus_areas?.length > 0 && (
          <div className="max-w-md">
            <div className="label-overline mb-1.5">Focus areas</div>
            <div className="flex flex-wrap gap-1.5">
              {plan.focus_areas.map((f, i) => (
                <span
                  key={i}
                  className="pill text-xs bg-ink-100 text-ink-700"
                >
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
