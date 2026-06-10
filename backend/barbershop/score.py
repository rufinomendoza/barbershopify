"""The score model — single source of truth for an arrangement.

Time is integer ticks at 480 per quarter note. Pitches are MIDI ints
(sounding pitch). Four named voices; chord annotations travel with the
score because both the legality validator and just-intonation playback
need to know what chord each vertical belongs to.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

TICKS_PER_QUARTER = 480


class VoiceName(str, Enum):
    tenor = "tenor"
    lead = "lead"
    bari = "bari"
    bass = "bass"


class Syllabic(str, Enum):
    single = "single"
    begin = "begin"
    middle = "middle"
    end = "end"


class Lyric(BaseModel):
    text: str
    syllabic: Syllabic = Syllabic.single
    extend: bool = False  # melisma extender line starts at this note


class Note(BaseModel):
    onset: int = Field(ge=0)  # absolute ticks from start of piece
    duration: int = Field(gt=0)  # ticks
    midi: int = Field(ge=0, le=127)  # sounding pitch
    lyric: Lyric | None = None

    @property
    def end(self) -> int:
        return self.onset + self.duration


class KeySig(BaseModel):
    fifths: int = Field(ge=-7, le=7)
    mode: Literal["major", "minor"] = "major"


class TimeSig(BaseModel):
    beats: int = Field(gt=0)
    beat_type: int = Field(gt=0)  # 4 = quarter, 8 = eighth, ...

    @property
    def ticks_per_beat(self) -> int:
        return TICKS_PER_QUARTER * 4 // self.beat_type

    @property
    def ticks_per_measure(self) -> int:
        return self.beats * self.ticks_per_beat

    def measure_of(self, onset: int) -> int:
        return onset // self.ticks_per_measure

    def beat_of(self, onset: int) -> float:
        return (onset % self.ticks_per_measure) / self.ticks_per_beat


class ChordSpan(BaseModel):
    """A chord annotation: this vertical region belongs to this chord."""

    onset: int = Field(ge=0)
    duration: int = Field(gt=0)
    root_pc: int = Field(ge=0, le=11)
    quality: str  # key into barbershop.vocabulary.CHORDS

    @property
    def end(self) -> int:
        return self.onset + self.duration


class Score(BaseModel):
    title: str
    key: KeySig
    time: TimeSig
    tempo: float = Field(gt=0)  # quarter notes per minute
    voices: dict[VoiceName, list[Note]]
    chords: list[ChordSpan]

    @property
    def total_ticks(self) -> int:
        ends = [n.end for notes in self.voices.values() for n in notes]
        return max(ends, default=0)

    @property
    def num_measures(self) -> int:
        total = self.total_ticks
        if total == 0:
            return 0
        tpm = self.time.ticks_per_measure
        return (total + tpm - 1) // tpm
