"""Rule-based, seeded melody generation over a phrase plan.

Each text line becomes a 4-bar phrase: a chord template (by cadence
role and mode), a rhythm fitted to the syllable count (quarters by
default, eighth-pairs to absorb extra syllables, a sustained cadence
note), and K candidate pitch contours scored for stress concordance,
contour balance (peak near the golden section), chord-tone placement,
and singability. Generation is one-note-per-syllable, so lyrics attach
by construction.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from barbershop.score import ChordSpan, Lyric, Note, Syllabic
from barbershop.textset.syllabify import Syllable
from barbershop.vocabulary import chord_pcs

BAR = 1920  # 4/4
PHRASE_BARS = 4
CENTER = 62

_MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
_MINOR_SCALE = [9, 11, 0, 2, 4, 5, 7]  # A natural minor pcs

# templates: (root_pc, quality) per bar, C major / A minor relative
_TEMPLATES = {
    ("major", "open"): [(0, "maj"), (5, "maj"), (0, "maj"), (7, "maj")],
    ("major", "open2"): [(0, "maj"), (9, "min"), (2, "min"), (7, "maj")],
    ("major", "close"): [(0, "maj"), (5, "maj"), (7, "maj"), (0, "maj")],
    ("minor", "open"): [(9, "min"), (5, "maj"), (2, "min"), (4, "maj")],
    ("minor", "open2"): [(9, "min"), (2, "min"), (11, "halfdim7"), (4, "maj")],
    ("minor", "close"): [(9, "min"), (11, "halfdim7"), (4, "maj"), (9, "min")],
}

# cadence scale degrees (pc relative to C-major frame)
_CADENCE_PC = {
    ("major", "close"): 0,  # tonic
    ("major", "open"): 7,  # fifth (half cadence)
    ("minor", "close"): 9,
    ("minor", "open"): 4,
}


@dataclass
class PhrasePlan:
    syllables: list[Syllable]
    role: str  # open / close
    cadence_pc: int | None  # forced cadence pitch class (rhyme matching)
    chords: list[tuple[int, str]]  # per-bar


def rhythm_for(n_sylls: int, first_unstressed: bool) -> list[tuple[int, int]]:
    """(onset_tick, duration) within a 4-bar phrase, one per syllable."""
    offset_beats = 1 if first_unstressed else 0
    total_beats = PHRASE_BARS * 4
    slots: list[tuple[float, float]] = []
    t = float(offset_beats)
    remaining = n_sylls
    while remaining > 0:
        beats_left = total_beats - t
        if remaining == 1:
            slots.append((t, max(0.5, min(4.0, beats_left))))
            remaining = 0
        elif beats_left <= remaining:  # compress into eighth pairs
            slots.append((t, 0.5))
            slots.append((t + 0.5, 0.5))
            t += 1.0
            remaining -= 2
        else:
            dur = 2.0 if beats_left - remaining >= 2 and remaining <= 4 else 1.0
            slots.append((t, dur))
            t += dur
            remaining -= 1
    return [(int(b * 480), int(d * 480)) for b, d in slots]


def _strength(onset: int) -> float:
    beat = (onset % BAR) / 480
    if beat == 0.0:
        return 3.0
    if beat == 2.0:
        return 2.0
    if beat == int(beat):
        return 1.0
    return 0.0


def _scale(mode: str, chord: tuple[int, str]) -> list[int]:
    pcs = list(_MAJOR_SCALE if mode == "major" else _MINOR_SCALE)
    if mode == "minor" and chord[0] == 4:  # dominant in A minor: raise G to G#
        pcs = [p for p in pcs if p != 7] + [8]
    return pcs


def _candidate(
    plan: PhrasePlan,
    rhythm: list[tuple[int, int]],
    mode: str,
    span: int,
    rng: random.Random,
) -> list[int]:
    n = len(rhythm)
    peak_idx = max(1, min(n - 2, round(0.618 * (n - 1)))) if n > 2 else max(0, n - 1)
    lo, hi = CENTER - span // 2, CENTER + span - span // 2
    pitches: list[int] = []
    current = CENTER + rng.choice([-2, 0, 3])
    for i, (onset, _dur) in enumerate(rhythm):
        bar = min(onset // BAR, PHRASE_BARS - 1)
        chord = plan.chords[bar]
        tones = chord_pcs(chord[0], chord[1])
        scale = _scale(mode, chord)
        if i == n - 1 and plan.cadence_pc is not None:
            target_pc = plan.cadence_pc
            options = [p for p in range(lo, hi + 1) if p % 12 == target_pc]
            pitch = min(options, key=lambda p: abs(p - current)) if options else current
        else:
            going_up = i < peak_idx
            strong = _strength(onset) >= 1.0
            allowed_pcs = tones if strong else set(scale) | tones
            step_options = [
                p
                for p in range(max(lo, current - 7), min(hi, current + 7) + 1)
                if p % 12 in allowed_pcs and p != current
            ]
            if not step_options:
                step_options = [current]
            direction = 1 if going_up else -1
            preferred = [p for p in step_options if (p - current) * direction > 0]
            pool = preferred or step_options
            pool.sort(key=lambda p: abs(p - current))
            pitch = pool[0] if rng.random() < 0.7 else rng.choice(pool[: max(1, len(pool) // 2)])
        pitch = max(lo, min(hi, pitch))
        pitches.append(pitch)
        current = pitch
    return pitches


def _score(pitches: list[int], rhythm: list[tuple[int, int]], plan: PhrasePlan) -> float:
    n = len(pitches)
    cost = 0.0
    # stress concordance
    for (onset, _), syll, pitch in zip(rhythm, plan.syllables, pitches):
        s = _strength(onset)
        if syll.stress == 1 and s < 1.0:
            cost += 1.0
        if syll.stress == 0 and s >= 3.0:
            cost += 0.4
    # contour balance: peak near golden section
    peak = max(range(n), key=lambda i: pitches[i])
    cost += abs(peak / max(1, n - 1) - 0.618) * 3.0
    # leaps
    for a, b in zip(pitches, pitches[1:]):
        d = abs(a - b)
        if d > 7:
            cost += 1.5
        if d in (6, 10, 11):
            cost += 2.0
    # static lines are boring
    if len(set(pitches)) <= 2:
        cost += 3.0
    return cost


def generate_phrase(
    plan: PhrasePlan, mode: str, span: int, rng: random.Random, candidates: int = 8
) -> tuple[list[tuple[int, int]], list[int]]:
    first_unstressed = bool(plan.syllables) and plan.syllables[0].stress == 0
    rhythm = rhythm_for(len(plan.syllables), first_unstressed)
    best, best_cost = None, float("inf")
    for _ in range(candidates):
        pitches = _candidate(plan, rhythm, mode, span, rng)
        cost = _score(pitches, rhythm, plan)
        if cost < best_cost:
            best, best_cost = pitches, cost
    assert best is not None
    return rhythm, best


def notes_and_chords(
    plans: list[PhrasePlan], mode: str, span: int, rng: random.Random
) -> tuple[list[Note], list[ChordSpan]]:
    notes: list[Note] = []
    chords: list[ChordSpan] = []
    for p, plan in enumerate(plans):
        base = p * PHRASE_BARS * BAR
        rhythm, pitches = generate_phrase(plan, mode, span, rng)
        for (onset, dur), pitch, syll in zip(rhythm, pitches, plan.syllables):
            if syll.word_begin and syll.word_end:
                syllabic = Syllabic.single
            elif syll.word_begin:
                syllabic = Syllabic.begin
            elif syll.word_end:
                syllabic = Syllabic.end
            else:
                syllabic = Syllabic.middle
            notes.append(
                Note(
                    onset=base + onset,
                    duration=dur,
                    midi=pitch,
                    lyric=Lyric(text=syll.text, syllabic=syllabic),
                )
            )
        for bar, (root, quality) in enumerate(plan.chords):
            chords.append(
                ChordSpan(onset=base + bar * BAR, duration=BAR, root_pc=root, quality=quality)
            )
    return notes, chords
