"""Stage 1: YouTube URL (or a local audio file) -> audio.wav"""
from __future__ import annotations

from pathlib import Path

from ..song import Song
from ..util import log, run_cmd

NAME = "download"


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.audio]


def run(song: Song, cfg: dict) -> None:
    source = cfg["_source"]
    if Path(source).expanduser().exists():
        # Local file: normalise to a 44.1 kHz stereo wav with ffmpeg.
        run_cmd(["ffmpeg", "-y", "-i", Path(source).expanduser(), "-ar", "44100", "-ac", "2", song.audio])
        return

    import yt_dlp

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(song.root / "audio.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
    }
    log.info("Downloading %s", source)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([source])
    if not song.audio.exists():
        raise RuntimeError(f"yt-dlp finished but {song.audio} is missing")


def video_id(url: str) -> str:
    """Folder name for a URL: the YouTube video id."""
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return info["id"]
