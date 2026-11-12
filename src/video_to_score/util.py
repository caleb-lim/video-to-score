from __future__ import annotations

import json
import logging
import shlex
import subprocess
from pathlib import Path
from typing import Any, Sequence

log = logging.getLogger("video_to_score")


def run_cmd(cmd: Sequence[str] | str, **kw: Any) -> None:
    """Run a command, echoing it, and raise with its stderr if it fails."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    cmd = [str(c) for c in cmd]
    log.info("$ %s", shlex.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {shlex.join(cmd)}\n{proc.stderr[-4000:]}"
        )


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def resolve_device(cfg: dict) -> str:
    """'auto' -> cuda if a GPU is visible (e.g. `docker run --gpus all`), else cpu."""
    dev = str(cfg.get("device", "auto")).lower()
    if dev not in ("auto", "cuda"):
        return dev
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    if dev == "cuda":
        log.warning("device=cuda but no GPU is visible; falling back to cpu")
    return "cpu"
