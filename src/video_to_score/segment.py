"""Pitch curve -> discrete notes. Pure numpy so it can be unit-tested and tuned quickly.

This is the step that decides how good the melody staff is. The knobs (config.yaml, `melody:`):
  smooth_frames      running median on the pitch curve (kills jitter, keeps note changes)
  split_semitones    how far pitch must leave the current note's median to count as a new note
  split_hold_frames  ...and for how many consecutive frames (stops vibrato causing splits)
  min_note_s         notes shorter than this are dropped (catches scoops and glitches)
  merge_gap_s        same-pitch notes separated by a tiny gap are merged
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Note:
    onset: float   # seconds
    offset: float  # seconds
    pitch: int     # MIDI note number

    @property
    def duration(self) -> float:
        return self.offset - self.onset


def hz_to_midi(f0_hz: np.ndarray) -> np.ndarray:
    f = np.asarray(f0_hz, dtype=float)
    out = np.full_like(f, np.nan)
    ok = np.isfinite(f) & (f > 0)
    out[ok] = 69.0 + 12.0 * np.log2(f[ok] / 440.0)
    return out


def running_median(x: np.ndarray, window: int) -> np.ndarray:
    """Median filter that ignores NaN (unvoiced) frames and never fills gaps."""
    if window <= 1:
        return x.copy()
    half = window // 2
    padded = np.pad(x, half, constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)
    with np.errstate(all="ignore"):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(windows, axis=1)
    med[~np.isfinite(x)] = np.nan
    return med


def segment_notes(
    times: np.ndarray,
    midi: np.ndarray,
    *,
    smooth_frames: int = 7,
    split_semitones: float = 0.7,
    split_hold_frames: int = 4,
    min_note_s: float = 0.08,
    merge_gap_s: float = 0.05,
) -> list[Note]:
    """Segment a frame-wise MIDI pitch curve (NaN = unvoiced) into notes."""
    times = np.asarray(times, dtype=float)
    midi = running_median(np.asarray(midi, dtype=float), smooth_frames)
    n = len(midi)
    if n == 0:
        return []
    hop = float(np.median(np.diff(times))) if n > 1 else 0.01

    # 1. Split into (start, end) frame ranges.
    segments: list[tuple[int, int]] = []
    start = None
    pending = 0  # consecutive frames that disagree with the current note
    for i in range(n):
        voiced = np.isfinite(midi[i])
        if not voiced:
            if start is not None:
                segments.append((start, i - pending))
                start, pending = None, 0
            continue
        if start is None:
            start, pending = i, 0
            continue
        ref = np.median(midi[start : i - pending]) if i - pending > start else midi[start]
        if abs(midi[i] - ref) > split_semitones:
            pending += 1
            if pending >= split_hold_frames:
                split_at = i - pending + 1
                segments.append((start, split_at))
                start, pending = split_at, 0
        else:
            pending = 0
    if start is not None:
        segments.append((start, n))

    # 2. Frame ranges -> notes, dropping very short ones.
    notes: list[Note] = []
    for s, e in segments:
        if e <= s:
            continue
        onset = times[s]
        offset = times[e - 1] + hop
        if offset - onset < min_note_s:
            continue
        notes.append(Note(onset, offset, int(round(float(np.median(midi[s:e]))))))

    # 3. Merge same-pitch neighbours with tiny gaps (re-articulated by the tracker, not the singer).
    merged: list[Note] = []
    for note in notes:
        if merged and note.pitch == merged[-1].pitch and note.onset - merged[-1].offset < merge_gap_s:
            merged[-1].offset = note.offset
        else:
            merged.append(note)
    return merged
