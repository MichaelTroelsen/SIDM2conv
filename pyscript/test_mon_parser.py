"""Tests for the Maniacs of Noise (Jeroen Tel) parser — sidm2/mon_parser.py.

Validates table location + note decode against Hawkeye.sid subtune 3 (the main theme).
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

HAWKEYE = os.path.join(ROOT, "SID", "Tel_Jeroen", "Hawkeye.sid")
pytestmark = pytest.mark.skipif(not os.path.exists(HAWKEYE), reason="Hawkeye SID missing")

from sidm2.mon_parser import load_sid, MON  # noqa: E402


def _mon():
    d, la, h = load_sid(HAWKEYE)
    return MON(d, la, subtune=3)


def test_load_embedded_address():
    d, la, h = load_sid(HAWKEYE)
    assert la == 0x7AE0                      # PSID load=0 -> embedded load word


def test_table_location():
    m = _mon()
    assert m.tbl_olptr == 0x83FC             # orderlist-ptr index table
    assert m.tbl_speed == 0x83F5             # per-subtune speed
    assert m.tbl_pat == 0x8409               # pattern pointer table
    assert m.tbl_freq == 0x8337              # note->freq table
    assert m.olset_hi == 0x7B
    assert m.speed == 3                       # subtune 3 speed = $03


def test_subtune3_orderlist_pointers():
    m = _mon()
    # subtune 3 ($83FC[3]=$1A) -> set at $7B1A -> V0 $8E2D, V1 $8E30, V2 $8E33
    assert m._orderlist_ptr(0) == 0x8E2D
    assert m._orderlist_ptr(1) == 0x8E30
    assert m._orderlist_ptr(2) == 0x8E33


def _siddump_abs_notes(seconds=10):
    txt = subprocess.run(["py", "-3", "pyscript/siddump_complete.py", HAWKEYE,
                          "-a3", f"-t{seconds}"], capture_output=True, text=True,
                         cwd=ROOT).stdout
    V = {0: [], 1: [], 2: []}
    for ln in txt.splitlines():
        if not ln.startswith("|") or "Frame" in ln:
            continue
        c = [x.strip() for x in ln.split("|")]
        if len(c) < 6:
            continue
        for vi, cell in enumerate(c[2:5]):
            mm = re.match(r"^([0-9A-F]{4})\s+[A-G][-#]\d\s+([0-9A-F]{2})", cell)
            if mm and mm.group(1) != "0000":
                V[vi].append(int(mm.group(2), 16) - 0x80)
    return V


def test_notes_match_siddump():
    # the MoN note byte == siddump's abs-note value; the parser's note sequence must
    # match the real player's, note-for-note (validated prefix, all 3 voices).
    m = _mon()
    real = _siddump_abs_notes()
    total_ok = total = 0
    for v in range(3):
        mine = [e.note for e in m.voices[v]]
        n = min(len(mine), len(real[v]))
        assert n > 0
        match = sum(1 for i in range(n) if mine[i] == real[v][i])
        total_ok += match
        total += n
        assert match == n, f"voice {v}: {match}/{n} (parser {mine[:n]} vs {real[v][:n]})"
    assert total_ok == total and total >= 24
