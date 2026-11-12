import { api } from './api'

export const subjectService = {
  list: () => api.get('/subjects').then((r) => r.data),
  get: (id) => api.get(`/subjects/${id}`).then((r) => r.data),
}

export const undertakingService = {
  status: () => api.get('/copyright-undertaking/status').then((r) => r.data),
  submit: (payload) => api.post('/copyright-undertaking', payload).then((r) => r.data),
}

export const documentService = {
  list: () => api.get('/documents').then((r) => r.data),
  get: (id) => api.get(`/documents/${id}`).then((r) => r.data),
  remove: (id) => api.delete(`/documents/${id}`),
  reindex: (id) => api.post(`/documents/${id}/reindex`).then((r) => r.data),
  archive: (id) => api.post(`/documents/${id}/archive`).then((r) => r.data),
  restore: (id) => api.post(`/documents/${id}/restore`).then((r) => r.data),
  makeLive: (id, version) => api.post(`/documents/${id}/versions/${version}/restore`).then((r) => r.data),
  upload: (formData, onProgress) =>
    api.post('/documents/upload', formData, {
      // Let the browser set the multipart boundary.
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
      onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
    }).then((r) => r.data),
}

export const adminService = {
  dashboard: () => api.get('/admin/dashboard').then((r) => r.data),
  doubts: (days) => api.get('/admin/doubts', { params: { days } }).then((r) => r.data),
  analytics: (days) => api.get('/admin/analytics', { params: { days } }).then((r) => r.data),
}
