"""Config loading: defaults deep-merged with an optional config.yaml."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "device": "auto",
    "separate": {"model": "htdemucs_6s"},
    "vocal_split": {"command": None},
    "transcribe": {
        "basic_pitch_cmd": "basic-pitch",
        "basic_pitch_stems": ["bass", "guitar", "other"],
        "piano_stem": "piano",
    },
    "melody": {
        "crepe_model": "full",
        "hop_ms": 10,
        "fmin_hz": 65,
        "fmax_hz": 1047,
        "periodicity_threshold": 0.21,
        "smooth_frames": 7,
        "split_semitones": 0.7,
        "split_hold_frames": 4,
        "min_note_s": 0.08,
        "merge_gap_s": 0.05,
    },
    "beats": {"checkpoint": "final0", "dbn": False},
    "assemble": {"grid_per_beat": 4, "beat_ql": 1.0, "piano_split_midi": 60},
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = Path("config.yaml")
    path = Path(path)
    user = {}
    if path.exists():
        user = yaml.safe_load(path.read_text()) or {}
    return _merge(DEFAULTS, user)
