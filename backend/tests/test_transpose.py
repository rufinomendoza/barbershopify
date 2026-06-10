"""Global transposition: put the melody in the Lead's comfortable tessitura."""
from barbershop.arranger.transpose import choose_transposition

LEAD_LO, LEAD_HI = 45, 67  # A2..G4


def test_comfortable_melody_is_untouched():
    melody = [55, 57, 59, 60, 62]  # G3..D4, snug in the center band
    shift, _ = choose_transposition(melody, original_fifths=0)
    assert shift == 0


def test_high_melody_comes_down():
    melody = [72, 74, 76, 77, 79]  # C5..G5, way above lead range
    shift, _ = choose_transposition(melody, original_fifths=0)
    assert all(LEAD_LO <= m + shift <= LEAD_HI for m in melody)
    assert shift <= -12


def test_low_melody_comes_up():
    melody = [38, 40, 41, 43]  # D2..G2, below lead range
    shift, _ = choose_transposition(melody, original_fifths=0)
    assert all(LEAD_LO <= m + shift <= LEAD_HI for m in melody)
    assert shift > 0


def test_key_signature_follows_shift():
    melody = [62, 64, 66, 67, 69]  # D4..A4 in D major; needs to come down
    shift, new_fifths = choose_transposition(melody, original_fifths=2)
    # fifths must be consistent with the shift on the circle of fifths
    assert (new_fifths - 2) % 12 == (shift * 7) % 12
    assert -6 <= new_fifths <= 6
