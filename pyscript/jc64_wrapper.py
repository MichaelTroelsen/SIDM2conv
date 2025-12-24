"""
JC64 Python Wrapper

Provides Python interface to JC64 Java-based C64 emulator and disassembler.
Supports player detection, SID file analysis, and disassembly.

Usage:
    from pyscript.jc64_wrapper import JC64Wrapper

    jc64 = JC64Wrapper()
    player = jc64.identify_player("music.sid")
    print(f"Detected player: {player}")
"""

import subprocess
import tempfile
import json
from pathlib import Path
from typing import Optional, Dict, List


class JC64Wrapper:
    """Python wrapper for JC64 Java components."""

    def __init__(self, jar_path: Optional[str] = None):
        """
        Initialize JC64 wrapper.

        Args:
            jar_path: Path to JC64.jar. If None, searches common locations.
        """
        if jar_path is None:
            jar_path = self._find_jc64_jar()

        self.jar_path = Path(jar_path)
        if not self.jar_path.exists():
            raise FileNotFoundError(f"JC64 JAR not found: {jar_path}")

    def _find_jc64_jar(self) -> str:
        """Find JC64.jar in common locations."""
        common_paths = [
            # Windows downloads
            Path("C:/Users/mit/Downloads/jc64dis-win64/win64/JC64.jar"),
            Path("C:/Users/mit/Downloads/jc64dis-java/JC64.jar"),
            # Current directory
            Path("JC64.jar"),
            Path("jc64/JC64.jar"),
            # Relative to SIDM2
            Path(__file__).parent.parent / "jc64/JC64.jar",
        ]

        for path in common_paths:
            if path.exists():
                return str(path)

        raise FileNotFoundError(
            "JC64.jar not found. Please specify jar_path or install JC64."
        )

    def parse_psid_header(self, sid_file: Path) -> Dict:
        """
        Parse PSID/RSID header using JC64's PSID parser.

        Args:
            sid_file: Path to SID file

        Returns:
            Dictionary with PSID metadata (title, author, init/play addresses, etc.)
        """
        # For now, implement basic Python PSID parser
        # TODO: Create Java wrapper class for direct PSID parsing

        with open(sid_file, 'rb') as f:
            data = f.read()

        if len(data) < 0x80:
            raise ValueError("File too small to be valid PSID/RSID")

        # Check magic bytes
        magic = data[0:4].decode('ascii', errors='ignore')
        if magic not in ['PSID', 'RSID']:
            raise ValueError(f"Invalid magic bytes: {magic}")

        # Parse version
        version = (data[4] << 8) | data[5]

        # Parse data offset
        data_offset = (data[6] << 8) | data[7]

        # Parse addresses (little-endian for load, big-endian for init/play)
        load_addr = data[9] + (data[8] * 256)
        init_addr = (data[10] << 8) | data[11]
        play_addr = (data[12] << 8) | data[13]

        # Song information
        song_count = (data[14] << 8) | data[15]
        start_song = (data[16] << 8) | data[17]

        # Metadata strings (null-terminated)
        title = data[0x16:0x36].split(b'\x00')[0].decode('ascii', errors='ignore')
        author = data[0x36:0x56].split(b'\x00')[0].decode('ascii', errors='ignore')
        copyright = data[0x56:0x76].split(b'\x00')[0].decode('ascii', errors='ignore')

        return {
            'magic': magic,
            'version': version,
            'data_offset': data_offset,
            'load_addr': load_addr,
            'init_addr': init_addr,
            'play_addr': play_addr,
            'song_count': song_count,
            'start_song': start_song,
            'title': title.strip(),
            'author': author.strip(),
            'copyright': copyright.strip(),
            'file_size': len(data)
        }

    def identify_player(self, sid_file: Path) -> str:
        """
        Identify SID player using JC64's SIDId algorithm.

        NOTE: This requires a custom Java wrapper class to be created.
        For now, returns basic detection based on PSID header.

        Args:
            sid_file: Path to SID file

        Returns:
            Player name string, or "Unknown" if not detected
        """
        # Parse header to get init address
        try:
            header = self.parse_psid_header(sid_file)
            init_addr = header['init_addr']

            # Basic Laxity detection (init at $1000)
            if init_addr == 0x1000:
                return "Laxity NewPlayer (tentative - based on init address)"
            else:
                return f"Unknown player (init: ${init_addr:04X})"

        except Exception as e:
            return f"Detection error: {e}"

    def disassemble_sid(self, sid_file: Path, output_file: Optional[Path] = None) -> str:
        """
        Disassemble SID file using FileDasm.

        NOTE: FileDasm has a known bug (ArrayIndexOutOfBoundsException at line 153).
        This method documents the issue for future reference.

        Args:
            sid_file: Path to input SID file
            output_file: Optional path for output assembly file

        Returns:
            Assembly code as string

        Raises:
            RuntimeError: If disassembly fails
        """
        if output_file is None:
            output_file = Path(tempfile.mktemp(suffix=".asm"))

        cmd = [
            "java",
            "-cp", str(self.jar_path),
            "sw_emulator.software.FileDasm",
            "-en",
            str(sid_file),
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_msg = result.stderr
            if "ArrayIndexOutOfBoundsException" in error_msg:
                raise RuntimeError(
                    "JC64 FileDasm has a known bug (ArrayIndexOutOfBoundsException). "
                    "This is a JC64 issue at FileDasm.java:153. "
                    "Consider using the GUI version or patching the source."
                )
            else:
                raise RuntimeError(f"JC64 disassembly failed: {error_msg}")

        if output_file.exists():
            return output_file.read_text()
        else:
            raise RuntimeError("Disassembly output file not created")

    def get_info(self) -> Dict:
        """Get information about JC64 wrapper configuration."""
        return {
            'jar_path': str(self.jar_path),
            'jar_exists': self.jar_path.exists(),
            'jar_size': self.jar_path.stat().st_size if self.jar_path.exists() else 0,
            'version': 'JC64 3.0 (2025-04-21)',
            'capabilities': [
                'PSID header parsing (Python)',
                'Player detection (basic)',
                'Disassembly (FileDasm - has known bug)',
            ],
            'status': 'Operational (with limitations)'
        }


def test_wrapper():
    """Test JC64 wrapper functionality."""
    print("Testing JC64 Python Wrapper...")
    print("-" * 60)

    try:
        wrapper = JC64Wrapper()
        print(f"[OK] JC64 wrapper initialized")
        print(f"  JAR: {wrapper.jar_path}")

        # Test with a Laxity SID file
        test_sid = Path("Laxity/Broware.sid")
        if not test_sid.exists():
            test_sid = Path("Laxity/Stinsens_Last_Night_of_89.sid")

        if test_sid.exists():
            print(f"\n[OK] Test file found: {test_sid}")

            # Test PSID header parsing
            print(f"\n--- PSID Header Parsing ---")
            header = wrapper.parse_psid_header(test_sid)
            print(f"  Magic: {header['magic']}")
            print(f"  Version: {header['version']}")
            print(f"  Title: {header['title']}")
            print(f"  Author: {header['author']}")
            print(f"  Copyright: {header['copyright']}")
            print(f"  Load: ${header['load_addr']:04X}")
            print(f"  Init: ${header['init_addr']:04X}")
            print(f"  Play: ${header['play_addr']:04X}")
            print(f"  Songs: {header['song_count']}")

            # Test player detection
            print(f"\n--- Player Detection ---")
            player = wrapper.identify_player(test_sid)
            print(f"  Detected: {player}")

            # Test disassembly (will likely fail due to bug)
            print(f"\n--- Disassembly Test ---")
            try:
                asm = wrapper.disassemble_sid(test_sid)
                print(f"  [OK] Disassembly succeeded ({len(asm)} bytes)")
            except RuntimeError as e:
                print(f"  [FAIL] Disassembly failed (expected): {e}")

        else:
            print(f"\n[WARN] No test SID files found")

        # Show wrapper info
        print(f"\n--- Wrapper Info ---")
        info = wrapper.get_info()
        for key, value in info.items():
            if isinstance(value, list):
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value}")

        print(f"\n" + "=" * 60)
        print(f"JC64 Wrapper Test Complete")
        print(f"=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_wrapper()
