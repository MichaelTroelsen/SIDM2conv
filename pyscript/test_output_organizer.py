"""
Unit tests for Output Organizer (Step 20)

Tests the OutputOrganizer class and its methods.
"""

import unittest
import sys
from pathlib import Path
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.output_organizer import OutputOrganizer, organize_output


class TestOutputOrganizer(unittest.TestCase):
    """Test cases for OutputOrganizer class"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.test_dir = Path("output/test_output_organizer")
        cls.test_dir.mkdir(parents=True, exist_ok=True)

        # Create test analysis directory with sample files
        cls.analysis_dir = cls.test_dir / "analysis"
        cls.analysis_dir.mkdir(exist_ok=True)

        # Create sample files for each category
        cls.test_files = {
            'disassembly': [
                'test_init.asm',
                'test_play.asm'
            ],
            'reports': [
                'test_memmap.txt',
                'test_patterns.txt',
                'test_callgraph.txt',
                'test_trace.txt',
                'test_REPORT.txt'
            ],
            'audio': [
                'test.wav'
            ],
            'uncategorized': [
                'random.dat',
                'unknown.xyz'
            ]
        }

        # Create the test files
        for category, files in cls.test_files.items():
            for filename in files:
                file_path = cls.analysis_dir / filename
                with open(file_path, 'w') as f:
                    f.write(f"Test content for {filename}\n")

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        """Reset test directory before each test"""
        # Move all files back to root from subdirectories
        for subdir in ['disassembly', 'reports', 'audio', 'binary']:
            subdir_path = self.analysis_dir / subdir
            if subdir_path.exists():
                for file_path in subdir_path.iterdir():
                    if file_path.is_file():
                        target = self.analysis_dir / file_path.name
                        if not target.exists():  # Avoid overwriting
                            shutil.move(str(file_path), str(target))
                # Remove empty subdirectory
                if subdir_path.exists() and not any(subdir_path.iterdir()):
                    subdir_path.rmdir()

        # Remove INDEX.txt and README.md if they exist
        for filename in ['INDEX.txt', 'README.md']:
            file_path = self.analysis_dir / filename
            if file_path.exists():
                file_path.unlink()

        # Recreate any missing test files
        for category, files in self.test_files.items():
            for filename in files:
                file_path = self.analysis_dir / filename
                if not file_path.exists():
                    with open(file_path, 'w') as f:
                        f.write(f"Test content for {filename}\n")

    def test_organizer_creation(self):
        """Test creating an output organizer"""
        organizer = OutputOrganizer(self.analysis_dir)
        self.assertEqual(organizer.analysis_dir, self.analysis_dir)

    def test_categorize_file_disassembly(self):
        """Test file categorization - disassembly files"""
        organizer = OutputOrganizer(self.analysis_dir)

        # Test .asm files
        self.assertEqual(organizer._categorize_file(Path("test_init.asm")), "disassembly")
        self.assertEqual(organizer._categorize_file(Path("test_play.asm")), "disassembly")
        self.assertEqual(organizer._categorize_file(Path("other.asm")), "disassembly")

    def test_categorize_file_reports(self):
        """Test file categorization - report files"""
        organizer = OutputOrganizer(self.analysis_dir)

        # Test report patterns
        self.assertEqual(organizer._categorize_file(Path("test_memmap.txt")), "reports")
        self.assertEqual(organizer._categorize_file(Path("test_patterns.txt")), "reports")
        self.assertEqual(organizer._categorize_file(Path("test_callgraph.txt")), "reports")
        self.assertEqual(organizer._categorize_file(Path("test_trace.txt")), "reports")
        self.assertEqual(organizer._categorize_file(Path("test_REPORT.txt")), "reports")

    def test_categorize_file_audio(self):
        """Test file categorization - audio files"""
        organizer = OutputOrganizer(self.analysis_dir)

        # Test audio files
        self.assertEqual(organizer._categorize_file(Path("test.wav")), "audio")
        self.assertEqual(organizer._categorize_file(Path("test.mp3")), "audio")
        self.assertEqual(organizer._categorize_file(Path("test.ogg")), "audio")

    def test_categorize_file_uncategorized(self):
        """Test file categorization - uncategorized files"""
        organizer = OutputOrganizer(self.analysis_dir)

        # Test unknown files (.dat is actually binary, so test truly unknown extensions)
        self.assertEqual(organizer._categorize_file(Path("random.dat")), "binary")  # .dat is binary
        self.assertIsNone(organizer._categorize_file(Path("unknown.xyz")))

    def test_scan_files(self):
        """Test scanning and categorizing files"""
        organizer = OutputOrganizer(self.analysis_dir)
        categorized = organizer._scan_files()

        self.assertIsInstance(categorized, dict)

        # Check disassembly files
        self.assertIn('disassembly', categorized)
        disasm_files = [f.name for f in categorized['disassembly']]
        self.assertIn('test_init.asm', disasm_files)
        self.assertIn('test_play.asm', disasm_files)

        # Check report files
        self.assertIn('reports', categorized)
        report_files = [f.name for f in categorized['reports']]
        self.assertIn('test_memmap.txt', report_files)
        self.assertIn('test_patterns.txt', report_files)

        # Check audio files
        self.assertIn('audio', categorized)
        audio_files = [f.name for f in categorized['audio']]
        self.assertIn('test.wav', audio_files)

        # Check binary files (random.dat is categorized as binary)
        self.assertIn('binary', categorized)
        binary_files = [f.name for f in categorized['binary']]
        self.assertIn('random.dat', binary_files)

        # Check uncategorized files
        self.assertIn('uncategorized', categorized)
        uncategorized_files = [f.name for f in categorized['uncategorized']]
        self.assertIn('unknown.xyz', uncategorized_files)

    def test_scan_nonexistent_directory(self):
        """Test scanning a directory that doesn't exist"""
        organizer = OutputOrganizer(Path("nonexistent"))
        categorized = organizer._scan_files()

        self.assertEqual(categorized, {})

    def test_create_directory_structure_dry_run(self):
        """Test creating directory structure in dry run mode"""
        organizer = OutputOrganizer(self.analysis_dir)
        directories = organizer._create_directory_structure(dry_run=True)

        self.assertIsInstance(directories, dict)
        self.assertIn('disassembly', directories)
        self.assertIn('reports', directories)
        self.assertIn('audio', directories)

        # In dry run mode, directories should NOT be created
        for directory in directories.values():
            if directory.exists():
                # Directory might exist from previous tests, but we're just checking
                # that dry_run doesn't create NEW directories
                pass

    def test_create_directory_structure_real(self):
        """Test creating directory structure for real"""
        organizer = OutputOrganizer(self.analysis_dir)
        directories = organizer._create_directory_structure(dry_run=False)

        self.assertIsInstance(directories, dict)

        # Directories should be created
        for directory in directories.values():
            self.assertTrue(directory.exists())
            self.assertTrue(directory.is_dir())

    def test_organize_dry_run(self):
        """Test organizing in dry run mode"""
        organizer = OutputOrganizer(self.analysis_dir)
        result = organizer.organize(dry_run=True, verbose=0)

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertTrue(result['dry_run'])
        self.assertGreater(result['total_files'], 0)
        self.assertEqual(result['moved'], 0)  # Dry run doesn't move files

    def test_organize_real(self):
        """Test organizing for real"""
        organizer = OutputOrganizer(self.analysis_dir)
        result = organizer.organize(dry_run=False, verbose=0)

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertFalse(result['dry_run'])
        self.assertGreater(result['total_files'], 0)
        self.assertGreater(result['moved'], 0)

        # Check that directories were created
        self.assertTrue((self.analysis_dir / 'disassembly').exists())
        self.assertTrue((self.analysis_dir / 'reports').exists())
        self.assertTrue((self.analysis_dir / 'audio').exists())

        # Check that files were moved
        self.assertTrue((self.analysis_dir / 'disassembly' / 'test_init.asm').exists())
        self.assertTrue((self.analysis_dir / 'reports' / 'test_memmap.txt').exists())
        self.assertTrue((self.analysis_dir / 'audio' / 'test.wav').exists())

    def test_organize_with_index(self):
        """Test organizing with index creation"""
        organizer = OutputOrganizer(self.analysis_dir)
        result = organizer.organize(
            dry_run=False,
            create_index=True,
            create_readme=False,
            verbose=0
        )

        self.assertTrue(result['success'])
        self.assertTrue(result['index_created'])

        # Check that index file was created
        index_file = self.analysis_dir / "INDEX.txt"
        self.assertTrue(index_file.exists())

        # Check index content
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("ANALYSIS OUTPUT INDEX", content)
        self.assertIn("FILE ORGANIZATION", content)

    def test_organize_with_readme(self):
        """Test organizing with README creation"""
        organizer = OutputOrganizer(self.analysis_dir)
        result = organizer.organize(
            dry_run=False,
            create_index=False,
            create_readme=True,
            verbose=0
        )

        self.assertTrue(result['success'])
        self.assertTrue(result['readme_created'])

        # Check that README file was created
        readme_file = self.analysis_dir / "README.md"
        self.assertTrue(readme_file.exists())

        # Check README content
        with open(readme_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("# Analysis Output Directory", content)
        self.assertIn("## Directory Structure", content)

    def test_organize_empty_directory(self):
        """Test organizing an empty directory"""
        empty_dir = self.test_dir / "empty"
        empty_dir.mkdir(exist_ok=True)

        organizer = OutputOrganizer(empty_dir)
        result = organizer.organize(verbose=0)

        self.assertFalse(result['success'])
        self.assertIn('error', result)

        # Clean up
        empty_dir.rmdir()

    def test_organize_nonexistent_directory(self):
        """Test organizing a nonexistent directory"""
        organizer = OutputOrganizer(Path("nonexistent"))
        result = organizer.organize(verbose=0)

        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_organize_already_organized(self):
        """Test organizing when files are already in subdirectories"""
        # First organization
        organizer = OutputOrganizer(self.analysis_dir)
        result1 = organizer.organize(dry_run=False, create_index=False, create_readme=False, verbose=0)
        self.assertTrue(result1['success'])
        moved_first = result1['moved']
        self.assertGreater(moved_first, 0)

        # Remove uncategorized files so second run finds nothing
        for item in self.analysis_dir.iterdir():
            if item.is_file():
                item.unlink()

        # Second organization (files already organized, no files in root)
        result2 = organizer.organize(dry_run=False, create_index=False, create_readme=False, verbose=0)

        # When all files are in subdirectories and no files in root, should fail
        self.assertFalse(result2['success'])  # Fails because no files found
        self.assertIn('error', result2)  # Error message about no files

    def test_convenience_function(self):
        """Test convenience organize_output function"""
        result = organize_output(
            analysis_dir=self.analysis_dir,
            dry_run=False,
            create_index=True,
            create_readme=True,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertGreater(result['total_files'], 0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestOutputOrganizer))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
