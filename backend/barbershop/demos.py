"""Built-in demo inputs that bypass audio analysis entirely.

Two public-domain tunes transcribed note-for-note:
- "Yankee Doodle" (traditional, 18th century) — also the canonical
  text-setting test case later.
- "Good Morning to All" (Mildred J. Hill, 1893) — the Happy Birthday
  tune; period-appropriate and melodically certain.

Input chords are deliberately coarse (one or two per measure): showing
how the engine substitutes and embellishes them is the point of the demo.
"""
from __future__ import annotations

from barbershop.arranger.arrange import ArrangeInput
from barbershop.score import ChordSpan, KeySig, Lyric, Note, Syllabic, TimeSig

Q = 480  # quarter
H = 960  # half
DH = 1440  # dotted half
E = 240  # eighth
DE = 360  # dotted eighth
S = 120  # sixteenth

# pitch helpers (octave 4 = middle C octave)
C3, D3, E3, F3, G3, A3, B3 = 48, 50, 52, 53, 55, 57, 59
C4, D4, E4, F4, G4, A4, B4 = 60, 62, 64, 65, 67, 69, 71
C5 = 72


def _notes(measure_len: int, spec: list[list[tuple[int, int]]]) -> list[Note]:
    """spec: per measure, list of (midi, duration); -1 midi = rest."""
    out: list[Note] = []
    for m, contents in enumerate(spec):
        t = m * measure_len
        for midi, dur in contents:
            if midi >= 0:
                out.append(Note(onset=t, duration=dur, midi=midi))
            t += dur
    return out


def _lyrics(melody: list[Note], tokens: list[str | None]) -> list[Note]:
    """Attach lyrics; tokens use '-' edges for syllabic position
    ("yan-", "-kee", "-a-"), None marks a melisma of the previous syllable."""
    assert len(melody) == len(tokens), f"{len(melody)} notes vs {len(tokens)} tokens"
    last_lyric: Lyric | None = None
    for note, token in zip(melody, tokens):
        if token is None:
            if last_lyric is not None:
                last_lyric.extend = True
            continue
        begin, end = token.startswith("-"), token.endswith("-")
        text = token.strip("-")
        if begin and end:
            syllabic = Syllabic.middle
        elif end:
            syllabic = Syllabic.begin
        elif begin:
            syllabic = Syllabic.end
        else:
            syllabic = Syllabic.single
        note.lyric = Lyric(text=text, syllabic=syllabic)
        last_lyric = note.lyric
    return melody


def _chords(measure_len: int, spec: list[list[tuple[int, str, int]]]) -> list[ChordSpan]:
    """spec: per measure, list of (root_pc, quality, duration)."""
    out: list[ChordSpan] = []
    for m, contents in enumerate(spec):
        t = m * measure_len
        for root, quality, dur in contents:
            out.append(ChordSpan(onset=t, duration=dur, root_pc=root, quality=quality))
            t += dur
    return out


YANKEE_DOODLE = ArrangeInput(
    title="Yankee Doodle",
    key=KeySig(fifths=0, mode="major"),
    time=TimeSig(beats=4, beat_type=4),
    tempo=104,
    melody=_lyrics(_notes(4 * Q, [
        [(C4, Q), (C4, Q), (D4, Q), (E4, Q)],   # Yan-kee Doo-dle
        [(C4, Q), (E4, Q), (D4, Q), (G3, Q)],   # went to town a-
        [(C4, Q), (C4, Q), (D4, Q), (E4, Q)],   # rid-ing on a
        [(C4, H), (B3, H)],                     # po-ny
        [(C4, Q), (C4, Q), (D4, Q), (E4, Q)],   # stuck a feath-er
        [(F4, Q), (E4, Q), (D4, Q), (C4, Q)],   # in his cap and
        [(B3, Q), (G3, Q), (A3, Q), (B3, Q)],   # called it mac-a-
        [(C4, H), (C4, H)],                     # ro-ni
    ]), [
        "yan-", "-kee", "doo-", "-dle",
        "went", "to", "town", "a-",
        "-rid-", "-ing", "on", "a",
        "po-", "-ny",
        "stuck", "a", "feath-", "-er",
        "in", "his", "cap", "and",
        "called", "it", "mac-", "-a-",
        "-ro-", "-ni",
    ]),
    chords=_chords(4 * Q, [
        [(0, "maj", 4 * Q)],
        [(0, "maj", 2 * Q), (7, "dom7", 2 * Q)],
        [(0, "maj", 4 * Q)],
        [(0, "maj", 2 * Q), (7, "dom7", 2 * Q)],
        [(0, "maj", 4 * Q)],
        [(5, "maj", 2 * Q), (0, "maj", 2 * Q)],
        [(7, "dom7", 4 * Q)],
        [(0, "maj", 4 * Q)],
    ]),
)


GOOD_MORNING = ArrangeInput(
    title="Good Morning to All",
    key=KeySig(fifths=0, mode="major"),
    time=TimeSig(beats=3, beat_type=4),
    tempo=84,
    melody=_lyrics(_notes(3 * Q, [
        [(-1, Q), (-1, Q), (G3, DE), (G3, S)],  # (pickup) good mor-
        [(A3, Q), (G3, Q), (C4, Q)],            # -ning to you
        [(B3, H), (G3, DE), (G3, S)],           # (you) good mor-
        [(A3, Q), (G3, Q), (D4, Q)],            # -ning to you
        [(C4, H), (G3, DE), (G3, S)],           # (you) good mor-
        [(G4, Q), (E4, Q), (C4, Q)],            # -ning dear chil-
        [(B3, Q), (A3, Q), (F4, DE), (F4, S)],  # -dren good mor-
        [(E4, Q), (C4, Q), (D4, Q)],            # -ning to all
        [(C4, DH)],
    ]), [
        "good", "morn-",
        "-ing", "to", "you",
        None, "good", "morn-",
        "-ing", "to", "you",
        None, "good", "morn-",
        "-ing", "dear", "chil-",
        "-dren", None, "good", "morn-",
        "-ing", "to", "all",
        None,
    ]),
    chords=_chords(3 * Q, [
        [(0, "maj", 3 * Q)],
        [(0, "maj", 3 * Q)],
        [(7, "dom7", 3 * Q)],
        [(7, "dom7", 3 * Q)],
        [(0, "maj", 3 * Q)],
        [(0, "maj", 3 * Q)],
        [(5, "maj", 3 * Q)],
        [(0, "maj", Q), (7, "dom7", 2 * Q)],
        [(0, "maj", 3 * Q)],
    ]),
)


DEMOS: dict[str, ArrangeInput] = {
    "yankee-doodle": YANKEE_DOODLE,
    "good-morning-to-all": GOOD_MORNING,
}
