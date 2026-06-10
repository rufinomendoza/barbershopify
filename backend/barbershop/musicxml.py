"""MusicXML serializer for the barbershop two-staff convention.

One fixed subset, fully controlled: part P1 = Tenor (voice 1, stems up)
+ Lead (voice 2, stems down) on a treble clef sounding an octave lower;
part P2 = Baritone (voice 1, stems up) + Bass (voice 2, stems down) on a
bass clef. Notes are split at barlines with ties; gaps become rests.

Spelling is chord-aware: chord tones are spelled as intervals above the
root (so the 3rd of D7 is F-sharp, never G-flat); everything else falls
back to nearest-on-the-circle-of-fifths relative to the key. dim7
sevenths are deliberately spelled as major sixths (A over C, not B-double-
flat) — singers read those.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from barbershop.score import ChordSpan, Note, Score, VoiceName

_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_LETTERS = ["C", "D", "E", "F", "G", "A", "B"]
_FIFTHS_INDEX = {"F": -1, "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5}

# quality -> interval -> (letter steps above root, semitones)
_DEGREE_SPELLING: dict[str, dict[int, tuple[int, int]]] = {
    "maj": {0: (0, 0), 4: (2, 4), 7: (4, 7)},
    "min": {0: (0, 0), 3: (2, 3), 7: (4, 7)},
    "dom7": {0: (0, 0), 4: (2, 4), 7: (4, 7), 10: (6, 10)},
    "maj6": {0: (0, 0), 4: (2, 4), 7: (4, 7), 9: (5, 9)},
    "min6": {0: (0, 0), 3: (2, 3), 7: (4, 7), 9: (5, 9)},
    "min7": {0: (0, 0), 3: (2, 3), 7: (4, 7), 10: (6, 10)},
    "dom9": {0: (0, 0), 2: (1, 2), 4: (2, 4), 7: (4, 7), 10: (6, 10)},
    "dim7": {0: (0, 0), 3: (2, 3), 6: (4, 6), 9: (5, 9)},
    "halfdim7": {0: (0, 0), 3: (2, 3), 6: (4, 6), 10: (6, 10)},
    "aug": {0: (0, 0), 4: (2, 4), 8: (4, 8)},
    "dom7b5": {0: (0, 0), 4: (2, 4), 6: (4, 6), 10: (6, 10)},
    "aug7": {0: (0, 0), 4: (2, 4), 8: (4, 8), 10: (6, 10)},
}

_TYPES = [(1920, "whole"), (960, "half"), (480, "quarter"), (240, "eighth"), (120, "16th"), (60, "32nd")]


def _spell_pc(pc: int, key_fifths: int) -> tuple[str, int]:
    """Spell a bare pitch class nearest the key on the circle of fifths."""
    best: tuple[str, int] | None = None
    best_score = 1e9
    for letter, natural in _LETTER_PC.items():
        for alter in (-1, 0, 1):
            if (natural + alter) % 12 != pc:
                continue
            index = _FIFTHS_INDEX[letter] + 7 * alter
            score = abs(index - key_fifths) + 0.1 * abs(alter)
            if score < best_score:
                best_score, best = score, (letter, alter)
    assert best is not None
    return best


def _spell_midi(midi: int, key_fifths: int, chord: ChordSpan | None) -> tuple[str, int, int]:
    pc = midi % 12
    step = alter = None
    if chord is not None:
        table = _DEGREE_SPELLING[chord.quality]
        interval = (pc - chord.root_pc) % 12
        if interval in table:
            root_step, root_alter = _spell_pc(chord.root_pc, key_fifths)
            steps, _ = table[interval]
            step = _LETTERS[(_LETTERS.index(root_step) + steps) % 7]
            alter = (pc - _LETTER_PC[step]) % 12
            alter = alter - 12 if alter > 6 else alter
            if abs(alter) > 2:  # degenerate (e.g. triple flat): fall back
                step = alter = None
    if step is None:
        step, alter = _spell_pc(pc, key_fifths)
    octave = (midi - alter - _LETTER_PC[step]) // 12 - 1
    return step, alter, octave


def _chord_at(chords: list[ChordSpan], tick: int) -> ChordSpan | None:
    for c in chords:
        if c.onset <= tick < c.end:
            return c
    return None


def _type_and_dots(duration: int) -> tuple[str | None, int]:
    for base, name in _TYPES:
        if duration == base:
            return name, 0
        if duration == base * 3 // 2:
            return name, 1
        if duration == base * 7 // 4:
            return name, 2
    for base, name in _TYPES:
        if base <= duration:
            return name, 0
    return "32nd", 0


def _split_at_barlines(note: Note, tpm: int) -> list[tuple[int, int, str | None]]:
    """(onset, duration, tie) pieces; tie in {None,'start','stop','both'}."""
    pieces = []
    pos, remaining = note.onset, note.duration
    while remaining > 0:
        room = tpm - (pos % tpm)
        d = min(remaining, room)
        pieces.append((pos, d))
        pos += d
        remaining -= d
    out = []
    for i, (p, d) in enumerate(pieces):
        first, last = i == 0, i == len(pieces) - 1
        tie = None if first and last else "start" if first else "stop" if last else "both"
        out.append((p, d, tie))
    return out


def _emit_note(
    parent: ET.Element,
    score: Score,
    note: Note | None,
    onset: int,
    duration: int,
    voice_number: int,
    stem: str,
    tie: str | None,
    *,
    full_measure_rest: bool = False,
) -> None:
    el = ET.SubElement(parent, "note")
    if note is None:
        ET.SubElement(el, "rest", {"measure": "yes"} if full_measure_rest else {})
    else:
        pitch = ET.SubElement(el, "pitch")
        step, alter, octave = _spell_midi(note.midi, score.key.fifths, _chord_at(score.chords, onset))
        ET.SubElement(pitch, "step").text = step
        if alter:
            ET.SubElement(pitch, "alter").text = str(alter)
        ET.SubElement(pitch, "octave").text = str(octave)
    ET.SubElement(el, "duration").text = str(duration)
    if note is not None and tie in ("start", "both"):
        ET.SubElement(el, "tie", {"type": "start"})
    if note is not None and tie in ("stop", "both"):
        ET.SubElement(el, "tie", {"type": "stop"})
    ET.SubElement(el, "voice").text = str(voice_number)
    if not full_measure_rest:
        type_name, dots = _type_and_dots(duration)
        if type_name:
            ET.SubElement(el, "type").text = type_name
        for _ in range(dots):
            ET.SubElement(el, "dot")
    if note is not None:
        ET.SubElement(el, "stem").text = stem
        if tie in ("start", "both") or tie in ("stop", "both"):
            notations = ET.SubElement(el, "notations")
            if tie in ("start", "both"):
                ET.SubElement(notations, "tied", {"type": "start"})
            if tie in ("stop", "both"):
                ET.SubElement(notations, "tied", {"type": "stop"})
    if note is not None and note.lyric is not None and tie not in ("stop", "both"):
        lyric = ET.SubElement(el, "lyric")
        ET.SubElement(lyric, "syllabic").text = note.lyric.syllabic.value
        ET.SubElement(lyric, "text").text = note.lyric.text
        if note.lyric.extend:
            ET.SubElement(lyric, "extend")


def _measure_stream(notes: list[Note], tpm: int, m: int) -> list[tuple[int, int, Note | None, str | None]]:
    """(onset, duration, note|None, tie) covering measure m completely."""
    lo, hi = m * tpm, (m + 1) * tpm
    items: list[tuple[int, int, Note | None, str | None]] = []
    for note in notes:
        for onset, duration, tie in _split_at_barlines(note, tpm):
            if lo <= onset < hi:
                items.append((onset, duration, note, tie))
    items.sort(key=lambda x: x[0])
    out: list[tuple[int, int, Note | None, str | None]] = []
    cursor = lo
    for onset, duration, note, tie in items:
        if onset > cursor:
            out.append((cursor, onset - cursor, None, None))
        out.append((onset, duration, note, tie))
        cursor = onset + duration
    if cursor < hi:
        out.append((cursor, hi - cursor, None, None))
    return out


_PARTS: list[tuple[str, str, list[tuple[VoiceName, int, str]]]] = [
    ("P1", "Tenor & Lead", [(VoiceName.tenor, 1, "up"), (VoiceName.lead, 2, "down")]),
    ("P2", "Baritone & Bass", [(VoiceName.bari, 1, "up"), (VoiceName.bass, 2, "down")]),
]


def to_musicxml(score: Score) -> str:
    tpm = score.time.ticks_per_measure
    num_measures = max(1, score.num_measures)
    root = ET.Element("score-partwise", {"version": "3.1"})
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = score.title
    part_list = ET.SubElement(root, "part-list")
    for part_id, part_name, _ in _PARTS:
        sp = ET.SubElement(part_list, "score-part", {"id": part_id})
        ET.SubElement(sp, "part-name").text = part_name

    for part_id, _, voices in _PARTS:
        part = ET.SubElement(root, "part", {"id": part_id})
        for m in range(num_measures):
            measure = ET.SubElement(part, "measure", {"number": str(m + 1)})
            if m == 0:
                attrs = ET.SubElement(measure, "attributes")
                ET.SubElement(attrs, "divisions").text = "480"
                key = ET.SubElement(attrs, "key")
                ET.SubElement(key, "fifths").text = str(score.key.fifths)
                ET.SubElement(key, "mode").text = score.key.mode
                time = ET.SubElement(attrs, "time")
                ET.SubElement(time, "beats").text = str(score.time.beats)
                ET.SubElement(time, "beat-type").text = str(score.time.beat_type)
                clef = ET.SubElement(attrs, "clef")
                if part_id == "P1":
                    ET.SubElement(clef, "sign").text = "G"
                    ET.SubElement(clef, "line").text = "2"
                    ET.SubElement(clef, "clef-octave-change").text = "-1"
                else:
                    ET.SubElement(clef, "sign").text = "F"
                    ET.SubElement(clef, "line").text = "4"
                if part_id == "P1":
                    direction = ET.SubElement(measure, "direction", {"placement": "above"})
                    dtype = ET.SubElement(direction, "direction-type")
                    metronome = ET.SubElement(dtype, "metronome")
                    ET.SubElement(metronome, "beat-unit").text = "quarter"
                    ET.SubElement(metronome, "per-minute").text = f"{score.tempo:g}"
                    ET.SubElement(direction, "sound", {"tempo": f"{score.tempo:g}"})

            for i, (voice_name, voice_number, stem) in enumerate(voices):
                if i == 1:
                    backup = ET.SubElement(measure, "backup")
                    ET.SubElement(backup, "duration").text = str(tpm)
                stream = _measure_stream(score.voices.get(voice_name, []), tpm, m)
                whole_rest = len(stream) == 1 and stream[0][2] is None
                for onset, duration, note, tie in stream:
                    _emit_note(
                        measure, score, note, onset, duration, voice_number, stem, tie,
                        full_measure_rest=whole_rest,
                    )

    ET.indent(root)
    body = ET.tostring(root, encoding="unicode")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 '
        'Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n' + body
    )
