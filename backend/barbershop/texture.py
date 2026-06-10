"""Texture segmentation: melody + chord annotations -> harmonic slots.

A slot is one vertical the trio sings: it starts at a structural melody
attack or at a chord change under a sounding note, and lasts until the
next slot or until the lead goes silent. Sub-threshold melody notes
(filigree) never start slots — the trio sustains through them.
"""
from __future__ import annotations

from dataclasses import dataclass

from barbershop.score import ChordSpan, Note


@dataclass
class Slot:
    onset: int
    duration: int
    melody_midi: int  # sounding melody pitch at slot start
    melody_max_midi: int  # highest lead pitch sounding during the slot
    melody_min_midi: int  # lowest lead pitch sounding during the slot
    melody_last_midi: int  # lead pitch sounding just before slot end
    melody_attack: bool  # lead attacks at slot start (False = chord moves under a hold)
    chord: ChordSpan
    structural: bool  # melody pitch must be a chord tone of this slot's chord
    phrase_end: bool
    swipe: bool = False  # harmony should move under the held lead here

    @property
    def end(self) -> int:
        return self.onset + self.duration


def _sounding_spans(melody: list[Note]) -> list[tuple[int, int]]:
    """Merge contiguous melody notes into continuous sounding spans."""
    spans: list[tuple[int, int]] = []
    for note in melody:
        if spans and note.onset <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(spans[-1][1], note.end))
        else:
            spans.append((note.onset, note.end))
    return spans


def _chord_at(chords: list[ChordSpan], tick: int) -> ChordSpan:
    current = chords[0]
    for c in chords:
        if c.onset <= tick:
            current = c
        else:
            break
    return current


def segment(melody: list[Note], chords: list[ChordSpan], threshold: int) -> list[Slot]:
    melody = sorted(melody, key=lambda n: n.onset)
    chords = sorted(chords, key=lambda c: c.onset)
    spans = _sounding_spans(melody)

    def span_of(tick: int) -> tuple[int, int] | None:
        for s in spans:
            if s[0] <= tick < s[1]:
                return s
        return None

    def note_at(tick: int) -> Note | None:
        for n in melody:
            if n.onset <= tick < n.end:
                return n
        return None

    # Slot boundaries: structural attacks, plus chord changes inside sounding spans.
    boundaries: dict[int, bool] = {}  # tick -> is_melody_attack
    for n in melody:
        if n.duration >= threshold:
            boundaries[n.onset] = True
    for c in chords:
        if span_of(c.onset) is not None and c.onset not in boundaries:
            note = note_at(c.onset)
            if note is not None and note.onset < c.onset:
                boundaries[c.onset] = False

    ticks = sorted(boundaries)
    slots: list[Slot] = []
    for i, t in enumerate(ticks):
        span = span_of(t)
        if span is None:
            continue
        next_t = ticks[i + 1] if i + 1 < len(ticks) else None
        end = span[1] if next_t is None or next_t >= span[1] else next_t
        note = note_at(t)
        assert note is not None
        sounding = [n for n in melody if n.onset < end and n.end > t]
        peak = max(n.midi for n in sounding)
        floor = min(n.midi for n in sounding)
        last = max(sounding, key=lambda n: n.onset).midi
        slots.append(
            Slot(
                onset=t,
                duration=end - t,
                melody_midi=note.midi,
                melody_max_midi=peak,
                melody_min_midi=floor,
                melody_last_midi=last,
                melody_attack=boundaries[t],
                chord=_chord_at(chords, t),
                structural=note.duration >= threshold,
                phrase_end=note.end == span[1],
            )
        )
    return slots
