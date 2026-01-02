"""Database operations for validation tracking."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


class ValidationDatabase:
    """Manages validation results database."""

    def __init__(self, db_path: Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Create database and tables if they don't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Return dict-like rows

        cursor = self.conn.cursor()

        # Create validation_runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                git_commit TEXT,
                pipeline_version TEXT,
                notes TEXT
            )
        """)

        # Create file_results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                filename TEXT NOT NULL,

                -- Conversion metrics
                conversion_method TEXT,
                conversion_success BOOLEAN,
                conversion_time_ms INTEGER,

                -- File sizes
                original_size INTEGER,
                sf2_size INTEGER,
                exported_size INTEGER,

                -- Accuracy metrics
                overall_accuracy REAL,
                frame_accuracy REAL,
                voice_accuracy REAL,
                register_accuracy REAL,
                filter_accuracy REAL,

                -- Pipeline steps success
                step1_conversion BOOLEAN,
                step2_packing BOOLEAN,
                step3_siddump BOOLEAN,
                step4_wav BOOLEAN,
                step5_hexdump BOOLEAN,
                step6_trace BOOLEAN,
                step7_info BOOLEAN,
                step8_disasm_python BOOLEAN,
                step9_disasm_sidwinder BOOLEAN,

                -- Quality indicators
                sidwinder_warnings INTEGER,
                audio_diff_rms REAL,

                FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
            )
        """)

        # Create metric_trends table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metric_trends (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                metric_name TEXT,
                metric_value REAL,
                FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
            )
        """)

        # Create batch_analysis_results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_analysis_results (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                timestamp TEXT NOT NULL,

                -- Batch configuration
                dir_a TEXT NOT NULL,
                dir_b TEXT NOT NULL,
                frames INTEGER,

                -- Aggregate metrics
                total_pairs INTEGER,
                successful INTEGER,
                failed INTEGER,
                partial INTEGER,
                avg_frame_match REAL,
                avg_register_accuracy REAL,
                avg_voice1_accuracy REAL,
                avg_voice2_accuracy REAL,
                avg_voice3_accuracy REAL,

                -- Best/worst
                best_match_filename TEXT,
                best_match_accuracy REAL,
                worst_match_filename TEXT,
                worst_match_accuracy REAL,

                -- Performance
                total_duration REAL,
                avg_duration_per_pair REAL,

                -- Output paths
                html_report_path TEXT,
                csv_path TEXT,
                json_path TEXT,

                FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
            )
        """)

        # Create batch_analysis_pair_results table (per-pair details)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_analysis_pair_results (
                pair_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER,

                -- File information
                filename_a TEXT NOT NULL,
                filename_b TEXT NOT NULL,
                path_a TEXT,
                path_b TEXT,

                -- Core metrics
                frame_match_percent REAL,
                register_accuracy REAL,
                total_diffs INTEGER,

                -- Voice 1 accuracy
                voice1_freq REAL,
                voice1_wave REAL,
                voice1_adsr REAL,
                voice1_pulse REAL,

                -- Voice 2 accuracy
                voice2_freq REAL,
                voice2_wave REAL,
                voice2_adsr REAL,
                voice2_pulse REAL,

                -- Voice 3 accuracy
                voice3_freq REAL,
                voice3_wave REAL,
                voice3_adsr REAL,
                voice3_pulse REAL,

                -- Status
                status TEXT,
                error_message TEXT,
                duration REAL,
                frames_traced INTEGER,

                -- Artifact paths
                heatmap_path TEXT,
                comparison_path TEXT,

                FOREIGN KEY (batch_id) REFERENCES batch_analysis_results(batch_id)
            )
        """)

        self.conn.commit()

    def create_run(self, git_commit: Optional[str] = None,
                   pipeline_version: Optional[str] = None,
                   notes: Optional[str] = None) -> int:
        """Create a new validation run.

        Args:
            git_commit: Git commit hash
            pipeline_version: Version string
            notes: Optional notes about this run

        Returns:
            run_id of the created run
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO validation_runs (timestamp, git_commit, pipeline_version, notes)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), git_commit, pipeline_version, notes))

        self.conn.commit()
        return cursor.lastrowid

    def add_file_result(self, run_id: int, **kwargs) -> int:
        """Add a file validation result.

        Args:
            run_id: ID of the validation run
            **kwargs: File result data (filename, conversion_method, etc.)

        Returns:
            result_id of the created result
        """
        # Build column names and values from kwargs
        columns = ['run_id'] + list(kwargs.keys())
        values = [run_id] + list(kwargs.values())
        placeholders = ','.join(['?' for _ in columns])

        cursor = self.conn.cursor()
        cursor.execute(f"""
            INSERT INTO file_results ({','.join(columns)})
            VALUES ({placeholders})
        """, values)

        self.conn.commit()
        return cursor.lastrowid

    def add_metric(self, run_id: int, metric_name: str, metric_value: float):
        """Add a metric to trends table.

        Args:
            run_id: ID of the validation run
            metric_name: Name of the metric
            metric_value: Value of the metric
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO metric_trends (run_id, metric_name, metric_value)
            VALUES (?, ?, ?)
        """, (run_id, metric_name, metric_value))
        self.conn.commit()

    def get_latest_run(self) -> Optional[Dict[str, Any]]:
        """Get the most recent validation run.

        Returns:
            Dict with run info, or None if no runs exist
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM validation_runs
            ORDER BY run_id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_run_results(self, run_id: int) -> List[Dict[str, Any]]:
        """Get all file results for a run.

        Args:
            run_id: ID of the validation run

        Returns:
            List of result dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM file_results
            WHERE run_id = ?
            ORDER BY filename
        """, (run_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_file_history(self, filename: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get validation history for a specific file.

        Args:
            filename: Name of the file
            limit: Maximum number of results to return

        Returns:
            List of result dicts with run info
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.*, vr.timestamp, vr.git_commit
            FROM file_results r
            JOIN validation_runs vr ON r.run_id = vr.run_id
            WHERE r.filename = ?
            ORDER BY vr.run_id DESC
            LIMIT ?
        """, (filename, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_metric_trend(self, metric_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trend data for a metric.

        Args:
            metric_name: Name of the metric
            limit: Maximum number of data points

        Returns:
            List of dicts with run_id, timestamp, and metric_value
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT mt.run_id, vr.timestamp, mt.metric_value
            FROM metric_trends mt
            JOIN validation_runs vr ON mt.run_id = vr.run_id
            WHERE mt.metric_name = ?
            ORDER BY mt.run_id DESC
            LIMIT ?
        """, (metric_name, limit))
        return [dict(row) for row in cursor.fetchall()]

    def compare_runs(self, run_id1: int, run_id2: int) -> Dict[str, Any]:
        """Compare two validation runs.

        Args:
            run_id1: First run ID
            run_id2: Second run ID

        Returns:
            Dict with comparison data including regressions
        """
        results1 = {r['filename']: r for r in self.get_run_results(run_id1)}
        results2 = {r['filename']: r for r in self.get_run_results(run_id2)}

        regressions = []
        improvements = []

        for filename in results1.keys() & results2.keys():
            r1 = results1[filename]
            r2 = results2[filename]

            # Check accuracy regression
            if r1['overall_accuracy'] and r2['overall_accuracy']:
                acc_diff = r2['overall_accuracy'] - r1['overall_accuracy']
                if acc_diff < -5.0:  # >5% drop is regression
                    regressions.append({
                        'filename': filename,
                        'type': 'accuracy_drop',
                        'old_value': r1['overall_accuracy'],
                        'new_value': r2['overall_accuracy'],
                        'diff': acc_diff
                    })
                elif acc_diff > 5.0:  # >5% improvement
                    improvements.append({
                        'filename': filename,
                        'type': 'accuracy_improvement',
                        'old_value': r1['overall_accuracy'],
                        'new_value': r2['overall_accuracy'],
                        'diff': acc_diff
                    })

            # Check step failures
            for step in range(1, 10):
                step_col = f'step{step}_conversion' if step == 1 else f'step{step}_packing' if step == 2 else f'step{step}_siddump' if step == 3 else f'step{step}_wav' if step == 4 else f'step{step}_hexdump' if step == 5 else f'step{step}_trace' if step == 6 else f'step{step}_info' if step == 7 else f'step{step}_disasm_python' if step == 8 else 'step9_disasm_sidwinder'

                if r1.get(step_col) and not r2.get(step_col):
                    regressions.append({
                        'filename': filename,
                        'type': 'step_failure',
                        'step': step,
                        'old_value': True,
                        'new_value': False
                    })

        return {
            'run1': run_id1,
            'run2': run_id2,
            'regressions': regressions,
            'improvements': improvements,
            'regression_count': len(regressions),
            'improvement_count': len(improvements)
        }

    def export_to_json(self, run_id: int, output_path: Path):
        """Export run results to JSON.

        Args:
            run_id: ID of the validation run
            output_path: Path to output JSON file
        """
        run_info = self.get_latest_run()
        results = self.get_run_results(run_id)

        data = {
            'run_info': run_info,
            'results': results,
            'summary': {
                'total_files': len(results),
                'passed': sum(1 for r in results if r.get('conversion_success')),
                'avg_accuracy': sum(r.get('overall_accuracy', 0) for r in results) / len(results) if results else 0
            }
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_batch_analysis(self, run_id: int, summary: Dict[str, Any],
                          config: Dict[str, Any], output_paths: Dict[str, str]) -> int:
        """Add a batch analysis result.

        Args:
            run_id: ID of the validation run
            summary: BatchAnalysisSummary data
            config: Batch configuration (dir_a, dir_b, frames)
            output_paths: Dictionary with html_report_path, csv_path, json_path

        Returns:
            batch_id of the created batch analysis
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO batch_analysis_results (
                run_id, timestamp, dir_a, dir_b, frames,
                total_pairs, successful, failed, partial,
                avg_frame_match, avg_register_accuracy,
                avg_voice1_accuracy, avg_voice2_accuracy, avg_voice3_accuracy,
                best_match_filename, best_match_accuracy,
                worst_match_filename, worst_match_accuracy,
                total_duration, avg_duration_per_pair,
                html_report_path, csv_path, json_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            datetime.now().isoformat(),
            config.get('dir_a', ''),
            config.get('dir_b', ''),
            config.get('frames', 0),
            summary.get('total_pairs', 0),
            summary.get('successful', 0),
            summary.get('failed', 0),
            summary.get('partial', 0),
            summary.get('avg_frame_match', 0.0),
            summary.get('avg_register_accuracy', 0.0),
            summary.get('avg_voice1_accuracy', 0.0),
            summary.get('avg_voice2_accuracy', 0.0),
            summary.get('avg_voice3_accuracy', 0.0),
            summary.get('best_match_filename', ''),
            summary.get('best_match_accuracy', 0.0),
            summary.get('worst_match_filename', ''),
            summary.get('worst_match_accuracy', 0.0),
            summary.get('total_duration', 0.0),
            summary.get('avg_duration_per_pair', 0.0),
            output_paths.get('html_report_path', ''),
            output_paths.get('csv_path', ''),
            output_paths.get('json_path', '')
        ))

        self.conn.commit()
        return cursor.lastrowid

    def add_batch_pair_result(self, batch_id: int, pair_result: Dict[str, Any]) -> int:
        """Add a batch analysis pair result.

        Args:
            batch_id: ID of the batch analysis
            pair_result: PairAnalysisResult data

        Returns:
            pair_id of the created pair result
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO batch_analysis_pair_results (
                batch_id, filename_a, filename_b, path_a, path_b,
                frame_match_percent, register_accuracy, total_diffs,
                voice1_freq, voice1_wave, voice1_adsr, voice1_pulse,
                voice2_freq, voice2_wave, voice2_adsr, voice2_pulse,
                voice3_freq, voice3_wave, voice3_adsr, voice3_pulse,
                status, error_message, duration, frames_traced,
                heatmap_path, comparison_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            pair_result.get('filename_a', ''),
            pair_result.get('filename_b', ''),
            pair_result.get('path_a', ''),
            pair_result.get('path_b', ''),
            pair_result.get('frame_match_percent', 0.0),
            pair_result.get('register_accuracy_overall', 0.0),
            pair_result.get('total_diff_count', 0),
            pair_result.get('voice1_freq', 0.0),
            pair_result.get('voice1_wave', 0.0),
            pair_result.get('voice1_adsr', 0.0),
            pair_result.get('voice1_pulse', 0.0),
            pair_result.get('voice2_freq', 0.0),
            pair_result.get('voice2_wave', 0.0),
            pair_result.get('voice2_adsr', 0.0),
            pair_result.get('voice2_pulse', 0.0),
            pair_result.get('voice3_freq', 0.0),
            pair_result.get('voice3_wave', 0.0),
            pair_result.get('voice3_adsr', 0.0),
            pair_result.get('voice3_pulse', 0.0),
            pair_result.get('status', 'pending'),
            pair_result.get('error_message'),
            pair_result.get('duration', 0.0),
            pair_result.get('frames_traced', 0),
            pair_result.get('heatmap_path'),
            pair_result.get('comparison_path')
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_batch_analysis_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent batch analysis results.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of batch analysis results
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM batch_analysis_results
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_batch_pair_results(self, batch_id: int) -> List[Dict[str, Any]]:
        """Get pair results for a specific batch.

        Args:
            batch_id: ID of the batch analysis

        Returns:
            List of pair results
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM batch_analysis_pair_results
            WHERE batch_id = ?
            ORDER BY filename_a
        """, (batch_id,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
