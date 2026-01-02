"""Smart Driver Selection System.

Automatically selects the best SF2 driver based on source SID player type.
Implements the SIDM2 Conversion Policy v2.0 (Quality-First approach).

Policy:
- Use best available driver for each player type
- Document driver selection in output
- Ensure SF2 format compatibility
- Validate all outputs

Driver Selection Matrix:
- Laxity NewPlayer v21 → Laxity Driver (99.93% accuracy)
- SF2-exported SID → Driver 11 (100% accuracy)
- NewPlayer 20.G4 → NP20 Driver (70-90% accuracy)
- Others → Driver 11 (safe default)
"""

import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DriverSelection:
    """Driver selection result."""
    driver_name: str              # "laxity", "driver11", "np20"
    driver_file: str              # "sf2driver_laxity_00.prg"
    expected_accuracy: str        # "99.93%", "100%", "70-90%"
    selection_reason: str         # Why this driver was selected
    player_type: str              # Identified player type
    alternative_driver: str = ""  # Alternative driver (not recommended)
    alternative_accuracy: str = "" # Alternative accuracy


class DriverSelector:
    """Selects best SF2 driver based on source SID player type."""

    # Driver file mappings
    DRIVER_FILES = {
        'laxity': 'sf2driver_laxity_00.prg',
        'driver11': 'sf2driver_11.prg',
        'np20': 'sf2driver_np20.prg',
    }

    # Player type → Driver mapping
    PLAYER_MAPPINGS = {
        # SF2-exported files (100% accuracy with Driver 11)
        # CRITICAL: "SidFactory_II/Laxity" = Files created IN SF2 BY author "Laxity"
        #           This is NOT the same as native Laxity NewPlayer v21 format!
        #           "Laxity" here refers to the AUTHOR, not the player format.
        'SidFactory_II/Laxity': 'driver11',  # SF2-exported by author Laxity
        'SidFactory/Laxity': 'driver11',     # Older SF2 version
        'SidFactory_II': 'driver11',         # Any SF2-exported file
        'SidFactory': 'driver11',            # Older SF2 version

        # Native Laxity variants (99.93-100% accuracy with Laxity driver)
        # These are TRUE Laxity NewPlayer v21 format files
        # "Laxity" here refers to the PLAYER FORMAT, not the author
        'Laxity_NewPlayer_V21': 'laxity',    # Native Laxity format
        'Vibrants/Laxity': 'laxity',         # Laxity player by Vibrants
        '256bytes/Laxity': 'laxity',         # Compact Laxity player

        # NewPlayer 20.G4
        'NewPlayer_20': 'np20',
        'NewPlayer_20.G4': 'np20',
        'NP20': 'np20',

        # SF2-exported (preserve Driver 11)
        'SF2_Exported': 'driver11',
        'Driver_11': 'driver11',
    }

    # Expected accuracies
    EXPECTED_ACCURACY = {
        'laxity': '99.93%',
        'driver11_sf2': '100%',     # For SF2-exported files
        'driver11_default': 'Safe default',  # For unknown files
        'np20': '70-90%',
    }

    def __init__(self, player_id_exe: Optional[Path] = None):
        """Initialize driver selector.

        Args:
            player_id_exe: Path to player-id.exe (optional)
        """
        self.player_id_exe = player_id_exe or Path('tools/player-id.exe')

    def identify_player(self, sid_file: Path) -> str:
        """Identify SID player type.

        Args:
            sid_file: Path to SID file

        Returns:
            Player type string or "Unknown"
        """
        if not self.player_id_exe.exists():
            return "Unknown"

        try:
            result = subprocess.run(
                [str(self.player_id_exe), str(sid_file)],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse output
            for line in result.stdout.split('\n'):
                if sid_file.name in line:
                    parts = line.split(sid_file.name)
                    if len(parts) >= 2:
                        player = parts[1].strip()
                        if player and player != "UNIDENTIFIED":
                            return player

            return "Unknown"

        except Exception:
            return "Unknown"

    def select_driver(
        self,
        sid_file: Path,
        player_type: Optional[str] = None,
        force_driver: Optional[str] = None
    ) -> DriverSelection:
        """Select best driver for SID file.

        Args:
            sid_file: Path to SID file
            player_type: Pre-identified player type (optional)
            force_driver: Force specific driver (expert override)

        Returns:
            DriverSelection with complete information
        """
        # Identify player if not provided
        if player_type is None:
            player_type = self.identify_player(sid_file)

        # Handle forced driver (expert override)
        if force_driver:
            return self._handle_forced_driver(force_driver, player_type)

        # Select best driver based on player type
        selected_driver = self._select_best_driver(player_type)

        # Build selection result
        return self._build_selection_result(selected_driver, player_type)

    def _select_best_driver(self, player_type: str) -> str:
        """Select best driver based on player type.

        Args:
            player_type: Identified player type

        Returns:
            Driver name ("laxity", "driver11", "np20")
        """
        # Check direct mapping
        if player_type in self.PLAYER_MAPPINGS:
            return self.PLAYER_MAPPINGS[player_type]

        # Check for partial matches
        player_lower = player_type.lower()

        if 'laxity' in player_lower:
            return 'laxity'

        if 'newplayer' in player_lower and '20' in player_lower:
            return 'np20'

        if 'sf2' in player_lower or 'driver' in player_lower:
            return 'driver11'

        # Default to Driver 11 (safe, universal)
        return 'driver11'

    def _build_selection_result(
        self,
        driver_name: str,
        player_type: str
    ) -> DriverSelection:
        """Build complete driver selection result.

        Args:
            driver_name: Selected driver
            player_type: Identified player type

        Returns:
            Complete DriverSelection
        """
        driver_file = self.DRIVER_FILES.get(driver_name, 'sf2driver_11.prg')

        # Determine expected accuracy
        if driver_name == 'laxity':
            expected_accuracy = self.EXPECTED_ACCURACY['laxity']
            selection_reason = "Laxity-specific driver for maximum accuracy"
            alternative_driver = "Driver 11"
            alternative_accuracy = "1-8%"

        elif driver_name == 'np20':
            expected_accuracy = self.EXPECTED_ACCURACY['np20']
            selection_reason = "NewPlayer 20.G4 specific driver"
            alternative_driver = "Driver 11"
            alternative_accuracy = "~10-20%"

        elif driver_name == 'driver11':
            # Check if SF2-exported
            if 'SF2' in player_type or 'Driver_11' in player_type:
                expected_accuracy = self.EXPECTED_ACCURACY['driver11_sf2']
                selection_reason = "SF2-exported file - preserving Driver 11"
            else:
                expected_accuracy = self.EXPECTED_ACCURACY['driver11_default']
                selection_reason = "Standard SF2 driver for maximum compatibility"

            alternative_driver = ""
            alternative_accuracy = ""

        else:
            expected_accuracy = "Unknown"
            selection_reason = "Unknown player type - using safe default"
            alternative_driver = ""
            alternative_accuracy = ""

        return DriverSelection(
            driver_name=driver_name,
            driver_file=driver_file,
            expected_accuracy=expected_accuracy,
            selection_reason=selection_reason,
            player_type=player_type,
            alternative_driver=alternative_driver,
            alternative_accuracy=alternative_accuracy
        )

    def _handle_forced_driver(
        self,
        force_driver: str,
        player_type: str
    ) -> DriverSelection:
        """Handle forced driver override.

        Args:
            force_driver: Forced driver name
            player_type: Identified player type

        Returns:
            DriverSelection for forced driver
        """
        driver_file = self.DRIVER_FILES.get(force_driver, force_driver)
        expected_accuracy = "User override"
        selection_reason = f"Manual override: --driver {force_driver}"

        return DriverSelection(
            driver_name=force_driver,
            driver_file=driver_file,
            expected_accuracy=expected_accuracy,
            selection_reason=selection_reason,
            player_type=player_type,
            alternative_driver="",
            alternative_accuracy=""
        )

    def format_selection_output(self, selection: DriverSelection) -> str:
        """Format driver selection for console output.

        Args:
            selection: Driver selection result

        Returns:
            Formatted multi-line string
        """
        lines = []
        lines.append("Driver Selection:")
        lines.append(f"  Player Type:     {selection.player_type}")
        lines.append(f"  Selected Driver: {selection.driver_name.upper()} ({selection.driver_file})")
        lines.append(f"  Expected Acc:    {selection.expected_accuracy}")
        lines.append(f"  Reason:          {selection.selection_reason}")

        if selection.alternative_driver:
            lines.append(f"  Alternative:     {selection.alternative_driver} "
                        f"({selection.alternative_accuracy} accuracy - not recommended)")

        return '\n'.join(lines)

    def format_info_file_section(self, selection: DriverSelection) -> str:
        """Format driver selection for info.txt file.

        Args:
            selection: Driver selection result

        Returns:
            Formatted info file section
        """
        lines = []
        lines.append("Driver Selection:")
        lines.append(f"  Selected Driver: {selection.driver_name.upper()} ({selection.driver_file})")
        lines.append(f"  Expected Acc:    {selection.expected_accuracy}")
        lines.append(f"  Reason:          {selection.selection_reason}")

        if selection.alternative_driver:
            lines.append(f"  Alternative:     {selection.alternative_driver} "
                        f"({selection.alternative_accuracy} accuracy)")

        return '\n'.join(lines)

    def create_conversion_info(
        self,
        selection: DriverSelection,
        sid_file: Path,
        output_file: Path,
        sid_metadata: Dict,
        validation_result: Optional[Dict] = None
    ) -> str:
        """Create complete conversion info file content.

        Args:
            selection: Driver selection result
            sid_file: Source SID file
            output_file: Output SF2 file
            sid_metadata: SID file metadata (title, author, etc.)
            validation_result: Validation result (optional)

        Returns:
            Complete info file content
        """
        lines = []
        lines.append("Conversion Information")
        lines.append("=" * 70)
        lines.append(f"File: {sid_file.name}")
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Converter: SIDM2 v2.8.0")
        lines.append("")

        # Source file metadata
        lines.append("Source File:")
        lines.append(f"  Title:           {sid_metadata.get('title', '(unknown)')}")
        lines.append(f"  Author:          {sid_metadata.get('author', '(unknown)')}")
        lines.append(f"  Copyright:       {sid_metadata.get('copyright', '(unknown)')}")
        lines.append(f"  Player Type:     {selection.player_type}")
        lines.append(f"  Format:          {sid_metadata.get('format', 'Unknown')}")
        lines.append(f"  Load Address:    ${sid_metadata.get('load_addr', 0):04X}")
        lines.append(f"  Init Address:    ${sid_metadata.get('init_addr', 0):04X}")
        lines.append(f"  Play Address:    ${sid_metadata.get('play_addr', 0):04X}")
        lines.append(f"  Songs:           {sid_metadata.get('songs', 0)}")
        lines.append("")

        # Driver selection
        lines.append(self.format_info_file_section(selection))
        lines.append("")

        # Conversion results
        lines.append("Conversion Results:")
        output_size = output_file.stat().st_size if output_file.exists() else 0
        lines.append(f"  Status:          SUCCESS")
        lines.append(f"  Output File:     {output_file.name}")
        lines.append(f"  Output Size:     {output_size:,} bytes")
        if validation_result:
            lines.append(f"  Validation:      {validation_result.get('status', 'UNKNOWN')}")
        lines.append("")

        # Validation details (if available)
        if validation_result and validation_result.get('details'):
            lines.append("Validation Details:")
            for detail in validation_result['details']:
                lines.append(f"  {detail}")
            lines.append("")

        return '\n'.join(lines)


# Convenience function for quick usage
def select_best_driver(sid_file: Path, player_type: Optional[str] = None) -> DriverSelection:
    """Quick function to select best driver.

    Args:
        sid_file: Path to SID file
        player_type: Pre-identified player type (optional)

    Returns:
        DriverSelection result
    """
    selector = DriverSelector()
    return selector.select_driver(sid_file, player_type)
