"""Beat grid: maps seconds to quantised musical positions so notes land on bar lines."""
from __future__ import annotations

import math
from collections import Counter
from fractions import Fraction

import numpy as np


class BeatGrid:
    def __init__(self, beats: list[float], downbeats: list[float], grid_per_beat: int = 4,
                 end_time: float | None = None):
        b = np.sort(np.asarray(beats, dtype=float))
        if len(b) < 2:
            raise ValueError("need at least two beats to build a grid")
        ival = float(np.median(np.diff(b)))
        self.beat_interval = ival
        end_time = max(end_time or 0.0, float(b[-1])) + ival

        # Extend the grid at constant tempo so every time in [0, end_time] has a beat position.
        head = []
        t = b[0] - ival
        while t > -ival:
            head.append(t)
            t -= ival
        tail = []
        t = b[-1] + ival
        while t < end_time + ival:
            tail.append(t)
            t += ival
        self.beats = np.concatenate([np.array(head[::-1]), b, np.array(tail)])
        self.grid_per_beat = grid_per_beat

        # Meter: most common number of beats between consecutive downbeats.
        d = np.sort(np.asarray(downbeats, dtype=float))
        idx = [int(np.argmin(np.abs(self.beats - x))) for x in d]
        counts = [j - i for i, j in zip(idx, idx[1:]) if j > i]
        self.beats_per_bar = Counter(counts).most_common(1)[0][0] if counts else 4
        first_db = idx[0] if idx else int(np.argmin(np.abs(self.beats)))
        # Shift so the first detected downbeat starts a bar; earlier music becomes pickup bars.
        pickup_bars = math.ceil(first_db / self.beats_per_bar) if first_db > 0 else 0
        self.beat_offset = pickup_bars * self.beats_per_bar - first_db

    @property
    def bpm(self) -> float:
        return 60.0 / self.beat_interval

    def time_to_beat(self, t: float) -> float:
        """Fractional beat index (bar-aligned) for a time in seconds."""
        raw = float(np.interp(t, self.beats, np.arange(len(self.beats))))
        return raw + self.beat_offset

    def quantise(self, t: float) -> int:
        """Nearest grid tick (beat * grid_per_beat)."""
        return int(round(self.time_to_beat(t) * self.grid_per_beat))

    def ticks_to_beats(self, ticks: int) -> Fraction:
        return Fraction(ticks, self.grid_per_beat)
