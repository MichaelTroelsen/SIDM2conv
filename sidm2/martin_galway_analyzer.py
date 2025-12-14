"""
Martin Galway player analyzer for extracting music data.

Analyzes Martin Galway format SID files (classic C64 game soundtracks).
Different from Laxity: variable player structure, game-specific data layouts,
mixed RSID/PSID formats.

Phase 1: Foundation - Basic detection and structure analysis
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class MartinGalwayAnalyzer:
    """
    Analyze Martin Galway player format.

    Martin Galway was a legendary C64 composer who created game-specific
    music players. Unlike Laxity's standardized format, Galway's players
    are adapted per-game with variable data layouts.

    Key characteristics:
    - Load addresses: Variable ($0C00, $0D00, $0800-$1FFF, $4000, etc.)
    - Format: Mix of PSID (relocatable) and RSID (autorun)
    - Player size: 2KB-12KB+ (varies per game)
    - Data layout: Game-specific (no standard table locations)
    - Composer: Martin Galway (famous for classics like Arkanoid, Green Beret)
    """

    def __init__(self, sid_path: str = None):
        """Initialize analyzer with optional SID file path."""
        self.sid_path = Path(sid_path) if sid_path else None
        self.player_signature = "Martin_Galway"
        self.confidence = 0.0
        self.analysis_data = {}

        # Track PSID vs RSID format
        self.is_rsid = False
        self.is_psid = False
        self.load_address = 0
        self.init_address = 0
        self.play_address = 0
        self.player_size = 0

    def analyze(self, c64_data: bytes, load_address: int,
                init_address: int, play_address: int) -> Dict[str, Any]:
        """
        Analyze Martin Galway player structure.

        Args:
            c64_data: Raw C64 binary data
            load_address: Load address from PSID header
            init_address: Init routine address
            play_address: Play routine address

        Returns:
            Dictionary with analysis results
        """
        logger.debug(f"Martin Galway: Analyzing structure")
        logger.debug(f"  Load address: ${load_address:04X}")
        logger.debug(f"  Init address: ${init_address:04X}")
        logger.debug(f"  Play address: ${play_address:04X}")
        logger.debug(f"  Data size: {len(c64_data):,} bytes")

        self.load_address = load_address
        self.init_address = init_address
        self.play_address = play_address
        self.player_size = len(c64_data)

        # Detect format (PSID vs RSID)
        self._detect_format()

        # Create analysis result
        self.analysis_data = {
            'format': 'Martin_Galway',
            'is_rsid': self.is_rsid,
            'is_psid': self.is_psid,
            'load_address': load_address,
            'init_address': init_address,
            'play_address': play_address,
            'data_size': len(c64_data),
            'player_size_estimate': self._estimate_player_size(c64_data),
            'confidence': self.confidence,
        }

        logger.info(f"Martin Galway analysis: {self.analysis_data}")
        return self.analysis_data

    def _detect_format(self) -> None:
        """Detect PSID vs RSID format based on addresses."""
        # RSID indicators:
        # - Init address is 0x0000 (autorun)
        # - Play address is small (0x0010-0x00FF)
        # - Load address is high (0x0800+)

        if self.init_address == 0x0000:
            self.is_rsid = True
            logger.debug(f"  Format: RSID (autorun, init=$0000)")
        else:
            self.is_psid = True
            logger.debug(f"  Format: PSID (relocatable, init=${self.init_address:04X})")

    def _estimate_player_size(self, c64_data: bytes) -> int:
        """
        Estimate player code size.

        Martin Galway players vary 2KB-12KB+. Use heuristics:
        - Look for large stretches of 0x00 (indicates data section)
        - Look for routine boundaries (RTS at 0x60)
        - Check for table markers
        """
        size_estimate = len(c64_data)

        # Heuristic 1: Find first large zero section (likely data)
        zero_run = 0
        max_code_size = 0

        for i, byte in enumerate(c64_data):
            if byte == 0x00:
                zero_run += 1
                if zero_run > 16:  # 16 consecutive zeros likely = data
                    max_code_size = max(max_code_size, i - zero_run)
            else:
                zero_run = 0

        if max_code_size > 1000:
            size_estimate = max_code_size
            logger.debug(f"  Player size estimate (from zero sections): {size_estimate:,} bytes")

        return size_estimate

    def get_profile(self) -> Dict[str, Any]:
        """Get player profile for converter routing."""
        return {
            'player_type': 'Martin_Galway',
            'is_rsid': self.is_rsid,
            'is_psid': self.is_psid,
            'load_address': self.load_address,
            'init_address': self.init_address,
            'play_address': self.play_address,
            'requires_relocation': self.is_psid,
            'analysis': self.analysis_data,
        }

    @staticmethod
    def detect_galway_player(sid_header: Dict[str, Any],
                            c64_data: bytes = None) -> bool:
        """
        Detect if this is a Martin Galway player based on SID header.

        Uses player-id.exe results or heuristics.

        Args:
            sid_header: PSID/RSID header information
            c64_data: Optional raw C64 data for analysis

        Returns:
            True if appears to be Martin Galway player
        """
        author = sid_header.get('author', '').lower()

        # Check author field for Galway indicators
        galway_indicators = ['martin galway', 'galway', 'm. galway', 'martin g']
        for indicator in galway_indicators:
            if indicator in author:
                logger.debug(f"Martin Galway detected in author: {author}")
                return True

        return False


# Module initialization
logger.debug("martin_galway_analyzer module loaded")
