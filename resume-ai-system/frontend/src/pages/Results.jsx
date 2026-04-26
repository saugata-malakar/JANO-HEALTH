import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Mail,
  Phone,
  MapPin,
  Github,
  Linkedin,
  Globe,
  Briefcase,
  GraduationCap,
  FolderGit2,
  Sparkles,
  Loader2,
  AlertTriangle,
  Trophy,
} from 'lucide-react'

import { api, ApiError } from '../lib/api'
import { useAuthClient } from '../hooks/useAuthClient'
import {
  ScoreRadar,
  ScoreDimensionCard,
  SkillMatchTable,
  OverallScore,
} from '../components/Scores'
import {
  VerificationPanel,
  InterviewQuestionCard,
  InterviewPlanHeader,
} from '../components/Verification'

const SESSION_KEY = 'hiresense:lastBatch'

/**
 * Results page
 * ------------
 * One candidate, fully unfolded. Hits sessionStorage first (fast back-nav
 * from Dashboard); if the candidate isn't there it falls back to the
 * baked sample evaluation so the route is never empty in demo mode.
 *
 * The interview plan is generated on demand to save LLM tokens during
 * the batch run — the user clicks "Generate interview" when they want it.
 */
export default function Results() {
  const { candidateId } = useParams()
  const { getToken } = useAuthClient()

  const [evaluation, setEvaluation] = useState(null)
  const [jd, setJd] = useState(null)
  const [error, setError] = useState(null)
  const [genLoading, setGenLoading] = useState(false)
  const [genError, setGenError] = useState(null)

  // Hydrate from sessionStorage; if missing, fetch the demo eval as a fallback
  useEffect(() => {
    let mounted = true
    async function hydrate() {
      try {
        const cached = sessionStorage.getItem(SESSION_KEY)
        if (cached) {
          const parsed = JSON.parse(cached)
          const match = (parsed.results || []).find(
            (r) => r.candidate_id === candidateId
          )
          if (match) {
            if (mounted) {
              setEvaluation(match)
              setJd(parsed.jd)
            }
            return
          }
        }
        // Fallback: demo evaluation
        const demo = await api.sampleEvaluation()
        const sampleJd = await api.sampleJD()
        if (mounted) {
          setEvaluation(demo)
          setJd(sampleJd)
        }
      } catch (e) {
        if (mounted) setError(e?.message || 'Could not load evaluation.')
      }
    }
    hydrate()
    return () => {
      mounted = false
    }
  }, [candidateId])

  const gaps = useMemo(() => {
    if (!evaluation) return []
    const list = []
    for (const m of evaluation.score?.skill_matches || []) {
      if (m.match_type === 'missing') list.push(m.jd_skill)
    }
    if ((evaluation.score?.achievement?.value || 0) < 50)
      list.push('quantified-impact (achievements lack metrics)')
    if ((evaluation.score?.ownership?.value || 0) < 50)
      list.push('ownership signal (mostly participation language)')
    return list
  }, [evaluation])

  const generateInterview = async () => {
    if (!evaluation || !jd) return
    setGenLoading(true)
    setGenError(null)
    try {
      const plan = await api.generateInterview(
        {
          parsed: evaluation.parsed,
          jd,
          score: evaluation.score,
          gaps,
        },
        { getToken }
      )
      const updated = { ...evaluation, interview: plan }
      setEvaluation(updated)
      // Update cache
      try {
        const cached = sessionStorage.getItem(SESSION_KEY)
        if (cached) {
          const parsed = JSON.parse(cached)
          parsed.results = (parsed.results || []).map((r) =>
            r.candidate_id === candidateId ? updated : r
          )
          sessionStorage.setItem(SESSION_KEY, JSON.stringify(parsed))
        }
      } catch (_) {
        /* ignore */
      }
    } catch (e) {
      const msg =
        e instanceof ApiError ? `${e.status}: ${e.message}` : e?.message
      setGenError(msg || 'Could not generate questions.')
    } finally {
      setGenLoading(false)
    }
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20 text-center">
        <AlertTriangle className="h-10 w-10 text-flame mx-auto mb-4" />
        <h1 className="font-display text-3xl font-semibold mb-2">
          Couldn't load evaluation
        </h1>
        <p className="text-ink-600">{error}</p>
        <Link to="/dashboard" className="btn-primary mt-6 inline-flex">
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>
      </div>
    )
  }

  if (!evaluation) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-20 text-center">
        <Loader2 className="h-8 w-8 text-ink-500 mx-auto animate-spin mb-3" />
        <p className="text-ink-500">Loading candidate dossier…</p>
      </div>
    )
  }

  const { parsed, score, verification, tier, interview } = evaluation

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-8 py-10">
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-2 text-sm text-ink-500 hover:text-ink-900 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to triage
      </Link>

      {/* Header — editorial spread */}
      <header className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 mb-12 pb-10 border-b border-ink-200">
        <div className="lg:col-span-8">
          <div className="label-overline mb-2">Candidate dossier</div>
          <h1 className="editorial-headline text-5xl lg:text-6xl font-semibold mb-3">
            {parsed.name || 'Unnamed candidate'}
          </h1>
          {parsed.headline && (
            <p className="font-display text-xl text-ink-600 italic">
              {parsed.headline}
            </p>
          )}

          <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-600">
            {parsed.email && (
              <a
                href={`mailto:${parsed.email}`}
                className="flex items-center gap-1.5 hover:text-flame transition-colors"
              >
                <Mail className="h-3.5 w-3.5" /> {parsed.email}
              </a>
            )}
            {parsed.phone && (
              <span className="flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" /> {parsed.phone}
              </span>
            )}
            {parsed.location && (
              <span className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" /> {parsed.location}
              </span>
            )}
            {parsed.links?.github && (
              <a
                href={parsed.links.github}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 hover:text-flame transition-colors"
              >
                <Github className="h-3.5 w-3.5" /> GitHub
              </a>
            )}
            {parsed.links?.linkedin && (
              <a
                href={parsed.links.linkedin}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 hover:text-flame transition-colors"
              >
                <Linkedin className="h-3.5 w-3.5" /> LinkedIn
              </a>
            )}
            {parsed.links?.portfolio && (
              <a
                href={parsed.links.portfolio}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 hover:text-flame transition-colors"
              >
                <Globe className="h-3.5 w-3.5" /> Portfolio
              </a>
            )}
          </div>

          {parsed.summary && (
            <p className="mt-6 max-w-2xl text-ink-700 leading-relaxed">
              {parsed.summary}
            </p>
          )}
        </div>

        <div className="lg:col-span-4">
          <OverallScore value={score.overall} tier={tier} />
        </div>
      </header>

      {/* Tier verdict */}
      {tier && (
        <motion.section
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="paper-card p-6 lg:p-8 mb-10 bg-gradient-to-br from-ink-100/60 to-transparent"
        >
          <div className="flex items-start gap-4">
            <Trophy className="h-5 w-5 text-flame mt-1 flex-shrink-0" />
            <div className="flex-1">
              <div className="label-overline">Panel verdict</div>
              <h2 className="font-display text-2xl font-semibold tracking-editorial mt-1 mb-3">
                {tier.label}
              </h2>
              <p className="text-ink-700 leading-relaxed max-w-3xl">
                {tier.reasoning}
              </p>
              <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-ink-900 text-ink-50 text-sm">
                <span className="text-flame-light">Next →</span>
                <span>{tier.next_action}</span>
              </div>
            </div>
          </div>
        </motion.section>
      )}

      {/* Score grid */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-12">
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ScoreDimensionCard dimensionKey="exact_match" dimension={score.exact_match} idx={0} />
          <ScoreDimensionCard dimensionKey="similarity" dimension={score.similarity} idx={1} />
          <ScoreDimensionCard dimensionKey="achievement" dimension={score.achievement} idx={2} />
          <ScoreDimensionCard dimensionKey="ownership" dimension={score.ownership} idx={3} />
        </div>
        <div className="lg:col-span-5 paper-card p-6 flex flex-col">
          <div className="label-overline mb-2">The shape of the fit</div>
          <ScoreRadar score={score} />
          <p className="text-xs text-ink-500 italic text-center mt-2">
            Higher area = stronger overall fit. Imbalance shows where to probe.
          </p>
        </div>
      </section>

      {/* Skill match table */}
      {score.skill_matches?.length > 0 && (
        <section className="mb-12">
          <SectionTitle small="II" big="Skill-by-skill ledger" />
          <SkillMatchTable matches={score.skill_matches} />
        </section>
      )}

      {/* Verification */}
      {verification && (
        <section className="mb-12">
          <SectionTitle small="III" big="Public-claim verification" />
          <VerificationPanel verification={verification} />
        </section>
      )}

      {/* Resume content — expandable */}
      <section className="mb-12">
        <SectionTitle small="IV" big="What the résumé says" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {parsed.experience?.length > 0 && (
            <ResumeBlock title="Experience" Icon={Briefcase}>
              <ul className="space-y-5">
                {parsed.experience.map((exp, i) => (
                  <li key={i} className="border-l-2 border-ink-200 pl-4">
                    <div className="font-medium text-ink-900">{exp.title}</div>
                    <div className="text-sm text-ink-600">
                      {exp.company}
                      {(exp.start_date || exp.end_date) && (
                        <span className="text-ink-400">
                          {' · '}
                          {exp.start_date} → {exp.end_date || 'Present'}
                        </span>
                      )}
                    </div>
                    {exp.bullets?.length > 0 && (
                      <ul className="mt-2 space-y-1.5">
                        {exp.bullets.map((b, j) => (
                          <li key={j} className="text-sm text-ink-700 leading-relaxed flex gap-2">
                            <span className="text-flame mt-1">▸</span>
                            <span>{b}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </ResumeBlock>
          )}

          {parsed.projects?.length > 0 && (
            <ResumeBlock title="Projects" Icon={FolderGit2}>
              <ul className="space-y-4">
                {parsed.projects.map((p, i) => (
                  <li key={i} className="border-l-2 border-ink-200 pl-4">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-ink-900">{p.name}</span>
                      {p.url && (
                        <a
                          href={p.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-flame hover:underline"
                        >
                          ↗
                        </a>
                      )}
                    </div>
                    {p.description && (
                      <p className="text-sm text-ink-600 mt-0.5">{p.description}</p>
                    )}
                    {p.technologies?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {p.technologies.map((t) => (
                          <span
                            key={t}
                            className="pill text-[10px] bg-ink-100 text-ink-600 font-mono"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                    {p.bullets?.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {p.bullets.map((b, j) => (
                          <li key={j} className="text-sm text-ink-700 leading-relaxed flex gap-2">
                            <span className="text-flame mt-1">▸</span>
                            <span>{b}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </ResumeBlock>
          )}

          {parsed.education?.length > 0 && (
            <ResumeBlock title="Education" Icon={GraduationCap}>
              <ul className="space-y-3">
                {parsed.education.map((e, i) => (
                  <li key={i}>
                    <div className="font-medium text-ink-900">{e.institution}</div>
                    <div className="text-sm text-ink-600">
                      {[e.degree, e.field_of_study].filter(Boolean).join(' · ')}
                    </div>
                    {(e.start_year || e.end_year) && (
                      <div className="text-xs text-ink-500">
                        {e.start_year} → {e.end_year || '—'}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </ResumeBlock>
          )}

          {parsed.skills?.length > 0 && (
            <ResumeBlock title="Skills" Icon={Sparkles}>
              <div className="flex flex-wrap gap-1.5">
                {parsed.skills.map((s) => (
                  <span
                    key={s}
                    className="pill text-xs bg-ink-100 text-ink-700 font-mono"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </ResumeBlock>
          )}
        </div>
      </section>

      {/* Interview plan */}
      <section className="mb-16">
        <SectionTitle small="V" big="Tailored interview plan" />
        {interview ? (
          <div className="space-y-4">
            <InterviewPlanHeader plan={interview} />
            <div className="space-y-3">
              {interview.questions.map((q, i) => (
                <InterviewQuestionCard key={i} q={q} idx={i} />
              ))}
            </div>
          </div>
        ) : (
          <div className="paper-card p-10 text-center">
            <Sparkles className="h-8 w-8 text-flame mx-auto mb-3" />
            <h3 className="font-display text-2xl font-semibold tracking-editorial mb-2">
              Generate questions for {parsed.name?.split(' ')[0] || 'this candidate'}
            </h3>
            <p className="text-ink-600 mb-6 max-w-md mx-auto">
              Eight questions, tuned to this candidate's projects, gaps, and seniority — costs ~3 seconds and one LLM call.
            </p>
            {genError && (
              <p className="text-sm text-flame-dark mb-3">{genError}</p>
            )}
            <button
              onClick={generateInterview}
              disabled={genLoading}
              className="btn-flame text-base px-6 py-3"
            >
              {genLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Writing…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" /> Generate interview
                </>
              )}
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

function SectionTitle({ small, big }) {
  return (
    <header className="mb-5 flex items-baseline gap-3">
      <span className="font-display text-2xl text-flame/40 font-semibold">{small}</span>
      <h2 className="font-display text-3xl font-semibold tracking-editorial">{big}</h2>
    </header>
  )
}

function ResumeBlock({ title, Icon, children }) {
  return (
    <div className="paper-card p-6">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="h-4 w-4 text-ink-500" />
        <span className="label-overline">{title}</span>
      </div>
      {children}
    </div>
  )
}
