"""Chord vocabulary: tiered palette and 4-voice sonority classification."""
import pytest

from barbershop.vocabulary import (
    CHORDS,
    Interpretation,
    chord_pcs,
    chord_degree,
    classify,
)


# --- vocabulary definitions -------------------------------------------------

def test_tier1_is_major_and_dom7():
    assert CHORDS["maj"].tier == 1
    assert CHORDS["dom7"].tier == 1


def test_dom7_pcs_relative_to_root():
    assert chord_pcs(0, "dom7") == frozenset({0, 4, 7, 10})


def test_major7_not_in_vocabulary():
    assert "maj7" not in CHORDS


def test_chord_degree_names():
    # G7: G=root, B=third, D=fifth, F=seventh
    assert chord_degree(7, "dom7", 7) == "root"
    assert chord_degree(7, "dom7", 11) == "third"
    assert chord_degree(7, "dom7", 2) == "fifth"
    assert chord_degree(7, "dom7", 5) == "seventh"
    assert chord_degree(7, "dom7", 0) is None  # not a chord tone


# --- classification of 4-voice sonorities ------------------------------------

def test_complete_dom7_classifies():
    # G2 B2 D3 F3
    interps = classify((7, 11, 2, 5))
    assert Interpretation(root_pc=7, quality="dom7", doubled_pc=None) in interps


def test_major_triad_doubled_root_classifies():
    # C E G C
    interps = classify((0, 4, 7, 0))
    assert Interpretation(root_pc=0, quality="maj", doubled_pc=0) in interps


def test_major_triad_doubled_fifth_classifies():
    # C E G G
    interps = classify((0, 4, 7, 7))
    assert Interpretation(root_pc=0, quality="maj", doubled_pc=7) in interps


def test_major_triad_doubled_third_is_flagged():
    # C E E G — classifiable, but the doubling is reported for repose checks
    interps = classify((0, 4, 4, 7))
    assert Interpretation(root_pc=0, quality="maj", doubled_pc=4) in interps


def test_major_seventh_sonority_is_illegal():
    # C E G B — not barbershop
    assert classify((0, 4, 7, 11)) == []


def test_open_fifth_is_illegal():
    # C G C G — no third, not classifiable
    assert classify((0, 7, 0, 7)) == []


def test_sus_sonority_is_illegal():
    # C F G C
    assert classify((0, 5, 7, 0)) == []


def test_dim7_classifies_under_any_rotation():
    interps = classify((0, 3, 6, 9))
    roots = {i.root_pc for i in interps if i.quality == "dim7"}
    assert roots == {0, 3, 6, 9}


def test_maj6_min7_ambiguity():
    # C6 (C E G A) is also Am7 — both readings are legal
    interps = classify((0, 4, 7, 9))
    assert Interpretation(root_pc=0, quality="maj6", doubled_pc=None) in interps
    assert Interpretation(root_pc=9, quality="min7", doubled_pc=None) in interps


def test_halfdim_classifies():
    # B D F A
    interps = classify((11, 2, 5, 9))
    assert any(i.root_pc == 11 and i.quality == "halfdim7" for i in interps)


def test_dom9_rootless_classifies_as_dom9():
    # C9 voiced rootless: E G Bb D
    interps = classify((4, 7, 10, 2))
    assert any(i.root_pc == 0 and i.quality == "dom9" for i in interps)


def test_classify_requires_four_pitches():
    with pytest.raises(ValueError):
        classify((0, 4, 7))
