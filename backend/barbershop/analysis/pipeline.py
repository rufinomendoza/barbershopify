"""Full analysis pipeline: audio file -> ArrangeInput (+ metadata).

Results are cached on disk keyed by content hash, so re-arranging at a
different spice never re-runs analysis.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from barbershop.analysis import beats as beats_mod
from barbershop.analysis import chords as chords_mod
from barbershop.analysis import key as key_mod
from barbershop.analysis import melody as melody_mod
from barbershop.analysis.decode import load_audio
from barbershop.arranger.arrange import ArrangeInput
from barbershop.score import TimeSig

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"


@dataclass
class AnalysisResult:
    input: ArrangeInput
    tempo: float
    duration_seconds: float


def _cache_key(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


def analyze(path: str, *, title: str | None = None, use_cache: bool = True) -> AnalysisResult:
    cache_file = CACHE_DIR / f"{_cache_key(path)}.json"
    if use_cache and cache_file.exists():
        data = json.loads(cache_file.read_text())
        return AnalysisResult(
            input=ArrangeInput.model_validate(data["input"]),
            tempo=data["tempo"],
            duration_seconds=data["duration_seconds"],
        )

    y, sr = load_audio(path)
    grid = beats_mod.track(y, sr)

    import librosa

    chroma_mean = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    detected_key = key_mod.detect(np.asarray(chroma_mean))

    # chord labels first: the downbeat phase is wherever chord changes
    # cluster, so measures land on real harmonic arrivals
    labels = chords_mod.label_beats(y, sr, grid.beat_times)
    grid.downbeat_phase = chords_mod.best_downbeat_phase(labels)
    melody = melody_mod.extract(y, sr, grid)
    chord_spans = chords_mod.spans_from_labels(labels, grid)

    if not melody:
        raise ValueError("no melody could be extracted from this audio")
    if not chord_spans:
        raise ValueError("no chords could be estimated from this audio")

    inp = ArrangeInput(
        title=title or Path(path).stem,
        key=detected_key,
        time=TimeSig(beats=4, beat_type=4),  # v1 assumes 4/4 (see DESIGN.md)
        tempo=round(grid.tempo, 1),
        melody=melody,
        chords=chord_spans,
    )
    result = AnalysisResult(
        input=inp, tempo=grid.tempo, duration_seconds=len(y) / sr
    )
    if use_cache:
        CACHE_DIR.mkdir(exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {
                    "input": inp.model_dump(),
                    "tempo": result.tempo,
                    "duration_seconds": result.duration_seconds,
                }
            )
        )
    return result
