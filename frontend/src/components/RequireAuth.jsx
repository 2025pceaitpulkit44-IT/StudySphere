import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './ui'

export const homeFor = (user) => (user?.role === 'admin' ? '/admin' : '/')

/** Gate for a route group. `role` restricts it to one role; the backend enforces the same rule on every API call. */
export default function RequireAuth({ role }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Spinner label="Restoring your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (role && user.role !== role) return <Navigate to={homeFor(user)} replace />
  return <Outlet />
}
