import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'
import { EmptyState, ProgressBar, Spinner } from '../../components/ui'
import { errorMessage } from '../../services/api'
import { studentService } from '../../services/studentService'

export default function Subjects() {
  const [subjects, setSubjects] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { studentService.overview().then(setSubjects).catch((e) => setError(errorMessage(e))) }, [])

  if (error) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!subjects) return <Spinner />
  if (subjects.length === 0) return <EmptyState icon={BookOpen} title="No subjects yet" message="No subjects are set up for your department yet." />
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 max-w-6xl">
      {subjects.map((s) => (
        <Link key={s.id} to={`/subjects/${s.id}`} className="card-index rounded-lg p-5 hover:border-primary/40 transition-colors">
          <div className="text-[11px] font-mono text-muted">{s.code} · Semester {s.semester}</div>
          <h3 className="font-display font-semibold text-[17px] mt-1 mb-3">{s.name}</h3>
          <dl className="text-[13px] text-muted space-y-1 mb-3">
            <div className="flex justify-between"><dt>Study material</dt><dd className="text-ink font-medium">{s.material_count}</dd></div>
            <div className="flex justify-between"><dt>Your doubts</dt><dd className="text-ink font-medium">{s.doubts_count}</dd></div>
            <div className="flex justify-between"><dt>Quiz average</dt><dd className="text-ink font-medium">{s.avg_score === null ? '—' : `${s.avg_score}%`}</dd></div>
          </dl>
          {s.avg_score !== null && <ProgressBar value={s.avg_score} />}
        </Link>
      ))}
    </div>
  )
}
