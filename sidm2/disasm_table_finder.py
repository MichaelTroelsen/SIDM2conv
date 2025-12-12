"""
Extract table addresses from 6502 disassembly.

This module parses disassembled 6502 code to find table addresses by analyzing
indexed addressing modes (LDA/STA with ,X or ,Y).
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Set
import logging

logger = logging.getLogger(__name__)


def disassemble_sid(sid_path: str) -> str:
    """Generate disassembly of SID file using our disassembler.

    Args:
        sid_path: Path to SID file

    Returns:
        Disassembly text
    """
    try:
        # Call disassemble_sid.py as subprocess
        result = subprocess.run(
            ['python', 'scripts/disassemble_sid.py', sid_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to disassemble {sid_path}: {e}")
        logger.error(f"Output: {e.output}")
        return ""
    except Exception as e:
        logger.error(f"Failed to disassemble {sid_path}: {e}")
        return ""


def extract_table_references(disasm: str) -> Dict[int, int]:
    """Extract all table address references from disassembly.

    Looks for indexed addressing patterns like:
    - LDA $ADDR,X
    - LDA $ADDR,Y
    - STA $ADDR,X
    - STA $ADDR,Y

    Args:
        disasm: Disassembly text

    Returns:
        Dict mapping address -> reference count
    """
    # Pattern to match indexed addressing
    # Example: "$104B  B9 9F 19      LDA    $199f,Y"
    # Format: $ADDR  BYTES         INSTRUCTION  $TARGET,X|Y
    pattern = r'\$([0-9A-Fa-f]{4})\s+([0-9A-Fa-f]{2}\s+){1,3}\s*(LDA|STA|LDX|LDY|STX|STY)\s+\$([0-9A-Fa-f]{4}),([XY])'

    table_refs = {}

    for line in disasm.split('\n'):
        match = re.search(pattern, line)
        if match:
            table_addr = int(match.group(4), 16)  # group(4) is now the target address

            # Only count addresses in typical music data range ($1600-$1B00)
            if 0x1600 <= table_addr <= 0x1B00:
                table_refs[table_addr] = table_refs.get(table_addr, 0) + 1

    return table_refs


def cluster_addresses(addresses: List[int], max_gap: int = 32) -> List[Tuple[int, int]]:
    """Cluster addresses into contiguous regions.

    Args:
        addresses: List of addresses
        max_gap: Maximum gap between addresses to consider them in same cluster

    Returns:
        List of (start_addr, end_addr) tuples
    """
    if not addresses:
        return []

    addresses = sorted(addresses)
    clusters = []
    start = addresses[0]
    prev = addresses[0]

    for addr in addresses[1:]:
        if addr - prev > max_gap:
            # Start new cluster
            clusters.append((start, prev))
            start = addr
        prev = addr

    # Add final cluster
    clusters.append((start, prev))

    return clusters


def identify_table_type(addr: int, known_addresses: Dict[str, int]) -> str:
    """Identify table type based on address proximity to known tables.

    Args:
        addr: Address to identify
        known_addresses: Dict of known table addresses

    Returns:
        Table type name or "unknown"
    """
    # Check for exact match
    for name, known_addr in known_addresses.items():
        if addr == known_addr:
            return name

    # Check for proximity (within 16 bytes might be same table)
    for name, known_addr in known_addresses.items():
        if abs(addr - known_addr) < 16:
            return f"{name}_region"

    return "unknown"


def find_tables_in_disassembly(sid_path: str) -> Dict[str, Tuple[int, int, int]]:
    """Find all music data tables by analyzing disassembly.

    Args:
        sid_path: Path to SID file

    Returns:
        Dict mapping table_name -> (start_addr, end_addr, length)
    """
    logger.info(f"Analyzing disassembly to find table addresses...")

    # Generate disassembly
    disasm = disassemble_sid(sid_path)
    if not disasm:
        logger.warning("Failed to generate disassembly")
        return {}

    # Extract all table references
    table_refs = extract_table_references(disasm)

    if not table_refs:
        logger.warning("No table references found in disassembly")
        return {}

    # Sort by reference count to find most-accessed tables
    sorted_refs = sorted(table_refs.items(), key=lambda x: x[1], reverse=True)

    logger.info(f"Found {len(sorted_refs)} unique table references")
    for addr, count in sorted_refs[:10]:
        logger.debug(f"  ${addr:04X}: {count} references")

    # Extract unique addresses
    addresses = [addr for addr, _ in sorted_refs]

    # Cluster addresses to find table regions
    clusters = cluster_addresses(addresses, max_gap=64)

    tables = {}
    for idx, (start, end) in enumerate(clusters):
        length = end - start + 1
        table_name = f"table_{idx}_${start:04X}"
        tables[table_name] = (start, end, length)
        logger.debug(f"Cluster {idx}: ${start:04X}-${end:04X} ({length} bytes)")

    return tables
