"""Harmonization: per-slot chord choice (fidelity at low spice,
secondary-dominant reharmonization at high spice, melody always sacrosanct)."""
from barbershop.score import ChordSpan, KeySig
from barbershop.texture import Slot
from barbershop.vocabulary import chord_pcs
from barbershop.arranger.config import ArrangerConfig
from barbershop.arranger.harmonize import harmonize

Q = 480
KEY_C = KeySig(fifths=0, mode="major")


def make_slot(onset, melody_midi, root_pc, quality, *, phrase_end=False, structural=True):
    return Slot(
        onset=onset,
        duration=Q,
        melody_midi=melody_midi,
        melody_max_midi=melody_midi,
        melody_last_midi=melody_midi,
        melody_attack=True,
        chord=ChordSpan(onset=onset, duration=Q, root_pc=root_pc, quality=quality),
        structural=structural,
        phrase_end=phrase_end,
    )


def turnaround_slots():
    """I - vi - ii - V - I with a melody compatible with the dominant chain."""
    return [
        make_slot(0, 60, 0, "maj"),  # C over I
        make_slot(Q, 64, 9, "min"),  # E over vi (also fits VI7)
        make_slot(2 * Q, 57, 2, "min"),  # A over ii (also fits II7)
        make_slot(3 * Q, 62, 7, "maj"),  # D over V
        make_slot(4 * Q, 60, 0, "maj", phrase_end=True),  # C over I
    ]


def test_melody_clash_forces_substitution():
    # melody F over an input C major: F is no chord tone of anything rooted C
    slots = [make_slot(0, 65, 0, "maj")]
    (chord,) = harmonize(slots, KEY_C, ArrangerConfig(spice=3))
    assert 5 in chord_pcs(chord.root_pc, chord.quality)


def test_spice1_keeps_the_skeleton():
    chords = harmonize(turnaround_slots(), KEY_C, ArrangerConfig(spice=1))
    assert [c.root_pc for c in chords] == [0, 9, 2, 7, 0]


def test_spice5_builds_dominant_chains():
    chords = harmonize(turnaround_slots(), KEY_C, ArrangerConfig(spice=5))
    doms = sum(1 for c in chords if c.quality in ("dom7", "dom9", "aug7", "dom7b5"))
    assert doms >= 2  # the middle of the turnaround should go dominant


def test_function_preserved_at_phrase_boundaries():
    for spice in (1, 5):
        chords = harmonize(turnaround_slots(), KEY_C, ArrangerConfig(spice=spice))
        assert chords[0].root_pc == 0
        assert chords[-1].root_pc == 0


def test_dom7_share_rises_with_spice():
    def share(spice):
        chords = harmonize(turnaround_slots(), KEY_C, ArrangerConfig(spice=spice))
        return sum(1 for c in chords if c.quality == "dom7") / len(chords)

    assert share(5) >= share(1)


def test_nonstructural_slots_keep_input_chord():
    slots = [make_slot(0, 62, 0, "maj", structural=False)]
    (chord,) = harmonize(slots, KEY_C, ArrangerConfig(spice=5))
    assert (chord.root_pc, chord.quality) == (0, "maj")
