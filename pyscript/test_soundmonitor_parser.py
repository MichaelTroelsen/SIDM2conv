"""Tests for the Sound Monitor (Hulsbeck "Musicmaster") parser.

Locks in the RE'd facts: fixed-address detection, the row model (linear with
8-bit wraparound), the (ctrl, data) step decode with the full data-flag map
($0F instr / $10 glide / $20 no-note-transpose / $40 arp / $80 no-sound-
transpose), row-header chord/arp tables, and the confirmed sound-record
layout prefix (byte0=WF, byte1=AD, byte2=SR). Onset validation across the
11-file cluster is bin/soundmonitor_validate.py (10/11 files 100%, 99.9%
corpus-wide at 30s windows, 2026-07-10).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from sidm2.soundmonitor_parser import (
    load_sid, is_soundmonitor, SoundMonitorModule, SM_INIT, SM_PLAY,
)

CORP = os.path.join(ROOT, "SID", "Fun_Fun")

CLUSTER = [
    "Dance_at_Night_remix", "Dreamix", "Dreamix_Two", "Final_Luv", "Fuck_Off",
    "Fun_Mix", "Just_Cant_Get_Enough", "No_Title", "Poppy_Road", "Thats_All",
    "Times_Up",
]


def _mod(name):
    d, la, h = load_sid(os.path.join(CORP, f"{name}.sid"))
    return SoundMonitorModule(d, la), d, la, h


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_detects_whole_cluster():
    """All 11 cluster files detect; the non-SM Fun_Fun players do not."""
    for name in CLUSTER:
        d, la, h = load_sid(os.path.join(CORP, f"{name}.sid"))
        assert is_soundmonitor(d, la, h), name
    for name in ("Delirious_9_tune_1", "Triangle_Intro"):  # ROMUZAK / FC
        d, la, h = load_sid(os.path.join(CORP, f"{name}.sid"))
        assert not is_soundmonitor(d, la, h), name


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_entry_points_and_signature():
    m, d, la, h = _mod("Dance_at_Night_remix")
    assert h.init_address == SM_INIT == 0xC000
    assert h.play_address == SM_PLAY == 0xC475
    # (the credit string is absent from truncated rips like Final_Luv, so it
    # is NOT the detection signature -- but the full rips carry it)
    assert b"MUSICMASTER CREATED BY CHRIS HUELSBECK" in d


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_row_header_fields():
    """Dance row 0: header at $BF18, speed 2, length 32."""
    m, d, la, h = _mod("Dance_at_Night_remix")
    hdr = m.row_header(0)
    assert hdr["ptr"] == 0xBF18
    assert hdr["speed"] == 2
    assert hdr["length"] == 32


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_row_chain_wraparound():
    """Fun_Mix starts at row 247 with row_count 165: the chain must wrap
    through 255->0 (a plain 6502 INX), yielding 174 rows -- a naive
    range(start, count) is empty here (the bug the first parser had)."""
    m, d, la, h = _mod("Fun_Mix")
    assert m.row_start == 247 and m.row_count == 165
    chain = m.row_chain()
    rows = [r for r, _ in chain]
    assert rows[:10] == [247, 248, 249, 250, 251, 252, 253, 254, 255, 0]
    assert rows[-1] == 164
    assert len(rows) == (256 - 247) + 165


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_octave_arp_table():
    """Dance row 0: every voice's bar selects the octave arp at header+$28."""
    m, d, la, h = _mod("Dance_at_Night_remix")
    for v in range(3):
        assert m.row_arp(v, 0) == (12, 0, 12, 0, 12, 0, 12, 0)


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_sound_record_prefix_and_full_index():
    """Dance's first note resolves to instrument 32 (0 + sound-transpose 32,
    NOT masked to 4 bits) whose record starts WF=$41, AD=$0E, SR=$EC --
    matching the siddump onset exactly."""
    m, d, la, h = _mod("Dance_at_Night_remix")
    assert m.row_sound_transpose(0, 0) == 32
    rec = m.sound(32)
    assert (rec[0], rec[1], rec[2]) == (0x41, 0x0E, 0xEC)
    # extension block present (byte16 != $FF)
    assert rec[16] != 0xFF


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_events_decode_dance():
    """First voice-0 note: C-5 (60) with the octave arp, after 27 rest/tie
    steps; kinds and flags decode per the data-flag map."""
    m, d, la, h = _mod("Dance_at_Night_remix")
    ev = m.events()
    v0 = ev[0]
    # step 27 of row 0 is a REST, step 28 the first note
    assert v0[27][2] == "rest"
    row, step, kind, note, instr, arp, glide = v0[28]
    assert (row, step, kind) == (0, 28, "note")
    assert note == 60
    assert instr == 32
    assert arp == (12, 0, 12, 0, 12, 0, 12, 0)
    assert glide is False


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_glide_flag_dreamix():
    """Dreamix voice 2: the data=$17 notes carry the glide flag, the data=$07
    ones do not (the empirical confirmation of bit $10 = portamento)."""
    m, d, la, h = _mod("Dreamix")
    ev = m.events()
    v2 = [e for e in ev[2] if e[2] == "note"]
    glides = [e for e in v2 if e[6]]
    assert glides, "expected glide notes in Dreamix voice 2"
    # row 0 step 8 (note 48) is the first glide note
    assert any(e[0] == 0 and e[1] == 8 and e[3] == 48 for e in glides)
    # and row 0 step 0 (note 45) is NOT a glide
    first = next(e for e in v2 if e[0] == 0 and e[1] == 0)
    assert first[3] == 45 and first[6] is False


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Fun_Fun corpus absent")
def test_events_all_cluster_files_nonempty():
    """Every cluster file decodes to a nonempty, 3-voice event stream with
    equal per-voice step counts (steps are globally synchronous)."""
    for name in CLUSTER:
        m, d, la, h = _mod(name)
        ev = m.events()
        lens = {v: len(ev[v]) for v in range(3)}
        assert lens[0] == lens[1] == lens[2] > 0, (name, lens)
        assert any(e[2] == "note" for v in range(3) for e in ev[v]), name
