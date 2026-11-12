import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import AuthShell from '../../components/AuthShell'
import { Button, Field } from '../../components/ui'
import { homeFor } from '../../components/RequireAuth'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'

const DEPARTMENTS = [
  'Computer Science & Engineering',
  'Information Technology',
  'Electronics & Telecommunication',
  'Mechanical Engineering',
  'Civil Engineering',
]

const selectCls = 'w-full px-3.5 py-2.5 rounded-md border border-line bg-white text-sm focus:border-primary'

export default function Register() {
  const { user, register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', department: DEPARTMENTS[0], year: 2 })
  const [showInvite, setShowInvite] = useState(false)
  const [invite, setInvite] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (user) return <Navigate to={homeFor(user)} replace />

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const payload = { ...form, year: Number(form.year), email: form.email.trim(), name: form.name.trim() }
      if (showInvite && invite.trim()) payload.admin_invite_code = invite.trim()
      const u = await register(payload)
      toast.success(`Welcome to StudySphere, ${u.name.split(' ')[0]}!`)
      navigate(homeFor(u), { replace: true })
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
      title="Create your account"
      subtitle="Register with your college email."
      footer={<>Already registered? <Link to="/login" className="text-primary font-medium">Sign in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="name" label="Full name" autoComplete="name" required value={form.name} onChange={set('name')} />
        <Field id="email" label="College Email" type="email" autoComplete="email" required value={form.email} onChange={set('email')} placeholder="name@svkmit.ac.in" />
        <Field id="password" label="Password" type="password" autoComplete="new-password" required
          value={form.password} onChange={set('password')} hint="At least 8 characters, with a letter and a number." />
        <Field id="department" label="Department">
          <select id="department" className={selectCls} value={form.department} onChange={set('department')}>
            {DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}
          </select>
        </Field>
        <Field id="year" label="Year">
          <select id="year" className={selectCls} value={form.year} onChange={set('year')}>
            {[1, 2, 3, 4].map((y) => <option key={y} value={y}>Year {y}</option>)}
          </select>
        </Field>

        {showInvite ? (
          <Field id="invite" label="Faculty invitation code" hint="Only for faculty/admin accounts. Students leave this empty."
            value={invite} onChange={(e) => setInvite(e.target.value)} autoComplete="off" />
        ) : (
          <button type="button" onClick={() => setShowInvite(true)} className="text-[13px] text-primary font-medium">
            I have a faculty invitation code
          </button>
        )}

        {error && <p role="alert" className="text-[13px] text-[#B3472E]">{error}</p>}
        <Button type="submit" className="w-full" size="lg" loading={busy}
          disabled={!form.name || !form.email || !form.password}>Create account</Button>
      </form>
    </AuthShell>
  )
}
