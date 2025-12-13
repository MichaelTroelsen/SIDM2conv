#!/usr/bin/env python3
"""
MIDI Comparison Test Tool

Tests both SIDtool and Python emulator on multiple SID files,
comparing their MIDI outputs for equivalence.

Usage:
    # Test Python emulator only (no Ruby needed)
    python test_midi_comparison.py --python-only

    # Test both SIDtool and Python emulator (requires Ruby)
    python test_midi_comparison.py --both

    # Compare specific files
    python test_midi_comparison.py --compare file1.mid file2.mid
"""

import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from mido import MidiFile
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    print("ERROR: mido library not installed")
    print("Install with: pip install mido")
    sys.exit(1)

from sidm2.sid_to_midi_emulator import convert_sid_to_midi

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MIDIComparisonTool:
    """Compare MIDI files from different sources"""

    def __init__(self, sidtool_path: str = None):
        self.sidtool_path = sidtool_path or self._find_sidtool()
        self.results = []

    def _find_sidtool(self) -> Optional[str]:
        """Find SIDtool installation"""
        possible_paths = [
            'C:/Users/mit/Downloads/sidtool-master/sidtool-master',
            '/c/Users/mit/Downloads/sidtool-master/sidtool-master',
        ]

        for path in possible_paths:
            sidtool_bin = os.path.join(path, 'bin', 'sidtool')
            if os.path.exists(sidtool_bin):
                return path

        return None

    def check_ruby(self) -> bool:
        """Check if Ruby is installed"""
        try:
            result = subprocess.run(['ruby', '--version'],
                                  capture_output=True,
                                  text=True,
                                  check=True)
            logger.info(f"Ruby found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def export_with_sidtool(self, sid_path: str, midi_path: str,
                          frames: int = 1000) -> bool:
        """Export MIDI using SIDtool (requires Ruby)"""
        if not self.sidtool_path:
            logger.error("SIDtool not found")
            return False

        sidtool_bin = os.path.join(self.sidtool_path, 'bin', 'sidtool')
        sidtool_lib = os.path.join(self.sidtool_path, 'lib')

        # Convert to absolute paths
        abs_sid_path = os.path.abspath(sid_path)
        abs_midi_path = os.path.abspath(midi_path)

        # Run sidtool from source with proper load path
        cmd = [
            'ruby',
            '-I', sidtool_lib,
            sidtool_bin,
            '--format', 'midi',
            '-o', abs_midi_path,
            '-f', str(frames),
            abs_sid_path
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.sidtool_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )

            if os.path.exists(midi_path):
                size = os.path.getsize(midi_path)
                logger.info(f"  SIDtool MIDI exported: {size} bytes")
                return True
            else:
                logger.error("  SIDtool did not create MIDI file")
                return False

        except subprocess.TimeoutExpired:
            logger.error("  SIDtool timed out (>60s)")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"  SIDtool failed: {e}")
            if e.stderr:
                logger.error(f"  Error: {e.stderr}")
            return False

    def export_with_python(self, sid_path: str, midi_path: str,
                         frames: int = 1000) -> bool:
        """Export MIDI using Python emulator"""
        try:
            success = convert_sid_to_midi(sid_path, midi_path, frames=frames)
            if success and os.path.exists(midi_path):
                size = os.path.getsize(midi_path)
                logger.info(f"  Python MIDI exported: {size} bytes")
                return True
            else:
                logger.error("  Python emulator failed")
                return False
        except Exception as e:
            logger.error(f"  Python emulator error: {e}")
            return False

    def analyze_midi(self, midi_path: str) -> Dict:
        """Analyze MIDI file structure"""
        try:
            mid = MidiFile(midi_path)

            stats = {
                'tracks': len(mid.tracks),
                'ticks_per_beat': mid.ticks_per_beat,
                'total_messages': 0,
                'note_on_count': 0,
                'note_off_count': 0,
                'tempo_changes': 0,
                'track_details': []
            }

            for track_idx, track in enumerate(mid.tracks):
                track_stats = {
                    'index': track_idx,
                    'messages': len(track),
                    'note_on': 0,
                    'note_off': 0,
                    'notes': []
                }

                for msg in track:
                    stats['total_messages'] += 1

                    if msg.type == 'note_on' and msg.velocity > 0:
                        stats['note_on_count'] += 1
                        track_stats['note_on'] += 1
                        track_stats['notes'].append(msg.note)
                    elif msg.type in ('note_off', 'note_on') and \
                         (msg.type == 'note_off' or msg.velocity == 0):
                        stats['note_off_count'] += 1
                        track_stats['note_off'] += 1
                    elif msg.type == 'set_tempo':
                        stats['tempo_changes'] += 1

                stats['track_details'].append(track_stats)

            return stats

        except Exception as e:
            logger.error(f"Failed to analyze {midi_path}: {e}")
            return None

    def compare_midi_files(self, midi1_path: str, midi2_path: str) -> Dict:
        """Compare two MIDI files in detail"""
        logger.info(f"\nComparing:")
        logger.info(f"  File 1: {midi1_path}")
        logger.info(f"  File 2: {midi2_path}")

        stats1 = self.analyze_midi(midi1_path)
        stats2 = self.analyze_midi(midi2_path)

        if not stats1 or not stats2:
            return {'error': 'Failed to analyze one or both files'}

        comparison = {
            'file1': midi1_path,
            'file2': midi2_path,
            'stats1': stats1,
            'stats2': stats2,
            'differences': {},
            'identical': True
        }

        # Compare basic stats
        if stats1['tracks'] != stats2['tracks']:
            comparison['differences']['tracks'] = (stats1['tracks'], stats2['tracks'])
            comparison['identical'] = False

        if stats1['ticks_per_beat'] != stats2['ticks_per_beat']:
            comparison['differences']['ticks_per_beat'] = \
                (stats1['ticks_per_beat'], stats2['ticks_per_beat'])
            comparison['identical'] = False

        if stats1['note_on_count'] != stats2['note_on_count']:
            comparison['differences']['note_on_count'] = \
                (stats1['note_on_count'], stats2['note_on_count'])
            comparison['identical'] = False

        if stats1['note_off_count'] != stats2['note_off_count']:
            comparison['differences']['note_off_count'] = \
                (stats1['note_off_count'], stats2['note_off_count'])
            comparison['identical'] = False

        # Compare track details
        for i in range(min(len(stats1['track_details']), len(stats2['track_details']))):
            track1 = stats1['track_details'][i]
            track2 = stats2['track_details'][i]

            if track1['note_on'] != track2['note_on']:
                comparison['differences'][f'track_{i}_note_on'] = \
                    (track1['note_on'], track2['note_on'])
                comparison['identical'] = False

            if track1['notes'] != track2['notes']:
                comparison['differences'][f'track_{i}_notes'] = \
                    f"Different note sequences"
                comparison['identical'] = False

        return comparison

    def test_single_file(self, sid_path: str, frames: int = 1000,
                        test_both: bool = False) -> Dict:
        """Test a single SID file with one or both tools"""
        basename = os.path.basename(sid_path).replace('.sid', '')
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {basename}")
        logger.info(f"{'='*60}")

        result = {
            'sid_file': sid_path,
            'basename': basename,
            'frames': frames,
            'python_success': False,
            'sidtool_success': False,
            'comparison': None
        }

        output_dir = 'output/midi_comparison'
        os.makedirs(output_dir, exist_ok=True)

        # Test Python emulator
        python_midi = os.path.join(output_dir, f'{basename}_python.mid')
        logger.info("\n[1/2] Testing Python emulator...")
        result['python_success'] = self.export_with_python(
            sid_path, python_midi, frames
        )

        if result['python_success']:
            result['python_stats'] = self.analyze_midi(python_midi)
            logger.info(f"  ✅ Python: {result['python_stats']['note_on_count']} notes")

        # Test SIDtool if requested
        if test_both:
            sidtool_midi = os.path.join(output_dir, f'{basename}_sidtool.mid')
            logger.info("\n[2/2] Testing SIDtool...")

            if not self.check_ruby():
                logger.error("  ❌ Ruby not installed - cannot test SIDtool")
                logger.info("\n  To install Ruby:")
                logger.info("    1. Download from: https://rubyinstaller.org/downloads/")
                logger.info("    2. Run installer as Administrator")
                logger.info("    3. Re-run this script with --both")
                result['sidtool_success'] = False
            else:
                result['sidtool_success'] = self.export_with_sidtool(
                    sid_path, sidtool_midi, frames
                )

                if result['sidtool_success']:
                    result['sidtool_stats'] = self.analyze_midi(sidtool_midi)
                    logger.info(f"  ✅ SIDtool: {result['sidtool_stats']['note_on_count']} notes")

                    # Compare outputs
                    logger.info("\n[3/3] Comparing outputs...")
                    result['comparison'] = self.compare_midi_files(
                        sidtool_midi, python_midi
                    )

                    if result['comparison']['identical']:
                        logger.info("  ✅ IDENTICAL - 100% match!")
                    else:
                        logger.info("  ⚠️  DIFFERENCES found:")
                        for key, value in result['comparison']['differences'].items():
                            logger.info(f"    - {key}: {value}")

        self.results.append(result)
        return result

    def generate_report(self, output_path: str = 'output/midi_comparison/REPORT.md'):
        """Generate markdown report of all tests"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# MIDI Comparison Test Report\n\n")
            f.write(f"**Total Files Tested**: {len(self.results)}\n\n")

            # Summary
            python_success = sum(1 for r in self.results if r['python_success'])
            sidtool_success = sum(1 for r in self.results if r['sidtool_success'])
            identical = sum(1 for r in self.results
                          if r.get('comparison') and r['comparison']['identical'])

            f.write("## Summary\n\n")
            f.write(f"- **Python Emulator**: {python_success}/{len(self.results)} successful\n")
            f.write(f"- **SIDtool**: {sidtool_success}/{len(self.results)} successful\n")
            if sidtool_success > 0:
                f.write(f"- **Identical Outputs**: {identical}/{sidtool_success} (100% match)\n")
            f.write("\n---\n\n")

            # Detailed results
            f.write("## Detailed Results\n\n")

            for result in self.results:
                f.write(f"### {result['basename']}\n\n")
                f.write(f"**SID File**: `{result['sid_file']}`\n\n")
                f.write(f"**Frames**: {result['frames']}\n\n")

                # Python results
                if result['python_success']:
                    stats = result['python_stats']
                    f.write(f"**Python Emulator**: ✅ Success\n")
                    f.write(f"- Tracks: {stats['tracks']}\n")
                    f.write(f"- Notes: {stats['note_on_count']}\n")
                    f.write(f"- Messages: {stats['total_messages']}\n")
                else:
                    f.write(f"**Python Emulator**: ❌ Failed\n")

                f.write("\n")

                # SIDtool results
                if result['sidtool_success']:
                    stats = result['sidtool_stats']
                    f.write(f"**SIDtool**: ✅ Success\n")
                    f.write(f"- Tracks: {stats['tracks']}\n")
                    f.write(f"- Notes: {stats['note_on_count']}\n")
                    f.write(f"- Messages: {stats['total_messages']}\n")
                elif 'sidtool_success' in result:
                    f.write(f"**SIDtool**: ❌ Failed (Ruby not installed)\n")

                f.write("\n")

                # Comparison
                if result.get('comparison'):
                    comp = result['comparison']
                    if comp['identical']:
                        f.write(f"**Comparison**: ✅ **IDENTICAL** (100% match)\n")
                    else:
                        f.write(f"**Comparison**: ⚠️  Differences found\n\n")
                        f.write("Differences:\n")
                        for key, value in comp['differences'].items():
                            f.write(f"- `{key}`: {value}\n")

                f.write("\n---\n\n")

        logger.info(f"\nReport saved: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Test and compare MIDI exports from SIDtool and Python emulator'
    )

    parser.add_argument('--python-only', action='store_true',
                       help='Test Python emulator only (no Ruby needed)')
    parser.add_argument('--both', action='store_true',
                       help='Test both SIDtool and Python emulator')
    parser.add_argument('--files', type=int, default=10,
                       help='Number of SID files to test (default: 10)')
    parser.add_argument('--frames', type=int, default=1000,
                       help='Number of frames to emulate (default: 1000)')
    parser.add_argument('--compare', nargs=2, metavar=('FILE1', 'FILE2'),
                       help='Compare two specific MIDI files')
    parser.add_argument('--sid-dir', default='SID',
                       help='Directory containing SID files')

    args = parser.parse_args()

    tool = MIDIComparisonTool()

    # Compare specific files
    if args.compare:
        comp = tool.compare_midi_files(args.compare[0], args.compare[1])
        if comp['identical']:
            print("\n✅ Files are IDENTICAL (100% match)")
            return 0
        else:
            print("\n⚠️  Files have DIFFERENCES:")
            for key, value in comp['differences'].items():
                print(f"  - {key}: {value}")
            return 1

    # Test multiple files
    test_both = args.both
    if not args.python_only and not args.both:
        # Default: try both if Ruby available
        test_both = tool.check_ruby()
        if not test_both:
            logger.info("Ruby not installed - testing Python emulator only")
            logger.info("Use --both after installing Ruby to compare outputs\n")

    # Get SID files
    sid_files = sorted(Path(args.sid_dir).glob('*.sid'))[:args.files]

    if not sid_files:
        logger.error(f"No SID files found in {args.sid_dir}")
        return 1

    logger.info(f"\n{'='*60}")
    logger.info(f"MIDI Comparison Test")
    logger.info(f"{'='*60}")
    logger.info(f"Files to test: {len(sid_files)}")
    logger.info(f"Frames per file: {args.frames}")
    logger.info(f"Mode: {'Both tools' if test_both else 'Python only'}")
    logger.info(f"{'='*60}\n")

    # Test each file
    for sid_path in sid_files:
        tool.test_single_file(str(sid_path), frames=args.frames, test_both=test_both)

    # Generate report
    tool.generate_report()

    # Final summary
    python_ok = sum(1 for r in tool.results if r['python_success'])
    logger.info(f"\n{'='*60}")
    logger.info(f"Test Complete!")
    logger.info(f"{'='*60}")
    logger.info(f"Python emulator: {python_ok}/{len(tool.results)} successful")

    if test_both:
        sidtool_ok = sum(1 for r in tool.results if r['sidtool_success'])
        identical = sum(1 for r in tool.results
                       if r.get('comparison') and r['comparison']['identical'])
        logger.info(f"SIDtool: {sidtool_ok}/{len(tool.results)} successful")
        if sidtool_ok > 0:
            logger.info(f"Identical: {identical}/{sidtool_ok} (100% match)")

    logger.info(f"\nDetailed report: output/midi_comparison/REPORT.md")
    logger.info(f"{'='*60}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
