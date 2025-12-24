"""Test SID Pattern Database

Tests the sidid_patterns.txt pattern database against real SID files.

Usage:
    python pyscript/test_pattern_database.py                    # Test on Laxity collection
    python pyscript/test_pattern_database.py --file music.sid   # Test single file
    python pyscript/test_pattern_database.py --dir path/to/sids # Test directory

Expected Results:
    - Laxity collection (286 files): 80%+ Laxity detection
    - Other collections: Measure false positive rate
"""

import argparse
from pathlib import Path
from collections import Counter
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.sid_pattern_matcher import SIDPatternMatcher, SIDPatternParser


class PatternDatabaseTester:
    """Tests pattern database against SID files."""

    def __init__(self, pattern_file: Path):
        """Initialize tester with pattern database.

        Args:
            pattern_file: Path to sidid_patterns.txt
        """
        self.matcher = SIDPatternMatcher()
        self.parser = SIDPatternParser(self.matcher)

        # Load patterns
        if not self.parser.parse_file(pattern_file):
            raise ValueError(f"Failed to load pattern file: {pattern_file}")

        print(f"Loaded {self.matcher.get_num_players()} players with {self.matcher.get_num_patterns()} patterns")

    def test_file(self, sid_file: Path) -> dict:
        """Test a single SID file.

        Args:
            sid_file: Path to .sid file

        Returns:
            Dictionary with test results:
            {
                'file': filename,
                'detected': list of detected player names,
                'matched': bool (True if any player detected)
            }
        """
        # Read SID file
        try:
            sid_data = sid_file.read_bytes()
        except Exception as e:
            return {
                'file': sid_file.name,
                'detected': [],
                'matched': False,
                'error': str(e)
            }

        # Identify players
        result = self.matcher.identify_buffer(sid_data)
        detected = [name.strip() for name in result.split() if name.strip()]

        return {
            'file': sid_file.name,
            'detected': detected,
            'matched': len(detected) > 0
        }

    def test_directory(self, directory: Path, pattern: str = "*.sid") -> list:
        """Test all SID files in directory.

        Args:
            directory: Path to directory
            pattern: Glob pattern for files (default: *.sid)

        Returns:
            List of test results
        """
        results = []

        sid_files = list(directory.glob(pattern))
        print(f"\nTesting {len(sid_files)} files in {directory}...")

        for i, sid_file in enumerate(sid_files, 1):
            result = self.test_file(sid_file)
            results.append(result)

            # Progress indicator
            if i % 10 == 0:
                print(f"  Tested {i}/{len(sid_files)}...")

        return results

    def print_statistics(self, results: list, expected_player: str = None):
        """Print test statistics.

        Args:
            results: List of test results from test_directory()
            expected_player: If provided, report accuracy for this player
        """
        print("\n" + "=" * 70)
        print("PATTERN DATABASE TEST RESULTS")
        print("=" * 70)

        # Overall statistics
        total_files = len(results)
        matched_files = sum(1 for r in results if r['matched'])
        match_rate = (matched_files / total_files * 100) if total_files > 0 else 0

        print(f"\nTotal files tested: {total_files}")
        print(f"Files with matches: {matched_files} ({match_rate:.1f}%)")
        print(f"Files with no match: {total_files - matched_files} ({100-match_rate:.1f}%)")

        # Player detection counts
        player_counts = Counter()
        for result in results:
            for player_name in result['detected']:
                player_counts[player_name] += 1

        print(f"\nPlayer Detection Counts:")
        for player, count in player_counts.most_common():
            pct = (count / total_files * 100) if total_files > 0 else 0
            print(f"  {player}: {count} ({pct:.1f}%)")

        # Expected player accuracy (if specified)
        if expected_player:
            expected_count = player_counts.get(expected_player, 0)
            expected_pct = (expected_count / total_files * 100) if total_files > 0 else 0

            print(f"\nExpected Player: {expected_player}")
            print(f"  Detected in: {expected_count}/{total_files} files ({expected_pct:.1f}%)")

            if expected_pct >= 80:
                status = "EXCELLENT [OK]"
            elif expected_pct >= 60:
                status = "GOOD [+]"
            elif expected_pct >= 40:
                status = "FAIR [~]"
            else:
                status = "POOR [-]"

            print(f"  Status: {status}")

        # Errors
        errors = [r for r in results if 'error' in r]
        if errors:
            print(f"\nErrors: {len(errors)}")
            for err in errors[:10]:  # Show first 10 errors
                print(f"  {err['file']}: {err['error']}")

        # Files with no match (sample)
        no_match = [r for r in results if not r['matched']]
        if no_match:
            print(f"\nSample files with no match (first 10):")
            for result in no_match[:10]:
                print(f"  {result['file']}")

        print("\n" + "=" * 70)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test SID Pattern Database")
    parser.add_argument('--file', type=Path, help='Test single SID file')
    parser.add_argument('--dir', type=Path, help='Test directory of SID files')
    parser.add_argument('--pattern', default='*.sid', help='Glob pattern for files (default: *.sid)')
    parser.add_argument('--expected', help='Expected player name for accuracy measurement')
    parser.add_argument('--patterns', type=Path,
                       default=Path(__file__).parent / 'sidid_patterns.txt',
                       help='Pattern database file (default: sidid_patterns.txt)')

    args = parser.parse_args()

    # Validate pattern file exists
    if not args.patterns.exists():
        print(f"ERROR: Pattern file not found: {args.patterns}")
        return 1

    # Create tester
    print(f"Loading pattern database: {args.patterns}")
    tester = PatternDatabaseTester(args.patterns)

    # Run tests
    if args.file:
        # Test single file
        if not args.file.exists():
            print(f"ERROR: File not found: {args.file}")
            return 1

        result = tester.test_file(args.file)

        print(f"\nFile: {result['file']}")
        if result['matched']:
            print(f"Detected players: {', '.join(result['detected'])}")
        else:
            print("No players detected")

        if 'error' in result:
            print(f"ERROR: {result['error']}")

    elif args.dir:
        # Test directory
        if not args.dir.exists():
            print(f"ERROR: Directory not found: {args.dir}")
            return 1

        results = tester.test_directory(args.dir, args.pattern)
        tester.print_statistics(results, expected_player=args.expected)

    else:
        # Default: Test Laxity collection
        laxity_dir = Path(__file__).parent.parent / "SIDS" / "Laxity NewPlayer v21"

        if not laxity_dir.exists():
            print(f"ERROR: Laxity collection not found: {laxity_dir}")
            print("\nUsage:")
            print("  python pyscript/test_pattern_database.py --file music.sid")
            print("  python pyscript/test_pattern_database.py --dir path/to/sids")
            return 1

        print(f"Testing Laxity collection: {laxity_dir}")
        results = tester.test_directory(laxity_dir)
        tester.print_statistics(results, expected_player="Laxity_NewPlayer_v21")

    return 0


if __name__ == "__main__":
    sys.exit(main())
