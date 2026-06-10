import { create } from 'zustand'
import { api } from './api'
import type { Arrangement, DemoInfo } from './types'

export type Stage = 'idle' | 'arranging' | 'rendering' | 'ready' | 'error'

interface AppState {
  demos: DemoInfo[]
  selectedDemo: string | null
  spice: number
  stage: Stage
  error: string | null
  arrangement: Arrangement | null

  loadDemos: () => Promise<void>
  setSpice: (spice: number) => void
  arrange: (demoId?: string) => Promise<void>
  setStage: (stage: Stage) => void
}

export const useStore = create<AppState>((set, get) => ({
  demos: [],
  selectedDemo: null,
  spice: 3,
  stage: 'idle',
  error: null,
  arrangement: null,

  loadDemos: async () => {
    const demos = await api.listDemos()
    set({ demos })
  },

  setSpice: (spice) => set({ spice }),

  arrange: async (demoId) => {
    const id = demoId ?? get().selectedDemo
    if (!id) return
    set({ selectedDemo: id, stage: 'arranging', error: null })
    try {
      const arrangement = await api.arrangeDemo(id, get().spice)
      set({ arrangement, stage: 'rendering' })
    } catch (err) {
      set({ stage: 'error', error: err instanceof Error ? err.message : String(err) })
    }
  },

  setStage: (stage) => set({ stage }),
}))
