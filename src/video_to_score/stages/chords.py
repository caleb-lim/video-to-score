"""Stage 7: full mix -> chord labels with times (Chordino via chord-extractor).

Optional. If chord-extractor or the Chordino Vamp plugin isn't installed, this writes an
empty chord list and the score simply has no chord symbols.
"""
from __future__ import annotations

from pathlib import Path

from ..song import Song
from ..util import log, write_json

NAME = "chords"


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.chords]


def run(song: Song, cfg: dict) -> None:
    try:
        from chord_extractor.extractors import Chordino
    except ImportError:
        log.warning("chords: chord-extractor not installed; skipping chord symbols")
        write_json(song.chords, [])
        return
    try:
        changes = Chordino(roll_on=1).extract(str(song.audio))
    except Exception as e:  # usually the Vamp plugin is missing
        log.warning("chords: Chordino failed (%s); skipping chord symbols", e)
        write_json(song.chords, [])
        return
    out = [{"time": float(c.timestamp), "label": c.chord} for c in changes if c.chord and c.chord != "N"]
    log.info("chords: %d changes", len(out))
    write_json(song.chords, out)
