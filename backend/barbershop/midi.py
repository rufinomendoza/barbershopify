"""MIDI export: one track per voice at 480 PPQ (score ticks map 1:1)."""
from __future__ import annotations

import io

import mido

from barbershop.score import Score, VoiceName

_PROGRAM = 52  # choir aahs
_VELOCITY = 88
_TRACK_NAMES = {
    VoiceName.tenor: "Tenor",
    VoiceName.lead: "Lead",
    VoiceName.bari: "Baritone",
    VoiceName.bass: "Bass",
}


def to_midi(score: Score) -> bytes:
    mid = mido.MidiFile(ticks_per_beat=480)

    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(score.tempo), time=0))
    meta.append(
        mido.MetaMessage(
            "time_signature",
            numerator=score.time.beats,
            denominator=score.time.beat_type,
            time=0,
        )
    )
    mid.tracks.append(meta)

    for channel, (voice, name) in enumerate(_TRACK_NAMES.items()):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=name, time=0))
        track.append(mido.Message("program_change", program=_PROGRAM, channel=channel, time=0))
        events: list[tuple[int, int, mido.Message]] = []  # (tick, order, msg)
        for n in score.voices.get(voice, []):
            events.append(
                (n.onset, 1, mido.Message("note_on", note=n.midi, velocity=_VELOCITY, channel=channel))
            )
            events.append(
                (n.end, 0, mido.Message("note_off", note=n.midi, velocity=0, channel=channel))
            )
        events.sort(key=lambda e: (e[0], e[1]))
        prev = 0
        for tick, _, msg in events:
            msg.time = tick - prev
            track.append(msg)
            prev = tick
        mid.tracks.append(track)

    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()
