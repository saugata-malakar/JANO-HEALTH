import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ClerkProvider, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react'

import './index.css'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Results from './pages/Results'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'
import AppShell from './components/AppShell'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY
const BYPASS_AUTH = import.meta.env.VITE_BYPASS_AUTH === 'true'

if (!PUBLISHABLE_KEY && !BYPASS_AUTH) {
  // eslint-disable-next-line no-console
  console.warn(
    'No VITE_CLERK_PUBLISHABLE_KEY set. Either add one or set VITE_BYPASS_AUTH=true for demo mode.'
  )
}

function ProtectedRoute({ children }) {
  if (BYPASS_AUTH) return children
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut><RedirectToSignIn /></SignedOut>
    </>
  )
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/sign-in/*" element={<SignInPage />} />
        <Route path="/sign-up/*" element={<SignUpPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppShell><Dashboard /></AppShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/results/:candidateId"
          element={
            <ProtectedRoute>
              <AppShell><Results /></AppShell>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

const root = ReactDOM.createRoot(document.getElementById('root'))

if (BYPASS_AUTH || !PUBLISHABLE_KEY) {
  // Demo mode: skip Clerk entirely
  root.render(<React.StrictMode><AppRoutes /></React.StrictMode>)
} else {
  root.render(
    <React.StrictMode>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
        <AppRoutes />
      </ClerkProvider>
    </React.StrictMode>
  )
}
