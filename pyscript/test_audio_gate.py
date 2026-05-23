"""Unit tests for sidm2.audio_gate.

The full `run_post_build_audio_gate` needs a zig64 tracer + real SID
file (covered by the end-to-end C2 reference regression suite). These
tests focus on the BUFFER-MUTATION primitives:
  - try_block2_native_redirect(out, init, play) — rewrites Block 2 in
    place, returns a saved-state tuple
  - restore_block2(out, saved) — undoes the redirect using the tuple

Synthetic SF2 buffers verify the mutations land at the right offsets
and the restore is a perfect inverse.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import audio_gate


def _build_sf2_with_block2(init: int = 0x0F90, stop: int = 0x0F98,
                            play: int = 0x0F94) -> bytearray:
    """Build a minimal synthetic SF2 buffer with a Block 1 + Block 2
    block chain. Returns (buf, block2_init_offset, block2_play_offset)
    so tests can directly inspect / verify the bytes."""
    out = bytearray(0x100)
    # PRG load + magic
    out[0:2] = (0x0D7E).to_bytes(2, 'little')
    out[2:4] = b"\x37\x13"  # 0x1337
    # Block 1 stub: id=1, size=4, body=[type=0,a,b,c]
    out[4] = 1
    out[5] = 4
    out[6:10] = bytes([0x00, 0x01, 0x02, 0x03])
    # Block 2: id=2, size=12, body=[init_lo,init_hi,stop_lo,stop_hi,play_lo,play_hi, + 6 more]
    b2_off = 4 + 2 + 4  # = 10
    out[b2_off] = 2
    out[b2_off + 1] = 12
    body = bytes([
        init & 0xFF, (init >> 8) & 0xFF,    # init
        stop & 0xFF, (stop >> 8) & 0xFF,    # stop
        play & 0xFF, (play >> 8) & 0xFF,    # play
        0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, # padding (untouched by redirect)
    ])
    out[b2_off + 2:b2_off + 2 + len(body)] = body
    # Block chain terminator
    out[b2_off + 2 + 12] = 0xFF
    return out


class TestTryBlock2NativeRedirect(unittest.TestCase):
    def test_finds_block2_and_patches_init_play(self):
        out = _build_sf2_with_block2()
        result = audio_gate.try_block2_native_redirect(
            out, init_addr=0x9000, play_addr=0x9006)
        self.assertIsNotNone(result, "Block 2 should be found")
        init_off, play_off, orig_init, orig_play = result
        # Verify saved state matches the pre-patch bytes
        self.assertEqual(orig_init, b"\x90\x0F")    # original init=$0F90 LE
        self.assertEqual(orig_play, b"\x94\x0F")    # original play=$0F94 LE
        # Verify the buffer NOW has the new addresses
        self.assertEqual(bytes(out[init_off:init_off + 2]), b"\x00\x90")  # $9000 LE
        self.assertEqual(bytes(out[play_off:play_off + 2]), b"\x06\x90")  # $9006 LE
        # Verify Stop and padding are unchanged (between init and play)
        # body offsets: init=0,1  stop=2,3  play=4,5
        # init_off = b2_off+2 = 12; stop at init_off+2=14
        stop_off = init_off + 2
        self.assertEqual(bytes(out[stop_off:stop_off + 2]), b"\x98\x0F")
        # And padding past play (at play_off+2) untouched
        self.assertEqual(bytes(out[play_off + 2:play_off + 4]), b"\xAA\xBB")

    def test_returns_none_when_no_block2(self):
        # SF2 with only Block 1 + terminator
        out = bytearray(0x100)
        out[0:2] = (0x0D7E).to_bytes(2, 'little')
        out[2:4] = b"\x37\x13"
        out[4] = 1; out[5] = 4
        out[10] = 0xFF  # terminator immediately after Block 1
        result = audio_gate.try_block2_native_redirect(out, 0x9000, 0x9006)
        self.assertIsNone(result)

    def test_returns_none_when_block2_too_small(self):
        # Block 2 with size < 6 (no room for init/stop/play addresses)
        out = bytearray(0x100)
        out[0:2] = (0x0D7E).to_bytes(2, 'little')
        out[2:4] = b"\x37\x13"
        out[4] = 1; out[5] = 4
        b2_off = 10
        out[b2_off] = 2
        out[b2_off + 1] = 5  # size=5, < 6 minimum
        out[b2_off + 7] = 0xFF
        result = audio_gate.try_block2_native_redirect(out, 0x9000, 0x9006)
        self.assertIsNone(result, "Block 2 too small → return None")


class TestRestoreBlock2(unittest.TestCase):
    def test_redirect_then_restore_is_identity(self):
        """Patch via try_block2_native_redirect, then restore — buffer
        should be byte-identical to the pre-patch state."""
        out = _build_sf2_with_block2()
        before = bytes(out)
        saved = audio_gate.try_block2_native_redirect(out, 0x9000, 0x9006)
        self.assertIsNotNone(saved)
        # Buffer is now patched
        self.assertNotEqual(bytes(out), before)
        # Restore
        audio_gate.restore_block2(out, saved)
        # Buffer is back to original
        self.assertEqual(bytes(out), before, "restore must be exact inverse")

    def test_multiple_redirects_each_restorable(self):
        """Patch twice with different addresses, restore in reverse order."""
        out = _build_sf2_with_block2()
        before = bytes(out)
        # 1st redirect: $9000/$9006
        saved1 = audio_gate.try_block2_native_redirect(out, 0x9000, 0x9006)
        # Verify intermediate state
        self.assertEqual(bytes(out[saved1[0]:saved1[0] + 2]), b"\x00\x90")
        # 2nd redirect: $1234/$5678 — saves the $9000/$9006 state
        saved2 = audio_gate.try_block2_native_redirect(out, 0x1234, 0x5678)
        self.assertEqual(saved2[2], b"\x00\x90", "saved2 should have post-1 state")
        self.assertEqual(saved2[3], b"\x06\x90")
        # Restore in reverse: undoes the 2nd, then the 1st
        audio_gate.restore_block2(out, saved2)
        self.assertEqual(bytes(out[saved2[0]:saved2[0] + 2]), b"\x00\x90")
        audio_gate.restore_block2(out, saved1)
        self.assertEqual(bytes(out), before)


class TestRunPostBuildAudioGateEdgeCases(unittest.TestCase):
    """The function should bail cleanly (no exception, empty result)
    when its required inputs are missing."""

    def test_missing_sid_path_returns_empty(self):
        out = bytearray(0x100)
        result = audio_gate.run_post_build_audio_gate(
            out=out, sid_path=None, np21_off=0,
            ch_seq_patches=[], wave_copy_jsr_offs=[],
            ch_seq_patch_layout=None,
            sid_init=0x1000, sid_play=0x1006,
        )
        self.assertEqual(result, {'ch_seq_reverted': False,
                                    'wave_copy_nopped': False,
                                    'block2_redirected': False})

    def test_missing_np21_off_returns_empty(self):
        out = bytearray(0x100)
        result = audio_gate.run_post_build_audio_gate(
            out=out, sid_path=Path("nonexistent.sid"), np21_off=None,
            ch_seq_patches=[], wave_copy_jsr_offs=[],
            ch_seq_patch_layout=None,
            sid_init=0x1000, sid_play=0x1006,
        )
        self.assertFalse(result.get('ch_seq_reverted'))
        self.assertFalse(result.get('wave_copy_nopped'))
        self.assertFalse(result.get('block2_redirected'))

    def test_nonexistent_sid_path_returns_empty(self):
        out = bytearray(0x100)
        result = audio_gate.run_post_build_audio_gate(
            out=out, sid_path=Path("__nonexistent_file_xyz123__.sid"),
            np21_off=0,
            ch_seq_patches=[], wave_copy_jsr_offs=[],
            ch_seq_patch_layout=None,
            sid_init=0x1000, sid_play=0x1006,
        )
        self.assertFalse(any(result.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
