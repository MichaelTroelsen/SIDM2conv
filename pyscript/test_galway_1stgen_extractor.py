"""Tests for sidm2.galway_1stgen_extractor (Phase 1: channel-PC recovery).

Corpus-based (emulates init via py65). Skips if py65 or the SID files are
absent. Asserts:
  * recovery succeeds with sane per-voice pointers for representative files
    spanning all 3 dispatch variants + relocation + subtune-sweep;
  * 2nd-gen and the known un-recoverable files return None.
"""
import os
import struct

import pytest

pytest.importorskip("py65")

from sidm2.galway_1stgen_extractor import (
    recover_channels, flatten_channel, flatten_all_channels,
    derive_opcode_lengths, extract_instruments, galway_to_voice_streams,
    GalwayEvent, GalwayInstrument, _SEQ_LEN,
)
from sidm2.galway_1stgen_detector import detect_galway_1stgen

SID_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                       "SID", "Galway_Martin")


def _load(name):
    path = os.path.join(SID_DIR, name)
    if not os.path.exists(path):
        pytest.skip(f"corpus file not present: {name}")
    d = open(path, "rb").read()
    off = struct.unpack(">H", d[6:8])[0]
    la = struct.unpack(">H", d[8:10])[0]
    init = struct.unpack(">H", d[0x0A:0x0C])[0]
    songs = struct.unpack(">H", d[0x0E:0x10])[0]
    start = struct.unpack(">H", d[0x10:0x12])[0]
    b = d[off:]
    if la == 0:
        la = struct.unpack("<H", b[0:2])[0]
        b = b[2:]
    return la, init, songs, start, b


def _recover(name):
    la, init, songs, start, b = _load(name)
    return recover_channels(b, la, init, songs=songs, start_song=start)


# Representative recoveries: indirect (Wizball), indexed (Green Beret),
# masked (Rambo), relocation+sweep (Game Over), reordered-indirect (Parallax).
@pytest.mark.parametrize("name", [
    "Wizball.sid",
    "Green_Beret.sid",
    "Rambo_First_Blood_Part_II.sid",
    "Game_Over.sid",
    "Parallax.sid",
    "Slap_Fight.sid",
])
def test_recovers_sane_channel_pointers(name):
    r = _recover(name)
    assert r is not None, f"{name} channel-PC recovery should succeed"
    assert len(r.pc) == 3
    live = [p for p in r.pc if p and (p >> 8) not in (0x00, 0x01)]
    assert len(live) >= 2, f"{name} should have >=2 live voice pointers"
    # pointers cluster near the located freq tables (relocation-safe check)
    assert all(abs(p - r.layout.lofrq_addr) < 0x3000 for p in live)
    assert 0 <= r.subtune < max(1, 16)


def test_wizball_picks_psid_default_subtune():
    # HVSC Wizball start song = 4 (A=3) = the Title tune; recovery should
    # honor the PSID default when it yields sane pointers.
    r = _recover("Wizball.sid")
    assert r is not None
    assert r.subtune == 3


def test_2ndgen_not_recovered():
    # 2nd-gen player: detector returns None, so does the extractor.
    assert _recover("Athena.sid") is None


@pytest.mark.parametrize("name", ["Highlander.sid", "Miami_Vice.sid"])
def test_known_unrecovered_return_none(name):
    # Documented Phase-1 gaps: pointers set during PLAY / non-consecutive ZP.
    assert _recover(name) is None


# ---- Phase 2: bytecode flattener ----

def _flatten_all(name):
    st = _recover(name)
    assert st is not None
    return st, [flatten_channel(st.ram, st.pc[v]) for v in range(3)]


def test_wizball_flattens_without_desync():
    # Wizball is source-confirmed ground truth (the engine map was RE'd from
    # wizball.asm). A wrong opcode length desyncs the walk onto an invalid
    # opcode; a clean full-control-flow walk validates the opcode spec.
    st, voices = _flatten_all("Wizball.sid")
    for v, ev in enumerate(voices):
        assert ev, f"V{v} produced no events"
        assert ev[-1].kind != "desync", f"V{v} desynced (opcode-length bug)"
        assert not any(e.kind == "desync" for e in ev)
    # V0 + V1 are the melody/harmony — substantial note streams (V0 was 0
    # before the Filter-length fix, so this also guards that regression).
    assert sum(1 for e in voices[0] if e.kind == "note") > 200
    assert sum(1 for e in voices[1] if e.kind == "note") > 200


@pytest.mark.parametrize("name", [
    "Commando_High-Score.sid", "Slap_Fight.sid", "Terra_Cresta.sid",
])
def test_known_compatible_opcode_set_flattens_clean(name):
    # These games share Wizball's opcode set, so they flatten without desync.
    _, voices = _flatten_all(name)
    for v, ev in enumerate(voices):
        assert ev[-1].kind != "desync", f"{name} V{v} desynced"


# ---- Generalization: per-file empirically-derived opcode lengths ----

def test_wizball_derived_table_matches_hardcoded():
    # The empirical prober must reproduce the hand-RE'd Wizball lengths.
    st = _recover("Wizball.sid")
    assert st is not None
    derived = derive_opcode_lengths(st.ram, st.pc0_zp, near=st.pc[0])
    for op, length in _SEQ_LEN.items():
        if op in derived:
            assert derived[op] == length, f"opcode ${op:02X}: {derived[op]} != {length}"


@pytest.mark.parametrize("name", ["Green_Beret.sid", "Ping_Pong.sid"])
def test_generalization_fixes_previously_desyncing_file(name):
    # These desync with the default (Wizball) table but flatten cleanly once
    # their own opcode lengths are derived (relocation-aware dispatch +
    # per-file table). Proves the generalization is a real win.
    st = _recover(name)
    assert st is not None
    # default table desyncs at least one voice
    assert any(flatten_channel(st.ram, st.pc[v])[-1].kind == "desync"
               for v in range(3))
    # generalized: no voice desyncs
    voices, used = flatten_all_channels(st)
    assert all(ev[-1].kind != "desync" for ev in voices), f"{name} still desyncs"
    assert used is not _SEQ_LEN  # used the derived table


def test_flatten_all_never_regresses_wizball():
    # flatten_all_channels must not make Wizball (already clean) worse.
    st = _recover("Wizball.sid")
    voices, _ = flatten_all_channels(st)
    assert all(ev[-1].kind != "desync" for ev in voices)


# ---- Phase 3: instrument extraction (decode logic, no file deps) ----

def test_decode_instrument_fields():
    # 5-byte Vlm def [VWF, VADV, VSRV, VADSD, VRD] at ptr 0x0800.
    ram = bytearray(0x10000)
    ram[0x0800:0x0805] = bytes([0x41, 0xCD, 0x0F, 0xFF, 0xC8])
    voices = [[GalwayEvent("instr", 0, 0, False, 0x0800, 0x1000)]]
    ins = extract_instruments(ram, voices)
    assert len(ins) == 1
    i = ins[0]
    assert i.ctrl == 0x41 and i.waveforms == ("pulse",)   # $40 pulse + gate
    assert i.attack == 0xC and i.decay == 0xD and i.ad == 0xCD
    assert i.sustain == 0x0 and i.release == 0xF and i.sr == 0x0F
    assert i.vadsd == 0xFF and i.vrd == 0xC8


def test_extract_instruments_dedups_and_orders():
    ram = bytearray(0x10000)
    ram[0x0900:0x0905] = bytes([0x21, 0x00, 0xA8, 0, 0])  # sawtooth
    ram[0x0910:0x0915] = bytes([0x80, 0x11, 0x22, 0, 0])  # noise
    voices = [
        [GalwayEvent("instr", 0, 0, False, 0x0900, 0),
         GalwayEvent("instr", 0, 0, False, 0x0900, 0)],   # dup
        [GalwayEvent("instr", 0, 0, False, 0x0910, 0)],
    ]
    ins = extract_instruments(ram, voices)
    assert [i.ptr for i in ins] == [0x0900, 0x0910]       # deduped, in order
    assert ins[0].waveforms == ("sawtooth",)
    assert ins[1].waveforms == ("noise",)


def test_terra_cresta_instruments_are_valid_sid():
    # Terra Cresta uses Vlm; decoded instruments should be real SID voices.
    st = _recover("Terra_Cresta.sid")
    voices, _ = flatten_all_channels(st)
    ins = extract_instruments(st.ram, voices)
    assert len(ins) >= 3
    assert all(i.waveforms for i in ins)                  # each has a waveform
    assert all(i.ad == (i.attack << 4 | i.decay) for i in ins)


def test_fload_full_dn_load_decodes_instrument():
    # FLoad with cnt>=26 loads a full Dn block; the VWF byte is at Dn offset
    # 24, so the instrument decodes from ptr+24. (Wizball's mechanism.)
    ram = bytearray(0x10000)
    tmpl = 0x5000
    ram[tmpl + 24] = 0x41           # VWF: pulse + gate
    ram[tmpl + 25] = 0x06           # VADV
    ram[tmpl + 26] = 0xFA           # VSRV
    voices = [[GalwayEvent("fload", 0, 28, False, tmpl, 0x1000)]]
    ins = extract_instruments(ram, voices)
    assert len(ins) == 1
    assert ins[0].waveforms == ("pulse",) and ins[0].ad == 0x06 and ins[0].sr == 0xFA
    # cnt < 26 does NOT load the waveform region → not an instrument
    voices2 = [[GalwayEvent("fload", 0, 14, False, tmpl, 0x1000)]]
    assert extract_instruments(ram, voices2) == []


def test_wizball_instruments_via_fload():
    # Wizball sets instruments via FLoad (no Vlm). The waveform gate must
    # yield real SID instruments, not garbage.
    st = _recover("Wizball.sid")
    voices, _ = flatten_all_channels(st)
    ins = extract_instruments(st.ram, voices)
    assert len(ins) >= 3
    assert all(i.waveforms for i in ins)


def test_waveform_gate_filters_nonvlm_garbage():
    # An $00 ctrl byte (no waveform) is not a real instrument and must be
    # filtered (e.g. games whose $D2 isn't Vlm decode to ctrl=$00).
    ram = bytearray(0x10000)
    # ptr -> 5 zero bytes => ctrl 0, no waveform
    voices = [[GalwayEvent("instr", 0, 0, False, 0x2000, 0)]]
    assert extract_instruments(ram, voices) == []


# ---- Phase 4: emit NP21-shape voice streams for the SF2 editor area ----

def test_galway_to_voice_streams_mapping():
    instrs = [
        GalwayInstrument(0x5000, 0x41, 0, 6, 0, 0xA, 0, 0, ("pulse",)),
        GalwayInstrument(0x5100, 0x21, 0, 9, 0, 0xA, 0, 0, ("sawtooth",)),
    ]
    voices = [
        [GalwayEvent("instr", 0, 0, False, 0x5000, 0),  # -> $A0
         GalwayEvent("note", 0x2F, 8, False, 0, 0),      # -> $30
         GalwayEvent("rest", 0, 4, False, 0, 0),         # -> $00
         GalwayEvent("instr", 0, 0, False, 0x5100, 0),   # -> $A1
         GalwayEvent("note", 0x6F, 8, False, 0, 0)],     # -> $6F (clamped)
        [], [],
    ]
    s = galway_to_voice_streams(voices, instrs)
    # $A0 (instr0), note $2F->$30, rest->$00, $A1 (instr1), note $6F->$6F (clamp)
    assert s[0] == bytes([0xA0, 0x30, 0x00, 0xA1, 0x6F])
    assert s[1] == b"" and s[2] == b""


def test_galway_streams_segment_into_sf2(monkeypatch=None):
    # End-to-end: real Galway file -> voice streams -> SF2 orderlists+seqs.
    from sidm2.placeholder_edit_area import _build_populated_orderlists
    st = _recover("Wizball.sid")
    voices, _ = flatten_all_channels(st)
    instrs = extract_instruments(st.ram, voices)
    streams = galway_to_voice_streams(voices, instrs)
    ols, seqs = _build_populated_orderlists(streams)
    assert len(ols) == 3
    assert len(seqs) >= 3
    # each orderlist terminates ($FE) and references patterns ($A0 markers)
    for ol in ols:
        assert 0xFE in ol
    # at least one real note ($01-$6F) made it into the sequences
    assert any(0x01 <= b <= 0x6F for seq in seqs for b in seq)


# ---- End-to-end: wired Galway conversion -> SF2 ----

def test_galway_conversion_produces_populated_sf2(tmp_path):
    # convert_galway_to_sf2 should emit a real SF2 (embedded player for audio
    # + editor populated from the extractor), replacing the old stub.
    from sidm2.conversion_pipeline import convert_galway_to_sf2
    src = os.path.join(SID_DIR, "Wizball.sid")
    if not os.path.exists(src):
        pytest.skip("Wizball.sid not present")
    out = str(tmp_path / "wizball.sf2")
    assert convert_galway_to_sf2(src, out) is True
    data = open(out, "rb").read()
    # PRG load word = minimal-embed LOAD_BASE $0D7E
    assert data[0] == 0x7E and data[1] == 0x0D
    # embedded 8320-byte player + populated edit area => substantial file
    assert len(data) > 15000
