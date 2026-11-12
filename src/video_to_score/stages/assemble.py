"""Stage 8: MIDI parts + beat grid + chords -> score.musicxml (one staff per part)."""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from ..grid import BeatGrid
from ..midi_io import read_notes
from ..segment import Note
from ..song import Song
from ..util import log, read_json

NAME = "assemble"

# (midi file part name, staff name, monophonic?, bass clef?)
PARTS = [
    ("melody", "Melody", True, False),
    ("backing", "Backing vocals", False, False),
    ("piano", "Piano", False, None),  # split into RH / LH
    ("guitar", "Guitar", False, False),
    ("other", "Other", False, False),
    ("bass", "Bass", False, True),
]


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.score]


def quantise_notes(notes: list[Note], grid: BeatGrid, monophonic: bool) -> list[tuple[int, int, int]]:
    """-> list of (onset_tick, duration_ticks, pitch). Every note lasts at least one tick."""
    q = []
    for n in notes:
        on = grid.quantise(n.onset)
        off = max(grid.quantise(n.offset), on + 1)
        q.append((on, off, n.pitch))
    q.sort()
    if monophonic:
        # One note at a time: later onset wins, earlier note is cut short; same-tick duplicates dropped.
        mono: list[tuple[int, int, int]] = []
        for on, off, p in q:
            if mono and mono[-1][0] == on:
                continue
            if mono and mono[-1][1] > on:
                mono[-1] = (mono[-1][0], on, mono[-1][2])
            mono.append((on, off, p))
        q = mono
    return [(on, off - on, p) for on, off, p in q if off > on]


def build_part(name: str, qnotes, grid: BeatGrid, beat_ql: Fraction, *, monophonic: bool,
               bass_clef: bool, ts: str, ks, mm=None):
    from music21 import chord, clef, instrument, note, stream

    def ql(ticks: int) -> Fraction:
        return grid.ticks_to_beats(ticks) * beat_ql

    raw = stream.Stream()
    for on, dur, p in qnotes:
        raw.insert(ql(on), note.Note(midi=p, quarterLength=ql(dur)))

    part = stream.Part(id=name)
    part.partName = name
    part.insert(0, instrument.Piano())
    part.insert(0, clef.BassClef() if bass_clef else clef.TrebleClef())
    from music21 import meter

    part.insert(0, meter.TimeSignature(ts))
    part.insert(0, ks)
    if mm is not None:
        part.insert(0, mm)

    if monophonic:
        for n in raw.notes:
            part.insert(n.offset, n)
    else:
        # Overlapping notes -> chords tied across each other's boundaries: readable enough for a draft.
        for c in raw.chordify().flatten().getElementsByClass(chord.Chord):
            part.insert(c.offset, c)
    part.makeRests(fillGaps=True, inPlace=True, timeRangeFromBarDuration=True)
    return part


def run(song: Song, cfg: dict) -> None:
    from music21 import duration, harmony, key, stream, tempo

    a = cfg["assemble"]
    beat_ql = Fraction(a["beat_ql"]).limit_denominator(8)
    bt = read_json(song.beats)

    parts_notes: dict[str, list[Note]] = {}
    for part, *_ in PARTS:
        p = song.midi(part)
        if p.exists():
            parts_notes[part] = read_notes(p)
    if not parts_notes:
        raise RuntimeError("assemble: no MIDI parts found")
    end = max((n.offset for ns in parts_notes.values() for n in ns), default=0.0)
    grid = BeatGrid(bt["beats"], bt["downbeats"], a["grid_per_beat"], end_time=end)

    ts = f"{grid.beats_per_bar}/4" if beat_ql == 1 else f"{grid.beats_per_bar * 3}/8"
    # Key from the melody and bass when available (they carry the tonality), else everything.
    from music21 import note as m21note

    probe = stream.Stream()
    src = [k for k in ("melody", "bass") if k in parts_notes] or list(parts_notes)
    for k in src:
        for n in parts_notes[k]:
            probe.append(m21note.Note(midi=n.pitch, quarterLength=max(n.duration / grid.beat_interval, 0.25)))
    k = probe.analyze("key")
    ks = key.KeySignature(k.sharps)
    mm = tempo.MetronomeMark(number=round(grid.bpm), referent=duration.Duration(float(beat_ql)))
    log.info("assemble: %s, %s, ~%d bpm", k, ts, round(grid.bpm))

    score = stream.Score()
    first = True
    for part, name, mono, bass in PARTS:
        if part not in parts_notes:
            continue
        notes = parts_notes[part]
        if part == "piano":
            split = a["piano_split_midi"]
            groups = [("Piano RH", [n for n in notes if n.pitch >= split], False),
                      ("Piano LH", [n for n in notes if n.pitch < split], True)]
        else:
            groups = [(name, notes, bass)]
        for staff, ns, bclef in groups:
            if not ns:
                continue
            q = quantise_notes(ns, grid, mono)
            p = build_part(staff, q, grid, beat_ql, monophonic=mono, bass_clef=bclef, ts=ts,
                           ks=key.KeySignature(ks.sharps), mm=mm if first else None)
            if part == "melody" and song.chords.exists():
                for c in read_json(song.chords):
                    try:
                        sym = harmony.ChordSymbol(c["label"].replace(":", ""))
                    except Exception:
                        continue
                    p.insert(float(grid.ticks_to_beats(grid.quantise(c["time"])) * beat_ql), sym)
            score.insert(0, p)
            first = False

    score.write("musicxml", fp=str(song.score))
    log.info("wrote %s", song.score)
