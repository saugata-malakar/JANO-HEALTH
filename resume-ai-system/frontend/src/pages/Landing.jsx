import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowUpRight,
  FileText,
  ScanLine,
  ShieldCheck,
  MessageCircleQuestion,
  Github,
} from 'lucide-react'
import Logo from '../components/Logo'

const BYPASS = import.meta.env.VITE_BYPASS_AUTH === 'true'

export default function Landing() {
  return (
    <div className="min-h-screen relative">
      {/* Top nav */}
      <nav className="absolute top-0 left-0 right-0 z-20">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Logo className="h-8 w-8 text-ink-900" />
            <span className="font-display text-xl font-semibold tracking-editorial">
              HireSense
            </span>
          </div>
          <div className="flex items-center gap-2">
            {!BYPASS && (
              <Link to="/sign-in" className="btn-secondary">
                Sign in
              </Link>
            )}
            <Link to={BYPASS ? '/dashboard' : '/sign-up'} className="btn-primary">
              {BYPASS ? 'Open dashboard' : 'Get started'}
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero — editorial cover spread */}
      <section className="relative pt-32 pb-24 lg:pt-40 lg:pb-32 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="grid grid-cols-12 gap-6 lg:gap-12"
          >
            {/* Left rail — issue marker */}
            <div className="col-span-12 lg:col-span-2">
              <div className="space-y-1 lg:sticky lg:top-24">
                <div className="text-[10px] uppercase tracking-[0.25em] text-ink-500 font-semibold">
                  Issue 01
                </div>
                <div className="h-px w-12 bg-flame" />
                <div className="text-[10px] uppercase tracking-[0.25em] text-ink-500">
                  Spring 2026
                </div>
              </div>
            </div>

            {/* Headline */}
            <div className="col-span-12 lg:col-span-9 lg:col-start-3">
              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
              >
                <p className="text-sm uppercase tracking-[0.2em] text-flame font-semibold mb-6">
                  AI Resume Triage · Built for the modern panel
                </p>
                <h1 className="editorial-headline text-[64px] sm:text-[88px] lg:text-[124px] font-semibold">
                  The hiring{' '}
                  <span className="italic font-normal">panel's</span>
                  <br />
                  research desk.
                </h1>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="mt-12 grid grid-cols-12 gap-6"
              >
                <p className="col-span-12 md:col-span-7 text-lg leading-relaxed text-ink-700 max-w-xl">
                  Drop a stack of résumés. We read every page, score four
                  dimensions of fit, verify the public claims, and write
                  questions tailored to each person — so the panel can spend
                  its time on judgement, not paper-shuffling.
                </p>
                <div className="col-span-12 md:col-span-5 md:pl-6 md:border-l md:border-ink-300 self-start">
                  <p className="text-sm leading-relaxed text-ink-600 italic">
                    "It told me <em className="text-flame not-italic font-medium">Kinesis is a Kafka</em> in different
                    clothing — and gave me three questions to make sure the
                    candidate could actually do the migration."
                  </p>
                  <p className="mt-2 text-xs text-ink-500 not-italic">
                    — what we want recruiters to say
                  </p>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.35 }}
                className="mt-10 flex flex-wrap items-center gap-3"
              >
                <Link to={BYPASS ? '/dashboard' : '/sign-up'} className="btn-primary text-base px-6 py-3">
                  {BYPASS ? 'Open the dashboard' : 'Start triaging'}
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
                <a
                  href="#how-it-works"
                  className="btn-secondary text-base px-6 py-3"
                >
                  How it works
                </a>
              </motion.div>
            </div>
          </motion.div>
        </div>

        {/* Decorative numerals */}
        <div className="absolute -bottom-20 -right-12 lg:-right-4 pointer-events-none select-none">
          <span className="font-display text-[18rem] lg:text-[28rem] leading-none text-flame/[0.04] font-semibold">
            01
          </span>
        </div>
      </section>

      {/* Pull-quote separator */}
      <section className="border-y border-ink-200 bg-ink-100/40 py-10">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 grid grid-cols-12 gap-4 items-baseline">
          <div className="col-span-12 md:col-span-3">
            <span className="label-overline">By the numbers</span>
          </div>
          <Stat n="4" label="score dimensions" />
          <Stat n="0.05¢" label="per resume LLM cost" />
          <Stat n="10k+" label="resumes/day capacity" />
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-12 md:col-span-3">
              <span className="label-overline">II</span>
              <h2 className="mt-2 font-display text-4xl font-semibold tracking-editorial">
                Four engines, one verdict.
              </h2>
            </div>
            <div className="col-span-12 md:col-span-9 md:pl-12">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Engine
                  num="01"
                  Icon={FileText}
                  title="Parser"
                  body="PDF and DOCX in. Strict-schema JSON out. Falls back to regex when the LLM gets nervous, so no resume ever produces a blank page."
                />
                <Engine
                  num="02"
                  Icon={ScanLine}
                  title="Scoring"
                  body="Four dimensions — Exact, Similarity, Achievement, Ownership. Each carries a sentence of reasoning and the bullets that drove it."
                />
                <Engine
                  num="03"
                  Icon={ShieldCheck}
                  title="Verification"
                  body="GitHub commit cadence, repo age, language fingerprint. We tell you when the resume claims Go but the commits are PHP."
                />
                <Engine
                  num="04"
                  Icon={MessageCircleQuestion}
                  title="Tier & Questions"
                  body="A, B, or C. Then eight questions written for this candidate — referencing their projects, their gaps, their seniority."
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Kinesis ↔ Kafka highlight */}
      <section className="py-24 bg-ink-900 text-ink-50 relative overflow-hidden">
        <div className="absolute inset-0 bg-noise opacity-[0.07] pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 lg:px-8 relative">
          <div className="grid grid-cols-12 gap-6 items-center">
            <div className="col-span-12 md:col-span-7">
              <span className="label-overline text-flame-light">III · The Kinesis problem</span>
              <h2 className="mt-3 editorial-headline text-5xl md:text-6xl font-semibold">
                A candidate has Kinesis.
                <br />
                The role wants Kafka.
              </h2>
              <p className="mt-6 text-lg text-ink-300 max-w-xl leading-relaxed">
                Most ATS systems mark this candidate{' '}
                <span className="line-through text-ink-500">missing</span>. We
                embed both, see they live in the same conceptual neighbourhood,
                surface the kinship as a <em className="text-flame-light not-italic">semantic match</em>,
                and write the rationale recruiters need to defend the decision.
              </p>
            </div>
            <div className="col-span-12 md:col-span-5">
              <div className="bg-ink-800/60 border border-ink-700 rounded-2xl p-6 font-mono text-sm space-y-3">
                <div>
                  <div className="text-ink-400 text-xs uppercase tracking-wider mb-1">JD requires</div>
                  <div className="text-flame-light">kafka</div>
                </div>
                <div className="h-px bg-ink-700" />
                <div>
                  <div className="text-ink-400 text-xs uppercase tracking-wider mb-1">Resume has</div>
                  <div className="text-ink-100">kinesis</div>
                </div>
                <div className="h-px bg-ink-700" />
                <div>
                  <div className="text-ink-400 text-xs uppercase tracking-wider mb-1">Cosine similarity</div>
                  <div className="text-2xl text-moss font-display tabular-nums">0.71</div>
                </div>
                <div className="h-px bg-ink-700" />
                <div className="text-ink-300 italic text-xs leading-relaxed">
                  "Both are partitioned, append-only event streams — operational
                  concepts transfer directly."
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-28">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="editorial-headline text-5xl md:text-7xl font-semibold">
            Ready to read fewer résumés?
          </h2>
          <p className="mt-6 text-lg text-ink-600 max-w-xl mx-auto">
            Sign in, paste a JD, drop a stack. We'll do the rest.
          </p>
          <div className="mt-10">
            <Link to={BYPASS ? '/dashboard' : '/sign-up'} className="btn-flame text-base px-8 py-3.5">
              {BYPASS ? 'Open the dashboard' : 'Create an account'}
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-ink-200 py-10 text-xs text-ink-500">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo className="h-5 w-5 text-ink-900" />
            <span>HireSense · 2026</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 hover:text-ink-900 transition-colors"
            >
              <Github className="h-3.5 w-3.5" /> Source
            </a>
            <span>·</span>
            <a
              href="https://github.com#system-design"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-900 transition-colors"
            >
              Architecture
            </a>
            <span>·</span>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-900 transition-colors"
            >
              API
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

function Stat({ n, label }) {
  return (
    <div className="col-span-4 md:col-span-3">
      <div className="stat-num text-5xl md:text-6xl text-ink-900">{n}</div>
      <div className="text-xs text-ink-500 uppercase tracking-wider mt-1">{label}</div>
    </div>
  )
}

function Engine({ num, Icon, title, body }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ duration: 0.5 }}
      className="paper-card p-6 hover:shadow-editorial transition-all hover:-translate-y-0.5"
    >
      <div className="flex items-start gap-3 mb-3">
        <span className="font-display text-3xl text-flame/40 font-semibold">{num}</span>
        <Icon className="h-5 w-5 text-ink-700 mt-2" />
      </div>
      <h3 className="font-display text-2xl font-semibold tracking-editorial mb-2">
        {title}
      </h3>
      <p className="text-sm text-ink-600 leading-relaxed">{body}</p>
    </motion.div>
  )
}
