from video_to_score.metrics import note_scores

REF = [(0.0, 0.5, 60), (0.5, 1.0, 62), (1.0, 2.0, 64)]


def test_perfect_match():
    s = note_scores(REF, REF)
    assert s["COn"] == s["COnP"] == s["COnPOff"] == 1.0


def test_wrong_pitch_counts_for_onset_only():
    est = [(0.0, 0.5, 60), (0.5, 1.0, 63), (1.0, 2.0, 64)]
    s = note_scores(REF, est)
    assert s["COn"] == 1.0
    assert abs(s["COnP"] - 2 / 3) < 1e-9


def test_empty_estimate():
    assert note_scores(REF, [])["COnP"] == 0.0
