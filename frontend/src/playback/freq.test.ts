import { describe, expect, it } from 'vitest'
import { midiToHz } from './freq'

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
