import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import AuthShell from '../../components/AuthShell'
import { Button, Field } from '../../components/ui'
import { homeFor } from '../../components/RequireAuth'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'

export default function Login() {
  const { user, login } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (user) return <Navigate to={homeFor(user)} replace />

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const u = await login(email.trim(), password)
      const from = location.state?.from
      // Only return to the previous page if this role is allowed there.
      const allowed = from && (u.role === 'admin' ? from.startsWith('/admin') : !from.startsWith('/admin'))
      navigate(allowed ? from : homeFor(u), { replace: true })
    } catch (err) {
      const msg = errorMessage(err)
      setError(msg)
      toast.error(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Sign in to your account"
      subtitle="Use your college email to continue."
      footer={<>Don't have an account? <Link to="/register" className="text-primary font-medium">Create one</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="email" label="College Email" type="email" autoComplete="email" required
          value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@svkmit.ac.in" />
        <Field id="password" label="Password" type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" error={error} />
        <Button type="submit" className="w-full" size="lg" loading={busy} disabled={!email || !password}>Sign In</Button>
      </form>
    </AuthShell>
  )
}
