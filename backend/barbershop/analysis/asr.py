"""Lyric transcription via faster-whisper, with honest degradation.

ASR on music — especially on acoustic-era 78s — is unreliable. The rules:
words attach to melody notes only when the transcription is confident
overall; per-word timestamps are trusted less than the melody's rhythm
(words snap to the nearest note onset within a tolerance window); and
when transcription is garbage the chart gets neutral doo/dah syllables
rather than committed nonsense.
"""
from __future__ import annotations

from dataclasses import dataclass

from barbershop.analysis.beats import BeatGrid
from barbershop.score import Lyric, Note, Syllabic
from barbershop.textset.phrases import split_phrases
from barbershop.textset.syllabify import syllabify_word

CONFIDENCE_THRESHOLD = 0.5
SNAP_TOLERANCE_TICKS = 480  # one beat


@dataclass
class Word:
    text: str
    start: float  # seconds
    end: float
    prob: float


def transcribe(path: str) -> list[Word] | None:
    """Run faster-whisper with word timestamps. None = unavailable/failed."""
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(path, word_timestamps=True, vad_filter=True)
        words: list[Word] = []
        for seg in segments:
            for w in seg.words or []:
                words.append(
                    Word(text=w.word.strip(), start=w.start, end=w.end, prob=w.probability)
                )
        return words
    except Exception:
        return None


def mean_confidence(words: list[Word]) -> float:
    return sum(w.prob for w in words) / len(words) if words else 0.0


def attach_lyrics(melody: list[Note], words: list[Word], grid: BeatGrid) -> bool:
    """Align timed words to melody notes. Returns False if not confident."""
    if not words or mean_confidence(words) < CONFIDENCE_THRESHOLD:
        return False
    notes = sorted(melody, key=lambda n: n.onset)
    cursor = 0
    for word in words:
        sylls = syllabify_word(word.text)
        if not sylls:
            continue
        word_tick = grid.time_to_tick(word.start)
        # trust the melody's rhythm: snap to the nearest free note onset
        best, best_dist = None, SNAP_TOLERANCE_TICKS + 1
        for j in range(cursor, len(notes)):
            dist = abs(notes[j].onset - word_tick)
            if dist < best_dist:
                best, best_dist = j, dist
            if notes[j].onset > word_tick + SNAP_TOLERANCE_TICKS:
                break
        if best is None:
            continue
        for offset, syll in enumerate(sylls):
            if best + offset >= len(notes):
                break
            if syll.word_begin and syll.word_end:
                syllabic = Syllabic.single
            elif syll.word_begin:
                syllabic = Syllabic.begin
            elif syll.word_end:
                syllabic = Syllabic.end
            else:
                syllabic = Syllabic.middle
            notes[best + offset].lyric = Lyric(text=syll.text, syllabic=syllabic)
        cursor = best + len(sylls)
    return True


def neutral_lyrics(melody: list[Note]) -> None:
    """The honest fallback: doo on moving notes, dah at phrase ends."""
    for phrase in split_phrases(melody):
        for note in phrase:
            note.lyric = Lyric(text="doo", syllabic=Syllabic.single)
        phrase[-1].lyric = Lyric(text="dah", syllabic=Syllabic.single)
