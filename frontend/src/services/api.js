import axios from 'axios'

export const TOKEN_KEY = 'ss_token'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url || ''
    // An expired/invalid session on a normal request -> tell the app to sign out.
    if (err.response?.status === 401 && !url.startsWith('/auth/login')) {
      window.dispatchEvent(new Event('auth:expired'))
    }
    return Promise.reject(err)
  }
)

/** Turns any axios/FastAPI error into a short, user-friendly sentence. */
export function errorMessage(err, fallback = 'Something went wrong. Please try again.') {
  if (!err.response) return 'Cannot reach the server. Check your connection and try again.'
  const detail = err.response.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') return detail.message
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{loc, msg}, ...]
    const first = detail[0]
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : ''
    const msg = String(first.msg || '').replace(/^Value error, /, '')
    return field && field !== 'body' ? `${field}: ${msg}` : msg
  }
  if (err.response.status === 429) return 'Too many attempts. Please wait a moment and try again.'
  return fallback
}
