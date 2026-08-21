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

    # --- NATIVE BUILDER ADVISORY (ROADMAP A4) ------------------------------
    # These describe a `bin/` native builder that claims this file. They are
    # ADVISORY and NEVER change `driver_name`: see identify_native_builder().
    native_family: str = ""       # "sdi", "hardtrack", ... or "" for none
    native_builder: str = ""      # "bin/build_sdi_native_song.py" or ""
    native_confident: bool = False  # True only on a unique signature match
    native_why: str = ""          # rank()'s own explanation, verbatim


class DriverSelector:
    """Selects best SF2 driver based on source SID player type."""

    # ---------------------------------------------------------------------------
    # PLAYER_REGISTRY — single source of truth for all supported player types.
    #
    # To add a new player type:
    #   1. Add an entry here with its player-id.exe detection strings, driver file,
    #      expected accuracy, and description.
    #   2. Add an entry to conversion_pipeline.PLAYER_CONVERTERS if it needs a
    #      custom convert function (like Laxity/Galway), or to PLAYER_EXTRACTORS
    #      if it needs a custom analyzer class.
    #   3. Add the driver .prg file to G5/drivers/.
    #   4. Implement the analyzer class inheriting from player_base.BasePlayerAnalyzer.
    # ---------------------------------------------------------------------------
    PLAYER_REGISTRY = {
        'laxity': {
            'player_ids': [
                'Laxity_NewPlayer_V21',   # Native Laxity NP21
                'Vibrants/Laxity',        # Laxity player by Vibrants
                '256bytes/Laxity',        # Compact Laxity player
                'SidFactory_II/Laxity',   # SF2-exported but embeds Laxity NP21 player code
                'SidFactory/Laxity',      # Older SF2 version, same situation
            ],
            'driver_file': 'sf2driver_laxity_00.prg',
            'accuracy': '99.93%',
            'description': 'Laxity NewPlayer v21 — custom driver with pointer patching',
        },
        'driver11': {
            'player_ids': [
                'SidFactory_II',          # Any SF2-exported file (non-Laxity author)
                'SidFactory',             # Older SF2 version
                'SF2_Exported',
                'Driver_11',
            ],
            'driver_file': 'sf2driver11_00.prg',
            'accuracy': '100% (SF2-exported) / safe default (unknown)',
            'description': 'SF2-exported files — Driver 11 preserves exact structure; also safe fallback',
        },
        'np20': {
            'player_ids': [
                'NewPlayer_20',
                'NewPlayer_20.G4',
                'NP20',
            ],
            'driver_file': 'sf2driver_np20_00.prg',
            'accuracy': '70-90%',
            'description': 'NewPlayer 20.G4',
        },
        'galway': {
            'player_ids': [
                'Martin_Galway',
                'Galway',
            ],
            'driver_file': 'sf2driver11_00.prg',
            'accuracy': 'Stage A: editable Driver 11 transpile (correct notes, approximated timbre); embed fallback',
            'description': 'Martin Galway 1st-gen — transpile the bytecode-extracted score to an editable, playable Driver 11 SF2 (notes/timing/envelopes correct; pulse/FM/filter modulation approximated — Stage B will add a native Galway driver). Falls back to embedded-player audio when recovery fails.',
        },
        # --- ADD NEW PLAYERS BELOW ---
        # 'myplayer': {
        #     'player_ids': ['MyPlayer_v1', 'MP1'],  # strings output by player-id.exe
        #     'driver_file': 'sf2driver_myplayer_00.prg',  # must exist in G5/drivers/
        #     'accuracy': 'TBD',
        #     'description': 'My custom player format',
        # },
    }

    # Build PLAYER_MAPPINGS and DRIVER_FILES from PLAYER_REGISTRY for backwards compat
    PLAYER_MAPPINGS = {
        pid: driver
        for driver, info in PLAYER_REGISTRY.items()
        for pid in info['player_ids']
    }

    DRIVER_FILES = {
        driver: info['driver_file']
        for driver, info in PLAYER_REGISTRY.items()
    }

    # Expected accuracies (kept for backwards compat; PLAYER_REGISTRY is authoritative).
    # 'laxity'/'np20'/'galway' are derived from PLAYER_REGISTRY so the two can't drift.
    # 'driver11_sf2'/'driver11_default' have no registry equivalent — PLAYER_REGISTRY['driver11']
    # stores one combined description, but _build_selection_result needs the SF2-exported and
    # unknown-fallback cases distinguished, so those two stay explicit literals.
    EXPECTED_ACCURACY = {
        'laxity': PLAYER_REGISTRY['laxity']['accuracy'],
        'driver11_sf2': '100%',
        'driver11_default': 'Safe default',
        'np20': PLAYER_REGISTRY['np20']['accuracy'],
        'galway': PLAYER_REGISTRY['galway']['accuracy'],
    }

    # -----------------------------------------------------------------------
    # NATIVE_BUILDERS - family name from sidm2.native_dispatch -> the `bin/`
    # script that builds it. This is the A4 wiring, and it is deliberately
    # NOT a second PLAYER_REGISTRY:
    #
    #   * PLAYER_REGISTRY maps a player-id string -> an SF2 DRIVER this
    #     package can actually run in-process.
    #   * NATIVE_BUILDERS maps a probed family -> a standalone SCRIPT. Every
    #     one of these reads `SID = sys.argv[1]` at MODULE level and then
    #     siddumps, emulates and traces the tune for tens of seconds to
    #     minutes. They are subprocess entry points, not importable
    #     converters, so the pipeline NAMES the builder; it never calls it.
    #
    # That is why the dispatcher is ADVISORY. See identify_native_builder().
    # -----------------------------------------------------------------------
    NATIVE_BUILDERS = {
        'blackbird':    'bin/build_blackbird_native_song.py',
        'sdi':          'bin/build_sdi_native_song.py',
        'hardtrack':    'bin/build_hardtrack_native_song.py',
        'mattgray':     'bin/build_mattgray_native_song.py',
        'dmc':          'bin/build_dmc_native_song.py',
        'mon':          'bin/build_mon_native_song.py',
        'hubbard':      'bin/build_hubbard_native_song.py',
        'soundmonitor': 'bin/build_soundmonitor_native_song.py',
    }

    def identify_native_builder(self, sid_file: Path, player_type: Optional[str] = None) -> Optional[Dict]:
        """Which `bin/` native builder claims this SID? ADVISORY, never a route.

        Returns None when no family accepts, else::

            {"family": str, "builder": str, "confident": bool,
             "why": str, "candidates": [family, ...]}

        `confident` is True only when `native_dispatch.rank()` found a UNIQUE
        signature-bearing family. When it is False, `family` is the first
        construct-only family that accepted and the answer is a CANDIDATE, not
        a verdict -- `dmc` and `mon` accept nearly every file ever measured, so
        their acceptance carries no information about ownership.

        WHY THIS NEVER SETS `driver_name`, measured 2026-08-21 over 734 files:

            SID/JohannesBjerregaard   88   best=None on all 88
            SID/Gallefoss_Glenn      441   sdi 160, None 281
            SID/Shogoon              150   hardtrack 33, sdi 20, None 97
            SID/Gray_Matt             55   mattgray 11, soundmonitor 6,
                                           sdi 1, None 37

        ZERO SIGNATURE COLLISIONS ACROSS ALL 734 -- AND THAT IS NOT SAFETY.
        No collision only means no two signature families claimed the same
        file; it says nothing about whether the one that claimed it was right.
        Checked against an independent identifier, ~26 of those confident
        answers are unverified and some are probably wrong:

          * 20 SID/Shogoon files rank `sdi` confidently. `player-id.exe` calls
            17 of them DMC and 3 Music_Assembler -- not one SIDDuzz'It. Among
            them is `Pollena_2000`, which native_dispatch's own comments already
            record as a file `is_sdi_play3` "claimed unopposed".
          * 6 SID/Gray_Matt files rank `soundmonitor` confidently, among them
            `Sanxion_Re-load` and `Crazy_Comets_Special_Re-Mix`.
            `is_soundmonitor` accepts 11 of the 20 files in its own SID/Fun_Fun
            corpus and 6 of the 55 in Gray_Matt: 11/17 on that pair.

        `player-id` is itself many-to-many with the builders -- that is ROADMAP
        A4's founding measurement -- so this does not PROVE 26 misroutes. It
        proves the confidence flag is not corroborated, which is enough: had
        this been wired as a router, those 26 files would have produced wrong
        SF2s silently. As an advisory the worst case is a misleading log line.

        A unique signature match is the strongest evidence this module has and
        it is still not proof of ownership. That is why `driver_name` is chosen
        before this runs and is never revised by it.
        """
        try:
            from sidm2 import native_dispatch
        except ImportError:                       # module is optional
            return None
        try:
            r = native_dispatch.rank(str(sid_file), player_id=player_type)
        except native_dispatch.ProbeBug:
            # A probe called its parser wrongly. That is a bug in the probe
            # layer, never a verdict about this file, and it must not silently
            # degrade driver selection -- so report "no advisory" and let the
            # dispatcher's own tests be the place it surfaces.
            return None
        except Exception:
            return None

        accepted = list(r["signature"]) + list(r["weak"])
        if not accepted:
            return None
        family = r["best"] or accepted[0]
        return {
            "family": family,
            "builder": self.NATIVE_BUILDERS.get(family, ""),
            "confident": bool(r["confident"]),
            "why": r["why"],
            "candidates": accepted,
        }

    @classmethod
    def registered_drivers(cls) -> list:
        """Return list of all registered driver names."""
        return list(cls.PLAYER_REGISTRY.keys())

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
            forced = self._handle_forced_driver(force_driver, player_type)
            self._attach_native_advisory(forced, sid_file, player_type)
            return forced

        # Select best driver based on player type
        selected_driver = self._select_best_driver(player_type)

        # Build selection result
        selection = self._build_selection_result(selected_driver, player_type)

        # ROADMAP A4: attach the native-builder advisory. This runs AFTER the
        # driver is chosen and cannot change it -- see identify_native_builder.
        self._attach_native_advisory(selection, sid_file, player_type)
        return selection

    def _attach_native_advisory(self, selection: DriverSelection,
                                sid_file: Path,
                                player_type: Optional[str] = None) -> DriverSelection:
        """Fill in `selection.native_*` from the probe dispatcher, in place.

        Separate from select_driver so the forced-driver path can share it: an
        expert who forces `--driver driver11` on a HardTrack rip should still be
        told a native builder exists, because that is exactly the case the
        default path is measured at 1-8% on.
        """
        adv = self.identify_native_builder(sid_file, player_type)
        if adv:
            selection.native_family = adv["family"]
            selection.native_builder = adv["builder"]
            selection.native_confident = adv["confident"]
            selection.native_why = adv["why"]
        return selection

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
        registry_acc = self.PLAYER_REGISTRY.get(force_driver, {}).get('accuracy')
        expected_accuracy = f"{registry_acc} (user override)" if registry_acc else "User override"
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

    @staticmethod
    def _format_native_advisory(selection: DriverSelection) -> list:
        """The native-builder lines, shared by the console and info-file forms.

        THE WORD "CANDIDATE" IS LOAD-BEARING. An unconfident advisory names a
        family that accepted without a signature, and `dmc`/`mon` accept nearly
        every file ever measured, so printing that as a recommendation would be
        worse than printing nothing at all.
        """
        if not selection.native_family:
            return []
        lines = []
        if selection.native_confident:
            lines.append(f"  Native builder:  {selection.native_family} "
                         f"-- {selection.native_builder}")
            lines.append(f"                   NOT run automatically: "
                         f"py -3 {selection.native_builder} <file.sid>")
        else:
            lines.append(f"  Native builder:  CANDIDATE ONLY: "
                         f"{selection.native_family} "
                         f"-- {selection.native_builder}")
            lines.append(f"                   {selection.native_why}")
        return lines

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

        lines.extend(self._format_native_advisory(selection))

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

        lines.extend(self._format_native_advisory(selection))

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
