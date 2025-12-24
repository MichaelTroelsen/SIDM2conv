"""
Report Generator for SID Conversion Pipeline - Phase 4

Consolidates all analysis outputs into a unified comprehensive report.
Integrated into the conversion pipeline as Step 19.

Usage:
    from sidm2.report_generator import ReportGenerator

    generator = ReportGenerator(
        sid_file=Path("input.sid"),
        analysis_dir=Path("output/analysis")
    )
    report = generator.generate()
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates consolidated analysis reports"""

    def __init__(self, sid_file: Path, analysis_dir: Path):
        """
        Initialize report generator.

        Args:
            sid_file: Path to original SID file
            analysis_dir: Directory containing analysis outputs
        """
        self.sid_file = sid_file
        self.analysis_dir = analysis_dir
        self.available_reports = {}

    def _scan_analysis_files(self) -> Dict[str, Path]:
        """
        Scan analysis directory for available reports.

        Returns:
            Dictionary mapping report type to file path
        """
        if not self.analysis_dir.exists():
            return {}

        reports = {}
        stem = self.sid_file.stem

        # Check for each analysis type
        report_types = {
            'trace': f'{stem}_trace.txt',
            'init_disasm': f'{stem}_init.asm',
            'play_disasm': f'{stem}_play.asm',
            'memmap': f'{stem}_memmap.txt',
            'patterns': f'{stem}_patterns.txt',
            'callgraph': f'{stem}_callgraph.txt',
            'audio': f'{stem}.wav',
        }

        for report_type, filename in report_types.items():
            file_path = self.analysis_dir / filename
            if file_path.exists():
                reports[report_type] = file_path

        return reports

    def _read_file_summary(self, file_path: Path, max_lines: int = 20) -> str:
        """
        Read summary of a file (first N lines).

        Args:
            file_path: Path to file
            max_lines: Maximum lines to read

        Returns:
            Summary text
        """
        try:
            if file_path.suffix == '.wav':
                # For WAV files, just show metadata
                size = file_path.stat().st_size
                return f"Audio file: {size:,} bytes"

            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip())

                if i >= max_lines:
                    lines.append(f"... ({i} more lines)")

                return '\n'.join(lines)

        except Exception as e:
            return f"Error reading file: {e}"

    def _extract_statistics(self) -> Dict[str, Any]:
        """
        Extract key statistics from available reports.

        Returns:
            Dictionary of statistics
        """
        stats = {}

        # Memory map statistics
        if 'memmap' in self.available_reports:
            try:
                with open(self.available_reports['memmap'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract total size
                    for line in content.split('\n'):
                        if 'Total size:' in line:
                            stats['total_size'] = line.split(':')[1].strip()
                        elif 'Code regions:' in line:
                            stats['code_size'] = line.split(':')[1].strip()
                        elif 'Data regions:' in line:
                            stats['data_size'] = line.split(':')[1].strip()
            except:
                pass

        # Pattern statistics
        if 'patterns' in self.available_reports:
            try:
                with open(self.available_reports['patterns'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if 'Total patterns:' in line:
                            stats['total_patterns'] = line.split(':')[1].strip()
                        elif 'Potential savings:' in line:
                            stats['potential_savings'] = line.split(':')[1].strip()
            except:
                pass

        # Call graph statistics
        if 'callgraph' in self.available_reports:
            try:
                with open(self.available_reports['callgraph'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if 'Total subroutines:' in line:
                            stats['total_subroutines'] = line.split(':')[1].strip()
                        elif 'Max call depth:' in line:
                            stats['max_call_depth'] = line.split(':')[1].strip()
            except:
                pass

        return stats

    def generate(self, output_file: Path, verbose: int = 0) -> Dict[str, Any]:
        """
        Generate consolidated report.

        Args:
            output_file: Path to output report file
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with generation results
        """
        try:
            # Scan for available reports
            self.available_reports = self._scan_analysis_files()

            if not self.available_reports:
                if verbose > 0:
                    logger.warning("No analysis files found to consolidate")
                return {
                    'success': False,
                    'error': 'No analysis files found'
                }

            # Extract statistics
            stats = self._extract_statistics()

            # Generate consolidated report
            with open(output_file, 'w', encoding='utf-8') as f:
                # Header
                f.write("=" * 70 + "\n")
                f.write("SID CONVERSION ANALYSIS REPORT\n")
                f.write("=" * 70 + "\n\n")

                # Generation info
                f.write("REPORT INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"Generated:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"SID file:    {self.sid_file.name}\n")
                f.write(f"Analysis:    {len(self.available_reports)} tools\n")
                f.write("\n")

                # Executive summary
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 70 + "\n")

                if stats:
                    if 'total_size' in stats:
                        f.write(f"File size:         {stats['total_size']}\n")
                    if 'code_size' in stats:
                        f.write(f"Code:              {stats['code_size']}\n")
                    if 'data_size' in stats:
                        f.write(f"Data:              {stats['data_size']}\n")
                    if 'total_patterns' in stats:
                        f.write(f"Patterns found:    {stats['total_patterns']}\n")
                    if 'potential_savings' in stats:
                        f.write(f"Potential savings: {stats['potential_savings']}\n")
                    if 'total_subroutines' in stats:
                        f.write(f"Subroutines:       {stats['total_subroutines']}\n")
                    if 'max_call_depth' in stats:
                        f.write(f"Max call depth:    {stats['max_call_depth']}\n")
                else:
                    f.write("(No statistics available)\n")

                f.write("\n")

                # Available analyses
                f.write("AVAILABLE ANALYSES\n")
                f.write("-" * 70 + "\n")

                analysis_names = {
                    'trace': 'SIDwinder Trace',
                    'init_disasm': '6502 Disassembly (Init)',
                    'play_disasm': '6502 Disassembly (Play)',
                    'memmap': 'Memory Map',
                    'patterns': 'Pattern Recognition',
                    'callgraph': 'Call Graph',
                    'audio': 'Audio Export'
                }

                for report_type, file_path in sorted(self.available_reports.items()):
                    name = analysis_names.get(report_type, report_type)
                    size = file_path.stat().st_size
                    f.write(f"  {name:<30} {file_path.name:<30} ({size:,} bytes)\n")

                f.write("\n")

                # File index
                f.write("FILE INDEX\n")
                f.write("-" * 70 + "\n")
                f.write("All analysis files are located in the analysis/ subdirectory:\n\n")

                for report_type, file_path in sorted(self.available_reports.items()):
                    name = analysis_names.get(report_type, report_type)
                    f.write(f"  {name}:\n")
                    f.write(f"    File: {file_path.name}\n")
                    f.write(f"    Path: {file_path}\n")
                    f.write(f"    Size: {file_path.stat().st_size:,} bytes\n")
                    f.write("\n")

                # Report previews
                f.write("REPORT PREVIEWS\n")
                f.write("-" * 70 + "\n")
                f.write("First 20 lines of each text report:\n\n")

                for report_type, file_path in sorted(self.available_reports.items()):
                    if file_path.suffix not in ['.txt', '.asm']:
                        continue

                    name = analysis_names.get(report_type, report_type)
                    f.write("-" * 70 + "\n")
                    f.write(f"{name} ({file_path.name})\n")
                    f.write("-" * 70 + "\n")

                    summary = self._read_file_summary(file_path, max_lines=20)
                    f.write(summary)
                    f.write("\n\n")

                # Footer
                f.write("=" * 70 + "\n")
                f.write("End of consolidated report\n")
                f.write("=" * 70 + "\n")
                f.write("\n")
                f.write("For detailed analysis, see individual files in the analysis/ directory.\n")

            result = {
                'success': True,
                'output_file': output_file,
                'report_count': len(self.available_reports),
                'available_reports': list(self.available_reports.keys()),
                'statistics': stats
            }

            if verbose > 0:
                print(f"  Consolidated report generated")
                print(f"    Output:   {output_file.name}")
                print(f"    Reports:  {len(self.available_reports)}")
                print(f"    Types:    {', '.join(self.available_reports.keys())}")

            return result

        except Exception as e:
            if verbose > 0:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(f"Report generation failed: {error_msg}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience function
def generate_consolidated_report(
    sid_file: Path,
    analysis_dir: Path,
    output_file: Path,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for generating consolidated reports.

    Args:
        sid_file: Path to original SID file
        analysis_dir: Directory containing analysis outputs
        output_file: Path to output report file
        verbose: Verbosity level

    Returns:
        Generation result dictionary or None on error
    """
    generator = ReportGenerator(sid_file, analysis_dir)
    return generator.generate(output_file, verbose=verbose)
