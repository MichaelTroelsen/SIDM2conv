"""Metrics collection from pipeline outputs."""

import re
from pathlib import Path
from typing import Dict, Optional, Any


class MetricsCollector:
    """Collects metrics from pipeline output files."""

    def __init__(self, output_base: Path):
        """Initialize metrics collector.

        Args:
            output_base: Base directory for pipeline outputs
        """
        self.output_base = output_base

    def collect_file_metrics(self, filename: str) -> Dict[str, Any]:
        """Collect all metrics for a single file.

        Args:
            filename: Name of the SID file (without extension)

        Returns:
            Dict of collected metrics
        """
        # Determine file paths
        file_dir = self.output_base / filename / "New"

        metrics = {
            'filename': filename,
            'conversion_success': False,
            'conversion_method': None,
            'step1_conversion': False,
            'step2_packing': False,
            'step3_siddump': False,
            'step4_wav': False,
            'step5_hexdump': False,
            'step6_trace': False,
            'step7_info': False,
            'step8_disasm_python': False,
            'step9_disasm_sidwinder': False,
        }

        # Check file existence for each step
        sf2_file = file_dir / f"{filename}.sf2"
        exported_sid = file_dir / f"{filename}_exported.sid"
        dump_file = file_dir / f"{filename}_exported.dump"
        wav_file = file_dir / f"{filename}_exported.wav"
        hex_file = file_dir / f"{filename}_exported.hex"
        trace_file = file_dir / f"{filename}_exported.txt"
        info_file = file_dir / "info.txt"
        disasm_python = file_dir / f"{filename}_exported_disassembly.md"
        disasm_sidwinder = file_dir / f"{filename}_exported_sidwinder.asm"

        metrics['step1_conversion'] = sf2_file.exists()
        metrics['step2_packing'] = exported_sid.exists()
        metrics['step3_siddump'] = dump_file.exists()
        metrics['step4_wav'] = wav_file.exists()
        metrics['step5_hexdump'] = hex_file.exists()
        metrics['step6_trace'] = trace_file.exists()
        metrics['step7_info'] = info_file.exists()
        metrics['step8_disasm_python'] = disasm_python.exists()
        metrics['step9_disasm_sidwinder'] = disasm_sidwinder.exists()

        # Overall conversion success if all critical steps passed
        metrics['conversion_success'] = all([
            metrics['step1_conversion'],
            metrics['step2_packing'],
            metrics['step7_info']
        ])

        # Collect file sizes
        try:
            if sf2_file.exists():
                metrics['sf2_size'] = sf2_file.stat().st_size
            if exported_sid.exists():
                metrics['exported_size'] = exported_sid.stat().st_size
        except Exception:
            pass

        # Parse info.txt for additional metrics
        if info_file.exists():
            metrics.update(self._parse_info_file(info_file))

        # Count SIDwinder warnings
        if disasm_sidwinder.exists():
            metrics['sidwinder_warnings'] = self._count_sidwinder_warnings(disasm_sidwinder)

        return metrics

    def _parse_info_file(self, info_path: Path) -> Dict[str, Any]:
        """Parse info.txt file for metrics.

        Args:
            info_path: Path to info.txt

        Returns:
            Dict of extracted metrics
        """
        metrics = {}

        try:
            content = info_path.read_text(encoding='utf-8', errors='ignore')

            # Extract conversion method
            method_match = re.search(r'Conversion Method:\s*(\w+)', content)
            if method_match:
                metrics['conversion_method'] = method_match.group(1)

            # Extract data size
            size_match = re.search(r'Data Size:\s*([\d,]+)\s*bytes', content)
            if size_match:
                size_str = size_match.group(1).replace(',', '')
                metrics['original_size'] = int(size_str)

            # Look for accuracy information (if present)
            acc_match = re.search(r'Overall Accuracy:\s*([\d.]+)%', content)
            if acc_match:
                metrics['overall_accuracy'] = float(acc_match.group(1))

            frame_match = re.search(r'Frame Accuracy:\s*([\d.]+)%', content)
            if frame_match:
                metrics['frame_accuracy'] = float(frame_match.group(1))

            voice_match = re.search(r'Voice Accuracy:\s*([\d.]+)%', content)
            if voice_match:
                metrics['voice_accuracy'] = float(voice_match.group(1))

            register_match = re.search(r'Register Accuracy:\s*([\d.]+)%', content)
            if register_match:
                metrics['register_accuracy'] = float(register_match.group(1))

            filter_match = re.search(r'Filter Accuracy:\s*([\d.]+)%', content)
            if filter_match:
                metrics['filter_accuracy'] = float(filter_match.group(1))

        except Exception as e:
            print(f"Warning: Error parsing info.txt for {info_path.parent.parent.name}: {e}")

        return metrics

    def _count_sidwinder_warnings(self, asm_path: Path) -> int:
        """Count warnings in SIDwinder disassembly.

        Args:
            asm_path: Path to .asm file

        Returns:
            Number of warnings found
        """
        try:
            content = asm_path.read_text(encoding='utf-8', errors='ignore')
            # Look for common warning patterns
            warnings = 0
            warnings += content.count('WARNING')
            warnings += content.count('ERROR')
            warnings += content.count('kil')  # Illegal opcodes
            return warnings
        except Exception:
            return 0

    def collect_aggregate_metrics(self, all_results: list) -> Dict[str, float]:
        """Calculate aggregate metrics across all files.

        Args:
            all_results: List of file result dicts

        Returns:
            Dict of aggregate metrics
        """
        if not all_results:
            return {}

        total = len(all_results)
        passed = sum(1 for r in all_results if r.get('conversion_success'))

        # Calculate averages for accuracy metrics
        accuracies = [r.get('overall_accuracy') for r in all_results if r.get('overall_accuracy')]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0

        # Calculate file size efficiency
        sizes = [(r.get('exported_size'), r.get('original_size'))
                 for r in all_results
                 if r.get('exported_size') and r.get('original_size')]
        avg_efficiency = sum(exp / orig for exp, orig in sizes) / len(sizes) if sizes else 0

        # Count step successes
        step_counts = {}
        for step_num in range(1, 10):
            step_key = [k for k in all_results[0].keys() if k.startswith(f'step{step_num}_')][0] if any(k.startswith(f'step{step_num}_') for k in all_results[0].keys()) else None
            if step_key:
                step_counts[f'step{step_num}_success_rate'] = sum(1 for r in all_results if r.get(step_key)) / total

        return {
            'total_files': total,
            'pass_rate': passed / total,
            'avg_overall_accuracy': avg_accuracy,
            'avg_file_size_efficiency': avg_efficiency,
            **step_counts
        }
