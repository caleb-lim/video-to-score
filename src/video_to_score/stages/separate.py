"""Stage 2: audio.wav -> stems (Demucs)."""
from __future__ import annotations

import sys
from pathlib import Path

from ..song import Song
from ..util import run_cmd

NAME = "separate"
STEMS_6 = ["vocals", "bass", "piano", "guitar", "drums", "other"]
STEMS_4 = ["vocals", "bass", "drums", "other"]


def _stems(cfg: dict) -> list[str]:
    return STEMS_6 if cfg["separate"]["model"].endswith("6s") else STEMS_4


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.stem(s) for s in _stems(cfg)]


def run(song: Song, cfg: dict) -> None:
    run_cmd([
        sys.executable, "-m", "demucs",
        "-n", cfg["separate"]["model"],
        "-d", cfg["device"],
        "-o", song.stems_dir,
        song.audio,
    ])
