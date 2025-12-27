"""
Martin Galway Table Injection System

Injects extracted Martin Galway tables into SF2 Driver 11 format.
Provides improved accuracy by using native Galway tables while keeping
the battle-tested Driver 11 as the base player.

Phase 4 implementation: Table injection and driver integration
"""

import logging
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InjectionPoint:
    """Represents where to inject a table into SF2 format"""
    table_type: str  # 'instruments', 'sequences', etc.
    sf2_offset: int  # Offset in final SF2 file
    size: int  # Size of injection
    driver: str  # Which driver ('driver11', 'np20', etc.)


class GalwayTableInjector:
    """
    Inject extracted Galway tables into SF2 driver format.

    Strategy: Keep Driver 11 as base, inject extracted Galway tables
    to improve accuracy while maintaining compatibility.

    Injection Points (Driver 11):
    - 0x0903: Sequences
    - 0x0A03: Instruments
    - 0x0B03: Wave table
    - 0x0D03: Pulse table
    - 0x0F03: Filter table
    """

    # Standard Driver 11 injection points
    DRIVER11_OFFSETS = {
        'sequences': 0x0903,
        'instruments': 0x0A03,
        'wave': 0x0B03,
        'pulse': 0x0D03,
        'filter': 0x0F03,
    }

    # NP20 driver offsets (different)
    NP20_OFFSETS = {
        'sequences': 0x0703,
        'instruments': 0x0803,
        'wave': 0x0903,
        'pulse': 0x0B03,
        'filter': 0x0D03,
    }

    def __init__(self, sf2_template: bytes, driver: str = "driver11"):
        """
        Initialize injector.

        Args:
            sf2_template: Base SF2 file (Driver 11 or NP20)
            driver: Driver type ('driver11' or 'np20')
        """
        self.sf2_template = bytearray(sf2_template)
        self.driver = driver
        self.injections: List[InjectionPoint] = []
        self.injection_errors: List[str] = []

        # Select offsets based on driver
        if driver == 'driver11':
            self.offsets = self.DRIVER11_OFFSETS
        elif driver == 'np20':
            self.offsets = self.NP20_OFFSETS
        else:
            logger.warning(f"Unknown driver: {driver}, using Driver11 offsets")
            self.offsets = self.DRIVER11_OFFSETS

    def inject_table(self, table_type: str, table_data: bytes,
                    max_size: Optional[int] = None) -> bool:
        """
        Inject a table into the SF2 driver.

        Args:
            table_type: Type of table ('instruments', 'sequences', etc.)
            table_data: Table data to inject
            max_size: Maximum size allowed (truncate if needed)

        Returns:
            True if injection successful
        """
        if table_type not in self.offsets:
            logger.warning(f"Unknown table type: {table_type}")
            self.injection_errors.append(f"Unknown table type: {table_type}")
            return False

        offset = self.offsets[table_type]

        # Check bounds
        if offset + len(table_data) > len(self.sf2_template):
            if max_size:
                table_data = table_data[:max_size]
                logger.info(f"Truncating {table_type} to {max_size} bytes")
            else:
                logger.error(
                    f"Table {table_type} too large for driver\n"
                    f"  Suggestion: Galway table exceeds driver capacity\n"
                    f"  Check: Table size {len(table_data)} > max {max_size} bytes\n"
                    f"  Try: Simplify music or use different driver\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#table-size-errors"
                )
                self.injection_errors.append(f"{table_type}: data exceeds bounds")
                return False

        try:
            # Inject table at offset
            self.sf2_template[offset:offset+len(table_data)] = table_data
            self.injections.append(InjectionPoint(table_type, offset, len(table_data), self.driver))
            logger.info(f"Injected {table_type} at ${offset:04X} ({len(table_data)} bytes)")
            return True

        except Exception as e:
            logger.error(
                f"Injection error for {table_type}: {e}\n"
                f"  Suggestion: Failed to inject {table_type} table into driver\n"
                f"  Check: Verify table data format is valid\n"
                f"  Try: Check if driver has space for this table\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#table-injection-errors"
            )
            self.injection_errors.append(f"{table_type}: {str(e)}")
            return False

    def inject_multiple(self, tables: Dict[str, bytes]) -> Tuple[int, int]:
        """
        Inject multiple tables at once.

        Args:
            tables: Dictionary of {table_type: data}

        Returns:
            (successful_count, failed_count)
        """
        success_count = 0
        failed_count = 0

        for table_type, table_data in tables.items():
            if self.inject_table(table_type, table_data):
                success_count += 1
            else:
                failed_count += 1

        return success_count, failed_count

    def get_result(self) -> bytes:
        """Get the final SF2 file with injected tables."""
        return bytes(self.sf2_template)

    def get_injection_report(self) -> Dict[str, Any]:
        """Get report on injections performed."""
        return {
            'driver': self.driver,
            'injections_successful': len(self.injections),
            'injections': [
                {
                    'type': inj.table_type,
                    'offset': f'${inj.sf2_offset:04X}',
                    'size': inj.size,
                }
                for inj in self.injections
            ],
            'errors': self.injection_errors,
            'error_count': len(self.injection_errors),
        }


class GalwayConversionIntegrator:
    """
    Integrate extracted tables and format conversion into SF2 output.

    Coordinates the complete flow:
    1. Extract tables (GalwayMemoryAnalyzer + GalwayTableExtractor)
    2. Convert format (GalwayFormatConverter)
    3. Inject into driver (GalwayTableInjector)
    4. Write SF2 file
    """

    def __init__(self, driver: str = "driver11"):
        """
        Initialize integrator.

        Args:
            driver: Target driver ('driver11', 'np20')
        """
        self.driver = driver
        self.extraction_results: Dict[str, Any] = {}
        self.conversion_results: Dict[str, Any] = {}
        self.injection_results: Dict[str, Any] = {}

    def integrate(self, c64_data: bytes, load_address: int,
                 sf2_template: bytes, memory_patterns: Optional[List] = None) -> Tuple[bytes, float]:
        """
        Complete integration: extract → convert → inject.

        Args:
            c64_data: Raw C64 binary data
            load_address: Load address
            sf2_template: Base SF2 driver template
            memory_patterns: Optional memory patterns from Phase 2

        Returns:
            (sf2_data, confidence_score)
        """
        logger.info(f"Galway conversion integration starting (${load_address:04X}, {len(c64_data):,} bytes)")

        try:
            # Step 1: Extract tables
            from sidm2.galway_table_extractor import GalwayTableExtractor
            extractor = GalwayTableExtractor(c64_data, load_address)
            extraction = extractor.extract(memory_patterns)
            self.extraction_results = {
                'success': extraction.success,
                'tables_found': len(extraction.tables_found),
                'tables': list(extraction.tables_found.keys()),
                'confidence': extraction.confidence_average,
            }

            if not extraction.success or not extraction.tables_found:
                logger.warning("No tables extracted, using Driver 11 defaults")
                return sf2_template, 0.3  # Low confidence, using defaults

            # Step 2: Convert tables to SF2 format
            from sidm2.galway_format_converter import GalwayFormatConverter
            converter = GalwayFormatConverter(self.driver)

            converted_tables = {}
            conversion_confidence = 0.0

            for table_type, table in extraction.tables_found.items():
                if table_type == 'instruments':
                    converted, conf = converter.convert_instruments(
                        table.data, table.address, table.entries, table.entry_size
                    )
                    converted_tables[table_type] = converted
                    conversion_confidence = max(conversion_confidence, conf)

                elif table_type == 'sequences':
                    converted, conf = converter.convert_sequences(table.data, table.address)
                    converted_tables[table_type] = converted
                    conversion_confidence = max(conversion_confidence, conf)

                elif table_type == 'wave':
                    converted, conf = converter.convert_wave_table(table.data, table.entries)
                    converted_tables[table_type] = converted
                    conversion_confidence = max(conversion_confidence, conf)

                elif table_type == 'pulse':
                    converted, conf = converter.convert_pulse_table(table.data, table.entries)
                    converted_tables[table_type] = converted
                    conversion_confidence = max(conversion_confidence, conf)

                elif table_type == 'filter':
                    converted, conf = converter.convert_filter_table(table.data, table.entries)
                    converted_tables[table_type] = converted
                    conversion_confidence = max(conversion_confidence, conf)

            self.conversion_results = converter.get_conversion_report()
            self.conversion_results['confidence'] = conversion_confidence

            # Step 3: Inject into driver
            injector = GalwayTableInjector(sf2_template, self.driver)
            injector.inject_multiple(converted_tables)
            self.injection_results = injector.get_injection_report()

            # Step 4: Get result
            sf2_data = injector.get_result()

            # Calculate overall confidence
            overall_confidence = (
                extraction.confidence_average * 0.4 +
                conversion_confidence * 0.3 +
                (len(injector.injections) / max(len(converted_tables), 1)) * 0.3
            )

            logger.info(f"Integration complete: {len(converted_tables)} tables injected, "
                       f"confidence: {overall_confidence:.0%}")

            return sf2_data, overall_confidence

        except Exception as e:
            logger.error(
                f"Integration error: {e}\n"
                f"  Suggestion: Failed to integrate Galway tables with driver\n"
                f"  Check: Verify all required tables are present\n"
                f"  Try: Enable verbose logging for detailed error trace\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#integration-errors"
            )
            import traceback
            traceback.print_exc()
            return sf2_template, 0.1  # Very low confidence on error

    def get_integration_report(self) -> Dict[str, Any]:
        """Get complete integration report."""
        return {
            'driver': self.driver,
            'extraction': self.extraction_results,
            'conversion': self.conversion_results,
            'injection': self.injection_results,
        }


# Module initialization
logger.debug("galway_table_injector module loaded")
