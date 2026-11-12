import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { TOKEN_KEY } from '../services/api'
import { authService } from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!localStorage.getItem(TOKEN_KEY))

  const clear = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }, [])

  // Restore the session on page load.
  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return
    authService.me().then(setUser).catch(clear).finally(() => setLoading(false))
  }, [clear])

  // Interceptor fires this when the server rejects our token (e.g. it expired).
  useEffect(() => {
    window.addEventListener('auth:expired', clear)
    return () => window.removeEventListener('auth:expired', clear)
  }, [clear])

  const accept = (data) => {
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setUser(data.user)
    return data.user
  }

  const value = {
    user,
    loading,
    login: async (email, password) => accept(await authService.login(email, password)),
    register: async (payload) => accept(await authService.register(payload)),
    logout: async () => {
      await authService.logout()
      clear()
    },
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
