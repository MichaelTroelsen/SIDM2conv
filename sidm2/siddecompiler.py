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
        Enhanced player type detection from disassembly

        Detects:
        - Laxity NewPlayer v21 (original SIDs)
        - SF2 Driver 11 (exported from SID Factory II)
        - SF2 NP20 Driver (NewPlayer v20 driver)
        - JCH NewPlayer variants
        - Rob Hubbard players

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

        # SF2 Driver Detection Patterns
        sf2_patterns = {
            'Driver 11': [
                'DriverCommon',
                'sf2driver',
                '; SID Factory II Driver 11',
                'DRIVER_VERSION = 11'
            ],
            'NP20 Driver': [
                'np20driver',
                'NewPlayer 20 Driver',
                'NP20_',
                'DRIVER_VERSION = 20'
            ],
            'Driver 12': ['DRIVER_VERSION = 12'],
            'Driver 13': ['DRIVER_VERSION = 13'],
            'Driver 14': ['DRIVER_VERSION = 14'],
            'Driver 15': ['DRIVER_VERSION = 15'],
            'Driver 16': ['DRIVER_VERSION = 16'],
        }

        # Check for SF2 drivers first
        content_lower = content.lower()
        for driver_name, patterns in sf2_patterns.items():
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    player_info.type = f"SF2 {driver_name}"
                    # Extract version if found
                    version_match = re.search(r'DRIVER_VERSION\s*=\s*(\d+)', content, re.IGNORECASE)
                    if version_match:
                        player_info.version = version_match.group(1)
                    return player_info  # SF2 drivers are definitive

        # Extract header information for author-based detection
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
        if 'player 21.g5' in content_lower:
            player_info.type = "NewPlayer v21.G5"
            player_info.version = "21.G5"
        elif 'player 21.g4' in content_lower:
            player_info.type = "NewPlayer v21.G4"
            player_info.version = "21.G4"
        elif 'player 21' in content_lower or 'newplayer v21' in content_lower:
            player_info.type = "NewPlayer v21 (Laxity)"
            player_info.version = "21"
        elif 'player 20' in content_lower or 'newplayer v20' in content_lower:
            player_info.type = "NewPlayer v20"
            player_info.version = "20"
        elif 'newplayer' in content_lower:
            player_info.type = "JCH NewPlayer (variant)"

        # Check for common Laxity code patterns
        laxity_patterns = [
            r'lda\s+#\$00\s+sta\s+\$d404',  # Laxity init pattern
            r'ldy\s+#\$07.*bpl\s+.*ldx\s+#\$18',  # Laxity voice init
            r'jsr\s+.*filter.*jsr\s+.*pulse',  # Laxity table processing
        ]

        if player_info.type == "Unknown":
            for pattern in laxity_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    player_info.type = "NewPlayer v21 (Laxity) - pattern match"
                    break

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

    def parse_memory_layout(self, asm_file: Path, player_info: PlayerInfo,
                           tables: Dict[str, TableInfo]) -> List[MemoryRegion]:
        """
        Parse memory layout from disassembly to create visual memory map

        Args:
            asm_file: Path to assembly file
            player_info: Detected player information
            tables: Extracted tables

        Returns:
            List of MemoryRegion objects sorted by address
        """
        regions = []

        if not asm_file.exists():
            return regions

        with open(asm_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Add player code region
        if player_info.memory_start and player_info.memory_end:
            regions.append(MemoryRegion(
                start=player_info.memory_start,
                end=player_info.memory_end,
                type='code',
                name='Player Code'
            ))

        # Add table regions
        for table_name, table in tables.items():
            if table.size:
                regions.append(MemoryRegion(
                    start=table.address,
                    end=table.address + table.size - 1,
                    type='table',
                    name=table.name
                ))
            else:
                # Estimate size if not known
                regions.append(MemoryRegion(
                    start=table.address,
                    end=table.address + 127,  # Estimate
                    type='table',
                    name=f"{table.name} (estimated)"
                ))

        # Look for data sections in disassembly
        data_pattern = re.compile(r'^\s*\$([0-9A-Fa-f]{4}):\s+\.byte', re.MULTILINE)
        for match in data_pattern.finditer(content):
            addr = int(match.group(1), 16)
            # Only add if not overlapping with existing regions
            overlaps = any(r.start <= addr <= r.end for r in regions)
            if not overlaps:
                regions.append(MemoryRegion(
                    start=addr,
                    end=addr + 15,  # Estimate 16 bytes
                    type='data',
                    name='Data block'
                ))

        # Sort by address
        regions.sort(key=lambda r: r.start)

        # Merge adjacent regions of same type
        merged = []
        current = None
        for region in regions:
            if current is None:
                current = region
            elif (current.type == region.type and
                  current.name == region.name and
                  region.start <= current.end + 1):
                # Merge adjacent regions
                current.end = max(current.end, region.end)
            else:
                merged.append(current)
                current = region

        if current:
            merged.append(current)

        return merged

    def generate_memory_map(self, regions: List[MemoryRegion]) -> str:
        """
        Generate visual ASCII memory map from memory regions

        Args:
            regions: List of MemoryRegion objects

        Returns:
            Formatted ASCII memory map string
        """
        if not regions:
            return "No memory regions to visualize"

        lines = []
        lines.append("Memory Layout:")
        lines.append("=" * 70)
        lines.append("")

        # Calculate total range
        min_addr = min(r.start for r in regions)
        max_addr = max(r.end for r in regions)
        total_size = max_addr - min_addr + 1

        # Visual representation
        for region in regions:
            size = region.end - region.start + 1
            name_str = region.name if region.name else region.type
            type_marker = {
                'code': '█',
                'data': '▒',
                'table': '░',
                'variable': '·'
            }.get(region.type, '?')

            # Create visual bar (max 40 chars)
            bar_len = min(40, max(1, int(40 * size / total_size)))
            bar = type_marker * bar_len

            lines.append(f"${region.start:04X}-${region.end:04X} [{bar:40s}] {name_str} ({size} bytes)")

        lines.append("")
        lines.append("Legend: █ Code  ▒ Data  ░ Tables")
        lines.append("=" * 70)

        return '\n'.join(lines)

    def generate_enhanced_report(self,
                                 sid_file: Path,
                                 asm_file: Path,
                                 stdout: str,
                                 tables: Dict[str, TableInfo],
                                 player_info: PlayerInfo,
                                 regions: List[MemoryRegion]) -> str:
        """
        Generate enhanced analysis report with memory maps and structure details

        Args:
            sid_file: Original SID file
            asm_file: Generated assembly file
            stdout: SIDdecompiler output
            tables: Extracted tables
            player_info: Detected player info
            regions: Memory regions

        Returns:
            Formatted enhanced report string
        """
        report = []
        report.append("=" * 70)
        report.append("SIDdecompiler Enhanced Analysis Report")
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

        # Memory layout visualization
        if regions:
            report.append(self.generate_memory_map(regions))
            report.append("")

        # Table information with addresses
        if tables:
            report.append("Detected Tables (with addresses):")
            report.append("-" * 70)

            # Group by type
            by_type = {}
            for table in tables.values():
                table_type = table.type or 'unknown'
                if table_type not in by_type:
                    by_type[table_type] = []
                by_type[table_type].append(table)

            for table_type in sorted(by_type.keys()):
                report.append(f"  {table_type.capitalize()} Tables:")
                for table in sorted(by_type[table_type], key=lambda t: t.address):
                    size_str = f" ({table.size} bytes)" if table.size else ""
                    report.append(f"    ${table.address:04X}: {table.name}{size_str}")
                report.append("")
        else:
            report.append("No tables detected")
            report.append("")

        # Structure summary
        if regions:
            report.append("Structure Summary:")
            report.append(f"  Total regions: {len(regions)}")
            code_regions = [r for r in regions if r.type == 'code']
            table_regions = [r for r in regions if r.type == 'table']
            data_regions = [r for r in regions if r.type == 'data']
            if code_regions:
                total_code = sum(r.end - r.start + 1 for r in code_regions)
                report.append(f"  Code regions: {len(code_regions)} ({total_code} bytes)")
            if table_regions:
                total_tables = sum(r.end - r.start + 1 for r in table_regions)
                report.append(f"  Table regions: {len(table_regions)} ({total_tables} bytes)")
            if data_regions:
                total_data = sum(r.end - r.start + 1 for r in data_regions)
                report.append(f"  Data regions: {len(data_regions)} ({total_data} bytes)")
            report.append("")

        # Statistics from stdout
        report.append("Analysis Statistics:")
        for line in stdout.split('\n'):
            if 'TraceNode' in line or 'pairs' in line or 'operands' in line:
                report.append(f"  {line.strip()}")

        report.append("=" * 70)

        return '\n'.join(report)

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
        regions = self.parse_memory_layout(asm_file, player_info, tables)

        # Generate enhanced report with memory layout
        report = self.generate_enhanced_report(
            sid_file=sid_file,
            asm_file=asm_file,
            stdout=stdout,
            tables=tables,
            player_info=player_info,
            regions=regions
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
