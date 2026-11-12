import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { Button, Field, SectionHeader, Spinner } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { undertakingService } from '../../services/adminService'

const AUTH_OPTIONS = [
  ['owner', 'I own / represent the copyright in the material.'],
  ['permission', 'I have permission / authorization from the copyright holder.'],
]

export default function Undertaking() {
  const { user } = useAuth()
  const toast = useToast()
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({
    institution: 'SVKM Institute of Technology', faculty_name: user.name.replace(/\s*\(demo\)/i, ''),
    designation: user.designation || '', email: user.email, department: user.department || '',
    authorization_type: '', accepted: false,
  })

  useEffect(() => {
    undertakingService.status().then(setStatus).catch((e) => setError(errorMessage(e)))
  }, [])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      setStatus(await undertakingService.submit(form))
      setEditing(false)
      toast.success('Undertaking recorded. You can now upload academic material.')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!status) return <Spinner />

  if (status.completed && !editing) {
    const r = status.record
    return (
      <div className="max-w-2xl">
        <SectionHeader eyebrow="Copyright" title="Undertaking completed" />
        <div className="card-index rounded-lg p-5">
          <div className="flex items-center gap-2 text-primary font-medium mb-4">
            <CheckCircle2 className="w-5 h-5" /> Accepted on {new Date(r.accepted_at).toLocaleString()}
          </div>
          <dl className="text-sm space-y-2 mb-5">
            {[['Institution', r.institution], ['Name', r.faculty_name], ['Designation', r.designation],
              ['Official email', r.email], ['Department', r.department],
              ['Authorization', r.authorization_type === 'owner' ? 'Owner / representative of the copyright holder' : 'Permission from the copyright holder'],
            ].map(([k, v]) => (
              <div key={k} className="flex"><dt className="w-36 text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>
            ))}
          </dl>
          <div className="flex gap-2">
            <Link to="/admin/upload"><Button>Upload Academic Material</Button></Link>
            <Button variant="secondary" onClick={() => setEditing(true)}>Submit a new undertaking</Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <SectionHeader eyebrow="Copyright" title="Copyright & Study-Purpose Undertaking" />
      <p className="text-sm text-muted mb-5">Complete this once before uploading. Your acceptance is recorded with a timestamp.</p>
      <form onSubmit={submit} className="card-index rounded-lg p-5 space-y-4" noValidate>
        <Field id="institution" label="Institution / College" required value={form.institution} onChange={set('institution')} />
        <div className="grid sm:grid-cols-2 gap-4">
          <Field id="faculty_name" label="Admin / Faculty name" required value={form.faculty_name} onChange={set('faculty_name')} />
          <Field id="designation" label="Designation" required value={form.designation} onChange={set('designation')} placeholder="e.g. Assistant Professor" />
          <Field id="email" label="Official email" type="email" required value={form.email} onChange={set('email')} />
          <Field id="department" label="Department" required value={form.department} onChange={set('department')} />
        </div>

        <fieldset>
          <legend className="text-[13px] font-medium mb-2">Authorization</legend>
          {AUTH_OPTIONS.map(([v, label]) => (
            <label key={v} className="flex items-start gap-2.5 text-sm mb-2 cursor-pointer">
              <input type="radio" name="auth" value={v} checked={form.authorization_type === v}
                onChange={set('authorization_type')} className="mt-1 accent-[#244B45]" />
              {label}
            </label>
          ))}
        </fieldset>

        <div className="bg-bg border border-line rounded-md p-4 text-[13.5px] leading-relaxed">{status.declaration}</div>

        <label className="flex items-start gap-2.5 text-sm cursor-pointer">
          <input type="checkbox" checked={form.accepted} onChange={(e) => setForm({ ...form, accepted: e.target.checked })}
            className="mt-1 accent-[#244B45]" />
          I have read and accept this copyright and study-purpose undertaking.
        </label>

        <div className="flex gap-2">
          <Button type="submit" loading={busy}
            disabled={!form.accepted || !form.authorization_type || !form.institution || !form.faculty_name || !form.designation || !form.email || !form.department}>
            Accept & submit
          </Button>
          {editing && <Button type="button" variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>}
        </div>
      </form>
    </div>
  )
}
