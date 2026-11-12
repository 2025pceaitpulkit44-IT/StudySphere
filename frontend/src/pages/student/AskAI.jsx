import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { BookOpenCheck, FileText, SearchX, Send, Sparkles } from 'lucide-react'
import { Button, Field, Pill } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { subjectService } from '../../services/adminService'
import { aiService } from '../../services/studentService'

const MODES = [
  ['ask', 'Ask', 'Short, direct answer'],
  ['explain', 'Explain', 'Step-by-step explanation'],
  ['solve', 'Solve', 'Worked solution'],
]
const selectCls = 'w-full px-3.5 py-2.5 rounded-md border border-line bg-white text-sm focus:border-primary'
const REL_TONE = { high: 'green', medium: 'gold', low: 'open' }

function Sources({ sources }) {
  return (
    <div className="mt-5 pt-4 border-t border-line">
      <div className="text-[11px] font-mono uppercase tracking-widest text-muted mb-2">Sources from your college material</div>
      <ul className="space-y-2">
        {sources.map((s) => (
          <li key={s.document_id} className="flex gap-2.5 text-sm bg-bg border border-line rounded-md p-3">
            <FileText className="w-4 h-4 mt-0.5 text-primary shrink-0" />
            <div className="min-w-0">
              <div className="font-medium">
                {s.title} <span className="font-mono text-[12px] text-muted">{s.refs.map((n) => `[${n}]`).join(' ')}</span>
                {!s.cited && <span className="ml-2 text-[11.5px] text-muted font-normal">retrieved, not cited</span>}
              </div>
              <div className="text-[12px] text-muted">{[s.subject, s.topic, s.unit, `v${s.version}`].filter(Boolean).join(' · ')}</div>
              <p className="text-[12.5px] text-ink/70 mt-1 line-clamp-2">“{s.snippet}”</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Answer({ item }) {
  const { question, mode, result: r } = item
  return (
    <div className="space-y-3 fade-up">
      <div className="flex justify-end">
        <div className="bg-primary text-white rounded-lg rounded-br-sm px-4 py-2.5 max-w-[85%] text-sm whitespace-pre-wrap">{question}</div>
      </div>
      <div className="card-index rounded-lg p-5">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <Pill tone="green">{mode.toUpperCase()}</Pill>
          {r.answerable && r.relevance && <Pill tone={REL_TONE[r.relevance.level]} >Relevance: {r.relevance.level} ({r.relevance.score})</Pill>}
          {!r.answerable && <Pill tone="open">Not in knowledge base</Pill>}
          {r.saved && <span className="text-[12px] text-muted">Saved to My Doubts</span>}
        </div>

        {!r.answerable ? (
          <div className="flex gap-3 items-start">
            <SearchX className="w-5 h-5 text-muted mt-0.5 shrink-0" />
            <div>
              <p className="text-sm">{r.answer}</p>
              <p className="text-[13px] text-muted mt-1.5">Try a different subject or wording, or ask your faculty to upload material on this topic.</p>
            </div>
          </div>
        ) : (
          <>
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{r.answer}</p>
            {r.explanation && (
              <div className="mt-4">
                <div className="text-[11px] font-mono uppercase tracking-widest text-muted mb-1.5">Explanation</div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-ink/90">{r.explanation}</p>
              </div>
            )}
            {r.key_points.length > 0 && (
              <div className="mt-4">
                <div className="text-[11px] font-mono uppercase tracking-widest text-muted mb-1.5">Key points</div>
                <ul className="list-disc pl-5 text-sm space-y-1">{r.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
              </div>
            )}
            {r.sources.length > 0 && <Sources sources={r.sources} />}
          </>
        )}
      </div>
    </div>
  )
}

export default function AskAI() {
  const toast = useToast()
  const prefill = useLocation().state || {}   // set by Search / Subject pages
  const bottom = useRef(null)
  const [subjects, setSubjects] = useState([])
  const [subjectId, setSubjectId] = useState(prefill.subjectId ? String(prefill.subjectId) : '')
  const [topic, setTopic] = useState(prefill.topic || '')
  const [mode, setMode] = useState('ask')
  const [question, setQuestion] = useState(prefill.question || '')
  const [save, setSave] = useState(true)
  const [busy, setBusy] = useState(false)
  const [items, setItems] = useState([])

  useEffect(() => {
    subjectService.list().then(setSubjects).catch((e) => toast.error(errorMessage(e)))
  }, [toast])

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [items, busy])

  const submit = async (e) => {
    e.preventDefault()
    const q = question.trim()
    if (q.length < 3 || busy) return
    setBusy(true)
    try {
      const result = await aiService.ask(mode, { question: q, subject_id: subjectId ? Number(subjectId) : null, topic: topic.trim(), save })
      setItems((prev) => [...prev, { question: q, mode, result }])
      setQuestion('')
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-5">
      <div className="card-index rounded-lg p-4 grid sm:grid-cols-2 gap-3">
        <Field id="subject" label="Subject">
          <select id="subject" className={selectCls} value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            <option value="">All my subjects</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        <Field id="topic" label="Topic (optional)" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Binary Search" />
      </div>

      <div className="space-y-5 min-h-[200px]">
        {items.length === 0 && !busy && (
          <div className="text-center py-12">
            <Sparkles className="w-8 h-8 text-gold-dark mx-auto mb-3" />
            <h2 className="font-display font-semibold text-lg mb-1">Ask StudySphere AI</h2>
            <p className="text-sm text-muted max-w-md mx-auto">
              Answers come only from the study material your faculty uploaded, with the sources shown. If the material doesn't cover it, I'll tell you.
            </p>
          </div>
        )}
        {items.map((it, i) => <Answer key={i} item={it} />)}
        {busy && (
          <div className="card-index rounded-lg p-4 inline-flex items-center gap-1.5 text-muted text-sm" role="status" aria-label="Searching your college material">
            <BookOpenCheck className="w-4 h-4 mr-1" /> Searching material
            <span className="typing-dot w-1.5 h-1.5 rounded-full bg-muted" /><span className="typing-dot w-1.5 h-1.5 rounded-full bg-muted" /><span className="typing-dot w-1.5 h-1.5 rounded-full bg-muted" />
          </div>
        )}
        <div ref={bottom} />
      </div>

      <form onSubmit={submit} className="card-index rounded-lg p-4 sticky bottom-4">
        <div className="flex gap-1.5 mb-3" role="radiogroup" aria-label="Mode">
          {MODES.map(([k, label, hint]) => (
            <button key={k} type="button" role="radio" aria-checked={mode === k} title={hint} onClick={() => setMode(k)}
              className={`px-3.5 py-1.5 rounded-md text-[13px] font-medium border transition-colors ${mode === k ? 'bg-primary text-white border-primary' : 'bg-white text-ink/75 border-line hover:border-primary/40'}`}>
              {label}
            </button>
          ))}
          <label className="ml-auto flex items-center gap-2 text-[12.5px] text-muted cursor-pointer">
            <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} className="accent-[#244B45]" />
            Save to My Doubts
          </label>
        </div>
        <div className="flex gap-2 items-end">
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} maxLength={2000}
            aria-label="Your question" placeholder={mode === 'solve' ? 'Type the problem to solve…' : 'e.g. Explain binary search'}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e) } }}
            className="flex-1 px-3.5 py-2.5 rounded-md border border-line bg-white text-sm resize-none focus:border-primary" />
          <Button type="submit" loading={busy} disabled={question.trim().length < 3} aria-label="Send"><Send className="w-4 h-4" /></Button>
        </div>
      </form>
    </div>
  )
}
