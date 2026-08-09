#!/usr/bin/env python3
"""Pin Driver 11's startup frame: the FIRST play call initialises, it does not play.

Driver 11's entry points are a command protocol over one byte at $16CC, and all
the work happens in the per-frame tick at $1006:

    $1000 init (A = subtune)  ->  $16CC = $00   "state not initialised"
    $1003 stop                ->  $16CC = $40
    $1006 tick                ->  dispatch: $80 play a row / $40 gate off /
                                  $00 clear+seed the state block, set $80, RTS

so the first tick after init writes NO SID register and the first row sounds on
the SECOND tick. Every Driver 11 render therefore starts exactly one frame later
than a native player whose play call plays a row immediately -- which is why
every Stage A validator here needs a lag term (`--lag 1`), and why patching
$16CC in the emitted file is the wrong fix (the driver would never initialise).

These tests exist because the mechanism was first documented WRONG: read off the
file at rest ($16CC = $40 on disk, `BVS $1047` "state-init") rather than from a
run. init overwrites that byte with $00 before the first tick, and $1047 is the
STOP path. The effect was right, the cause was not. See docs/players/DRIVER11.md
and PATTERNS.md F6.
"""
import sys
import unittest
from pathlib import Path

import pytest

py65 = pytest.importorskip("py65.devices.mpu6502")
from py65.devices.mpu6502 import MPU  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "G5" / "examples" / "Driver 11 Test - Arpeggio.sf2"

INIT, STOP, TICK = 0x1000, 0x1003, 0x1006
CMD = 0x16CC
STATE_FIRST, STATE_LAST = 0x16CC, 0x1740
SID = 0xD400


def _load(path):
    data = path.read_bytes()
    load = data[0] | (data[1] << 8)
    mpu = MPU()
    for i, b in enumerate(data[2:]):
        mpu.memory[(load + i) & 0xFFFF] = b
    return mpu


def _call(mpu, addr, max_steps=400_000):
    """Call addr as a subroutine, returning when its RTS lands on a sentinel."""
    ret = 0xFFF0
    mpu.pc = addr
    for byte in ((ret - 1) >> 8, (ret - 1) & 0xFF):
        mpu.memory[0x0100 + mpu.sp] = byte
        mpu.sp = (mpu.sp - 1) & 0xFF
    for _ in range(max_steps):
        if mpu.pc == ret:
            return
        mpu.step()
    raise AssertionError(f"${addr:04X} did not return within {max_steps} steps")


def _sid(mpu):
    return [mpu.memory[SID + i] for i in range(0x19)]


class TestDriver11StartupFrame(unittest.TestCase):
    def setUp(self):
        if not TEMPLATE.exists():
            self.skipTest(f"missing {TEMPLATE}")
        self.mpu = _load(TEMPLATE)

    def test_init_leaves_the_command_byte_at_zero(self):
        """The $40 stored in the FILE is irrelevant -- init overwrites it."""
        self.assertEqual(self.mpu.memory[CMD], 0x40, "template byte changed")
        self.mpu.a = 0
        _call(self.mpu, INIT)
        self.assertEqual(self.mpu.memory[CMD], 0x00,
                         "init must leave the command byte at $00")

    def test_first_tick_initialises_and_plays_nothing(self):
        self.mpu.a = 0
        _call(self.mpu, INIT)

        before_sid = _sid(self.mpu)
        before_state = [self.mpu.memory[a] for a in range(STATE_FIRST, STATE_LAST + 1)]
        _call(self.mpu, TICK)

        self.assertEqual(_sid(self.mpu), before_sid,
                         "the first tick must not touch the SID")
        after_state = [self.mpu.memory[a] for a in range(STATE_FIRST, STATE_LAST + 1)]
        self.assertGreater(sum(1 for a, b in zip(before_state, after_state) if a != b), 1,
                           "the first tick must initialise the state block")
        self.assertEqual(self.mpu.memory[CMD], 0x80,
                         "the first tick must arm the play command")

        _call(self.mpu, TICK)
        self.assertNotEqual(_sid(self.mpu), before_sid,
                            "the SECOND tick must play the first row")

    def test_the_lag_is_exactly_one_frame(self):
        """No further silent frames hide behind the first one."""
        self.mpu.a = 0
        _call(self.mpu, INIT)
        first_write = None
        for frame in range(8):
            before = _sid(self.mpu)
            _call(self.mpu, TICK)
            if _sid(self.mpu) != before:
                first_write = frame
                break
        self.assertEqual(first_write, 1,
                         "the first SID write must land on tick 1, not %r" % first_write)

    def test_stop_entry_gates_off_and_is_not_the_init_path(self):
        """$1003/$40 is STOP -- the path at $1047, which the old writeup called init."""
        self.mpu.a = 0
        _call(self.mpu, INIT)
        _call(self.mpu, TICK)          # initialise
        _call(self.mpu, TICK)          # play one row (voices gated on)
        _call(self.mpu, STOP)
        self.assertEqual(self.mpu.memory[CMD], 0x40)

        _call(self.mpu, TICK)
        for ctrl in (0xD404, 0xD40B, 0xD412):
            self.assertEqual(self.mpu.memory[ctrl] & 0x01, 0,
                             f"${ctrl:04X} should be gated off after stop")
        self.assertEqual(self.mpu.memory[CMD], 0x40,
                         "stop must be sticky, not a one-shot")


if __name__ == "__main__":
    sys.exit(unittest.main())
