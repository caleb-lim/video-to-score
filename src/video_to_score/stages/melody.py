"""Stage 5: lead vocal -> melody notes.

Two steps, cached separately so you can re-tune segmentation without re-running CREPE:
  1. torchcrepe pitch tracking  -> analysis/lead_f0.npz   (slow; delete the file to redo)
  2. segment.segment_notes      -> midi/melody.mid        (fast; tune config.yaml `melody:`)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..midi_io import write_notes
from ..segment import hz_to_midi, segment_notes
from ..song import Song
from ..util import log

NAME = "melody"


def outputs(song: Song, cfg: dict) -> list[Path]:
    return [song.midi("melody")]


def track_pitch(song: Song, cfg: dict) -> None:
    import torch
    import torchaudio
    import torchcrepe

    m = cfg["melody"]
    audio, sr = torchaudio.load(str(song.lead))
    audio = audio.mean(0, keepdim=True)  # stereo stem -> mono, shape (1, samples)
    hop = int(sr * m["hop_ms"] / 1000)
    device = cfg["device"] if cfg["device"] != "cuda" or torch.cuda.is_available() else "cpu"
    log.info("torchcrepe (%s) on %s", m["crepe_model"], device)
    pitch, periodicity = torchcrepe.predict(
        audio, sr, hop,
        fmin=m["fmin_hz"], fmax=m["fmax_hz"],
        model=m["crepe_model"], batch_size=2048,
        device=device, return_periodicity=True,
    )
    periodicity = torchcrepe.filter.median(periodicity, 3)
    pitch = torchcrepe.threshold.At(m["periodicity_threshold"])(pitch, periodicity)
    f0 = pitch.squeeze(0).cpu().numpy()
    times = np.arange(len(f0)) * hop / sr
    np.savez(song.f0, times=times, f0_hz=f0, periodicity=periodicity.squeeze(0).cpu().numpy())


def run(song: Song, cfg: dict) -> None:
    if not song.f0.exists():
        track_pitch(song, cfg)
    data = np.load(song.f0)
    m = cfg["melody"]
    notes = segment_notes(
        data["times"], hz_to_midi(data["f0_hz"]),
        smooth_frames=m["smooth_frames"],
        split_semitones=m["split_semitones"],
        split_hold_frames=m["split_hold_frames"],
        min_note_s=m["min_note_s"],
        merge_gap_s=m["merge_gap_s"],
    )
    log.info("melody: %d notes", len(notes))
    write_notes(song.midi("melody"), notes, program=0, name="Melody")
