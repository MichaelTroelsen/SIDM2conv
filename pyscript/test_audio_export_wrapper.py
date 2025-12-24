"""
Unit tests for Audio Export Integration Wrapper (Step 16)

Tests the AudioExportIntegration class and its methods.
"""

import unittest
import sys
from pathlib import Path
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_export_wrapper import AudioExportIntegration


class TestAudioExportIntegration(unittest.TestCase):
    """Test cases for AudioExportIntegration class"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        # Find a PSID test file (SID2WAV v1.8 doesn't support RSID)
        test_dirs = [
            Path("Fun_Fun"),  # Known to have PSID files
            Path("laxity_music"),
            Path("test_files"),
            Path("music"),
            Path(".")
        ]

        cls.test_sid = None
        for test_dir in test_dirs:
            if test_dir.exists():
                sid_files = list(test_dir.glob("*.sid"))
                # Find a PSID file (not RSID)
                for sid_file in sid_files:
                    try:
                        with open(sid_file, 'rb') as f:
                            magic = f.read(4)
                            if magic == b'PSID':  # Only use PSID files
                                cls.test_sid = sid_file
                                break
                    except:
                        continue
                if cls.test_sid:
                    break

        if not cls.test_sid:
            raise unittest.SkipTest("No PSID test files found (SID2WAV v1.8 requires PSID format)")

        # Create output directory for tests
        cls.output_dir = Path("output/test_audio_export")
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def test_check_tool_available(self):
        """Test checking if SID2WAV.EXE is available"""
        available = AudioExportIntegration._check_tool_available()

        # Tool should exist in tools/ directory
        tool_path = Path(AudioExportIntegration.SID2WAV_EXE)
        self.assertEqual(available, tool_path.exists())

    def test_export_with_nonexistent_file(self):
        """Test exporting a non-existent SID file"""
        output_file = self.output_dir / "nonexistent.wav"

        result = AudioExportIntegration.export_to_wav(
            sid_file=Path("nonexistent.sid"),
            output_file=output_file,
            duration=5,
            verbose=0
        )

        if result is not None:
            self.assertFalse(result['success'])
            self.assertIn('error', result)

    @unittest.skipIf(
        not AudioExportIntegration._check_tool_available(),
        "SID2WAV.EXE not available"
    )
    def test_export_with_valid_file(self):
        """Test exporting a valid SID file"""
        output_file = self.output_dir / f"{self.test_sid.stem}_test.wav"

        # Remove existing file if present
        if output_file.exists():
            output_file.unlink()

        result = AudioExportIntegration.export_to_wav(
            sid_file=self.test_sid,
            output_file=output_file,
            duration=5,  # Short duration for quick test
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertEqual(result['output_file'], output_file)
        self.assertTrue(output_file.exists())
        self.assertGreater(result['file_size'], 0)

        # Clean up
        if output_file.exists():
            output_file.unlink()

    @unittest.skipIf(
        not AudioExportIntegration._check_tool_available(),
        "SID2WAV.EXE not available"
    )
    def test_export_with_custom_settings(self):
        """Test exporting with custom audio settings"""
        output_file = self.output_dir / f"{self.test_sid.stem}_custom.wav"

        # Remove existing file if present
        if output_file.exists():
            output_file.unlink()

        result = AudioExportIntegration.export_to_wav(
            sid_file=self.test_sid,
            output_file=output_file,
            duration=3,
            frequency=22050,  # Lower frequency
            bit_depth=8,  # 8-bit
            stereo=False,  # Mono
            fade_out=1,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertEqual(result['duration'], 3)
        self.assertEqual(result['frequency'], 22050)
        self.assertEqual(result['bit_depth'], 8)
        self.assertFalse(result['stereo'])
        self.assertTrue(output_file.exists())

        # Clean up
        if output_file.exists():
            output_file.unlink()

    @unittest.skipIf(
        not AudioExportIntegration._check_tool_available(),
        "SID2WAV.EXE not available"
    )
    def test_export_result_structure(self):
        """Test that export result has correct structure"""
        output_file = self.output_dir / f"{self.test_sid.stem}_struct.wav"

        # Remove existing file if present
        if output_file.exists():
            output_file.unlink()

        result = AudioExportIntegration.export_to_wav(
            sid_file=self.test_sid,
            output_file=output_file,
            duration=3,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertIn('success', result)

        if result['success']:
            self.assertIn('output_file', result)
            self.assertIn('duration', result)
            self.assertIn('frequency', result)
            self.assertIn('bit_depth', result)
            self.assertIn('stereo', result)
            self.assertIn('file_size', result)

        # Clean up
        if output_file.exists():
            output_file.unlink()

    @unittest.skipIf(
        not AudioExportIntegration._check_tool_available(),
        "SID2WAV.EXE not available"
    )
    def test_export_16bit_stereo(self):
        """Test exporting with 16-bit stereo (default settings)"""
        output_file = self.output_dir / f"{self.test_sid.stem}_16bit.wav"

        # Remove existing file if present
        if output_file.exists():
            output_file.unlink()

        result = AudioExportIntegration.export_to_wav(
            sid_file=self.test_sid,
            output_file=output_file,
            duration=3,
            bit_depth=16,
            stereo=True,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertEqual(result['bit_depth'], 16)
        self.assertTrue(result['stereo'])

        # Clean up
        if output_file.exists():
            output_file.unlink()

    def test_convenience_function(self):
        """Test convenience export_to_wav function"""
        from sidm2.audio_export_wrapper import export_to_wav

        output_file = self.output_dir / f"{self.test_sid.stem}_convenience.wav"

        # Remove existing file if present
        if output_file.exists():
            output_file.unlink()

        result = export_to_wav(
            sid_file=self.test_sid,
            output_file=output_file,
            duration=3,
            verbose=0
        )

        # Should return result or None based on tool availability
        if result is not None:
            self.assertIn('success', result)

        # Clean up
        if output_file.exists():
            output_file.unlink()


class TestAudioExportConstants(unittest.TestCase):
    """Test default constants"""

    def test_default_constants(self):
        """Test that default constants are reasonable"""
        self.assertEqual(AudioExportIntegration.DEFAULT_DURATION, 30)
        self.assertEqual(AudioExportIntegration.DEFAULT_FREQUENCY, 44100)
        self.assertEqual(AudioExportIntegration.DEFAULT_BIT_DEPTH, 16)
        self.assertEqual(AudioExportIntegration.DEFAULT_FADE_OUT, 2)
        self.assertEqual(AudioExportIntegration.SID2WAV_EXE, "tools/SID2WAV.EXE")


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestAudioExportIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAudioExportConstants))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
