/**
 * useAuthClient — small wrapper around Clerk's useAuth() that supports
 * bypass mode for demos / screen recordings without a Clerk account.
 */
import { useAuth as useClerkAuth, useUser as useClerkUser } from '@clerk/clerk-react'

const BYPASS = import.meta.env.VITE_BYPASS_AUTH === 'true'

export function useAuthClient() {
  if (BYPASS) {
    return {
      isSignedIn: true,
      isLoaded: true,
      getToken: async () => null,
      signOut: () => { window.location.href = '/' },
    }
  }
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useClerkAuth()
}

export function useUserClient() {
  if (BYPASS) {
    return {
      isLoaded: true,
      user: { firstName: 'Guest', primaryEmailAddress: { emailAddress: 'demo@hiresense.local' } },
    }
  }
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useClerkUser()
}
