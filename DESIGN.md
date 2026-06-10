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

## Two interpretations in the 7th-resolution rule (theory nerds: argue here)

The spec demands "chordal 7ths resolve down by step," enforced as a hard constraint and a
validator check. Two principled exceptions, both forced by other hard rules:

1. **Transferred resolution.** V7→I with the melody landing on the I's 3rd: barbershop dom7s are
   complete (no omissions) and 3rds are never doubled, so the inner-voice 7th *cannot* fall by
   step — the lead owns the resolution tone. Standard practice (and ours): the resolution
   transfers to the lead; the 7th-voice moves to another chord tone, preferring downward motion.
   Allowed only when the lead actually sounds the resolution pitch class.
2. **dim7 has no functional 7th.** A diminished 7th chord is fully symmetric; which tone is "the
   7th" is an artifact of root spelling (we pick one of four equivalent roots). Enforcing
   down-by-step on that label created provably unvoiceable progressions (verified by exhaustive
   search over the voicing lattice). dim7 tones follow the general smoothness costs — step or
   hold — which is how passing/neighbor diminished chords actually behave. Half-diminished and
   minor 7ths keep the strict rule; their 7ths are real.

## Demo tunes: certainty over period flavor

The bundled no-audio demos are "Yankee Doodle" (trad.) and "Good Morning to All" (Mildred J.
Hill, 1893) rather than the spec's example suggestions ("My Wild Irish Rose," "Shine On, Harvest
Moon") — chosen because I can transcribe these two note-perfectly from memory, and a demo whose
melody is *wrong* fails the "sounds like barbershop" bar worse than one that's merely older.
Both are public domain; GMtA is squarely in the right era. A true barbershop-era tune joins in
Milestone 3 once verified against actual sheet music. The deliberately coarse demo chord inputs
(one or two per measure) are a feature: the engine's substitutions and dominant chains are the
demo.

## Octave folding is artifact correction, not melody bending

pyin's classic failure mode is the octave jump. Two defenses: extraction folds notes sitting more
than a fifth from their local median back toward it in octaves, and `arrange()` folds any note
that no global transposition could bring inside the Lead's range. Pitch classes — and therefore
all harmony decisions — are untouched, so this does not violate "melody is sacrosanct"; it
corrects transcription artifacts the way a human transcriber silently would.

## Residual violations on noisy real-world audio are reported, not hidden

The arranger guarantees a complete chart even when the (noisy, chromatic) extracted melody plus
the chord chain make some legality constraint locally unsatisfiable — hard constraints become
10k-cost edges, so Viterbi picks the least-bad chart rather than crashing. On clean inputs (all
demo tunes, all spice levels, and two of the four bundled 78s) the validator reports zero
violations; on the noisiest two 78s a handful (≤6) survive at feasibility crunches, and the UI
shows the count. A joint chord+voicing feasibility pass is planned with the M7 voice-leading
refinements. The audio pipeline assumes 4/4 in v1 — wrong for waltz-time songs, which simply get
re-barred, not mis-harmonized; 3/4 detection is a known gap.

## Affect → music mapping (the part to argue about)

Composition mode scores text with a deterministic valence/arousal lexicon (negation-aware,
offline, testable). The mapping:

- **Valence → mode and color.** Below −0.15 the chart goes minor (A-minor frame; the arranger
  picks the final singable key), leaning on barbershop's minor palette — ii⌀7→V motion is baked
  into the closing template. Otherwise major. The *ending stanza's* valence decides the last
  chord of a minor chart: brightening texts earn a picardy major; unrelieved ones end minor (the
  validator accepts a minor final only in minor keys).
- **Arousal → energy.** Tempo = 92 + arousal×36 BPM, clamped to 60–132 (a sad poem lands in the
  ~63–79 band, an exuberant one ~105–128). Melodic span = 12 + (arousal+1)×2.5 semitones. Above
  0.25 arousal, closing phrases get cadential acceleration: the dominant bar splits into
  predominant→dominant halves.
- **Rhyme → form.** Lines map 1:1 to 4-bar phrases. The second occurrence of a rhyme letter
  closes its couplet (authentic cadence); first occurrences stay open (half cadence). Rhyming
  lines answer with the same cadence scale degree. An iambic opening shifts the phrase onto a
  weak-beat start so stressed syllables land on beats.
- **Melody.** Eight seeded candidates per phrase, scored for stress–meter concordance, peak near
  the golden section, leap economy, and chord-tone placement on strong beats; re-compose bumps
  the seed.

Three counterpoint rulings tightened while testing composed charts, now applied engine-wide:
parallel fifths/octaves require *same-direction* motion (contrary "anti-parallels" are legal, as
in the classic ragtime turnaround); a predominant 7th (min7/ii⌀7) may *hold* its 7th into a chord
containing it (common-tone resolution, e.g. ii⌀7→i); and parallels are not counted across a
phrase rest (no linear connection). The harmonizer also avoids the "fifth-to-fifth trap" —
harmonizing a rising melody as the 5th of two consecutive complete 7th chords, which would force
bass/lead parallels no voicing can escape.

## Melody extraction defaults to pyin; basic-pitch and demucs are opt-in flags

`librosa.pyin` is pure-Python/numpy, deterministic, and well-suited to the bundled test material
(mono, melody-dominant acoustic-era recordings). `basic-pitch` drags in a TensorFlow runtime and
`demucs` a Torch stack — both are quality boosters for dense modern mixes, so they're behind
config flags with lazy imports rather than install-time requirements. (Spec allows either default;
this is the pragmatic-install choice.)
