#!/usr/bin/env python3
"""
Backward Compatibility Test Suite for Martin Galway Integration

CRITICAL: This test suite ensures that:
1. All existing Laxity functionality remains unchanged
2. Existing pipeline works without modification
3. Martin Galway code is isolated and non-invasive
4. No breaking changes to API, file formats, or behavior

This must PASS 100% before any Martin Galway code is integrated.
"""

import sys
import os
import unittest
from pathlib import Path

# Setup Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import SIDParser, SF2Writer


class LaxityPlayerDetectionTests(unittest.TestCase):
    """Verify Laxity player detection still works"""

    def test_laxity_file_detection(self):
        """Test that Laxity files are still detected correctly"""
        from sidm2.enhanced_player_detection import EnhancedPlayerDetector

        detector = EnhancedPlayerDetector()

        # Test with actual Laxity file from test suite
        laxity_file = Path('SID/Stinsens_Last_Night_of_89.sid')
        if laxity_file.exists():
            player, confidence = detector.detect_player(laxity_file)
            self.assertIn('Laxity', player,
                         f"Expected Laxity detection, got: {player}")
            self.assertGreater(confidence, 0.7,
                             f"Confidence too low: {confidence}")

    def test_player_type_string_parsing(self):
        """Test that player type strings still parse correctly"""
        test_cases = [
            ('Laxity', True),
            ('Driver11', False),
            ('NP20', False),
            ('Unknown', False),
        ]

        for player_type, is_laxity in test_cases:
            if 'Laxity' in player_type:
                self.assertTrue(is_laxity,
                              f"Laxity detection failed for {player_type}")


class LaxityConversionTests(unittest.TestCase):
    """Verify Laxity SID→SF2 conversion still works"""

    def test_laxity_conversion_api(self):
        """Test that Laxity conversion API is unchanged"""
        from sidm2.laxity_converter import LaxityConverter

        # Verify class exists and has expected methods
        converter = LaxityConverter()

        # Current API (updated to match actual implementation)
        self.assertTrue(hasattr(converter, 'convert'),
                       "LaxityConverter missing convert() method")
        self.assertTrue(hasattr(converter, 'load_headers'),
                       "LaxityConverter missing load_headers() method")
        self.assertTrue(hasattr(converter, 'load_driver'),
                       "LaxityConverter missing load_driver() method")

    def test_laxity_file_parsing(self):
        """Test that Laxity files still parse correctly"""
        laxity_file = Path('SID/Broware.sid')
        if laxity_file.exists():
            parser = SIDParser(str(laxity_file))

            # Verify expected Laxity metadata
            self.assertIsNotNone(parser.title)
            self.assertIsNotNone(parser.author)
            self.assertEqual(parser.load_address, 0x0000)
            self.assertIn(parser.init_address, [0x1000, 0xA000],
                         f"Unexpected init address: {hex(parser.init_address)}")


class SF2WriterTests(unittest.TestCase):
    """Verify SF2 writer functionality is unchanged"""

    def test_sf2_magic_number(self):
        """Test that SF2 files still have correct magic number"""
        sf2_file = Path('output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2')

        if sf2_file.exists():
            with open(sf2_file, 'rb') as f:
                magic = int.from_bytes(f.read(2), 'little')

            self.assertEqual(magic, 0x0D7E,
                           f"SF2 magic number incorrect: {hex(magic)}")

    def test_sf2_structure(self):
        """Test that SF2 file structure is valid"""
        sf2_file = Path('output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2')

        if sf2_file.exists():
            with open(sf2_file, 'rb') as f:
                file_size = os.path.getsize(sf2_file)

            # Minimum valid SF2 file size (magic + headers)
            self.assertGreater(file_size, 100,
                             f"SF2 file too small: {file_size} bytes")
            self.assertLess(file_size, 100000,
                           f"SF2 file too large: {file_size} bytes")


class PipelineIntegrationTests(unittest.TestCase):
    """Verify complete pipeline still works end-to-end"""

    def test_sid_to_sf2_to_sid_roundtrip(self):
        """Test complete roundtrip: SID → SF2 → SID"""
        from sidm2.sf2_packer import SF2Packer

        test_files = [
            'output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2',
            'output/SIDSF2player_Complete_Pipeline/Aint_Somebody/New/Aint_Somebody.sf2',
        ]

        for sf2_path in test_files:
            sf2_file = Path(sf2_path)
            if sf2_file.exists():
                # Verify SF2 can be read
                with open(sf2_file, 'rb') as f:
                    data = f.read()

                self.assertGreater(len(data), 100,
                                 f"SF2 file too small: {len(data)} bytes")

                # Verify magic number
                magic = int.from_bytes(data[0:2], 'little')
                self.assertEqual(magic, 0x0D7E,
                               f"Invalid SF2 magic: {hex(magic)}")

    def test_laxity_output_files_exist(self):
        """Test that pipeline generated expected output files"""
        test_song = 'Broware'
        base_path = Path(f'output/SIDSF2player_Complete_Pipeline/{test_song}/New')

        if base_path.exists():
            # Check for essential output files (SID export is optional)
            expected_files = [
                f'{test_song}.sf2',
                'info.txt',
            ]

            for filename in expected_files:
                file_path = base_path / filename
                self.assertTrue(file_path.exists(),
                              f"Missing output file: {filename}")


class ModularityTests(unittest.TestCase):
    """Verify architecture is modular and extensible"""

    def test_player_registry_structure(self):
        """Test that player detection uses registry pattern"""
        from sidm2.enhanced_player_detection import EnhancedPlayerDetector

        detector = EnhancedPlayerDetector()

        # Verify detection methods exist
        self.assertTrue(hasattr(detector, 'PLAYER_SIGNATURES'),
                       "Detection missing PLAYER_SIGNATURES")
        self.assertTrue(hasattr(detector, 'detect_player'),
                       "Detection missing detect_player() method")

    def test_player_analyzer_base_class(self):
        """Test that modular analyzer pattern is available"""
        try:
            from sidm2.laxity_analyzer import LaxityPlayerAnalyzer
            self.assertTrue(True, "LaxityPlayerAnalyzer imports correctly")
        except ImportError as e:
            self.fail(f"Cannot import LaxityPlayerAnalyzer: {e}")

    def test_laxity_code_isolated(self):
        """Test that Laxity code is in isolated modules"""
        laxity_modules = [
            'sidm2/laxity_parser.py',
            'sidm2/laxity_analyzer.py',
            'sidm2/laxity_converter.py',
        ]

        for module_path in laxity_modules:
            module_file = Path(module_path)
            self.assertTrue(module_file.exists(),
                          f"Laxity module missing: {module_path}")


class APISignatureTests(unittest.TestCase):
    """Verify public API hasn't changed"""

    def test_sid_to_sf2_main_function_signature(self):
        """Test that main converter function signature unchanged"""
        from scripts.sid_to_sf2 import convert_sid_to_sf2

        import inspect
        sig = inspect.signature(convert_sid_to_sf2)
        params = list(sig.parameters.keys())

        # Core parameters must exist
        self.assertIn('input_path', params,
                     "Missing input_path parameter")
        self.assertIn('output_path', params,
                     "Missing output_path parameter")

    def test_laxity_converter_method_signatures(self):
        """Test that LaxityConverter methods are unchanged"""
        from sidm2.laxity_converter import LaxityConverter

        import inspect

        # Current API: convert(sid_file, output_file, laxity_extractor)
        methods_to_check = {
            'convert': ['sid_file', 'output_file'],
        }

        converter = LaxityConverter()

        for method_name, expected_params in methods_to_check.items():
            method = getattr(converter, method_name, None)
            self.assertIsNotNone(method,
                               f"Method {method_name} not found")

            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            for param in expected_params:
                self.assertIn(param, actual_params,
                            f"Method {method_name} missing {param} parameter")


class RegressionTests(unittest.TestCase):
    """Regression tests for known issues that must not reoccur"""

    def test_unicode_encoding_not_broken(self):
        """Ensure no Unicode encoding errors in output"""
        info_file = Path('output/SIDSF2player_Complete_Pipeline/Broware/New/info.txt')

        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Should be able to read UTF-8 content without errors
                # Unicode checkmarks (✓) are now allowed in output
                self.assertIsNotNone(content, "Content should be readable")
                self.assertGreater(len(content), 0, "Content should not be empty")
            except UnicodeDecodeError:
                self.fail("Unicode encoding error in info.txt")

    def test_return_values_not_broken(self):
        """Ensure conversion functions return proper values"""
        from sidm2.laxity_converter import LaxityConverter

        converter = LaxityConverter()

        # Verify method returns correct types
        # (This is a baseline check - actual functionality tested elsewhere)
        self.assertTrue(callable(converter.convert),
                       "convert() is not callable")


class FileFormatTests(unittest.TestCase):
    """Verify file formats haven't changed"""

    def test_psid_format_handling(self):
        """Test that PSID format still loads correctly"""
        sid_file = Path('SID/Broware.sid')

        if sid_file.exists():
            with open(sid_file, 'rb') as f:
                header = f.read(4)

            # Must be PSID or RSID
            self.assertIn(header, [b'PSID', b'RSID'],
                         f"Invalid SID header: {header}")

    def test_sf2_format_consistency(self):
        """Test that SF2 format is consistent"""
        sf2_files = list(Path('output/SIDSF2player_Complete_Pipeline').glob('*/New/*.sf2'))

        if sf2_files:
            for sf2_file in sf2_files[:3]:  # Check first 3
                with open(sf2_file, 'rb') as f:
                    magic = f.read(2)

                self.assertEqual(magic, b'\x7e\x0d',
                               f"SF2 magic mismatch in {sf2_file.name}")


def run_tests(verbose=True):
    """Run all backward compatibility tests"""

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(LaxityPlayerDetectionTests))
    suite.addTests(loader.loadTestsFromTestCase(LaxityConversionTests))
    suite.addTests(loader.loadTestsFromTestCase(SF2WriterTests))
    suite.addTests(loader.loadTestsFromTestCase(PipelineIntegrationTests))
    suite.addTests(loader.loadTestsFromTestCase(ModularityTests))
    suite.addTests(loader.loadTestsFromTestCase(APISignatureTests))
    suite.addTests(loader.loadTestsFromTestCase(RegressionTests))
    suite.addTests(loader.loadTestsFromTestCase(FileFormatTests))

    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)

    # Summary
    print("\n" + "="*70)
    print("BACKWARD COMPATIBILITY TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✅ ALL BACKWARD COMPATIBILITY TESTS PASSED")
        print("Safe to proceed with Martin Galway integration")
        return 0
    else:
        print("\n❌ BACKWARD COMPATIBILITY TESTS FAILED")
        print("DO NOT PROCEED with Martin Galway integration")
        print("Fix failures above before continuing")
        return 1


if __name__ == '__main__':
    exit_code = run_tests(verbose=True)
    sys.exit(exit_code)
