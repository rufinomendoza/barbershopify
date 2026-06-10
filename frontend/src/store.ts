import { create } from 'zustand'
import { api } from './api'
import { engine, VOICE_ORDER } from './playback/engine'
import type { Arrangement, DemoInfo, VoiceName } from './types'

export type Stage = 'idle' | 'analyzing' | 'arranging' | 'rendering' | 'ready' | 'error'

export type Source = { kind: 'demo' | 'song'; id: string } | { kind: 'upload'; name: string }

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
  testSongs: DemoInfo[]
  source: Source | null
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
  arrangeSource: (source: Source) => Promise<void>
  rearrange: () => Promise<void>
  uploadFile: (file: File) => Promise<void>
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

  const finish = (arrangement: Arrangement) => {
    engine.setScore(arrangement.score)
    set({ arrangement, stage: 'rendering', tempoBpm: arrangement.score.tempo })
  }

  const fail = (err: unknown) =>
    set({ stage: 'error', error: err instanceof Error ? err.message : String(err) })

  return {
    demos: [],
    testSongs: [],
    source: null,
    spice: 3,
    stage: 'idle',
    error: null,
    arrangement: null,

    playing: false,
    currentTick: null,
    tempoBpm: 100,
    voiceSettings: defaultVoiceSettings(),

    loadDemos: async () => {
      const [demos, testSongs] = await Promise.all([api.listDemos(), api.listTestSongs()])
      set({ demos, testSongs })
    },

    setSpice: (spice) => set({ spice }),

    arrangeSource: async (source) => {
      if (source.kind === 'upload') return
      set({ source, stage: source.kind === 'song' ? 'analyzing' : 'arranging', error: null })
      try {
        const arrangement =
          source.kind === 'demo'
            ? await api.arrangeDemo(source.id, get().spice)
            : await api.arrangeTestSong(source.id, get().spice)
        finish(arrangement)
      } catch (err) {
        fail(err)
      }
    },

    rearrange: async () => {
      const input = get().arrangement?.input
      if (!input) return
      set({ stage: 'arranging', error: null })
      try {
        finish(await api.arrangeInput(input, get().spice))
      } catch (err) {
        fail(err)
      }
    },

    uploadFile: async (file) => {
      set({ source: { kind: 'upload', name: file.name }, stage: 'analyzing', error: null })
      try {
        finish(await api.upload(file, get().spice))
      } catch (err) {
        fail(err)
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
