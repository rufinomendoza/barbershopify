"""Syllabification and lexical stress.

Counts and stress come from the CMU Pronouncing Dictionary (via
`pronouncing`); the *written* split comes from pyphen's hyphenation
dictionary, reconciled to the CMU count. Out-of-vocabulary words (user
lyrics are full of them) fall back to a deterministic vowel-group split
with alternating-stress guess — offline-safe by design (DESIGN.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pronouncing
import pyphen

_PYPHEN = pyphen.Pyphen(lang="en_US")
_VOWEL_RUN = re.compile(r"[aeiouy]+", re.IGNORECASE)
_OPEN_VOWEL_PHONES = {"AA", "AE", "AH", "AO", "OW", "UW", "AY", "AW", "EY"}


@dataclass
class Syllable:
    text: str
    stress: int  # 1 primary, 2 secondary, 0 unstressed
    word_begin: bool = True
    word_end: bool = True
    open_vowel: bool = False
    word: str = ""


def _clean(word: str) -> str:
    return re.sub(r"[^a-z']", "", word.lower())


def _stresses_and_vowels(word: str) -> tuple[list[int], list[str]] | None:
    phones = pronouncing.phones_for_word(word)
    if not phones:
        return None
    stresses: list[int] = []
    vowels: list[str] = []
    for phone in phones[0].split():
        if phone[-1].isdigit():
            stresses.append(int(phone[-1]))
            vowels.append(phone[:-1])
    return (stresses, vowels) if stresses else None


def _written_split(word: str, n: int) -> list[str]:
    """Split the written word into n singable chunks."""
    if n <= 1:
        return [word]
    parts = _PYPHEN.inserted(word).split("-")
    if len(parts) == n:
        return parts
    # reconcile: split at vowel-group boundaries to match the CMU count
    runs = list(_VOWEL_RUN.finditer(word))
    if len(runs) >= n:
        cuts = []
        for i in range(n - 1):
            cuts.append((runs[i].end() + runs[i + 1].start() + 1) // 2)
        out, prev = [], 0
        for c in cuts:
            out.append(word[prev:c])
            prev = c
        out.append(word[prev:])
        return [p for p in out if p] or [word]
    # last resort: equal character chunks
    step = max(1, len(word) // n)
    out = [word[i * step : (i + 1) * step] for i in range(n - 1)]
    out.append(word[(n - 1) * step :])
    return [p for p in out if p] or [word]


def syllabify_word(word: str) -> list[Syllable]:
    cleaned = _clean(word)
    if not cleaned:
        return []
    looked_up = _stresses_and_vowels(cleaned)
    if looked_up is not None:
        stresses, vowels = looked_up
    else:
        runs = _VOWEL_RUN.findall(cleaned)
        n = max(1, len(runs))
        # alternating-stress guess, primary first
        stresses = [1 if i % 2 == 0 else 0 for i in range(n)]
        vowels = ["AH"] * n
    texts = _written_split(cleaned, len(stresses))
    # pad/trim defensively: counts must agree
    while len(texts) < len(stresses):
        texts.append(texts[-1])
    texts = texts[: len(stresses)]
    out = []
    for i, (text, stress, vowel) in enumerate(zip(texts, stresses, vowels)):
        out.append(
            Syllable(
                text=text,
                stress=stress,
                word_begin=(i == 0),
                word_end=(i == len(stresses) - 1),
                open_vowel=vowel in _OPEN_VOWEL_PHONES,
                word=cleaned,
            )
        )
    return out


def syllabify_line(line: str) -> list[Syllable]:
    out: list[Syllable] = []
    for word in line.split():
        out.extend(syllabify_word(word))
    return out
