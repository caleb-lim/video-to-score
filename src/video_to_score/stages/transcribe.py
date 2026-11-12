"""Stage 4: instrument stems -> MIDI.

Piano stem -> Transkun (piano-specific: notes, velocity, pedal).
Bass / guitar / other / backing vocals -> Basic Pitch (general-purpose, polyphonic).
In --solo-piano mode the whole mix goes to Transkun and nothing else runs.
"""
from __future__ import annotations

import os
import shlex
import shutil
import tempfile
from pathlib import Path

from ..song import Song
from ..util import log, resolve_device, run_cmd

NAME = "transcribe"


def _basic_pitch_jobs(song: Song, cfg: dict) -> dict[str, Path]:
    jobs = {s: song.stem(s) for s in cfg["transcribe"]["basic_pitch_stems"]}
    if song.backing.exists():
        jobs["backing"] = song.backing
    return jobs


def outputs(song: Song, cfg: dict) -> list[Path]:
    if song.solo_piano:
        return [song.midi("piano")]
    return [song.midi("piano")] + [song.midi(p) for p in _basic_pitch_jobs(song, cfg)]


def transkun(src: Path, dst: Path, device: str) -> None:
    run_cmd(["transkun", src, dst, "--device", device])


def basic_pitch(cmd: str, src: Path, dst: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_cmd(shlex.split(os.path.expanduser(cmd)) + [tmp, str(src)])
        produced = list(Path(tmp).glob("*.mid"))
        if not produced:
            raise RuntimeError(f"basic-pitch wrote no MIDI for {src}")
        shutil.move(str(produced[0]), dst)


def run(song: Song, cfg: dict) -> None:
    device = resolve_device(cfg)
    if song.solo_piano:
        transkun(song.audio, song.midi("piano"), device)
        return

    piano_src = song.stem(cfg["transcribe"]["piano_stem"])
    if not song.midi("piano").exists():
        transkun(piano_src, song.midi("piano"), device)

    for part, src in _basic_pitch_jobs(song, cfg).items():
        dst = song.midi(part)
        if dst.exists():
            continue
        if not src.exists():
            log.warning("transcribe: %s missing, skipping %s", src, part)
            continue
        basic_pitch(cfg["transcribe"]["basic_pitch_cmd"], src, dst)
