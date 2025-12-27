#!/usr/bin/env python3
"""
Measure accuracy improvements from B2+B3 integration.

This script:
1. Selects Laxity NewPlayer v21 test files
2. Converts SID → SF2 → SID (roundtrip)
3. Compares original vs exported using siddump
4. Calculates frame-by-frame accuracy
5. Generates detailed report

Usage:
    python pyscript/measure_b2_b3_accuracy.py
    python pyscript/measure_b2_b3_accuracy.py --files 5
    python pyscript/measure_b2_b3_accuracy.py --directory Fun_Fun
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.enhanced_player_detection import EnhancedPlayerDetector


class AccuracyMeasurement:
    """Measure B2+B3 integration accuracy improvements"""

    def __init__(self, test_dir: str = "Fun_Fun", max_files: int = 10):
        self.test_dir = test_dir
        self.max_files = max_files
        self.results = []
        self.temp_dir = Path("accuracy_test_temp")
        self.temp_dir.mkdir(exist_ok=True)
        self.detector = EnhancedPlayerDetector()

    def find_laxity_files(self) -> List[Path]:
        """Find Laxity NewPlayer v21 files"""
        print(f"\n[*] Scanning {self.test_dir} for Laxity NewPlayer v21 files...")

        laxity_files = []
        test_path = Path(self.test_dir)

        if not test_path.exists():
            print(f"[!] Directory not found: {self.test_dir}")
            return []

        for sid_file in test_path.glob("*.sid"):
            try:
                # Detect player type
                player_type, confidence = self.detector.detect_player(sid_file)

                if player_type and "laxity" in player_type.lower():
                    print(f"  [+] {sid_file.name} - {player_type} ({confidence:.1%})")
                    laxity_files.append(sid_file)

                    if len(laxity_files) >= self.max_files:
                        break
                else:
                    print(f"  [ ] {sid_file.name} - {player_type} (skipped)")

            except Exception as e:
                print(f"  [!] {sid_file.name} - Error: {e}")
                continue

        print(f"\n[=] Found {len(laxity_files)} Laxity files (max: {self.max_files})")
        return laxity_files

    def convert_sid_to_sf2(self, sid_file: Path) -> Path:
        """Convert SID to SF2 using B2+B3 integration"""
        sf2_file = self.temp_dir / f"{sid_file.stem}.sf2"

        cmd = [
            "python", "scripts/sid_to_sf2.py",
            str(sid_file),
            str(sf2_file),
            "--driver", "laxity",
            "-q"  # Quiet mode
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if result.returncode != 0 or not sf2_file.exists():
            # Remove Unicode chars from error message
            error_msg = result.stderr.encode('ascii', 'ignore').decode('ascii')
            raise Exception(f"Conversion failed: {error_msg}")

        return sf2_file

    def convert_sf2_to_sid(self, sf2_file: Path) -> Path:
        """Convert SF2 back to SID"""
        sid_file = self.temp_dir / f"{sf2_file.stem}_exported.sid"

        cmd = [
            "python", "scripts/sf2_to_sid.py",
            str(sf2_file),
            str(sid_file),
            "-q"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if result.returncode != 0 or not sid_file.exists():
            # Remove Unicode chars from error message
            error_msg = result.stderr.encode('ascii', 'ignore').decode('ascii')
            raise Exception(f"Export failed: {error_msg}")

        return sid_file

    def compare_with_siddump(self, original: Path, exported: Path, frames: int = 300) -> Dict:
        """Compare original vs exported using siddump"""

        # Run siddump on original (capture stdout)
        cmd_orig = [
            "python", "pyscript/siddump_complete.py",
            str(original),
            f"-t{frames // 50}",  # Convert frames to seconds (50 Hz)
        ]
        result_orig = subprocess.run(cmd_orig, capture_output=True, text=True, encoding='utf-8', errors='replace')

        # Run siddump on exported
        cmd_exp = [
            "python", "pyscript/siddump_complete.py",
            str(exported),
            f"-t{frames // 50}",
        ]
        result_exp = subprocess.run(cmd_exp, capture_output=True, text=True, encoding='utf-8', errors='replace')

        # Write dumps to files for comparison
        orig_dump = self.temp_dir / f"{original.stem}_orig.txt"
        exp_dump = self.temp_dir / f"{exported.stem}_exp.txt"

        with open(orig_dump, 'w', encoding='utf-8') as f:
            f.write(result_orig.stdout)

        with open(exp_dump, 'w', encoding='utf-8') as f:
            f.write(result_exp.stdout)

        # Compare dumps
        if orig_dump.exists() and exp_dump.exists() and orig_dump.stat().st_size > 0:
            return self._calculate_accuracy(orig_dump, exp_dump)
        else:
            return {"accuracy": 0.0, "error": f"Dump files empty or not created (orig: {orig_dump.stat().st_size if orig_dump.exists() else 0} bytes)"}

    def _calculate_accuracy(self, orig_dump: Path, exp_dump: Path) -> Dict:
        """Calculate frame-by-frame accuracy from dump files"""

        try:
            with open(orig_dump, 'r') as f:
                orig_lines = f.readlines()
            with open(exp_dump, 'r') as f:
                exp_lines = f.readlines()

            # Extract register writes (lines with SID register changes)
            orig_writes = [line for line in orig_lines if line.strip() and not line.startswith('#')]
            exp_writes = [line for line in exp_lines if line.strip() and not line.startswith('#')]

            # Compare line by line
            matches = 0
            total = max(len(orig_writes), len(exp_writes))

            for i in range(min(len(orig_writes), len(exp_writes))):
                if orig_writes[i].strip() == exp_writes[i].strip():
                    matches += 1

            accuracy = (matches / total * 100) if total > 0 else 0.0

            return {
                "accuracy": accuracy,
                "matches": matches,
                "total": total,
                "orig_writes": len(orig_writes),
                "exp_writes": len(exp_writes)
            }

        except Exception as e:
            return {"accuracy": 0.0, "error": str(e)}

    def safe_print(self, msg: str):
        """Print with ASCII-safe encoding for Windows console"""
        try:
            print(msg)
        except UnicodeEncodeError:
            # Fallback: encode as ASCII, replacing non-ASCII chars
            print(msg.encode('ascii', 'ignore').decode('ascii'))

    def test_file(self, sid_file: Path) -> Dict:
        """Run complete accuracy test on one file"""
        self.safe_print(f"\n{'='*60}")
        self.safe_print(f"Testing: {sid_file.name}")
        self.safe_print(f"{'='*60}")

        result = {
            "file": sid_file.name,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }

        try:
            # Step 1: SID → SF2
            self.safe_print("  [1/3] Converting SID → SF2...")
            sf2_file = self.convert_sid_to_sf2(sid_file)
            result["sf2_file"] = sf2_file.name
            result["sf2_size"] = sf2_file.stat().st_size
            self.safe_print(f"        [+] Created {sf2_file.name} ({result['sf2_size']} bytes)")

            # Step 2: SF2 → SID
            self.safe_print("  [2/3] Converting SF2 → SID...")
            exported_sid = self.convert_sf2_to_sid(sf2_file)
            result["exported_sid"] = exported_sid.name
            result["exported_size"] = exported_sid.stat().st_size
            self.safe_print(f"        [+] Created {exported_sid.name} ({result['exported_size']} bytes)")

            # Step 3: Compare accuracy
            self.safe_print("  [3/3] Measuring accuracy with siddump...")
            accuracy_data = self.compare_with_siddump(sid_file, exported_sid)
            result.update(accuracy_data)

            if "error" not in accuracy_data:
                result["success"] = True
                self.safe_print(f"        [+] Accuracy: {accuracy_data['accuracy']:.2f}%")
                self.safe_print(f"        [=] Matches: {accuracy_data['matches']}/{accuracy_data['total']} frames")
            else:
                self.safe_print(f"        [!] Error: {accuracy_data['error']}")

        except Exception as e:
            result["error"] = str(e)
            self.safe_print(f"        [!] Failed: {e}")

        return result

    def run_all_tests(self):
        """Run accuracy tests on all Laxity files"""
        print("\n" + "="*60)
        print("B2+B3 INTEGRATION ACCURACY MEASUREMENT")
        print("="*60)

        # Find test files
        test_files = self.find_laxity_files()

        if not test_files:
            print("\n[!] No Laxity files found!")
            return

        # Run tests
        print(f"\n[TEST] Running accuracy tests on {len(test_files)} files...")

        for sid_file in test_files:
            result = self.test_file(sid_file)
            self.results.append(result)

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate detailed accuracy report"""
        print("\n" + "="*60)
        print("ACCURACY MEASUREMENT RESULTS")
        print("="*60)

        successful = [r for r in self.results if r.get("success")]
        failed = [r for r in self.results if not r.get("success")]

        if successful:
            accuracies = [r["accuracy"] for r in successful]
            avg_accuracy = sum(accuracies) / len(accuracies)
            min_accuracy = min(accuracies)
            max_accuracy = max(accuracies)

            print(f"\n[=] Summary:")
            print(f"  Total files tested: {len(self.results)}")
            print(f"  Successful: {len(successful)}")
            print(f"  Failed: {len(failed)}")
            print(f"\n[STATS] Accuracy Metrics:")
            print(f"  Average: {avg_accuracy:.2f}%")
            print(f"  Minimum: {min_accuracy:.2f}%")
            print(f"  Maximum: {max_accuracy:.2f}%")

            # Detailed results
            print(f"\n[LIST] Detailed Results:")
            for r in successful:
                print(f"  {r['file']:40s} {r['accuracy']:6.2f}%  ({r['matches']}/{r['total']} frames)")

        else:
            print("\n[!] No successful tests!")

        if failed:
            print(f"\n[!]  Failed Tests:")
            for r in failed:
                print(f"  {r['file']:40s} Error: {r.get('error', 'Unknown')}")

        # Save JSON report
        report_file = Path("B2_B3_ACCURACY_REPORT.json")
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.results),
                    "successful": len(successful),
                    "failed": len(failed),
                    "average_accuracy": avg_accuracy if successful else 0.0,
                    "min_accuracy": min_accuracy if successful else 0.0,
                    "max_accuracy": max_accuracy if successful else 0.0
                },
                "results": self.results
            }, f, indent=2)

        print(f"\n[SAVE] Full report saved: {report_file}")

        # Cleanup suggestion
        print(f"\n[CLEAN] Cleanup: rm -rf {self.temp_dir}")


def main():
    parser = argparse.ArgumentParser(description="Measure B2+B3 accuracy improvements")
    parser.add_argument("--directory", "-d", default="Fun_Fun", help="Directory with test files")
    parser.add_argument("--files", "-n", type=int, default=10, help="Max files to test")

    args = parser.parse_args()

    measurement = AccuracyMeasurement(test_dir=args.directory, max_files=args.files)
    measurement.run_all_tests()


if __name__ == "__main__":
    main()
