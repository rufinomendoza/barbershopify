"""Decode any audio file (.mp3/.m4a/.wav) to mono PCM via ffmpeg."""
from __future__ import annotations

import subprocess

import numpy as np

TARGET_SR = 22050


def load_audio(path: str, sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    """Decode to mono float32 at the target sample rate."""
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", path,
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", "1", "-ar", str(sr),
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        raise ValueError(f"ffmpeg could not decode {path!r}: {proc.stderr.decode(errors='replace')[:500]}")
    y = np.frombuffer(proc.stdout, dtype=np.float32)
    if len(y) == 0:
        raise ValueError(f"no audio decoded from {path!r}")
    return y, sr
