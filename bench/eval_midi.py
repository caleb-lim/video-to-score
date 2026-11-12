"""Compare a transcribed MIDI file to a reference MIDI (e.g. MAESTRO's aligned MIDI).

Example (Chopin / MAESTRO benchmark of the piano stage):
    video-to-score maestro/2018/<file>.wav --solo-piano --name maestro_test1
    python bench/eval_midi.py songs/maestro_test1/midi/piano.mid maestro/2018/<file>.midi

Reference point: Transkun V2 reports ~98 onset F1 on the MAESTRO test split; expect lower
on YouTube recordings (different pianos, rooms, compression).
"""
from __future__ import annotations

import argparse

from video_to_score.metrics import note_scores
from video_to_score.midi_io import read_notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("estimate")
    ap.add_argument("reference")
    args = ap.parse_args()
    est = [(n.onset, n.offset, n.pitch) for n in read_notes(args.estimate)]
    ref = [(n.onset, n.offset, n.pitch) for n in read_notes(args.reference)]
    s = note_scores(ref, est)
    print(f"COn {s['COn']*100:.1f}  COnP {s['COnP']*100:.1f}  COnPOff {s['COnPOff']*100:.1f}  "
          f"({s['n_est']} est / {s['n_ref']} ref notes)")


if __name__ == "__main__":
    main()
