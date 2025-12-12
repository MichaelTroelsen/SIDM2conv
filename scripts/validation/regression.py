"""Regression detection for validation system."""

from typing import Dict, List, Any, Optional, Tuple


class RegressionDetector:
    """Detects regressions between validation runs."""

    def __init__(self, threshold_accuracy: float = 5.0,
                 threshold_size: float = 20.0):
        """Initialize regression detector.

        Args:
            threshold_accuracy: Accuracy drop % to consider regression (default 5%)
            threshold_size: Size increase % to consider regression (default 20%)
        """
        self.threshold_accuracy = threshold_accuracy
        self.threshold_size = threshold_size

    def detect_regressions(self, baseline: List[Dict[str, Any]],
                          current: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect regressions between two validation runs.

        Args:
            baseline: List of file results from baseline run
            current: List of file results from current run

        Returns:
            Dict with regression details and summary
        """
        # Convert to dicts keyed by filename
        baseline_dict = {r['filename']: r for r in baseline}
        current_dict = {r['filename']: r for r in current}

        regressions = []
        improvements = []
        warnings = []

        # Check each file that appears in both runs
        common_files = set(baseline_dict.keys()) & set(current_dict.keys())

        for filename in sorted(common_files):
            base = baseline_dict[filename]
            curr = current_dict[filename]

            # Check for accuracy regression
            acc_regression = self._check_accuracy_regression(filename, base, curr)
            if acc_regression:
                if acc_regression['severity'] == 'regression':
                    regressions.append(acc_regression)
                elif acc_regression['severity'] == 'improvement':
                    improvements.append(acc_regression)
                elif acc_regression['severity'] == 'warning':
                    warnings.append(acc_regression)

            # Check for step failures
            step_regressions = self._check_step_regressions(filename, base, curr)
            regressions.extend(step_regressions)

            # Check for step improvements
            step_improvements = self._check_step_improvements(filename, base, curr)
            improvements.extend(step_improvements)

            # Check for file size regression
            size_regression = self._check_size_regression(filename, base, curr)
            if size_regression:
                if size_regression['severity'] == 'regression':
                    regressions.append(size_regression)
                elif size_regression['severity'] == 'warning':
                    warnings.append(size_regression)

            # Check for new warnings
            warning_regression = self._check_warning_regression(filename, base, curr)
            if warning_regression:
                warnings.append(warning_regression)

        # Check for new files and removed files
        new_files = set(current_dict.keys()) - set(baseline_dict.keys())
        removed_files = set(baseline_dict.keys()) - set(current_dict.keys())

        return {
            'regressions': regressions,
            'improvements': improvements,
            'warnings': warnings,
            'new_files': sorted(new_files),
            'removed_files': sorted(removed_files),
            'regression_count': len(regressions),
            'improvement_count': len(improvements),
            'warning_count': len(warnings),
            'summary': self._generate_summary(regressions, improvements, warnings)
        }

    def _check_accuracy_regression(self, filename: str,
                                   baseline: Dict[str, Any],
                                   current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for accuracy regression.

        Returns:
            Dict with regression details, or None if no regression
        """
        base_acc = baseline.get('overall_accuracy')
        curr_acc = current.get('overall_accuracy')

        if base_acc is None or curr_acc is None:
            return None

        diff = curr_acc - base_acc

        # Significant drop (regression)
        if diff < -self.threshold_accuracy:
            return {
                'type': 'accuracy_drop',
                'filename': filename,
                'severity': 'regression',
                'baseline_value': base_acc,
                'current_value': curr_acc,
                'diff': diff,
                'message': f"Accuracy dropped {abs(diff):.1f}% ({base_acc:.1f}% → {curr_acc:.1f}%)"
            }

        # Significant improvement
        elif diff > self.threshold_accuracy:
            return {
                'type': 'accuracy_improvement',
                'filename': filename,
                'severity': 'improvement',
                'baseline_value': base_acc,
                'current_value': curr_acc,
                'diff': diff,
                'message': f"Accuracy improved {diff:.1f}% ({base_acc:.1f}% → {curr_acc:.1f}%)"
            }

        # Small drop (warning)
        elif diff < 0:
            return {
                'type': 'accuracy_drop',
                'filename': filename,
                'severity': 'warning',
                'baseline_value': base_acc,
                'current_value': curr_acc,
                'diff': diff,
                'message': f"Accuracy decreased {abs(diff):.1f}% ({base_acc:.1f}% → {curr_acc:.1f}%)"
            }

        return None

    def _check_step_regressions(self, filename: str,
                                baseline: Dict[str, Any],
                                current: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for pipeline step failures.

        Returns:
            List of step regression dicts
        """
        regressions = []

        # Define step names
        steps = [
            ('step1_conversion', 'SF2 Conversion'),
            ('step2_packing', 'SID Packing'),
            ('step3_siddump', 'Siddump'),
            ('step4_wav', 'WAV Generation'),
            ('step5_hexdump', 'Hexdump'),
            ('step6_trace', 'Trace'),
            ('step7_info', 'Info Generation'),
            ('step8_disasm_python', 'Python Disassembly'),
            ('step9_disasm_sidwinder', 'SIDwinder Disassembly'),
        ]

        for step_key, step_name in steps:
            base_pass = baseline.get(step_key, False)
            curr_pass = current.get(step_key, False)

            # Step that was passing now fails
            if base_pass and not curr_pass:
                regressions.append({
                    'type': 'step_failure',
                    'filename': filename,
                    'severity': 'regression',
                    'step': step_name,
                    'step_key': step_key,
                    'baseline_value': True,
                    'current_value': False,
                    'message': f"Step '{step_name}' now fails (was passing)"
                })

        return regressions

    def _check_step_improvements(self, filename: str,
                                 baseline: Dict[str, Any],
                                 current: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for pipeline step improvements.

        Returns:
            List of step improvement dicts
        """
        improvements = []

        # Define step names
        steps = [
            ('step1_conversion', 'SF2 Conversion'),
            ('step2_packing', 'SID Packing'),
            ('step3_siddump', 'Siddump'),
            ('step4_wav', 'WAV Generation'),
            ('step5_hexdump', 'Hexdump'),
            ('step6_trace', 'Trace'),
            ('step7_info', 'Info Generation'),
            ('step8_disasm_python', 'Python Disassembly'),
            ('step9_disasm_sidwinder', 'SIDwinder Disassembly'),
        ]

        for step_key, step_name in steps:
            base_pass = baseline.get(step_key, False)
            curr_pass = current.get(step_key, False)

            # Step that was failing now passes
            if not base_pass and curr_pass:
                improvements.append({
                    'type': 'step_fixed',
                    'filename': filename,
                    'severity': 'improvement',
                    'step': step_name,
                    'step_key': step_key,
                    'baseline_value': False,
                    'current_value': True,
                    'message': f"Step '{step_name}' now passes (was failing)"
                })

        return improvements

    def _check_size_regression(self, filename: str,
                               baseline: Dict[str, Any],
                               current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for file size regression.

        Returns:
            Dict with size regression details, or None
        """
        base_size = baseline.get('exported_size')
        curr_size = current.get('exported_size')

        if base_size is None or curr_size is None:
            return None

        if base_size == 0:
            return None

        percent_increase = ((curr_size - base_size) / base_size) * 100

        # Significant increase (regression)
        if percent_increase > self.threshold_size:
            return {
                'type': 'size_increase',
                'filename': filename,
                'severity': 'regression',
                'baseline_value': base_size,
                'current_value': curr_size,
                'diff': curr_size - base_size,
                'percent': percent_increase,
                'message': f"File size increased {percent_increase:.1f}% ({base_size} → {curr_size} bytes)"
            }

        # Moderate increase (warning)
        elif percent_increase > 10.0:
            return {
                'type': 'size_increase',
                'filename': filename,
                'severity': 'warning',
                'baseline_value': base_size,
                'current_value': curr_size,
                'diff': curr_size - base_size,
                'percent': percent_increase,
                'message': f"File size increased {percent_increase:.1f}% ({base_size} → {curr_size} bytes)"
            }

        return None

    def _check_warning_regression(self, filename: str,
                                  baseline: Dict[str, Any],
                                  current: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check for new SIDwinder warnings.

        Returns:
            Dict with warning regression details, or None
        """
        base_warnings = baseline.get('sidwinder_warnings', 0)
        curr_warnings = current.get('sidwinder_warnings', 0)

        if curr_warnings > base_warnings:
            diff = curr_warnings - base_warnings
            return {
                'type': 'new_warnings',
                'filename': filename,
                'severity': 'warning',
                'baseline_value': base_warnings,
                'current_value': curr_warnings,
                'diff': diff,
                'message': f"{diff} new warning(s) in SIDwinder disassembly ({base_warnings} → {curr_warnings})"
            }

        return None

    def _generate_summary(self, regressions: List[Dict[str, Any]],
                         improvements: List[Dict[str, Any]],
                         warnings: List[Dict[str, Any]]) -> str:
        """Generate human-readable summary.

        Args:
            regressions: List of regression dicts
            improvements: List of improvement dicts
            warnings: List of warning dicts

        Returns:
            Summary string
        """
        lines = []

        if regressions:
            lines.append(f"❌ {len(regressions)} REGRESSION(S) DETECTED")
            for reg in regressions[:5]:  # Show first 5
                lines.append(f"  - {reg['filename']}: {reg['message']}")
            if len(regressions) > 5:
                lines.append(f"  ... and {len(regressions) - 5} more")

        if warnings:
            lines.append(f"⚠️  {len(warnings)} WARNING(S)")
            for warn in warnings[:3]:  # Show first 3
                lines.append(f"  - {warn['filename']}: {warn['message']}")
            if len(warnings) > 3:
                lines.append(f"  ... and {len(warnings) - 3} more")

        if improvements:
            lines.append(f"✅ {len(improvements)} IMPROVEMENT(S)")
            for imp in improvements[:3]:  # Show first 3
                lines.append(f"  - {imp['filename']}: {imp['message']}")
            if len(improvements) > 3:
                lines.append(f"  ... and {len(improvements) - 3} more")

        if not regressions and not warnings and not improvements:
            lines.append("✅ No significant changes detected")

        return "\n".join(lines)

    def format_regression_report(self, results: Dict[str, Any]) -> str:
        """Format regression detection results as a text report.

        Args:
            results: Results from detect_regressions()

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 70)
        lines.append("REGRESSION DETECTION REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        lines.append(results['summary'])
        lines.append("")

        # Detailed regressions
        if results['regressions']:
            lines.append("-" * 70)
            lines.append("REGRESSIONS (CRITICAL)")
            lines.append("-" * 70)
            for reg in results['regressions']:
                lines.append(f"\n{reg['filename']}:")
                lines.append(f"  Type: {reg['type']}")
                lines.append(f"  {reg['message']}")

        # Detailed warnings
        if results['warnings']:
            lines.append("")
            lines.append("-" * 70)
            lines.append("WARNINGS")
            lines.append("-" * 70)
            for warn in results['warnings']:
                lines.append(f"\n{warn['filename']}:")
                lines.append(f"  Type: {warn['type']}")
                lines.append(f"  {warn['message']}")

        # Improvements
        if results['improvements']:
            lines.append("")
            lines.append("-" * 70)
            lines.append("IMPROVEMENTS")
            lines.append("-" * 70)
            for imp in results['improvements']:
                lines.append(f"\n{imp['filename']}:")
                lines.append(f"  Type: {imp['type']}")
                lines.append(f"  {imp['message']}")

        # New/removed files
        if results['new_files']:
            lines.append("")
            lines.append(f"NEW FILES: {', '.join(results['new_files'])}")

        if results['removed_files']:
            lines.append(f"REMOVED FILES: {', '.join(results['removed_files'])}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)
