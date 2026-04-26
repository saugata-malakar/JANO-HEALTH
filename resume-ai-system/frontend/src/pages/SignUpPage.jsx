import { SignUp } from '@clerk/clerk-react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-6 py-5">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <Logo className="h-7 w-7 text-ink-900" />
          <span className="font-display text-lg font-semibold tracking-editorial">HireSense</span>
        </Link>
      </header>
      <main className="flex-1 grid place-items-center px-6 py-12">
        <div className="w-full max-w-md">
          <h1 className="editorial-headline text-4xl font-semibold mb-3 text-center">
            Make an account.
          </h1>
          <p className="text-center text-ink-500 mb-8">
            Read fewer résumés this week.
          </p>
          <div className="paper-card p-1.5">
            <SignUp
              appearance={{ elements: { card: 'bg-transparent shadow-none' } }}
              routing="path"
              path="/sign-up"
              signInUrl="/sign-in"
              afterSignUpUrl="/dashboard"
            />
          </div>
        </div>
      </main>
    </div>
  )
}
