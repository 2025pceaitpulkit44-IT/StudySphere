import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Circle, Loader2, ShieldAlert, XCircle } from 'lucide-react'
import { Button, EmptyState, Field, ProgressBar, SectionHeader, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { documentService, subjectService, undertakingService } from '../../services/adminService'
import { ACCEPTED_EXTENSIONS, MATERIAL_TYPES, STAGES, UNITS, currentAcademicYear, formatBytes } from '../../utils/constants'

const selectCls = 'w-full px-3.5 py-2.5 rounded-md border border-line bg-white text-sm focus:border-primary'

function Tracker({ doc }) {
  const failed = doc.status === 'failed'
  const complete = doc.status === 'indexed'
  const idx = Math.max(STAGES.findIndex(([k]) => k === doc.stage), 0)
  return (
    <div className="card-index rounded-lg p-5">
      <div className="font-medium text-sm mb-1">{doc.title} <span className="text-muted font-normal">· version {doc.version}</span></div>
      <ol className="mt-4 space-y-2.5">
        {STAGES.map(([key, label], i) => {
          const done = complete || i < idx
          const active = !complete && !failed && i === idx
          const bad = failed && i === idx
          return (
            <li key={key} className={`flex items-center gap-2.5 text-sm ${done || active ? 'text-ink' : 'text-muted'}`}>
              {done ? <CheckCircle2 className="w-4 h-4 text-primary" />
                : active ? <Loader2 className="w-4 h-4 animate-spin text-gold-dark" />
                : bad ? <XCircle className="w-4 h-4 text-[#B3472E]" /> : <Circle className="w-4 h-4" />}
              {label}
            </li>
          )
        })}
      </ol>
      {failed && <p role="alert" className="mt-4 text-sm text-[#B3472E]">{doc.error_message}</p>}
      {complete && (
        <p className="mt-4 text-sm text-ink bg-bg border border-line rounded-md p-3">
          Knowledge Base Updated — <b>{doc.chunk_count}</b> passages are now searchable by StudySphere AI.
        </p>
      )}
    </div>
  )
}

export default function Upload() {
  const toast = useToast()
  const fileRef = useRef(null)
  const [ready, setReady] = useState(null) // null = loading, true/false
  const [subjects, setSubjects] = useState([])
  const [form, setForm] = useState({
    subject_id: '', semester: 3, department: '', academic_year: currentAcademicYear(),
    material_type: MATERIAL_TYPES[0], topic: '', unit: '', title: '',
  })
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(null)
  const [busy, setBusy] = useState(false)
  const [doc, setDoc] = useState(null)

  useEffect(() => {
    Promise.all([undertakingService.status(), subjectService.list()])
      .then(([u, s]) => { setReady(u.completed); setSubjects(s) })
      .catch((e) => { toast.error(errorMessage(e)); setReady(false) })
  }, [toast])

  // Poll real pipeline status until the document settles.
  useEffect(() => {
    if (!doc || ['indexed', 'failed'].includes(doc.status)) return
    const t = setInterval(() => documentService.get(doc.id).then(setDoc).catch(() => {}), 1500)
    return () => clearInterval(t)
  }, [doc])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const pickSubject = (e) => {
    const s = subjects.find((x) => String(x.id) === e.target.value)
    setForm({ ...form, subject_id: e.target.value, ...(s && { semester: s.semester, department: s.department }) })
  }

  const submit = async (e) => {
    e.preventDefault()
    const fd = new FormData()
    Object.entries(form).forEach(([k, v]) => fd.append(k, v))
    fd.append('file', file)
    setBusy(true); setProgress(0); setDoc(null)
    try {
      setDoc(await documentService.upload(fd, setProgress))
      toast.success('File uploaded. Processing has started.')
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setBusy(false); setProgress(null)
    }
  }

  if (ready === null) return <Spinner />
  if (!ready) {
    return (
      <EmptyState icon={ShieldAlert} title="Copyright undertaking required"
        message="Before uploading academic material you must confirm you have the right to share it."
        action={<Link to="/admin/undertaking"><Button>Complete Undertaking</Button></Link>} />
    )
  }

  return (
    <div className="grid lg:grid-cols-[1fr_340px] gap-6 max-w-5xl">
      <div>
        <SectionHeader eyebrow="Knowledge base" title="Upload Academic Material" />
        <form onSubmit={submit} className="card-index rounded-lg p-5 space-y-4" noValidate>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field id="subject" label="Subject">
              <select id="subject" className={selectCls} value={form.subject_id} onChange={pickSubject} required>
                <option value="">Select a subject…</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
              </select>
            </Field>
            <Field id="material_type" label="Material type">
              <select id="material_type" className={selectCls} value={form.material_type} onChange={set('material_type')}>
                {MATERIAL_TYPES.map((m) => <option key={m}>{m}</option>)}
              </select>
            </Field>
            <Field id="department" label="Department" required value={form.department} onChange={set('department')} />
            <Field id="semester" label="Semester">
              <select id="semester" className={selectCls} value={form.semester} onChange={set('semester')}>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => <option key={n} value={n}>Semester {n}</option>)}
              </select>
            </Field>
            <Field id="academic_year" label="Academic year" required value={form.academic_year} onChange={set('academic_year')} hint="Format: 2026-27" />
            <Field id="unit" label="Unit">
              <select id="unit" className={selectCls} value={form.unit} onChange={set('unit')}>
                <option value="">Not specific</option>
                {UNITS.map((u) => <option key={u}>{u}</option>)}
              </select>
            </Field>
          </div>
          <Field id="topic" label="Topic" value={form.topic} onChange={set('topic')} placeholder="e.g. Binary Search" />
          <Field id="title" label="Title" value={form.title} onChange={set('title')}
            hint="Uploading the same title again for the same subject and type creates a new version." placeholder="Leave empty to use the file name" />

          <Field id="file" label="File" hint="PDF, DOCX, PPTX, TXT or Markdown, up to 25 MB. Legacy .doc/.ppt: please save as .docx/.pptx first.">
            <input id="file" ref={fileRef} type="file" accept={ACCEPTED_EXTENSIONS} required
              onChange={(e) => setFile(e.target.files[0] || null)}
              className="block w-full text-sm file:mr-3 file:px-3 file:py-2 file:rounded-md file:border-0 file:bg-primary/10 file:text-primary file:font-medium" />
          </Field>
          {file && <p className="text-[12.5px] text-muted">{file.name} · {formatBytes(file.size)}</p>}

          {progress !== null && (
            <div><div className="text-[12px] text-muted mb-1">Uploading… {progress}%</div><ProgressBar value={progress} tone="gold" /></div>
          )}
          <Button type="submit" loading={busy} disabled={!file || !form.subject_id || !form.department}>Upload & process</Button>
        </form>
      </div>

      <div className="lg:pt-[70px]">
        {doc ? <Tracker doc={doc} /> : (
          <div className="card-index rounded-lg p-5 text-sm text-muted">Processing progress will appear here after you upload a file.</div>
        )}
      </div>
    </div>
  )
}
