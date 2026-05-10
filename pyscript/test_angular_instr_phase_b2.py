"""Stage 7 Phase B.2 (Angular variant) — detector tests.

Angular uses a row-major NP21 instrument table at $1ADB with **2 bytes
per instrument** (AD followed by SR). Direct-edit verified 2026-05-10:
- Patch $1ADB ($0F → $5A): osc<v>_attack_decay flips
- Patch $1ADC ($01 → $66): osc<v>_sustain_release flips

Compared to Stinsen (column-major at $1808/$181C, 1B stride per col)
and Beast (row-major 8B/instr at $1B38, AD@+5 SR@+6), Angular is the
most compact variant: 2B/instr row-major.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.angular_instr_detector import (
    detect_angular_layout,
    extract_angular_instruments,
    ANGULAR_SIG_BYTES,
)


def _angular_signature_binary(load_addr: int = 0x1000) -> bytes:
    buf = bytearray(0x2000)
    buf[0xAD8:0xADF] = ANGULAR_SIG_BYTES
    # AD/SR pairs starting at $1ADB
    # instr 0: AD=$0F SR=$01  ← in signature (0F at offset 0xADB, 01 at 0xADC)
    # instr 1: AD=$A0 SR=$28  ← in signature
    # Need to set positions 0xADD and 0xADE explicitly since signature
    # only covers 0xAD8..0xADE inclusive (7 bytes).
    buf[0xADD] = 0xA0
    buf[0xADE] = 0x28
    # instr 2: AD=$60 SR=$32
    buf[0xADF] = 0x60
    buf[0xAE0] = 0x32
    # instr 3: AD=$00 SR=$40
    buf[0xAE1] = 0x00
    buf[0xAE2] = 0x40
    # instr 4..: zeros (terminator behavior)
    return bytes(buf)


class TestDetector:
    def test_matches_synthetic(self):
        c64 = _angular_signature_binary()
        layout = detect_angular_layout(c64, 0x1000)
        assert layout is not None
        assert layout.table_addr == 0x1ADB
        assert layout.ad_offset == 0
        assert layout.sr_offset == 1

    def test_rejects_arbitrary(self):
        assert detect_angular_layout(bytes(0x2000), 0x1000) is None

    def test_rejects_too_short(self):
        assert detect_angular_layout(b"\x00" * 100, 0x1000) is None

    def test_rejects_wrong_signature(self):
        buf = bytearray(0x2000)
        buf[0xAD8:0xAE0] = b"\xff" * 8
        assert detect_angular_layout(bytes(buf), 0x1000) is None

    def test_extract_returns_real_ad_sr(self):
        c64 = _angular_signature_binary()
        instrs = extract_angular_instruments(c64, 0x1000)
        assert instrs is not None
        # From the signature + extra bytes:
        assert instrs[0]['ad'] == 0x0F
        assert instrs[0]['sr'] == 0x01
        assert instrs[1]['ad'] == 0xA0
        assert instrs[1]['sr'] == 0x28
        assert instrs[2]['ad'] == 0x60
        assert instrs[2]['sr'] == 0x32

    def test_real_angular_file(self):
        sid = ROOT / "SID" / "Angular.sid"
        if not sid.exists():
            pytest.skip("missing Angular.sid")
        buf = open(sid, "rb").read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do + 1] << 8)
            c64 = buf[do + 2:]
        else:
            c64 = buf[do:]
        layout = detect_angular_layout(c64, load)
        assert layout is not None
        assert layout.table_addr == 0x1ADB
        instrs = extract_angular_instruments(c64, load)
        # Direct-edit-verified values
        assert instrs[0]['ad'] == 0x0F
        assert instrs[0]['sr'] == 0x01

    def test_does_not_match_stinsen_or_beast(self):
        """Other variants should NOT match Angular's signature."""
        for name in ("Stinsens_Last_Night_of_89", "Beast"):
            sid = ROOT / "SID" / f"{name}.sid"
            if not sid.exists():
                continue
            buf = open(sid, "rb").read()
            do = (buf[6] << 8) | buf[7]
            load = (buf[8] << 8) | buf[9]
            if load == 0:
                load = buf[do] | (buf[do + 1] << 8)
                c64 = buf[do + 2:]
            else:
                c64 = buf[do:]
            assert detect_angular_layout(c64, load) is None, f"false positive: {name}"


class TestEmitInstrCopyWithStride:
    def test_default_stride_8(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        # No stride arg → default 8.
        code_default = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
        )
        code_explicit = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
            np21_stride=8,
        )
        assert code_default == code_explicit

    def test_stride_2_for_angular(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        # Angular: stride 2, fields=[(0, 0), (1, 1)]
        code = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x1ADB, n_instruments=8,
            fields=[(0, 0), (1, 1)],
            np21_stride=2,
        )
        # 2 fields × ~22 bytes + RTS = ~50 bytes
        assert 30 <= len(code) <= 70
        assert code[-1] == 0x60   # RTS
        # The ADC immediate values should be 2 (np21 stride) and 6 (sf2 stride)
        # Check both opcodes appear in the generated bytes
        assert bytes([0x69, 0x02]) in code, "ADC #2 missing"
        assert bytes([0x69, 0x06]) in code, "ADC #6 missing"

    def test_stride_out_of_range_raises(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        with pytest.raises(ValueError):
            w._emit_instr_copy_routine(
                sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
                np21_stride=0,
            )
        with pytest.raises(ValueError):
            w._emit_instr_copy_routine(
                sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
                np21_stride=17,
            )
