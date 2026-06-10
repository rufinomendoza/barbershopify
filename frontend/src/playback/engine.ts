// Four-voice playback engine on Tone.js. The Transport runs at PPQ 480
// so score ticks map 1:1 onto transport ticks: tempo changes apply live
// without rescheduling. Each voice is a warm, vocal-ish mono chain
// (detuned saws -> lowpass -> channel with mute/solo/volume/pan).
import * as Tone from 'tone'
import { justHz, midiToHz, type ChordRef } from './freq'
import type { ChordSpan, Score, VoiceName } from '../types'

export type TuningMode = 'just' | 'equal'

export const VOICE_ORDER: VoiceName[] = ['tenor', 'lead', 'bari', 'bass']

const PAN: Record<VoiceName, number> = { tenor: -0.2, lead: 0.12, bari: 0.24, bass: 0 }

class VoiceChain {
  readonly synth: Tone.Synth
  readonly channel: Tone.Channel

  constructor(pan: number) {
    this.channel = new Tone.Channel({ volume: -8, pan }).toDestination()
    const filter = new Tone.Filter(1500, 'lowpass')
    this.synth = new Tone.Synth({
      oscillator: { type: 'fatsawtooth', count: 3, spread: 12 },
      envelope: { attack: 0.05, decay: 0.12, sustain: 0.85, release: 0.2 },
    })
    this.synth.chain(filter, this.channel)
  }
}

export interface EngineCallbacks {
  onTick: (tick: number | null) => void
  onStateChange: (playing: boolean) => void
}

export class PlaybackEngine {
  private chains = new Map<VoiceName, VoiceChain>()
  private callbacks: EngineCallbacks | null = null
  private started = false
  private chords: ChordSpan[] = []
  tuning: TuningMode = 'just' // the barbershop default; toggle is live

  private chordAt(tick: number): ChordRef | null {
    for (const c of this.chords) {
      if (c.onset <= tick && tick < c.onset + c.duration) return c
    }
    return null
  }

  private hzFor(voice: VoiceName, midi: number, tick: number): number {
    // the lead holds the ET pitch center; harmony voices tune into the chord
    if (this.tuning === 'equal' || voice === 'lead') return midiToHz(midi)
    return justHz(midi, this.chordAt(tick))
  }

  private transport() {
    return Tone.getTransport()
  }

  private ensureChains() {
    if (this.chains.size) return
    this.transport().PPQ = 480
    for (const voice of VOICE_ORDER) {
      this.chains.set(voice, new VoiceChain(PAN[voice]))
    }
  }

  setCallbacks(cb: EngineCallbacks) {
    this.callbacks = cb
  }

  setScore(score: Score) {
    this.ensureChains()
    this.stop()
    this.transport().cancel(0)
    this.transport().bpm.value = score.tempo
    this.chords = score.chords

    const onsets = new Set<number>()
    let totalTicks = 0
    for (const voice of VOICE_ORDER) {
      const chain = this.chains.get(voice)!
      for (const note of score.voices[voice]) {
        onsets.add(note.onset)
        totalTicks = Math.max(totalTicks, note.onset + note.duration)
        this.transport().schedule((time) => {
          // duration and tuning resolve at fire time, so live tempo
          // changes and the just/equal toggle apply mid-playback
          const seconds = Tone.Time(`${note.duration - 8}i`).toSeconds()
          const hz = this.hzFor(voice, note.midi, note.onset)
          chain.synth.triggerAttackRelease(hz, seconds, time)
        }, `${note.onset}i`)
      }
    }

    for (const tick of onsets) {
      this.transport().schedule((time) => {
        Tone.getDraw().schedule(() => this.callbacks?.onTick(tick), time)
      }, `${tick}i`)
    }
    this.transport().schedule((time) => {
      Tone.getDraw().schedule(() => {
        this.stop()
      }, time)
    }, `${totalTicks}i`)
  }

  async play() {
    this.ensureChains()
    if (!this.started) {
      await Tone.start()
      this.started = true
    }
    this.transport().start()
    this.callbacks?.onStateChange(true)
  }

  pause() {
    this.transport().pause()
    this.callbacks?.onStateChange(false)
  }

  stop() {
    this.transport().stop()
    this.transport().position = 0
    this.callbacks?.onStateChange(false)
    this.callbacks?.onTick(null)
  }

  setTempo(bpm: number) {
    this.transport().bpm.value = bpm
  }

  setMute(voice: VoiceName, mute: boolean) {
    this.ensureChains()
    this.chains.get(voice)!.channel.mute = mute
  }

  setSolo(voice: VoiceName, solo: boolean) {
    this.ensureChains()
    this.chains.get(voice)!.channel.solo = solo
  }

  setVolume(voice: VoiceName, db: number) {
    this.ensureChains()
    this.chains.get(voice)!.channel.volume.value = db
  }

  /** Audible feedback while editing: sound a pitch briefly in a voice's timbre. */
  async preview(voice: VoiceName, midi: number) {
    this.ensureChains()
    if (!this.started) {
      await Tone.start()
      this.started = true
    }
    this.chains.get(voice)!.synth.triggerAttackRelease(midiToHz(midi), 0.25)
  }
}

export const engine = new PlaybackEngine()

if (import.meta.env.DEV) {
  // live-debugging handle: inspect transport state from the console
  ;(window as unknown as Record<string, unknown>).__engine = engine
  ;(window as unknown as Record<string, unknown>).__tone = Tone
}
