"""
Enhanced Player Detection System

Provides comprehensive player type identification for SID files including:
- Classic game music players (Rob Hubbard, Martin Galway, etc.)
- SID Factory II drivers (Driver 11, NP20)
- Laxity NewPlayer variants
- Custom and unknown players
"""

import struct
from pathlib import Path
from typing import Dict, Optional, Tuple


class EnhancedPlayerDetector:
    """Enhanced player detection with composer and format recognition"""

    # Known player signatures and patterns
    PLAYER_SIGNATURES = {
        # Laxity NewPlayer v21
        'Laxity': {
            'init_addrs': [0x1000, 0xA000],
            'play_addrs': [0x10A1, 0xA0A1],
            'code_size_range': (700, 1400),
            'confidence': 0.95
        },
        # Driver 11 / SF2
        'Driver11': {
            'init_addrs': [0x0D7E],
            'play_addrs': [0x0D7E, 0x0D81],
            'code_size_range': (200, 300),
            'confidence': 0.95
        },
        # JCH NewPlayer v20 / NP20
        'NP20': {
            'init_addrs': [0x0F00, 0x1000],
            'play_addrs': [0x1000, 0x10A0],
            'code_size_range': (500, 700),
            'confidence': 0.85
        },
        # Rob Hubbard (classic C64 game music)
        'Rob_Hubbard': {
            'init_addrs': [0x0800, 0x0900, 0x0A00],
            'authors': ['rob hubbard', 'hubbard'],
            'confidence': 0.80
        },
        # Martin Galway
        'Martin_Galway': {
            'init_addrs': [0x0C00, 0x0D00],
            'authors': ['martin galway', 'galway'],
            'confidence': 0.80
        },
        # JCH (John C. Hardin)
        'JCH': {
            'init_addrs': [0x1000, 0x1100],
            'authors': ['jch', 'john c. hardin', 'john hardin'],
            'confidence': 0.75
        },
        # Generic/Unknown modern format
        'Generic_Modern': {
            'init_addrs': [0x1000, 0x1100, 0x1200],
            'play_addrs': [0x1000, 0x1100, 0x1200],
            'confidence': 0.50
        },
    }

    def __init__(self):
        """Initialize detector"""
        pass

    def detect_player(self, sid_file: Path) -> Tuple[str, float]:
        """
        Detect player type from SID file

        Args:
            sid_file: Path to SID file

        Returns:
            Tuple of (player_name, confidence)
        """
        if not sid_file.exists():
            return "Unknown", 0.0

        try:
            # Parse PSID header
            with open(sid_file, 'rb') as f:
                header = f.read(126)

            if len(header) < 114:
                return "Unknown", 0.0

            # Extract metadata
            magic = header[0:4].decode('ascii', errors='ignore')
            if magic not in ['PSID', 'RSID']:
                return "Unknown", 0.0

            init_addr = struct.unpack('>H', header[10:12])[0]
            play_addr = struct.unpack('>H', header[12:14])[0]
            name = header[16:48].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            author = header[48:80].split(b'\x00')[0].decode('ascii', errors='ignore').strip()

            # Try detection methods in order of confidence
            # 1. Check code size (highest confidence)
            player, confidence = self._detect_by_code_size(sid_file, init_addr)
            if confidence >= 0.90:
                return player, confidence

            # 2. Check signatures
            player, confidence = self._detect_by_signature(init_addr, play_addr, author)
            if confidence >= 0.75:
                return player, confidence

            # 3. Check author/composer
            player, confidence = self._detect_by_composer(name, author)
            if confidence >= 0.70:
                return player, confidence

            # 4. Check address patterns
            player, confidence = self._detect_by_address(init_addr, play_addr)
            if confidence >= 0.60:
                return player, confidence

            return "Unknown", 0.0

        except Exception as e:
            return "Unknown", 0.0

    def _detect_by_code_size(self, sid_file: Path, init_addr: int) -> Tuple[str, float]:
        """Detect by disassembly code size"""
        try:
            # Try to use SIDdecompiler if available
            from sidm2.siddecompiler import SIDdecompilerAnalyzer
            analyzer = SIDdecompilerAnalyzer()
            player, conf = analyzer.detect_player(str(sid_file))
            if player != "Unknown":
                return player, conf
        except:
            pass
        return "Unknown", 0.0

    def _detect_by_signature(self, init_addr: int, play_addr: int, author: str) -> Tuple[str, float]:
        """Detect by init/play address signatures"""
        author_lower = author.lower() if author else ""

        for player_name, sig in self.PLAYER_SIGNATURES.items():
            # Check init address match
            if 'init_addrs' in sig and init_addr in sig['init_addrs']:
                # Check play address if available
                if 'play_addrs' in sig:
                    if play_addr in sig['play_addrs']:
                        return player_name, sig.get('confidence', 0.5)
                else:
                    # Init match is sufficient
                    return player_name, sig.get('confidence', 0.5) * 0.8

            # Check author match
            if 'authors' in sig:
                for author_pattern in sig['authors']:
                    if author_pattern in author_lower:
                        return player_name, sig.get('confidence', 0.5) * 0.9

        return "Unknown", 0.0

    def _detect_by_composer(self, name: str, author: str) -> Tuple[str, float]:
        """Detect by composer/author name"""
        name_lower = (name or "").lower()
        author_lower = (author or "").lower()

        composer_patterns = {
            'Rob_Hubbard': ['rob hubbard', 'hubbard', 'r.hubbard'],
            'Martin_Galway': ['martin galway', 'galway', 'm.galway'],
            'JCH': ['jch', 'john c. hardin', 'john hardin'],
            'Jeroen_Tel': ['jeroen tel', 'tel'],
            'Maniacs_Of_Noise': ['maniacs', 'mon'],
            'Chris_Huelsbeck': ['huelsbeck', 'chris'],
            'Tal_Asada': ['tal asada', 'asada'],
        }

        for player_name, patterns in composer_patterns.items():
            for pattern in patterns:
                if pattern in name_lower or pattern in author_lower:
                    return player_name, 0.80

        return "Unknown", 0.0

    def _detect_by_address(self, init_addr: int, play_addr: int) -> Tuple[str, float]:
        """Detect by address patterns"""
        # Laxity pattern: init = play or play = init + 0xA1
        if init_addr in [0x1000, 0xA000]:
            if play_addr in [init_addr, init_addr + 0xA1]:
                return "Laxity", 0.70

        # Driver 11 pattern
        if init_addr == 0x0D7E:
            return "Driver11", 0.75

        # Classic game music pattern (0x0800-0x0D00)
        if 0x0800 <= init_addr <= 0x0D00:
            return "Classic_Game_Music", 0.50

        # Modern format pattern (0x1000+)
        if init_addr >= 0x1000:
            return "Modern_Player", 0.40

        return "Unknown", 0.0


def get_player_id(player_name: str, instance: int = 1) -> str:
    """
    Generate player-ID from player name

    Args:
        player_name: Player type name
        instance: Instance number for multiple instances

    Returns:
        Player-ID string (e.g., "LAXITY_001", "ROB_HUBBARD_001")
    """
    if not player_name or player_name == "Unknown":
        return "UNKNOWN_001"

    # Normalize name
    normalized = player_name.upper().replace(' ', '_').replace('.', '')

    # Format with instance number
    return f"{normalized}_{instance:03d}"
