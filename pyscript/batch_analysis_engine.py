#!/usr/bin/env python3
"""
Batch Analysis Engine - Compare multiple SID file pairs

Orchestrates batch comparison of SID file pairs, generating:
- Trace comparison metrics
- Individual heatmaps
- Individual comparison HTMLs
- Aggregate summary reports (HTML, CSV, JSON)

Version: 1.0.0
Date: 2026-01-01
"""

import sys
import os
import time
import csv
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.sidtracer import SIDTracer
from pyscript.trace_comparator import TraceComparator
from pyscript.accuracy_heatmap_generator import HeatmapGenerator
from pyscript.accuracy_heatmap_exporter import AccuracyHeatmapExporter
from pyscript.trace_comparison_html_exporter import TraceComparisonHTMLExporter


@dataclass
class PairAnalysisResult:
    """Complete analysis results for one SID pair"""

    # File identification
    filename_a: str
    filename_b: str
    path_a: str
    path_b: str

    # Core trace comparison metrics
    frame_match_percent: float = 0.0
    register_accuracy_overall: float = 0.0
    total_diff_count: int = 0

    # Per-voice accuracy (Voice 1, 2, 3)
    voice1_freq: float = 0.0
    voice1_wave: float = 0.0
    voice1_adsr: float = 0.0
    voice1_pulse: float = 0.0

    voice2_freq: float = 0.0
    voice2_wave: float = 0.0
    voice2_adsr: float = 0.0
    voice2_pulse: float = 0.0

    voice3_freq: float = 0.0
    voice3_wave: float = 0.0
    voice3_adsr: float = 0.0
    voice3_pulse: float = 0.0

    # File info
    frames_traced: int = 0
    file_size_a: int = 0
    file_size_b: int = 0

    # Analysis artifacts (relative paths)
    heatmap_path: Optional[str] = None
    comparison_path: Optional[str] = None

    # Status and performance
    status: str = "pending"  # "success", "failed", "partial"
    error_message: Optional[str] = None
    duration: float = 0.0  # seconds


@dataclass
class BatchAnalysisConfig:
    """Configuration for batch analysis run"""

    dir_a: Path
    dir_b: Path
    output_dir: Path

    frames: int = 300
    generate_heatmaps: bool = True
    generate_comparisons: bool = True
    export_csv: bool = True
    export_json: bool = True
    export_html: bool = True

    verbose: int = 0


@dataclass
class BatchAnalysisSummary:
    """Aggregate summary of batch analysis"""

    # Counts
    total_pairs: int = 0
    successful: int = 0
    failed: int = 0
    partial: int = 0  # Some analyses succeeded, others failed

    # Accuracy statistics
    avg_frame_match: float = 0.0
    avg_register_accuracy: float = 0.0

    # Best/worst matches
    best_match_filename: Optional[str] = None
    best_match_accuracy: float = 0.0
    worst_match_filename: Optional[str] = None
    worst_match_accuracy: float = 0.0

    # Voice accuracy averages
    avg_voice1_accuracy: float = 0.0
    avg_voice2_accuracy: float = 0.0
    avg_voice3_accuracy: float = 0.0

    # Performance
    total_duration: float = 0.0
    avg_duration_per_pair: float = 0.0

    # Output paths (absolute)
    html_report_path: Optional[str] = None
    csv_path: Optional[str] = None
    json_path: Optional[str] = None


class BatchAnalysisEngine:
    """Batch analysis orchestrator"""

    def __init__(self, config: BatchAnalysisConfig):
        """
        Initialize batch analysis engine.

        Args:
            config: BatchAnalysisConfig with all settings
        """
        self.config = config
        self.results: List[PairAnalysisResult] = []
        self.start_time: float = 0.0

    def find_pairs(self) -> List[Tuple[Path, Path]]:
        """
        Auto-pair files from two directories by matching basenames.

        Handles common suffixes:
        - _exported
        - _laxity
        - _d11
        - _np20
        - .sf2

        Matching examples:
        - song.sid ↔ song_exported.sid
        - song.sid ↔ song_laxity_exported.sid
        - song.sid ↔ song.sf2_exported.sid

        Returns:
            List of (path_a, path_b) tuples
        """
        if not self.config.dir_a.exists():
            raise ValueError(f"Directory A does not exist: {self.config.dir_a}")

        if not self.config.dir_b.exists():
            raise ValueError(f"Directory B does not exist: {self.config.dir_b}")

        # Get all .sid files from both directories
        files_a = {f for f in self.config.dir_a.iterdir() if f.suffix.lower() == '.sid'}
        files_b = {f for f in self.config.dir_b.iterdir() if f.suffix.lower() == '.sid'}

        # Build basename map for directory B (with suffix removal)
        basename_map_b = {}
        for file_b in files_b:
            basename = self._normalize_basename(file_b.stem)
            basename_map_b[basename] = file_b

        # Match files from directory A
        pairs = []
        for file_a in files_a:
            basename_a = self._normalize_basename(file_a.stem)

            # Try to find matching file in directory B
            if basename_a in basename_map_b:
                file_b = basename_map_b[basename_a]
                pairs.append((file_a, file_b))

        return sorted(pairs, key=lambda p: p[0].name)

    def _normalize_basename(self, stem: str) -> str:
        """
        Normalize filename stem by removing common suffixes.

        Args:
            stem: Filename without extension

        Returns:
            Normalized basename for matching
        """
        # Remove common suffixes in order (longest first)
        suffixes = [
            '_laxity_exported',
            '_np20_exported',
            '_d11_exported',
            '.sf2_exported',
            '_exported',
            '_laxity',
            '_np20',
            '_d11',
            '.sf2',
        ]

        normalized = stem.lower()
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break  # Only remove one suffix

        return normalized

    def analyze_pair(self, path_a: Path, path_b: Path) -> PairAnalysisResult:
        """
        Analyze one SID pair.

        Steps:
        1. Trace both files using SIDTracer
        2. Compare using TraceComparator
        3. If config.generate_heatmaps: Generate heatmap HTML
        4. If config.generate_comparisons: Generate comparison HTML
        5. Return PairAnalysisResult

        Args:
            path_a: Path to first SID file
            path_b: Path to second SID file

        Returns:
            PairAnalysisResult with all metrics and artifact paths
        """
        pair_start_time = time.time()

        result = PairAnalysisResult(
            filename_a=path_a.name,
            filename_b=path_b.name,
            path_a=str(path_a),
            path_b=str(path_b),
            file_size_a=path_a.stat().st_size,
            file_size_b=path_b.stat().st_size
        )

        try:
            # Step 1: Trace both files
            if self.config.verbose >= 1:
                print(f"  Tracing {path_a.name}...")

            tracer_a = SIDTracer(path_a, verbose=0)
            trace_a = tracer_a.trace(frames=self.config.frames)

            if self.config.verbose >= 1:
                print(f"  Tracing {path_b.name}...")

            tracer_b = SIDTracer(path_b, verbose=0)
            trace_b = tracer_b.trace(frames=self.config.frames)

            result.frames_traced = min(trace_a.frames, trace_b.frames)

            # Step 2: Compare traces
            if self.config.verbose >= 1:
                print(f"  Comparing traces...")

            comparator = TraceComparator(trace_a, trace_b)
            comparison = comparator.compare()

            # Extract core metrics
            result.frame_match_percent = comparison.frame_match_percent
            result.register_accuracy_overall = comparison.register_accuracy_overall
            result.total_diff_count = comparison.total_diff_count

            # Extract voice accuracies
            if 1 in comparison.voice_accuracy:
                v1 = comparison.voice_accuracy[1]
                result.voice1_freq = v1.get('frequency', 0.0)
                result.voice1_wave = v1.get('waveform', 0.0)
                result.voice1_adsr = v1.get('adsr', 0.0)
                result.voice1_pulse = v1.get('pulse', 0.0)

            if 2 in comparison.voice_accuracy:
                v2 = comparison.voice_accuracy[2]
                result.voice2_freq = v2.get('frequency', 0.0)
                result.voice2_wave = v2.get('waveform', 0.0)
                result.voice2_adsr = v2.get('adsr', 0.0)
                result.voice2_pulse = v2.get('pulse', 0.0)

            if 3 in comparison.voice_accuracy:
                v3 = comparison.voice_accuracy[3]
                result.voice3_freq = v3.get('frequency', 0.0)
                result.voice3_wave = v3.get('waveform', 0.0)
                result.voice3_adsr = v3.get('adsr', 0.0)
                result.voice3_pulse = v3.get('pulse', 0.0)

            # Step 3: Generate heatmap (if requested)
            if self.config.generate_heatmaps:
                if self.config.verbose >= 1:
                    print(f"  Generating heatmap...")

                try:
                    heatmap_dir = self.config.output_dir / "heatmaps"
                    heatmap_dir.mkdir(parents=True, exist_ok=True)

                    heatmap_filename = f"{path_a.stem}_heatmap.html"
                    heatmap_path = heatmap_dir / heatmap_filename

                    generator = HeatmapGenerator(
                        trace_a, trace_b, comparison,
                        filename_a=path_a.name,
                        filename_b=path_b.name
                    )
                    heatmap_data = generator.generate()

                    exporter = AccuracyHeatmapExporter(heatmap_data)
                    if exporter.export(str(heatmap_path)):
                        result.heatmap_path = f"heatmaps/{heatmap_filename}"
                except Exception as e:
                    if self.config.verbose >= 1:
                        print(f"    [WARNING] Heatmap generation failed: {e}")
                    result.status = "partial"

            # Step 4: Generate comparison HTML (if requested)
            if self.config.generate_comparisons:
                if self.config.verbose >= 1:
                    print(f"  Generating comparison HTML...")

                try:
                    comparison_dir = self.config.output_dir / "comparisons"
                    comparison_dir.mkdir(parents=True, exist_ok=True)

                    comparison_filename = f"{path_a.stem}_comparison.html"
                    comparison_path = comparison_dir / comparison_filename

                    html_exporter = TraceComparisonHTMLExporter(
                        trace_a, trace_b, comparison,
                        filename_a=path_a.name,
                        filename_b=path_b.name
                    )

                    if html_exporter.export(str(comparison_path)):
                        result.comparison_path = f"comparisons/{comparison_filename}"
                except Exception as e:
                    if self.config.verbose >= 1:
                        print(f"    [WARNING] Comparison HTML generation failed: {e}")
                    result.status = "partial"

            # Success (unless already marked as partial)
            if result.status != "partial":
                result.status = "success"

        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            if self.config.verbose >= 0:
                print(f"  [ERROR] Analysis failed: {e}")

        result.duration = time.time() - pair_start_time
        return result

    def run(self) -> BatchAnalysisSummary:
        """
        Execute batch analysis.

        Process:
        1. Find pairs
        2. Create output directory structure
        3. For each pair: analyze_pair()
        4. Generate summary statistics
        5. Export results (CSV, JSON, HTML if requested)
        6. Return BatchAnalysisSummary

        Returns:
            BatchAnalysisSummary with aggregate metrics and output paths
        """
        self.start_time = time.time()

        # Step 1: Find pairs
        print(f"\nFinding SID pairs...")
        print(f"  Directory A: {self.config.dir_a}")
        print(f"  Directory B: {self.config.dir_b}")

        pairs = self.find_pairs()

        if not pairs:
            print(f"\n[ERROR] No matching pairs found!")
            print(f"  Ensure files in both directories have matching basenames.")
            return BatchAnalysisSummary()

        print(f"  Found {len(pairs)} pairs\n")

        # Step 2: Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Analyze each pair
        print(f"Analyzing pairs...")
        for i, (path_a, path_b) in enumerate(pairs, 1):
            print(f"\n[{i}/{len(pairs)}] {path_a.name} vs {path_b.name}")

            result = self.analyze_pair(path_a, path_b)
            self.results.append(result)

            # Print quick summary
            if result.status == "success":
                print(f"  [OK] {result.frame_match_percent:.1f}% accuracy, {result.duration:.1f}s")
            elif result.status == "partial":
                print(f"  [PARTIAL] {result.frame_match_percent:.1f}% accuracy, {result.duration:.1f}s (some outputs failed)")
            else:
                print(f"  [FAILED] {result.error_message}")

        # Step 4: Generate summary
        summary = self._generate_summary()

        # Step 5: Export results
        if self.config.export_csv:
            csv_path = self.config.output_dir / "batch_results.csv"
            self.export_csv(csv_path)
            summary.csv_path = str(csv_path.absolute())

        if self.config.export_json:
            json_path = self.config.output_dir / "batch_results.json"
            self.export_json(json_path, summary)
            summary.json_path = str(json_path.absolute())

        return summary

    def _generate_summary(self) -> BatchAnalysisSummary:
        """
        Generate aggregate summary from results.

        Returns:
            BatchAnalysisSummary with all aggregate metrics
        """
        summary = BatchAnalysisSummary()

        if not self.results:
            return summary

        # Counts
        summary.total_pairs = len(self.results)
        summary.successful = sum(1 for r in self.results if r.status == "success")
        summary.failed = sum(1 for r in self.results if r.status == "failed")
        summary.partial = sum(1 for r in self.results if r.status == "partial")

        # Filter successful results for accuracy calculations
        successful_results = [r for r in self.results if r.status in ("success", "partial")]

        if successful_results:
            # Average accuracies
            frame_matches = [r.frame_match_percent for r in successful_results]
            register_accuracies = [r.register_accuracy_overall for r in successful_results]

            summary.avg_frame_match = sum(frame_matches) / len(frame_matches)
            summary.avg_register_accuracy = sum(register_accuracies) / len(register_accuracies)

            # Best/worst matches (by frame match percent)
            best = max(successful_results, key=lambda r: r.frame_match_percent)
            worst = min(successful_results, key=lambda r: r.frame_match_percent)

            summary.best_match_filename = best.filename_a
            summary.best_match_accuracy = best.frame_match_percent
            summary.worst_match_filename = worst.filename_a
            summary.worst_match_accuracy = worst.frame_match_percent

            # Voice accuracy averages
            voice1_accs = [(r.voice1_freq + r.voice1_wave + r.voice1_adsr + r.voice1_pulse) / 4
                          for r in successful_results]
            voice2_accs = [(r.voice2_freq + r.voice2_wave + r.voice2_adsr + r.voice2_pulse) / 4
                          for r in successful_results]
            voice3_accs = [(r.voice3_freq + r.voice3_wave + r.voice3_adsr + r.voice3_pulse) / 4
                          for r in successful_results]

            summary.avg_voice1_accuracy = sum(voice1_accs) / len(voice1_accs) if voice1_accs else 0.0
            summary.avg_voice2_accuracy = sum(voice2_accs) / len(voice2_accs) if voice2_accs else 0.0
            summary.avg_voice3_accuracy = sum(voice3_accs) / len(voice3_accs) if voice3_accs else 0.0

        # Performance
        summary.total_duration = time.time() - self.start_time
        summary.avg_duration_per_pair = summary.total_duration / summary.total_pairs if summary.total_pairs > 0 else 0.0

        return summary

    def export_csv(self, output_path: Path) -> bool:
        """
        Export results to CSV file.

        Args:
            output_path: Path to CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'filename_a', 'filename_b', 'frame_match_percent', 'register_accuracy',
                    'voice1_freq', 'voice1_wave', 'voice1_adsr', 'voice1_pulse',
                    'voice2_freq', 'voice2_wave', 'voice2_adsr', 'voice2_pulse',
                    'voice3_freq', 'voice3_wave', 'voice3_adsr', 'voice3_pulse',
                    'total_diffs', 'frames_traced', 'status', 'duration',
                    'heatmap_path', 'comparison_path'
                ])

                # Data rows
                for r in self.results:
                    writer.writerow([
                        r.filename_a, r.filename_b, f"{r.frame_match_percent:.2f}",
                        f"{r.register_accuracy_overall:.2f}",
                        f"{r.voice1_freq:.2f}", f"{r.voice1_wave:.2f}",
                        f"{r.voice1_adsr:.2f}", f"{r.voice1_pulse:.2f}",
                        f"{r.voice2_freq:.2f}", f"{r.voice2_wave:.2f}",
                        f"{r.voice2_adsr:.2f}", f"{r.voice2_pulse:.2f}",
                        f"{r.voice3_freq:.2f}", f"{r.voice3_wave:.2f}",
                        f"{r.voice3_adsr:.2f}", f"{r.voice3_pulse:.2f}",
                        r.total_diff_count, r.frames_traced, r.status, f"{r.duration:.2f}",
                        r.heatmap_path or "", r.comparison_path or ""
                    ])

            return True

        except Exception as e:
            print(f"[ERROR] Failed to export CSV: {e}")
            return False

    def export_json(self, output_path: Path, summary: BatchAnalysisSummary) -> bool:
        """
        Export results and summary to JSON file.

        Args:
            output_path: Path to JSON file
            summary: BatchAnalysisSummary to include

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build JSON structure
            data = {
                "summary": {
                    "total_pairs": summary.total_pairs,
                    "successful": summary.successful,
                    "failed": summary.failed,
                    "partial": summary.partial,
                    "avg_frame_match": round(summary.avg_frame_match, 2),
                    "avg_register_accuracy": round(summary.avg_register_accuracy, 2),
                    "best_match": {
                        "filename": summary.best_match_filename,
                        "accuracy": round(summary.best_match_accuracy, 2)
                    } if summary.best_match_filename else None,
                    "worst_match": {
                        "filename": summary.worst_match_filename,
                        "accuracy": round(summary.worst_match_accuracy, 2)
                    } if summary.worst_match_filename else None,
                    "avg_voice1_accuracy": round(summary.avg_voice1_accuracy, 2),
                    "avg_voice2_accuracy": round(summary.avg_voice2_accuracy, 2),
                    "avg_voice3_accuracy": round(summary.avg_voice3_accuracy, 2),
                    "total_duration": round(summary.total_duration, 2),
                    "avg_duration_per_pair": round(summary.avg_duration_per_pair, 2)
                },
                "config": {
                    "frames": self.config.frames,
                    "generate_heatmaps": self.config.generate_heatmaps,
                    "generate_comparisons": self.config.generate_comparisons
                },
                "results": []
            }

            # Add individual results
            for r in self.results:
                result_dict = {
                    "filename_a": r.filename_a,
                    "filename_b": r.filename_b,
                    "path_a": r.path_a,
                    "path_b": r.path_b,
                    "metrics": {
                        "frame_match_percent": round(r.frame_match_percent, 2),
                        "register_accuracy": round(r.register_accuracy_overall, 2),
                        "total_diffs": r.total_diff_count,
                        "voice_accuracy": {
                            "voice1": {
                                "frequency": round(r.voice1_freq, 2),
                                "waveform": round(r.voice1_wave, 2),
                                "adsr": round(r.voice1_adsr, 2),
                                "pulse": round(r.voice1_pulse, 2)
                            },
                            "voice2": {
                                "frequency": round(r.voice2_freq, 2),
                                "waveform": round(r.voice2_wave, 2),
                                "adsr": round(r.voice2_adsr, 2),
                                "pulse": round(r.voice2_pulse, 2)
                            },
                            "voice3": {
                                "frequency": round(r.voice3_freq, 2),
                                "waveform": round(r.voice3_wave, 2),
                                "adsr": round(r.voice3_adsr, 2),
                                "pulse": round(r.voice3_pulse, 2)
                            }
                        }
                    },
                    "status": r.status,
                    "duration": round(r.duration, 2),
                    "frames_traced": r.frames_traced,
                    "artifacts": {
                        "heatmap": r.heatmap_path,
                        "comparison": r.comparison_path
                    }
                }

                if r.error_message:
                    result_dict["error"] = r.error_message

                data["results"].append(result_dict)

            # Write JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            print(f"[ERROR] Failed to export JSON: {e}")
            return False


def main():
    """Test batch analysis engine."""
    print("Batch Analysis Engine - Test Mode")
    print("This module is meant to be imported, not run directly.")
    print()
    print("Usage:")
    print("  from batch_analysis_engine import BatchAnalysisEngine, BatchAnalysisConfig")
    print("  config = BatchAnalysisConfig(dir_a=Path('originals'), dir_b=Path('exported'), ...)")
    print("  engine = BatchAnalysisEngine(config)")
    print("  summary = engine.run()")
    print()
    print("See batch_analysis_tool.py for complete CLI usage.")


if __name__ == '__main__':
    main()
