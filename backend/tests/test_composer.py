"""Lyric-driven composition: prosody, affect, and the full text->chart path."""
import pytest

from barbershop.arranger.config import ArrangerConfig
from barbershop.arranger.validate import validate
from barbershop.composer.affect import analyze_affect
from barbershop.composer.compose import compose
from barbershop.composer.prosody import analyze_prosody

SAD_POEM = """The winter rain falls cold and gray
upon the grave where you now sleep
alone I mourn the dying day
and bitter tears in silence weep"""

HAPPY_POEM = """The morning sun is bright with joy
we dance and laugh and sing along
the summer wind is warm and sweet
my happy heart bursts into song"""

AABB_STANZA = """The cat sat on the mat today
and watched the children run and play
the dog beneath the apple tree
was happy as a dog can be"""

AABA_STANZA = """I wandered down the road alone
the night was dark I should have known
the stars were hiding in the mist
and now my weary heart has flown"""


def test_rhyme_scheme_abab():
    p = analyze_prosody(SAD_POEM)
    assert p.stanzas[0].rhyme_scheme == "ABAB"


def test_rhyme_scheme_aabb():
    p = analyze_prosody(AABB_STANZA)
    assert p.stanzas[0].rhyme_scheme == "AABB"


def test_rhyme_scheme_aaba():
    p = analyze_prosody(AABA_STANZA)
    assert p.stanzas[0].rhyme_scheme == "AABA"


def test_iambic_detection():
    p = analyze_prosody(SAD_POEM)  # strict tetrameter
    assert p.dominant_foot == "iambic"


def test_affect_polarity():
    sad = analyze_affect(SAD_POEM)
    happy = analyze_affect(HAPPY_POEM)
    assert sad.valence < -0.1
    assert happy.valence > 0.1
    assert happy.arousal > sad.arousal


def test_sad_poem_composes_minor_and_slow():
    result = compose(SAD_POEM, seed=42)
    assert result.input.key.mode == "minor"
    assert result.input.tempo <= 84


def test_happy_poem_composes_major_and_faster():
    result = compose(HAPPY_POEM, seed=42)
    assert result.input.key.mode == "major"
    assert result.input.tempo >= 92


def test_composition_is_deterministic():
    a = compose(SAD_POEM, seed=7)
    b = compose(SAD_POEM, seed=7)
    assert [n.midi for n in a.input.melody] == [n.midi for n in b.input.melody]
    c = compose(SAD_POEM, seed=8)
    assert [n.midi for n in c.input.melody] != [n.midi for n in a.input.melody]


def test_every_syllable_gets_a_note():
    result = compose(HAPPY_POEM, seed=1)
    lyric_notes = [n for n in result.input.melody if n.lyric is not None]
    assert len(lyric_notes) == len(result.input.melody)  # syllable-driven generation


@pytest.mark.parametrize("spice", [1, 3, 5])
@pytest.mark.parametrize("poem", [SAD_POEM, HAPPY_POEM])
def test_composed_charts_pass_the_legality_suite(poem, spice):
    from barbershop.arranger.arrange import arrange

    result = compose(poem, seed=11)
    score = arrange(result.input, ArrangerConfig(spice=spice))
    violations = validate(score)
    assert violations == [], "\n".join(map(str, violations))
