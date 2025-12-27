"""
Subroutine Tracer for SID Conversion Pipeline - Phase 3

Traces JSR (Jump to Subroutine) calls in 6502 code to build call graphs.
Integrated into the conversion pipeline as Step 18.

Usage:
    from sidm2.subroutine_tracer import SubroutineTracer

    tracer = SubroutineTracer(sid_file=Path("input.sid"))
    call_graph = tracer.analyze()
    report = tracer.generate_report(call_graph, output_file)
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict
import logging

from .errors import InvalidInputError

logger = logging.getLogger(__name__)


class Subroutine:
    """Represents a subroutine in the code"""

    def __init__(self, address: int):
        self.address = address
        self.callers = []  # Addresses that call this subroutine
        self.calls = []    # Addresses this subroutine calls
        self.size = 0      # Estimated size in bytes

    def add_caller(self, caller_addr: int):
        """Add a caller to this subroutine"""
        if caller_addr not in self.callers:
            self.callers.append(caller_addr)

    def add_call(self, target_addr: int):
        """Add a call target from this subroutine"""
        if target_addr not in self.calls:
            self.calls.append(target_addr)

    def __repr__(self):
        return f"Subroutine(${self.address:04X}, {len(self.callers)} callers, {len(self.calls)} calls)"


class SubroutineTracer:
    """Traces subroutine calls in SID files"""

    # 6502 opcodes
    JSR_OPCODE = 0x20  # JSR absolute
    RTS_OPCODE = 0x60  # RTS
    JMP_OPCODE = 0x4C  # JMP absolute

    def __init__(self, sid_file: Path):
        """
        Initialize subroutine tracer.

        Args:
            sid_file: Path to SID file to analyze
        """
        self.sid_file = sid_file
        self.header = {}
        self.data = b''
        self.load_addr = 0
        self.subroutines = {}  # Dict[address, Subroutine]

    def _read_sid_header(self) -> Dict[str, Any]:
        """Read and parse SID file header"""
        with open(self.sid_file, 'rb') as f:
            header_bytes = f.read(0x7E)

        if len(header_bytes) < 0x7E:
            raise InvalidInputError(
                input_type='SID file',
                value=str(self.sid_file),
                expected='At least 126 bytes for SID header',
                got=f'Only {len(header_bytes)} bytes available',
                suggestions=[
                    'Verify file is a complete SID file (not truncated)',
                    'Check if file was fully downloaded',
                    f'File size: {self.sid_file.stat().st_size if self.sid_file.exists() else 0} bytes',
                    'SID files should be at least 126 bytes + music data',
                    'Try re-downloading or re-exporting the file'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        magic = header_bytes[0:4]
        if magic not in (b'PSID', b'RSID'):
            raise InvalidInputError(
                input_type='SID file',
                value=str(self.sid_file),
                expected='PSID or RSID magic bytes at file start',
                got=f'Magic bytes: {repr(magic)}',
                suggestions=[
                    'Verify file is a valid SID file (not corrupted)',
                    'Check file extension is .sid',
                    'Try opening file in a SID player (e.g., VICE) to verify',
                    f'Inspect file header: hexdump -C {self.sid_file} | head -5',
                    'Re-download file if obtained from internet'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        return {
            'magic': magic.decode('ascii'),
            'version': int.from_bytes(header_bytes[4:6], 'big'),
            'data_offset': int.from_bytes(header_bytes[6:8], 'big'),
            'load_addr': int.from_bytes(header_bytes[8:10], 'big'),
            'init_addr': int.from_bytes(header_bytes[10:12], 'big'),
            'play_addr': int.from_bytes(header_bytes[12:14], 'big'),
            'name': header_bytes[22:54].split(b'\x00')[0].decode('ascii', errors='ignore'),
            'author': header_bytes[54:86].split(b'\x00')[0].decode('ascii', errors='ignore'),
        }

    def _read_sid_data(self) -> Tuple[bytes, int]:
        """Read SID music data"""
        with open(self.sid_file, 'rb') as f:
            f.seek(self.header['data_offset'])
            data = f.read()

        load_addr = self.header['load_addr']
        if load_addr == 0:
            load_addr = data[0] | (data[1] << 8)
            data = data[2:]

        return data, load_addr

    def _trace_subroutines(self, start_addr: int, max_depth: int = 100) -> Set[int]:
        """
        Trace subroutines starting from a given address.

        Args:
            start_addr: Starting address to trace
            max_depth: Maximum depth to trace (prevent infinite loops)

        Returns:
            Set of discovered subroutine addresses
        """
        discovered = set()
        to_analyze = [(start_addr, 0)]  # (address, depth)
        analyzed = set()

        while to_analyze:
            addr, depth = to_analyze.pop(0)

            # Check depth limit
            if depth >= max_depth:
                continue

            # Skip if already analyzed
            if addr in analyzed:
                continue
            analyzed.add(addr)

            # Check if address is within data bounds
            offset = addr - self.load_addr
            if offset < 0 or offset >= len(self.data):
                continue

            # Scan for JSR instructions
            current_offset = offset
            end_offset = min(offset + 500, len(self.data))  # Scan up to 500 bytes

            while current_offset < end_offset:
                opcode = self.data[current_offset]

                # JSR absolute (0x20)
                if opcode == self.JSR_OPCODE and current_offset + 2 < len(self.data):
                    target_low = self.data[current_offset + 1]
                    target_high = self.data[current_offset + 2]
                    target_addr = target_low | (target_high << 8)

                    # Record this subroutine call
                    caller_addr = self.load_addr + current_offset
                    discovered.add(target_addr)

                    # Create or get subroutine objects
                    if target_addr not in self.subroutines:
                        self.subroutines[target_addr] = Subroutine(target_addr)
                    if caller_addr not in self.subroutines:
                        self.subroutines[caller_addr] = Subroutine(caller_addr)

                    # Record the call relationship
                    self.subroutines[target_addr].add_caller(caller_addr)
                    self.subroutines[caller_addr].add_call(target_addr)

                    # Add target to analysis queue
                    to_analyze.append((target_addr, depth + 1))

                    current_offset += 3  # JSR is 3 bytes

                # RTS (0x60) - end of subroutine
                elif opcode == self.RTS_OPCODE:
                    break

                else:
                    # Skip to next byte (simplified - real disassembler would use proper lengths)
                    current_offset += 1

        return discovered

    def analyze(self, verbose: int = 0) -> Dict[str, Any]:
        """
        Analyze subroutine calls in the SID file.

        Args:
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with analysis results
        """
        try:
            # Read header and data
            self.header = self._read_sid_header()
            self.data, self.load_addr = self._read_sid_data()

            # Trace from init routine
            init_subs = set()
            if self.header['init_addr'] > 0:
                init_subs = self._trace_subroutines(self.header['init_addr'])

            # Trace from play routine
            play_subs = set()
            if self.header['play_addr'] > 0:
                play_subs = self._trace_subroutines(self.header['play_addr'])

            # Calculate statistics
            total_subroutines = len(self.subroutines)
            init_only = init_subs - play_subs
            play_only = play_subs - init_subs
            shared = init_subs & play_subs

            # Find entry points (subroutines with no callers - likely init/play)
            entry_points = [s for s in self.subroutines.values() if len(s.callers) == 0]

            # Find leaf subroutines (subroutines that don't call others)
            leaf_subs = [s for s in self.subroutines.values() if len(s.calls) == 0]

            # Calculate call depth for each subroutine
            max_depth = 0
            for sub in self.subroutines.values():
                depth = self._calculate_call_depth(sub.address, set())
                if depth > max_depth:
                    max_depth = depth

            result = {
                'success': True,
                'sid_file': self.sid_file,
                'header': self.header,
                'total_subroutines': total_subroutines,
                'init_subroutines': len(init_subs),
                'play_subroutines': len(play_subs),
                'shared_subroutines': len(shared),
                'init_only': len(init_only),
                'play_only': len(play_only),
                'entry_points': len(entry_points),
                'leaf_subroutines': len(leaf_subs),
                'max_call_depth': max_depth,
                'subroutines': self.subroutines,
                'init_set': init_subs,
                'play_set': play_subs,
                'shared_set': shared
            }

            if verbose > 0:
                print(f"  Subroutine trace complete")
                print(f"    Total subroutines:  {total_subroutines}")
                print(f"    Init routines:      {len(init_subs)}")
                print(f"    Play routines:      {len(play_subs)}")
                print(f"    Shared:             {len(shared)}")
                print(f"    Max call depth:     {max_depth}")

            return result

        except Exception as e:
            if verbose > 0:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(f"Subroutine trace failed: {error_msg}")
            return {
                'success': False,
                'error': str(e)
            }

    def _calculate_call_depth(self, addr: int, visited: Set[int]) -> int:
        """
        Calculate the maximum call depth from a subroutine.

        Args:
            addr: Subroutine address
            visited: Set of already visited addresses (prevent cycles)

        Returns:
            Maximum call depth
        """
        if addr in visited:
            return 0  # Cycle detected

        if addr not in self.subroutines:
            return 0

        visited.add(addr)
        sub = self.subroutines[addr]

        if len(sub.calls) == 0:
            return 0  # Leaf subroutine

        max_depth = 0
        for call_addr in sub.calls:
            depth = self._calculate_call_depth(call_addr, visited.copy())
            if depth > max_depth:
                max_depth = depth

        return max_depth + 1

    def generate_report(self, analysis_result: Dict[str, Any], output_file: Path) -> bool:
        """
        Generate a text report of the subroutine trace analysis.

        Args:
            analysis_result: Result from analyze()
            output_file: Output file path for the report

        Returns:
            True if successful, False otherwise
        """
        try:
            if not analysis_result.get('success'):
                return False

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("SID SUBROUTINE CALL TRACE\n")
                f.write("=" * 70 + "\n\n")

                # File information
                f.write("FILE INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"File:        {self.sid_file.name}\n")
                f.write(f"Format:      {analysis_result['header']['magic']}\n")
                f.write(f"Name:        {analysis_result['header']['name']}\n")
                f.write(f"Author:      {analysis_result['header']['author']}\n")
                f.write(f"Init addr:   ${analysis_result['header']['init_addr']:04X}\n")
                f.write(f"Play addr:   ${analysis_result['header']['play_addr']:04X}\n")
                f.write("\n")

                # Subroutine statistics
                f.write("SUBROUTINE STATISTICS\n")
                f.write("-" * 70 + "\n")
                f.write(f"Total subroutines:   {analysis_result['total_subroutines']}\n")
                f.write(f"Init subroutines:    {analysis_result['init_subroutines']}\n")
                f.write(f"Play subroutines:    {analysis_result['play_subroutines']}\n")
                f.write(f"Shared subroutines:  {analysis_result['shared_subroutines']}\n")
                f.write(f"Init-only:           {analysis_result['init_only']}\n")
                f.write(f"Play-only:           {analysis_result['play_only']}\n")
                f.write(f"Entry points:        {analysis_result['entry_points']}\n")
                f.write(f"Leaf subroutines:    {analysis_result['leaf_subroutines']}\n")
                f.write(f"Max call depth:      {analysis_result['max_call_depth']}\n")
                f.write("\n")

                # Call graph
                f.write("CALL GRAPH\n")
                f.write("-" * 70 + "\n")
                f.write(f"{'Address':<10} {'Callers':<10} {'Calls':<10} {'Type'}\n")
                f.write("-" * 70 + "\n")

                # Sort subroutines by address
                sorted_subs = sorted(analysis_result['subroutines'].values(),
                                   key=lambda s: s.address)

                for sub in sorted_subs:
                    # Determine type
                    sub_type = []
                    if sub.address in analysis_result['init_set']:
                        sub_type.append("INIT")
                    if sub.address in analysis_result['play_set']:
                        sub_type.append("PLAY")
                    if len(sub.callers) == 0:
                        sub_type.append("ENTRY")
                    if len(sub.calls) == 0:
                        sub_type.append("LEAF")

                    type_str = ",".join(sub_type) if sub_type else "CODE"

                    f.write(f"${sub.address:04X}      {len(sub.callers):<10} {len(sub.calls):<10} {type_str}\n")

                f.write("\n")

                # Detailed call relationships
                f.write("DETAILED CALL RELATIONSHIPS\n")
                f.write("-" * 70 + "\n")

                for sub in sorted_subs[:20]:  # Limit to first 20 for readability
                    f.write(f"\n${sub.address:04X}:\n")

                    if sub.callers:
                        caller_addrs = ", ".join(f"${addr:04X}" for addr in sorted(sub.callers))
                        f.write(f"  Called by:  {caller_addrs}\n")

                    if sub.calls:
                        call_addrs = ", ".join(f"${addr:04X}" for addr in sorted(sub.calls))
                        f.write(f"  Calls:      {call_addrs}\n")

                    if not sub.callers and not sub.calls:
                        f.write(f"  (No call relationships)\n")

                if len(sorted_subs) > 20:
                    f.write(f"\n... ({len(sorted_subs) - 20} more subroutines not shown)\n")

                f.write("\n")

                f.write("=" * 70 + "\n")
                f.write("End of subroutine trace\n")
                f.write("=" * 70 + "\n")

            return True

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return False


# Convenience function
def trace_subroutines(
    sid_file: Path,
    output_file: Path,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for tracing subroutines in SID files.

    Args:
        sid_file: Path to SID file
        output_file: Path to output report file
        verbose: Verbosity level

    Returns:
        Analysis result dictionary or None on error
    """
    tracer = SubroutineTracer(sid_file)
    result = tracer.analyze(verbose=verbose)

    if result['success']:
        tracer.generate_report(result, output_file)

    return result
