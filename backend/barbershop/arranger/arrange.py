"""Top-level arranger pipeline: ArrangeInput -> four-part Score.

transpose -> segment into slots -> harmonize (chord per slot) ->
voice (tenor/bari/bass per slot) -> assemble Score. The lead carries the
melody verbatim (transposed); the trio re-attacks on structural melody
notes, holds through filigree, and merges common tones across chord
changes under a held lead.
"""
from __future__ import annotations

from dataclasses import replace

from pydantic import BaseModel, Field

from barbershop.score import ChordSpan, KeySig, Note, Score, TimeSig, VoiceName
from barbershop.texture import segment
from barbershop.arranger.config import ArrangerConfig
from barbershop.arranger.harmonize import harmonize
from barbershop.arranger.transpose import choose_transposition
from barbershop.arranger.voicing import voice_slots


class ArrangeInput(BaseModel):
    title: str
    key: KeySig
    time: TimeSig
    tempo: float = Field(gt=0)
    melody: list[Note]
    chords: list[ChordSpan]


def arrange(inp: ArrangeInput, cfg: ArrangerConfig) -> Score:
    if not inp.melody:
        raise ValueError("cannot arrange an empty melody")

    shift, fifths = choose_transposition([n.midi for n in inp.melody], inp.key.fifths)
    key = KeySig(fifths=fifths, mode=inp.key.mode)
    melody = [n.model_copy(update={"midi": n.midi + shift}) for n in inp.melody]
    chords = [
        c.model_copy(update={"root_pc": (c.root_pc + shift) % 12}) for c in inp.chords
    ]

    threshold = int(cfg.structural_beats * inp.time.ticks_per_beat)
    slots = segment(melody, chords, threshold)
    chosen = harmonize(slots, key, cfg)
    slots = [replace(slot, chord=chord) for slot, chord in zip(slots, chosen)]
    voicings = voice_slots(slots, key, cfg)

    voices: dict[VoiceName, list[Note]] = {VoiceName.lead: melody}
    for name in (VoiceName.tenor, VoiceName.bari, VoiceName.bass):
        notes: list[Note] = []
        for slot, v in zip(slots, voicings):
            pitch = v.pitch(name.value)
            held = (
                notes
                and not slot.melody_attack
                and notes[-1].end == slot.onset
                and notes[-1].midi == pitch
            )
            if held:
                notes[-1].duration += slot.duration
            else:
                notes.append(Note(onset=slot.onset, duration=slot.duration, midi=pitch))
        voices[name] = notes

    merged: list[ChordSpan] = []
    for c in chosen:
        if (
            merged
            and merged[-1].end == c.onset
            and merged[-1].root_pc == c.root_pc
            and merged[-1].quality == c.quality
        ):
            merged[-1].duration += c.duration
        else:
            merged.append(c.model_copy())

    return Score(
        title=inp.title,
        key=key,
        time=inp.time,
        tempo=inp.tempo,
        voices=voices,
        chords=merged,
    )
