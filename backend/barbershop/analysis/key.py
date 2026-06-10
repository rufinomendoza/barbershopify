"""Global key detection: Krumhansl-Schmuckler profile correlation."""
from __future__ import annotations

import numpy as np

from barbershop.score import KeySig

_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# tonic pitch class -> key signature fifths (major); minor relative
_MAJOR_FIFTHS = {0: 0, 7: 1, 2: 2, 9: 3, 4: 4, 11: 5, 6: 6, 1: -5, 8: -4, 3: -3, 10: -2, 5: -1}


def detect(chroma_mean: np.ndarray) -> KeySig:
    best: tuple[float, int, str] = (-2.0, 0, "major")
    for tonic in range(12):
        rotated = np.roll(chroma_mean, -tonic)
        for profile, mode in ((_MAJOR, "major"), (_MINOR, "minor")):
            r = float(np.corrcoef(rotated, profile)[0, 1])
            if r > best[0]:
                best = (r, tonic, mode)
    _, tonic, mode = best
    if mode == "major":
        fifths = _MAJOR_FIFTHS[tonic]
    else:
        fifths = _MAJOR_FIFTHS[(tonic + 3) % 12]  # relative major's signature
    return KeySig(fifths=fifths, mode=mode)
