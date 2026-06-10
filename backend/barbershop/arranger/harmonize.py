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

    if slot.swipe and cand.root_pc == inp.root_pc and cand.quality == inp.quality:
        cost += 1.5  # a swipe slot wants the harmony to move under the hold

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


def _seventh_resolution_feasible(prev: _Candidate, cur: _Candidate, slot: Slot) -> bool:
    """Joint chord-voicing feasibility: a chord with a true 7th may only be
    followed by a chord where that 7th can resolve down by step, hold as a
    common tone (predominant 7ths), or hand its resolution to the lead."""
    if prev.quality == "dim7":  # symmetric, no functional 7th
        return True
    seventh_iv = next(
        (iv for iv, d in CHORDS[prev.quality].degrees.items() if d == "seventh"), None
    )
    if seventh_iv is None:
        return True  # triads/6ths: nothing to resolve
    seventh_pc = (prev.root_pc + seventh_iv) % 12
    next_pcs = chord_pcs(cur.root_pc, cur.quality)
    targets = {(seventh_pc - 1) % 12, (seventh_pc - 2) % 12} & next_pcs
    if targets:
        return True  # a trio voice can step down (or transfer to the lead)
    if prev.quality in ("min7", "halfdim7") and seventh_pc in next_pcs:
        return True  # common-tone hold
    return False


def _transition_cost(
    prev: _Candidate, cur: _Candidate, prev_slot: Slot, slot: Slot, cfg: ArrangerConfig
) -> float:
    cost = 0.0
    same_chord = prev == cur
    if not same_chord and not _seventh_resolution_feasible(prev, cur, slot):
        cost += 50.0  # no legal voice-leading exists; only as a last resort
    descending_fifth = (prev.root_pc - 7) % 12 == cur.root_pc
    if descending_fifth and not same_chord:
        cost -= cfg.w_circle
    if prev.quality in _DOM_FAMILY and not same_chord:
        if descending_fifth:
            cost -= cfg.w_dom_resolve
        else:
            cost += cfg.w_dom_hang

    # parallel-fifth trap: melody on the 5th of two different chords forces
    # the bass (on the root, the 5th being taken) into parallel motion with
    # the lead — unescapable on 4-tone chords, which forbid doublings
    if not same_chord and len(CHORDS[cur.quality].intervals) >= 4:
        prev_fifth = next(
            (iv for iv, d in CHORDS[prev.quality].degrees.items() if d == "fifth"), None
        )
        cur_fifth = next(
            (iv for iv, d in CHORDS[cur.quality].degrees.items() if d == "fifth"), None
        )
        if (
            prev_fifth is not None
            and cur_fifth is not None
            and slot.melody_midi > prev_slot.melody_last_midi  # bass must chase upward
            and (prev_slot.melody_midi - prev.root_pc) % 12 == prev_fifth
            and (slot.melody_midi - cur.root_pc) % 12 == cur_fifth
        ):
            cost += 6.0
    return cost


def _candidates(
    slot: Slot, cfg: ArrangerConfig, *, boundary: bool, final: bool = False, mode: str = "major"
) -> list[tuple[_Candidate, float]]:
    inp = slot.chord
    if not slot.structural:
        return [(_Candidate(inp.root_pc, inp.quality), 0.0)]

    melody_pc = slot.melody_midi % 12
    forced = melody_pc not in chord_pcs(inp.root_pc, inp.quality)
    allowed = _function_class(inp.quality) if boundary else None
    if final:
        # the last chord must be a stable triad: major always; minor keys
        # may also end minor (picardy is the composer's choice). If the
        # melody can't sit in one on the input root, try other roots.
        final_ok = frozenset({"maj"}) if mode == "major" else frozenset({"maj", "min"})
        fits_input = any(
            (melody_pc - inp.root_pc) % 12 in CHORDS[q].intervals for q in final_ok
        )
        if not fits_input:
            return [
                (_Candidate(melody_pc, "maj"), 0.0),  # melody as root
                (_Candidate((melody_pc - 4) % 12, "maj"), 0.5),  # as third
                (_Candidate((melody_pc - 7) % 12, "maj"), 0.5),  # as fifth
            ]
        allowed = final_ok
    cands: list[_Candidate] = []
    for root in range(12):
        if boundary and root != inp.root_pc:
            continue  # keep the skeleton's function at phrase boundaries
        interval = (melody_pc - root) % 12
        for quality, cdef in CHORDS.items():
            if allowed is not None and quality not in allowed:
                continue
            # dom9 is voiced rootless or 5th-omitted, "only when the melody
            # forces it": with the melody on root or 5th the bass has no
            # legal tone left, so only offer it for melody on 9th/3rd/7th
            if quality == "dom9" and interval not in (2, 4, 10):
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
        col = _candidates(slot, cfg, boundary=boundary, final=final, mode=key.mode)
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
                c = best[j] + _transition_cost(prev, cand, slots[i - 1], slots[i], cfg)
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
