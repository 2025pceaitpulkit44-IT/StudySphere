import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ClipboardCheck, FileText, Sparkles } from 'lucide-react'
import { Button, Pill, SectionHeader, Spinner } from '../../components/ui'
import { DownloadButton } from '../../components/student'
import { errorMessage } from '../../services/api'
import { subjectService } from '../../services/adminService'
import { studentService } from '../../services/studentService'

export default function SubjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [subject, setSubject] = useState(null)
  const [docs, setDocs] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([subjectService.get(id), studentService.documents(id)])
      .then(([s, d]) => { setSubject(s); setDocs(d) }).catch((e) => setError(errorMessage(e)))
  }, [id])

  if (error) return <div><p role="alert" className="text-sm text-[#B3472E] mb-3">{error}</p><Link to="/subjects" className="text-primary text-sm">Back to subjects</Link></div>
  if (!subject || !docs) return <Spinner />

  const units = Array.from({ length: subject.units }, (_, i) => `Unit ${i + 1}`)
  const known = new Set(units)
  const byUnit = (u) => docs.filter((d) => d.unit === u)
  const other = docs.filter((d) => !known.has(d.unit))

  const Section = ({ title, items }) => (
    <section className="mb-6">
      <SectionHeader title={title} eyebrow={`${items.length} document${items.length === 1 ? '' : 's'}`} />
      {items.length === 0 ? <p className="text-sm text-muted">No material uploaded for this unit yet.</p> : (
        <ul className="space-y-2">
          {items.map((d) => (
            <li key={d.id} className="card-index rounded-lg p-4 flex items-center gap-3">
              <FileText className="w-5 h-5 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{d.title}</div>
                <div className="flex flex-wrap gap-1.5 mt-1"><Pill>{d.material_type}</Pill>{d.topic && <Pill tone="green">{d.topic}</Pill>}<Pill>v{d.version}</Pill></div>
              </div>
              <DownloadButton doc={d} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <div className="text-[11px] font-mono text-muted">{subject.code} · Semester {subject.semester}</div>
        <h2 className="font-display text-2xl font-semibold mb-3">{subject.name}</h2>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => navigate('/ask', { state: { subjectId: subject.id } })}><Sparkles className="w-4 h-4" /> Ask about this subject</Button>
          <Button size="sm" variant="secondary" onClick={() => navigate(`/quiz?subject=${subject.id}`)}><ClipboardCheck className="w-4 h-4" /> Practice quiz</Button>
        </div>
      </div>
      {units.map((u) => <Section key={u} title={u} items={byUnit(u)} />)}
      {other.length > 0 && <Section title="General material" items={other} />}
    </div>
  )
}
