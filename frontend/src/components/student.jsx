import { useState } from 'react'
import { CheckCircle2, Download, XCircle } from 'lucide-react'
import { Button, Pill } from './ui'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import { downloadDocument } from '../services/studentService'
import { TOPIC_STATUS } from '../utils/constants'

export function TopicPill({ status }) {
  const [label, tone] = TOPIC_STATUS[status] || TOPIC_STATUS.new
  return <Pill tone={tone}>{label}</Pill>
}

export function StatCard({ label, value, hint }) {
  return (
    <div className="card-index rounded-lg p-4">
      <div className="text-[11px] font-mono uppercase tracking-widest text-muted">{label}</div>
      <div className="font-display text-2xl font-semibold mt-1">{value}</div>
      {hint && <div className="text-[12px] text-muted mt-0.5">{hint}</div>}
    </div>
  )
}

export function DownloadButton({ doc, size = 'sm' }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const go = async () => {
    setBusy(true)
    try { await downloadDocument(doc) } catch (e) { toast.error(errorMessage(e, 'Download failed.')) } finally { setBusy(false) }
  }
  return <Button variant="secondary" size={size} loading={busy} onClick={go} aria-label={`Download ${doc.title}`}><Download className="w-3.5 h-3.5" /> Download</Button>
}

/** Question-by-question review used after a quiz and when reopening past attempts. */
export function QuizReview({ review }) {
  return (
    <ol className="space-y-4">
      {review.map((r, i) => (
        <li key={i} className="card-index rounded-lg p-4">
          <div className="flex gap-2 items-start mb-2.5">
            {r.correct ? <CheckCircle2 className="w-4.5 h-4.5 mt-0.5 text-primary shrink-0" /> : <XCircle className="w-4.5 h-4.5 mt-0.5 text-[#B3472E] shrink-0" />}
            <p className="text-sm font-medium">{i + 1}. {r.question}</p>
          </div>
          <ul className="space-y-1.5 ml-6">
            {r.options.map((o, j) => {
              const isCorrect = j === r.correct_index
              const chosenWrong = j === r.chosen_index && !isCorrect
              return (
                <li key={j} className={`text-sm px-3 py-1.5 rounded-md border ${isCorrect ? 'border-primary/40 bg-primary/8' : chosenWrong ? 'border-[#E9C3B9] bg-[#F7E4DF]' : 'border-line'}`}>
                  {o}{isCorrect && <span className="text-[11px] text-primary font-medium ml-2">correct</span>}
                  {chosenWrong && <span className="text-[11px] text-[#8f3722] font-medium ml-2">your answer</span>}
                </li>
              )
            })}
          </ul>
          {r.chosen_index === null && <p className="ml-6 mt-1.5 text-[12px] text-muted">Not answered</p>}
          {r.explanation && <p className="ml-6 mt-2.5 text-[13px] text-ink/80">{r.explanation}{r.source && <span className="text-muted"> — from “{r.source}”</span>}</p>}
        </li>
      ))}
    </ol>
  )
}
