"""video-to-score <youtube-url | audio file> [options]"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from . import stages
from .config import load_config
from .song import Song
from .util import log


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_") or "song"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="video-to-score", description=__doc__)
    ap.add_argument("source", help="YouTube URL or path to a local audio file")
    ap.add_argument("--name", help="song folder name (default: video id or file name)")
    ap.add_argument("--songs-dir", default="songs", help="where song folders live (default: songs/)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--device", help="override config device: cuda | cpu | mps")
    ap.add_argument("--solo-piano", action="store_true",
                    help="solo piano recording: skip separation/vocals, Transkun on the full mix")
    ap.add_argument("--from-stage", choices=list(stages.BY_NAME),
                    help="force re-run from this stage onward (earlier finished stages are reused)")
    ap.add_argument("--only", choices=list(stages.BY_NAME), help="run just this one stage (forced)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    cfg = load_config(args.config)
    if args.device:
        cfg["device"] = args.device
    cfg["_source"] = args.source

    if args.name:
        name = args.name
    elif Path(args.source).expanduser().exists():
        name = Path(args.source).stem
    else:
        from .stages.download import video_id

        name = video_id(args.source)
    song = Song(Path(args.songs_dir) / _slug(name), demucs_model=cfg["separate"]["model"],
                solo_piano=args.solo_piano)
    log.info("song folder: %s", song.root)

    plan = stages.SOLO_PIANO if args.solo_piano else stages.FULL
    names = [s.NAME for s in plan]
    forced_from = None
    if args.only:
        if args.only not in names:
            ap.error(f"--only {args.only} is not part of this pipeline mode")
        plan = [stages.BY_NAME[args.only]]
        forced_from = 0
    elif args.from_stage:
        if args.from_stage not in names:
            ap.error(f"--from-stage {args.from_stage} is not part of this pipeline mode")
        forced_from = names.index(args.from_stage)

    for i, stage in enumerate(plan):
        forced = forced_from is not None and i >= forced_from
        if not forced and all(p.exists() for p in stage.outputs(song, cfg)):
            log.info("[%s] done already, skipping", stage.NAME)
            continue
        if forced:
            for p in stage.outputs(song, cfg):
                p.unlink(missing_ok=True)
        log.info("[%s] running", stage.NAME)
        try:
            stage.run(song, cfg)
        except Exception as e:
            log.error("[%s] failed: %s", stage.NAME, e)
            return 1

    log.info("Done. Open %s in MuseScore.", song.score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
