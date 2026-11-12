import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FileText, MessageCircleQuestion, Search, Trash2, X } from 'lucide-react'
import { Button, ConfirmDialog, EmptyState, Pill, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { subjectService } from '../../services/adminService'
import { studentService } from '../../services/studentService'
import { formatDate } from '../../utils/constants'

const selectCls = 'px-3 py-2 rounded-md border border-line bg-white text-sm focus:border-primary'

function Detail({ doubt, onClose, onDelete }) {
  return (
    <div className="card-index rounded-lg p-5 fade-up">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-wrap gap-2">
          {doubt.subject && <Pill tone="green">{doubt.subject}</Pill>}
          {doubt.topic && <Pill>{doubt.topic}</Pill>}
          <Pill tone="gold">{doubt.mode.toUpperCase()}</Pill>
          {!doubt.answerable && <Pill tone="open">Not in knowledge base</Pill>}
        </div>
        <button onClick={onClose} aria-label="Close" className="p-1 rounded hover:bg-bg"><X className="w-4 h-4" /></button>
      </div>
      <h3 className="font-display font-semibold text-[16px] mb-1">{doubt.question}</h3>
      <div className="text-[12px] text-muted mb-4">{formatDate(doubt.created_at, true)}</div>
      <p className="text-sm leading-relaxed whitespace-pre-wrap">{doubt.answer}</p>
      {doubt.explanation && <p className="text-sm leading-relaxed whitespace-pre-wrap mt-3 text-ink/85">{doubt.explanation}</p>}
      {doubt.key_points.length > 0 && <ul className="list-disc pl-5 text-sm space-y-1 mt-3">{doubt.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>}
      {doubt.sources.length > 0 && (
        <div className="mt-4 pt-3 border-t border-line">
          <div className="text-[11px] font-mono uppercase tracking-widest text-muted mb-2">Sources</div>
          {doubt.sources.map((s) => (
            <div key={s.document_id} className="flex gap-2 text-sm mb-1.5"><FileText className="w-4 h-4 text-primary mt-0.5" />
              <span>{s.title} <span className="text-muted font-mono text-[12px]">{s.refs.map((n) => `[${n}]`).join(' ')}</span></span></div>
          ))}
        </div>
      )}
      <div className="mt-5"><Button variant="secondary" size="sm" onClick={onDelete}><Trash2 className="w-3.5 h-3.5" /> Delete</Button></div>
    </div>
  )
}

export default function Doubts() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const [rows, setRows] = useState(null)
  const [subjects, setSubjects] = useState([])
  const [q, setQ] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [open, setOpen] = useState(null)
  const [confirm, setConfirm] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { subjectService.list().then(setSubjects).catch(() => {}) }, [])

  const load = useCallback(() => {
    const t = setTimeout(() => {
      studentService.doubts({ q: q.trim() || undefined, subject_id: subjectId || undefined })
        .then((r) => { setRows(r); setError('') }).catch((e) => setError(errorMessage(e)))
    }, 250) // debounce typing
    return () => clearTimeout(t)
  }, [q, subjectId])
  useEffect(load, [load])

  const select = useCallback(async (id) => {
    try { setOpen(await studentService.doubt(id)); setParams({ open: id }, { replace: true }) }
    catch (e) { toast.error(errorMessage(e)) }
  }, [setParams, toast])

  useEffect(() => { const id = params.get('open'); if (id && !open) select(id) }, [params, open, select])

  const remove = async () => {
    try {
      await studentService.deleteDoubt(open.id)
      toast.success('Doubt deleted.')
      setOpen(null); setConfirm(false); setParams({}, { replace: true }); load()
    } catch (e) { toast.error(errorMessage(e)) }
  }

  const filtered = q.trim() || subjectId
  return (
    <div className="max-w-6xl">
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="flex items-center gap-2 px-3 py-2 rounded-md border border-line bg-white flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search your doubts" placeholder="Search your questions…" className="w-full text-sm outline-none" />
        </div>
        <select aria-label="Filter by subject" className={selectCls} value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
          <option value="">All subjects</option>
          {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>

      {error ? <p role="alert" className="text-sm text-[#B3472E]">{error}</p> : rows === null ? <Spinner /> : rows.length === 0 ? (
        <EmptyState icon={MessageCircleQuestion} title={filtered ? 'No doubts match' : 'No doubts yet'}
          message={filtered ? 'Try a different search or subject.' : 'Ask StudySphere AI your first question.'} />
      ) : (
        <div className="grid lg:grid-cols-[1fr_1.1fr] gap-5 items-start">
          <ul className="space-y-2">
            {rows.map((d) => (
              <li key={d.id}>
                <button onClick={() => select(d.id)} className={`w-full text-left card-index rounded-lg p-4 transition-colors ${open?.id === d.id ? 'border-primary' : 'hover:border-primary/40'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    {d.subject && <Pill tone="green">{d.subject}</Pill>}
                    {!d.answerable && <Pill tone="open">Not in knowledge base</Pill>}
                    <span className="text-[12px] text-muted ml-auto">{formatDate(d.created_at)}</span>
                  </div>
                  <p className="text-sm font-medium">{d.question}</p>
                  {d.preview && <p className="text-[13px] text-muted mt-1 line-clamp-2">{d.preview}</p>}
                </button>
              </li>
            ))}
          </ul>
          {open ? <Detail doubt={open} onClose={() => { setOpen(null); setParams({}, { replace: true }) }} onDelete={() => setConfirm(true)} />
            : <div className="hidden lg:block text-sm text-muted p-6 text-center card-index rounded-lg">Select a question to see the full answer and its sources.</div>}
        </div>
      )}
      <ConfirmDialog open={confirm} danger title="Delete this doubt?" message="The question and its saved answer will be removed from your history." confirmLabel="Delete" onConfirm={remove} onCancel={() => setConfirm(false)} />
    </div>
  )
}
