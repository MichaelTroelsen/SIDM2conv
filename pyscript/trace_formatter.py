"""
Trace Formatter - Formats trace data to SIDwinder text format

This module provides the TraceFormatter class which formats captured
SID register writes into the text format used by SIDwinder.exe.

Output Format:
    Line 1: Initialization writes (no FRAME: prefix)
            D417:$00,D416:$00,...,D400:$00,

    Lines 2+: Frame writes (with FRAME: prefix, one per frame)
            FRAME: D405:$04,D406:$A5,D404:$08,
            FRAME: D40F:$00,D408:$00,D401:$0F,

Part of the Python SIDwinder replacement project (v2.8.0).
"""

from typing import List, TextIO
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sidm2.cpu6502_emulator import SIDRegisterWrite
from pyscript.sidtracer import TraceData


class TraceFormatter:
    """Formats trace data to SIDwinder-compatible text format."""

    @staticmethod
    def _format_register(write: SIDRegisterWrite) -> str:
        """Format single register write: D40X:$YY

        Args:
            write: SID register write event

        Returns:
            Formatted string like "D405:$A4"
        """
        return f"{write.address:04X}:${write.value:02X}"

    @staticmethod
    def _format_init_line(writes: List[SIDRegisterWrite]) -> str:
        """Format initialization line (no FRAME: prefix).

        Args:
            writes: List of SID register writes during init

        Returns:
            Formatted line like "D417:$00,D416:$00,...,\n"
        """
        if not writes:
            return "\n"  # Empty init line

        # Format each write
        formatted = [TraceFormatter._format_register(w) for w in writes]

        # Join with commas, add trailing comma and newline
        return ",".join(formatted) + ",\n"

    @staticmethod
    def _format_frame_line(writes: List[SIDRegisterWrite]) -> str:
        """Format frame line (with FRAME: prefix).

        Args:
            writes: List of SID register writes during this frame

        Returns:
            Formatted line like "FRAME: D405:$04,D406:$A5,\n"
            If no writes, returns "FRAME:\n"
        """
        if not writes:
            return "FRAME:\n"  # Empty frame (no register changes)

        # Format each write
        formatted = [TraceFormatter._format_register(w) for w in writes]

        # Join with commas, add FRAME: prefix, trailing comma and newline
        return "FRAME: " + ",".join(formatted) + ",\n"

    @staticmethod
    def format_trace(trace_data: TraceData) -> str:
        """Format complete trace data to SIDwinder text format.

        Args:
            trace_data: Trace data from SIDTracer

        Returns:
            Complete formatted trace output as string
        """
        lines = []

        # Line 1: Initialization writes
        lines.append(TraceFormatter._format_init_line(trace_data.init_writes))

        # Lines 2+: Frame writes
        for frame_writes in trace_data.frame_writes:
            lines.append(TraceFormatter._format_frame_line(frame_writes))

        return "".join(lines)

    @staticmethod
    def write_trace_file(trace_data: TraceData, output_path: Path):
        """Write trace data to file in SIDwinder text format.

        Args:
            trace_data: Trace data from SIDTracer
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(TraceFormatter.format_trace(trace_data))

    @staticmethod
    def format_trace_summary(trace_data: TraceData) -> str:
        """Format trace summary for logging/debugging.

        Args:
            trace_data: Trace data from SIDTracer

        Returns:
            Human-readable summary
        """
        lines = []
        lines.append(f"Trace Summary:")
        lines.append(f"  Frames: {trace_data.frames}")
        lines.append(f"  Cycles: {trace_data.cycles:,}")
        lines.append(f"  Init writes: {len(trace_data.init_writes)}")

        total_frame_writes = sum(len(fw) for fw in trace_data.frame_writes)
        lines.append(f"  Frame writes: {total_frame_writes:,} total")

        if trace_data.frame_writes:
            avg_per_frame = total_frame_writes / len(trace_data.frame_writes)
            lines.append(f"  Avg per frame: {avg_per_frame:.1f}")

        # Register usage statistics
        if trace_data.init_writes or trace_data.frame_writes:
            reg_usage = TraceFormatter._analyze_register_usage(trace_data)
            lines.append(f"  Most used registers:")
            for reg, count in sorted(reg_usage.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"    {reg:04X}: {count:,} writes")

        return "\n".join(lines)

    @staticmethod
    def _analyze_register_usage(trace_data: TraceData) -> dict:
        """Analyze which registers were written to most.

        Args:
            trace_data: Trace data from SIDTracer

        Returns:
            Dict mapping register address to write count
        """
        usage = {}

        # Count init writes
        for write in trace_data.init_writes:
            usage[write.address] = usage.get(write.address, 0) + 1

        # Count frame writes
        for frame_writes in trace_data.frame_writes:
            for write in frame_writes:
                usage[write.address] = usage.get(write.address, 0) + 1

        return usage


if __name__ == "__main__":
    # Simple test
    from pyscript.sidtracer import SIDTracer

    if len(sys.argv) < 2:
        print("Usage: python trace_formatter.py <sid_file> [output_file] [frames]")
        sys.exit(1)

    sid_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("trace_output.txt")
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    print(f"Tracing {sid_path.name}...")
    tracer = SIDTracer(sid_path, verbose=0)
    trace_data = tracer.trace(frames)

    print(f"\n{TraceFormatter.format_trace_summary(trace_data)}")

    print(f"\nWriting trace to {output_path}...")
    TraceFormatter.write_trace_file(trace_data, output_path)

    print(f"Done! ({output_path.stat().st_size:,} bytes)")
