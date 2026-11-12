"""Score the melody stage against MIR-ST500 vocal note labels.

1. Get the dataset: git clone https://github.com/york135/singing_transcription_ICASSP2021
   It has the labels (JSON: song id -> [[onset_s, offset_s, midi_pitch], ...]) and a script
   that downloads each song's audio from YouTube. Put the audio in bench/data/mirst500/<id>.mp3
2. Run the pipeline up to the melody stage for each song, e.g.
       for f in bench/data/mirst500/*.mp3; do
         video-to-score "$f" --songs-dir songs/mirst500 --name "$(basename "$f" .mp3)"
       done
   (Use --from-stage melody after changing config.yaml; the slow pitch tracking is cached.)
3. python bench/eval_melody.py --labels <path to MIR-ST500 json> --songs-dir songs/mirst500

Reference point (published state of the art on MIR-ST500): COn ~78, COnP ~70, COnPOff ~53.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from video_to_score.metrics import note_scores
from video_to_score.midi_io import read_notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="MIR-ST500 label JSON")
    ap.add_argument("--songs-dir", default="songs/mirst500")
    ap.add_argument("--ids", nargs="*", help="only these song ids (default: every song folder found)")
    args = ap.parse_args()

    labels = json.loads(Path(args.labels).read_text())
    songs_dir = Path(args.songs_dir)
    ids = args.ids or sorted(p.name for p in songs_dir.iterdir() if (p / "midi" / "melody.mid").exists())

    rows = []
    for sid in ids:
        if sid not in labels:
            print(f"{sid}: no label, skipped")
            continue
        est = [(n.onset, n.offset, n.pitch) for n in read_notes(songs_dir / sid / "midi" / "melody.mid")]
        ref = [tuple(x[:3]) for x in labels[sid]]
        s = note_scores(ref, est)
        rows.append(s)
        print(f"{sid:>6}  COn {s['COn']*100:5.1f}  COnP {s['COnP']*100:5.1f}  "
              f"COnPOff {s['COnPOff']*100:5.1f}  ({s['n_est']} est / {s['n_ref']} ref notes)")

    if rows:
        mean = {k: sum(r[k] for r in rows) / len(rows) for k in ("COn", "COnP", "COnPOff")}
        print(f"\nMEAN over {len(rows)} songs  COn {mean['COn']*100:5.1f}  "
              f"COnP {mean['COnP']*100:5.1f}  COnPOff {mean['COnPOff']*100:5.1f}")


if __name__ == "__main__":
    main()
