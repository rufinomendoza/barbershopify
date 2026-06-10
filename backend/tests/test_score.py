"""Score model: tick arithmetic and measure math."""
from barbershop.score import (
    TICKS_PER_QUARTER,
    KeySig,
    Note,
    Score,
    TimeSig,
    VoiceName,
)


def test_ticks_per_quarter_is_480():
    assert TICKS_PER_QUARTER == 480


def test_ticks_per_measure_common_time():
    assert TimeSig(beats=4, beat_type=4).ticks_per_measure == 1920


def test_ticks_per_measure_waltz():
    assert TimeSig(beats=3, beat_type=4).ticks_per_measure == 1440


def test_ticks_per_measure_compound():
    # 6/8: six eighth notes of 240 ticks each
    assert TimeSig(beats=6, beat_type=8).ticks_per_measure == 1440


def test_measure_and_beat_of_onset():
    ts = TimeSig(beats=4, beat_type=4)
    # beat 3 of measure 2 (both zero-indexed: measure 1, beat 2.0)
    onset = 1920 + 2 * 480
    assert ts.measure_of(onset) == 1
    assert ts.beat_of(onset) == 2.0


def test_score_total_ticks_spans_longest_voice():
    score = Score(
        title="t",
        key=KeySig(fifths=0, mode="major"),
        time=TimeSig(beats=4, beat_type=4),
        tempo=96,
        voices={
            VoiceName.lead: [Note(onset=0, duration=480, midi=60)],
            VoiceName.bass: [Note(onset=0, duration=960, midi=48)],
            VoiceName.tenor: [],
            VoiceName.bari: [],
        },
        chords=[],
    )
    assert score.total_ticks == 960
    assert score.num_measures == 1
