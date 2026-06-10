"""Texture segmentation: melody + chords -> harmonic slots for the trio.

Barbershop texture is homophonic at the structural level: the trio
re-attacks with each structural melody note, sustains through melodic
filigree (sub-threshold NCT runs), moves when the harmony moves (chord
changes under a held melody note), and rests when the lead rests.
"""
from barbershop.score import ChordSpan, Note
from barbershop.texture import segment

Q = 480  # quarter note
THRESH = 480  # structural threshold: one beat


def n(onset, dur, midi):
    return Note(onset=onset, duration=dur, midi=midi)


def test_simple_homophony_one_slot_per_note():
    melody = [n(0, Q, 60), n(Q, Q, 62), n(2 * Q, Q, 64), n(3 * Q, Q, 65)]
    chords = [ChordSpan(onset=0, duration=4 * Q, root_pc=0, quality="maj")]
    slots = segment(melody, chords, THRESH)
    assert len(slots) == 4
    assert [s.onset for s in slots] == [0, Q, 2 * Q, 3 * Q]
    assert all(s.melody_attack and s.structural for s in slots)
    assert all(s.chord.root_pc == 0 for s in slots)


def test_filigree_is_absorbed_into_preceding_slot():
    # quarter (structural), two eighths (filigree), quarter (structural)
    melody = [n(0, Q, 60), n(Q, Q // 2, 62), n(Q + Q // 2, Q // 2, 64), n(2 * Q, Q, 65)]
    chords = [ChordSpan(onset=0, duration=3 * Q, root_pc=0, quality="maj")]
    slots = segment(melody, chords, THRESH)
    assert len(slots) == 2
    first, second = slots
    assert first.onset == 0 and first.duration == 2 * Q  # trio holds under the run
    assert second.onset == 2 * Q
    # the run's peak matters for keeping the tenor above the lead
    assert first.melody_max_midi == 64


def test_chord_change_under_held_note_moves_the_trio():
    melody = [n(0, 4 * Q, 67)]  # whole note G
    chords = [
        ChordSpan(onset=0, duration=2 * Q, root_pc=0, quality="maj"),
        ChordSpan(onset=2 * Q, duration=2 * Q, root_pc=7, quality="dom7"),
    ]
    slots = segment(melody, chords, THRESH)
    assert len(slots) == 2
    assert slots[0].melody_attack and not slots[1].melody_attack
    assert slots[1].chord.quality == "dom7"
    assert slots[1].structural  # held note must be a chord tone in both chords


def test_trio_rests_when_lead_rests():
    melody = [n(0, Q, 60), n(2 * Q, Q, 64)]  # rest in measure middle
    chords = [ChordSpan(onset=0, duration=4 * Q, root_pc=0, quality="maj")]
    slots = segment(melody, chords, THRESH)
    assert len(slots) == 2
    assert slots[0].duration == Q  # trio stops at the rest, doesn't bridge it


def test_phrase_end_flags_note_before_rest_and_final_note():
    melody = [n(0, Q, 60), n(Q, Q, 62), n(3 * Q, Q, 64)]
    chords = [ChordSpan(onset=0, duration=4 * Q, root_pc=0, quality="maj")]
    slots = segment(melody, chords, THRESH)
    assert [s.phrase_end for s in slots] == [False, True, True]
