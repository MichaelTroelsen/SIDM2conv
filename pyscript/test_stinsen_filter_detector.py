"""Tests for sidm2.stinsen_filter_detector — F5 filter byte-stream
detector for Stage 7 Phase B.2 (F5 wire-up).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.stinsen_filter_detector import (
    detect_stinsen_filter_layout,
    STINSEN_FILTER_CMD_OFF,
    STINSEN_FILTER_VAL_OFF,
    STINSEN_FILTER_AUX_OFF,
    STINSEN_FILTER_N_STEPS_DEFAULT,
)
from sidm2.stinsen_instr_detector import STINSEN_SIG_BYTES, STINSEN_SIG_OFFSET


def _synth_stinsen_binary(load=0x1000, n=0x1000):
    data = bytearray(n)
    data[STINSEN_SIG_OFFSET : STINSEN_SIG_OFFSET + len(STINSEN_SIG_BYTES)] = STINSEN_SIG_BYTES
    for i in range(8):
        data[STINSEN_SIG_OFFSET + 8 + i] = 0x80 + i
        data[STINSEN_SIG_OFFSET + 8 + 0x14 + i] = 0x40 + i
    # Marker filter bytes
    for i in range(STINSEN_FILTER_N_STEPS_DEFAULT):
        data[STINSEN_FILTER_CMD_OFF + i] = 0x80 + i
        data[STINSEN_FILTER_VAL_OFF + i] = 0x10 + i
        data[STINSEN_FILTER_AUX_OFF + i] = 0xF0 + i
    return bytes(data), load


class TestStinsenFilterDetector:
    def test_random_binary_returns_none(self):
        assert detect_stinsen_filter_layout(bytes(0x1000), 0x1000) is None

    def test_short_binary_returns_none(self):
        n = STINSEN_FILTER_CMD_OFF + 4
        data = bytearray(n)
        data[STINSEN_SIG_OFFSET : STINSEN_SIG_OFFSET + len(STINSEN_SIG_BYTES)] = STINSEN_SIG_BYTES
        for i in range(8):
            data[STINSEN_SIG_OFFSET + 8 + i] = 0x80 + i
            data[STINSEN_SIG_OFFSET + 8 + 0x14 + i] = 0x40 + i
        assert detect_stinsen_filter_layout(bytes(data), 0x1000) is None

    def test_synthetic_match(self):
        data, load = _synth_stinsen_binary()
        result = detect_stinsen_filter_layout(data, load)
        assert result is not None
        assert result.cmd_addr == load + STINSEN_FILTER_CMD_OFF
        assert result.val_addr == load + STINSEN_FILTER_VAL_OFF
        assert result.aux_addr == load + STINSEN_FILTER_AUX_OFF
        assert result.n_steps == STINSEN_FILTER_N_STEPS_DEFAULT

    def test_real_stinsen_binary(self):
        """Canonical Stinsen.sid: cmd_addr=$1989, val_addr=$19A3,
        aux_addr=$19BD (RE'd 2026-05-11 by py65 trace + handler disasm)."""
        sid_path = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"
        if not sid_path.exists():
            pytest.skip("missing Stinsen.sid")
        buf = open(sid_path, "rb").read()
        do = (buf[6] << 8) | buf[7]
        load = (buf[8] << 8) | buf[9]
        if load == 0:
            load = buf[do] | (buf[do+1] << 8); c64 = buf[do+2:]
        else:
            c64 = buf[do:]
        result = detect_stinsen_filter_layout(c64, load)
        assert result is not None
        assert result.cmd_addr == 0x1989
        assert result.val_addr == 0x19A3
        assert result.aux_addr == 0x19BD
        assert result.n_steps == 16
