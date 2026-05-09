"""Stage 7 Phase B.2 — unit tests for the instruments + pulse 6502
split-copy routines.

Mirrors the wave Phase B.1 tests in scope:
  1. The emit functions return non-empty bytes.
  2. The routines assemble (correct opcodes, in-range branches).
  3. py65 step-through actually overwrites the destination bytes —
     i.e. the SF2-edit-area source flows to the NP21 destination.
  4. Round-trip identity: feeding the SF2 view that mirrors the NP21
     state back through the routine leaves NP21 bytes unchanged.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.sf2_writer import SF2Writer

py65 = pytest.importorskip("py65.devices.mpu6502")
MPU = py65.MPU


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_writer():
    return object.__new__(SF2Writer)   # bypass __init__; we only use methods


def _run_routine(code: bytes, sf2_addr: int, np21_addr: int,
                 sf2_bytes: bytes, np21_initial: bytes, code_addr: int = 0xC000) -> bytes:
    """Load `code` into a py65 MPU at `code_addr`, install sf2 bytes at
    `sf2_addr` and np21_initial at `np21_addr`, JSR into code, and return
    the np21 region after execution."""
    mpu = MPU()
    mem = [0] * 0x10000
    for i, b in enumerate(code):
        mem[code_addr + i] = b
    for i, b in enumerate(sf2_bytes):
        mem[sf2_addr + i] = b
    for i, b in enumerate(np21_initial):
        mem[np21_addr + i] = b

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
        raise RuntimeError("routine did not RTS within budget")

    return bytes(new_mem[np21_addr:np21_addr + len(np21_initial)])


# ---------------------------------------------------------------------------
# Instruments (5 fields, NP21 stride 8, SF2 stride 6)
# ---------------------------------------------------------------------------

class TestInstrCopyRoutine:
    def test_assembles_and_executes(self):
        w = _new_writer()
        code = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x1A6B, n_instruments=4,
        )
        assert len(code) >= 60   # 5 passes × ~22B + RTS
        assert code[-1] == 0x60  # RTS

    def test_n_out_of_range_raises(self):
        w = _new_writer()
        with pytest.raises(ValueError):
            w._emit_instr_copy_routine(0x4000, 0x1A6B, n_instruments=0)
        with pytest.raises(ValueError):
            w._emit_instr_copy_routine(0x4000, 0x1A6B, n_instruments=33)

    def test_copies_ad_sr_hr_pulse_wave_for_one_row(self):
        """Single instrument: ensure all 5 mapped fields propagate
        (and bytes 3/4/5 of NP21 are NOT overwritten)."""
        w = _new_writer()
        code = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=1,
        )
        sf2 = bytes([
            0x09,   # AD
            0xA0,   # SR
            0x42,   # HR
            0xFF,   # Filter (must NOT propagate)
            0x12,   # Pulse
            0x34,   # Wave
        ])
        np21_initial = bytes([
            0x00,   # AD slot (pre-test 0x00; will be overwritten with 0x09)
            0x00,   # SR slot
            0x00,   # HR slot
            0xAA,   # flags2 — preserved
            0xBB,   # flags3 — preserved
            0xCC,   # pulse_pm — preserved
            0x00,   # pulse_ptr slot
            0x00,   # wave_ptr slot
        ])
        out = _run_routine(code, 0x4000, 0x5000, sf2, np21_initial)
        assert out[0] == 0x09   # AD copied
        assert out[1] == 0xA0   # SR copied
        assert out[2] == 0x42   # HR copied
        assert out[3] == 0xAA   # flags2 PRESERVED (not 0xFF)
        assert out[4] == 0xBB   # flags3 PRESERVED
        assert out[5] == 0xCC   # pulse_pm PRESERVED
        assert out[6] == 0x12   # Pulse ptr copied
        assert out[7] == 0x34   # Wave ptr copied

    def test_multiple_rows(self):
        w = _new_writer()
        n = 4
        code = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=n,
        )
        # SF2: each row r has (r, r+1, r+2, 0xEE, r+4, r+5)
        sf2 = bytearray()
        for r in range(n):
            sf2.extend([r, r + 1, r + 2, 0xEE, r + 4, r + 5])
        # NP21: 0x00 in copied slots, 0xA?/0xB?/0xC? in preserved slots
        np21_initial = bytearray()
        for r in range(n):
            np21_initial.extend([
                0x00, 0x00, 0x00,
                0xA0 + r, 0xB0 + r, 0xC0 + r,
                0x00, 0x00,
            ])
        out = _run_routine(code, 0x4000, 0x5000, bytes(sf2), bytes(np21_initial))
        for r in range(n):
            base = r * 8
            assert out[base + 0] == r,         f"row {r} AD"
            assert out[base + 1] == r + 1,     f"row {r} SR"
            assert out[base + 2] == r + 2,     f"row {r} HR"
            assert out[base + 3] == 0xA0 + r,  f"row {r} flags2 preserved"
            assert out[base + 4] == 0xB0 + r,  f"row {r} flags3 preserved"
            assert out[base + 5] == 0xC0 + r,  f"row {r} pulse_pm preserved"
            assert out[base + 6] == r + 4,     f"row {r} pulse_ptr"
            assert out[base + 7] == r + 5,     f"row {r} wave_ptr"

    def test_round_trip_identity(self):
        """If SF2 view exactly mirrors what'd be extracted from NP21
        (AD, SR, HR, 0=Filter, pulse_ptr, wave_ptr), the result equals
        the original NP21 — no edit, no change."""
        w = _new_writer()
        n = 4
        code = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=n,
        )
        np21 = bytearray()
        for r in range(n):
            np21.extend([
                (r * 7 + 1) & 0xFF,    # AD
                (r * 7 + 2) & 0xFF,    # SR
                (r * 7 + 3) & 0xFF,    # HR
                (r * 7 + 4) & 0xFF,    # flags2 (preserved)
                (r * 7 + 5) & 0xFF,    # flags3 (preserved)
                (r * 7 + 6) & 0xFF,    # pulse_pm (preserved)
                (r * 7 + 7) & 0xFF,    # pulse_ptr
                (r * 7 + 8) & 0xFF,    # wave_ptr
            ])
        sf2 = bytearray()
        for r in range(n):
            base = r * 8
            sf2.extend([
                np21[base + 0],   # AD
                np21[base + 1],   # SR
                np21[base + 2],   # HR
                0x00,             # Filter (synthesised)
                np21[base + 6],   # pulse_ptr
                np21[base + 7],   # wave_ptr
            ])
        out = _run_routine(code, 0x4000, 0x5000, bytes(sf2), bytes(np21))
        assert out == bytes(np21)


# ---------------------------------------------------------------------------
# Pulse (3 fields, NP21 stride 4, SF2 stride 3)
# ---------------------------------------------------------------------------

class TestPulseCopyRoutine:
    def test_assembles_and_executes(self):
        w = _new_writer()
        code = w._emit_pulse_copy_routine(
            sf2_pulse_addr=0x4000, np21_pulse_addr=0x1A3B, n_rows=8,
        )
        assert len(code) >= 40
        assert code[-1] == 0x60

    def test_copies_first_three_bytes_preserves_fourth(self):
        w = _new_writer()
        code = w._emit_pulse_copy_routine(
            sf2_pulse_addr=0x4000, np21_pulse_addr=0x5000, n_rows=1,
        )
        sf2 = bytes([0x11, 0x22, 0x33])
        np21_initial = bytes([0x00, 0x00, 0x00, 0xDD])
        out = _run_routine(code, 0x4000, 0x5000, sf2, np21_initial)
        assert out == bytes([0x11, 0x22, 0x33, 0xDD])

    def test_multiple_rows(self):
        w = _new_writer()
        n = 4
        code = w._emit_pulse_copy_routine(
            sf2_pulse_addr=0x4000, np21_pulse_addr=0x5000, n_rows=n,
        )
        sf2 = bytearray()
        for r in range(n):
            sf2.extend([r, r + 10, r + 20])
        np21_initial = bytearray()
        for r in range(n):
            np21_initial.extend([0x00, 0x00, 0x00, 0xD0 + r])
        out = _run_routine(code, 0x4000, 0x5000, bytes(sf2), bytes(np21_initial))
        for r in range(n):
            base = r * 4
            assert out[base + 0] == r,        f"row {r} byte 0"
            assert out[base + 1] == r + 10,   f"row {r} byte 1"
            assert out[base + 2] == r + 20,   f"row {r} byte 2"
            assert out[base + 3] == 0xD0 + r, f"row {r} byte 3 preserved"

    def test_round_trip_identity(self):
        w = _new_writer()
        n = 4
        code = w._emit_pulse_copy_routine(
            sf2_pulse_addr=0x4000, np21_pulse_addr=0x5000, n_rows=n,
        )
        np21 = bytearray()
        for r in range(n):
            np21.extend([(r * 5 + 1) & 0xFF,
                         (r * 5 + 2) & 0xFF,
                         (r * 5 + 3) & 0xFF,
                         (r * 5 + 4) & 0xFF])
        sf2 = bytearray()
        for r in range(n):
            sf2.extend(np21[r*4 : r*4 + 3])   # drop byte 3
        out = _run_routine(code, 0x4000, 0x5000, bytes(sf2), bytes(np21))
        assert out == bytes(np21)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_pulse_n_too_large(self):
        w = _new_writer()
        with pytest.raises(ValueError):
            w._emit_pulse_copy_routine(0x4000, 0x5000, n_rows=33)

    def test_instr_n_total_under_256(self):
        """Largest valid n_instruments * 8 = 256 — boundary case
        (should NOT raise; CPX #0 sentinel works because BNE will branch
        for any non-zero X). Test: n=32 → np21_total=256 → CPX #0."""
        w = _new_writer()
        # n=32 → np21_total = 256, which mod 256 = 0. The routine uses
        # CPX #(n*8 & 0xFF) = CPX #0. After 32 iterations X wraps to 0
        # and BNE no-branches, exiting the loop. Verify it ALSO RTSes.
        code = w._emit_instr_copy_routine(
            sf2_instr_addr=0x4000, np21_instr_addr=0x5000, n_instruments=32,
        )
        sf2 = bytes(0x55 for _ in range(32 * 6))
        np21 = bytes(0x00 for _ in range(32 * 8))
        out = _run_routine(code, 0x4000, 0x5000, sf2, np21)
        # All copied fields should be 0x55
        for r in range(32):
            base = r * 8
            assert out[base + 0] == 0x55, f"row {r} AD not propagated"
            assert out[base + 6] == 0x55, f"row {r} pulse_ptr not propagated"
            assert out[base + 7] == 0x55, f"row {r} wave_ptr not propagated"
