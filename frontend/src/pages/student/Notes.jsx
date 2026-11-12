import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { EmptyState, Pill, Spinner } from '../../components/ui'
import { DownloadButton } from '../../components/student'
import { errorMessage } from '../../services/api'
import { subjectService } from '../../services/adminService'
import { studentService } from '../../services/studentService'
import { formatDate } from '../../utils/constants'

export default function Notes() {
  const [docs, setDocs] = useState(null)
  const [subjects, setSubjects] = useState([])
  const [subjectId, setSubjectId] = useState('')
  const [error, setError] = useState('')

  useEffect(() => { subjectService.list().then(setSubjects).catch(() => {}) }, [])
  useEffect(() => {
    setDocs(null)
    studentService.documents(subjectId || undefined).then(setDocs).catch((e) => setError(errorMessage(e)))
  }, [subjectId])

  return (
    <div className="max-w-5xl">
      <select aria-label="Filter by subject" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}
        className="mb-5 px-3 py-2 rounded-md border border-line bg-white text-sm focus:border-primary">
        <option value="">All subjects</option>
        {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      {error ? <p role="alert" className="text-sm text-[#B3472E]">{error}</p> : docs === null ? <Spinner /> : docs.length === 0 ? (
        <EmptyState icon={FileText} title="No material yet" message="Notes uploaded and indexed by your faculty will appear here." />
      ) : (
        <ul className="space-y-2">
          {docs.map((d) => (
            <li key={d.id} className="card-index rounded-lg p-4 flex items-center gap-3">
              <FileText className="w-5 h-5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{d.title}</div>
                <div className="flex flex-wrap items-center gap-1.5 mt-1">
                  <Link to={`/subjects/${d.subject.id}`}><Pill tone="green">{d.subject.name}</Pill></Link>
                  <Pill>{d.material_type}</Pill>{d.unit && <Pill>{d.unit}</Pill>}{d.topic && <Pill>{d.topic}</Pill>}
                  <span className="text-[12px] text-muted ml-1">{formatDate(d.created_at)}</span>
                </div>
              </div>
              <DownloadButton doc={d} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
