"""Pipeline stages, in run order.

Each stage module exposes:
    NAME: str
    outputs(song, cfg) -> list[Path]   files the stage produces (used to skip finished work)
    run(song, cfg) -> None
"""
from . import assemble, beats, chords, download, melody, separate, transcribe, vocal_split

FULL = [download, separate, vocal_split, transcribe, melody, beats, chords, assemble]
SOLO_PIANO = [download, transcribe, beats, assemble]

BY_NAME = {m.NAME: m for m in FULL}
