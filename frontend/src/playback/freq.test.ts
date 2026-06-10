import { describe, expect, it } from 'vitest'
import { justHz, midiToHz } from './freq'

const CENT = 1.0005777895 // one cent as a frequency ratio

function centsOff(actual: number, expected: number): number {
  return Math.abs(1200 * Math.log2(actual / expected))
}

describe('midiToHz (equal temperament)', () => {
  it('A4 is 440', () => {
    expect(midiToHz(69)).toBeCloseTo(440, 6)
  })

  it('middle C is ~261.626', () => {
    expect(midiToHz(60)).toBeCloseTo(261.6256, 3)
  })

  it('octaves double', () => {
    expect(midiToHz(81)).toBeCloseTo(880, 6)
  })
})

describe('justHz (root-anchored just intonation)', () => {
  // C7 chord: C4 E4 G4 Bb4 must hit exact 4:5:6:7 over the ET root
  const chord = { root_pc: 0, quality: 'dom7' }
  const rootHz = midiToHz(60)

  it('root stays on the ET anchor', () => {
    expect(centsOff(justHz(60, chord), rootHz)).toBeLessThan(0.01)
  })

  it('major third rings at 5:4', () => {
    expect(centsOff(justHz(64, chord), rootHz * (5 / 4))).toBeLessThan(1)
  })

  it('fifth rings at 3:2', () => {
    expect(centsOff(justHz(67, chord), rootHz * (3 / 2))).toBeLessThan(1)
  })

  it('barbershop seventh rings at 7:4 (~31 cents flat of ET)', () => {
    const just = justHz(70, chord)
    expect(centsOff(just, rootHz * (7 / 4))).toBeLessThan(1)
    expect(centsOff(just, midiToHz(70))).toBeGreaterThan(25) // audibly flat of ET
  })

  it('voices above the root octave keep pure ratios', () => {
    // E5 over a C root: 5:4 ratio times two octaves... E5 sits over C5
    expect(centsOff(justHz(76, chord), midiToHz(72) * (5 / 4))).toBeLessThan(1)
  })

  it('non-chord tones fall back to equal temperament', () => {
    expect(justHz(61, chord)).toBeCloseTo(midiToHz(61), 6)
  })

  it('cent constant sanity', () => {
    expect(1200 * Math.log2(CENT)).toBeCloseTo(1, 3)
  })
})
