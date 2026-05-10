"""Stage 7 Phase B.2 (Beast variant) — detector tests.

Beast uses a row-major NP21 instrument table at $1B38, 8 bytes per
instrument, with AD at offset +5 and SR at offset +6. Direct-edit
verified 2026-05-10 by patching $1B3D / $1B45 and observing
osc2_attack_decay flips in zig64 trace.

The wire-up in `_inject_laxity_raw_np21` is gated on `num_patterns
> 0`, so Beast itself doesn't currently get the runtime instr-copy
emitted (its ch_seq_ptr autodetect fails). The detector + extractor
are still correct work, exercised here.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.beast_instr_detector import (
    detect_beast_layout,
    extract_beast_instruments,
    BEAST_SIG_BYTES,
)


def _beast_signature_binary(load_addr: int = 0x1000) -> bytes:
    """Synthetic c64_data with Beast signature + a few extra rows."""
    buf = bytearray(0x2000)
    buf[0xB38:0xB48] = BEAST_SIG_BYTES
    # Row 2 at $1B48: AD=$C0, SR=$74 (matches real Beast)
    buf[0xB48:0xB50] = bytes([0x00, 0x00, 0x04, 0x00, 0x07, 0xC0, 0x74, 0x10])
    # Row 3 at $1B50: AD=$03, SR=$EA
    buf[0xB50:0xB58] = bytes([0xF1, 0x34, 0x00, 0x00, 0x80, 0x03, 0xEA, 0x81])
    # Row 4 at $1B58: AD=$03, SR=$C6
    buf[0xB58:0xB60] = bytes([0x00, 0x00, 0x08, 0x01, 0x0F, 0x03, 0xC6, 0x10])
    # Row 5 at $1B60: AD=$07, SR=$C9
    buf[0xB60:0xB68] = bytes([0xF1, 0x28, 0x10, 0x00, 0x13, 0x07, 0xC9, 0x10])
    # Row 6 onwards: all zero → terminator
    return bytes(buf)


class TestDetector:
    def test_matches_synthetic_signature(self):
        c64 = _beast_signature_binary()
        layout = detect_beast_layout(c64, load_addr=0x1000)
        assert layout is not None
        assert layout.table_addr == 0x1B38
        assert layout.ad_offset == 5
        assert layout.sr_offset == 6
        assert layout.n_instruments == 6   # rows 0..5 are non-zero

    def test_rejects_arbitrary(self):
        assert detect_beast_layout(bytes(0x2000), 0x1000) is None

    def test_rejects_too_short(self):
        assert detect_beast_layout(b"\x00" * 100, 0x1000) is None

    def test_rejects_wrong_signature(self):
        buf = bytearray(0x2000)
        buf[0xB38:0xB40] = b"\xff" * 8
        assert detect_beast_layout(bytes(buf), 0x1000) is None

    def test_extract_returns_real_ad_sr(self):
        c64 = _beast_signature_binary()
        instrs = extract_beast_instruments(c64, 0x1000)
        assert instrs is not None
        # From signature: row 0 has AD=$07 SR=$F8, row 1 AD=$07 SR=$E8
        assert instrs[0]['ad'] == 0x07
        assert instrs[0]['sr'] == 0xF8
        assert instrs[1]['ad'] == 0x07
        assert instrs[1]['sr'] == 0xE8
        assert instrs[2]['ad'] == 0xC0
        assert instrs[2]['sr'] == 0x74

    def test_real_beast_file(self):
        """Detector matches the real Beast.sid corpus file with the
        AD/SR values verified by direct-edit."""
        sid = ROOT / "SID" / "Beast.sid"
        if not sid.exists():
            pytest.skip("missing Beast.sid")
        buf = open(sid, "rb").read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do + 1] << 8)
            c64 = buf[do + 2:]
        else:
            c64 = buf[do:]
        layout = detect_beast_layout(c64, load)
        assert layout is not None
        assert layout.table_addr == 0x1B38
        instrs = extract_beast_instruments(c64, load)
        # Direct-edit-verified values
        assert instrs[0]['ad'] == 0x07
        assert instrs[0]['sr'] == 0xF8
        assert instrs[1]['ad'] == 0x07
        assert instrs[1]['sr'] == 0xE8

    def test_does_not_match_stinsen(self):
        """Stinsen has a different signature — make sure we don't
        false-positive."""
        sid = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            pytest.skip("missing Stinsen.sid")
        buf = open(sid, "rb").read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do + 1] << 8)
            c64 = buf[do + 2:]
        else:
            c64 = buf[do:]
        assert detect_beast_layout(c64, load) is None


class TestEmitInstrCopyWithCustomFields:
    """Ensure _emit_instr_copy_routine accepts a custom fields list
    (used for Beast: [(0, 5), (1, 6)] mapping AD/SR to row offsets
    +5/+6 instead of the default Driver-11 layout)."""

    def test_default_fields_match_old_behavior(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        # No fields arg → default mapping (5 fields).
        code_default = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
        )
        # Explicit default → same bytes.
        code_explicit = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
            fields=[(0, 0), (1, 1), (2, 2), (4, 6), (5, 7)],
        )
        assert code_default == code_explicit

    def test_beast_fields_emit_smaller_routine(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        code_beast = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
            fields=[(0, 5), (1, 6)],
        )
        # Beast = 2 fields; default = 5 fields → ~40% size.
        code_default = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=4,
        )
        assert len(code_beast) < len(code_default)
        assert code_beast[-1] == 0x60   # RTS
