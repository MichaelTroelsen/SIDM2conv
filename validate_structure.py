"""
Validate SID Structure Comparison

Test the comprehensive structure extraction and comparison system.
This tool helps achieve 99% accuracy by comparing music structure before/after conversion.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

from sidm2.sid_structure_extractor import SIDStructureExtractor, extract_and_compare
from sidm2.logging_config import setup_logging


def test_structure_extraction(sid_path: str, duration: int = 10):
    """Test structure extraction on a single SID file"""
    print(f"\n{'='*70}")
    print(f"Testing Structure Extraction: {os.path.basename(sid_path)}")
    print(f"{'='*70}\n")

    extractor = SIDStructureExtractor()

    # Extract structure
    structure = extractor.extract_structure(sid_path, duration)

    # Display results
    print(f"Duration: {structure['statistics']['duration']:.2f} seconds")
    print(f"Total Frames: {structure['statistics']['total_frames']}")
    print()

    print("Voice Activity:")
    for voice in range(3):
        count = structure['statistics']['voice_activity_counts'][voice]
        notes = structure['statistics']['unique_notes'][voice]
        print(f"  Voice {voice+1}: {count} events, {len(notes)} unique notes")
        if notes:
            print(f"    Notes: {', '.join(notes[:10])}{' ...' if len(notes) > 10 else ''}")

    print()
    print(f"Unique Waveforms: {structure['statistics']['unique_waveforms']}")
    print(f"Instruments: {len(structure['instruments'])}")
    print(f"Filter Changes: {structure['statistics']['filter_changes']}")

    # Show sample of instruments
    if structure['instruments']:
        print("\nInstrument Summary:")
        for instr_id, instr in list(structure['instruments'].items())[:5]:
            print(f"  Instrument {instr_id}:")
            print(f"    Waveform: 0x{instr['waveform']:02X}")
            print(f"    Attack/Decay: 0x{instr['attack_decay']:02X}")
            print(f"    Sustain/Release: 0x{instr['sustain_release']:02X}")
            print(f"    Usage: {instr['usage_count']} times")

    # Show detected patterns
    print("\nDetected Patterns:")
    for voice in range(3):
        patterns = structure['patterns'][voice]
        if patterns:
            print(f"  Voice {voice+1}: {len(patterns)} patterns")
            for i, pattern in enumerate(patterns[:3]):
                print(f"    Pattern {i+1}: Length {pattern['length']}, starts at note {pattern['start']}")

    return structure


def compare_sid_structures(original_sid: str, converted_sid: str,
                          output_dir: str = None, duration: int = 10):
    """Compare structures of original and converted SID files"""
    print(f"\n{'='*70}")
    print(f"Comparing SID Structures")
    print(f"{'='*70}\n")

    print(f"Original:  {os.path.basename(original_sid)}")
    print(f"Converted: {os.path.basename(converted_sid)}")
    print()

    # Extract and compare
    comparison = extract_and_compare(original_sid, converted_sid, output_dir, duration)

    # Display results
    print(f"\n{'='*70}")
    print(f"Comparison Results")
    print(f"{'='*70}\n")

    print(f"Overall Similarity: {comparison['overall_similarity']*100:.2f}%\n")

    # Header comparison
    print("Header Comparison:")
    if comparison['header_match']['differences']:
        for diff in comparison['header_match']['differences']:
            print(f"  - {diff}")
    else:
        print("  ✓ Headers match")
    print(f"  Similarity: {comparison['header_match']['similarity']*100:.1f}%\n")

    # Voice activity comparison
    print("Voice Activity Comparison:")
    for voice in range(3):
        match = comparison['voice_activity_match'][voice]
        print(f"  Voice {voice+1}:")
        print(f"    Length Difference: {match['length_diff']} events")
        print(f"    Note Similarity: {match['note_similarity']*100:.2f}%")
        print(f"    Matching Notes: {match['matching_notes']}/{match['total_compared']}")
        print(f"    Overall Similarity: {match['similarity']*100:.2f}%")

    # Instrument comparison
    print(f"\nInstrument Comparison:")
    instr_match = comparison['instrument_match']
    print(f"  Matching Instruments: {instr_match['matching_count']}/{instr_match['total_unique']}")
    print(f"  Similarity: {instr_match['similarity']*100:.2f}%")

    # Filter comparison
    print(f"\nFilter Comparison:")
    filt_match = comparison['filter_match']
    print(f"  Filter Change Count Diff: {filt_match['count_diff']}")
    print(f"  Similarity: {filt_match['similarity']*100:.2f}%")

    # Statistics comparison
    print(f"\nStatistics Comparison:")
    stats_match = comparison['statistics_match']
    if stats_match['differences']:
        for diff in stats_match['differences']:
            print(f"  - {diff}")
    else:
        print("  ✓ Statistics match")
    print(f"  Similarity: {stats_match['similarity']*100:.1f}%")

    # Grade the similarity
    overall = comparison['overall_similarity'] * 100
    if overall >= 95:
        grade = "EXCELLENT"
    elif overall >= 85:
        grade = "GOOD"
    elif overall >= 70:
        grade = "FAIR"
    else:
        grade = "POOR"

    print(f"\n{'='*70}")
    print(f"Grade: {grade} ({overall:.2f}%)")
    print(f"{'='*70}\n")

    return comparison


def batch_validate_structures(sid_dir: str, output_dir: str, duration: int = 10):
    """Validate all SID files in a directory using structure comparison"""
    print(f"\n{'='*70}")
    print(f"Batch Structure Validation")
    print(f"{'='*70}\n")

    # Find all SID files
    sid_files = sorted(Path(sid_dir).glob("*.sid"))
    print(f"Found {len(sid_files)} SID files in {sid_dir}\n")

    results = []

    for sid_file in sid_files:
        print(f"\nProcessing: {sid_file.name}")

        # Look for corresponding exported SID file
        # Assuming naming convention: original.sid -> original_exported.sid
        base_name = sid_file.stem
        exported_sid = sid_file.parent / f"{base_name}_exported.sid"

        if not exported_sid.exists():
            print(f"  ⚠ No exported SID found: {exported_sid.name}")
            continue

        # Create output directory for this file
        file_output_dir = os.path.join(output_dir, base_name)
        os.makedirs(file_output_dir, exist_ok=True)

        try:
            # Compare structures
            comparison = extract_and_compare(
                str(sid_file),
                str(exported_sid),
                file_output_dir,
                duration
            )

            similarity = comparison['overall_similarity'] * 100

            result = {
                'file': sid_file.name,
                'similarity': similarity,
                'grade': _get_grade(similarity),
                'output_dir': file_output_dir
            }

            results.append(result)

            print(f"  ✓ Similarity: {similarity:.2f}% ({result['grade']})")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'file': sid_file.name,
                'similarity': 0.0,
                'grade': 'ERROR',
                'error': str(e)
            })

    # Generate summary report
    print(f"\n{'='*70}")
    print(f"Batch Validation Summary")
    print(f"{'='*70}\n")

    print(f"Total Files: {len(results)}")
    print(f"Average Similarity: {sum(r['similarity'] for r in results)/len(results):.2f}%\n")

    # Group by grade
    by_grade = {'EXCELLENT': [], 'GOOD': [], 'FAIR': [], 'POOR': [], 'ERROR': []}
    for result in results:
        by_grade[result['grade']].append(result)

    for grade in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'ERROR']:
        files = by_grade[grade]
        if files:
            print(f"{grade}: {len(files)} files")
            for f in files:
                print(f"  - {f['file']}: {f['similarity']:.2f}%")

    # Save summary
    summary_file = os.path.join(output_dir, "structure_validation_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nSummary saved to: {summary_file}")

    return results


def _get_grade(similarity: float) -> str:
    """Convert similarity percentage to grade"""
    if similarity >= 95:
        return "EXCELLENT"
    elif similarity >= 85:
        return "GOOD"
    elif similarity >= 70:
        return "FAIR"
    else:
        return "POOR"


def main():
    parser = argparse.ArgumentParser(description="SID Structure Validation Tool")
    parser.add_argument("mode", choices=["test", "compare", "batch"],
                       help="Operation mode")
    parser.add_argument("input", help="Input SID file or directory")
    parser.add_argument("--converted", help="Converted SID file (for compare mode)")
    parser.add_argument("--output", help="Output directory for results")
    parser.add_argument("--duration", type=int, default=10,
                       help="Analysis duration in seconds (default: 10)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

    try:
        if args.mode == "test":
            # Test single file structure extraction
            test_structure_extraction(args.input, args.duration)

        elif args.mode == "compare":
            # Compare two SID files
            if not args.converted:
                print("Error: --converted required for compare mode")
                return 1

            output_dir = args.output or "structure_output"
            compare_sid_structures(args.input, args.converted, output_dir, args.duration)

        elif args.mode == "batch":
            # Batch validate directory
            output_dir = args.output or "structure_validation_output"
            batch_validate_structures(args.input, output_dir, args.duration)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
