import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ClipboardCheck } from 'lucide-react'
import { Button, Field, ProgressBar, SectionHeader } from '../../components/ui'
import { QuizReview } from '../../components/student'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { subjectService } from '../../services/adminService'
import { quizService } from '../../services/studentService'

const selectCls = 'w-full px-3.5 py-2.5 rounded-md border border-line bg-white text-sm focus:border-primary'

export default function Quiz() {
  const toast = useToast()
  const [params] = useSearchParams()
  const [subjects, setSubjects] = useState([])
  const [subjectId, setSubjectId] = useState(params.get('subject') || '')
  const [topic, setTopic] = useState(params.get('topic') || '')
  const [count, setCount] = useState(5)
  const [quiz, setQuiz] = useState(null)       // active quiz (no answers inside)
  const [chosen, setChosen] = useState({})     // question id -> option index
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { subjectService.list().then(setSubjects).catch((e) => toast.error(errorMessage(e))) }, [toast])

  const start = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      setQuiz(await quizService.start({ subject_id: Number(subjectId), topic: topic.trim(), num_questions: Number(count) }))
      setChosen({}); setResult(null)
    } catch (err) { toast.error(errorMessage(err)) } finally { setBusy(false) }
  }

  const submit = async () => {
    setBusy(true)
    try {
      const answers = quiz.questions.map((q) => ({ question_id: q.id, chosen_index: chosen[q.id] ?? null }))
      setResult(await quizService.submit({ attempt_id: quiz.attempt_id, answers }))
      setQuiz(null)
    } catch (err) { toast.error(errorMessage(err)) } finally { setBusy(false) }
  }

  if (result) {
    return (
      <div className="max-w-3xl">
        <div className="card-index rounded-lg p-6 mb-5 text-center">
          <div className="text-[11px] font-mono uppercase tracking-widest text-muted mb-1">{result.subject}{result.topic && ` · ${result.topic}`}</div>
          <div className="font-display text-4xl font-semibold">{result.score}<span className="text-muted text-2xl"> / {result.total}</span></div>
          <div className="text-sm text-muted mt-1">{result.percent}%</div>
          <div className="max-w-xs mx-auto mt-3"><ProgressBar value={result.percent} /></div>
          <div className="flex justify-center gap-2 mt-5">
            <Button onClick={() => setResult(null)}>New quiz</Button>
          </div>
        </div>
        <SectionHeader eyebrow="Review" title="Your answers" />
        <QuizReview review={result.review} />
      </div>
    )
  }

  if (quiz) {
    const answered = Object.keys(chosen).length
    return (
      <div className="max-w-3xl">
        <SectionHeader eyebrow={quiz.subject} title={quiz.topic ? `Quiz: ${quiz.topic}` : 'Practice quiz'}
          action={<span className="text-[13px] text-muted font-mono">{answered}/{quiz.questions.length} answered</span>} />
        <ol className="space-y-4">
          {quiz.questions.map((q, i) => (
            <li key={q.id} className="card-index rounded-lg p-4">
              <fieldset>
                <legend className="text-sm font-medium mb-3">{i + 1}. {q.question}</legend>
                <div className="space-y-1.5">
                  {q.options.map((o, j) => (
                    <label key={j} className={`flex items-start gap-2.5 text-sm px-3 py-2 rounded-md border cursor-pointer transition-colors ${chosen[q.id] === j ? 'border-primary bg-primary/8' : 'border-line hover:border-primary/40'}`}>
                      <input type="radio" name={`q${q.id}`} checked={chosen[q.id] === j} onChange={() => setChosen({ ...chosen, [q.id]: j })} className="mt-0.5 accent-[#244B45]" />
                      {o}
                    </label>
                  ))}
                </div>
              </fieldset>
            </li>
          ))}
        </ol>
        <div className="flex gap-2 mt-5">
          <Button onClick={submit} loading={busy}>Submit quiz</Button>
          <Button variant="secondary" onClick={() => setQuiz(null)} disabled={busy}>Abandon</Button>
        </div>
        {answered < quiz.questions.length && <p className="text-[12.5px] text-muted mt-2">Unanswered questions count as incorrect.</p>}
      </div>
    )
  }

  return (
    <div className="max-w-xl">
      <SectionHeader eyebrow="Practice" title="Start a quiz" />
      <form onSubmit={start} className="card-index rounded-lg p-5 space-y-4">
        <p className="text-sm text-muted">Questions are generated only from the study material your faculty uploaded.</p>
        <Field id="subject" label="Subject">
          <select id="subject" className={selectCls} value={subjectId} onChange={(e) => setSubjectId(e.target.value)} required>
            <option value="">Select a subject…</option>
            {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        <Field id="topic" label="Topic (optional)" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Binary Search" hint="Leave empty for a mix from the whole subject." />
        <Field id="count" label="Number of questions">
          <select id="count" className={selectCls} value={count} onChange={(e) => setCount(e.target.value)}>
            {[3, 5, 8, 10].map((n) => <option key={n}>{n}</option>)}
          </select>
        </Field>
        <Button type="submit" loading={busy} disabled={!subjectId}><ClipboardCheck className="w-4 h-4" /> {busy ? 'Building your quiz…' : 'Start quiz'}</Button>
      </form>
    </div>
  )
}
