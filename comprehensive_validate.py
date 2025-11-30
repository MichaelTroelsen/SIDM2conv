"""
Comprehensive SID Validation

Uses ALL available tools to validate conversion accuracy:
1. Register-level validation (siddump comparison)
2. Audio-level validation (WAV comparison)
3. Structure-level validation (music structure extraction)

This comprehensive approach helps achieve 99% accuracy by identifying
issues at multiple levels and learning from the differences.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

from sidm2.validation import quick_validate
from sidm2.wav_comparison import WAVComparator
from sidm2.sid_structure_analyzer import analyze_and_compare
from sidm2.logging_config import setup_logging

logger = logging.getLogger(__name__)


def comprehensive_validate(original_sid: str, converted_sid: str,
                          output_dir: str, duration: int = 10):
    """
    Comprehensive validation using all available methods

    Args:
        original_sid: Original SID file
        converted_sid: Converted SID file (from SF2)
        output_dir: Output directory for results
        duration: Duration to analyze in seconds

    Returns:
        Combined validation results
    """
    print(f"\n{'='*70}")
    print(f"Comprehensive SID Validation")
    print(f"{'='*70}\n")

    print(f"Original:  {os.path.basename(original_sid)}")
    print(f"Converted: {os.path.basename(converted_sid)}")
    print(f"Duration:  {duration} seconds")
    print()

    os.makedirs(output_dir, exist_ok=True)

    results = {
        'timestamp': datetime.now().isoformat(),
        'original_sid': original_sid,
        'converted_sid': converted_sid,
        'duration': duration,
        'register_validation': None,
        'audio_validation': None,
        'structure_validation': None,
        'overall_score': 0.0,
        'grade': 'UNKNOWN',
        'recommendations': []
    }

    # ========================================
    # 1. REGISTER-LEVEL VALIDATION (siddump)
    # ========================================
    print(f"{'='*70}")
    print("1. REGISTER-LEVEL VALIDATION (siddump)")
    print(f"{'='*70}\n")

    try:
        register_results = quick_validate(original_sid, converted_sid)

        if register_results:
            results['register_validation'] = {
                'overall_accuracy': register_results.get('overall_accuracy', 0),
                'frame_accuracy': register_results.get('frame_accuracy', 0),
                'voice_accuracy': register_results.get('voice_accuracy', 0),
                'register_accuracy': register_results.get('register_accuracy', 0),
                'filter_accuracy': register_results.get('filter_accuracy', 0),
                'grade': register_results.get('grade', 'UNKNOWN')
            }

            print(f"Overall Accuracy: {register_results['overall_accuracy']:.2f}%")
            print(f"Frame Accuracy:   {register_results['frame_accuracy']:.2f}%")
            print(f"Voice Accuracy:   {register_results['voice_accuracy']:.2f}%")
            print(f"Register Accuracy: {register_results['register_accuracy']:.2f}%")
            print(f"Filter Accuracy:  {register_results['filter_accuracy']:.2f}%")
            print(f"Grade: {register_results['grade']}\n")

            # Analyze register issues
            if register_results['overall_accuracy'] < 95:
                results['recommendations'].append(
                    f"Register accuracy is {register_results['overall_accuracy']:.1f}% - "
                    f"Check voice and filter settings"
                )
        else:
            print("X Register validation failed\n")
            results['recommendations'].append("Register validation failed - check siddump output")

    except Exception as e:
        logger.error(f"Register validation error: {e}")
        print(f"X Register validation error: {e}\n")
        results['recommendations'].append(f"Register validation error: {e}")

    # ========================================
    # 2. AUDIO-LEVEL VALIDATION (WAV)
    # ========================================
    print(f"{'='*70}")
    print("2. AUDIO-LEVEL VALIDATION (WAV Comparison)")
    print(f"{'='*70}\n")

    try:
        comparator = WAVComparator()
        audio_results = comparator.compare_sids_with_wav(
            original_sid,
            converted_sid,
            duration=duration,
            cleanup=True
        )

        if audio_results['comparison']:
            comp = audio_results['comparison']

            results['audio_validation'] = {
                'audio_accuracy': comp['audio_accuracy'],
                'byte_match': comp['byte_match'],
                'rms_difference': comp['rms_difference'],
                'size_match': comp['size_match']
            }

            print(f"Audio Accuracy: {comp['audio_accuracy']:.2f}%")
            print(f"Byte Match:     {comp['byte_match']:.2f}%")
            print(f"RMS Difference: {comp['rms_difference']:.4f}")
            print(f"Size Match:     {'Yes' if comp['size_match'] else 'No'}\n")

            # Analyze audio vs register discrepancy
            if results['register_validation']:
                reg_acc = results['register_validation']['overall_accuracy']
                aud_acc = comp['audio_accuracy']

                if abs(reg_acc - aud_acc) > 20:
                    results['recommendations'].append(
                        f"Large discrepancy between register ({reg_acc:.1f}%) and "
                        f"audio ({aud_acc:.1f}%) accuracy - investigate structural differences"
                    )
        else:
            print(f"X Audio validation failed: {audio_results.get('error', 'Unknown error')}\n")
            results['recommendations'].append("Audio validation failed - check SID2WAV.EXE")

    except Exception as e:
        logger.error(f"Audio validation error: {e}")
        print(f"X Audio validation error: {e}\n")
        results['recommendations'].append(f"Audio validation error: {e}")

    # ========================================
    # 3. STRUCTURE-LEVEL VALIDATION
    # ========================================
    print(f"{'='*70}")
    print("3. STRUCTURE-LEVEL VALIDATION (Music Structure)")
    print(f"{'='*70}\n")

    try:
        structure_dir = os.path.join(output_dir, "structure")
        comparison = analyze_and_compare(
            original_sid,
            converted_sid,
            structure_dir,
            duration=duration
        )

        results['structure_validation'] = {
            'overall_similarity': comparison['overall_similarity'],
            'voice_similarity': {},
            'instrument_similarity': comparison['instrument_comparison']['similarity']
        }

        for voice_num in range(1, 4):
            voice_comp = comparison['voice_comparison'][voice_num]
            results['structure_validation']['voice_similarity'][voice_num] = voice_comp['similarity']

        print(f"Overall Similarity: {comparison['overall_similarity']:.2f}%")

        print(f"\nVoice Activity Similarity:")
        for voice_num in range(1, 4):
            voice_comp = comparison['voice_comparison'][voice_num]
            print(f"  Voice {voice_num}: {voice_comp['similarity']:.2f}% "
                  f"({voice_comp['matching_notes']}/{voice_comp['total_compared']} notes)")

        print(f"\nInstrument Similarity: {comparison['instrument_comparison']['similarity']:.2f}%\n")

        # Analyze structure issues
        if comparison['overall_similarity'] < 90:
            # Check which aspect is worst
            worst_aspect = "unknown"
            worst_score = 100

            voice_avg = sum(comparison['voice_comparison'][v]['similarity']
                          for v in range(1, 4)) / 3

            if voice_avg < worst_score:
                worst_score = voice_avg
                worst_aspect = "voice activity"

            if comparison['instrument_comparison']['similarity'] < worst_score:
                worst_score = comparison['instrument_comparison']['similarity']
                worst_aspect = "instruments"

            results['recommendations'].append(
                f"Structure similarity is {comparison['overall_similarity']:.1f}% - "
                f"worst aspect is {worst_aspect} ({worst_score:.1f}%)"
            )

    except Exception as e:
        logger.error(f"Structure validation error: {e}")
        print(f"X Structure validation error: {e}\n")
        results['recommendations'].append(f"Structure validation error: {e}")

    # ========================================
    # 4. COMBINED ANALYSIS
    # ========================================
    print(f"{'='*70}")
    print("4. COMBINED ANALYSIS")
    print(f"{'='*70}\n")

    # Calculate overall score (weighted average)
    scores = []

    if results['register_validation']:
        scores.append(results['register_validation']['overall_accuracy'] * 0.40)

    if results['audio_validation']:
        scores.append(results['audio_validation']['audio_accuracy'] * 0.30)

    if results['structure_validation']:
        scores.append(results['structure_validation']['overall_similarity'] * 0.30)

    if scores:
        results['overall_score'] = sum(scores) / len(scores) * (len(scores) / 3)

        # Determine grade
        if results['overall_score'] >= 95:
            results['grade'] = "EXCELLENT"
        elif results['overall_score'] >= 85:
            results['grade'] = "GOOD"
        elif results['overall_score'] >= 70:
            results['grade'] = "FAIR"
        else:
            results['grade'] = "POOR"

    print(f"Overall Score: {results['overall_score']:.2f}%")
    print(f"Grade: {results['grade']}\n")

    if results['recommendations']:
        print("Recommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
        print()

    # Save results
    results_file = os.path.join(output_dir, "comprehensive_validation.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {results_file}")

    # Generate HTML report
    generate_html_report(results, output_dir)

    return results


def generate_html_report(results: dict, output_dir: str):
    """Generate HTML report for comprehensive validation"""
    html_file = os.path.join(output_dir, "comprehensive_validation.html")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Comprehensive SID Validation Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #95a5a6; padding-bottom: 8px; }}
        .score {{ font-size: 48px; font-weight: bold; text-align: center; margin: 20px 0; }}
        .grade {{ text-align: center; font-size: 24px; margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .grade.EXCELLENT {{ background: #2ecc71; color: white; }}
        .grade.GOOD {{ background: #3498db; color: white; }}
        .grade.FAIR {{ background: #f39c12; color: white; }}
        .grade.POOR {{ background: #e74c3c; color: white; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #ecf0f1; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .recommendations {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .recommendations ul {{ margin: 10px 0; padding-left: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Comprehensive SID Validation Report</h1>

        <p><strong>Original SID:</strong> {os.path.basename(results['original_sid'])}</p>
        <p><strong>Converted SID:</strong> {os.path.basename(results['converted_sid'])}</p>
        <p><strong>Analysis Duration:</strong> {results['duration']} seconds</p>
        <p><strong>Timestamp:</strong> {results['timestamp']}</p>

        <div class="score">{results['overall_score']:.2f}%</div>
        <div class="grade {results['grade']}">{results['grade']}</div>

        <h2>1. Register-Level Validation (siddump)</h2>
"""

    if results['register_validation']:
        reg = results['register_validation']
        html += f"""
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Overall Accuracy</div>
                <div class="metric-value">{reg['overall_accuracy']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Frame Accuracy</div>
                <div class="metric-value">{reg['frame_accuracy']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Voice Accuracy</div>
                <div class="metric-value">{reg['voice_accuracy']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Register Accuracy</div>
                <div class="metric-value">{reg['register_accuracy']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Filter Accuracy</div>
                <div class="metric-value">{reg['filter_accuracy']:.2f}%</div>
            </div>
        </div>
"""
    else:
        html += "<p>X Register validation failed or unavailable</p>"

    html += "<h2>2. Audio-Level Validation (WAV)</h2>"

    if results['audio_validation']:
        aud = results['audio_validation']
        html += f"""
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Audio Accuracy</div>
                <div class="metric-value">{aud['audio_accuracy']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Byte Match</div>
                <div class="metric-value">{aud['byte_match']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">RMS Difference</div>
                <div class="metric-value">{aud['rms_difference']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Size Match</div>
                <div class="metric-value">{'Yes' if aud['size_match'] else 'No'}</div>
            </div>
        </div>
"""
    else:
        html += "<p>X Audio validation failed or unavailable</p>"

    html += "<h2>3. Structure-Level Validation (Music Structure)</h2>"

    if results['structure_validation']:
        struct = results['structure_validation']
        html += f"""
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Overall Similarity</div>
                <div class="metric-value">{struct['overall_similarity']:.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Instrument Similarity</div>
                <div class="metric-value">{struct['instrument_similarity']:.2f}%</div>
            </div>
        </div>

        <h3>Voice Activity Similarity</h3>
        <table>
            <tr>
                <th>Voice</th>
                <th>Similarity</th>
            </tr>
"""
        for voice_num in range(1, 4):
            sim = struct['voice_similarity'][voice_num]
            html += f"""
            <tr>
                <td>Voice {voice_num}</td>
                <td>{sim:.2f}%</td>
            </tr>
"""
        html += "</table>"
    else:
        html += "<p>X Structure validation failed or unavailable</p>"

    if results['recommendations']:
        html += """
        <h2>Recommendations</h2>
        <div class="recommendations">
            <ul>
"""
        for rec in results['recommendations']:
            html += f"                <li>{rec}</li>\n"

        html += """
            </ul>
        </div>
"""

    html += f"""
        <div class="footer">
            <p>Generated by Comprehensive SID Validation System</p>
            <p>SIDM2 v0.6.4 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

    with open(html_file, 'w') as f:
        f.write(html)

    print(f"HTML report saved to: {html_file}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive SID Validation - Uses ALL validation methods"
    )
    parser.add_argument("original", help="Original SID file")
    parser.add_argument("converted", help="Converted SID file (from SF2)")
    parser.add_argument("--output", default="comprehensive_validation_output",
                       help="Output directory for results")
    parser.add_argument("--duration", type=int, default=10,
                       help="Analysis duration in seconds (default: 10)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

    try:
        results = comprehensive_validate(
            args.original,
            args.converted,
            args.output,
            args.duration
        )

        # Return exit code based on grade
        if results['grade'] == 'EXCELLENT':
            return 0
        elif results['grade'] == 'GOOD':
            return 0
        elif results['grade'] == 'FAIR':
            return 1
        else:
            return 2

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
