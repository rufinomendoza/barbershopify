# barbershopify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local web app that turns uploaded songs (or pasted poems) into editable, playable TTBB barbershop quartet arrangements, per `SPEC.md`.

**Architecture:** Python/FastAPI backend hosting a *pure* music package (score model, rule-based arrangement engine, MusicXML/MIDI serializers, text-setting, composition) plus heavyweight audio analysis behind lazy imports; React+TypeScript+Vite frontend holding the score-JSON working copy, rendering via OpenSheetMusicDisplay, playing via Tone.js with per-chord just-intonation frequencies. The backend is a stateless transformer: score JSON in → score JSON / MusicXML / MIDI out.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, numpy/librosa (analysis), faster-whisper (ASR), pronouncing/g2p-en (lyrics), pytest; React 18, TypeScript, Vite, zustand, OSMD, Tone.js.

This plan is intentionally **short** (the user asked for architecture + milestone order; `SPEC.md` §Milestones fixes the order). Each milestone is planned in detail when started; `SPEC.md` is the authority for requirements, `DESIGN.md` records decisions.

---

## Core contracts (locked in up front)

1. **Score JSON is the single source of truth.** Pydantic models in `backend/barbershop/score.py`, mirrored as TypeScript types. Time in integer ticks, **480 per quarter note**; pitches as MIDI ints; four named voices (tenor/lead/bari/bass); per-slot chord annotations (root pitch class, quality) carried in the score — playback JI tuning and the legality validator both need them. Lyrics attach to lead events with syllabic state (single/begin/middle/end) and extender flags.
2. **MusicXML is the backend→renderer contract**, produced only by the backend (`barbershop/musicxml.py`, hand-written ElementTree serializer for our constrained subset: two parts — Tenor+Lead on treble-8vb, Bari+Bass on bass clef — two stem-locked voices per staff, lyrics under the Lead). Every edit: frontend mutates score JSON → `POST /api/render` → OSMD re-renders. Note identity across the boundary = deterministic ordering (part, voice, measure, index).
3. **The arranger is pure and audio-free**: input `(melody, chords, key, meter, tempo, lyrics?, spice)` → four-part score. Two-stage Viterbi: chord selection over harmonic slots (hard: melody-note containment, vocabulary legality; soft: tier bias, function preservation, circle-of-fifths reward, dom7-share band), then voicing selection (hard: ranges, tenor≥lead, bass never on 7th, no parallel 8ves; soft: ring, cone spacing, voice-leading smoothness, 7th resolution). Weights in a config object; spice = preset scaling.
4. **API surface** (all stateless): `GET /api/demos`, `POST /api/arrange`, `POST /api/render` (MusicXML), `POST /api/export/midi`, later `POST /api/analyze` (audio, cached by content hash), `POST /api/lyrics/set`, `POST /api/compose`.

## Repository layout

```
backend/
  app/                  # FastAPI layer (routes, schemas) — thin
  barbershop/           # pure music package
    score.py            # score model (pydantic) + tick math
    vocabulary.py       # tiered chord vocabulary + sonority classifier
    arranger/           # harmonize.py, voicing.py, embellish.py, validate.py, transpose.py, config.py
    musicxml.py midi.py
    textset/            # syllabify.py, align.py, phrases.py
    composer/           # prosody.py, affect.py, melodygen.py
    analysis/           # decode.py, beats.py, key.py, melody.py, chords.py, asr.py (lazy imports)
    demos.py            # hardcoded demo tunes
  tests/
  requirements.txt      # pinned
frontend/
  src/                  # React app: store/ (zustand score store + undo), api/, score/ (OSMD wrapper),
                        # playback/ (Tone.js engine, JI tuner), ui/
test_songs/             # public-domain recordings + SOURCES.md
docs/                   # this plan; DESIGN.md lives at repo root
Makefile  run.sh
```

## Milestone order (fixed by SPEC.md; each ends working, committed, pushed)

- [x] **M0 Repo setup** — done (`c7cb2ce`).
- [ ] **M1 Skeleton + demo path** — score model; chord vocabulary + sonority classifier; legality validator suite (written test-first — it doubles as the arranger's quality gate); transposition picker; voicing Viterbi; harmonize Viterbi (v1: given chords + clash substitution, light secondary-dominant reharm by spice); MusicXML serializer; 2–3 hardcoded demos; FastAPI endpoints; Vite/React shell rendering the demo score via OSMD; spice slider + re-arrange.
- [ ] **M2 Playback** — Tone.js engine from score JSON; Transport-scheduled four voices; play/pause/stop/tempo; OSMD cursor sync; per-voice mute/solo/volume; warm pad timbre. (JI toggle lands in M7 per spec; engine designed frequency-first so JI is a drop-in.)
- [ ] **M3 Audio pipeline + test songs** — source/verify 2–4 public-domain recordings (+`SOURCES.md`, trimmed, <25 MB total); ffmpeg decode; librosa beat grid + key; pyin melody (basic-pitch/demucs optional flags); chroma-template chords + Viterbi smoothing; quantization to grid; analysis cache; upload UI + one-click test songs; synthetic-WAV pipeline test.
- [ ] **M4 Editing** — note selection via OSMD graphical mapping; pitch arrows w/ audible feedback; duration keys; delete/insert rest; undo/redo (snapshot stack); MusicXML + MIDI export of the edited score.
- [ ] **M5 Lyrics** — textset engine (CMUdict + g2p-en syllabification/stress, prosodic alignment scorer, melisma/split ops, MusicXML lyric encoding); ASR pathway w/ confidence + doo/dah fallback; pasted-lyric substitution w/ per-phrase fit diagnosis UI; lyric editing (click syllable, edit-all panel).
- [ ] **M6 Lyric-driven composition** — prosody (meter/foot, stanzas, rhyme scheme via phoneme tails); affect (lexicon core, optional Anthropic enrichment behind a flag); affect→parameter mapping (documented in DESIGN.md); seeded constrained melody generation w/ candidate ranking + re-compose; feeds standard arranger.
- [ ] **M7 Polish + README** — embellishments in order: swipes → tags → key changes → bells/echoes (spice-gated, post-validation); just-intonation playback toggle (root-anchored, lead ET-pinned; numeric 4:5:6:7 tests); voice-leading refinement pass; screenshot; friend-proof README verified from a clean clone.

## Testing strategy (per SPEC.md §Quality bar)

Validators are written before the engines they police. The arranger legality suite (ranges, vocabulary, tenor/lead, bass-7th ban, doubling rules, parallel motion, 7th resolution, dom7 share, melody fidelity, final-chord ring) runs at every spice level on every demo input — and later on every composed output. JI gets numeric ratio tests; textset gets syllabification/concordance/round-trip tests; composition gets fixed-seed determinism tests. Audio gets a synthesized-WAV ground-truth test plus by-ear checks on the bundled songs.
