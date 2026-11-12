import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Archive, ArchiveRestore, Download, Eye, Library, RefreshCw, Search, Trash2, X } from 'lucide-react'
import { Button, ConfirmDialog, EmptyState, Pill, SectionHeader, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { errorMessage } from '../../services/api'
import { documentService } from '../../services/adminService'
import { downloadDocument } from '../../services/studentService'
import { STATUS_LABEL, STATUS_TONE, formatBytes, formatDate } from '../../utils/constants'

const selectCls = 'px-3 py-2 rounded-md border border-line bg-white text-sm focus:border-primary'
const BUSY = ['uploaded', 'processing']
const iconBtn = 'p-1.5 rounded-md text-muted hover:bg-bg'

function VersionPanel({ doc, onClose, onMakeLive, busy }) {
  const toast = useToast()
  const get = async (v) => {
    try { await downloadDocument({ id: doc.id, original_filename: v.original_filename, title: doc.title }, v.version_number) }
    catch (e) { toast.error(errorMessage(e, 'Download failed.')) }
  }
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-ink/30" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label={`Details of ${doc.title}`} onClick={(e) => e.stopPropagation()}
        className="fade-up w-full max-w-lg bg-white h-full overflow-y-auto p-5 border-l border-line">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div><h3 className="font-display font-semibold text-lg">{doc.title}</h3>
            <p className="text-[13px] text-muted">{doc.subject.name} · {doc.material_type}{doc.unit && ` · ${doc.unit}`}</p></div>
          <button onClick={onClose} aria-label="Close" className={iconBtn}><X className="w-4 h-4" /></button>
        </div>
        <dl className="text-sm grid grid-cols-[110px_1fr] gap-y-1.5 mb-6">
          {[['Topic', doc.topic || '—'], ['Department', doc.department], ['Semester', doc.semester], ['Academic year', doc.academic_year],
            ['Uploaded by', doc.uploader_name], ['First uploaded', formatDate(doc.created_at)]].map(([k, v]) => (
            <Fragment key={k}><dt className="text-muted">{k}</dt><dd>{v}</dd></Fragment>))}
        </dl>

        <h4 className="font-display font-semibold text-[15px] mb-2">Versions</h4>
        <p className="text-[12.5px] text-muted mb-3">Only the live version is used to answer questions. Making an older version live re-indexes its stored file.</p>
        <ul className="space-y-2">
          {[...doc.versions].reverse().map((v) => (
            <li key={v.version_number} className="border border-line rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-sm font-medium">v{v.version_number}</span>
                {v.is_current && <Pill tone="green">Live</Pill>}
                <Pill tone={STATUS_TONE[v.status] || 'neutral'}>{STATUS_LABEL[v.status] || v.status}</Pill>
              </div>
              <div className="text-[12.5px] text-muted">{v.original_filename} · {formatBytes(v.size_bytes)} · {formatDate(v.created_at)}{v.is_current && ` · ${v.chunk_count} passages`}</div>
              {v.status === 'failed' && <div className="text-[12.5px] text-[#B3472E] mt-1">{v.error_message}</div>}
              <div className="flex gap-2 mt-2">
                <Button size="sm" variant="secondary" onClick={() => get(v)}><Download className="w-3.5 h-3.5" /> Download</Button>
                {!v.is_current && !BUSY.includes(v.status) && (
                  <Button size="sm" variant="subtle" disabled={busy} onClick={() => onMakeLive(v.version_number)}>Make live</Button>)}
              </div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}

export default function KnowledgeBase() {
  const toast = useToast()
  const [docs, setDocs] = useState(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [subject, setSubject] = useState('')
  const [target, setTarget] = useState(null)      // doc pending delete
  const [deleting, setDeleting] = useState(false)
  const [viewId, setViewId] = useState(null)
  const [working, setWorking] = useState(false)

  const load = useCallback(() => {
    documentService.list().then((d) => { setDocs(d); setError('') }).catch((e) => setError(errorMessage(e)))
  }, [])
  useEffect(load, [load])

  useEffect(() => {   // refresh while anything is processing
    if (!docs?.some((d) => d.versions.some((v) => BUSY.includes(v.status)))) return
    const t = setInterval(load, 2500)
    return () => clearInterval(t)
  }, [docs, load])

  const subjects = useMemo(() => [...new Map((docs || []).map((d) => [d.subject.id, d.subject.name]))], [docs])
  const rows = useMemo(() => (docs || []).filter((d) =>
    (!status || d.status === status) && (!subject || String(d.subject.id) === subject) &&
    (!q.trim() || `${d.title} ${d.topic} ${d.original_filename}`.toLowerCase().includes(q.trim().toLowerCase()))), [docs, q, status, subject])
  const viewDoc = docs?.find((d) => d.id === viewId)

  const act = async (fn, okMsg) => {
    setWorking(true)
    try { await fn(); toast.success(okMsg); load() } catch (e) { toast.error(errorMessage(e)) } finally { setWorking(false) }
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await documentService.remove(target.id)
      toast.success('Document, stored files and all indexed passages were deleted.')
      setTarget(null); setViewId(null); load()
    } catch (e) { toast.error(errorMessage(e)) } finally { setDeleting(false) }
  }

  if (error && !docs) return <p role="alert" className="text-sm text-[#B3472E]">{error}</p>
  if (!docs) return <Spinner />

  return (
    <div>
      <SectionHeader eyebrow="Knowledge base" title="Documents" action={<Link to="/admin/upload"><Button size="sm">Upload material</Button></Link>} />
      {docs.length === 0 ? (
        <EmptyState icon={Library} title="No documents yet" message="Upload your first academic material to start building the knowledge base."
          action={<Link to="/admin/upload"><Button>Upload material</Button></Link>} />
      ) : (
        <>
          <div className="flex flex-wrap gap-3 mb-4">
            <div className="flex items-center gap-2 px-3 py-2 rounded-md border border-line bg-white flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-muted" />
              <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search documents" placeholder="Search title, topic or file…" className="w-full text-sm outline-none" />
            </div>
            <select aria-label="Filter by status" className={selectCls} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select aria-label="Filter by subject" className={selectCls} value={subject} onChange={(e) => setSubject(e.target.value)}>
              <option value="">All subjects</option>
              {subjects.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
          </div>

          {rows.length === 0 ? <p className="text-sm text-muted py-8 text-center">No documents match these filters.</p> : (
            <div className="card-index rounded-lg overflow-x-auto">
              <table className="w-full text-sm min-w-[820px]">
                <thead className="text-left text-[11.5px] font-mono uppercase tracking-wider text-muted border-b border-line">
                  <tr>{['Document', 'Subject', 'Topic', 'Uploader', 'Uploaded', 'Status', 'Ver.', 'Passages', ''].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {rows.map((d) => (
                    <tr key={d.id}>
                      <td className="px-4 py-3"><div className="font-medium">{d.title}</div><div className="text-[12px] text-muted">{d.original_filename}</div></td>
                      <td className="px-4 py-3">{d.subject.name}</td>
                      <td className="px-4 py-3">{d.topic || '—'}</td>
                      <td className="px-4 py-3">{d.uploader_name}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(d.created_at)}</td>
                      <td className="px-4 py-3">
                        <Pill tone={STATUS_TONE[d.status] || 'neutral'}>{STATUS_LABEL[d.status] || d.status}</Pill>
                        {d.status === 'failed' && <div className="text-[12px] text-[#B3472E] mt-1 max-w-[220px]">{d.error_message}</div>}
                      </td>
                      <td className="px-4 py-3 font-mono">v{d.version}</td>
                      <td className="px-4 py-3 font-mono">{d.chunk_count}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end">
                          <button className={iconBtn} onClick={() => setViewId(d.id)} aria-label={`View ${d.title}`} title="View & versions"><Eye className="w-4 h-4" /></button>
                          {['chunked', 'failed', 'indexed'].includes(d.status) && (
                            <button className={iconBtn} disabled={working} onClick={() => act(() => documentService.reindex(d.id), `Re-indexing “${d.title}”…`)} aria-label={`Re-index ${d.title}`} title="Re-index"><RefreshCw className="w-4 h-4" /></button>)}
                          {d.status === 'archived'
                            ? <button className={iconBtn} disabled={working} onClick={() => act(() => documentService.restore(d.id), 'Document restored to the knowledge base.')} aria-label={`Restore ${d.title}`} title="Restore"><ArchiveRestore className="w-4 h-4" /></button>
                            : d.status === 'indexed' && <button className={iconBtn} disabled={working} onClick={() => act(() => documentService.archive(d.id), 'Archived. Students and the AI no longer use it.')} aria-label={`Archive ${d.title}`} title="Archive"><Archive className="w-4 h-4" /></button>}
                          <button className={`${iconBtn} hover:!text-[#B3472E]`} onClick={() => setTarget(d)} aria-label={`Delete ${d.title}`} title="Delete"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {viewDoc && <VersionPanel doc={viewDoc} busy={working} onClose={() => setViewId(null)}
        onMakeLive={(n) => act(() => documentService.makeLive(viewDoc.id, n), `Version ${n} is being re-indexed and will go live.`)} />}

      <ConfirmDialog open={!!target} danger loading={deleting} confirmLabel="Delete" title="Delete this document?"
        message={target ? `“${target.title}”, all ${target.versions.length} version(s), the stored files and every passage derived from them will be permanently removed. To keep it but hide it from students, archive it instead.` : ''}
        onConfirm={confirmDelete} onCancel={() => setTarget(null)} />
    </div>
  )
}
