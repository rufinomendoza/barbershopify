"""Harmonization: choose a vocabulary chord for every slot.

The melody is sacrosanct: a structural slot only admits chords containing
the melody's pitch class. The input progression is the prior — leaving it
costs more at low spice. Transitions reward circle-of-fifths motion and
resolved dominants, which is how secondary-dominant chains emerge at high
spice without being scripted.
"""
from __future__ import annotations

from dataclasses import dataclass

from barbershop.score import ChordSpan, KeySig
from barbershop.texture import Slot
from barbershop.vocabulary import CHORDS, chord_pcs
from barbershop.arranger.config import ArrangerConfig

_DOM_FAMILY = ("dom7", "dom9", "aug7", "dom7b5")

# function classes: at phrase boundaries a substitution must keep the
# input chord's function (tonic/stable vs dominant vs diminished)
_STABLE = frozenset({"maj", "maj6", "min", "min6", "min7"})
_DOMINANT = frozenset(_DOM_FAMILY) | {"aug"}
_DIMINISHED = frozenset({"dim7", "halfdim7"})


def _function_class(quality: str) -> frozenset[str]:
    if quality in _DOMINANT:
        return _DOMINANT | {"maj"}  # a dominant may relax to its plain triad
    if quality in _DIMINISHED:
        return _DIMINISHED
    return _STABLE


@dataclass(frozen=True)
class _Candidate:
    root_pc: int
    quality: str


def _static_cost(cand: _Candidate, slot: Slot, cfg: ArrangerConfig, *, forced: bool) -> float:
    inp = slot.chord
    cost = 0.0
    tier = CHORDS[cand.quality].tier
    if tier == 2:
        cost += cfg.w_tier2
    elif tier == 3:
        cost += cfg.w_tier3
    if cand.quality in _DOM_FAMILY:
        cost += cfg.w_dom_bias

    if cand.root_pc == inp.root_pc:
        if cand.quality != inp.quality:
            cost += cfg.w_same_root_upgrade
    else:
        if not forced:
            # leaving a viable input chord is a stylistic choice, priced by spice;
            # when the melody clashes, every candidate is a substitute — no charge
            cost += cfg.w_substitution
        shared = len(chord_pcs(cand.root_pc, cand.quality) & chord_pcs(inp.root_pc, inp.quality))
        cost += cfg.w_overlap * max(0, 3 - shared)
    return cost


def _transition_cost(prev: _Candidate, cur: _Candidate, cfg: ArrangerConfig) -> float:
    cost = 0.0
    same_chord = prev == cur
    descending_fifth = (prev.root_pc - 7) % 12 == cur.root_pc
    if descending_fifth and not same_chord:
        cost -= cfg.w_circle
    if prev.quality in _DOM_FAMILY and not same_chord:
        if descending_fifth:
            cost -= cfg.w_dom_resolve
        else:
            cost += cfg.w_dom_hang
    return cost


def _candidates(
    slot: Slot, cfg: ArrangerConfig, *, boundary: bool, final: bool = False
) -> list[tuple[_Candidate, float]]:
    inp = slot.chord
    if not slot.structural:
        return [(_Candidate(inp.root_pc, inp.quality), 0.0)]

    melody_pc = slot.melody_midi % 12
    forced = melody_pc not in chord_pcs(inp.root_pc, inp.quality)
    allowed = _function_class(inp.quality) if boundary else None
    if final:
        allowed = frozenset({"maj"})  # the last chord must be a major triad
    cands: list[_Candidate] = []
    for root in range(12):
        if boundary and root != inp.root_pc:
            continue  # keep the skeleton's function at phrase boundaries
        interval = (melody_pc - root) % 12
        for quality, cdef in CHORDS.items():
            if allowed is not None and quality not in allowed:
                continue
            if interval in cdef.intervals:
                cands.append(_Candidate(root, quality))
    if not cands:  # boundary fallback: melody can't sit on the input root
        return _candidates(slot, cfg, boundary=False)

    scored = [(c, _static_cost(c, slot, cfg, forced=forced)) for c in cands]
    scored.sort(key=lambda item: item[1])
    return scored[: cfg.max_chord_candidates]


def harmonize(slots: list[Slot], key: KeySig, cfg: ArrangerConfig) -> list[ChordSpan]:
    """Viterbi over per-slot chord candidates; returns one ChordSpan per slot."""
    if not slots:
        return []
    columns = []
    for i, slot in enumerate(slots):
        final = i == len(slots) - 1
        boundary = i == 0 or final or slot.phrase_end
        col = _candidates(slot, cfg, boundary=boundary, final=final)
        if not col:
            raise ValueError(f"no legal chord for slot at tick {slot.onset}")
        columns.append(col)

    best = [c for _, c in columns[0]]
    back: list[list[int]] = [[-1] * len(columns[0])]
    for i in range(1, len(columns)):
        costs, pointers = [], []
        for cand, static in columns[i]:
            j_best, c_best = 0, float("inf")
            for j, (prev, _) in enumerate(columns[i - 1]):
                c = best[j] + _transition_cost(prev, cand, cfg)
                if c < c_best:
                    c_best, j_best = c, j
            costs.append(c_best + static)
            pointers.append(j_best)
        best = costs
        back.append(pointers)

    idx = min(range(len(best)), key=lambda j: best[j])
    path = [idx]
    for i in range(len(columns) - 1, 0, -1):
        idx = back[i][idx]
        path.append(idx)
    path.reverse()

    return [
        ChordSpan(
            onset=slot.onset,
            duration=slot.duration,
            root_pc=columns[i][j][0].root_pc,
            quality=columns[i][j][0].quality,
        )
        for i, (slot, j) in enumerate(zip(slots, path))
    ]
