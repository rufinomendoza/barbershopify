"""Pick the global transposition that puts the melody in the Lead's sweet spot."""
from __future__ import annotations

LEAD_LO, LEAD_HI = 45, 67  # A2..G4 hard range
CENTER_LO, CENTER_HI = 48, 64  # C3..E4 comfort band

_HARD = 10_000.0


def _normalize_fifths(fifths: int) -> int:
    """Map a circle-of-fifths position into [-6, 6], preferring fewer accidentals."""
    f = fifths % 12  # 0..11
    candidates = [f, f - 12]
    return min((c for c in candidates if -6 <= c <= 6), key=abs, default=f - 12)


def choose_transposition(melody: list[int], original_fifths: int) -> tuple[int, int]:
    """Return (semitone_shift, new_key_fifths) optimizing lead comfort.

    Hard: every shifted note inside A2..G4. Soft: centered in C3..E4,
    minimal shift, simple key signature.
    """
    best_shift, best_cost = 0, float("inf")
    for shift in range(-24, 25):
        cost = 0.0
        for m in melody:
            p = m + shift
            if p < LEAD_LO or p > LEAD_HI:
                cost += _HARD
            cost += max(0, CENTER_LO - p, p - CENTER_HI)
        new_fifths = _normalize_fifths(original_fifths + shift * 7)
        cost += 0.1 * abs(shift) + 0.3 * abs(new_fifths)
        if cost < best_cost:
            best_cost, best_shift = cost, shift
    return best_shift, _normalize_fifths(original_fifths + best_shift * 7)
