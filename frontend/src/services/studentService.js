import { api } from './api'

const get = (url, params) => api.get(url, { params }).then((r) => r.data)

export const aiService = {
  ask: (mode, payload) => api.post(`/ai/${mode}`, payload, { timeout: 90000 }).then((r) => r.data),
}

export const studentService = {
  dashboard: () => get('/dashboard'),
  progress: () => get('/progress'),
  overview: () => get('/subjects/overview'),
  subject: (id) => get(`/subjects/${id}`),
  documents: (subjectId) => get('/documents', subjectId ? { subject_id: subjectId } : undefined),
  search: (q) => get('/search', { q }),
  doubts: (params) => get('/doubts', params),
  doubt: (id) => get(`/doubts/${id}`),
  deleteDoubt: (id) => api.delete(`/doubts/${id}`),
}

export const quizService = {
  start: (payload) => api.post('/quiz/start', payload, { timeout: 90000 }).then((r) => r.data),
  submit: (payload) => api.post('/quiz/submit', payload).then((r) => r.data),
  attempts: () => get('/quiz/attempts'),
  review: (id) => get(`/quiz/attempts/${id}`),
}

/** Downloads need the auth header, so fetch as a blob and save it. */
export async function downloadDocument(doc, version) {
  const res = await api.get(`/documents/${doc.document_id ?? doc.id}/download`, { responseType: 'blob', params: version ? { version } : undefined })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = doc.original_filename || doc.title
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
