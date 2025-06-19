import React, { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../services/api'

interface User {
  id: number
  email: string
  username: string
  is_active: boolean
  created_at: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is logged in
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token')
      if (token) {
        try {
          const response = await authAPI.getUser()
          setUser(response.data)
        } catch (error) {
          localStorage.removeItem('access_token')
        }
      }
      setLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (username: string, password: string) => {
    const response = await authAPI.login(username, password)
    localStorage.setItem('access_token', response.data.access_token)
    
    // Get user data
    const userResponse = await authAPI.getUser()
    setUser(userResponse.data)
  }

  const logout = async () => {
    await authAPI.logout()
    localStorage.removeItem('access_token')
    setUser(null)
  }

  const register = async (email: string, username: string, password: string) => {
    await authAPI.register({ email, username, password })
    // Auto-login after registration
    await login(username, password)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  )
}