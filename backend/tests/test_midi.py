"""MIDI export: four tracks, correct tempo and timing at 480 PPQ."""
import io

import mido

from barbershop.arranger.arrange import arrange
from barbershop.arranger.config import ArrangerConfig
from barbershop.demos import DEMOS
from barbershop.midi import to_midi
from barbershop.score import VoiceName


def _load(data: bytes) -> mido.MidiFile:
    return mido.MidiFile(file=io.BytesIO(data))


def test_midi_has_four_voice_tracks_and_tempo():
    score = arrange(DEMOS["yankee-doodle"], ArrangerConfig())
    mid = _load(to_midi(score))
    assert mid.ticks_per_beat == 480
    note_tracks = [t for t in mid.tracks if any(m.type == "note_on" for m in t)]
    assert len(note_tracks) == 4
    tempos = [m for t in mid.tracks for m in t if m.type == "set_tempo"]
    assert tempos and abs(mido.tempo2bpm(tempos[0].tempo) - score.tempo) < 0.5


def test_midi_note_timing_matches_score():
    score = arrange(DEMOS["yankee-doodle"], ArrangerConfig())
    mid = _load(to_midi(score))
    lead_notes = score.voices[VoiceName.lead]
    track = next(
        t for t in mid.tracks if t.name == "Lead"
    )
    abs_time = 0
    events = []
    for msg in track:
        abs_time += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            events.append((abs_time, msg.note))
    assert events[0] == (lead_notes[0].onset, lead_notes[0].midi)
    assert len(events) == len(lead_notes)
