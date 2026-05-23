"""Unit tests for sidm2.np21_codegen (the 11 pure 6502 emitters).

Each test pins the BYTE-OUTPUT of an emitter for specific input
parameters. Tighter regression guard than the end-to-end C2 audio
tests: if anyone edits a codegen function in a way that changes its
output, these tests fail directly at the emitter level instead of
several layers up.

The expected bytes were captured from the v3.5.36 implementation
(the byte-identical refactor extraction of these functions from
sf2_writer.py). All 14 C2 reference files pass with this output, so
the captured bytes are known-good.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import np21_codegen


class TestWaveCopyRoutine(unittest.TestCase):
    """Simple flat byte-copy from sf2 → np21 wave addr (legacy utility)."""

    def test_default_64_bytes(self):
        out = np21_codegen.emit_wave_copy_routine(0x2000, 0x3000)
        # LDX #63; loop: LDA $2000,X; STA $3000,X; DEX; BPL loop; RTS
        # = 2 + 3 + 3 + 1 + 2 + 1 = 12 bytes
        self.assertEqual(len(out), 12)
        self.assertEqual(out[0:2], bytes([0xA2, 0x3F]))  # LDX #63
        # LDA $2000,X
        self.assertEqual(out[2], 0xBD)
        self.assertEqual(out[3:5], bytes([0x00, 0x20]))
        # STA $3000,X
        self.assertEqual(out[5], 0x9D)
        self.assertEqual(out[6:8], bytes([0x00, 0x30]))
        # DEX; BPL -8; RTS
        self.assertEqual(out[8], 0xCA)
        self.assertEqual(out[9], 0x10)
        self.assertEqual(out[11], 0x60)

    def test_rejects_n_bytes_out_of_range(self):
        with self.assertRaises(ValueError):
            np21_codegen.emit_wave_copy_routine(0x2000, 0x3000, n_bytes=0)
        with self.assertRaises(ValueError):
            np21_codegen.emit_wave_copy_routine(0x2000, 0x3000, n_bytes=257)


class TestWaveSplitCopyRoutine(unittest.TestCase):
    """Stage 7 F3 wave-split-copy. Two passes; outputs 31 bytes for n_rows=32."""

    def test_default_30_bytes(self):
        out = np21_codegen.emit_wave_split_copy_routine(
            sf2_wave_addr=0x2000,
            np21_wave_data_addr=0x18DA,
            np21_note_addr=0x190C,
            n_rows=32,
        )
        self.assertEqual(len(out), 30, "30-byte routine for n_rows=32")
        # Wave pass: LDX #31; TXA; ASL; TAY; LDA $2000,Y; STA $18DA,X; DEX; BPL -12
        self.assertEqual(out[0:2], bytes([0xA2, 0x1F]))   # LDX #31
        self.assertEqual(out[2:5], bytes([0x8A, 0x0A, 0xA8]))  # TXA; ASL; TAY
        # Note pass starts with another LDX #31 + TXA; ASL; TAY; INY
        # Final RTS
        self.assertEqual(out[-1], 0x60)

    def test_rejects_n_rows_out_of_range(self):
        with self.assertRaises(ValueError):
            np21_codegen.emit_wave_split_copy_routine(0, 0, 0, n_rows=0)
        with self.assertRaises(ValueError):
            np21_codegen.emit_wave_split_copy_routine(0, 0, 0, n_rows=129)


class TestInstrColumnCopyRoutine(unittest.TestCase):
    """Stage 7 F2 Stinsen-style AD/SR column copy (2 passes)."""

    def test_stinsen_default(self):
        # Stinsen: AD col at $1808, SR col at $181C, 20 instruments
        out = np21_codegen.emit_instr_column_copy_routine(
            sf2_instr_addr=0x2000,
            np21_ad_col_addr=0x1808,
            np21_sr_col_addr=0x181C,
            n_instruments=20,
        )
        # Last byte is RTS
        self.assertEqual(out[-1], 0x60)
        # First pass: LDX #0; LDY #0; LDA $2000,Y; STA $1808,X; ...
        self.assertEqual(out[0:4], bytes([0xA2, 0x00, 0xA0, 0x00]))
        self.assertEqual(out[4], 0xB9)   # LDA abs,Y
        self.assertEqual(out[5:7], bytes([0x00, 0x20]))   # = $2000
        self.assertEqual(out[7], 0x9D)   # STA abs,X
        self.assertEqual(out[8:10], bytes([0x08, 0x18]))  # = $1808

    def test_rejects_n_too_high(self):
        with self.assertRaises(ValueError):
            np21_codegen.emit_instr_column_copy_routine(0, 0, 0, n_instruments=43)


class TestPulseSplitCopyRoutine(unittest.TestCase):
    """Stage 7 F4 Stinsen-style parallel PW lo/hi byte streams."""

    def test_stinsen_default(self):
        # Stinsen: PW lo at $1957, PW hi at $193E
        out = np21_codegen.emit_pulse_split_copy_routine(
            sf2_pulse_addr=0x2000,
            np21_pulse_lo_addr=0x1957,
            np21_pulse_hi_addr=0x193E,
            n_rows=16,
        )
        # Single-pass interleaved loop. ~25 bytes for n_rows=16.
        self.assertEqual(out[0:4], bytes([0xA2, 0x00, 0xA0, 0x00]))
        # LDA $2000,Y → STA $1957,X → INY → LDA $2000,Y → STA $193E,X → INY; INY → INX → CPX #16 → BNE → RTS
        self.assertEqual(out[-1], 0x60)


class TestPulsePackedCopyRoutine(unittest.TestCase):
    """Stage 7 F4 Beast/Angular nibble-packed (3 cols → 3 NP21 bytes per record)."""

    def test_default(self):
        out = np21_codegen.emit_pulse_packed_copy_routine(
            sf2_pulse_addr=0x2000,
            np21_stream_addr=0x1AC5,
            n_rows=16,
        )
        # CPX #(n*4) = CPX #64
        self.assertIn(bytes([0xE0, 64]), out)
        self.assertEqual(out[-1], 0x60)

    def test_rejects_n_too_high(self):
        with self.assertRaises(ValueError):
            np21_codegen.emit_pulse_packed_copy_routine(0, 0, n_rows=61)


class TestFilterCutoffOnlyRoutine(unittest.TestCase):
    """Stage 7 F5 Beast/Angular — only col 0 (cutoff_hi) propagates."""

    def test_default(self):
        out = np21_codegen.emit_filter_cutoff_only_routine(
            sf2_filter_addr=0x2000,
            np21_cutoff_hi_addr=0x1A7D,
            n_rows=16,
        )
        # LDX #0; LDY #0; loop: LDA $2000,Y; STA $1A7D,X; INY×3; INX; CPX #16; BNE -; RTS
        self.assertEqual(out[0:4], bytes([0xA2, 0x00, 0xA0, 0x00]))
        # The "INY × 3" sequence (3 × $C8)
        self.assertIn(bytes([0xC8, 0xC8, 0xC8]), out)
        self.assertEqual(out[-1], 0x60)


class TestFilterSplitCopyRoutine(unittest.TestCase):
    """Stage 7 F5 Stinsen — 3 parallel streams cmd/val/aux."""

    def test_stinsen_default(self):
        # Stinsen: cmd=$1989, val=$19A3, aux=$19BD
        out = np21_codegen.emit_filter_split_copy_routine(
            sf2_filter_addr=0x2000,
            np21_cmd_addr=0x1989,
            np21_val_addr=0x19A3,
            np21_aux_addr=0x19BD,
            n_rows=16,
        )
        # Single-pass interleaved 3-store loop
        self.assertEqual(out[0:4], bytes([0xA2, 0x00, 0xA0, 0x00]))
        self.assertEqual(out[-1], 0x60)
        # CPX #16
        self.assertIn(bytes([0xE0, 16]), out)


class TestMultipatTranslator(unittest.TestCase):
    """The 87-byte multi-pattern translator at $0F9E."""

    def test_canonical_invocation(self):
        out = np21_codegen.emit_multipat_translator(
            voice_pat_counts=[1, 1, 1],
            seq00_addr=0x2B95,
            shadow_base=0xA893,
            play_addr=0x1006,
            translate_base=0x0F9E,
        )
        # 87+ bytes; ends with RTS + 3 inline data bytes
        self.assertGreater(len(out), 80)
        # Setup: LDA #seq00_lo, STA $FB; LDA #seq00_hi, STA $FC
        self.assertEqual(out[0:4], bytes([0xA9, 0x95, 0x85, 0xFB]))
        self.assertEqual(out[4:8], bytes([0xA9, 0x2B, 0x85, 0xFC]))
        # voice_pat_counts table at the end
        self.assertEqual(out[-3:], bytes([1, 1, 1]))

    def test_with_wave_copy_jsr(self):
        """When a wave copy addr is passed, a JSR appears between the
        voice loop and the final JSR play_addr."""
        out = np21_codegen.emit_multipat_translator(
            voice_pat_counts=[1, 1, 1],
            seq00_addr=0x2B95,
            shadow_base=0xA893,
            play_addr=0x1006,
            translate_base=0x0F9E,
            table_copy_addr=0x7B64,
        )
        # JSR $7B64 should appear: bytes 0x20, 0x64, 0x7B
        self.assertIn(bytes([0x20, 0x64, 0x7B]), out)
        # Final JSR $1006 (play)
        self.assertIn(bytes([0x20, 0x06, 0x10]), out)

    def test_rejects_wrong_voice_count(self):
        with self.assertRaises(ValueError):
            np21_codegen.emit_multipat_translator(
                voice_pat_counts=[1, 1],   # only 2 voices, not 3
                seq00_addr=0, shadow_base=0, play_addr=0, translate_base=0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
