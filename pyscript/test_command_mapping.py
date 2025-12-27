"""
Unit tests for Laxity → SF2 command decomposition.

Tests the command_mapping module which handles conversion of
Laxity super-commands to SF2 simple commands.

Run: python pyscript/test_command_mapping.py -v
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.command_mapping import (
    decompose_laxity_command,
    get_command_expansion_ratio,
    CommandDecomposer,
    LaxityCommand,
    SF2Command
)


class TestCommandEnums(unittest.TestCase):
    """Test command enumeration definitions"""

    def test_laxity_command_ranges(self):
        """Test Laxity command value ranges"""
        # Note events
        self.assertEqual(LaxityCommand.NOTE_MIN, 0x00)
        self.assertEqual(LaxityCommand.NOTE_MAX, 0x5F)

        # Control commands
        self.assertEqual(LaxityCommand.SET_INSTRUMENT, 0x60)
        self.assertEqual(LaxityCommand.VIBRATO, 0x61)
        self.assertEqual(LaxityCommand.PITCH_SLIDE_UP, 0x62)
        self.assertEqual(LaxityCommand.PITCH_SLIDE_DOWN, 0x63)

        # Extended commands
        self.assertEqual(LaxityCommand.ARPEGGIO, 0x70)
        self.assertEqual(LaxityCommand.PORTAMENTO, 0x71)
        self.assertEqual(LaxityCommand.TREMOLO, 0x72)

        # Control markers
        self.assertEqual(LaxityCommand.CUT_NOTE, 0x7E)
        self.assertEqual(LaxityCommand.END_SEQUENCE, 0x7F)

    def test_sf2_command_types(self):
        """Test SF2 command type values"""
        self.assertEqual(SF2Command.SLIDE, 0x00)
        self.assertEqual(SF2Command.VIBRATO_DEPTH, 0x01)
        self.assertEqual(SF2Command.VIBRATO_SPEED, 0x02)
        self.assertEqual(SF2Command.SLIDE_UP, 0x03)
        self.assertEqual(SF2Command.SLIDE_DOWN, 0x04)
        self.assertEqual(SF2Command.ARPEGGIO_NOTE1, 0x05)
        self.assertEqual(SF2Command.ARPEGGIO_NOTE2, 0x06)
        self.assertEqual(SF2Command.PORTAMENTO, 0x07)
        self.assertEqual(SF2Command.TREMOLO_DEPTH, 0x08)
        self.assertEqual(SF2Command.TREMOLO_SPEED, 0x09)

        # Gate markers
        self.assertEqual(SF2Command.GATE_ON, 0x7E)
        self.assertEqual(SF2Command.GATE_OFF, 0x80)


class TestNoteEventMapping(unittest.TestCase):
    """Test note event command mapping (0x00-0x5F)"""

    def test_note_direct_mapping(self):
        """Test notes map directly without decomposition"""
        # Test various notes
        test_cases = [
            (0x00, [(0x00, None)]),  # C-0
            (0x0C, [(0x0C, None)]),  # C-1
            (0x18, [(0x18, None)]),  # C-2
            (0x24, [(0x24, None)]),  # C-3
            (0x30, [(0x30, None)]),  # C-4
            (0x3C, [(0x3C, None)]),  # C-5
            (0x48, [(0x48, None)]),  # C-6
            (0x54, [(0x54, None)]),  # C-7
            (0x5F, [(0x5F, None)]),  # B-7 (highest note)
        ]

        for laxity_note, expected in test_cases:
            with self.subTest(note=laxity_note):
                result = decompose_laxity_command(laxity_note)
                self.assertEqual(result, expected)

    def test_chromatic_scale(self):
        """Test all notes in chromatic scale map correctly"""
        for note in range(0x00, 0x60):  # 0x00-0x5F
            result = decompose_laxity_command(note)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0], (note, None))


class TestVibratoDecomposition(unittest.TestCase):
    """Test vibrato command decomposition (0x61)"""

    def test_vibrato_basic(self):
        """Test basic vibrato decomposition"""
        # $61 $35: depth=3, speed=5
        result = decompose_laxity_command(0x61, 0x35)

        expected = [
            (0xA1, 3),  # T1 depth
            (0xA2, 5),  # T2 speed
        ]
        self.assertEqual(result, expected)

    def test_vibrato_packed_parameters(self):
        """Test vibrato parameter packing/unpacking"""
        test_cases = [
            (0x00, 0, 0),  # No vibrato
            (0x11, 1, 1),  # Minimal vibrato
            (0xFF, 15, 15),  # Maximum vibrato
            (0x35, 3, 5),  # Example from docs
            (0x82, 8, 2),  # Different depth/speed
        ]

        for param, expected_depth, expected_speed in test_cases:
            with self.subTest(param=param):
                result = decompose_laxity_command(0x61, param)

                self.assertEqual(len(result), 2)
                self.assertEqual(result[0], (0xA1, expected_depth))  # T1
                self.assertEqual(result[1], (0xA2, expected_speed))  # T2

    def test_vibrato_expansion_ratio(self):
        """Test vibrato expansion ratio is 2.0"""
        # Laxity: 2 bytes ($61 $35)
        # SF2: 4 bytes (T1 $03, T2 $05)
        ratio = get_command_expansion_ratio(0x61, 0x35)
        self.assertEqual(ratio, 2.0)


class TestArpeggioDecomposition(unittest.TestCase):
    """Test arpeggio command decomposition (0x70)"""

    def test_arpeggio_major_chord(self):
        """Test major chord arpeggio (0, 4, 7)"""
        # $70 $47: note1=4, note2=7 (C major: C + E + G)
        result = decompose_laxity_command(0x70, 0x47)

        expected = [
            (0xA5, 4),  # T5 note1 (+4 semitones = E)
            (0xA6, 7),  # T6 note2 (+7 semitones = G)
        ]
        self.assertEqual(result, expected)

    def test_arpeggio_minor_chord(self):
        """Test minor chord arpeggio (0, 3, 7)"""
        # $70 $37: note1=3, note2=7 (C minor: C + Eb + G)
        result = decompose_laxity_command(0x70, 0x37)

        expected = [
            (0xA5, 3),  # T5 note1 (+3 semitones = Eb)
            (0xA6, 7),  # T6 note2 (+7 semitones = G)
        ]
        self.assertEqual(result, expected)

    def test_arpeggio_octave(self):
        """Test octave arpeggio (0, 12)"""
        # $70 $C0: note1=12, note2=0
        result = decompose_laxity_command(0x70, 0xC0)

        expected = [
            (0xA5, 12),  # T5 note1 (+12 semitones = octave)
            (0xA6, 0),   # T6 note2 (no offset)
        ]
        self.assertEqual(result, expected)

    def test_arpeggio_expansion_ratio(self):
        """Test arpeggio expansion ratio is 2.0"""
        ratio = get_command_expansion_ratio(0x70, 0x47)
        self.assertEqual(ratio, 2.0)


class TestTremoloDecomposition(unittest.TestCase):
    """Test tremolo command decomposition (0x72)"""

    def test_tremolo_basic(self):
        """Test basic tremolo decomposition"""
        # $72 $24: depth=2, speed=4
        result = decompose_laxity_command(0x72, 0x24)

        expected = [
            (0xA8, 2),  # T8 depth
            (0xA9, 4),  # T9 speed
        ]
        self.assertEqual(result, expected)

    def test_tremolo_various_params(self):
        """Test tremolo with various parameters"""
        test_cases = [
            (0x00, 0, 0),
            (0x11, 1, 1),
            (0x88, 8, 8),
            (0xF5, 15, 5),
        ]

        for param, expected_depth, expected_speed in test_cases:
            with self.subTest(param=param):
                result = decompose_laxity_command(0x72, param)

                self.assertEqual(len(result), 2)
                self.assertEqual(result[0], (0xA8, expected_depth))  # T8
                self.assertEqual(result[1], (0xA9, expected_speed))  # T9


class TestSlideDecomposition(unittest.TestCase):
    """Test pitch slide command decomposition"""

    def test_slide_up(self):
        """Test pitch slide up decomposition (0x62)"""
        # $62 $10: slide up speed 16
        result = decompose_laxity_command(0x62, 0x10)

        expected = [(0xA3, 0x10)]  # T3 speed=16
        self.assertEqual(result, expected)

    def test_slide_down(self):
        """Test pitch slide down decomposition (0x63)"""
        # $63 $20: slide down speed 32
        result = decompose_laxity_command(0x63, 0x20)

        expected = [(0xA4, 0x20)]  # T4 speed=32
        self.assertEqual(result, expected)

    def test_slide_expansion_ratio(self):
        """Test slide expansion ratio is 1.0 (no expansion)"""
        # Laxity: 2 bytes ($62 $10)
        # SF2: 2 bytes (T3 $10)
        ratio_up = get_command_expansion_ratio(0x62, 0x10)
        ratio_down = get_command_expansion_ratio(0x63, 0x20)

        self.assertEqual(ratio_up, 1.0)
        self.assertEqual(ratio_down, 1.0)


class TestPortamentoDecomposition(unittest.TestCase):
    """Test portamento command decomposition (0x71)"""

    def test_portamento_basic(self):
        """Test basic portamento decomposition"""
        # $71 $08: portamento speed 8
        result = decompose_laxity_command(0x71, 0x08)

        expected = [(0xA7, 0x08)]  # T7 speed=8
        self.assertEqual(result, expected)

    def test_portamento_various_speeds(self):
        """Test portamento with various speeds"""
        test_cases = [0x01, 0x04, 0x08, 0x10, 0x20, 0xFF]

        for speed in test_cases:
            with self.subTest(speed=speed):
                result = decompose_laxity_command(0x71, speed)
                self.assertEqual(result, [(0xA7, speed)])


class TestVolumeDecomposition(unittest.TestCase):
    """Test volume command decomposition"""

    def test_set_volume(self):
        """Test set volume decomposition (0x66)"""
        # $66 $0F: volume 15 (max)
        result = decompose_laxity_command(0x66, 0x0F)

        expected = [(0xAE, 0x0F)]  # Te volume=15
        self.assertEqual(result, expected)

    def test_fine_volume(self):
        """Test fine volume decomposition (0x67)"""
        # $67 $0A: fine volume (currently maps to global)
        result = decompose_laxity_command(0x67, 0x0A)

        expected = [(0xAE, 0x0A)]  # Te volume=10 (uses low nibble)
        self.assertEqual(result, expected)

    def test_volume_4bit_mask(self):
        """Test volume uses 4-bit mask (0-15)"""
        # Test values > 15 are masked
        result = decompose_laxity_command(0x66, 0xFF)

        # Should extract low 4 bits: 0x0F
        self.assertEqual(result[0][1], 0x0F)


class TestControlMarkers(unittest.TestCase):
    """Test control marker decomposition"""

    def test_cut_note(self):
        """Test cut note decomposition (0x7E → gate off)"""
        result = decompose_laxity_command(0x7E)

        expected = [(0x80, None)]  # Gate off
        self.assertEqual(result, expected)

    def test_end_sequence(self):
        """Test end sequence decomposition (0x7F)"""
        result = decompose_laxity_command(0x7F)

        expected = [(0x7F, None)]  # Direct mapping
        self.assertEqual(result, expected)

    def test_marker_expansion_ratio(self):
        """Test markers have 1.0 expansion ratio (no expansion)"""
        ratio_cut = get_command_expansion_ratio(0x7E)
        ratio_end = get_command_expansion_ratio(0x7F)

        self.assertEqual(ratio_cut, 1.0)
        self.assertEqual(ratio_end, 1.0)


class TestInstrumentDecomposition(unittest.TestCase):
    """Test instrument command decomposition"""

    def test_set_instrument(self):
        """Test set instrument decomposition (0x60)"""
        # $60 $05: instrument 5
        result = decompose_laxity_command(0x60, 0x05)

        expected = [(0xA1, 0x05)]  # Direct mapping
        self.assertEqual(result, expected)

    def test_set_instrument_range(self):
        """Test set instrument with various indices"""
        for inst_idx in range(0, 32):  # Valid range: 0-31
            with self.subTest(instrument=inst_idx):
                result = decompose_laxity_command(0x60, inst_idx)
                self.assertEqual(result, [(0xA1, inst_idx)])


class TestPatternCommands(unittest.TestCase):
    """Test pattern control command decomposition"""

    def test_pattern_jump(self):
        """Test pattern jump has no SF2 equivalent"""
        # $64 $02: jump to pattern 2
        result = decompose_laxity_command(0x64, 0x02)

        # No SF2 equivalent - returns empty list
        self.assertEqual(result, [])

    def test_pattern_break(self):
        """Test pattern break has no SF2 equivalent"""
        # $65: break pattern
        result = decompose_laxity_command(0x65, 0x00)

        # No SF2 equivalent - returns empty list
        self.assertEqual(result, [])


class TestUnknownCommands(unittest.TestCase):
    """Test handling of unknown/unsupported commands"""

    def test_unknown_command_passthrough(self):
        """Test unknown commands pass through unchanged"""
        # Test an undefined command (e.g., 0x80)
        result = decompose_laxity_command(0x80, 0x12)

        # Should pass through as-is
        self.assertEqual(result, [(0x80, 0x12)])

    def test_reserved_range(self):
        """Test commands in reserved ranges"""
        # Commands in undefined ranges
        reserved_commands = [0x68, 0x69, 0x6A, 0x73, 0x74, 0x75]

        for cmd in reserved_commands:
            with self.subTest(command=cmd):
                result = decompose_laxity_command(cmd, 0x00)
                # Should pass through
                self.assertEqual(result, [(cmd, 0x00)])


class TestExpansionRatios(unittest.TestCase):
    """Test sequence expansion ratios"""

    def test_expansion_ratio_calculations(self):
        """Test expansion ratio calculations for various commands"""
        test_cases = [
            # (cmd, param, expected_ratio, description)
            (0x3C, 0x00, 1.0, "Note (no expansion)"),
            (0x61, 0x35, 2.0, "Vibrato (2x expansion)"),
            (0x70, 0x47, 2.0, "Arpeggio (2x expansion)"),
            (0x72, 0x24, 2.0, "Tremolo (2x expansion)"),
            (0x62, 0x10, 1.0, "Slide up (no expansion)"),
            (0x71, 0x08, 1.0, "Portamento (no expansion)"),
            (0x7E, 0x00, 1.0, "Cut note (no expansion)"),
            (0x7F, 0x00, 1.0, "End sequence (no expansion)"),
        ]

        for cmd, param, expected_ratio, desc in test_cases:
            with self.subTest(description=desc):
                ratio = get_command_expansion_ratio(cmd, param)
                self.assertAlmostEqual(ratio, expected_ratio, places=2)

    def test_average_expansion_ratio(self):
        """Test average expansion ratio for typical sequence"""
        # Typical sequence: notes + vibrato + arpeggio
        commands = [
            (0x3C, 0x00),  # Note C-4 (1.0x)
            (0x61, 0x35),  # Vibrato (2.0x)
            (0x40, 0x00),  # Note E-4 (1.0x)
            (0x70, 0x47),  # Arpeggio (2.0x)
            (0x7F, 0x00),  # End (1.0x)
        ]

        total_laxity_bytes = sum(2 if cmd >= 0x60 and cmd < 0x7E else 1
                                  for cmd, _ in commands)
        total_sf2_bytes = sum(
            sum(2 if p is not None else 1 for _, p in decompose_laxity_command(cmd, param))
            for cmd, param in commands
        )

        avg_ratio = total_sf2_bytes / total_laxity_bytes
        # Expected: (1 + 4 + 1 + 4 + 1) / (1 + 2 + 1 + 2 + 1) = 11/7 ≈ 1.57
        self.assertAlmostEqual(avg_ratio, 1.57, places=2)


class TestCommandDecomposerClass(unittest.TestCase):
    """Test CommandDecomposer class directly"""

    def test_decomposer_initialization(self):
        """Test decomposer initializes correctly"""
        decomposer = CommandDecomposer()
        self.assertIsNotNone(decomposer.decomposition_map)
        self.assertGreater(len(decomposer.decomposition_map), 0)

    def test_decomposer_singleton_pattern(self):
        """Test global decomposer instance exists"""
        from sidm2.command_mapping import _decomposer
        self.assertIsInstance(_decomposer, CommandDecomposer)

    def test_decompose_method(self):
        """Test decompose method works correctly"""
        decomposer = CommandDecomposer()

        # Test vibrato
        result = decomposer.decompose(0x61, 0x35)
        self.assertEqual(result, [(0xA1, 3), (0xA2, 5)])

        # Test note
        result = decomposer.decompose(0x3C, 0x00)
        self.assertEqual(result, [(0x3C, None)])


class TestRegressionCases(unittest.TestCase):
    """Test specific regression cases and edge conditions"""

    def test_zero_parameters(self):
        """Test commands with zero parameters"""
        # All nibbles = 0
        result = decompose_laxity_command(0x61, 0x00)
        self.assertEqual(result, [(0xA1, 0), (0xA2, 0)])

    def test_max_parameters(self):
        """Test commands with maximum parameters"""
        # All nibbles = F
        result = decompose_laxity_command(0x61, 0xFF)
        self.assertEqual(result, [(0xA1, 15), (0xA2, 15)])

    def test_boundary_notes(self):
        """Test boundary note values"""
        # Lowest note
        result = decompose_laxity_command(0x00, 0x00)
        self.assertEqual(result, [(0x00, None)])

        # Highest note
        result = decompose_laxity_command(0x5F, 0x00)
        self.assertEqual(result, [(0x5F, None)])

    def test_command_just_above_notes(self):
        """Test first command after note range"""
        # 0x60 = SET_INSTRUMENT (first non-note command)
        result = decompose_laxity_command(0x60, 0x05)
        self.assertEqual(result, [(0xA1, 0x05)])


def run_tests():
    """Run all tests with verbose output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestCommandEnums,
        TestNoteEventMapping,
        TestVibratoDecomposition,
        TestArpeggioDecomposition,
        TestTremoloDecomposition,
        TestSlideDecomposition,
        TestPortamentoDecomposition,
        TestVolumeDecomposition,
        TestControlMarkers,
        TestInstrumentDecomposition,
        TestPatternCommands,
        TestUnknownCommands,
        TestExpansionRatios,
        TestCommandDecomposerClass,
        TestRegressionCases,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
