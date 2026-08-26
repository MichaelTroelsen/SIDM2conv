"""Tests for pyscript/abpage_chips.py -- the A/B page measures rail.

Each test here pins one rule the task's verify names. The rules are not
stylistic: every one of them is a shape of wrong answer this repo has actually
shipped, or that docs/AUDIO_LISTENING_CALIBRATION.md measured and warned about.
"""
from __future__ import annotations

import json
import math
import struct
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyscript import abpage as A
from pyscript import abpage_chips as C


def write_wav(path: Path, seconds=1.0, rate=44100, freq=440.0, amp=0.5,
              channels=1):
    n = int(rate * seconds)
    frames = bytearray()
    for i in range(n):
        v = int(amp * 32767 * math.sin(2 * math.pi * freq * i / rate))
        for _ in range(channels):
            frames += struct.pack("<h", v)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(bytes(frames))
    return path


def write_silence(path: Path, seconds=1.0, rate=44100):
    return write_wav(path, seconds=seconds, rate=rate, freq=1.0, amp=0.0)


def write_notes(path: Path, n_notes=8, note_s=0.25, gap_s=0.05, rate=44100,
                freq=440.0, shift_ms=0.0):
    """A burst train with real attacks, so the onset detector has something to
    find. A continuous sine has NO onsets -- spectral flux needs an edge."""
    frames = bytearray()
    for _ in range(int(rate * shift_ms / 1000.0)):
        frames += struct.pack("<h", 0)
    for k in range(n_notes):
        for i in range(int(rate * note_s)):
            env = math.exp(-4.0 * i / (rate * note_s))       # a decaying attack
            v = int(0.6 * env * 32767 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", max(-32768, min(32767, v)))
        for _ in range(int(rate * gap_s)):
            frames += struct.pack("<h", 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(bytes(frames))
    return path


# ---------------------------------------------------------------------------
# THE RULE THAT MATTERS MOST: no renderer is invoked
# ---------------------------------------------------------------------------

def test_chips_invoke_no_renderer_at_all(tmp_path, monkeypatch):
    """The whole affordability argument is that this reads staged bytes.

    Enforced by making every subprocess entry point explode: if any code path
    reaches for vsid, sidplayfp or siddump, this fails loudly instead of
    quietly costing a render per song across a 100-song corpus.
    """
    import subprocess

    def boom(*a, **k):
        raise AssertionError("a renderer/subprocess was invoked: %r" % (a,))

    for attr in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, attr, boom)

    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=447.0)
    chips, blind = C.chips_for_pair(a, b)
    assert chips  # it really did produce numbers


# ---------------------------------------------------------------------------
# The vacuous-agreement guard
# ---------------------------------------------------------------------------

def test_two_silences_report_both_silent_not_a_zero_delta(tmp_path):
    """A delta between two silent renders is 0.0, and 0.0 reads as perfect.

    Same shape as the vacuous-100 bug fidelity_common.exercised() exists to
    catch. The chip must say so in words.
    """
    a = write_silence(tmp_path / "a.wav")
    b = write_silence(tmp_path / "b.wav")
    chips, blind = C.chips_for_pair(a, b)
    assert chips == {"signal": "both silent"}
    assert "0.0" not in json.dumps(chips)
    assert "read as perfect agreement" in blind["signal"]


def test_one_silent_side_is_called_out(tmp_path):
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_silence(tmp_path / "b.wav", seconds=0.5)
    chips, blind = C.chips_for_pair(a, b)
    assert chips["signal"] == "ours is silent"
    assert "not fidelity" in blind["signal"]


def test_identical_input_gives_zero_deltas_and_is_not_refused(tmp_path):
    """Identical audio SHOULD read as zero -- the guard is about silence, not
    about refusing every zero. A guard that fired here would be useless."""
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=440.0)
    chips, _ = C.chips_for_pair(a, b)
    assert "signal" not in chips
    assert chips["level"] == "+0.0 dB"
    assert chips["level dBA"] == "+0.0 dBA"


# ---------------------------------------------------------------------------
# Calibration rule 1: onset is opt-in, ordinal only, and carries no gate
# ---------------------------------------------------------------------------

def test_onset_is_omitted_by_default(tmp_path):
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=447.0)
    chips, _ = C.chips_for_pair(a, b)
    assert "onset" not in chips and "offset" not in chips


def test_onset_on_audio_with_no_attacks_says_so_rather_than_scoring_it(tmp_path):
    """A continuous tone has no onsets. Reporting 0% (or 100%) for that would be
    a number where there is no measurement -- the vacuous case again."""
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=447.0)
    chips, blind = C.chips_for_pair(a, b, with_onset=True)
    assert chips["onset"] == "no onsets"
    assert "%" not in chips["onset"]
    assert "nothing to match" in blind["onset"]


def test_onset_when_present_is_labelled_ordinal_with_no_floor(tmp_path):
    a = write_notes(tmp_path / "a.wav")
    b = write_notes(tmp_path / "b.wav", shift_ms=8.0)
    chips, blind = C.chips_for_pair(a, b, with_onset=True)
    assert "onset" in chips and "%" in chips["onset"]
    assert "offset" in chips
    note = blind["onset"]
    assert "ORDINAL ONLY" in note
    assert "NO GATE" in note and "NO FLOOR" in note
    assert "64.7" in note and "85-91" in note      # the measured numbers, in place
    assert "never as pass/fail" in note


def test_no_literal_double_percent_leaks_into_chips_or_notes(tmp_path):
    """A '%%' in a string that is never %-formatted reaches the page literally.

    Half these notes ARE %-formatted and must double their signs; half are not
    and must not. Getting it backwards is invisible in code review and obvious
    on the page, which is the wrong order.
    """
    a = write_notes(tmp_path / "a.wav")
    b = write_notes(tmp_path / "b.wav", shift_ms=8.0)
    chips, blind = C.chips_for_pair(a, b, with_onset=True)
    for k, v in list(chips.items()) + list(blind.items()):
        assert "%%" not in v, (k, v)


def test_a_unitless_chip_has_no_trailing_space(tmp_path):
    a = write_notes(tmp_path / "a.wav")
    b = write_notes(tmp_path / "b.wav", shift_ms=8.0)
    chips, _ = C.chips_for_pair(a, b)
    for k, v in chips.items():
        assert v == v.strip(), (k, repr(v))


def test_no_chip_renders_as_a_passfail_verdict(tmp_path):
    """No chip value may be a verdict word. The rail reports, it never judges."""
    a = write_notes(tmp_path / "a.wav")
    b = write_notes(tmp_path / "b.wav", shift_ms=8.0)
    chips, _ = C.chips_for_pair(a, b, with_onset=True)
    banned = ("pass", "fail", "ok", "good", "bad", "clean", "broken")
    for k, v in chips.items():
        assert v.lower() not in banned, (k, v)


# ---------------------------------------------------------------------------
# Calibration rule 2: several features, each labelled with what it cannot see
# ---------------------------------------------------------------------------

def test_several_independent_features_are_emitted_not_one_composite(tmp_path):
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=447.0)
    chips, _ = C.chips_for_pair(a, b)
    for k in ("level", "level dBA", "brightness", "rolloff", "noisiness", "pitch"):
        assert k in chips, k
    assert "score" not in chips and "overall" not in chips


def test_every_chip_carries_a_blind_note(tmp_path):
    a = write_notes(tmp_path / "a.wav")
    b = write_notes(tmp_path / "b.wav", shift_ms=8.0)
    chips, blind = C.chips_for_pair(a, b, with_onset=True)
    missing = [k for k in chips if not blind.get(k)]
    assert not missing, missing


def test_the_dBA_blind_note_records_that_it_is_noise_on_a_pitch_defect(tmp_path):
    """The calibration's sharpest finding, and the one most likely to be lost:
    a null dBA does NOT clear a tuning error."""
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=447.0)
    _c, blind = C.chips_for_pair(a, b)
    note = blind["level dBA"]
    assert "0.011" in note
    assert "does not clear a tuning error" in note
    assert "chroma" in note


# ---------------------------------------------------------------------------
# Chroma: all-zero means no evidence, never agreement
# ---------------------------------------------------------------------------

def test_chroma_with_no_pitched_energy_says_no_evidence(tmp_path, monkeypatch):
    """audio_listen's own chroma_shift_description refuses to describe a shift
    from an all-zero chroma; this must not compute a distance from it."""
    real = C.extract_features

    def zero_chroma(x, sr, **kw):
        f = real(x, sr, **kw)
        f.chroma = np.zeros(12)
        return f

    monkeypatch.setattr(C, "extract_features", zero_chroma)
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=447.0)
    chips, blind = C.chips_for_pair(a, b)
    assert chips["pitch"] == "no pitched energy"
    assert "absence of evidence, not agreement" in blind["pitch"]


def test_chroma_distance_is_bounded_and_zero_on_identical(tmp_path):
    a = write_wav(tmp_path / "a.wav", seconds=0.5, freq=440.0)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, freq=440.0)
    chips, _ = C.chips_for_pair(a, b)
    assert float(chips["pitch"]) == pytest.approx(0.0, abs=1e-6)


def test_chroma_moves_when_the_pitch_class_changes(tmp_path):
    """A semitone apart must not read as identical -- otherwise the one feature
    that fires on a pitch defect is inert."""
    a = write_wav(tmp_path / "a.wav", seconds=1.0, freq=440.0)     # A
    b = write_wav(tmp_path / "b.wav", seconds=1.0, freq=523.25)    # C
    chips, _ = C.chips_for_pair(a, b)
    assert float(chips["pitch"]) > 0.1


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

def test_sample_rate_mismatch_is_refused_not_resampled(tmp_path):
    a = write_wav(tmp_path / "a.wav", seconds=0.5, rate=44100)
    b = write_wav(tmp_path / "b.wav", seconds=0.5, rate=22050)
    with pytest.raises(C.ChipRefusal) as e:
        C.chips_for_pair(a, b)
    assert "sample-rate mismatch" in str(e.value)


def test_band_scale_mismatch_is_refused(tmp_path, monkeypatch):
    """A 'linear' and a 'mel' AudioFeatures are not comparable; a delta between
    them looks like a real difference and is not one."""
    real = C.extract_features
    seen = {"n": 0}

    def alternating(x, sr, **kw):
        f = real(x, sr, **kw)
        seen["n"] += 1
        f.band_scale = "linear" if seen["n"] == 1 else "mel"
        return f

    monkeypatch.setattr(C, "extract_features", alternating)
    a = write_wav(tmp_path / "a.wav", seconds=0.5)
    b = write_wav(tmp_path / "b.wav", seconds=0.5)
    with pytest.raises(C.ChipRefusal) as e:
        C.chips_for_pair(a, b)
    assert "band-scale mismatch" in str(e.value)


# ---------------------------------------------------------------------------
# Wiring into abpage: the JSON round-trips and reaches the page
# ---------------------------------------------------------------------------

@pytest.fixture
def staged(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    d = tmp_path / "build" / "listen"
    write_wav(d / "Tune.original.wav", seconds=0.5, freq=440.0)
    write_wav(d / ("Tune.%s.wav" % A.OURS), seconds=0.5, freq=447.0)
    return tmp_path


def test_chips_subcommand_writes_json_and_build_puts_it_in_the_rail(staged):
    assert A.chips(None, False, 0) == 0
    out = staged / "build" / "listen" / "chips.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "Tune" in doc and "chips" in doc["Tune"] and "blind" in doc["Tune"]

    assert A.build(out, None, None, None) == 0
    html = (staged / "build" / "listen" / "Tune.html").read_text(encoding="utf-8")
    assert "not in --chips" not in html          # the gap-chip is gone
    assert "level dBA" in html
    assert 'class="chip hasblind"' in html       # the caveat is ON the number
    assert "does not clear a tuning error" in html


def test_chips_rows_accepts_both_the_flat_and_annotated_shapes(tmp_path):
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps({"T": {"onset": "94%"}}), encoding="utf-8")
    assert A.chips_rows(flat) == {"T": {"onset": "94%"}}
    assert A.blind_rows(flat) == {}

    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps(
        {"T": {"chips": {"onset": "94%"}, "blind": {"onset": "ordinal"}}}),
        encoding="utf-8")
    assert A.chips_rows(ann) == {"T": {"onset": "94%"}}
    assert A.blind_rows(ann) == {"T": {"onset": "ordinal"}}


def test_a_refused_pair_is_named_not_silently_dropped(staged, capsys):
    """A tune missing from the rail must be distinguishable from a tune whose
    numbers were all fine."""
    write_wav(staged / "build" / "listen" / ("Tune.%s.wav" % A.OURS),
              seconds=0.5, rate=22050)
    assert A.chips(None, False, 0) == 0
    out = capsys.readouterr().out
    assert "REFUSED Tune" in out and "sample-rate mismatch" in out


def test_chips_runs_as_a_SCRIPT_not_only_as_an_import(tmp_path):
    """Running `py -3 pyscript/abpage.py chips` puts pyscript/ on sys.path[0],
    NOT the repo root, so `pyscript.abpage_chips` is not importable.

    Every other test in this file imports the module, which silently puts ROOT
    on the path and hides the failure completely. This one shells out, which is
    the only way to see it -- and it is exactly the "caught only by running the
    tool" class the fidelity docstring records.
    """
    import subprocess

    # The subprocess resolves ROOT from __file__, so it reads the REAL
    # build/listen whatever cwd is. That makes staged state none of this
    # test's business: assert on the import path only. Exit 2 ("no staged
    # pairs") is a perfectly good pass -- it means the module loaded and the
    # command ran.
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run(
        [sys.executable, str(root / "pyscript" / "abpage.py"), "chips",
         "-o", str(tmp_path / "chips.json")],
        capture_output=True, text=True, cwd=str(tmp_path))
    assert "ModuleNotFoundError" not in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode in (0, 2), (r.returncode, r.stdout, r.stderr)


def test_build_without_chips_still_works(staged):
    """The chips layer is additive; `build` must stay stdlib-only and usable
    with no measurement at all."""
    assert A.build(None, None, None, None) == 0
    html = (staged / "build" / "listen" / "Tune.html").read_text(encoding="utf-8")
    assert "not in --chips" in html
