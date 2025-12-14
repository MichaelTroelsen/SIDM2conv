"""
SIDdecompiler Wrapper Module

Provides Python interface to SIDdecompiler.exe for automated player analysis,
table extraction, and memory layout visualization.

Based on SIDdecompiler 0.8 by Stein Pedersen/Prosonix
"""

import subprocess
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MemoryRegion:
    """Represents a memory region in the SID player"""
    start: int
    end: int
    type: str  # 'code', 'data', 'variable', 'table'
    name: Optional[str] = None

    def __repr__(self):
        name_str = f" ({self.name})" if self.name else ""
        return f"${self.start:04X}-${self.end:04X}: {self.type}{name_str}"


@dataclass
class TableInfo:
    """Information about a detected table"""
    name: str
    address: int
    size: Optional[int] = None
    type: Optional[str] = None  # 'filter', 'pulse', 'instrument', 'wave', etc.

    def __repr__(self):
        size_str = f" ({self.size} bytes)" if self.size else ""
        return f"{self.name} @ ${self.address:04X}{size_str}"


@dataclass
class PlayerInfo:
    """Detected player information"""
    type: str
    version: Optional[str] = None
    init_addr: Optional[int] = None
    play_addr: Optional[int] = None
    load_addr: Optional[int] = None
    memory_start: Optional[int] = None
    memory_end: Optional[int] = None

    def __repr__(self):
        version_str = f" v{self.version}" if self.version else ""
        return f"{self.type}{version_str}"


class SIDdecompilerAnalyzer:
    """
    Wrapper for SIDdecompiler.exe with analysis capabilities

    Provides:
    - Automated disassembly with configurable options
    - Table address extraction
    - Memory layout analysis
    - Player type detection
    - Structure reports
    """

    def __init__(self, siddecompiler_path: str = "tools/SIDdecompiler.exe"):
        """
        Initialize SIDdecompiler wrapper

        Args:
            siddecompiler_path: Path to SIDdecompiler.exe
        """
        self.exe = Path(siddecompiler_path)

        if not self.exe.exists():
            raise FileNotFoundError(f"SIDdecompiler not found at {self.exe}")

    def analyze(self,
                sid_file: Path,
                output_dir: Path,
                reloc_addr: int = 0x1000,
                ticks: int = 3000,
                verbose: int = 2,
                create_prg: bool = False,
                relocate_zp: bool = False) -> Dict:
        """
        Run SIDdecompiler analysis on a SID file

        Args:
            sid_file: Path to SID file
            output_dir: Directory for output files
            reloc_addr: Relocation address (default: $1000)
            ticks: Number of play routine calls (default: 3000 = 60s at 50Hz)
            verbose: Verbosity level 0-2 (default: 2)
            create_prg: Generate runnable PRG file (default: False)
            relocate_zp: Create labels for ZP addresses (default: False)

        Returns:
            Dictionary with analysis results:
            - 'asm_file': Path to generated assembly
            - 'success': True if successful
            - 'stdout': Command output
            - 'stderr': Error output
            - 'returncode': Process return code
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        sid_file = Path(sid_file)
        output_asm = output_dir / f"{sid_file.stem}_siddecompiler.asm"

        # Build command
        cmd = [
            str(self.exe),
            str(sid_file),
            "-o", str(output_asm),
            "-a", f"{reloc_addr:04x}",
            "-t", str(ticks),
            "-v", str(verbose)
        ]

        if create_prg:
            cmd.append("-p")

        if relocate_zp:
            cmd.append("-z")

        # Run SIDdecompiler
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                'asm_file': output_asm,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'asm_file': output_asm,
                'success': False,
                'stdout': '',
                'stderr': 'SIDdecompiler timed out after 60 seconds',
                'returncode': -1
            }

        except Exception as e:
            return {
                'asm_file': output_asm,
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }

    def extract_tables(self, asm_file: Path) -> Dict[str, TableInfo]:
        """
        Extract table addresses from disassembly

        Args:
            asm_file: Path to assembly file

        Returns:
            Dictionary mapping table names to TableInfo objects
        """
        tables = {}

        if not asm_file.exists():
            return tables

        with open(asm_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Common table name patterns
        table_patterns = {
            'filter': r'(filt|filter)',
            'pulse': r'(puls|pulse)',
            'instrument': r'(instr|instrument|sound)',
            'wave': r'(wave|arp|waveform)',
            'note': r'(note|freq)',
            'speed': r'(speed|tempo)',
            'voice': r'(voice|track)',
            'sequence': r'(seq|sequence)',
            'supertab': r'(super|command)',
        }

        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Look for label definitions with addresses
            # Format: "label = $1234" or "label: lda #$00"

            # Pattern 1: label = $address
            match = re.match(r'^(\w+)\s*=\s*\$([0-9a-fA-F]{4})', line)
            if match:
                label = match.group(1).lower()
                addr = int(match.group(2), 16)

                # Check if label matches known table patterns
                for table_type, pattern in table_patterns.items():
                    if re.search(pattern, label, re.IGNORECASE):
                        tables[label] = TableInfo(
                            name=label,
                            address=addr,
                            type=table_type
                        )
                        break

            # Pattern 2: label: (with address in previous line or same line)
            match = re.match(r'^(\w+):', line)
            if match:
                label = match.group(1).lower()

                # Try to find address in this line or previous lines
                addr_match = re.search(r'\$([0-9a-fA-F]{4})', line)
                if not addr_match and i > 0:
                    addr_match = re.search(r'\$([0-9a-fA-F]{4})', lines[i-1])

                if addr_match:
                    addr = int(addr_match.group(1), 16)

                    for table_type, pattern in table_patterns.items():
                        if re.search(pattern, label, re.IGNORECASE):
                            tables[label] = TableInfo(
                                name=label,
                                address=addr,
                                type=table_type
                            )
                            break

        return tables

    def parse_memory_map(self, stdout: str) -> List[MemoryRegion]:
        """
        Parse memory access map from SIDdecompiler output

        Args:
            stdout: SIDdecompiler stdout output

        Returns:
            List of MemoryRegion objects
        """
        regions = []

        # Find the memory map section
        lines = stdout.split('\n')
        in_map = False

        for line in lines:
            # Start of map
            if 'Emulated memory access map' in line:
                in_map = True
                continue

            # End of map
            if in_map and 'TraceNode stats' in line:
                break

            # Parse map line: "$1000: xoo???xoxooxoxoxox..."
            if in_map and line.startswith('$'):
                match = re.match(r'\$([0-9a-fA-F]{4}):\s*(.+)', line)
                if match:
                    start_addr = int(match.group(1), 16)
                    access_map = match.group(2).strip()

                    # Each character represents one byte
                    for i, char in enumerate(access_map):
                        addr = start_addr + i

                        # Determine region type from access pattern
                        if char == 'x':
                            region_type = 'code'
                        elif char == 'r':
                            region_type = 'data'
                        elif char in ['+', 'w']:
                            region_type = 'variable'
                        elif char == 'o':
                            region_type = 'operand'
                        elif char == '?':
                            region_type = 'unused'
                        else:
                            region_type = 'mixed'

                        # Could merge consecutive regions of same type
                        # For now, store individual bytes
                        # (optimization for later)

        # Merge consecutive regions of same type
        regions = self._merge_regions(regions)

        return regions

    def _merge_regions(self, regions: List[MemoryRegion]) -> List[MemoryRegion]:
        """Merge consecutive memory regions of the same type"""
        if not regions:
            return []

        merged = []
        current = regions[0]

        for next_region in regions[1:]:
            if (next_region.type == current.type and
                next_region.start == current.end + 1):
                # Extend current region
                current = MemoryRegion(
                    start=current.start,
                    end=next_region.end,
                    type=current.type,
                    name=current.name
                )
            else:
                # Different type or gap, save current and start new
                merged.append(current)
                current = next_region

        merged.append(current)
        return merged

    def detect_player(self, asm_file: Path, stdout: str = '') -> PlayerInfo:
        """
        Detect player type from disassembly

        Args:
            asm_file: Path to assembly file
            stdout: SIDdecompiler stdout (optional)

        Returns:
            PlayerInfo object with detected information
        """
        player_info = PlayerInfo(type="Unknown")

        if not asm_file.exists():
            return player_info

        with open(asm_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Extract header information
        for line in content.split('\n')[:20]:  # Check first 20 lines
            if 'Name:' in line:
                pass  # Could extract name
            if 'Author:' in line:
                author = line.split('Author:')[1].strip()
                # Detect player by author
                if 'Laxity' in author or 'Petersen' in author:
                    player_info.type = "NewPlayer v21 (Laxity)"
                elif 'JCH' in author or 'Glover' in author:
                    player_info.type = "JCH NewPlayer"
                elif 'Hubbard' in author:
                    player_info.type = "Rob Hubbard Player"

        # Look for player signatures in code
        content_lower = content.lower()

        if 'player 21.g5' in content_lower:
            player_info.type = "NewPlayer v21.G5"
            player_info.version = "21.G5"
        elif 'player 21.g4' in content_lower:
            player_info.type = "NewPlayer v21.G4"
            player_info.version = "21.G4"
        elif 'player 20' in content_lower:
            player_info.type = "NewPlayer v20"
            player_info.version = "20"
        elif 'newplayer' in content_lower:
            player_info.type = "JCH NewPlayer (variant)"

        # Extract addresses from stdout
        if stdout:
            for line in stdout.split('\n'):
                if 'Load address:' in line:
                    match = re.search(r'\$([0-9a-fA-F]{4})', line)
                    if match:
                        player_info.load_addr = int(match.group(1), 16)

                if 'Init address:' in line:
                    match = re.search(r'\$([0-9a-fA-F]{4})', line)
                    if match:
                        player_info.init_addr = int(match.group(1), 16)

                if 'Play address:' in line:
                    match = re.search(r'\$([0-9a-fA-F]{4})', line)
                    if match:
                        player_info.play_addr = int(match.group(1), 16)

                if 'Start:' in line and 'End:' in line:
                    matches = re.findall(r'\$([0-9a-fA-F]{4})', line)
                    if len(matches) >= 2:
                        player_info.memory_start = int(matches[0], 16)
                        player_info.memory_end = int(matches[1], 16)

        return player_info

    def generate_report(self,
                       sid_file: Path,
                       asm_file: Path,
                       stdout: str,
                       tables: Dict[str, TableInfo],
                       player_info: PlayerInfo) -> str:
        """
        Generate analysis report

        Args:
            sid_file: Original SID file
            asm_file: Generated assembly file
            stdout: SIDdecompiler output
            tables: Extracted tables
            player_info: Detected player info

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 70)
        report.append("SIDdecompiler Analysis Report")
        report.append("=" * 70)
        report.append(f"File: {sid_file.name}")
        report.append(f"Output: {asm_file.name}")
        report.append("")

        # Player information
        report.append("Player Information:")
        report.append(f"  Type: {player_info.type}")
        if player_info.version:
            report.append(f"  Version: {player_info.version}")
        if player_info.load_addr is not None:
            report.append(f"  Load Address: ${player_info.load_addr:04X}")
        if player_info.init_addr is not None:
            report.append(f"  Init Address: ${player_info.init_addr:04X}")
        if player_info.play_addr is not None:
            report.append(f"  Play Address: ${player_info.play_addr:04X}")
        if player_info.memory_start is not None and player_info.memory_end is not None:
            size = player_info.memory_end - player_info.memory_start + 1
            report.append(f"  Memory Range: ${player_info.memory_start:04X}-${player_info.memory_end:04X} ({size} bytes)")
        report.append("")

        # Table information
        if tables:
            report.append("Detected Tables:")

            # Group by type
            by_type = {}
            for table in tables.values():
                table_type = table.type or 'unknown'
                if table_type not in by_type:
                    by_type[table_type] = []
                by_type[table_type].append(table)

            for table_type in sorted(by_type.keys()):
                report.append(f"  {table_type.capitalize()}:")
                for table in sorted(by_type[table_type], key=lambda t: t.address):
                    size_str = f" ({table.size} bytes)" if table.size else ""
                    report.append(f"    ${table.address:04X}: {table.name}{size_str}")
            report.append("")
        else:
            report.append("No tables detected")
            report.append("")

        # Statistics from stdout
        report.append("Analysis Statistics:")
        for line in stdout.split('\n'):
            if 'TraceNode' in line or 'pairs' in line or 'operands' in line:
                report.append(f"  {line.strip()}")

        report.append("=" * 70)

        return '\n'.join(report)

    def analyze_and_report(self,
                          sid_file: Path,
                          output_dir: Path,
                          reloc_addr: int = 0x1000,
                          ticks: int = 3000) -> Tuple[bool, str]:
        """
        Complete analysis with report generation

        Args:
            sid_file: Path to SID file
            output_dir: Output directory
            reloc_addr: Relocation address
            ticks: Number of play ticks

        Returns:
            Tuple of (success: bool, report: str)
        """
        # Run analysis
        result = self.analyze(
            sid_file=sid_file,
            output_dir=output_dir,
            reloc_addr=reloc_addr,
            ticks=ticks,
            verbose=2
        )

        if not result['success']:
            error_report = f"SIDdecompiler failed:\n{result['stderr']}"
            return False, error_report

        # Extract information
        asm_file = result['asm_file']
        stdout = result['stdout']

        tables = self.extract_tables(asm_file)
        player_info = self.detect_player(asm_file, stdout)

        # Generate report
        report = self.generate_report(
            sid_file=sid_file,
            asm_file=asm_file,
            stdout=stdout,
            tables=tables,
            player_info=player_info
        )

        # Save report
        report_file = output_dir / f"{sid_file.stem}_analysis_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        return True, report


def main():
    """Test the SIDdecompiler wrapper"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python siddecompiler.py <sid_file>")
        sys.exit(1)

    sid_file = Path(sys.argv[1])
    output_dir = Path("output") / sid_file.stem / "analysis"

    analyzer = SIDdecompilerAnalyzer()

    print(f"Analyzing {sid_file.name}...")
    success, report = analyzer.analyze_and_report(
        sid_file=sid_file,
        output_dir=output_dir
    )

    if success:
        print(report)
        print(f"\nAnalysis complete! Files saved to {output_dir}")
    else:
        print(f"Analysis failed: {report}")
        sys.exit(1)


if __name__ == "__main__":
    main()
