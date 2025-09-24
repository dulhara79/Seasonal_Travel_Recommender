import React, { createContext, useContext, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthContext = createContext()
const API_BASE = import.meta.env.VITE_API_BASE || ''

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  const navigate = useNavigate()

  useEffect(() => {
    let mounted = true
    async function fetchProfile() {
      if (!token) return
      try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error('Unauth')
        const data = await res.json()
        if (mounted) setUser(data)
      } catch (e) {
        if (mounted) {
          setUser(null)
          setToken(null)
          localStorage.removeItem('access_token')
        }
      }
    }
    fetchProfile()
    return () => {
      mounted = false
    }
  }, [token])

  const login = async ({ login, password }) => {
    const body = new URLSearchParams()
    body.append('username', login)
    body.append('password', password)

    const res = await fetch(`${API_BASE}/api/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    localStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    return data
  }

  const signup = async ({ username, name, email, password }) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, name, email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Registration failed')
    }
    const data = await res.json()
    // Auto-login
    await login({ login: username, password })
    return data
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('access_token')
    navigate('/login')
  }

  const value = { user, token, login, signup, logout, isAuthenticated: !!token }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

export default AuthContext
