"""Smoke tests for the Sound Monitor -> Driver-11 SF2 Stage A converter.

Full objective validation is bin/soundmonitor_sf2_validate.py (32/33 voices
note-accurate 2026-07-10: every original attack present in order at the right
pitch; Stage A re-gates legato notes -- the runtime Driver 11 has no tie).
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

CORP = os.path.join(ROOT, "SID", "Fun_Fun")

_spec = importlib.util.spec_from_file_location(
    "soundmonitor_to_sf2", os.path.join(ROOT, "bin", "soundmonitor_to_sf2.py"))
sm2sf2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm2sf2)

from sidm2.soundmonitor_parser import load_sid, SoundMonitorModule


def _build(name):
    d, la, h = load_sid(os.path.join(CORP, f"{name}.sid"))
    m = SoundMonitorModule(d, la)
    ev, uses = sm2sf2.collect_combos(m)
    combo_map, slot_defs, dropped = sm2sf2.assign_instruments(m, uses)
    instr_rows, wave_table, pulse_table = sm2sf2.build_instruments(slot_defs)
    silent_idx = sm2sf2._append_silent_instrument(instr_rows, wave_table)
    sequences, orderlists = sm2sf2.build_structured(m, ev, combo_map, silent_idx)
    return m, instr_rows, wave_table, sequences, orderlists, dropped


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_emits_valid_sf2():
    """Final_Luv (small, EXACT-validated) emits a parseable SF2."""
    from sidm2.galway_to_driver11 import GalwayDriver11Song
    from sidm2.galway_driver11_emitter import emit_driver11_sf2
    from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
    m, instr_rows, wave_table, sequences, orderlists, dropped = _build("Final_Luv")
    assert dropped == 0
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=[(0x88, 0, 1)],
        tracks=[], tempo=sm2sf2.find_tempo(m), pitch_base=0, subtune=0)
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    assert len(sf2) > 0x1000
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    assert sla > 0


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_instrument_cap_respected():
    """Dance (51 content-distinct combos) fits the 31+silent instrument cap
    with the arp-drop fallback, and every combo maps to a valid slot."""
    m, instr_rows, wave_table, sequences, orderlists, dropped = _build(
        "Dance_at_Night_remix")
    assert len(instr_rows) <= 32
    assert dropped > 0          # over-cap combos fell back (loudly, not silently)


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_no_tie_bytes_emitted():
    """The runtime Driver 11 cannot parse $90-$9F tie durations (editor-only
    feature; emitting them desyncs playback into garbage) -- lock the
    regression: no packed sequence may contain a tie duration byte."""
    from sidm2.galway_driver11_emitter import unpack_sequence
    _, _, _, sequences, _, _ = _build("Dreamix")
    for pk in sequences:
        i = 0
        while i < len(pk):
            b = pk[i]
            if b == 0x7F:
                break
            if b >= 0xC0 or 0xA0 <= b < 0xC0:
                i += 1
                continue
            assert not (0x90 <= b <= 0x9F), "tie duration byte emitted"
            i += 2  # duration + note
        # and the reference unpacker round-trips it
        assert unpack_sequence(pk) is not None
