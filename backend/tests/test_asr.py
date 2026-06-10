"""ASR lyric pathway: timed-word alignment, confidence gating, doo/dah fallback."""
import numpy as np

from barbershop.analysis.asr import Word, attach_lyrics, neutral_lyrics
from barbershop.analysis.beats import BeatGrid
from barbershop.score import Note

# 120 BPM grid: beat every 0.5s, downbeat at t=0
GRID = BeatGrid(tempo=120, beat_times=np.arange(0, 20, 0.5), downbeat_phase=0)


def quarters(pitches):
    return [Note(onset=i * 480, duration=480, midi=m) for i, m in enumerate(pitches)]


def test_confident_words_attach_to_nearest_notes():
    melody = quarters([60, 62, 64, 65])
    words = [
        Word(text="yankee", start=0.02, end=0.95, prob=0.9),
        Word(text="doodle", start=1.04, end=1.9, prob=0.9),
    ]
    assert attach_lyrics(melody, words, GRID) is True
    texts = [n.lyric.text if n.lyric else None for n in melody]
    assert texts == ["yan", "kee", "doo", "dle"]


def test_low_confidence_refuses_to_attach():
    melody = quarters([60, 62])
    words = [Word(text="mumble", start=0.0, end=0.5, prob=0.2)]
    assert attach_lyrics(melody, words, GRID) is False
    assert all(n.lyric is None for n in melody)


def test_neutral_fallback_doo_dah():
    melody = quarters([60, 62, 64]) + [Note(onset=5 * 480, duration=480, midi=65)]
    neutral_lyrics(melody)
    texts = [n.lyric.text for n in melody]
    assert texts[:2] == ["doo", "doo"]
    assert texts[2] == "dah"  # phrase-final gets the closing vowel
    assert texts[3] == "dah"
