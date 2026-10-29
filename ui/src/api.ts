import type { DocumentDetail, Summary } from './types'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  queue: () => call<Summary[]>('/review-queue'),
  documents: () => call<Summary[]>('/documents'),
  document: (id: string) => call<DocumentDetail>(`/documents/${id}`),
  fileUrl: (id: string) => `/api/documents/${id}/file`,
  upload: (file: File, docType: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('doc_type', docType)
    return call<DocumentDetail>('/documents', { method: 'POST', body: form })
  },
  correct: (id: string, field: string, value: unknown, reviewer: string) =>
    call<DocumentDetail>(`/documents/${id}/corrections`, json({ field, value, reviewer })),
  approve: (id: string, reviewer: string) =>
    call<DocumentDetail>(`/documents/${id}/approve`, json({ reviewer })),
}
