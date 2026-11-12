"""Stage 6: full mix -> beat and downbeat times (beat_this). These become the bar lines."""
from __future__ import annotations

from pathlib import Path

from ..song import Song
from ..util import log, resolve_device, write_json

NAME = "beats"


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.beats]


def run(song: Song, cfg: dict) -> None:
    from beat_this.inference import File2Beats

    device = resolve_device(cfg)
    f2b = File2Beats(checkpoint_path=cfg["beats"]["checkpoint"], device=device, dbn=cfg["beats"]["dbn"])
    beats, downbeats = f2b(str(song.audio))
    beats = [float(b) for b in beats]
    downbeats = [float(d) for d in downbeats]
    log.info("beats: %d beats, %d downbeats", len(beats), len(downbeats))
    write_json(song.beats, {"beats": beats, "downbeats": downbeats})
