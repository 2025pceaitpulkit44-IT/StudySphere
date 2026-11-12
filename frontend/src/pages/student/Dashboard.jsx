import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, BookOpen, FileText, MessageCircleQuestion, Sparkles, Target } from 'lucide-react'
import { Button, EmptyState, Pill, ProgressBar, SectionHeader, Spinner } from '../../components/ui'
import { StatCard, TopicPill } from '../../components/student'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { studentService } from '../../services/studentService'
import { formatDate } from '../../utils/constants'

export default function Dashboard() {
  const toast = useToast()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    studentService.dashboard().then(setData).catch((e) => setError(errorMessage(e)))
  }, [])

  if (error) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!data) return <Spinner />

  const ask = (e) => {
    e.preventDefault()
    if (q.trim().length < 3) return toast.error('Type your question first (at least 3 characters).')
    navigate('/ask', { state: { question: q.trim() } })
  }

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="rounded-lg bg-primary text-white p-6 relative overflow-hidden">
        <div className="absolute inset-0 opacity-[0.07]" style={{ backgroundImage: 'repeating-linear-gradient(to bottom, transparent, transparent 27px, #fff 27px, #fff 28px)' }} />
        <div className="relative">
          <div className="text-[11px] font-mono uppercase tracking-[0.2em] text-gold mb-1.5">Welcome back</div>
          <h2 className="font-display text-2xl font-semibold mb-4">{data.name.replace(/\s*\(demo\)/i, '').split(' ')[0]}, what are you stuck on?</h2>
          <form onSubmit={ask} className="flex gap-2 max-w-2xl">
            <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Ask StudySphere AI" placeholder="e.g. Explain binary search"
              className="flex-1 px-4 py-2.5 rounded-md text-ink text-sm bg-white" />
            <Button type="submit" variant="gold"><Sparkles className="w-4 h-4" /> Ask AI</Button>
          </form>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Doubts asked" value={data.doubts_total} />
        <StatCard label="Quizzes taken" value={data.quizzes_taken} />
        <StatCard label="Average score" value={data.avg_score === null ? '—' : `${data.avg_score}%`} hint={data.avg_score === null ? 'Take a quiz to see this' : undefined} />
        <StatCard label="Activity streak" value={`${data.streak_days} day${data.streak_days === 1 ? '' : 's'}`} hint="Days with a doubt or quiz" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2">
          <SectionHeader eyebrow="History" title="Recent Doubts" action={<Link to="/doubts" className="text-[13px] text-primary font-medium">View all</Link>} />
          {data.recent_doubts.length === 0 ? (
            <EmptyState icon={MessageCircleQuestion} title="No doubts yet" message="Ask StudySphere AI your first question."
              action={<Link to="/ask"><Button>Ask a question</Button></Link>} />
          ) : (
            <ul className="space-y-2">
              {data.recent_doubts.map((d) => (
                <li key={d.id}>
                  <Link to={`/doubts?open=${d.id}`} className="card-index rounded-lg p-4 block hover:border-primary/40 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      {d.subject && <Pill tone="green">{d.subject}</Pill>}
                      {!d.answerable && <Pill tone="open">Not in knowledge base</Pill>}
                      <span className="text-[12px] text-muted ml-auto">{formatDate(d.created_at)}</span>
                    </div>
                    <p className="text-sm font-medium">{d.question}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <SectionHeader eyebrow="Focus" title="Weak Topics" />
          {data.weak_topics.length === 0 ? (
            <EmptyState icon={Target} title="Nothing flagged" message="Take a quiz or ask a few doubts and topics that need work will show up here." />
          ) : (
            <ul className="space-y-2">
              {data.weak_topics.map((t) => (
                <li key={`${t.subject_id}-${t.topic}`} className="card-index rounded-lg p-3.5">
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-sm font-medium">{t.topic}</span><TopicPill status={t.status} />
                  </div>
                  <div className="text-[12px] text-muted mb-2">{t.subject} · {t.doubts_count} doubt{t.doubts_count === 1 ? '' : 's'}</div>
                  {t.avg_score !== null && <ProgressBar value={t.avg_score} tone={t.avg_score < 50 ? 'gold' : 'primary'} />}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section>
        <SectionHeader eyebrow="Suggested" title="Recommended for You" />
        {data.recommended.length === 0 ? (
          <EmptyState icon={FileText} title="No recommendations yet" message="Recommendations appear once material is uploaded or you've practised a topic." />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.recommended.map((r, i) => (
              <Link key={i} to={r.link} className="card-index rounded-lg p-4 hover:border-primary/40 transition-colors flex items-start gap-3">
                {r.kind === 'practice' ? <Target className="w-5 h-5 text-gold-dark mt-0.5" /> : <FileText className="w-5 h-5 text-primary mt-0.5" />}
                <div className="flex-1 min-w-0"><div className="text-sm font-medium">{r.title}</div><div className="text-[12px] text-muted">{r.subtitle}</div></div>
                <ArrowRight className="w-4 h-4 text-muted mt-1" />
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader eyebrow="Library" title="Subjects" action={<Link to="/subjects" className="text-[13px] text-primary font-medium">All subjects</Link>} />
        {data.subjects.length === 0 ? (
          <EmptyState icon={BookOpen} title="No subjects for your department yet" message="Your faculty will add them." />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.subjects.map((s) => (
              <Link key={s.id} to={`/subjects/${s.id}`} className="card-index rounded-lg p-4 hover:border-primary/40 transition-colors">
                <div className="text-[11px] font-mono text-muted">{s.code} · Sem {s.semester}</div>
                <div className="font-display font-semibold mt-0.5 mb-2">{s.name}</div>
                <div className="text-[12.5px] text-muted">{s.material_count} document{s.material_count === 1 ? '' : 's'}{s.avg_score !== null && ` · quiz avg ${s.avg_score}%`}</div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
