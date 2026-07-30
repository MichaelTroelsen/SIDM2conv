#!/usr/bin/env python3
"""Tests for the shared native Stage-B building blocks (sidm2/native_build.py).

The headline test is `program_jump_col`: that one expression was hand-copied
five times across the three native song builders and was the site of a real
shipped bug (build_blackbird_native_song.py's "B3 BUG FOUND" comment). The
tests below pin BOTH the correct behaviour and the specific reason the bug
went unnoticed -- a 2-row program's wrong target coincidentally equals the
jump row's own index, which the driver reads as an intentional self-freeze.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.native_build import (            # noqa: E402
    NATIVE_STATE_ADDR, NATIVE_TCNT_ADDR, PROGRAM_JUMP_OP, SEQ_SLOT_STRIDE,
    make_native_gen, lay_out_sequences, program_jump_col)


class TestProgramJumpCol(unittest.TestCase):
    def test_non_jump_row_passes_its_data_through_unchanged(self):
        """col_last on a normal row is data (semitone offset / duration) and
        must NOT have `start` added, however far into the table it lands."""
        self.assertEqual(program_jump_col(0x41, 5, 0), 5)
        self.assertEqual(program_jump_col(0x41, 5, 200), 5)
        self.assertEqual(program_jump_col(0x00, 0, 77), 0)

    def test_jump_row_target_is_relative_to_the_program_start(self):
        """A $7F row's target is relative-to-start in the source program and
        absolute in the emitted table."""
        self.assertEqual(program_jump_col(PROGRAM_JUMP_OP, 0, 0), 0)
        self.assertEqual(program_jump_col(PROGRAM_JUMP_OP, 0, 40), 40)
        self.assertEqual(program_jump_col(PROGRAM_JUMP_OP, 3, 40), 43)

    def test_result_is_masked_to_a_byte(self):
        """The table column is one byte; a program landing high must wrap the
        same way the original hand-written `& 0xFF` did."""
        self.assertEqual(program_jump_col(PROGRAM_JUMP_OP, 10, 250), 4)
        self.assertEqual(program_jump_col(0x41, 0x1FF, 0), 0xFF)

    def test_high_bit_set_col0_is_recognised_as_a_jump(self):
        """Callers pass col0 values that may carry high bits; the original
        expressions all masked with & 0xFF before comparing to $7F, and some
        call sites pass ints wider than a byte."""
        self.assertEqual(program_jump_col(0x17F, 0, 40), 40)   # masks to $7F
        self.assertEqual(program_jump_col(0xFF, 0, 40), 0)     # $FF is NOT a jump

    def test_the_b3_bug_shape_is_not_reproduced(self):
        """THE regression this module exists for.

        The bug used the row's own local index instead of the program start.
        For the 2-row default program [SET, jump-to-row-0] laid at start=0,
        the jump row is r=1, b2=0: the buggy formula gave 1 (== the jump row's
        own index, which fp_read treats as a deliberate self-freeze, hiding
        the defect), the correct answer is 0.
        """
        b2, jump_row_index, start = 0, 1, 0
        self.assertEqual(program_jump_col(PROGRAM_JUMP_OP, b2, start), 0)
        self.assertNotEqual(program_jump_col(PROGRAM_JUMP_OP, b2, start),
                            jump_row_index)

    def test_longer_program_is_where_the_bug_would_have_been_visible(self):
        """The bug comment notes any program longer than 2 rows "would have
        jumped to entirely the wrong row" -- i.e. the coincidence that hid it
        does not survive. Pin that the correct value is start-relative, and
        that it differs from the row-local index the bug would have produced.
        """
        # 5-row program at start=0, jump row is r=4, loops back to row 0.
        self.assertEqual(program_jump_col(PROGRAM_JUMP_OP, 0, 0), 0)
        self.assertNotEqual(program_jump_col(PROGRAM_JUMP_OP, 0, 0), 4)


class TestMakeNativeGen(unittest.TestCase):
    def test_sets_the_block2_playback_state_contract(self):
        gen = make_native_gen("TestPlayer", 0x1000, 0x1003, 0x1006)
        self.assertEqual(gen.PLAYER_ADDRESSES["driver_state"], NATIVE_STATE_ADDR)
        self.assertEqual(gen.PLAYER_ADDRESSES["tempo_counter"], NATIVE_TCNT_ADDR)
        self.assertEqual((gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP),
                         (0x1000, 0x1003, 0x1006))
        self.assertEqual(gen.driver_name, "TestPlayer")

    def test_native_drivers_share_overlay_slot_17(self):
        """All three native drivers declare version 17.0 (their shared F12
        overlay slot); a silent change here would break the editor's overlay."""
        gen = make_native_gen("TestPlayer", 0x1000, 0x1003, 0x1006)
        self.assertEqual((gen.driver_version_major, gen.driver_version_minor),
                         (17, 0))
        self.assertEqual(gen.driver_code_top, 0x1000)

    def test_does_not_mutate_the_class_level_player_addresses(self):
        """The original Galway code called this out explicitly and it matters:
        PLAYER_ADDRESSES is a CLASS attribute, so mutating it in place would
        leak into every other SF2HeaderGenerator built in the same process --
        and one corpus run builds dozens of songs."""
        from sidm2.sf2_header_generator import SF2HeaderGenerator
        pristine = dict(SF2HeaderGenerator.PLAYER_ADDRESSES)
        make_native_gen("TestPlayer", 0x1000, 0x1003, 0x1006)
        self.assertEqual(SF2HeaderGenerator.PLAYER_ADDRESSES, pristine,
                         "make_native_gen mutated the class-level dict")

    def test_two_gens_do_not_share_one_addresses_dict(self):
        a = make_native_gen("A", 0x1000, 0x1003, 0x1006)
        b = make_native_gen("B", 0x2000, 0x2003, 0x2006)
        self.assertIsNot(a.PLAYER_ADDRESSES, b.PLAYER_ADDRESSES)


class TestLayOutSequences(unittest.TestCase):
    EDIT_BASE = 0x1A00

    def _segs(self, counts):
        """counts[v] packed sequences for voice v, each distinguishable."""
        return [[bytes([0xA0 + v, 0x10 + s, 0x7F]) for s in range(counts[v])]
                for v in range(3)]

    def test_writes_every_sequence_into_its_own_slot_in_voice_order(self):
        """Slots are numbered globally across voices, voice 0's first. This
        ordering is what every native driver's layout.inc SEQ<v> symbols
        assume, so a change here silently mis-points all three voices."""
        segs = self._segs([2, 1, 3])
        gen = make_native_gen("TestPlayer", 0x1000, 0x1003, 0x1006)
        edit, mdp, seq0 = lay_out_sequences(segs, gen, self.EDIT_BASE)
        slot = 0
        for v in range(3):
            for s, pk in enumerate(segs[v]):
                off = (seq0 + slot * SEQ_SLOT_STRIDE) - self.EDIT_BASE
                self.assertEqual(bytes(edit[off:off + len(pk)]), pk,
                                 f"voice {v} seq {s} not at global slot {slot}")
                slot += 1

    def test_returns_a_mutable_bytearray(self):
        """Callers keep writing instrument/table columns into `edit` after
        this returns, so it must not come back immutable."""
        edit, _, _ = lay_out_sequences(self._segs([1, 1, 1]),
                                       make_native_gen("T", 0x1000, 0x1003, 0x1006),
                                       self.EDIT_BASE)
        self.assertIsInstance(edit, bytearray)

    def test_single_sequence_per_voice_is_the_degenerate_case(self):
        segs = self._segs([1, 1, 1])
        gen = make_native_gen("TestPlayer", 0x1000, 0x1003, 0x1006)
        edit, mdp, seq0 = lay_out_sequences(segs, gen, self.EDIT_BASE)
        for v in range(3):
            off = (seq0 + v * SEQ_SLOT_STRIDE) - self.EDIT_BASE
            self.assertEqual(bytes(edit[off:off + 3]), segs[v][0])


if __name__ == "__main__":
    unittest.main()
