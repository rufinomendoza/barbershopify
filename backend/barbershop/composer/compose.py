"""Lyric-driven composition: poem -> (melody, progression, lyrics).

The affect -> musical-parameter mapping (documented in DESIGN.md):
valence picks mode (and picardy vs minor ending, by the closing
stanza's sentiment); arousal maps to tempo (60-132 BPM), melodic span,
and — at high arousal — cadential harmonic-rhythm acceleration. The
rhyme scheme assigns cadence roles (the second occurrence of a rhyme
letter closes its couplet) and rhyming lines share their cadence tone.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from barbershop.arranger.arrange import ArrangeInput
from barbershop.composer.affect import Affect, analyze_affect
from barbershop.composer.melodygen import _TEMPLATES, PhrasePlan, notes_and_chords
from barbershop.composer.prosody import Prosody, analyze_prosody
from barbershop.score import KeySig, TimeSig


@dataclass
class CompositionResult:
    input: ArrangeInput
    prosody: Prosody
    affect: Affect
    meta: dict


def _tempo(arousal: float) -> float:
    return float(max(60, min(132, round(92 + arousal * 36))))


def compose(text: str, *, seed: int = 0, title: str = "Untitled") -> CompositionResult:
    prosody = analyze_prosody(text)
    affect = analyze_affect(text)
    if not prosody.lines:
        raise ValueError("no usable lines of text")

    mode = "minor" if affect.valence < -0.15 else "major"
    tempo = _tempo(affect.arousal)
    span = 12 + round((affect.arousal + 1) * 2.5)  # melodic width in semitones
    rng = random.Random(seed)

    # cadence roles from the rhyme scheme: a rhyme letter's second
    # occurrence closes the couplet it completes
    plans: list[PhrasePlan] = []
    cadence_by_rhyme: dict[str, int] = {}
    ending_valence = affect.per_stanza[-1][0] if affect.per_stanza else affect.valence
    for stanza in prosody.stanzas:
        seen: dict[str, int] = {}
        for line, letter in zip(stanza.lines, stanza.rhyme_scheme):
            seen[letter] = seen.get(letter, 0) + 1
            role = "close" if seen[letter] >= 2 else "open"
            template_key = (mode, role)
            if role == "open" and rng.random() < 0.4:
                template_key = (mode, "open2")
            chords = list(_TEMPLATES[template_key])
            cadence_pc = _cadence_pc(mode, role, letter, cadence_by_rhyme)
            plans.append(
                PhrasePlan(
                    syllables=line.syllables,
                    role=role,
                    cadence_pc=cadence_pc,
                    chords=chords,
                )
            )

    # the final line always closes; picardy decided by the ending sentiment
    plans[-1] = PhrasePlan(
        syllables=plans[-1].syllables,
        role="close",
        cadence_pc=9 if mode == "minor" else 0,
        chords=list(_TEMPLATES[(mode, "close")]),
    )
    if mode == "minor" and ending_valence > 0.1:
        chords = list(plans[-1].chords)
        chords[-1] = (9, "maj")  # picardy lift
        plans[-1] = PhrasePlan(
            syllables=plans[-1].syllables, role="close", cadence_pc=9, chords=chords
        )

    melody, chord_spans = notes_and_chords(plans, mode, span, rng)

    # cadential acceleration at higher arousal: the dominant bar of a
    # closing phrase gets its own predominant in the first half
    if affect.arousal > 0.25:
        from barbershop.score import ChordSpan

        predominant = (2, "min") if mode == "major" else (11, "halfdim7")
        accelerated: list[ChordSpan] = []
        for span_ in chord_spans:
            bar_in_phrase = (span_.onset // 1920) % 4
            phrase_idx = span_.onset // (4 * 1920)
            splittable = (
                phrase_idx < len(plans)
                and plans[phrase_idx].role == "close"
                and bar_in_phrase == 2
                and span_.duration == 1920  # only whole dominant bars split
            )
            if splittable:
                accelerated.append(
                    ChordSpan(
                        onset=span_.onset,
                        duration=960,
                        root_pc=predominant[0],
                        quality=predominant[1],
                    )
                )
                accelerated.append(
                    ChordSpan(
                        onset=span_.onset + 960,
                        duration=960,
                        root_pc=span_.root_pc,
                        quality=span_.quality,
                    )
                )
            else:
                accelerated.append(span_)
        chord_spans = accelerated

    inp = ArrangeInput(
        title=title,
        # composed in the C-major / A-minor frame; the arranger transposes
        key=KeySig(fifths=0, mode=mode),
        time=TimeSig(beats=4, beat_type=4),
        tempo=tempo,
        melody=melody,
        chords=chord_spans,
    )
    return CompositionResult(
        input=inp,
        prosody=prosody,
        affect=affect,
        meta={
            "mode": mode,
            "tempo": tempo,
            "foot": prosody.dominant_foot,
            "schemes": [s.rhyme_scheme for s in prosody.stanzas],
            "valence": round(affect.valence, 2),
            "arousal": round(affect.arousal, 2),
            "span": span,
        },
    )


def _cadence_pc(mode: str, role: str, letter: str, memo: dict[str, int]) -> int:
    """Rhyming lines answer each other with the same cadence tone."""
    key = f"{letter}:{role}"
    if key not in memo:
        from barbershop.composer.melodygen import _CADENCE_PC

        memo[key] = _CADENCE_PC[(mode, role)]
    return memo[key]
