from fractions import Fraction

from video_to_score.grid import BeatGrid


def make_grid():
    beats = [0.25 + 0.5 * i for i in range(17)]          # 120 bpm
    downbeats = [beats[i] for i in range(1, 17, 4)]       # one pickup beat before bar 1
    return BeatGrid(beats, downbeats, grid_per_beat=4), beats


def test_meter_and_tempo():
    g, _ = make_grid()
    assert g.beats_per_bar == 4
    assert abs(g.bpm - 120) < 1e-6


def test_first_downbeat_lands_on_a_bar_line():
    g, beats = make_grid()
    b = g.time_to_beat(beats[1])
    assert b % g.beats_per_bar == 0


def test_quantise_snaps_to_sixteenths():
    g, beats = make_grid()
    on_beat = g.quantise(beats[5])
    assert on_beat % 4 == 0
    assert g.quantise(beats[5] + 0.13) == on_beat + 1   # 0.125 s = one 16th at 120 bpm
    assert g.ticks_to_beats(6) == Fraction(3, 2)


def test_times_before_first_beat_are_non_negative():
    g, _ = make_grid()
    assert g.time_to_beat(0.0) >= 0
