"""Syllabification & stress: CMUdict-backed with a deterministic OOV fallback."""
from barbershop.textset.syllabify import Syllable, syllabify_word, syllabify_line


def test_known_word_count_and_stress():
    sylls = syllabify_word("doodle")
    assert len(sylls) == 2
    assert sylls[0].stress == 1 and sylls[1].stress == 0


def test_written_split_is_singable():
    sylls = syllabify_word("yankee")
    assert [s.text for s in sylls] == ["yan", "kee"]


def test_monosyllable():
    sylls = syllabify_word("town")
    assert len(sylls) == 1
    assert sylls[0].text == "town"
    assert sylls[0].stress == 1


def test_oov_word_falls_back_to_vowel_groups():
    sylls = syllabify_word("barbershopify")  # not in CMUdict
    assert len(sylls) >= 4  # bar-ber-shop-i-fy ish
    assert all(isinstance(s, Syllable) for s in sylls)


def test_line_keeps_word_boundaries_and_punctuation_clean():
    sylls = syllabify_line("Yankee Doodle went to town,")
    texts = [s.text for s in sylls]
    assert texts == ["yan", "kee", "doo", "dle", "went", "to", "town"]
    # word-position flags drive MusicXML syllabic values
    assert sylls[0].word_begin and not sylls[0].word_end
    assert sylls[1].word_end and not sylls[1].word_begin
    assert sylls[4].word_begin and sylls[4].word_end  # monosyllable


def test_open_vowel_detection_for_melisma_preference():
    (ah,) = syllabify_word("ah")
    (it,) = syllabify_word("it")
    assert ah.open_vowel and not it.open_vowel
