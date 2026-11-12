# video-to-score

Paste a YouTube link to a song (ballads work best) and get a **draft score** to arrange a piano cover from. The MusicXML file has one staff per part:

| Staff | Comes from | Tool |
|---|---|---|
| Melody (with chord symbols) | lead vocal stem | torchcrepe pitch tracking + note segmentation |
| Backing vocals | backing vocal stem (once a karaoke splitter is configured) | Basic Pitch |
| Piano RH / Piano LH | piano stem | Transkun |
| Guitar, Other | guitar / other stems | Basic Pitch |
| Bass | bass stem | Basic Pitch |

Bar lines come from beat_this and chords from Chordino. Open the result in MuseScore, check each part against its stem, and build your arrangement from there.

> **Status:** v0 scaffold. The parts that don't need ML models (segmentation, beat grid, quantisation, MusicXML assembly, metrics) have unit tests and pass. The model stages are thin wrappers that haven't been run end to end yet. Expect to fix CLI flags or API details the first time you run each one.

## Pipeline

```
YouTube URL ─► download (yt-dlp) ─┬─► separate (Demucs htdemucs_6s) ─┬─► vocal_split ─► melody (torchcrepe + segment)
                                  │                                  └─► transcribe (Transkun piano, Basic Pitch others)
                                  └─► beats (beat_this) · chords (Chordino)
                                                       all ─► assemble (quantise to beat grid → MusicXML)
```

Each stage reads and writes files in `songs/<name>/`. If a stage's outputs already exist it's skipped, so re-tuning the melody step doesn't re-run Demucs.

```
songs/<name>/
  audio.wav
  stems/htdemucs_6s/audio/{vocals,bass,piano,guitar,drums,other}.wav
  vocals/lead.wav (backing.wav)
  midi/{melody,backing,piano,guitar,other,bass}.mid
  analysis/{beats.json, chords.json, lead_f0.npz}
  score.musicxml
```

## Setup

Prerequisites: Python **3.11** (3.10–3.12 work; avoid 3.13), `ffmpeg` on your PATH, git, MuseScore 4. An NVIDIA GPU is optional but makes separation about 5–10× faster.

```bash
git clone https://github.com/caleb-lim/video-to-score && cd video-to-score
python3.11 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 1. PyTorch FIRST: pick the CUDA or CPU build for your machine at https://pytorch.org
pip install torch torchaudio            # <- replace with the command pytorch.org gives you

# 2. This package + the ML stack
pip install -e ".[ml,dev]"

# 3. Basic Pitch (bass/guitar/other). Try it in the same venv first:
pip install -e ".[basicpitch]"
#    If it fights torch over numpy, put it in its own venv instead and point
#    transcribe.basic_pitch_cmd in config.yaml at that venv's `basic-pitch` executable.

# 4. Optional, chord symbols: needs the Chordino Vamp plugin installed system-wide
#    (Vamp plugins / "nnls-chroma" pack), then:
pip install -e ".[chords]"

pip freeze > requirements.lock          # snapshot a working environment
pytest                                  # unit tests should pass
```

On a CPU-only machine set `device: cpu` in `config.yaml`, or pass `--device cpu`.

## Usage

```bash
video-to-score "https://www.youtube.com/watch?v=..."           # full pipeline
video-to-score song.mp3 --name my-song                          # local file
video-to-score "<url>" --from-stage melody                      # re-run melody onward (pitch curve stays cached)
video-to-score "<url>" --only assemble                          # just rebuild the score
video-to-score chopin.wav --solo-piano                          # solo piano: Transkun on the full mix
```

### Smoke-test each tool first

Before trusting the pipeline, run each tool once by hand on a sparse piano-and-vocal ballad:

```bash
S=songs/test && mkdir -p $S
yt-dlp -x --audio-format wav -o "$S/audio.%(ext)s" "<url>"
demucs -n htdemucs_6s -o $S/stems $S/audio.wav
transkun $S/stems/htdemucs_6s/audio/piano.wav $S/piano.mid
basic-pitch $S $S/stems/htdemucs_6s/audio/bass.wav
```

Listen to the stems. If separation is muddy, every stage after it will be too. If a command's flags differ in your installed version, fix the matching wrapper in `src/video_to_score/stages/`.

## Tuning the melody

The melody staff is the weakest link, and it's where tuning time pays off. All the knobs are under `melody:` in `config.yaml`:

| Knob | Raise it if… | Lower it if… |
|---|---|---|
| `split_semitones` | vibrato or slides split one note into several | separate notes get merged |
| `split_hold_frames` | short scoops create extra notes | quick passing notes go missing |
| `min_note_s` | there are lots of tiny glitch notes | fast runs lose notes |
| `smooth_frames` | the pitch is jittery | note changes get blurred |
| `periodicity_threshold` | breaths and noise come out as notes | quiet sung notes go missing |

Loop: edit `config.yaml` → `video-to-score <url> --from-stage melody` → check in MuseScore, or score it with the benchmark below.

## Benchmarks

**Melody vs MIR-ST500** (500 pop songs with hand-labelled vocal notes and YouTube links):

```bash
git clone https://github.com/york135/singing_transcription_ICASSP2021 bench/data/mirst500-repo
# use its download script to fetch audio into bench/data/mirst500/<id>.mp3, then:
for f in bench/data/mirst500/*.mp3; do
  video-to-score "$f" --songs-dir songs/mirst500 --name "$(basename "$f" .mp3)"
done
python bench/eval_melody.py --labels <MIR-ST500 label json> --songs-dir songs/mirst500
```

For reference, the published state of the art is about COn 78 / COnP 70 / COnPOff 53.

**Piano vs MAESTRO** (audio with aligned MIDI). Transkun reports about 98 onset F1 on MAESTRO's test split; YouTube recordings will score lower.

```bash
video-to-score maestro/<file>.wav --solo-piano --name maestro1
python bench/eval_midi.py songs/maestro1/midi/piano.mid maestro/<file>.midi
```

**Score readability:** compare a `--solo-piano` run on a Chopin Ballade against the IMSLP score, bar by bar. This is the hardest case (rubato, runs, hand crossings), so treat the result as the worst you'll see.

## Known limitations (v0)

- **Melody segmentation is heuristic.** Expect extra short notes on runs and misplaced pickups.
- **Vocal split is a pass-through** until you configure `vocal_split.command` with a karaoke model, so adlibs land on the melody staff.
- **Piano hands are split at a fixed pitch** (`piano_split_midi`, default middle C).
- **Polyphonic parts are chordified**, so overlapping notes become tied chords. That's readable enough for a draft, not engraving quality.
- **Assumes a steady beat.** Free-time intros quantise badly; play those by ear.
- **Downloading from YouTube breaches its ToS.** Use this for personal practice only.

## Layout

```
src/video_to_score/
  cli.py        stage runner (skip finished stages, --from-stage / --only)
  config.py     defaults + config.yaml merge
  song.py       paths inside a song folder
  segment.py    pitch curve → notes (pure numpy, unit-tested)
  grid.py       beat grid + quantisation (unit-tested)
  metrics.py    COn / COnP / COnPOff via mir_eval
  midi_io.py
  stages/       download, separate, vocal_split, transcribe, melody, beats, chords, assemble
bench/          eval_melody.py (MIR-ST500), eval_midi.py (MAESTRO / any reference MIDI)
tests/
```
