"""Stage 3: vocal stem -> lead.wav (+ backing.wav).

v0 passes the whole vocal stem through as the lead. To split lead vs backing, set
vocal_split.command in config.yaml to a karaoke-model command, e.g. something like
    audio-separator {input} --model_filename <karaoke model> ...
then make sure it writes {lead} and {backing}.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ..song import Song
from ..util import log, run_cmd

NAME = "vocal_split"


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.lead]


def run(song: Song, cfg: dict) -> None:
    vocals = song.stem("vocals")
    template = cfg["vocal_split"].get("command")
    if not template:
        log.info("vocal_split: no model configured, using the full vocal stem as lead")
        shutil.copy(vocals, song.lead)
        return
    run_cmd(template.format(input=vocals, lead=song.lead, backing=song.backing))
    if not song.lead.exists():
        raise RuntimeError(f"vocal_split command ran but did not write {song.lead}")
