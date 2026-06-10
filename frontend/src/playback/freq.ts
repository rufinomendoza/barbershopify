// Pitch -> frequency. The playback engine is frequency-first: every
// scheduled note carries an explicit Hz, so just intonation is purely a
// different pitch->Hz mapping, never a different scheduler.

export function midiToHz(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12)
}

// Just intonation, root-anchored: each chord tone is a pure ratio over
// the chord root taken at EQUAL temperament. Anchoring every root to the
// fixed ET grid makes comma drift structurally impossible (DESIGN.md);
// the lead is rendered at ET separately, so the pitch center holds.
const JUST_RATIOS: Record<number, number> = {
  0: 1, // root
  2: 9 / 8, // ninth
  3: 6 / 5, // minor third
  4: 5 / 4, // major third
  5: 4 / 3, // fourth (rare, swipes)
  6: 7 / 5, // diminished fifth
  7: 3 / 2, // perfect fifth
  8: 8 / 5, // augmented fifth
  9: 5 / 3, // sixth
  10: 7 / 4, // the barbershop seventh: ~31 cents flat of ET
}

export interface ChordRef {
  root_pc: number
  quality: string
}

export function justHz(midi: number, chord: ChordRef | null): number {
  if (!chord) return midiToHz(midi)
  const interval = (((midi - chord.root_pc) % 12) + 12) % 12
  const ratio = JUST_RATIOS[interval]
  if (ratio === undefined) return midiToHz(midi)
  // the root in the octave at or below this note, anchored to ET
  const rootMidi = midi - interval
  return midiToHz(rootMidi) * ratio
}
