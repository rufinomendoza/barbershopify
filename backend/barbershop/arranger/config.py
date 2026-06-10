"""Arranger configuration: voice ranges, cost weights, spice presets.

All soft-constraint weights live here so the optimizer's taste is tunable
in one place. The user-facing spice dial (1-5) selects scaled presets in
the harmonization stage; voicing weights are largely style-invariant.
"""
from __future__ import annotations

from dataclasses import dataclass

# Sounding-pitch ranges (MIDI), per SPEC: tenor G3-C5, lead A2-G4,
# bari A2-G4, bass E2-C4.
RANGES: dict[str, tuple[int, int]] = {
    "tenor": (55, 72),
    "lead": (45, 67),
    "bari": (45, 67),
    "bass": (40, 60),
}

# Comfortable tessitura centers used for range-comfort scoring.
COMFORT: dict[str, tuple[int, int]] = {
    "tenor": (59, 70),
    "bari": (50, 62),
    "bass": (43, 55),
}

HARD = 10_000.0  # effectively-forbidden transition/static cost


@dataclass
class ArrangerConfig:
    spice: int = 3

    # --- voicing: static weights ---
    w_ring: float = 4.0  # ring potential on sustained/cadential chords
    w_cone: float = 1.5  # cone-shaped spacing
    w_range: float = 1.0  # tessitura comfort
    w_cadence_bass_root: float = 6.0  # bass should take root at phrase ends
    w_doubled_fifth: float = 1.0  # prefer doubled root on triads

    # --- voicing: transition weights ---
    w_motion_tenor: float = 1.2
    w_motion_bari: float = 1.0
    w_motion_bass: float = 0.5
    w_leap: float = 0.8  # extra per semitone beyond a 4th in tenor/bari
    w_awkward_interval: float = 3.0  # tritones, sevenths within a part
    w_leading_tone: float = 1.0
    w_common_tone: float = 0.6  # bonus (subtracted) per held common tone

    # --- texture ---
    structural_beats: float = 1.0  # structural-length threshold, in beats

    # cap on voicing candidates per slot (keeps Viterbi fast)
    max_candidates: int = 48
