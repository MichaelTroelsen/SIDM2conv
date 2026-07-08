"""Tests for the DMC (Bjerregaard / Demo Music Creator) parser.

Locks in the RE'd facts: signature-based table location (relocation-safe),
the chromatic freq table, tempo detection, and the track/sector decode
producing onset-validated note streams.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from sidm2.dmc_parser import load_sid, DMCModule, decode_song, decode_track
from sidm2.fidelity_common import freq_to_semi

CORP = os.path.join(ROOT, "SID", "JohannesBjerregaard")


def _mod(name):
    d, la, h = load_sid(os.path.join(CORP, f"{name}.sid"))
    return DMCModule(d, la), la, h


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_balloon_tables():
    """Balloon (load $1000) — the reference addresses from the RE."""
    m, la, h = _mod("Balloon")
    assert la == 0x1000
    assert m.lay.sector_lo == 0x1900 and m.lay.sector_hi == 0x1980
    assert m.lay.sound == 0x1500
    assert m.lay.freq == 0x135F
    assert m.lay.trk_lo == 0x104A and m.lay.trk_hi == 0x104D
    assert m.lay.tempo_reload == 4          # 4 frames/tick baked in code


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_relocation_safe():
    """A relocated tune ($C000) locates the same tables offset by load."""
    m, la, h = _mod("Cant_Stop")
    assert la == 0xC000
    # every table sits in the relocated image, above load
    for addr in (m.lay.sector_lo, m.lay.sound, m.lay.freq, m.lay.trk_lo):
        assert la <= addr < la + 0x1000


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_freq_table_is_chromatic():
    """The freq table must be a rising chromatic scale (~1.0595 per step)."""
    m, la, h = _mod("Balloon")
    prev = 0
    for note in range(2, 40):
        f = m.note_freq(note)
        assert f > prev, f"freq table not rising at note {note}"
        # each row within ~a semitone of the standard chromatic index
        assert abs(freq_to_semi(f) - note) <= 1
        prev = f


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_track_terminates():
    """Track decode stops at $FF (loop) / $FE (end), not a runaway."""
    m, la, h = _mod("Dummy_II")
    for v in range(3):
        sectors, loop = decode_track(m, v)
        assert len(sectors) < 512


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_decode_produces_notes():
    """decode_song yields tick-timed note events with valid pitches."""
    m, la, h = _mod("Dummy_II")
    voices = decode_song(m, tick_budget=200)
    assert sum(len(v) for v in voices) > 20
    notes = [n for v in voices for _, n in v if n.pitch >= 0]
    assert notes and all(0 <= n.pitch < 128 for n in notes)


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_onset_validation_main_player():
    """A couple of main-player tunes decode to >=90% onset match vs siddump."""
    from sidm2.fidelity_common import siddump_note_onsets
    for name in ("Dummy_II", "Blobby"):
        path = os.path.join(CORP, f"{name}.sid")
        m, la, h = _mod(name)
        fpt = m.lay.tempo_reload + 1
        voices = decode_song(m, tick_budget=800)
        real = siddump_note_onsets(path, ["-a0", "-t12"])
        matched = total = 0
        for v in range(3):
            rl = real[v] if isinstance(real, (list, tuple)) else real.get(v, [])
            rf = set(fr for fr, _ in rl if fr < 560)
            if len(rf) < 3:
                continue
            pf = set(tk * fpt for tk, n in voices[v] if n.pitch >= 0)
            best = max(sum(1 for fr in rf if fr in set(x + ph for x in pf))
                       for ph in range(10))
            matched += best
            total += len(rf)
        assert total and 100 * matched / total >= 90, f"{name} onsets low"
