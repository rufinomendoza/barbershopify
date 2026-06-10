"""Melody phrase detection: rests delimit phrases (v1)."""
from __future__ import annotations

from barbershop.score import Note

GAP = 120  # any silence of a 16th or more breaks the phrase


def split_phrases(melody: list[Note]) -> list[list[Note]]:
    phrases: list[list[Note]] = []
    for note in sorted(melody, key=lambda n: n.onset):
        if phrases and note.onset - phrases[-1][-1].end < GAP:
            phrases[-1].append(note)
        else:
            phrases.append([note])
    return phrases
