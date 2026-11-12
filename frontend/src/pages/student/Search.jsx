import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { FileText, Search as SearchIcon, Sparkles } from 'lucide-react'
import { Button, EmptyState, Pill, SectionHeader, Spinner } from '../../components/ui'
import { DownloadButton } from '../../components/student'
import { errorMessage } from '../../services/api'
import { studentService } from '../../services/studentService'

export default function Search() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const q = (params.get('q') || '').trim()
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (q.length < 2) return setRes(null)
    setRes(null); setError('')
    studentService.search(q).then(setRes).catch((e) => setError(errorMessage(e)))
  }, [q])

  if (q.length < 2) return <EmptyState icon={SearchIcon} title="Search your college material" message="Use the search box above to look up a concept, topic or subject." />
  if (error) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!res) return <Spinner label="Searching…" />

  const nothing = !res.documents.length && !res.subjects.length && !res.topics.length
  return (
    <div className="max-w-4xl space-y-7">
      <div className="card-index rounded-lg p-4 flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-gold-dark shrink-0" />
        <div className="flex-1 text-sm">Want an explanation of <b>“{q}”</b> instead of a list of notes?</div>
        <Button size="sm" onClick={() => navigate('/ask', { state: { question: `Explain ${q}` } })}>Ask StudySphere AI</Button>
      </div>
      {!res.semantic && <p className="text-[13px] text-muted">Smart search is unavailable right now; showing title and topic matches only.</p>}

      {nothing && <EmptyState icon={SearchIcon} title={`Nothing found for “${q}”`} message="Try different words, or ask StudySphere AI." />}

      {res.subjects.length > 0 && (
        <section><SectionHeader title="Subjects" />
          <div className="flex flex-wrap gap-2">{res.subjects.map((s) => <Link key={s.id} to={`/subjects/${s.id}`}><Pill tone="green" className="!text-[13px] !px-3 !py-1">{s.name}</Pill></Link>)}</div></section>
      )}
      {res.topics.length > 0 && (
        <section><SectionHeader title="Topics" />
          <div className="flex flex-wrap gap-2">{res.topics.map((t, i) => (
            <Link key={i} to={`/subjects/${t.subject_id}`}><Pill className="!text-[13px] !px-3 !py-1">{t.topic} · {t.subject}</Pill></Link>))}</div></section>
      )}
      {res.documents.length > 0 && (
        <section><SectionHeader title="Notes & documents" eyebrow={`${res.documents.length} result${res.documents.length === 1 ? '' : 's'}`} />
          <ul className="space-y-2">
            {res.documents.map((d) => (
              <li key={d.document_id} className="card-index rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-primary mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium">{d.title}</div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      <Link to={`/subjects/${d.subject_id}`}><Pill tone="green">{d.subject}</Pill></Link>
                      {d.topic && <Pill>{d.topic}</Pill>}{d.unit && <Pill>{d.unit}</Pill>}
                      {d.score !== null && <Pill tone="gold">match {Math.round(d.score * 100)}%</Pill>}
                    </div>
                    {d.snippet && <p className="text-[13px] text-ink/70 mt-2 line-clamp-2">“{d.snippet}”</p>}
                  </div>
                  <DownloadButton doc={d} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
