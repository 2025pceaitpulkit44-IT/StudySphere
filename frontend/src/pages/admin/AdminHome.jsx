import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, Loader2, ShieldAlert } from 'lucide-react'
import { Button, EmptyState, Pill, SectionHeader, Spinner } from '../../components/ui'
import { StatCard } from '../../components/student'
import { errorMessage } from '../../services/api'
import { adminService } from '../../services/adminService'
import { STATUS_LABEL, STATUS_TONE, formatDate } from '../../utils/constants'

const KB_BANNER = {
  empty: ['neutral', 'The knowledge base is empty. Upload material to get started.'],
  healthy: ['ok', 'Knowledge base is up to date. All documents are indexed.'],
  updating: ['busy', 'Some documents are still being processed.'],
  attention: ['warn', 'Some documents failed to process. Open the knowledge base to re-index or fix them.'],
}

export default function AdminHome() {
  const [d, setD] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = () => adminService.dashboard().then(setD).catch((e) => setError(errorMessage(e)))
    load()
    const t = setInterval(load, 15000)   // keeps the numbers live while documents are processing
    return () => clearInterval(t)
  }, [])

  if (error) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!d) return <Spinner />

  const [tone, text] = KB_BANNER[d.kb_status]
  const Icon = tone === 'ok' ? CheckCircle2 : tone === 'busy' ? Loader2 : AlertTriangle

  return (
    <div className="space-y-8 max-w-6xl">
      {!d.undertaking_completed && (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-gold/40 bg-gold/15 p-4">
          <ShieldAlert className="w-5 h-5 text-gold-dark shrink-0" />
          <p className="text-sm flex-1 min-w-[220px]"><b>Copyright undertaking required.</b> You must complete it before you can upload academic material.</p>
          <Link to="/admin/undertaking"><Button size="sm" variant="gold">Complete Undertaking</Button></Link>
        </div>
      )}

      <div className={`flex items-center gap-2.5 rounded-lg border p-3.5 text-sm ${tone === 'warn' ? 'border-[#E9C3B9] bg-[#F7E4DF]' : 'border-line bg-white'}`}>
        <Icon className={`w-4.5 h-4.5 ${tone === 'busy' ? 'animate-spin text-gold-dark' : tone === 'warn' ? 'text-[#8f3722]' : tone === 'ok' ? 'text-primary' : 'text-muted'}`} />
        {text}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <StatCard label="Students" value={d.total_students} />
        <StatCard label="Documents" value={d.total_documents} hint={`${d.indexed_documents} indexed${d.archived_documents ? ` · ${d.archived_documents} archived` : ''}`} />
        <StatCard label="Indexed passages" value={d.indexed_passages.toLocaleString()} hint="Searchable by StudySphere AI" />
        <StatCard label="Subjects covered" value={`${d.subjects_covered} / ${d.subjects_total}`} hint="With at least one indexed document" />
        <StatCard label="Student doubts" value={d.total_doubts} hint={d.unanswered_doubts ? `${d.unanswered_doubts} not answerable from the material` : undefined} />
        <StatCard label="Needs attention" value={d.failed_documents + d.processing_documents} hint={`${d.failed_documents} failed · ${d.processing_documents} processing`} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2">
          <SectionHeader eyebrow="Latest" title="Recent uploads" action={<Link to="/admin/kb" className="text-[13px] text-primary font-medium">Manage</Link>} />
          {d.recent_uploads.length === 0 ? (
            <EmptyState title="Nothing uploaded yet" message="Upload your first academic material to build the knowledge base."
              action={<Link to="/admin/upload"><Button>Upload material</Button></Link>} />
          ) : (
            <ul className="space-y-2">
              {d.recent_uploads.map((u) => (
                <li key={u.id} className="card-index rounded-lg p-3.5 flex items-center gap-3">
                  <div className="flex-1 min-w-0"><div className="text-sm font-medium">{u.title}</div>
                    <div className="text-[12px] text-muted">{u.subject} · v{u.version} · {formatDate(u.created_at)}</div></div>
                  <Pill tone={STATUS_TONE[u.status] || 'neutral'}>{STATUS_LABEL[u.status] || u.status}</Pill>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <SectionHeader eyebrow="Shortcuts" title="Quick actions" />
          <div className="space-y-2">
            <Link to="/admin/upload" className="card-index rounded-lg p-3.5 block text-sm font-medium hover:border-primary/40">Upload academic material</Link>
            <Link to="/admin/doubts" className="card-index rounded-lg p-3.5 block text-sm font-medium hover:border-primary/40">See what students are asking</Link>
            <Link to="/admin/analytics" className="card-index rounded-lg p-3.5 block text-sm font-medium hover:border-primary/40">View analytics</Link>
          </div>
        </section>
      </div>
    </div>
  )
}
