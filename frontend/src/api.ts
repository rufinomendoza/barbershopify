import type { Arrangement, DemoInfo, Score } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${detail}`)
  }
  return res.json() as Promise<T>
}

const post = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  listDemos: () => request<DemoInfo[]>('/api/demos'),
  arrangeDemo: (id: string, spice: number) =>
    request<Arrangement>(`/api/demos/${id}/arrange`, post({ spice })),
  render: (score: Score) =>
    request<{ musicxml: string }>('/api/render', post({ score })),
}
