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
  listTestSongs: () => request<DemoInfo[]>('/api/test-songs'),
  arrangeDemo: (id: string, spice: number) =>
    request<Arrangement>(`/api/demos/${id}/arrange`, post({ spice })),
  arrangeTestSong: (id: string, spice: number) =>
    request<Arrangement>(`/api/test-songs/${id}/arrange`, post({ spice })),
  arrangeInput: (input: unknown, spice: number) =>
    request<Arrangement>('/api/arrange', post({ input, spice })),
  upload: (file: File, spice: number) => {
    const form = new FormData()
    form.append('file', file)
    return request<Arrangement>(`/api/upload?spice=${spice}`, {
      method: 'POST',
      body: form,
    })
  },
  render: (score: Score) =>
    request<{ musicxml: string }>('/api/render', post({ score })),
}
