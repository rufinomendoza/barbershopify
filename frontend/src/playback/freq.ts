// Pitch -> frequency. The playback engine is frequency-first: every
// scheduled note carries an explicit Hz, so the just-intonation mode
// (Milestone 7) only swaps this mapping, never the scheduler.

export function midiToHz(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12)
}
