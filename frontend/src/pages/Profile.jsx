import { SectionHeader } from '../components/ui'
import { useAuth } from '../context/AuthContext'

export default function Profile() {
  const { user } = useAuth()
  const rows = [
    ['Name', user.name],
    ['Email', user.email],
    ['Role', user.role === 'admin' ? 'Faculty / Admin' : 'Student'],
    ['Department', user.department],
    user.role === 'student' && ['Year', user.year && `Year ${user.year}`],
    user.role === 'student' && ['Semester', user.semester],
    user.role === 'admin' && ['Designation', user.designation || 'Not set'],
  ].filter(Boolean)

  return (
    <div className="max-w-2xl">
      <SectionHeader eyebrow="Account" title="Your profile" />
      <dl className="card-index rounded-lg divide-y divide-line">
        {rows.map(([k, v]) => (
          <div key={k} className="flex px-5 py-3.5 text-sm">
            <dt className="w-36 text-muted">{k}</dt>
            <dd className="font-medium">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
