"""Text setting: prosodic alignment, melisma/split handling, fit diagnosis."""
from barbershop.score import Note, TimeSig
from barbershop.textset.align import set_lyrics
from barbershop.textset.phrases import split_phrases

Q = 480
T44 = TimeSig(beats=4, beat_type=4)


def quarters(pitches, start=0):
    return [Note(onset=start + i * Q, duration=Q, midi=m) for i, m in enumerate(pitches)]


def test_phrases_split_at_rests():
    melody = quarters([60, 62, 64]) + quarters([65, 67], start=4 * Q)
    phrases = split_phrases(melody)
    assert [len(p) for p in phrases] == [3, 2]


def test_yankee_doodle_stress_lands_on_strong_beats():
    # "Yan-kee Doo-dle went to town" over the famous seven quarters
    melody = quarters([60, 60, 62, 64, 60, 64, 62])
    notes, reports = set_lyrics(melody, "Yankee Doodle went to town", T44)
    assert len(notes) == 7
    stressed_beats = [
        T44.beat_of(n.onset)
        for n in notes
        if n.lyric and n.lyric.text in ("yan", "doo", "went", "town")
    ]
    # all stressed syllables on full beats, mostly downbeats/mid-bar
    assert all(b == int(b) for b in stressed_beats)
    assert stressed_beats[0] == 0.0  # "yan" on the downbeat
    assert reports[0].status == "green"
    # syllabic flags drive hyphenation: yan=begin kee=end went=single
    assert notes[0].lyric.syllabic.value == "begin"
    assert notes[1].lyric.syllabic.value == "end"
    assert notes[4].lyric.syllabic.value == "single"


def test_melisma_when_fewer_syllables_than_notes():
    melody = quarters([60, 62, 64, 65, 67, 69])
    notes, reports = set_lyrics(melody, "ah lovely day", T44)  # 4 syllables, 6 notes
    assert len(notes) == 6
    sung = [n for n in notes if n.lyric is not None]
    assert len(sung) == 4
    assert any(n.lyric.extend for n in sung)  # melisma start carries the extender
    assert sum(n.duration for n in notes) == 6 * Q  # rhythm untouched
    assert reports[0].status in ("green", "yellow")


def test_split_when_more_syllables_than_notes():
    melody = quarters([60, 60, 62, 64])
    notes, reports = set_lyrics(melody, "everybody get up and go", T44)  # 8 syllables, 4 notes
    assert len(notes) == 8
    assert all(n.lyric is not None for n in notes)
    assert sum(n.duration for n in notes) == 4 * Q  # total time preserved
    # splits keep the original pitch
    assert notes[0].midi == notes[1].midi == 60
    assert reports[0].status in ("yellow", "red")


def test_severe_mismatch_reports_red_but_still_sets():
    melody = quarters([60, 62, 64])
    text = "supercalifragilisticexpialidocious indeed my friend"
    notes, reports = set_lyrics(melody, text, T44)
    assert reports[0].status == "red"
    assert all(n.lyric is not None for n in notes)


def test_lines_map_to_phrases():
    melody = quarters([60, 62, 64, 65]) + quarters([67, 65, 64, 62], start=5 * Q)
    notes, reports = set_lyrics(melody, "sing a song now\nhear the music play", T44)
    assert len(reports) == 2
    first_phrase_lyrics = [n.lyric.text for n in notes[:4]]
    assert first_phrase_lyrics == ["sing", "a", "song", "now"]
