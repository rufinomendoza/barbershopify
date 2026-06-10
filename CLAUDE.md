# barbershopify — notes for Claude sessions

**Read `SPEC.md` first.** It is the canonical specification for this project, committed verbatim
from the original brief. Re-read the relevant sections at the start of each milestone and whenever
resuming work in a fresh session. When memory and spec disagree, the spec wins. If the spec changes
by agreement mid-project, update `SPEC.md` in the same commit as the change.

Design decisions and their rationale live in `DESIGN.md` — keep it current as non-obvious choices
are made.

## Project shape

- `backend/` — Python 3.12 / FastAPI. Audio analysis, arrangement engine, MusicXML generation.
  The arrangement engine (`backend/arranger/`) is a pure module independent of the web layer:
  it consumes (melody, chord progression, lyrics) and produces a four-part TTBB score. Test it
  without audio or HTTP.
- `frontend/` — browser UI: score rendering, playback, editing.
- `test_songs/` — bundled public-domain recordings + `SOURCES.md` provenance.

## Working agreements

- Milestone order is defined at the bottom of `SPEC.md`; get each working end-to-end before
  moving on. Commit at meaningful checkpoints; push after each milestone.
- Remote: `https://github.com/derekhaase259/barbershopify` (private, already exists — never
  recreate it or change its visibility).
- Pin dependencies.
- The arrangement engine is rule-based, not ML. Its unit tests (legality validators, voice-leading
  checks, range compliance) are the project's quality bar — run `pytest` in `backend/` before
  declaring arranger work done.
- Run the app and look at / listen to actual output before calling a milestone complete.
