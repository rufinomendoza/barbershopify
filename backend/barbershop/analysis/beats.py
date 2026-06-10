"""Tempo and beat grid. 4/4 is assumed (v1); the downbeat phase is chosen
by onset energy so measures land where the music actually accents."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BeatGrid:
    tempo: float  # BPM (quarter notes)
    beat_times: np.ndarray  # seconds, one per beat
    downbeat_phase: int  # index into beat_times of the first downbeat

    def time_to_tick(self, t: float) -> float:
        """Map a time to ticks (480/beat), measure origin at the first downbeat."""
        times = self.beat_times
        origin = self.downbeat_phase
        if len(times) < 2:
            return 0.0
        # locate t between beats (extrapolate at the edges)
        i = int(np.searchsorted(times, t)) - 1
        i = max(0, min(i, len(times) - 2))
        span = times[i + 1] - times[i]
        frac = (t - times[i]) / span if span > 0 else 0.0
        return ((i - origin) + frac) * 480.0


def track(y: np.ndarray, sr: int) -> BeatGrid:
    """Beat grid with downbeat phase 0; the pipeline refines the phase
    afterwards by aligning chord changes to measure starts."""
    import librosa

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])

    # the tracker rarely emits the very first beat: extrapolate leading
    # beats back toward t=0 (and one trailing beat) so pickups survive
    if len(beat_times) >= 2:
        interval = float(np.median(np.diff(beat_times)))
        lead = []
        t = beat_times[0] - interval
        while t > -0.4 * interval and len(lead) < 8:
            lead.append(max(t, 0.0))
            t -= interval
        beat_times = np.concatenate([lead[::-1], beat_times, [beat_times[-1] + interval]])
    return BeatGrid(tempo=tempo, beat_times=beat_times, downbeat_phase=0)
