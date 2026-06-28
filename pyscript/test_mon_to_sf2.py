"""Tests for the MoN Stage-A transpiler — bin/mon_to_sf2.py.

Builds a Driver-11 SF2 from Hawkeye subtune 3 and validates that the emitted SF2,
when played back, reproduces the original player's note onsets (note + frame).
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

HAWKEYE = os.path.join(ROOT, "SID", "Tel_Jeroen", "Hawkeye.sid")
pytestmark = pytest.mark.skipif(not os.path.exists(HAWKEYE), reason="Hawkeye SID missing")


def _load_mod(name, relpath):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_emit_and_structure():
    from sidm2.mon_parser import load_sid, MON
    mon_to_sf2 = _load_mod("mon_to_sf2", os.path.join("bin", "mon_to_sf2.py"))
    d, la, _ = load_sid(HAWKEYE)
    m = MON(d, la, 3)
    used = mon_to_sf2.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = mon_to_sf2.build_instruments(m, used)
    # subtune 3 uses exactly 3 instruments ($0A,$0B,$18) -> 3 compact slots
    assert len(instr_rows) == len(used) == 3
    assert set(idx_map) == set(used)
    sequences, orderlists = mon_to_sf2.build_structured(m, 0, idx_map)
    # subtune 3 = one pattern per voice -> 3 sequences, one orderlist entry each
    assert len(sequences) == 3
    assert [len(o) for o in orderlists] == [1, 1, 1]


@pytest.mark.parametrize("subtune", [2, 3])
def test_sf2_roundtrip_onsets(subtune):
    # the emitted SF2, played back, must reproduce the original onsets exactly
    # (note + aligned frame), all 3 voices. Subtune 2 also exercises the $40-$5F
    # orderlist pattern-repeat counter; subtune 3 is the simple case.
    val = _load_mod("mon_sf2_validate", os.path.join("bin", "mon_sf2_validate.py"))
    os.chdir(ROOT)
    os.makedirs("out", exist_ok=True)
    probe = os.path.join("out", f"_mon_test_probe_{subtune}.sid")
    open(probe, "wb").write(val.build_probe(HAWKEYE, subtune))
    orig = val.onsets(HAWKEYE, [f"-a{subtune}", "-t12"])
    sf2 = val.onsets(probe, ["-t12"])
    deltas = [sf2[v][0][0] - orig[v][0][0] for v in range(3) if orig[v] and sf2[v]]
    off = sorted(deltas)[len(deltas) // 2]
    for v in range(3):
        o = orig[v]
        limit = o[-1][0]
        s = [(f - off, nm) for (f, nm) in sf2[v] if f - off <= limit + 1]
        assert len(s) == len(o), f"subtune {subtune} voice {v}: {len(s)} vs {len(o)}"
        assert s == o, f"subtune {subtune} voice {v}: {s} vs {o}"
