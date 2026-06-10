"""Prosodic analysis of pasted text: feet, stanzas, rhyme schemes."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pronouncing

from barbershop.textset.syllabify import Syllable, syllabify_line

_FEET = {
    "iambic": [0, 1],
    "trochaic": [1, 0],
    "anapestic": [0, 0, 1],
    "dactylic": [1, 0, 0],
}


@dataclass
class Line:
    text: str
    syllables: list[Syllable]
    rhyme_tail: str  # phoneme tail of the final word ('' if unknown)


@dataclass
class Stanza:
    lines: list[Line]
    rhyme_scheme: str  # e.g. "AABB", "ABAB", "AABA"


@dataclass
class Prosody:
    stanzas: list[Stanza]
    dominant_foot: str  # iambic / trochaic / anapestic / dactylic / free

    @property
    def lines(self) -> list[Line]:
        return [ln for st in self.stanzas for ln in st.lines]


def _rhyme_tail(word: str) -> str:
    cleaned = re.sub(r"[^a-z']", "", word.lower())
    phones = pronouncing.phones_for_word(cleaned)
    if phones:
        return pronouncing.rhyming_part(phones[0])
    # OOV fallback: final vowel-run + trailing consonants of the spelling
    m = re.search(r"[aeiouy]+[^aeiouy]*$", cleaned)
    return m.group(0) if m else cleaned[-2:]


def _scheme(lines: list[Line]) -> str:
    letters: list[str] = []
    seen: dict[str, str] = {}
    for line in lines:
        tail = line.rhyme_tail
        match = None
        for known, letter in seen.items():
            if tail and tail == known:
                match = letter
                break
        if match is None:
            match = chr(ord("A") + len(set(seen.values())))
            seen[tail or f"?{len(letters)}"] = match
        letters.append(match)
    return "".join(letters)


def _dominant_foot(lines: list[Line]) -> str:
    stresses: list[int] = []
    for line in lines:
        stresses.extend(1 if s.stress >= 1 else 0 for s in line.syllables)
        stresses.append(-1)  # line boundary sentinel
    best, best_score = "free", 0.62
    for name, pattern in _FEET.items():
        hits = total = 0
        pos = 0
        for s in stresses:
            if s < 0:
                pos = 0  # feet restart at line boundaries
                continue
            if s == pattern[pos % len(pattern)]:
                hits += 1
            total += 1
            pos += 1
        score = hits / total if total else 0.0
        if score > best_score:
            best, best_score = name, score
    return best


def analyze_prosody(text: str) -> Prosody:
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    stanzas: list[Stanza] = []
    for block in blocks:
        lines = []
        for raw in block.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            words = raw.split()
            lines.append(
                Line(
                    text=raw,
                    syllables=syllabify_line(raw),
                    rhyme_tail=_rhyme_tail(words[-1]) if words else "",
                )
            )
        if lines:
            stanzas.append(Stanza(lines=lines, rhyme_scheme=_scheme(lines)))
    return Prosody(stanzas=stanzas, dominant_foot=_dominant_foot([l for s in stanzas for l in s.lines]))
