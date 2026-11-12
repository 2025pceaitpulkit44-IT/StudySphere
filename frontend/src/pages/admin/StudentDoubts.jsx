import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Lock, SearchX } from 'lucide-react'
import { Button, EmptyState, Pill, SectionHeader, Spinner } from '../../components/ui'
import { StatCard } from '../../components/student'
import { errorMessage } from '../../services/api'
import { adminService } from '../../services/adminService'
import { formatDate } from '../../utils/constants'

export default function StudentDoubts() {
  const [days, setDays] = useState(30)
  const [d, setD] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setD(null); setError('')
    adminService.doubts(days).then(setD).catch((e) => setError(errorMessage(e)))
  }, [days])

  return (
    <div className="max-w-6xl space-y-8">
      <div className="flex flex-wrap items-center gap-3 justify-between">
        <p className="text-[13px] text-muted flex items-center gap-1.5"><Lock className="w-3.5 h-3.5" /> Anonymised: no names, emails or IDs are shown, and a concept appears only when several students asked about it.</p>
        <select aria-label="Time range" value={days} onChange={(e) => setDays(Number(e.target.value))} className="px-3 py-2 rounded-md border border-line bg-white text-sm focus:border-primary">
          {[7, 30, 90].map((n) => <option key={n} value={n}>Last {n} days</option>)}
        </select>
      </div>

      {error ? <p role="alert" className="text-sm text-[#B3472E]">{error}</p> : !d ? <Spinner /> : d.total_questions === 0 ? (
        <EmptyState title="No student questions in this period" message="Questions will appear here once students start using Ask StudySphere AI." />
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            <StatCard label="Questions asked" value={d.total_questions} />
            <StatCard label="Not in knowledge base" value={d.unanswered} />
            <StatCard label="Answer rate" value={d.answer_rate === null ? '—' : `${d.answer_rate}%`} hint="Questions the material could answer" />
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <section>
              <SectionHeader eyebrow="By subject" title="Questions per subject" />
              <div className="card-index rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="text-left text-[11.5px] font-mono uppercase tracking-wider text-muted border-b border-line"><tr><th className="px-4 py-2.5 font-medium">Subject</th><th className="px-4 py-2.5 font-medium text-right">Questions</th><th className="px-4 py-2.5 font-medium text-right">Unanswered</th></tr></thead>
                  <tbody className="divide-y divide-line">{d.by_subject.map((s) => (
                    <tr key={s.subject}><td className="px-4 py-2.5">{s.subject}</td><td className="px-4 py-2.5 text-right font-mono">{s.count}</td><td className="px-4 py-2.5 text-right font-mono">{s.unanswered}</td></tr>))}</tbody>
                </table>
              </div>
            </section>
            <section>
              <SectionHeader eyebrow="Topics" title="Most asked topics" />
              {d.top_topics.length === 0 ? <p className="text-sm text-muted">Students haven't tagged topics yet.</p> : (
                <ul className="space-y-2">{d.top_topics.map((t, i) => (
                  <li key={i} className="card-index rounded-lg px-4 py-2.5 flex items-center justify-between text-sm"><span>{t.topic} <span className="text-muted text-[12px]">· {t.subject}</span></span><span className="font-mono">{t.count}</span></li>))}</ul>
              )}
            </section>
          </div>

          <section>
            <SectionHeader eyebrow="Patterns" title="Frequently asked concepts" />
            {d.frequent_concepts.length === 0 ? (
              <p className="text-sm text-muted">Nothing yet. A concept is listed once at least {d.min_students_for_concepts} different students ask about it.</p>
            ) : (
              <div className="flex flex-wrap gap-2">{d.frequent_concepts.map((c) => (
                <Pill key={c.term} tone="green" className="!text-[13px] !px-3 !py-1.5">{c.term} <span className="font-mono opacity-70">· {c.students} students</span></Pill>))}</div>
            )}
          </section>

          <section>
            <SectionHeader eyebrow="Gaps" title="Unanswered questions" action={<Link to="/admin/upload"><Button size="sm">Upload material</Button></Link>} />
            {d.unanswered_questions.length === 0 ? (
              <EmptyState icon={SearchX} title="No gaps found" message="Every question in this period could be answered from the knowledge base." />
            ) : (
              <>
                <p className="text-[13px] text-muted mb-3">The knowledge base had nothing relevant for these. Uploading material on them would help students.</p>
                <ul className="space-y-2">{d.unanswered_questions.map((q, i) => (
                  <li key={i} className="card-index rounded-lg p-4">
                    <p className="text-sm font-medium">{q.question}</p>
                    <div className="flex flex-wrap items-center gap-1.5 mt-1.5"><Pill tone="green">{q.subject}</Pill>{q.topic && <Pill>{q.topic}</Pill>}
                      <Pill tone="open">asked {q.times_asked}×</Pill><span className="text-[12px] text-muted">last {formatDate(q.last_asked)}</span></div>
                  </li>))}</ul>
              </>
            )}
          </section>
        </>
      )}
    </div>
  )
}
