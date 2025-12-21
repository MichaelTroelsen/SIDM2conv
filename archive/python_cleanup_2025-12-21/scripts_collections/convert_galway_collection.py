#!/usr/bin/env python3
"""
Batch converter for Martin Galway SID collection.

Converts all 40 Martin Galway files from PSID/RSID format to SF2 format
using the table extraction and injection pipeline (Phases 2-4).
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import (
    SIDParser,
    MartinGalwayAnalyzer,
    GalwayMemoryAnalyzer,
    GalwayTableExtractor,
    GalwayConversionIntegrator,
    SF2Writer,
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class GalwayBatchConverter:
    """Batch convert Martin Galway SID files to SF2 format."""

    def __init__(self, input_dir: str = "Galway_Martin",
                 output_dir: str = "output/Galway_Martin_Converted",
                 driver: str = "driver11"):
        """
        Initialize batch converter.

        Args:
            input_dir: Directory containing Martin Galway SID files
            output_dir: Output directory for converted SF2 files
            driver: Target driver ('driver11', 'np20')
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.driver = driver
        self.results: Dict[str, Dict[str, Any]] = {}

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_galway_files(self) -> List[Path]:
        """Get all Martin Galway SID files."""
        if not self.input_dir.exists():
            logger.warning(f"Input directory not found: {self.input_dir}")
            return []

        files = sorted(list(self.input_dir.glob('*.sid')))
        logger.info(f"Found {len(files)} Martin Galway SID files")
        return files

    def convert_file(self, sid_file: Path) -> Tuple[bool, Dict[str, Any]]:
        """
        Convert single SID file to SF2.

        Args:
            sid_file: Path to SID file

        Returns:
            (success, result_dict)
        """
        result = {
            'filename': sid_file.name,
            'status': 'pending',
            'error': None,
            'confidence': 0.0,
            'tables_found': 0,
            'output_file': None,
        }

        try:
            logger.info(f"Converting: {sid_file.name}")

            # Step 1: Parse SID
            parser = SIDParser(str(sid_file))
            header = parser.parse_header()
            c64_data = parser.data[header.data_offset:]

            result['load_address'] = f"${header.load_address:04X}"
            result['init_address'] = f"${header.init_address:04X}"
            result['play_address'] = f"${header.play_address:04X}"

            # Step 2: Analyze Martin Galway player
            galway_analyzer = MartinGalwayAnalyzer(str(sid_file))
            analysis = galway_analyzer.analyze(c64_data, header.load_address,
                                              header.init_address, header.play_address)

            result['format'] = analysis.get('format', 'unknown')
            result['is_rsid'] = analysis.get('is_rsid', False)
            result['is_psid'] = analysis.get('is_psid', False)

            # Step 3: Memory analysis
            memory_analyzer = GalwayMemoryAnalyzer(c64_data, header.load_address)
            memory_result = memory_analyzer.analyze()

            # Step 4: Table extraction
            extractor = GalwayTableExtractor(c64_data, header.load_address)
            extraction = extractor.extract()

            result['tables_found'] = len(extraction.tables_found)

            # Step 5: Get base driver template
            driver_path = Path('G5/drivers/sf2driver_common_11.prg')
            if driver_path.exists():
                with open(driver_path, 'rb') as f:
                    sf2_template = f.read()
            else:
                # Use minimal template
                sf2_template = bytes(20000)

            # Step 6: Integration (extract → convert → inject)
            integrator = GalwayConversionIntegrator(self.driver)
            sf2_data, confidence = integrator.integrate(
                c64_data,
                header.load_address,
                sf2_template,
                memory_result.get('patterns', [])
            )

            result['confidence'] = confidence

            # Step 7: Write SF2 file
            output_file = self.output_dir / sid_file.stem / "converted.sf2"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'wb') as f:
                f.write(sf2_data)

            result['output_file'] = str(output_file)
            result['status'] = 'success'

            logger.info(f"  [OK] Converted to {output_file.name} ({confidence:.0%} confidence)")

            return True, result

        except Exception as e:
            logger.error(f"  [FAIL] {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
            return False, result

    def convert_all(self) -> None:
        """Convert all Martin Galway SID files."""
        files = self.get_galway_files()

        if not files:
            logger.error("No files found to convert")
            return

        print("\n" + "="*70)
        print(f"MARTIN GALWAY BATCH CONVERTER")
        print(f"Driver: {self.driver.upper()}")
        print(f"Files: {len(files)}")
        print("="*70 + "\n")

        successful = 0
        failed = 0

        for i, sid_file in enumerate(files, 1):
            success, result = self.convert_file(sid_file)
            self.results[result['filename']] = result

            if success:
                successful += 1
            else:
                failed += 1

            print(f"[{i:2d}/{len(files)}] {result['filename']:40s} {result['status']:8s}",
                  end="")
            if success:
                print(f" {result['confidence']:.0%}")
            else:
                print(f" {result['error']}")

        # Summary
        print("\n" + "="*70)
        print("CONVERSION SUMMARY")
        print("="*70)
        print(f"Total files: {len(files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {successful/len(files):.0%}")

        # Confidence statistics
        confidences = [r['confidence'] for r in self.results.values()
                      if r['status'] == 'success']
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            max_confidence = max(confidences)
            min_confidence = min(confidences)
            print(f"\nConfidence Statistics:")
            print(f"  Average: {avg_confidence:.0%}")
            print(f"  Max: {max_confidence:.0%}")
            print(f"  Min: {min_confidence:.0%}")

        # Save detailed report
        self._save_report()

    def _save_report(self) -> None:
        """Save detailed conversion report."""
        report_file = self.output_dir / "CONVERSION_REPORT.md"

        lines = [
            f"# Martin Galway Batch Conversion Report",
            f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Driver: {self.driver.upper()}",
            f"",
            f"## Summary",
            f"- Total files: {len(self.results)}",
            f"- Successful: {sum(1 for r in self.results.values() if r['status'] == 'success')}",
            f"- Failed: {sum(1 for r in self.results.values() if r['status'] == 'failed')}",
            f"",
            f"## Details",
            f"",
        ]

        for filename in sorted(self.results.keys()):
            result = self.results[filename]
            lines.append(f"### {filename}")
            lines.append(f"- Status: {result['status']}")
            lines.append(f"- Format: {result.get('format', 'unknown')}")
            lines.append(f"- Tables found: {result['tables_found']}")
            lines.append(f"- Confidence: {result['confidence']:.0%}")
            if result['output_file']:
                lines.append(f"- Output: {result['output_file']}")
            if result['error']:
                lines.append(f"- Error: {result['error']}")
            lines.append("")

        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))

        logger.info(f"Report saved to {report_file}")


def main():
    """Main entry point."""
    # Check for command-line options
    driver = "driver11"
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--driver", "-d"]:
            if len(sys.argv) > 2:
                driver = sys.argv[2]

    # Create converter
    converter = GalwayBatchConverter(driver=driver)

    # Convert all files
    converter.convert_all()

    return 0


if __name__ == '__main__':
    sys.exit(main())
