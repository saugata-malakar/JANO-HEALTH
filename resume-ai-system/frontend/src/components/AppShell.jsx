import { Link, useLocation } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuthClient, useUserClient } from '../hooks/useAuthClient'
import Logo from './Logo'

export default function AppShell({ children }) {
  const { signOut } = useAuthClient()
  const { user } = useUserClient()
  const location = useLocation()

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="sticky top-0 z-40 bg-ink-50/80 backdrop-blur-xl border-b border-ink-200">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-3 group">
            <Logo className="h-8 w-8 text-ink-900 transition-transform group-hover:rotate-[-8deg]" />
            <div className="leading-tight">
              <div className="font-display text-xl font-semibold tracking-editorial">
                HireSense
              </div>
              <div className="text-[10px] text-ink-500 uppercase tracking-[0.2em] -mt-0.5">
                Issue No. 01 · Spring 2026
              </div>
            </div>
          </Link>

          <div className="flex items-center gap-6">
            <NavLink to="/dashboard" current={location.pathname}>
              Triage
            </NavLink>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-sm text-ink-600 hover:text-ink-900 transition-colors"
            >
              API
            </a>
            <div className="h-5 w-px bg-ink-200" />
            <div className="flex items-center gap-3">
              <div className="text-right leading-tight hidden sm:block">
                <div className="text-sm font-medium text-ink-900">
                  {user?.firstName || 'Recruiter'}
                </div>
                <div className="text-[11px] text-ink-500">
                  {user?.primaryEmailAddress?.emailAddress || ''}
                </div>
              </div>
              <button
                onClick={() => signOut()}
                className="p-2 rounded-full hover:bg-ink-100 transition-colors text-ink-600"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-ink-200 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-500">
          <div>© 2026 HireSense · Built for the assignment</div>
          <div className="flex items-center gap-4">
            <span>v1.0.0</span>
            <span>·</span>
            <span>4 modules · 1 pipeline</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

function NavLink({ to, current, children }) {
  const active = current === to
  return (
    <Link
      to={to}
      className={`text-sm transition-colors relative ${
        active ? 'text-ink-900 font-medium' : 'text-ink-600 hover:text-ink-900'
      }`}
    >
      {children}
      {active && (
        <span className="absolute -bottom-[21px] left-0 right-0 h-[2px] bg-flame" />
      )}
    </Link>
  )
}
