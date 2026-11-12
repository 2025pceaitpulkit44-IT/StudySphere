import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, ChevronDown } from 'lucide-react'
import { EmptyState, ProgressBar, SectionHeader, Spinner } from '../../components/ui'
import { QuizReview, TopicPill } from '../../components/student'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { quizService, studentService } from '../../services/studentService'
import { formatDate } from '../../utils/constants'

export default function Progress() {
  const toast = useToast()
  const [topics, setTopics] = useState(null)
  const [attempts, setAttempts] = useState([])
  const [open, setOpen] = useState(null)   // { id, review }
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([studentService.progress(), quizService.attempts()])
      .then(([t, a]) => { setTopics(t); setAttempts(a) }).catch((e) => setError(errorMessage(e)))
  }, [])

  const toggle = async (id) => {
    if (open?.id === id) return setOpen(null)
    try { setOpen({ id, review: (await quizService.review(id)).review }) } catch (e) { toast.error(errorMessage(e)) }
  }

  if (error) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!topics) return <Spinner />

  return (
    <div className="max-w-4xl space-y-8">
      <section>
        <SectionHeader eyebrow="Topics" title="Where you stand" />
        {topics.length === 0 ? (
          <EmptyState icon={BarChart3} title="No progress yet" message="Ask a few doubts or take a quiz and your topics will show up here."
            action={<Link to="/quiz" className="text-primary text-sm font-medium">Take a quiz</Link>} />
        ) : (
          <ul className="grid sm:grid-cols-2 gap-3">
            {topics.map((t) => (
              <li key={`${t.subject_id}-${t.topic}`} className="card-index rounded-lg p-4">
                <div className="flex items-start justify-between gap-2 mb-1"><span className="text-sm font-medium">{t.topic}</span><TopicPill status={t.status} /></div>
                <div className="text-[12px] text-muted mb-2.5">{t.subject}</div>
                {t.avg_score !== null ? <><ProgressBar value={t.avg_score} tone={t.avg_score < 50 ? 'gold' : 'primary'} />
                  <div className="text-[12px] text-muted mt-1.5">Quiz average {t.avg_score}% over {t.quizzes_taken} quiz{t.quizzes_taken === 1 ? '' : 'zes'}</div></>
                  : <div className="text-[12px] text-muted">No quiz yet · {t.doubts_count} doubt{t.doubts_count === 1 ? '' : 's'}</div>}
                <Link to={`/quiz?subject=${t.subject_id}&topic=${encodeURIComponent(t.topic)}`} className="text-[12.5px] text-primary font-medium mt-2 inline-block">Practice this topic</Link>
              </li>
            ))}
          </ul>
        )}
        <p className="text-[12px] text-muted mt-3">Statuses are based only on your quiz scores and the number of doubts you've asked on a topic.</p>
      </section>

      <section>
        <SectionHeader eyebrow="History" title="Past quizzes" />
        {attempts.length === 0 ? <p className="text-sm text-muted">You haven't submitted a quiz yet.</p> : (
          <ul className="space-y-2">
            {attempts.map((a) => (
              <li key={a.id}>
                <button onClick={() => toggle(a.id)} aria-expanded={open?.id === a.id} className="w-full card-index rounded-lg p-4 flex items-center gap-3 text-left hover:border-primary/40">
                  <div className="flex-1"><div className="text-sm font-medium">{a.subject}{a.topic && ` · ${a.topic}`}</div><div className="text-[12px] text-muted">{formatDate(a.submitted_at, true)}</div></div>
                  <div className="font-mono text-sm">{a.score}/{a.total} <span className="text-muted">({a.percent}%)</span></div>
                  <ChevronDown className={`w-4 h-4 text-muted transition-transform ${open?.id === a.id ? 'rotate-180' : ''}`} />
                </button>
                {open?.id === a.id && <div className="mt-2"><QuizReview review={open.review} /></div>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
