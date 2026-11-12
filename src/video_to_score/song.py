"""Paths inside one song folder. Every stage reads and writes files here."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Song:
    root: Path
    demucs_model: str = "htdemucs_6s"
    solo_piano: bool = False

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        for d in (self.root, self.vocals_dir, self.midi_dir, self.analysis_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def audio(self) -> Path:
        return self.root / "audio.wav"

    @property
    def stems_dir(self) -> Path:
        return self.root / "stems"

    def stem(self, name: str) -> Path:
        # Demucs writes <out>/<model>/<track name>/<stem>.wav; our track is always "audio".
        return self.stems_dir / self.demucs_model / "audio" / f"{name}.wav"

    @property
    def vocals_dir(self) -> Path:
        return self.root / "vocals"

    @property
    def lead(self) -> Path:
        return self.vocals_dir / "lead.wav"

    @property
    def backing(self) -> Path:
        return self.vocals_dir / "backing.wav"

    @property
    def midi_dir(self) -> Path:
        return self.root / "midi"

    def midi(self, part: str) -> Path:
        return self.midi_dir / f"{part}.mid"

    @property
    def analysis_dir(self) -> Path:
        return self.root / "analysis"

    @property
    def beats(self) -> Path:
        return self.analysis_dir / "beats.json"

    @property
    def chords(self) -> Path:
        return self.analysis_dir / "chords.json"

    @property
    def f0(self) -> Path:
        return self.analysis_dir / "lead_f0.npz"

    @property
    def score(self) -> Path:
        return self.root / "score.musicxml"
