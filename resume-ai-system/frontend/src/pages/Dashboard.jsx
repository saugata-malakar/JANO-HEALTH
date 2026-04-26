import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload,
  FileText,
  X,
  Sparkles,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Trash2,
  Wand2,
} from 'lucide-react'

import { api, ApiError } from '../lib/api'
import { useAuthClient } from '../hooks/useAuthClient'
import { TierBadge } from '../components/Scores'

/**
 * Dashboard
 * ---------
 * The recruiter's working desk.
 *
 *   1. Compose / paste / load a Job Description on the left.
 *   2. Drag-and-drop one or many resumes on the right.
 *   3. Hit "Run triage" → batch evaluation runs in parallel.
 *   4. A live results table appears below, sorted by overall score.
 *   5. Click any row to deep-dive into /results/<candidate_id>.
 *
 * We persist the latest batch in sessionStorage so navigating to a
 * results page and back doesn't lose work.
 */

const SESSION_KEY = 'hiresense:lastBatch'

export default function Dashboard() {
  const { getToken } = useAuthClient()
  const navigate = useNavigate()

  const [jd, setJd] = useState({
    title: '',
    company: '',
    description: '',
    required_skills: [],
    nice_to_have: [],
    seniority: 'mid',
    years_experience: 3,
  })
  const [skillsRaw, setSkillsRaw] = useState('')
  const [niceRaw, setNiceRaw] = useState('')
  const [files, setFiles] = useState([])
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const [loadedDemo, setLoadedDemo] = useState(false)

  // Restore previous batch on mount
  useEffect(() => {
    try {
      const cached = sessionStorage.getItem(SESSION_KEY)
      if (cached) {
        const parsed = JSON.parse(cached)
        if (parsed?.results) setResults(parsed.results)
        if (parsed?.jd) {
          setJd(parsed.jd)
          setSkillsRaw((parsed.jd.required_skills || []).join(', '))
          setNiceRaw((parsed.jd.nice_to_have || []).join(', '))
        }
      }
    } catch (_) {
      /* ignore */
    }
  }, [])

  const loadSampleJD = useCallback(async () => {
    try {
      const sample = await api.sampleJD()
      setJd(sample)
      setSkillsRaw((sample.required_skills || []).join(', '))
      setNiceRaw((sample.nice_to_have || []).join(', '))
      setLoadedDemo(true)
    } catch (e) {
      setError(`Could not load sample JD: ${e.message}`)
    }
  }, [])

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected?.length) {
      setError(
        `Skipped ${rejected.length} file(s): only PDF/DOCX/TXT, max 5 MB each.`
      )
    }
    setFiles((prev) => {
      const seen = new Set(prev.map((f) => `${f.name}-${f.size}`))
      const fresh = accepted.filter((f) => !seen.has(`${f.name}-${f.size}`))
      return [...prev, ...fresh].slice(0, 25)
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: 5 * 1024 * 1024,
    noClick: false,
  })

  const removeFile = (name, size) => {
    setFiles((prev) => prev.filter((f) => !(f.name === name && f.size === size)))
  }

  const clearAll = () => {
    setFiles([])
    setResults([])
    sessionStorage.removeItem(SESSION_KEY)
  }

  const canRun = useMemo(() => {
    return (
      !running &&
      files.length > 0 &&
      jd.title.trim().length > 2 &&
      jd.description.trim().length > 20 &&
      skillsRaw.trim().length > 0
    )
  }, [running, files, jd, skillsRaw])

  const buildJD = () => ({
    ...jd,
    required_skills: skillsRaw
      .split(/[,\n]/)
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
    nice_to_have: niceRaw
      .split(/[,\n]/)
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
  })

  const runTriage = async () => {
    setRunning(true)
    setError(null)
    setResults([])
    const finalJD = buildJD()
    try {
      const data = await api.evaluateBatch(
        {
          files,
          jd: finalJD,
          verify: true,
          generate_questions: false,
        },
        { getToken }
      )
      const sorted = [...data].sort(
        (a, b) => (b.score?.overall || 0) - (a.score?.overall || 0)
      )
      setResults(sorted)
      // Persist for the Results page
      sessionStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ results: sorted, jd: finalJD })
      )
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.status}: ${e.message}`
          : e?.message || 'Unknown error'
      setError(msg)
    } finally {
      setRunning(false)
    }
  }

  const openResult = (candidateId) => {
    navigate(`/results/${candidateId}`)
  }

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-8 py-10">
      {/* Page header */}
      <header className="mb-10 flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="label-overline">The desk</div>
          <h1 className="editorial-headline text-5xl font-semibold mt-1">
            Triage room.
          </h1>
          <p className="mt-2 text-ink-600 max-w-xl">
            Compose the role, drop the résumés, and let the four engines do
            their reading.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadSampleJD}
            className="btn-secondary text-sm"
            disabled={running}
          >
            <Wand2 className="h-3.5 w-3.5" />
            {loadedDemo ? 'Sample loaded' : 'Load sample JD'}
          </button>
          {(files.length > 0 || results.length > 0) && (
            <button onClick={clearAll} className="btn-secondary text-sm" disabled={running}>
              <Trash2 className="h-3.5 w-3.5" /> Clear
            </button>
          )}
        </div>
      </header>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mb-6 paper-card p-4 border-flame/40 bg-flame/5 flex items-start gap-3"
          >
            <AlertTriangle className="h-4 w-4 text-flame-dark mt-0.5 flex-shrink-0" />
            <div className="flex-1 text-sm text-flame-dark">{error}</div>
            <button
              onClick={() => setError(null)}
              className="text-flame-dark/60 hover:text-flame-dark"
            >
              <X className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* JD column */}
        <section className="lg:col-span-7 paper-card p-6 lg:p-8 space-y-5">
          <div>
            <span className="label-overline">Section A · Job description</span>
            <h2 className="font-display text-2xl font-semibold tracking-editorial mt-1">
              The role you're hiring for.
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Title" required>
              <input
                type="text"
                value={jd.title}
                onChange={(e) => setJd({ ...jd, title: e.target.value })}
                placeholder="Senior Backend Engineer"
                className="input"
              />
            </Field>
            <Field label="Company">
              <input
                type="text"
                value={jd.company || ''}
                onChange={(e) => setJd({ ...jd, company: e.target.value })}
                placeholder="Streamline Systems"
                className="input"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Seniority">
              <select
                value={jd.seniority || 'mid'}
                onChange={(e) => setJd({ ...jd, seniority: e.target.value })}
                className="input"
              >
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="staff">Staff / Principal</option>
              </select>
            </Field>
            <Field label="Years of experience expected">
              <input
                type="number"
                min={0}
                max={30}
                value={jd.years_experience ?? ''}
                onChange={(e) =>
                  setJd({
                    ...jd,
                    years_experience: e.target.value ? parseInt(e.target.value, 10) : null,
                  })
                }
                className="input"
              />
            </Field>
          </div>

          <Field label="Description" required>
            <textarea
              rows={6}
              value={jd.description}
              onChange={(e) => setJd({ ...jd, description: e.target.value })}
              placeholder="Paste the full job posting. The more detail, the better the questions."
              className="input resize-none leading-relaxed"
            />
          </Field>

          <Field label="Required skills" required hint="Comma or newline separated. These drive the score.">
            <textarea
              rows={2}
              value={skillsRaw}
              onChange={(e) => setSkillsRaw(e.target.value)}
              placeholder="python, kafka, postgresql, kubernetes, redis"
              className="input resize-none font-mono text-sm"
            />
          </Field>

          <Field label="Nice to have" hint="Lower-weight skills.">
            <textarea
              rows={2}
              value={niceRaw}
              onChange={(e) => setNiceRaw(e.target.value)}
              placeholder="go, grpc, snowflake"
              className="input resize-none font-mono text-sm"
            />
          </Field>
        </section>

        {/* Resume column */}
        <section className="lg:col-span-5 space-y-6">
          <div className="paper-card p-6 lg:p-8">
            <div className="mb-4">
              <span className="label-overline">Section B · Résumés</span>
              <h2 className="font-display text-2xl font-semibold tracking-editorial mt-1">
                Drop the stack.
              </h2>
            </div>

            <div
              {...getRootProps()}
              className={`relative cursor-pointer rounded-xl border-2 border-dashed transition-all p-8 text-center ${
                isDragActive
                  ? 'border-flame bg-flame/5'
                  : 'border-ink-300 bg-ink-100/40 hover:border-ink-500 hover:bg-ink-100/60'
              }`}
            >
              <input {...getInputProps()} />
              <Upload
                className={`h-8 w-8 mx-auto mb-3 transition-colors ${
                  isDragActive ? 'text-flame' : 'text-ink-500'
                }`}
              />
              <p className="text-sm font-medium text-ink-800">
                {isDragActive ? 'Drop them right here.' : 'Drag résumés here'}
              </p>
              <p className="text-xs text-ink-500 mt-1">
                or click to browse · PDF / DOCX / TXT · max 5MB each · up to 25 files
              </p>
            </div>

            {files.length > 0 && (
              <ul className="mt-4 space-y-2 max-h-72 overflow-y-auto pr-1">
                {files.map((f) => (
                  <li
                    key={`${f.name}-${f.size}`}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ink-100/60 border border-ink-200"
                  >
                    <FileText className="h-4 w-4 text-ink-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-ink-800 truncate font-medium">
                        {f.name}
                      </div>
                      <div className="text-[11px] text-ink-500">
                        {(f.size / 1024).toFixed(0)} KB
                      </div>
                    </div>
                    <button
                      onClick={() => removeFile(f.name, f.size)}
                      className="text-ink-400 hover:text-flame-dark transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            onClick={runTriage}
            disabled={!canRun}
            className="w-full btn-primary text-base py-3.5 disabled:bg-ink-300"
          >
            {running ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Reading {files.length} résumé{files.length !== 1 ? 's' : ''}…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run triage on {files.length || 'your'} résumé{files.length === 1 ? '' : 's'}
              </>
            )}
          </button>

          {!canRun && !running && (
            <p className="text-xs text-ink-500 text-center -mt-3">
              {files.length === 0
                ? 'Drop at least one résumé.'
                : 'Fill in title, description, and required skills.'}
            </p>
          )}
        </section>
      </div>

      {/* Results table */}
      {(running || results.length > 0) && (
        <section className="mt-12">
          <header className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
            <div>
              <span className="label-overline">Section C · Verdicts</span>
              <h2 className="font-display text-3xl font-semibold tracking-editorial mt-1">
                {running ? 'Reading…' : `${results.length} candidates, sorted.`}
              </h2>
            </div>
            {!running && results.length > 0 && (
              <div className="flex items-center gap-3 text-xs">
                <TierLegend tier="A" count={results.filter((r) => r.tier?.tier === 'A').length} />
                <TierLegend tier="B" count={results.filter((r) => r.tier?.tier === 'B').length} />
                <TierLegend tier="C" count={results.filter((r) => r.tier?.tier === 'C').length} />
              </div>
            )}
          </header>

          {running ? (
            <SkeletonRows count={Math.min(files.length, 6)} />
          ) : (
            <div className="paper-card overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-ink-200 bg-ink-100/40">
                    <th className="text-left px-5 py-3 label-overline">Candidate</th>
                    <th className="text-left px-5 py-3 label-overline hidden md:table-cell">Tier</th>
                    <th className="text-right px-5 py-3 label-overline">Exact</th>
                    <th className="text-right px-5 py-3 label-overline">Similar</th>
                    <th className="text-right px-5 py-3 label-overline hidden lg:table-cell">Achv.</th>
                    <th className="text-right px-5 py-3 label-overline hidden lg:table-cell">Own.</th>
                    <th className="text-right px-5 py-3 label-overline">Overall</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <ResultRow key={r.candidate_id + i} r={r} idx={i} onClick={() => openResult(r.candidate_id)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

function Field({ label, hint, required, children }) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="label-overline">
          {label}
          {required && <span className="text-flame ml-1">*</span>}
        </span>
        {hint && <span className="text-[10px] text-ink-400">{hint}</span>}
      </div>
      {children}
    </label>
  )
}

function ResultRow({ r, idx, onClick }) {
  const tierColor = {
    A: 'bg-moss text-ink-50',
    B: 'bg-ink-700 text-ink-50',
    C: 'bg-flame text-ink-50',
  }[r.tier?.tier || 'C']

  return (
    <motion.tr
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
      onClick={onClick}
      className="border-b border-ink-100 last:border-b-0 cursor-pointer hover:bg-ink-100/50 transition-colors group"
    >
      <td className="px-5 py-4">
        <div className="font-medium text-ink-900">
          {r.parsed?.name || 'Unnamed candidate'}
        </div>
        <div className="text-xs text-ink-500 truncate max-w-[28ch]">
          {r.parsed?.headline || r.parsed?.email || ''}
        </div>
      </td>
      <td className="px-5 py-4 hidden md:table-cell">
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${tierColor}`}
        >
          Tier {r.tier?.tier}
          <span className="opacity-70">·</span>
          <span>{r.tier?.label}</span>
        </span>
      </td>
      <ScoreCell value={r.score?.exact_match?.value} />
      <ScoreCell value={r.score?.similarity?.value} />
      <ScoreCell value={r.score?.achievement?.value} className="hidden lg:table-cell" />
      <ScoreCell value={r.score?.ownership?.value} className="hidden lg:table-cell" />
      <td className="px-5 py-4 text-right">
        <div className="stat-num text-2xl text-ink-900 group-hover:text-flame transition-colors">
          {Math.round(r.score?.overall || 0)}
        </div>
      </td>
    </motion.tr>
  )
}

function ScoreCell({ value, className = '' }) {
  const v = Math.round(value || 0)
  const color = v >= 75 ? 'text-moss' : v >= 50 ? 'text-ink-700' : 'text-ink-400'
  return (
    <td className={`px-5 py-4 text-right tabular-nums ${color} ${className}`}>
      {v}
    </td>
  )
}

function TierLegend({ tier, count }) {
  const c = {
    A: 'bg-moss',
    B: 'bg-ink-700',
    C: 'bg-flame',
  }[tier]
  return (
    <span className="inline-flex items-center gap-1.5 text-ink-600">
      <span className={`h-2 w-2 rounded-full ${c}`} />
      <span>
        Tier {tier} · {count}
      </span>
    </span>
  )
}

function SkeletonRows({ count }) {
  return (
    <div className="paper-card overflow-hidden">
      <div className="divide-y divide-ink-100">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="px-5 py-4 flex items-center gap-4">
            <div className="flex-1 space-y-2">
              <div className="h-4 w-48 shimmer rounded" />
              <div className="h-3 w-32 shimmer rounded opacity-70" />
            </div>
            <div className="h-6 w-24 shimmer rounded-full" />
            <div className="flex items-center gap-1.5 text-xs text-ink-400">
              <Clock className="h-3 w-3 animate-pulse" />
              <span className="hidden sm:inline">parsing… scoring… verifying…</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
