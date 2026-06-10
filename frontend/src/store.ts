import { create } from 'zustand'
import { api } from './api'
import { engine, VOICE_ORDER } from './playback/engine'
import type { Arrangement, DemoInfo, VoiceName } from './types'

export type Stage = 'idle' | 'arranging' | 'rendering' | 'ready' | 'error'

export interface VoiceSettings {
  mute: boolean
  solo: boolean
  volume: number // dB
}

const defaultVoiceSettings = (): Record<VoiceName, VoiceSettings> =>
  Object.fromEntries(
    VOICE_ORDER.map((v) => [v, { mute: false, solo: false, volume: -8 }]),
  ) as Record<VoiceName, VoiceSettings>

interface AppState {
  demos: DemoInfo[]
  selectedDemo: string | null
  spice: number
  stage: Stage
  error: string | null
  arrangement: Arrangement | null

  playing: boolean
  currentTick: number | null
  tempoBpm: number
  voiceSettings: Record<VoiceName, VoiceSettings>

  loadDemos: () => Promise<void>
  setSpice: (spice: number) => void
  arrange: (demoId?: string) => Promise<void>
  setStage: (stage: Stage) => void

  play: () => Promise<void>
  pause: () => void
  stop: () => void
  setTempo: (bpm: number) => void
  toggleMute: (voice: VoiceName) => void
  toggleSolo: (voice: VoiceName) => void
  setVolume: (voice: VoiceName, db: number) => void
}

export const useStore = create<AppState>((set, get) => {
  engine.setCallbacks({
    onTick: (tick) => set({ currentTick: tick }),
    onStateChange: (playing) => set({ playing }),
  })

  return {
    demos: [],
    selectedDemo: null,
    spice: 3,
    stage: 'idle',
    error: null,
    arrangement: null,

    playing: false,
    currentTick: null,
    tempoBpm: 100,
    voiceSettings: defaultVoiceSettings(),

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
        engine.setScore(arrangement.score)
        set({ arrangement, stage: 'rendering', tempoBpm: arrangement.score.tempo })
      } catch (err) {
        set({ stage: 'error', error: err instanceof Error ? err.message : String(err) })
      }
    },

    setStage: (stage) => set({ stage }),

    play: () => engine.play(),
    pause: () => engine.pause(),
    stop: () => engine.stop(),

    setTempo: (bpm) => {
      engine.setTempo(bpm)
      set({ tempoBpm: bpm })
    },

    toggleMute: (voice) => {
      const settings = { ...get().voiceSettings }
      settings[voice] = { ...settings[voice], mute: !settings[voice].mute }
      engine.setMute(voice, settings[voice].mute)
      set({ voiceSettings: settings })
    },

    toggleSolo: (voice) => {
      const settings = { ...get().voiceSettings }
      settings[voice] = { ...settings[voice], solo: !settings[voice].solo }
      engine.setSolo(voice, settings[voice].solo)
      set({ voiceSettings: settings })
    },

    setVolume: (voice, db) => {
      const settings = { ...get().voiceSettings }
      settings[voice] = { ...settings[voice], volume: db }
      engine.setVolume(voice, db)
      set({ voiceSettings: settings })
    },
  }
})
