"""Affect analysis: valence/arousal from a deterministic lexicon core.

A compact VAD-style lexicon with negation handling keeps this testable
and offline. An optional Anthropic enrichment can refine it when an API
key is configured; the lexicon remains the fallback and the test target.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# word -> (valence, arousal), both in [-1, 1]
_LEXICON: dict[str, tuple[float, float]] = {
    # negative, low arousal
    "sad": (-0.8, -0.4), "grave": (-0.7, -0.5), "sleep": (-0.1, -0.8),
    "mourn": (-0.9, -0.3), "weep": (-0.8, -0.2), "tears": (-0.7, -0.2),
    "lonely": (-0.8, -0.5), "alone": (-0.6, -0.5), "cold": (-0.5, -0.3),
    "gray": (-0.4, -0.5), "grey": (-0.4, -0.5), "dying": (-0.9, -0.3),
    "death": (-0.9, -0.2), "dead": (-0.9, -0.3), "silence": (-0.3, -0.8),
    "bitter": (-0.7, 0.0), "dark": (-0.5, -0.3), "winter": (-0.3, -0.4),
    "sorrow": (-0.9, -0.3), "weary": (-0.6, -0.7), "fade": (-0.4, -0.5),
    "lost": (-0.6, -0.2), "goodbye": (-0.5, -0.2), "ache": (-0.7, -0.1),
    "rain": (-0.3, -0.3), "still": (-0.1, -0.7), "slow": (-0.1, -0.7),
    "empty": (-0.6, -0.5), "broken": (-0.7, -0.1), "cry": (-0.7, 0.0),
    # negative, high arousal
    "storm": (-0.4, 0.7), "rage": (-0.8, 0.9), "fear": (-0.8, 0.6),
    "scream": (-0.7, 0.9), "fire": (-0.2, 0.8), "fight": (-0.5, 0.8),
    "angry": (-0.7, 0.7), "wild": (0.1, 0.8),
    # positive, low arousal
    "calm": (0.5, -0.7), "peace": (0.7, -0.6), "gentle": (0.6, -0.5),
    "sweet": (0.7, -0.2), "warm": (0.6, -0.3), "home": (0.6, -0.3),
    "tender": (0.6, -0.4), "dream": (0.4, -0.5), "moon": (0.3, -0.5),
    "soft": (0.5, -0.5), "rest": (0.4, -0.7),
    # positive, high arousal
    "joy": (0.9, 0.5), "dance": (0.7, 0.7), "laugh": (0.8, 0.6),
    "sing": (0.7, 0.5), "song": (0.6, 0.3), "bright": (0.7, 0.3),
    "sun": (0.6, 0.2), "happy": (0.9, 0.4), "love": (0.9, 0.3),
    "celebrate": (0.8, 0.8), "shine": (0.7, 0.3), "run": (0.2, 0.7),
    "play": (0.6, 0.5), "summer": (0.5, 0.3), "morning": (0.4, 0.1),
    "burst": (0.3, 0.8), "heart": (0.4, 0.2), "shout": (0.3, 0.8),
    "glad": (0.8, 0.3), "smile": (0.8, 0.2), "spring": (0.5, 0.3),
}

_NEGATORS = {"not", "no", "never", "without", "ain't", "cannot", "can't"}


@dataclass
class Affect:
    valence: float
    arousal: float
    per_stanza: list[tuple[float, float]]

    @property
    def arc(self) -> float:
        """Positive = brightening toward the end."""
        if len(self.per_stanza) < 2:
            return 0.0
        return self.per_stanza[-1][0] - self.per_stanza[0][0]


def _score_block(text: str) -> tuple[float, float]:
    words = re.findall(r"[a-z']+", text.lower())
    valences: list[float] = []
    arousals: list[float] = []
    negate_window = 0
    for word in words:
        if word in _NEGATORS:
            negate_window = 3
            continue
        hit = _LEXICON.get(word)
        if hit:
            v, a = hit
            if negate_window > 0:
                v = -v * 0.8  # negation flips (and slightly dampens) valence
            valences.append(v)
            arousals.append(a)
        if negate_window > 0:
            negate_window -= 1
    if not valences:
        return 0.0, 0.0
    return sum(valences) / len(valences), sum(arousals) / len(arousals)


def analyze_affect(text: str) -> Affect:
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()] or [text]
    per_stanza = [_score_block(b) for b in blocks]
    v_all, a_all = _score_block(text)
    return Affect(valence=v_all, arousal=a_all, per_stanza=per_stanza)
