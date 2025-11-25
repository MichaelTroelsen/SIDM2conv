"""
Laxity NewPlayer v21 analyzer implementation.

This wraps the existing LaxityPlayerAnalyzer with the profile-based
architecture for multi-player support.
"""

import logging
from typing import List

from ..player_base import BasePlayerAnalyzer, PlayerProfile, PlayerRegistry, get_laxity_profile
from ..models import ExtractedData, PSIDHeader
from ..laxity_analyzer import LaxityPlayerAnalyzer

logger = logging.getLogger(__name__)

# Create the Laxity profile
LAXITY_PROFILE = get_laxity_profile()


class LaxityPlayerAnalyzerV2(BasePlayerAnalyzer):
    """
    Laxity NewPlayer analyzer using the profile system.

    This wraps the existing LaxityPlayerAnalyzer to maintain backward
    compatibility while supporting the new multi-player architecture.
    """

    def __init__(self, c64_data: bytes, load_address: int, header: PSIDHeader):
        """Initialize the Laxity analyzer."""
        super().__init__(c64_data, load_address, header)

        # Create the underlying analyzer
        self._analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)

    @classmethod
    def get_profile(cls) -> PlayerProfile:
        """Return the Laxity player profile."""
        return LAXITY_PROFILE

    def extract_music_data(self) -> ExtractedData:
        """
        Extract music data using the underlying Laxity analyzer.

        Returns:
            ExtractedData with all extracted components
        """
        return self._analyzer.extract_music_data()

    def validate_extraction(self, data: ExtractedData) -> List[str]:
        """
        Validate extracted data and return warnings.

        Args:
            data: Extracted data to validate

        Returns:
            List of warning messages
        """
        warnings = []

        # Use profile values for validation
        profile = self.profile

        # Check sequences
        max_seqs = len(data.sequences) if data.sequences else 0
        for i, orderlist in enumerate(data.orderlists):
            for j, (trans, seq_idx) in enumerate(orderlist):
                if seq_idx >= max_seqs:
                    warnings.append(
                        f"Orderlist {i} entry {j}: invalid seq index {seq_idx}"
                    )

        # Check instruments
        for i, instr in enumerate(data.instruments):
            if len(instr) < 7:
                continue

            # Check table pointers against profile limits
            pulse_ptr = instr[5]
            filter_ptr = instr[4]

            # Pulse table bytes (from extraction)
            pulse_bytes = len(data.pulsetable) if data.pulsetable else 0
            filter_bytes = len(data.filtertable) if data.filtertable else 0

            if pulse_ptr > pulse_bytes and pulse_ptr < 128:
                warnings.append(
                    f"Instrument {i}: pulse_ptr {pulse_ptr} exceeds pulse table bytes {pulse_bytes}"
                )

            if filter_ptr > filter_bytes and filter_ptr < 128:
                warnings.append(
                    f"Instrument {i}: filter_ptr {filter_ptr} exceeds filter table bytes {filter_bytes}"
                )

        return warnings


# Register the Laxity analyzer as the default
PlayerRegistry.register(LaxityPlayerAnalyzerV2, is_default=True)
