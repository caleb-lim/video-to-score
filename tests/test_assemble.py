"""End-to-end check of the score step with synthetic MIDI, beats and chords (no ML models)."""
from music21 import converter, harmony

from video_to_score.config import load_config
from video_to_score.midi_io import write_notes
from video_to_score.segment import Note
from video_to_score.song import Song
from video_to_score.stages import assemble
from video_to_score.util import write_json

BEAT = 0.5  # 120 bpm


def build_song(tmp_path):
    song = Song(tmp_path / "song")
    beats = [BEAT * i for i in range(33)]          # 8 bars of 4/4
    write_json(song.beats, {"beats": beats, "downbeats": beats[::4]})
    # Melody: C D E F, quarter notes, slightly off-grid like a real singer.
    melody = [Note(i * BEAT + 0.02, (i + 1) * BEAT - 0.03, p) for i, p in enumerate([60, 62, 64, 65])]
    write_notes(song.midi("melody"), melody)
    # Piano: a C major chord split across both hands, two bars long.
    piano = [Note(0.0, 4 * BEAT * 2, p) for p in (48, 55, 64, 67)]
    write_notes(song.midi("piano"), piano)
    bass = [Note(0.0, 4 * BEAT, 36), Note(4 * BEAT, 8 * BEAT, 43)]
    write_notes(song.midi("bass"), bass)
    write_json(song.chords, [{"time": 0.0, "label": "C"}, {"time": 4 * BEAT, "label": "G7"}])
    return song


def test_assemble_writes_readable_score(tmp_path):
    song = build_song(tmp_path)
    cfg = load_config(tmp_path / "missing.yaml")
    assemble.run(song, cfg)
    assert song.score.exists()

    score = converter.parse(str(song.score))
    names = [p.partName for p in score.parts]
    assert names == ["Melody", "Piano RH", "Piano LH", "Bass"]

    melody = score.parts[0]
    pitches = [n.pitch.midi for n in melody.recurse().notes if not isinstance(n, harmony.ChordSymbol)]
    assert pitches == [60, 62, 64, 65]
    durs = [float(n.quarterLength) for n in melody.recurse().notes if not isinstance(n, harmony.ChordSymbol)]
    assert durs == [1.0, 1.0, 1.0, 1.0]

    symbols = [c.figure for c in melody.recurse().getElementsByClass(harmony.ChordSymbol)]
    assert symbols == ["C", "G7"]

    ts = melody.recurse().getElementsByClass("TimeSignature")[0]
    assert ts.ratioString == "4/4"
