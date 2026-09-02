/**
 * Authentication state.
 *
 * The token is the single source of truth: it is stored once, and the current
 * user is fetched from /api/me so a stale or revoked token is detected on load
 * rather than trusted from local storage.
 */

import { useQueryClient } from '@tanstack/react-query'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { authApi } from '@/services/api/endpoints'
import { tokenStorage, UNAUTHORIZED_EVENT } from '@/services/api/client'
import type { AuthToken, User } from '@/types/api'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  signIn: (token: AuthToken) => void
  signOut: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(() => tokenStorage.get() !== null)
  const queryClient = useQueryClient()

  const loadUser = useCallback(async () => {
    if (!tokenStorage.get()) {
      setUser(null)
      setIsLoading(false)
      return
    }
    try {
      setUser(await authApi.me())
    } catch {
      // An invalid token is cleared by the client; treat it as signed out.
      tokenStorage.clear()
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadUser()
  }, [loadUser])

  // Any 401 anywhere in the app ends the session exactly once.
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null)
      queryClient.clear()
    }
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [queryClient])

  const signIn = useCallback(
    (token: AuthToken) => {
      tokenStorage.set(token.access_token)
      setUser(token.user)
      setIsLoading(false)
      void queryClient.invalidateQueries()
    },
    [queryClient],
  )

  const signOut = useCallback(() => {
    tokenStorage.clear()
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      isAdmin: user?.role === 'ADMIN',
      signIn,
      signOut,
      refresh: loadUser,
    }),
    [user, isLoading, signIn, signOut, loadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
