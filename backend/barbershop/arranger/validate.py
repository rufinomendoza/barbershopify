"""Chart legality validator + quality metrics (SPEC.md quality bar).

Walks every vertical sonority of a finished score and names violations
by measure and beat: vocabulary legality, voice crossing, ranges, bass
discipline, doubled thirds at repose, unresolved chordal 7ths, parallel
octaves/fifths. NCT verticals (lead filigree under a held trio) are
exempt from full classification but the trio must stay on chord tones.
"""
from __future__ import annotations

from dataclasses import dataclass

from barbershop.score import ChordSpan, Note, Score, VoiceName
from barbershop.vocabulary import CHORDS, chord_degree, chord_pcs, classify
from barbershop.arranger.config import RANGES

_DOM_FAMILY = ("dom7", "dom9", "aug7", "dom7b5")
_TRIO = (VoiceName.tenor, VoiceName.bari, VoiceName.bass)


@dataclass(frozen=True)
class Violation:
    measure: int  # 1-indexed
    beat: float  # 1-indexed
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"m{self.measure} b{self.beat:g}: [{self.kind}] {self.detail}"


def _sounding(notes: list[Note], tick: int) -> Note | None:
    for n in notes:
        if n.onset <= tick < n.end:
            return n
    return None


def _chord_at(chords: list[ChordSpan], tick: int) -> ChordSpan | None:
    for c in chords:
        if c.onset <= tick < c.end:
            return c
    return None


def _seventh_pc(chord: ChordSpan) -> int | None:
    for interval, name in CHORDS[chord.quality].degrees.items():
        if name == "seventh":
            return (chord.root_pc + interval) % 12
    return None


def _event_ticks(score: Score) -> list[int]:
    return sorted({n.onset for notes in score.voices.values() for n in notes})


def _phrase_final_lead_notes(lead: list[Note], threshold: int) -> set[int]:
    """Onsets of lead notes that end a contiguous sung span AND are of
    structural length — repose implies sustain; a short trailing ornament
    is not a point of repose."""
    out = set()
    for i, n in enumerate(lead):
        if (i + 1 == len(lead) or lead[i + 1].onset > n.end) and n.duration >= threshold:
            out.add(n.onset)
    return out


def validate(score: Score, threshold: int | None = None) -> list[Violation]:
    if threshold is None:
        threshold = score.time.ticks_per_beat
    out: list[Violation] = []

    def report(tick: int, kind: str, detail: str) -> None:
        out.append(
            Violation(
                measure=score.time.measure_of(tick) + 1,
                beat=score.time.beat_of(tick) + 1,
                kind=kind,
                detail=detail,
            )
        )

    # --- ranges (per note, any voice) ---
    for voice, notes in score.voices.items():
        lo, hi = RANGES[voice.value]
        for n in notes:
            if not (lo <= n.midi <= hi):
                report(n.onset, "range", f"{voice.value} sings midi {n.midi}, range is {lo}..{hi}")

    lead_notes = score.voices[VoiceName.lead]
    repose_onsets = _phrase_final_lead_notes(lead_notes, threshold)
    ticks = _event_ticks(score)

    verticals: list[tuple[int, dict[VoiceName, Note]]] = []
    for t in ticks:
        sounding = {v: n for v in VoiceName if (n := _sounding(score.voices[v], t))}
        # --- crossing rules apply whenever the voices in question sound ---
        if VoiceName.tenor in sounding and VoiceName.lead in sounding:
            if sounding[VoiceName.tenor].midi < sounding[VoiceName.lead].midi:
                report(t, "crossing", "tenor below lead")
        if VoiceName.tenor in sounding and VoiceName.bari in sounding:
            if sounding[VoiceName.bari].midi > sounding[VoiceName.tenor].midi:
                report(t, "crossing", "bari above tenor")
        if VoiceName.bass in sounding:
            for upper in (VoiceName.tenor, VoiceName.lead, VoiceName.bari):
                if upper in sounding and sounding[upper].midi < sounding[VoiceName.bass].midi:
                    report(t, "crossing", f"bass above {upper.value}")
        if len(sounding) == 4:
            verticals.append((t, sounding))

    for t, sounding in verticals:
        chord = _chord_at(score.chords, t)
        lead_note = sounding[VoiceName.lead]
        structural = lead_note.duration >= threshold
        pcs = tuple(sounding[v].midi % 12 for v in VoiceName)

        # --- vocabulary legality ---
        if structural:
            if not classify(pcs):
                report(t, "vocabulary", f"unclassifiable sonority pcs={sorted(set(pcs))}")
        elif chord is not None:
            trio_pcs = {sounding[v].midi % 12 for v in _TRIO}
            if not trio_pcs <= chord_pcs(chord.root_pc, chord.quality):
                report(t, "vocabulary", "trio off chord tones under lead filigree")

        if chord is None:
            continue

        # --- bass discipline ---
        bass_pc = sounding[VoiceName.bass].midi % 12
        seventh = _seventh_pc(chord)
        if seventh is not None and bass_pc == seventh:
            report(t, "bass-seventh", f"bass on the 7th of {chord.quality}")

        # --- doubled third at repose ---
        if lead_note.onset in repose_onsets:
            third_pc = (chord.root_pc + next(
                iv for iv, deg in CHORDS[chord.quality].degrees.items() if deg == "third"
            )) % 12
            if sum(1 for p in pcs if p == third_pc) > 1:
                report(t, "doubled-third", "doubled third at point of repose")

    # --- parallel perfect intervals between consecutive verticals ---
    for (t1, s1), (t2, s2) in zip(verticals, verticals[1:]):
        names = list(VoiceName)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                p1a, p1b = s1[a].midi, s1[b].midi
                p2a, p2b = s2[a].midi, s2[b].midi
                if p1a == p2a or p1b == p2b:
                    continue  # a voice held or repeated: not parallel motion
                iv1, iv2 = abs(p1a - p1b), abs(p2a - p2b)
                if iv1 % 12 == 0 and iv2 % 12 == 0:
                    report(t2, "parallels", f"parallel octaves/unisons {a.value}-{b.value}")
                elif VoiceName.bass in (a, b) and iv1 % 12 == 7 and iv2 % 12 == 7:
                    report(t2, "parallels", f"parallel fifths {a.value}-{b.value}")

    # --- chordal 7ths resolve down by step at chord changes ---
    for c1, c2 in zip(score.chords, score.chords[1:]):
        if c1.end != c2.onset:
            continue  # phrase gap
        if (c1.root_pc, c1.quality) == (c2.root_pc, c2.quality):
            continue
        seventh = _seventh_pc(c1)
        if seventh is None or c1.quality == "dim7":
            continue  # symmetric dim7: the labeled 7th is notational, not functional
        next_pcs = chord_pcs(c2.root_pc, c2.quality)
        lead_after = _sounding(score.voices[VoiceName.lead], c2.onset)
        targets = {(seventh - 1) % 12, (seventh - 2) % 12} & next_pcs
        lead_took = lead_after is not None and lead_after.midi % 12 in targets
        for voice in _TRIO:  # the lead's melody is sacrosanct, exempt
            before = _sounding(score.voices[voice], c1.end - 1)
            after = _sounding(score.voices[voice], c2.onset)
            if before is None or after is None:
                continue
            if before.midi % 12 != seventh or 1 <= before.midi - after.midi <= 2:
                continue
            # transferred resolution: the lead sounds the resolution tone,
            # so the inner voice may take another chord tone instead
            if lead_took and after.midi % 12 in next_pcs:
                continue
            report(
                c2.onset,
                "seventh-resolution",
                f"{voice.value} leaves the 7th of {c1.quality} by "
                f"{after.midi - before.midi:+d} (must resolve down by step)",
            )

    # --- final chord: root-position major triad ---
    if verticals and score.chords:
        t, sounding = verticals[-1]
        final = score.chords[-1]
        if final.quality != "maj":
            report(t, "final-chord", f"final chord is {final.quality}, not a major triad")
        if sounding[VoiceName.bass].midi % 12 != final.root_pc:
            report(t, "final-chord", "final chord not in root position")

    return out


def metrics(score: Score) -> dict:
    """Quality metrics: not violations, but the bands a good chart hits."""
    spans = score.chords
    dom = sum(1 for c in spans if c.quality in _DOM_FAMILY)

    bass_ok = bass_total = 0
    for n in score.voices[VoiceName.bass]:
        chord = _chord_at(spans, n.onset)
        if chord is None:
            continue
        bass_total += 1
        if chord_degree(chord.root_pc, chord.quality, n.midi % 12) in ("root", "fifth"):
            bass_ok += 1

    ring = False
    if spans:
        final = spans[-1]
        last_lead = score.voices[VoiceName.lead][-1]
        last_bass = score.voices[VoiceName.bass][-1]
        last_tenor = score.voices[VoiceName.tenor][-1]
        ring = (
            final.quality == "maj"
            and last_bass.midi % 12 == final.root_pc
            and chord_degree(final.root_pc, final.quality, last_lead.midi % 12) in ("root", "fifth")
            and last_tenor.midi - last_lead.midi <= 9
        )

    return {
        "dom7_family_share": dom / len(spans) if spans else 0.0,
        "bass_root_fifth_share": bass_ok / bass_total if bass_total else 0.0,
        "final_chord_ring": ring,
    }
