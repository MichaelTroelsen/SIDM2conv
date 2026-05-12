"""Tests for Beast + Angular F5 filter detectors (v3.5.9).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.beast_filter_detector import (
    detect_beast_filter_layout,
    BEAST_FILTER_CUTOFF_HI_OFF,
    BEAST_FILTER_N_STEPS_DEFAULT,
)
from sidm2.angular_filter_detector import (
    detect_angular_filter_layout,
    ANGULAR_FILTER_CUTOFF_HI_OFF,
    ANGULAR_FILTER_N_STEPS_DEFAULT,
)


class TestBeastFilterDetector:
    def test_random_binary_returns_none(self):
        assert detect_beast_filter_layout(bytes(0x1000), 0x1000) is None

    def test_real_beast_binary(self):
        sid = ROOT / 'SID' / 'Beast.sid'
        if not sid.exists():
            pytest.skip("missing Beast.sid")
        buf = open(sid, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        c64 = buf[do:] if load else buf[do+2:]
        if not load: load = buf[do] | (buf[do+1] << 8)
        result = detect_beast_filter_layout(c64, load)
        assert result is not None
        assert result.cutoff_hi_stream_addr == 0x1A7D
        assert result.n_steps == 16

    def test_stinsen_not_matched(self):
        """Beast detector relies on Beast instr signature — must NOT
        match Stinsen, which has a different instr layout."""
        sid = ROOT / 'SID' / 'Stinsens_Last_Night_of_89.sid'
        if not sid.exists():
            pytest.skip("missing Stinsen.sid")
        buf = open(sid, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        c64 = buf[do:] if load else buf[do+2:]
        if not load: load = buf[do] | (buf[do+1] << 8)
        assert detect_beast_filter_layout(c64, load) is None


class TestAngularFilterDetector:
    def test_random_binary_returns_none(self):
        assert detect_angular_filter_layout(bytes(0x1000), 0x1000) is None

    def test_real_angular_binary(self):
        sid = ROOT / 'SID' / 'Angular.sid'
        if not sid.exists():
            pytest.skip("missing Angular.sid")
        buf = open(sid, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        c64 = buf[do:] if load else buf[do+2:]
        if not load: load = buf[do] | (buf[do+1] << 8)
        result = detect_angular_filter_layout(c64, load)
        assert result is not None
        assert result.cutoff_hi_stream_addr == 0x1A1F
        assert result.n_steps == 16

    def test_beast_not_matched(self):
        sid = ROOT / 'SID' / 'Beast.sid'
        if not sid.exists():
            pytest.skip("missing Beast.sid")
        buf = open(sid, 'rb').read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        c64 = buf[do:] if load else buf[do+2:]
        if not load: load = buf[do] | (buf[do+1] << 8)
        assert detect_angular_filter_layout(c64, load) is None


class TestFilterCutoffOnlyRoutine:
    """Single-column cutoff_hi-only routine (Beast/Angular F5)."""

    def test_assembles_and_rtses(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        code = w._emit_filter_cutoff_only_routine(0x4000, 0x1A7D, n_rows=16)
        assert len(code) >= 15
        assert code[-1] == 0x60  # RTS

    def test_n_out_of_range_raises(self):
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        with pytest.raises(ValueError):
            w._emit_filter_cutoff_only_routine(0x4000, 0x1A7D, n_rows=0)
        with pytest.raises(ValueError):
            w._emit_filter_cutoff_only_routine(0x4000, 0x1A7D, n_rows=86)

    def test_copies_col0_at_stride_3(self):
        """Verify via py65 step-through that col 0 reads at SF2 stride 3
        (skipping cols 1, 2)."""
        py65 = pytest.importorskip("py65.devices.mpu6502")
        MPU = py65.MPU
        from sidm2.sf2_writer import SF2Writer
        w = object.__new__(SF2Writer)
        n = 4
        code = w._emit_filter_cutoff_only_routine(0x4000, 0x5000, n_rows=n)
        sf2_bytes = bytes([0x11, 0xAA, 0xBB,  # row 0
                            0x22, 0xCC, 0xDD,  # row 1
                            0x33, 0xEE, 0xFF,  # row 2
                            0x44, 0x00, 0x00])  # row 3
        mpu = MPU()
        mem = list([0] * 0x10000)
        for i, b in enumerate(code):
            mem[0xC000 + i] = b
        for i, b in enumerate(sf2_bytes):
            mem[0x4000 + i] = b
        class M(list): pass
        new_mem = M(mem)
        mpu.memory = new_mem
        sentinel = 0xFFFE
        new_mem[0x100 | mpu.sp] = sentinel >> 8; mpu.sp = (mpu.sp - 1) & 0xFF
        new_mem[0x100 | mpu.sp] = sentinel & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = 0xC000
        for _ in range(200_000):
            mpu.step()
            if mpu.pc == 0xFFFF: break
        # Verify NP21 destination got col-0 bytes
        assert new_mem[0x5000] == 0x11
        assert new_mem[0x5001] == 0x22
        assert new_mem[0x5002] == 0x33
        assert new_mem[0x5003] == 0x44
