"""
Accuracy Validation Integration for Pipeline Phase 5

Compares original SID with exported SID for accuracy measurement.
Uses frame-by-frame register comparison from siddump outputs.

Usage:
    from sidm2.accuracy_integration import AccuracyIntegration

    result = AccuracyIntegration.validate_accuracy(
        original_sid=Path("original.sid"),
        exported_sid=Path("exported.sid"),
        output_dir=Path("analysis"),
        duration=30
    )
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from sidm2.accuracy import calculate_accuracy_from_sids, SIDRegisterCapture

logger = logging.getLogger(__name__)


class AccuracyIntegration:
    """Integration wrapper for SID accuracy validation"""

    @staticmethod
    def validate_accuracy(
        original_sid: Path,
        exported_sid: Path,
        output_dir: Path,
        duration: int = 30,
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Validate conversion accuracy by comparing SID register writes.

        Args:
            original_sid: Path to original SID file
            exported_sid: Path to exported/converted SID file
            output_dir: Directory for output files
            duration: Comparison duration in seconds
            verbose: Verbosity level

        Returns:
            Dictionary with accuracy results or None on failure
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate accuracy report filename
            report_file = output_dir / f"{original_sid.stem}_accuracy.txt"

            if verbose > 0:
                print(f"  Validating accuracy: {report_file.name}")
                print(f"    Original: {original_sid.name}")
                print(f"    Exported: {exported_sid.name}")
                print(f"    Duration: {duration}s")

            # Calculate accuracy using frame-by-frame comparison
            try:
                accuracy_result = calculate_accuracy_from_sids(
                    str(original_sid),
                    str(exported_sid),
                    duration=duration
                )

                if not accuracy_result:
                    logger.warning(f"Accuracy calculation failed - no result returned")
                    return None
            except Exception as e:
                logger.error(f"Accuracy calculation error: {e}")
                return None

            # Generate accuracy report
            report_content = _generate_accuracy_report(
                original_sid,
                exported_sid,
                accuracy_result,
                duration
            )

            # Write report
            report_file.write_text(report_content, encoding='utf-8')

            return {
                'success': True,
                'report_file': report_file,
                'overall_accuracy': accuracy_result.get('overall_accuracy', 0.0),
                'frame_accuracy': accuracy_result.get('frame_accuracy', 0.0),
                'register_accuracy': accuracy_result.get('register_accuracy', {}),
                'total_frames': accuracy_result.get('total_frames', 0),
                'matching_frames': accuracy_result.get('matching_frames', 0),
                'file_size': report_file.stat().st_size
            }

        except Exception as e:
            logger.error(f"Accuracy validation failed: {e}")
            return None


def _generate_accuracy_report(
    original_sid: Path,
    exported_sid: Path,
    accuracy_result: Dict,
    duration: int
) -> str:
    """Generate formatted accuracy report"""
    from datetime import datetime

    lines = []
    lines.append("=" * 70)
    lines.append("SID CONVERSION ACCURACY REPORT")
    lines.append("=" * 70)
    lines.append("")

    lines.append("FILE INFORMATION")
    lines.append("-" * 70)
    lines.append(f"Original:  {original_sid.name}")
    lines.append(f"Exported:  {exported_sid.name}")
    lines.append(f"Duration:  {duration}s")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("OVERALL ACCURACY")
    lines.append("-" * 70)
    overall = accuracy_result.get('overall_accuracy', 0.0)
    frame_acc = accuracy_result.get('frame_accuracy', 0.0)
    total_frames = accuracy_result.get('total_frames', 0)
    matching_frames = accuracy_result.get('matching_frames', 0)

    lines.append(f"Overall Accuracy:    {overall:.2f}%")
    lines.append(f"Frame Accuracy:      {frame_acc:.2f}%")
    lines.append(f"Total Frames:        {total_frames}")
    lines.append(f"Matching Frames:     {matching_frames}")
    lines.append(f"Mismatched Frames:   {total_frames - matching_frames}")
    lines.append("")

    lines.append("REGISTER-LEVEL ACCURACY")
    lines.append("-" * 70)
    register_acc = accuracy_result.get('register_accuracy', {})
    for reg_name, acc_value in sorted(register_acc.items()):
        lines.append(f"  {reg_name:<30} {acc_value:.2f}%")
    lines.append("")

    lines.append("INTERPRETATION")
    lines.append("-" * 70)
    if overall >= 99.0:
        lines.append("  EXCELLENT: Conversion is highly accurate")
    elif overall >= 90.0:
        lines.append("  GOOD: Conversion quality is acceptable")
    elif overall >= 70.0:
        lines.append("  FAIR: Noticeable differences may occur")
    else:
        lines.append("  POOR: Significant conversion issues detected")
    lines.append("")

    lines.append("=" * 70)
    lines.append("End of report")
    lines.append("=" * 70)

    return "\n".join(lines)


def validate_accuracy(
    original_sid: Path,
    exported_sid: Path,
    output_dir: Path,
    duration: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for accuracy validation.

    Args:
        original_sid: Path to original SID file
        exported_sid: Path to exported SID file
        output_dir: Directory for output files
        duration: Comparison duration in seconds

    Returns:
        Result dictionary or None on failure
    """
    return AccuracyIntegration.validate_accuracy(
        original_sid,
        exported_sid,
        output_dir,
        duration
    )
