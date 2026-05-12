"""Tests for Beast + Angular F4 pulse detectors + packed-copy routine (v3.5.10).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.beast_pulse_detector import detect_beast_pulse_layout
from sidm2.angular_pulse_detector import detect_angular_pulse_layout

py65 = pytest.importorskip("py65.devices.mpu6502")
MPU = py65.MPU


def _load_sid(name):
    sid_path = ROOT / "SID" / name
    if not sid_path.exists():
        pytest.skip(f"missing {name}")
    buf = open(sid_path, "rb").read()
    do = (buf[6] << 8) | buf[7]
    load = (buf[8] << 8) | buf[9]
    c64 = buf[do:] if load else buf[do+2:]
    if not load: load = buf[do] | (buf[do+1] << 8)
    return c64, load


class TestBeastPulseDetector:
    def test_random_binary_returns_none(self):
        assert detect_beast_pulse_layout(bytes(0x1000), 0x1000) is None

    def test_real_beast_detects(self):
        c64, load = _load_sid('Beast.sid')
        result = detect_beast_pulse_layout(c64, load)
        assert result is not None
        assert result.stream_addr == 0x1AC5
        assert result.n_steps == 16

    def test_stinsen_not_matched(self):
        c64, load = _load_sid('Stinsens_Last_Night_of_89.sid')
        assert detect_beast_pulse_layout(c64, load) is None


class TestAngularPulseDetector:
    def test_real_angular_detects(self):
        c64, load = _load_sid('Angular.sid')
        result = detect_angular_pulse_layout(c64, load)
        assert result is not None
        assert result.stream_addr == 0x1A3B
        assert result.n_steps == 16

    def test_beast_not_matched(self):
        c64, load = _load_sid('Beast.sid')
        assert detect_angular_pulse_layout(c64, load) is None


class TestPulsePackedCopyRoutine:
    """Beast/Angular F4: stride-4 NP21, stride-3 SF2, 3 cols per row."""

    def test_assembles_and_rtses(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        code = w._emit_pulse_packed_copy_routine(0x4000, 0x1AC5, n_rows=16)
        assert len(code) >= 25
        assert code[-1] == 0x60  # RTS

    def test_n_out_of_range_raises(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        with pytest.raises(ValueError):
            w._emit_pulse_packed_copy_routine(0x4000, 0x1AC5, n_rows=0)
        with pytest.raises(ValueError):
            w._emit_pulse_packed_copy_routine(0x4000, 0x1AC5, n_rows=61)

    def test_three_cols_at_stride_4(self):
        """SF2 rows of 3 bytes → NP21 stride-4 records. NP21 byte 3
        (offset +3 within each step) must be PRESERVED."""
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        n = 3
        code = w._emit_pulse_packed_copy_routine(0x4000, 0x5000, n_rows=n)
        sf2 = bytes([0x11, 0x22, 0x33,   # row 0
                     0x44, 0x55, 0x66,   # row 1
                     0x77, 0x88, 0x99])  # row 2
        # NP21: each 4-byte slot starts with marker bytes
        np21_init = bytearray()
        for r in range(n):
            np21_init.extend([0xAA, 0xBB, 0xCC, 0xDD + r])

        mpu = MPU()
        mem = list([0] * 0x10000)
        for i, b in enumerate(code): mem[0xC000 + i] = b
        for i, b in enumerate(sf2): mem[0x4000 + i] = b
        for i, b in enumerate(np21_init): mem[0x5000 + i] = b
        class M(list): pass
        new_mem = M(mem); mpu.memory = new_mem
        sentinel = 0xFFFE
        new_mem[0x100 | mpu.sp] = sentinel >> 8; mpu.sp = (mpu.sp - 1) & 0xFF
        new_mem[0x100 | mpu.sp] = sentinel & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = 0xC000
        for _ in range(200_000):
            mpu.step()
            if mpu.pc == 0xFFFF: break

        # Verify per-row layout
        for r in range(n):
            base = 0x5000 + r * 4
            assert new_mem[base + 0] == sf2[r * 3 + 0], f"row {r} byte 0"
            assert new_mem[base + 1] == sf2[r * 3 + 1], f"row {r} byte 1"
            assert new_mem[base + 2] == sf2[r * 3 + 2], f"row {r} byte 2"
            assert new_mem[base + 3] == 0xDD + r,        f"row {r} byte 3 preserved"
