"""Audio analysis pipeline, tested against a synthesized ground truth:
a sine melody with a click track and low triad pads at 120 BPM in C major.
Signal-processing assertions are tolerant by design."""
import numpy as np
import pytest
import soundfile as sf

from barbershop.analysis.decode import load_audio
from barbershop.analysis.pipeline import analyze

SR = 22050
BPM = 120
BEAT = 60 / BPM  # 0.5s

# one melody note per beat (midi), chord root/quality per measure underneath
MELODY = [60, 62, 64, 65, 67, 64, 60, 62, 64, 65, 67, 69, 67, 64, 62, 60]
CHORDS = [(0, "maj"), (5, "maj"), (7, "dom7"), (0, "maj")]
CHORD_PCS = {"maj": (0, 4, 7), "dom7": (0, 4, 7, 10)}


def _tone(freq: float, dur: float, amp: float) -> np.ndarray:
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    env = np.minimum(1, np.minimum(t / 0.01, (dur - t) / 0.02))
    # a couple of harmonics make pyin and chroma behave like real signals
    return amp * env * (
        np.sin(2 * np.pi * freq * t)
        + 0.3 * np.sin(4 * np.pi * freq * t)
        + 0.1 * np.sin(6 * np.pi * freq * t)
    )


def _midi_hz(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


@pytest.fixture(scope="module")
def test_wav(tmp_path_factory):
    total = len(MELODY) * BEAT
    y = np.zeros(int(SR * total), dtype=np.float64)
    for i, midi in enumerate(MELODY):
        s = int(i * BEAT * SR)
        seg = _tone(_midi_hz(midi), BEAT, 0.5)
        y[s : s + len(seg)] += seg
    for m, (root, quality) in enumerate(CHORDS):
        s = int(m * 4 * BEAT * SR)
        for pc in CHORD_PCS[quality]:
            seg = _tone(_midi_hz(48 + ((root + pc) % 12)), 4 * BEAT, 0.22)
            y[s : s + len(seg)] += seg
        # bass root an octave down, like a real accompaniment
        seg = _tone(_midi_hz(36 + root), 4 * BEAT, 0.3)
        y[s : s + len(seg)] += seg
    # click track for the beat tracker
    rng = np.random.default_rng(7)
    for i in range(len(MELODY)):
        s = int(i * BEAT * SR)
        click = rng.uniform(-1, 1, int(0.012 * SR)) * np.linspace(1, 0, int(0.012 * SR)) * 0.4
        y[s : s + len(click)] += click
    y /= np.abs(y).max() * 1.1
    path = tmp_path_factory.mktemp("audio") / "synth.wav"
    sf.write(path, y.astype(np.float32), SR)
    return path


@pytest.fixture(scope="module")
def analysis(test_wav):
    return analyze(str(test_wav), use_cache=False)


def test_decode_loads_mono_float(test_wav):
    y, sr = load_audio(str(test_wav))
    assert sr == 22050
    assert y.ndim == 1
    assert abs(len(y) / sr - len(MELODY) * BEAT) < 0.1


def test_full_analysis(analysis):
    inp = analysis.input

    # tempo within 5% (or a metrical-level alias)
    assert any(abs(inp.tempo - BPM * f) < 6 for f in (1, 0.5, 2)), inp.tempo

    # key: C major
    assert inp.key.fifths == 0 and inp.key.mode == "major"

    # melody: sample the extracted notes at beat centers, compare pitch classes
    got = []
    for i in range(len(MELODY)):
        tick = i * 480 + 240
        note = next((n for n in inp.melody if n.onset <= tick < n.onset + n.duration), None)
        got.append(note.midi % 12 if note else None)
    want = [m % 12 for m in MELODY]
    agreement = sum(1 for g, w in zip(got, want) if g == w) / len(want)
    assert agreement >= 0.7, f"melody agreement {agreement}: {got} vs {want}"

    # chords: at least 60% of beats carry the right root
    ok = total = 0
    for m, (root, _) in enumerate(CHORDS):
        for b in range(4):
            tick = (m * 4 + b) * 480 + 240
            span = next((c for c in inp.chords if c.onset <= tick < c.onset + c.duration), None)
            total += 1
            if span is not None and span.root_pc == root:
                ok += 1
    assert ok / total >= 0.6, f"chord root accuracy {ok}/{total}"


def test_analysis_feeds_the_arranger(analysis):
    from barbershop.arranger.arrange import arrange
    from barbershop.arranger.config import ArrangerConfig
    from barbershop.arranger.validate import validate

    score = arrange(analysis.input, ArrangerConfig(spice=3))
    assert validate(score) == []
