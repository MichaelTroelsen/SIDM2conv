"""Unit tests for sidm2.minimal_embed_builder.

build_minimal_embed_sf2 builds the Stage 8 Path A minimal-embed SF2
for non-Laxity SIDs. Tests cover:

  - Returns None for empty c64_data
  - High-load case raises ConversionError
  - Low-load case delegates to low_load_layout (returns skip_aux=True)
  - Normal case builds an SF2 with the expected layout

The full byte-for-byte equivalence is verified by the C2 reference
suite (every minimal-embed file routes through this function);
these tests focus on the API contract and dispatch logic.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import minimal_embed_builder, errors


class TestBuildMinimalEmbedSf2(unittest.TestCase):
    def test_returns_none_for_empty_data(self):
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=b"",
            sid_la=0x1000,
            init_addr=0x1000,
            play_addr=0x1003,
        )
        self.assertIsNone(result)

    def test_high_load_uses_alternate_layout_when_possible(self):
        """v3.5.55: when post-binary is too small but the alternate
        layout fits, the high-load layout recovers the file."""
        # 2KB binary at $F800 — ends at $10000, leaving 0 post-binary,
        # but the high-load layout places the edit area at $1000+
        # before the binary and fits the file under 64K.
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes(0x800),
            sid_la=0xF800,
            init_addr=0xF800,
            play_addr=0xF803,
        )
        self.assertIsNotNone(result)
        self.assertFalse(result.skip_aux,
                         "high-load layout has free $0FFB slot — no skip_aux")

    def test_high_load_raises_conversion_error_when_unrecoverable(self):
        """When BOTH the normal layout AND the high-load fallback fail,
        the architectural-error ConversionError is raised."""
        # sid_la=$8000, binary=$9000 bytes → ends at $11000 → file_size
        # would exceed 64K in either layout.
        with self.assertRaises(errors.ConversionError) as ctx:
            minimal_embed_builder.build_minimal_embed_sf2(
                c64_data=bytes(0x9000),
                sid_la=0x8000,
                init_addr=0x8000,
                play_addr=0x8003,
            )
        self.assertIn('high-load', str(ctx.exception).lower())

    def test_low_load_returns_skip_aux_true(self):
        """A binary at $0F00 should route through low_load_layout
        and return skip_aux=True."""
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes(200),
            sid_la=0x0F00,
            init_addr=0x0F00,
            play_addr=0x0F06,
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.skip_aux,
                        "low-load layout must request skip_aux")
        self.assertIsInstance(result.sf2_bytes, bytes)

    def test_low_load_returns_none_when_no_fit(self):
        """A binary at $0400 has no room for the header below the floor."""
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes(1000),
            sid_la=0x0400,
            init_addr=0x0400,
            play_addr=0x0403,
        )
        self.assertIsNone(result, "no room below $0500 floor")

    def test_normal_layout_returns_skip_aux_false(self):
        """A binary at $1000 uses the normal layout (no skip_aux)."""
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes(256),
            sid_la=0x1000,
            init_addr=0x1000,
            play_addr=0x1003,
        )
        self.assertIsNotNone(result)
        self.assertFalse(result.skip_aux,
                         "normal layout should not skip aux")

    def test_normal_layout_embeds_binary_at_sid_la(self):
        """The c64_data bytes appear at the file offset corresponding
        to sid_la (computed from LOAD_BASE = $0D7E)."""
        # Use distinctive payload bytes
        payload = bytes(range(256))
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=payload,
            sid_la=0x1000,
            init_addr=0x1000,
            play_addr=0x1003,
        )
        self.assertIsNotNone(result)
        # File starts with LOAD_BASE = $0D7E (LE), so the bytes at
        # offset 2 + (sid_la - $0D7E) should match payload
        LOAD_BASE = 0x0D7E
        sid_la = 0x1000
        off = 2 + (sid_la - LOAD_BASE)
        self.assertEqual(result.sf2_bytes[off:off + 256], payload)

    def test_handler_stubs_at_handler_base(self):
        """INIT/PLAY/STOP handler stubs are at $0F90."""
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes(256),
            sid_la=0x1000,
            init_addr=0x1234,
            play_addr=0x1238,
        )
        LOAD_BASE = 0x0D7E
        HANDLER_BASE = 0x0F90
        hnd_off = 2 + (HANDLER_BASE - LOAD_BASE)
        # INIT: JSR $1234; RTS
        self.assertEqual(
            bytes(result.sf2_bytes[hnd_off:hnd_off + 4]),
            bytes([0x20, 0x34, 0x12, 0x60]),
            "INIT handler should be JSR $1234; RTS"
        )
        # PLAY: JSR $1238; RTS
        self.assertEqual(
            bytes(result.sf2_bytes[hnd_off + 4:hnd_off + 8]),
            bytes([0x20, 0x38, 0x12, 0x60]),
            "PLAY handler should be JSR $1238; RTS"
        )
        # STOP: LDA #0; STA $D418; RTS
        self.assertEqual(
            bytes(result.sf2_bytes[hnd_off + 8:hnd_off + 14]),
            bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60]),
            "STOP handler should silence voice volume"
        )

    def test_trampoline_only_when_sid_la_ge_1007(self):
        """Compatibility trampoline at $1000 is only placed when
        sid_la >= $1007 (otherwise binary at $1000 would be corrupted)."""
        LOAD_BASE = 0x0D7E
        tramp_off = 2 + (0x1000 - LOAD_BASE)

        # sid_la = $1007 → trampoline placed
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes(256),
            sid_la=0x1007,
            init_addr=0x1234,
            play_addr=0x1238,
        )
        self.assertEqual(
            bytes(result.sf2_bytes[tramp_off:tramp_off + 3]),
            bytes([0x4C, 0x34, 0x12]),
            "Expected JMP $1234 trampoline at $1000"
        )

        # sid_la = $1000 → no trampoline (binary occupies $1000)
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data=bytes([0xAB] + [0] * 255),  # marker byte at sid_la
            sid_la=0x1000,
            init_addr=0x1234,
            play_addr=0x1238,
        )
        # Binary byte 0 (0xAB) should be at $1000, not a JMP opcode
        self.assertEqual(result.sf2_bytes[tramp_off], 0xAB,
                         "Binary at $1000 should be preserved (no trampoline)")


class TestMinimalEmbedResult(unittest.TestCase):
    def test_dataclass_fields(self):
        r = minimal_embed_builder.MinimalEmbedResult(
            sf2_bytes=b"abc",
            skip_aux=True,
        )
        self.assertEqual(r.sf2_bytes, b"abc")
        self.assertTrue(r.skip_aux)


if __name__ == "__main__":
    unittest.main(verbosity=2)
