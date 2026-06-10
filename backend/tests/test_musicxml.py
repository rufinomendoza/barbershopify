"""MusicXML serialization: two-staff barbershop convention, ties, spelling."""
import xml.etree.ElementTree as ET

from barbershop.arranger.arrange import arrange
from barbershop.arranger.config import ArrangerConfig
from barbershop.demos import DEMOS
from barbershop.musicxml import to_musicxml
from barbershop.score import ChordSpan, KeySig, Note, Score, TimeSig, VoiceName


def _score(voices, *, fifths=0, beats=4, chords=None):
    return Score(
        title="t",
        key=KeySig(fifths=fifths, mode="major"),
        time=TimeSig(beats=beats, beat_type=4),
        tempo=100,
        voices={
            VoiceName.tenor: voices.get("tenor", []),
            VoiceName.lead: voices.get("lead", []),
            VoiceName.bari: voices.get("bari", []),
            VoiceName.bass: voices.get("bass", []),
        },
        chords=chords or [],
    )


def test_demo_serializes_to_wellformed_musicxml():
    score = arrange(DEMOS["yankee-doodle"], ArrangerConfig())
    root = ET.fromstring(to_musicxml(score))
    assert root.tag == "score-partwise"
    parts = root.findall("part")
    assert len(parts) == 2


def test_clefs_treble_8vb_and_bass():
    score = arrange(DEMOS["yankee-doodle"], ArrangerConfig())
    root = ET.fromstring(to_musicxml(score))
    p1_clef = root.find("part[@id='P1']/measure/attributes/clef")
    assert p1_clef.findtext("sign") == "G"
    assert p1_clef.findtext("clef-octave-change") == "-1"
    p2_clef = root.find("part[@id='P2']/measure/attributes/clef")
    assert p2_clef.findtext("sign") == "F"


def test_stem_directions_and_voice_numbers():
    score = _score({
        "tenor": [Note(onset=0, duration=480, midi=67)],
        "lead": [Note(onset=0, duration=480, midi=64)],
        "bari": [Note(onset=0, duration=480, midi=55)],
        "bass": [Note(onset=0, duration=480, midi=48)],
    })
    root = ET.fromstring(to_musicxml(score))
    p1_notes = [n for n in root.findall("part[@id='P1']/measure/note") if n.find("rest") is None]
    by_voice = {n.findtext("voice"): n for n in p1_notes}
    assert by_voice["1"].findtext("stem") == "up"  # tenor
    assert by_voice["2"].findtext("stem") == "down"  # lead


def test_note_spanning_barline_splits_with_tie():
    score = _score({
        "lead": [Note(onset=1440, duration=960, midi=60)],  # crosses m1->m2
    })
    root = ET.fromstring(to_musicxml(score))
    measures = root.findall("part[@id='P1']/measure")
    m1_lead = [n for n in measures[0].findall("note") if n.find("pitch") is not None]
    m2_lead = [n for n in measures[1].findall("note") if n.find("pitch") is not None]
    assert m1_lead[0].find("tie[@type='start']") is not None
    assert m2_lead[0].find("tie[@type='stop']") is not None
    assert int(m1_lead[0].findtext("duration")) == 480
    assert int(m2_lead[0].findtext("duration")) == 480


def test_gaps_become_rests():
    score = _score({
        "lead": [Note(onset=960, duration=960, midi=60)],  # rest for beats 1-2
    })
    root = ET.fromstring(to_musicxml(score))
    m1 = root.findall("part[@id='P1']/measure")[0]
    lead_items = [n for n in m1.findall("note") if n.findtext("voice") == "2"]
    assert lead_items[0].find("rest") is not None
    assert int(lead_items[0].findtext("duration")) == 960


def test_spelling_follows_chord_context():
    # F#4 over a D7 chord in C major must be F-sharp, not G-flat
    chords = [ChordSpan(onset=0, duration=480, root_pc=2, quality="dom7")]
    score = _score({"lead": [Note(onset=0, duration=480, midi=66)]}, chords=chords)
    root = ET.fromstring(to_musicxml(score))
    pitch = root.find("part[@id='P1']/measure/note/pitch")
    assert pitch.findtext("step") == "F"
    assert pitch.findtext("alter") == "1"
    assert pitch.findtext("octave") == "4"


def test_spelling_flats_in_flat_context():
    # Eb over a Cmin chord: E-flat, not D-sharp
    chords = [ChordSpan(onset=0, duration=480, root_pc=0, quality="min")]
    score = _score({"lead": [Note(onset=0, duration=480, midi=63)]}, chords=chords)
    root = ET.fromstring(to_musicxml(score))
    pitch = root.find("part[@id='P1']/measure/note/pitch")
    assert pitch.findtext("step") == "E"
    assert pitch.findtext("alter") == "-1"


def test_tempo_direction_present():
    score = arrange(DEMOS["yankee-doodle"], ArrangerConfig())
    root = ET.fromstring(to_musicxml(score))
    sound = root.find("part[@id='P1']/measure/direction/sound")
    assert sound is not None and float(sound.get("tempo")) > 0
