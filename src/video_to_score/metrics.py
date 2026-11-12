"""Note-level transcription metrics (same definitions the singing/piano transcription papers use).

COn      onset within 50 ms                              (ignores pitch)
COnP     onset within 50 ms AND pitch within 50 cents
COnPOff  COnP AND offset within max(50 ms, 20% of note length)
"""
from __future__ import annotations

import numpy as np


def _arrays(notes):
    """notes: iterable of (onset, offset, midi_pitch) -> (intervals, pitches_hz)."""
    notes = [n for n in notes if n[1] > n[0]]
    if not notes:
        return np.zeros((0, 2)), np.zeros(0)
    arr = np.asarray(notes, dtype=float)
    hz = 440.0 * 2.0 ** ((arr[:, 2] - 69.0) / 12.0)
    return arr[:, :2], hz


def note_scores(ref, est, onset_tol: float = 0.05) -> dict[str, float]:
    import mir_eval

    ri, rp = _arrays(ref)
    ei, ep = _arrays(est)
    if len(ri) == 0 or len(ei) == 0:
        return {"COn": 0.0, "COnP": 0.0, "COnPOff": 0.0, "n_ref": len(ri), "n_est": len(ei)}
    _, _, con = mir_eval.transcription.onset_precision_recall_f1(ri, ei, onset_tolerance=onset_tol)
    _, _, conp, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ri, rp, ei, ep, onset_tolerance=onset_tol, offset_ratio=None)
    _, _, conpoff, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ri, rp, ei, ep, onset_tolerance=onset_tol, offset_ratio=0.2, offset_min_tolerance=0.05)
    return {"COn": con, "COnP": conp, "COnPOff": conpoff, "n_ref": len(ri), "n_est": len(ei)}
