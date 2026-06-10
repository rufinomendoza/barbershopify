# DESIGN.md — decisions and why

Running log of non-obvious engineering decisions. The requirements live in `SPEC.md`; this file
explains the choices the spec left open.

## Score model: JSON source of truth, MusicXML as render contract

The frontend holds the working score as JSON (mirroring pydantic models in
`backend/barbershop/score.py`); the backend is a stateless transformer. Every edit mutates the
JSON and round-trips `POST /api/render` → fresh MusicXML → OSMD re-render. Rationale: MusicXML is
excellent as a *rendering/interchange* contract but miserable as a *mutable editor model* (ties,
divisions, voice interleaving). Keeping one MusicXML serializer — in Python, where the music logic
and its tests live — avoids maintaining duplicate serializers in two languages. The round-trip
costs ~tens of ms locally, dominated by OSMD's own layout pass, which we'd pay anyway.

- **Time**: integer ticks, 480/quarter. Integer arithmetic kills float-drift bugs, divides cleanly
  for triplets/dotted values, and maps 1:1 onto MusicXML `<divisions>` and MIDI PPQ.
- **Chord annotations travel with the score** (root pitch class + quality per harmonic slot).
  Both the legality validator and just-intonation playback need to know "what chord is this
  vertical" — recovering it by re-analysis would be fragile where it must be exact.

## OSMD over VexFlow

OSMD consumes MusicXML directly and owns engraving layout (systems, beams, lyrics, extenders);
VexFlow is a glyph-drawing library that would require building a layout engine — a project in
itself. Editing doesn't need glyph-level mutation: we map a click to a score-JSON note via
deterministic ordering (part, voice, measure, index — identical traversal on both sides), edit the
model, re-render. OSMD also ships a playback cursor API we use for the moving highlight.

## Playback synthesizes from score JSON, not from MusicXML or OSMD playback

Just intonation requires commanding exact frequencies per note per chord context; OSMD's playback
and general MIDI paths quantize to 12-TET. Tone.js lets us schedule each voice's events with
explicit Hz. The engine is frequency-first from day one (M2) so the JI toggle (M7) only swaps the
pitch→Hz function, not the scheduler.

## Just-intonation drift strategy (root-anchored, lead-pinned)

Each chord is tuned as pure ratios (4:5:6:7 family) relative to its **root taken at equal
temperament**; the lead's line is always rendered at ET. Comma drift is the classic failure of
"tune each chord relative to the previous one" — anchoring every chord's root to the fixed ET grid
makes drift structurally impossible, at the cost of small horizontal steps in harmony voices
between chords (real quartets do exactly this: melody holds the pitch center, harmony voices
adjust vertically). Documented here per spec; numeric tests assert 4:5:6:7 within a cent.

## Arranger: two-stage Viterbi (chords, then voicings)

Joint optimization over (chord × voicing) per slot explodes combinatorially; factoring into chord
selection (melody-note containment hard, tier bias / function preservation / circle-of-fifths
rewards soft) followed by voicing selection (range & crossing & parallels hard, ring / cone /
smoothness soft) keeps each DP small, debuggable, and independently testable. The voicing stage
sees the chosen chord sequence, which is what determines voice-leading anyway. Weights live in one
config object; the spice dial selects scaled presets rather than exposing raw weights.

## Hand-written MusicXML serializer (no music21)

We emit a narrow, fixed MusicXML subset (two parts, two voices each, fixed clefs, lyrics on one
voice). A direct ElementTree serializer is ~hundreds of lines, fully controlled (stem direction,
8vb clef, extenders — things music21 can fight you on), imports in milliseconds, and adds zero
dependencies. music21 stays out of the runtime; MIDI export uses `mido` (a tiny pure-Python dep).

## Melody extraction defaults to pyin; basic-pitch and demucs are opt-in flags

`librosa.pyin` is pure-Python/numpy, deterministic, and well-suited to the bundled test material
(mono, melody-dominant acoustic-era recordings). `basic-pitch` drags in a TensorFlow runtime and
`demucs` a Torch stack — both are quality boosters for dense modern mixes, so they're behind
config flags with lazy imports rather than install-time requirements. (Spec allows either default;
this is the pragmatic-install choice.)
