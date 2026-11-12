export const MATERIAL_TYPES = [
  'Lecture Notes', 'Unit Notes', 'Assignment', 'Question Bank', 'Lab Manual', 'Syllabus', 'Reference Material',
]

export const UNITS = ['Unit 1', 'Unit 2', 'Unit 3', 'Unit 4', 'Unit 5']

export const ACCEPTED_EXTENSIONS = '.pdf,.docx,.pptx,.txt,.md'

export const DEPARTMENTS = [
  'Computer Science & Engineering',
  'Information Technology',
  'Electronics & Telecommunication',
  'Mechanical Engineering',
  'Civil Engineering',
]

// Pipeline stages in order (mirrors backend/app/rag/pipeline.py).
export const STAGES = [
  ['uploaded', 'Uploaded'],
  ['extracting', 'Extracting text'],
  ['cleaning', 'Cleaning text'],
  ['chunking', 'Chunking'],
  ['embedding', 'Generating embeddings'],
  ['indexing', 'Indexing'],
  ['indexed', 'Knowledge Base Updated'],
]

export const STATUS_TONE = {
  uploaded: 'neutral', processing: 'open', chunked: 'gold', indexed: 'green', failed: 'danger', archived: 'neutral',
}

export const STATUS_LABEL = {
  uploaded: 'Uploaded', processing: 'Processing', chunked: 'Chunked (needs re-index)', indexed: 'Indexed',
  failed: 'Failed', archived: 'Archived',
}

export function currentAcademicYear(d = new Date()) {
  const y = d.getMonth() >= 5 ? d.getFullYear() : d.getFullYear() - 1
  return `${y}-${String((y + 1) % 100).padStart(2, '0')}`
}

export function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export const TOPIC_STATUS = {
  needs_revision: ['Needs revision', 'danger'],
  practice: ['Practice recommended', 'gold'],
  improving: ['Improving', 'green'],
  good: ['On track', 'green'],
  new: ['Just started', 'neutral'],
}

export function formatDate(iso, withTime = false) {
  const d = new Date(iso)
  return withTime ? d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : d.toLocaleDateString([], { dateStyle: 'medium' })
}
