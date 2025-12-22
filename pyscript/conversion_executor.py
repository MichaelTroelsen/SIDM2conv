#!/usr/bin/env python3
"""
Conversion Executor - Backend engine for batch SID conversion

Orchestrates batch conversion with configurable pipeline steps,
subprocess management, and real-time progress tracking.

Version: 1.0.0
Date: 2025-12-22
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QProcess, QTimer, QThreadPool, QRunnable, QMutex
    from PyQt6.QtCore import QProcessEnvironment
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("ERROR: PyQt6 is required for the Conversion Executor")
    sys.exit(1)

from pipeline_config import PipelineConfig, PipelineStep


@dataclass
class FileResult:
    """Results for a single file conversion"""
    filename: str
    driver: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    accuracy: float = 0.0
    status: str = "pending"  # pending, running, passed, failed, warning
    error_message: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    output_files: List[str] = field(default_factory=list)


class FileWorker(QRunnable):
    """Worker for processing a single file in a thread pool"""

    def __init__(self, executor: 'ConversionExecutor', sid_file: str, file_index: int, total_files: int):
        super().__init__()
        self.executor = executor
        self.sid_file = sid_file
        self.file_index = file_index
        self.total_files = total_files
        self.setAutoDelete(True)

    def run(self):
        """Execute pipeline for this file (runs in worker thread)"""
        try:
            # Emit file started signal
            self.executor.file_started.emit(self.sid_file, self.file_index, self.total_files)

            # Initialize result for this file (thread-safe)
            self.executor._mutex.lock()
            result = FileResult(
                filename=self.sid_file,
                driver=self.executor.config.primary_driver,
                start_time=time.time()
            )
            self.executor.results[self.sid_file] = result
            self.executor._mutex.unlock()

            # Run pipeline for this file
            self._run_pipeline_for_file()

            # Mark file as completed (thread-safe)
            self.executor._mutex.lock()
            result = self.executor.results[self.sid_file]
            result.end_time = time.time()
            if result.status == "running":
                result.status = "passed" if result.steps_completed == result.total_steps else "warning"

            # Collect final results
            self._collect_results()

            # Emit file completed
            self.executor.file_completed.emit(self.sid_file, self.executor._result_to_dict(result))

            # Update progress
            completed = sum(1 for r in self.executor.results.values() if r.status in ["passed", "warning", "failed"])
            progress = int((completed / self.total_files) * 100)
            self.executor.progress_updated.emit(progress)

            # Decrement active workers count
            self.executor._active_workers -= 1
            has_pending = self.executor._has_pending_files()
            active_count = self.executor._active_workers
            self.executor._mutex.unlock()

            # Start next workers if there are pending files
            if has_pending and self.executor.is_running and not self.executor.is_paused:
                self.executor._start_next_workers()

            # Check if batch is complete
            if active_count == 0 and not has_pending:
                summary = self.executor._get_summary()
                self.executor.batch_completed.emit(summary)
                self.executor.is_running = False

        except Exception as e:
            # Handle any unexpected errors
            self.executor._mutex.lock()
            if self.sid_file in self.executor.results:
                self.executor.results[self.sid_file].status = "failed"
                self.executor.results[self.sid_file].error_message = str(e)
            self.executor._active_workers -= 1
            self.executor._mutex.unlock()
            self.executor.error_occurred.emit(self.sid_file, str(e))

    def _run_pipeline_for_file(self):
        """Execute configured pipeline steps for one file"""
        enabled_steps = self.executor.config.get_enabled_steps()

        self.executor._mutex.lock()
        result = self.executor.results[self.sid_file]
        result.total_steps = len(enabled_steps)
        result.status = "running"
        self.executor._mutex.unlock()

        for step_num, step_name in enumerate(enabled_steps, 1):
            if not self.executor.is_running or self.executor.is_paused:
                break

            self.executor.step_started.emit(step_name, step_num, len(enabled_steps))

            success, message = self._run_step(step_name)

            self.executor.step_completed.emit(step_name, success, message)

            self.executor._mutex.lock()
            if success:
                result.steps_completed += 1
            else:
                result.error_message = message
                if self.executor.config.stop_on_error:
                    result.status = "failed"
                    self.executor._mutex.unlock()
                    break
            self.executor._mutex.unlock()

    def _run_step(self, step_name: str) -> Tuple[bool, str]:
        """Run a single pipeline step using QProcess (thread-safe)"""
        # Map step name to command
        commands = self.executor._get_step_command(step_name, self.sid_file)

        if not commands:
            return False, f"Unknown step: {step_name}"

        self.executor.log_message.emit("DEBUG", f"[Worker {self.file_index}] Running: {' '.join(commands)}")

        # Handle steps with output redirection
        output_file = self.executor._get_output_file_for_step(step_name, self.sid_file)

        # Create QProcess for this step (each worker gets its own)
        process = QProcess()
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # Start process
        program = commands[0]
        args = commands[1:] if len(commands) > 1 else []

        process.start(program, args)

        if not process.waitForStarted(3000):
            error = process.errorString()
            return False, f"Failed to start: {error}"

        # Wait for process to finish (with timeout)
        timeout = self.executor.config.step_timeout_ms
        if not process.waitForFinished(timeout):
            process.kill()
            return False, f"Process timeout ({timeout}ms)"

        exit_code = process.exitCode()
        success = exit_code == 0

        # Save output to file if needed
        if output_file and success:
            try:
                output_data = bytes(process.readAllStandardOutput()).decode('utf-8', errors='replace')
                if output_data:
                    with open(output_file, 'w') as f:
                        f.write(output_data)
                    message = f"Exit code: {exit_code}, output saved to {Path(output_file).name}"
                else:
                    message = f"Exit code: {exit_code}"
            except Exception as e:
                message = f"Exit code: {exit_code}, but failed to save output: {e}"
        else:
            message = f"Exit code: {exit_code}"

        return success, message

    def _collect_results(self):
        """Parse output files to collect results (simplified for now)"""
        # TODO: Parse info.txt and other files to extract accuracy metrics
        # For now, just mark as completed
        pass


class ConversionExecutor(QObject):
    """
    Backend engine for batch conversion with configurable pipeline steps.

    Emits signals for UI updates:
    - batch_started: When batch conversion begins
    - file_started: When processing a new file
    - step_started: When starting a pipeline step
    - step_completed: When a step finishes
    - file_completed: When all steps for a file complete
    - batch_completed: When entire batch finishes
    - progress_updated: Percentage progress (0-100)
    - log_message: Log output from subprocesses
    - error_occurred: When an error happens
    """

    # Signals (Qt event system)
    batch_started = pyqtSignal(int)                    # total_files
    file_started = pyqtSignal(str, int, int)           # filename, index, total
    step_started = pyqtSignal(str, int, int)           # step_name, step_num, total_steps
    step_completed = pyqtSignal(str, bool, str)        # step_name, success, message
    file_completed = pyqtSignal(str, dict)             # filename, results_dict
    batch_completed = pyqtSignal(dict)                 # summary_dict
    progress_updated = pyqtSignal(int)                 # percentage (0-100)
    log_message = pyqtSignal(str, str)                 # level, message
    error_occurred = pyqtSignal(str, str)              # filename, error_message

    def __init__(self, config: PipelineConfig):
        super().__init__()
        self.config = config
        self.process: Optional[QProcess] = None
        self.is_running = False
        self.is_paused = False
        self.current_file_index = 0
        self.files_to_process: List[str] = []
        self.results: Dict[str, FileResult] = {}
        self.start_time = 0.0

        # Concurrent processing support
        self._thread_pool = QThreadPool.globalInstance()
        self._thread_pool.setMaxThreadCount(self.config.concurrent_workers)
        self._mutex = QMutex()
        self._active_workers = 0
        self._pending_file_indices: List[int] = []

    def start_batch(self, files: List[str]):
        """Start batch conversion using thread pool"""
        if self.is_running:
            self.log_message.emit("WARN", "Conversion already running")
            return

        self.files_to_process = files
        self.is_running = True
        self.is_paused = False
        self.current_file_index = 0
        self.results = {}
        self.start_time = time.time()
        self._active_workers = 0
        self._pending_file_indices = list(range(len(files)))

        workers_str = f"{self.config.concurrent_workers} worker(s)"
        self.log_message.emit("INFO", f"Starting batch conversion: {len(files)} files with {workers_str}")
        self.batch_started.emit(len(files))

        # Start initial batch of workers (up to concurrent_workers limit)
        self._start_next_workers()

    def pause(self):
        """Pause batch processing"""
        if not self.is_running or self.is_paused:
            return

        self.is_paused = True
        self.log_message.emit("INFO", "Batch conversion paused")

        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            self.process.waitForFinished(3000)

    def resume(self):
        """Resume batch processing"""
        if not self.is_running or not self.is_paused:
            return

        self.is_paused = False
        self.log_message.emit("INFO", "Batch conversion resumed")
        self._start_next_workers()

    def stop(self):
        """Stop batch processing"""
        if not self.is_running:
            return

        self.is_running = False
        self.is_paused = False
        self.log_message.emit("INFO", "Batch conversion stopped")

        # Clear pending files
        self._mutex.lock()
        self._pending_file_indices.clear()
        self._mutex.unlock()

        # Wait for active workers to finish
        self._thread_pool.waitForDone(5000)  # 5 second timeout

        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process.waitForFinished(1000)

        # Emit completion with partial results
        summary = self._get_summary()
        self.batch_completed.emit(summary)

    def _start_next_workers(self):
        """Start next batch of workers up to concurrent_workers limit"""
        self._mutex.lock()

        # Start workers up to the limit
        while (self._active_workers < self.config.concurrent_workers and
               len(self._pending_file_indices) > 0 and
               self.is_running and not self.is_paused):

            # Get next file index
            file_index = self._pending_file_indices.pop(0)
            sid_file = self.files_to_process[file_index]

            # Create and start worker
            worker = FileWorker(self, sid_file, file_index, len(self.files_to_process))
            self._active_workers += 1
            self._thread_pool.start(worker)

            self.log_message.emit("DEBUG", f"Started worker {file_index + 1}/{len(self.files_to_process)} ({self._active_workers} active)")

        self._mutex.unlock()

    def _has_pending_files(self) -> bool:
        """Check if there are pending files to process"""
        # Mutex should already be locked by caller
        return len(self._pending_file_indices) > 0

    # Note: Old sequential processing methods (_process_next_file, _run_pipeline_for_file, _run_step)
    # have been replaced by FileWorker class for concurrent processing.
    # See FileWorker.run() and FileWorker._run_pipeline_for_file() above.

    def _get_output_file_for_step(self, step_name: str, sid_file: str) -> Optional[str]:
        """Get output file path for steps that generate output"""
        output_dir = Path(self.config.output_directory or "output")
        sid_path = Path(sid_file)
        base_name = sid_path.stem
        output_base = output_dir / base_name / "New"
        analysis_dir = output_base / "analysis"

        output_map = {
            "siddump_original": str(output_base / f"{base_name}_original.dump"),
            "siddump_exported": str(output_base / f"{base_name}_exported.dump"),
            "sidwinder_trace": str(analysis_dir / f"{base_name}_trace.txt"),
            "siddecompiler": str(analysis_dir / f"{base_name}_siddecompiler.asm"),
            "sidwinder_disasm": str(analysis_dir / f"{base_name}_disassembly.asm"),
        }

        return output_map.get(step_name)

    def _get_step_command(self, step_name: str, sid_file: str) -> List[str]:
        """Get command for a pipeline step"""
        # Base paths
        scripts_dir = Path(__file__).parent.parent / "scripts"
        pyscript_dir = Path(__file__).parent
        tools_dir = Path(__file__).parent.parent / "tools"
        output_dir = Path(self.config.output_directory or "output")

        # Generate output filenames
        sid_path = Path(sid_file)
        base_name = sid_path.stem
        output_base = output_dir / base_name / "New"
        output_base.mkdir(parents=True, exist_ok=True)

        # Analysis directory
        analysis_dir = output_base / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        sf2_file = str(output_base / f"{base_name}_d11.sf2")
        sid_export = str(output_base / f"{base_name}_exported.sid")
        original_dump = str(output_base / f"{base_name}_original.dump")
        exported_dump = str(output_base / f"{base_name}_exported.dump")
        original_wav = str(output_base / f"{base_name}_original.wav")
        exported_wav = str(output_base / f"{base_name}_exported.wav")
        original_hex = str(output_base / f"{base_name}_original.hex")
        exported_hex = str(output_base / f"{base_name}_exported.hex")
        trace_file = str(analysis_dir / f"{base_name}_trace.txt")
        disasm_file = str(analysis_dir / f"{base_name}_disassembly.asm")
        info_file = str(output_base / "info.txt")
        siddecompiler_asm = str(analysis_dir / f"{base_name}_siddecompiler.asm")
        analysis_report = str(analysis_dir / f"{base_name}_analysis_report.txt")

        # Command mappings for all 14 steps
        command_map = {
            # Step 1: SID → SF2 Conversion (Required)
            "conversion": [
                "python", str(scripts_dir / "sid_to_sf2.py"),
                sid_file, sf2_file,
                "--driver", self.config.primary_driver
            ],

            # Step 2: Siddump (Original)
            "siddump_original": [
                str(tools_dir / "siddump.exe"),
                sid_file, "-t30"
            ],

            # Step 3: SIDdecompiler Analysis
            "siddecompiler": [
                str(tools_dir / "SIDdecompiler.exe"),
                sid_file
            ],

            # Step 4: SF2 → SID Packing (Required for validation)
            "packing": [
                "python", str(scripts_dir / "sf2_to_sid.py"),
                sf2_file, sid_export
            ],

            # Step 5: Siddump (Exported)
            "siddump_exported": [
                str(tools_dir / "siddump.exe"),
                sid_export, "-t30"
            ],

            # Step 6: WAV Rendering (Original)
            "wav_original": [
                str(tools_dir / "SID2WAV.EXE"),
                "-t30", "-16", sid_file, original_wav
            ],

            # Step 7: WAV Rendering (Exported)
            "wav_exported": [
                str(tools_dir / "SID2WAV.EXE"),
                "-t30", "-16", sid_export, exported_wav
            ],

            # Step 8: Hexdump Generation
            "hexdump": [
                "cmd", "/c",
                f'xxd "{sid_file}" > "{original_hex}" && xxd "{sid_export}" > "{exported_hex}"'
            ],

            # Step 9: SIDwinder Trace
            "sidwinder_trace": [
                str(tools_dir / "SIDwinder.exe"),
                "trace", sid_file
            ],

            # Step 10: Info.txt Report (Generated during conversion)
            "info_report": [
                "python", "-c",
                f'print("Info report generated during conversion")'
            ],

            # Step 11: Annotated Disassembly
            "annotated_disasm": [
                "python", str(scripts_dir / "disassemble_sid.py"),
                sid_export
            ],

            # Step 12: SIDwinder Disassembly
            "sidwinder_disasm": [
                str(tools_dir / "SIDwinder.exe"),
                "disassemble", sid_export
            ],

            # Step 13: Validation (File checks)
            "validation": [
                "python", str(scripts_dir / "validate_sid_accuracy.py"),
                sid_file, sid_export
            ],

            # Step 14: MIDI Comparison
            "midi_comparison": [
                "python", str(scripts_dir / "test_midi_comparison.py"),
                sid_file, sid_export
            ]
        }

        return command_map.get(step_name, [])

    def _on_output_ready(self):
        """Capture and emit subprocess output"""
        if self.process:
            output = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
            for line in output.strip().split('\n'):
                if line:
                    level = self._extract_log_level(line)
                    self.log_message.emit(level, line)

    def _extract_log_level(self, line: str) -> str:
        """Extract log level from log line"""
        line_upper = line.upper()
        if "ERROR" in line_upper or "FAIL" in line_upper:
            return "ERROR"
        elif "WARN" in line_upper:
            return "WARN"
        elif "DEBUG" in line_upper:
            return "DEBUG"
        else:
            return "INFO"

    def _collect_results(self, sid_file: str):
        """Parse output files to collect results"""
        result = self.results[sid_file]

        # Check for output files
        sid_path = Path(sid_file)
        base_name = sid_path.stem
        output_base = Path(self.config.output_directory or "output") / base_name / "New"

        # Look for info.txt for accuracy
        info_file = output_base / "info.txt"
        if info_file.exists():
            try:
                with open(info_file, 'r') as f:
                    content = f.read()
                    # Parse accuracy if present
                    if "Accuracy:" in content:
                        for line in content.split('\n'):
                            if "Accuracy:" in line:
                                try:
                                    accuracy_str = line.split(':')[1].strip().rstrip('%')
                                    result.accuracy = float(accuracy_str)
                                except:
                                    pass
            except:
                pass

        # Count output files
        if output_base.exists():
            result.output_files = [str(f) for f in output_base.iterdir() if f.is_file()]

    def _result_to_dict(self, result: FileResult) -> Dict:
        """Convert FileResult to dictionary"""
        return {
            "filename": result.filename,
            "driver": result.driver,
            "steps_completed": result.steps_completed,
            "total_steps": result.total_steps,
            "accuracy": result.accuracy,
            "status": result.status,
            "error_message": result.error_message,
            "duration": result.end_time - result.start_time if result.end_time > 0 else 0,
            "output_files": result.output_files
        }

    def _get_summary(self) -> Dict:
        """Get batch summary statistics"""
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r.status == "passed")
        failed = sum(1 for r in self.results.values() if r.status == "failed")
        warnings = sum(1 for r in self.results.values() if r.status == "warning")

        accuracies = [r.accuracy for r in self.results.values() if r.accuracy > 0]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0

        duration = time.time() - self.start_time if self.start_time > 0 else 0

        return {
            "total_files": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "avg_accuracy": avg_accuracy,
            "duration": duration,
            "pass_rate": (passed / total * 100) if total > 0 else 0
        }
