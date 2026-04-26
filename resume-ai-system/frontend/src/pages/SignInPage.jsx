import { SignIn } from '@clerk/clerk-react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'

export default function SignInPage() {
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
          <h1 className="editorial-headline text-4xl font-semibold mb-8 text-center">
            Welcome back.
          </h1>
          <div className="paper-card p-1.5">
            <SignIn
              appearance={{ elements: { card: 'bg-transparent shadow-none' } }}
              routing="path"
              path="/sign-in"
              signUpUrl="/sign-up"
              afterSignInUrl="/dashboard"
            />
          </div>
        </div>
      </main>
    </div>
  )
}
