import { useEffect, useState } from 'react'
import { Spinner } from '../../components/ui'
import { StatCard } from '../../components/student'
import { ChartCard, DayBars, DayLine, RankBars } from '../../components/charts'
import { errorMessage } from '../../services/api'
import { adminService } from '../../services/adminService'

const hasData = (series) => series.some((p) => p.value > 0)

export default function Analytics() {
  const [days, setDays] = useState(30)
  const [a, setA] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setA(null); setError('')
    adminService.analytics(days).then(setA).catch((e) => setError(errorMessage(e)))
  }, [days])

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex justify-end">
        <select aria-label="Time range" value={days} onChange={(e) => setDays(Number(e.target.value))} className="px-3 py-2 rounded-md border border-line bg-white text-sm focus:border-primary">
          {[7, 30, 90].map((n) => <option key={n} value={n}>Last {n} days</option>)}
        </select>
      </div>
      {error ? <p role="alert" className="text-sm text-[#B3472E]">{error}</p> : !a ? <Spinner /> : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard label="Active students" value={a.active_students} hint="Signed in, asked or took a quiz" />
            <StatCard label="Doubts asked" value={a.total_doubts} />
            <StatCard label="Quizzes taken" value={a.quiz_attempts} />
            <StatCard label="Avg quiz score" value={a.quiz_avg_percent === null ? '—' : `${a.quiz_avg_percent}%`} />
          </div>
          <div className="grid lg:grid-cols-2 gap-5">
            <ChartCard title="Doubts per day" empty={!hasData(a.doubts_per_day)}><DayLine data={a.doubts_per_day} /></ChartCard>
            <ChartCard title="Upload activity" subtitle="Documents uploaded per day" empty={!hasData(a.uploads_per_day)}><DayBars data={a.uploads_per_day} /></ChartCard>
            <ChartCard title="Knowledge base growth" subtitle="Total documents over time" empty={a.kb_growth.at(-1)?.value === 0}><DayLine data={a.kb_growth} color="#D9A441" /></ChartCard>
            <ChartCard title="Most asked subjects" empty={a.top_subjects.length === 0}><RankBars data={a.top_subjects} /></ChartCard>
            <ChartCard title="Most asked topics" empty={a.top_topics.length === 0}><RankBars data={a.top_topics} color="#D9A441" /></ChartCard>
            <ChartCard title="Quiz performance by subject" subtitle="Average score (%)" empty={a.quiz_by_subject.length === 0}>
              <RankBars data={a.quiz_by_subject} dataKey="avg_percent" nameKey="subject" max={100} />
            </ChartCard>
          </div>
        </>
      )}
    </div>
  )
}
