import numpy as np

from video_to_score.segment import hz_to_midi, segment_notes

HOP = 0.01


def curve(*pieces):
    """pieces: (midi_pitch or None, seconds, vibrato_semitones)"""
    out = []
    for pitch, dur, vib in pieces:
        n = int(round(dur / HOP))
        t = np.arange(n) * HOP
        if pitch is None:
            out.append(np.full(n, np.nan))
        else:
            out.append(pitch + vib * np.sin(2 * np.pi * 5.5 * t))
    midi = np.concatenate(out)
    return np.arange(len(midi)) * HOP, midi


def test_hz_to_midi():
    m = hz_to_midi(np.array([440.0, 0.0, np.nan, 261.6256]))
    assert m[0] == 69
    assert np.isnan(m[1]) and np.isnan(m[2])
    assert abs(m[3] - 60) < 1e-3


def test_vibrato_does_not_split_and_steps_do():
    t, m = curve((69, 0.5, 0.4), (72, 0.5, 0.4), (None, 0.1, 0), (72, 0.3, 0.0))
    notes = segment_notes(t, m)
    assert [n.pitch for n in notes] == [69, 72, 72]
    assert abs(notes[0].onset - 0.0) < 0.02
    assert abs(notes[1].onset - 0.5) < 0.05
    assert abs(notes[2].onset - 1.1) < 0.02


def test_short_glitch_is_ignored():
    t, m = curve((69, 0.3, 0), (75, 0.03, 0), (69, 0.3, 0))
    notes = segment_notes(t, m)
    assert [n.pitch for n in notes] == [69]


def test_tiny_gap_same_pitch_merges():
    t, m = curve((67, 0.3, 0), (None, 0.03, 0), (67, 0.3, 0))
    notes = segment_notes(t, m)
    assert len(notes) == 1
    assert abs(notes[0].duration - 0.63) < 0.03


def test_too_short_notes_dropped():
    t, m = curve((None, 0.2, 0), (64, 0.05, 0), (None, 0.2, 0))
    assert segment_notes(t, m) == []
