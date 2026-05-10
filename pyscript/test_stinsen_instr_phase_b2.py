"""Stage 7 Phase B.2 (Stinsen variant) — unit tests for the
column-major instrument table detector + 6502 column-copy routine.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.stinsen_instr_detector import (
    detect_stinsen_layout,
    extract_stinsen_instruments,
    StinsenInstrLayout,
    STINSEN_SIG_BYTES,
)
from sidm2.sf2_writer import SF2Writer

py65 = pytest.importorskip("py65.devices.mpu6502")
MPU = py65.MPU


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

def _stinsen_signature_binary(load_addr: int = 0x1000) -> bytes:
    """Build a synthetic c64_data with the Stinsen signature at the
    expected offset, and a known AD/SR column."""
    buf = bytearray(0x2000)
    # Signature at offset $0800
    buf[0x800:0x808] = STINSEN_SIG_BYTES
    # AD column at $0808 (relative): instr 0=0x20, 1=0xA0, 2=0xE0, ...
    ad_col = bytes([0x20, 0xA0, 0xE0, 0xD0, 0x00, 0x00, 0x05, 0x00,
                    0x00, 0x3A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00])
    buf[0x808:0x81C] = ad_col
    # SR column at $081C
    sr_col = bytes([0x3A, 0x25, 0x03, 0x03, 0x12, 0x8A, 0x66, 0x78,
                    0xF7, 0x80, 0xC0, 0xC0, 0xC0, 0xC0, 0x00, 0xC0,
                    0xC0, 0x80, 0x00, 0x80])
    buf[0x81C:0x830] = sr_col
    return bytes(buf)


class TestDetector:
    def test_detects_stinsen_signature(self):
        c64 = _stinsen_signature_binary()
        layout = detect_stinsen_layout(c64, load_addr=0x1000)
        assert layout is not None
        assert layout.ad_col_addr == 0x1808
        assert layout.sr_col_addr == 0x181C

    def test_rejects_arbitrary_binary(self):
        # All zeros - no signature
        layout = detect_stinsen_layout(bytes(0x2000), load_addr=0x1000)
        assert layout is None

    def test_rejects_too_short(self):
        layout = detect_stinsen_layout(b"\x00" * 100, load_addr=0x1000)
        assert layout is None

    def test_rejects_wrong_signature(self):
        buf = bytearray(0x2000)
        buf[0x800:0x808] = b"\xff" * 8   # different bytes
        layout = detect_stinsen_layout(bytes(buf), load_addr=0x1000)
        assert layout is None

    def test_n_instruments_counts_used_slots(self):
        c64 = _stinsen_signature_binary()
        layout = detect_stinsen_layout(c64, load_addr=0x1000)
        # AD column has non-zero bytes through index 9 (0x3A); rest are 0
        assert layout.n_instruments == 10

    def test_extract_returns_real_ad_sr(self):
        c64 = _stinsen_signature_binary()
        instrs = extract_stinsen_instruments(c64, load_addr=0x1000)
        assert instrs is not None
        # Instr 1 should have AD=$A0, SR=$25 (per Stinsen's verified data)
        assert instrs[1]['ad'] == 0xA0
        assert instrs[1]['sr'] == 0x25
        # Instr 0
        assert instrs[0]['ad'] == 0x20
        assert instrs[0]['sr'] == 0x3A

    def test_extract_real_stinsen_file(self):
        """If the real Stinsen SID is in the corpus, detector + extractor
        should pull plausible AD/SR values."""
        sid = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            pytest.skip("missing Stinsen SID")
        buf = open(sid, "rb").read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do + 1] << 8)
            c64 = buf[do + 2:]
        else:
            c64 = buf[do:]
        layout = detect_stinsen_layout(c64, load)
        assert layout is not None
        assert layout.ad_col_addr == 0x1808
        assert layout.sr_col_addr == 0x181C
        instrs = extract_stinsen_instruments(c64, load)
        assert instrs[1]['ad'] == 0xA0   # verified by direct-edit
        assert instrs[1]['sr'] == 0x25


# ---------------------------------------------------------------------------
# 6502 column-copy routine
# ---------------------------------------------------------------------------

def _new_writer():
    return object.__new__(SF2Writer)


def _run_routine(code: bytes, sf2_addr: int, np21_ad_addr: int,
                 np21_sr_addr: int, sf2_bytes: bytes,
                 np21_initial_ad: bytes, np21_initial_sr: bytes,
                 code_addr: int = 0xC000):
    mpu = MPU()
    mem = [0] * 0x10000
    for i, b in enumerate(code):
        mem[code_addr + i] = b
    for i, b in enumerate(sf2_bytes):
        mem[sf2_addr + i] = b
    for i, b in enumerate(np21_initial_ad):
        mem[np21_ad_addr + i] = b
    for i, b in enumerate(np21_initial_sr):
        mem[np21_sr_addr + i] = b

    class M(list):
        pass

    new_mem = M(mem)
    mpu.memory = new_mem

    sentinel = 0xFFFE
    new_mem[0x100 | mpu.sp] = (sentinel >> 8) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    new_mem[0x100 | mpu.sp] = sentinel & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = code_addr

    for _ in range(200_000):
        mpu.step()
        if mpu.pc == 0xFFFF:
            break
    else:
        raise RuntimeError("did not RTS in budget")

    out_ad = bytes(new_mem[np21_ad_addr:np21_ad_addr + len(np21_initial_ad)])
    out_sr = bytes(new_mem[np21_sr_addr:np21_sr_addr + len(np21_initial_sr)])
    return out_ad, out_sr


class TestColumnCopyRoutine:
    def test_assembles(self):
        w = _new_writer()
        code = w._emit_instr_column_copy_routine(
            sf2_instr_addr=0x4000, np21_ad_col_addr=0x1808,
            np21_sr_col_addr=0x181C, n_instruments=20,
        )
        # 2 passes × ~22 bytes + RTS
        assert len(code) >= 40
        assert code[-1] == 0x60

    def test_n_out_of_range_raises(self):
        w = _new_writer()
        with pytest.raises(ValueError):
            w._emit_instr_column_copy_routine(
                sf2_instr_addr=0x4000, np21_ad_col_addr=0x1808,
                np21_sr_col_addr=0x181C, n_instruments=0,
            )
        with pytest.raises(ValueError):
            w._emit_instr_column_copy_routine(
                sf2_instr_addr=0x4000, np21_ad_col_addr=0x1808,
                np21_sr_col_addr=0x181C, n_instruments=43,
            )

    def test_copies_ad_and_sr_one_instrument(self):
        w = _new_writer()
        code = w._emit_instr_column_copy_routine(
            sf2_instr_addr=0x4000, np21_ad_col_addr=0x5000,
            np21_sr_col_addr=0x6000, n_instruments=1,
        )
        # SF2 row: AD=$09, SR=$A0, HR=$42, Filter=$FF, Pulse=$12, Wave=$34
        sf2 = bytes([0x09, 0xA0, 0x42, 0xFF, 0x12, 0x34])
        np21_ad = bytes([0x00])
        np21_sr = bytes([0x00])
        out_ad, out_sr = _run_routine(
            code, 0x4000, 0x5000, 0x6000, sf2, np21_ad, np21_sr,
        )
        assert out_ad[0] == 0x09   # AD copied
        assert out_sr[0] == 0xA0   # SR copied

    def test_copies_multiple_instruments(self):
        w = _new_writer()
        n = 5
        code = w._emit_instr_column_copy_routine(
            sf2_instr_addr=0x4000, np21_ad_col_addr=0x5000,
            np21_sr_col_addr=0x6000, n_instruments=n,
        )
        # SF2: 5 rows × 6 cols. Each row r: (r, r+10, junk, junk, junk, junk).
        sf2 = bytearray()
        for r in range(n):
            sf2.extend([r, r + 10, 0xEE, 0xFF, 0xCC, 0xBB])
        np21_ad = bytes(n)
        np21_sr = bytes(n)
        out_ad, out_sr = _run_routine(
            code, 0x4000, 0x5000, 0x6000, bytes(sf2), np21_ad, np21_sr,
        )
        assert list(out_ad) == [0, 1, 2, 3, 4]
        assert list(out_sr) == [10, 11, 12, 13, 14]

    def test_round_trip_identity(self):
        """If the SF2 view mirrors what'd be extracted from NP21
        (AD/SR pairs in row-major, other cols zero), copying back
        leaves NP21 unchanged."""
        w = _new_writer()
        n = 6
        code = w._emit_instr_column_copy_routine(
            sf2_instr_addr=0x4000, np21_ad_col_addr=0x5000,
            np21_sr_col_addr=0x6000, n_instruments=n,
        )
        np21_ad = bytes([(i * 7 + 1) & 0xFF for i in range(n)])
        np21_sr = bytes([(i * 11 + 3) & 0xFF for i in range(n)])
        sf2 = bytearray()
        for i in range(n):
            sf2.extend([np21_ad[i], np21_sr[i], 0, 0, 0, 0])
        out_ad, out_sr = _run_routine(
            code, 0x4000, 0x5000, 0x6000, bytes(sf2), np21_ad, np21_sr,
        )
        assert out_ad == np21_ad
        assert out_sr == np21_sr
