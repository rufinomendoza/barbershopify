"""End-to-end arranger: ArrangeInput -> four-part Score."""
import pytest

from barbershop.arranger.arrange import arrange
from barbershop.arranger.config import RANGES, ArrangerConfig
from barbershop.demos import DEMOS
from barbershop.score import VoiceName


@pytest.fixture(params=list(DEMOS))
def demo(request):
    return DEMOS[request.param]


def test_lead_is_melody_verbatim_modulo_transposition(demo):
    score = arrange(demo, ArrangerConfig(spice=3))
    lead = score.voices[VoiceName.lead]
    assert len(lead) == len(demo.melody)
    shift = lead[0].midi - demo.melody[0].midi
    for got, want in zip(lead, demo.melody):
        assert got.onset == want.onset
        assert got.duration == want.duration
        assert got.midi == want.midi + shift


def test_all_voices_inhabit_their_ranges(demo):
    score = arrange(demo, ArrangerConfig(spice=3))
    for voice, notes in score.voices.items():
        lo, hi = RANGES[voice.value]
        assert notes, f"{voice} is empty"
        for n in notes:
            assert lo <= n.midi <= hi, f"{voice} out of range: {n.midi} at {n.onset}"


def test_harmony_parts_cover_the_melody_span(demo):
    score = arrange(demo, ArrangerConfig(spice=3))
    lead = score.voices[VoiceName.lead]
    for voice in (VoiceName.tenor, VoiceName.bari, VoiceName.bass):
        notes = score.voices[voice]
        # trio sings from the first structural beat to the end of the tune
        assert notes[-1].end == lead[-1].end


def test_chord_annotations_cover_all_trio_attacks(demo):
    score = arrange(demo, ArrangerConfig(spice=3))
    chord_ticks = [(c.onset, c.end) for c in score.chords]
    for n in score.voices[VoiceName.bass]:
        assert any(on <= n.onset < end for on, end in chord_ticks)


@pytest.mark.parametrize("spice", [1, 2, 3, 4, 5])
def test_every_spice_level_arranges_every_demo(spice):
    for demo in DEMOS.values():
        score = arrange(demo, ArrangerConfig(spice=spice))
        assert score.voices[VoiceName.lead]


def test_spice_changes_the_chart():
    demo = next(iter(DEMOS.values()))
    mild = arrange(demo, ArrangerConfig(spice=1))
    wild = arrange(demo, ArrangerConfig(spice=5))
    assert mild.chords != wild.chords
