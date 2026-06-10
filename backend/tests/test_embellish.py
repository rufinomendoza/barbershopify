"""Embellishments: swipes and the tag, gated by spice."""
from barbershop.arranger.arrange import arrange
from barbershop.arranger.config import ArrangerConfig
from barbershop.arranger.validate import validate
from barbershop.demos import DEMOS
from barbershop.score import VoiceName


def _chord_changes_under_held_lead(score) -> int:
    """Chord boundaries that fall strictly inside a sounding lead note."""
    lead = score.voices[VoiceName.lead]
    count = 0
    for c1, c2 in zip(score.chords, score.chords[1:]):
        boundary = c2.onset
        for n in lead:
            if n.onset < boundary < n.end:
                count += 1
                break
    return count


def test_spice1_has_no_swipes():
    score = arrange(DEMOS["good-morning-to-all"], ArrangerConfig(spice=1))
    assert _chord_changes_under_held_lead(score) == 0


def test_spice4_swipes_on_sustained_notes():
    mild = arrange(DEMOS["good-morning-to-all"], ArrangerConfig(spice=1))
    wild = arrange(DEMOS["good-morning-to-all"], ArrangerConfig(spice=4))
    assert _chord_changes_under_held_lead(wild) > _chord_changes_under_held_lead(mild)


def test_tag_extends_the_final_note_at_spice3():
    plain = arrange(DEMOS["yankee-doodle"], ArrangerConfig(spice=2))
    tagged = arrange(DEMOS["yankee-doodle"], ArrangerConfig(spice=3))
    plain_final = plain.voices[VoiceName.lead][-1]
    tagged_final = tagged.voices[VoiceName.lead][-1]
    tpm = tagged.time.ticks_per_measure
    assert tagged_final.duration >= plain_final.duration + 2 * tpm
    # the post is harmonized by a walking trio: chords change under it
    walks = sum(
        1 for c in tagged.chords if tagged_final.onset < c.onset < tagged_final.onset + tagged_final.duration
    )
    assert walks >= 2


def test_tagged_charts_still_validate_clean():
    for name in DEMOS:
        for spice in (3, 4, 5):
            score = arrange(DEMOS[name], ArrangerConfig(spice=spice))
            violations = validate(score)
            assert violations == [], f"{name} spice={spice}: " + "; ".join(map(str, violations))
