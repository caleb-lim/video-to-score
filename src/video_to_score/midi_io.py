from __future__ import annotations

from pathlib import Path

import pretty_midi

from .segment import Note


def write_notes(path: Path, notes: list[Note], program: int = 0, name: str = "") -> None:
    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=program, name=name)
    for n in notes:
        inst.notes.append(pretty_midi.Note(velocity=90, pitch=int(n.pitch), start=float(n.onset), end=float(n.offset)))
    pm.instruments.append(inst)
    pm.write(str(path))


def read_notes(path: Path) -> list[Note]:
    """All non-drum notes in a MIDI file, sorted by onset."""
    pm = pretty_midi.PrettyMIDI(str(path))
    notes = [
        Note(n.start, n.end, n.pitch)
        for inst in pm.instruments
        if not inst.is_drum
        for n in inst.notes
    ]
    return sorted(notes, key=lambda n: (n.onset, n.pitch))
