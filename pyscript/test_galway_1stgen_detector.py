"""Tests for sidm2.galway_1stgen_detector.

Two layers:
  * Synthetic byte-signature tests (no file deps) — exercise both dispatch
    variants, the note-freq idiom, the confidence flag, and rejection.
  * Corpus tests — assert detection on the four source-confirmed 1st-gen
    players (Wizball/Arkanoid/Game Over/Green Beret) and NON-detection on
    the three known 2nd-gen players (Athena/Times of Lore/Insects in Space).
    Ground truth: github.com/MartinGalway/C64_music + the README's
    1st-gen/2nd-gen split. Corpus tests skip if the SID files are absent.
"""
import os
import struct

import pytest

from sidm2.galway_1stgen_detector import detect_galway_1stgen

SID_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                       "SID", "Galway_Martin")


# --------------------------------------------------------------------------
# Synthetic-signature unit tests (no external files)
# --------------------------------------------------------------------------

def _note_write_block(lofrq, hifrq):
    # LDY HiFrq,X ; LDA LoFrq,X ; STA $D400 ; STY $D401
    return bytes([0xBC, hifrq & 0xFF, hifrq >> 8,
                  0xBD, lofrq & 0xFF, lofrq >> 8,
                  0x8D, 0x00, 0xD4, 0x8C, 0x01, 0xD4])


def _init_block():
    return bytes([0xA9, 0x08, 0x9D, 0x00, 0xD4,
                  0xA9, 0x00, 0x9D, 0x00, 0xD4, 0xCA, 0x10, 0xF4])


def _indirect_dispatch(vt0):
    # CMP #$C0 ; BCC ; INY ; ADC #imm ; STA $0200 ; JMP (vt0)
    return bytes([0xC9, 0xC0, 0x90, 0x02, 0xC8, 0x69, 0x1A,
                  0x8D, 0x00, 0x02, 0x6C, vt0 & 0xFF, vt0 >> 8])


def _indirect_dispatch_parallax(vt0):
    # Parallax order: CMP #$C0 ; BCC ; ADC #imm ; STA $0200 ; INY ; JMP (vt0)
    return bytes([0xC9, 0xC0, 0x90, 0x02, 0x69, 0x3F,
                  0x8D, 0x00, 0x02, 0xC8, 0x6C, vt0 & 0xFF, vt0 >> 8])


def _indexed_dispatch(vt0):
    base = (vt0 - 0xC0) & 0xFFFF  # operand is vt0-192
    # CMP #$C0 ; BCC ; TAX ; LDA base,X ; STA ; LDA ; STA ; JMP abs
    return bytes([0xC9, 0xC0, 0x90, 0x02, 0xAA,
                  0xBD, base & 0xFF, base >> 8, 0x8D, 0x01, 0x02,
                  0xBD, (base + 1) & 0xFF, (base + 1) >> 8, 0x8D, 0x02, 0x02,
                  0x4C, 0x00, 0x00])


def _masked_dispatch(vt0):
    # Rambo order: CMP #$C0 ; BCC ; AND #$3F ; TAX ; LDA vt0,X ; STA ; LDA ; STA ; JMP abs
    return bytes([0xC9, 0xC0, 0x90, 0x02, 0x29, 0x3F, 0xAA,
                  0xBD, vt0 & 0xFF, vt0 >> 8, 0x8D, 0x01, 0x02,
                  0xBD, (vt0 + 1) & 0xFF, (vt0 + 1) >> 8, 0x8D, 0x02, 0x02,
                  0x4C, 0x00, 0x00])


def test_indirect_variant_detected_high_confidence():
    la = 0x1000
    blob = (b"\xEA" * 16 + _indirect_dispatch(0x4606)
            + b"\xEA" * 16 + _note_write_block(0x471A, 0x4775)
            + b"\xEA" * 16 + _init_block())
    r = detect_galway_1stgen(blob, la)
    assert r is not None
    assert r.dispatch_variant == "indirect"
    assert r.vt0_addr == 0x4606
    assert r.lofrq_addr == 0x471A
    assert r.hifrq_addr == 0x4775
    assert r.confidence == "high"
    assert r.initsound_addr is not None


def test_indexed_variant_detected_and_vt0_offset_applied():
    la = 0x9F90
    blob = (b"\xEA" * 8 + _indexed_dispatch(0xEDF6)
            + b"\xEA" * 8 + _note_write_block(0xED97, 0xED38))
    r = detect_galway_1stgen(blob, la)
    assert r is not None
    assert r.dispatch_variant == "indexed"
    assert r.vt0_addr == 0xEDF6           # base + $C0 recovered
    assert r.confidence == "medium"        # no init loop in this blob
    assert r.initsound_addr is None


def test_masked_variant_detected_vt0_direct():
    la = 0x6F00
    blob = (b"\xEA" * 8 + _masked_dispatch(0x2AE9)
            + b"\xEA" * 8 + _note_write_block(0x2A90, 0x2A37))
    r = detect_galway_1stgen(blob, la)
    assert r is not None
    assert r.dispatch_variant == "masked"
    assert r.vt0_addr == 0x2AE9           # read directly (no +$C0)


def test_indirect_parallax_order_detected():
    la = 0xA400
    blob = (b"\xEA" * 8 + _indirect_dispatch_parallax(0xA40E)
            + b"\xEA" * 8 + _note_write_block(0xB1E8, 0xB189))
    r = detect_galway_1stgen(blob, la)
    assert r is not None
    assert r.dispatch_variant == "indirect"
    assert r.vt0_addr == 0xA40E


def test_requires_both_idioms():
    la = 0x1000
    # dispatch only -> None
    assert detect_galway_1stgen(_indirect_dispatch(0x4606), la) is None
    # note write only -> None
    assert detect_galway_1stgen(_note_write_block(0x471A, 0x4775), la) is None


def test_random_buffer_not_detected():
    assert detect_galway_1stgen(bytes(range(256)) * 8, 0x1000) is None
    assert detect_galway_1stgen(b"\x00" * 4096, 0x1000) is None


# --------------------------------------------------------------------------
# Corpus tests (skip if SID files absent)
# --------------------------------------------------------------------------

def _load_psid(path):
    with open(path, "rb") as f:
        d = f.read()
    data_off = struct.unpack(">H", d[6:8])[0]
    load = struct.unpack(">H", d[8:10])[0]
    body = d[data_off:]
    if load == 0:
        load = struct.unpack("<H", body[0:2])[0]
        body = body[2:]
    return load, body


def _detect_file(name):
    path = os.path.join(SID_DIR, name)
    if not os.path.exists(path):
        pytest.skip(f"corpus file not present: {name}")
    load, body = _load_psid(path)
    return detect_galway_1stgen(body, load)


# Source-confirmed 1st-gen (full player source in MartinGalway/C64_music)
# + Parallax (indirect-reordered) and Rambo (masked), now covered.
@pytest.mark.parametrize("name", [
    "Wizball.sid",
    "Arkanoid.sid",
    "Game_Over.sid",
    "Green_Beret.sid",
    "Parallax.sid",
    "Rambo_First_Blood_Part_II.sid",
])
def test_corpus_1stgen_detected(name):
    r = _detect_file(name)
    assert r is not None, f"{name} should be detected as 1st-gen Galway"
    assert r.dispatch_variant in ("indirect", "indexed", "masked")
    assert r.confidence in ("high", "medium")


# Known 2nd-gen player (Athena/Times of Lore/Insects) — must NOT match.
@pytest.mark.parametrize("name", [
    "Athena.sid",
    "Times_of_Lore.sid",
    "Insects_in_Space.sid",
])
def test_corpus_2ndgen_not_detected(name):
    assert _detect_file(name) is None, f"{name} is 2nd-gen, should not match"
