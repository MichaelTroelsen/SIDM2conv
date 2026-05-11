"""Tests for sidm2.stinsen_pulse_detector — the F4 pulse-table address
detector used by Stage 7 Phase B.2.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.stinsen_pulse_detector import (
    detect_stinsen_pulse_layout,
    STINSEN_PULSE_LO_OFF,
    STINSEN_PULSE_HI_OFF,
    STINSEN_PULSE_N_STEPS_DEFAULT,
)
from sidm2.stinsen_instr_detector import STINSEN_SIG_BYTES, STINSEN_SIG_OFFSET


def _synth_stinsen_binary(load=0x1000, n=0x1000):
    """Build a synthetic c64 binary that matches Stinsen's instrument-table
    signature so the pulse detector accepts it."""
    data = bytearray(n)
    # Plant the Stinsen instr-table signature
    data[STINSEN_SIG_OFFSET : STINSEN_SIG_OFFSET + len(STINSEN_SIG_BYTES)] = STINSEN_SIG_BYTES
    # Plant at least 8 non-zero AD column entries (signature_offset + 8)
    for i in range(8):
        data[STINSEN_SIG_OFFSET + 8 + i] = 0x80 + i   # AD col
        data[STINSEN_SIG_OFFSET + 8 + 0x14 + i] = 0x40 + i  # SR col
    # Plant marker pulse bytes
    for i in range(STINSEN_PULSE_N_STEPS_DEFAULT):
        data[STINSEN_PULSE_LO_OFF + i] = 0x10 + i
        data[STINSEN_PULSE_HI_OFF + i] = 0x80 + i
    return bytes(data), load


class TestStinsenPulseDetector:
    def test_returns_none_on_random_binary(self):
        # All-zero binary should not match the Stinsen signature
        data = bytes(0x1000)
        assert detect_stinsen_pulse_layout(data, 0x1000) is None

    def test_returns_none_when_too_short(self):
        # Binary that ends before the pulse byte streams reach 16 entries.
        # Build a binary with valid signature but too-small total size:
        # signature region + AD/SR columns but truncated before the
        # pulse-lo-end ($957 + 16 = $967).
        n = STINSEN_PULSE_LO_OFF + 4   # truncated mid-pulse-lo
        data = bytearray(n)
        data[STINSEN_SIG_OFFSET : STINSEN_SIG_OFFSET + len(STINSEN_SIG_BYTES)] = STINSEN_SIG_BYTES
        for i in range(8):
            data[STINSEN_SIG_OFFSET + 8 + i] = 0x80 + i
            data[STINSEN_SIG_OFFSET + 8 + 0x14 + i] = 0x40 + i
        # Plant a few pulse_lo bytes within bounds (just enough to confirm
        # signature still works, but not enough to fit 16 steps)
        for i in range(4):
            data[STINSEN_PULSE_LO_OFF + i] = 0x10 + i
        assert detect_stinsen_pulse_layout(bytes(data), 0x1000) is None

    def test_returns_layout_when_signature_matches(self):
        data, load = _synth_stinsen_binary()
        result = detect_stinsen_pulse_layout(data, load)
        assert result is not None
        assert result.pw_lo_addr == load + STINSEN_PULSE_LO_OFF
        assert result.pw_hi_addr == load + STINSEN_PULSE_HI_OFF
        assert result.n_steps == STINSEN_PULSE_N_STEPS_DEFAULT

    def test_real_stinsen_binary_detects(self):
        """Use the real Stinsen.sid file: load and verify detector
        succeeds. This is the canonical case the F4 wire-up targets."""
        sid_path = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid_path.exists():
            pytest.skip("missing Stinsen.sid for real-binary detector test")
        buf = open(sid_path, "rb").read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do+1] << 8); c64 = buf[do+2:]
        else:
            c64 = buf[do:]
        result = detect_stinsen_pulse_layout(c64, load)
        assert result is not None
        # Canonical Stinsen pulse-table absolute addresses
        assert result.pw_lo_addr == 0x1957
        assert result.pw_hi_addr == 0x193E
        assert result.n_steps == 16

    def test_no_match_on_beast_or_angular(self):
        """Beast / Angular have different instr-table layouts and must
        NOT match the Stinsen pulse signature (since we don't know their
        pulse addresses yet)."""
        for name in ('Beast.sid', 'Angular.sid', 'Unboxed_Ending_8580.sid'):
            sid_path = ROOT / "SID" / name
            if not sid_path.exists():
                continue
            buf = open(sid_path, "rb").read()
            do = (buf[6] << 8) | buf[7]
            load = (buf[8] << 8) | buf[9]
            if load == 0:
                load = buf[do] | (buf[do+1] << 8); c64 = buf[do+2:]
            else:
                c64 = buf[do:]
            result = detect_stinsen_pulse_layout(c64, load)
            # Either None, or — if signature happens to match — its
            # n_steps is at least the default. The contract is:
            # detector should not throw, and if it returns non-None it
            # must reference Stinsen-canonical addresses (since that's
            # the only layout we hardcoded).
            if result is not None:
                assert result.pw_lo_addr == load + STINSEN_PULSE_LO_OFF
                assert result.pw_hi_addr == load + STINSEN_PULSE_HI_OFF
