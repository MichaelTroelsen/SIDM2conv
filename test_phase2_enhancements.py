#!/usr/bin/env python3
"""
Test Phase 2 Enhancements:
- Enhanced player detection (SF2 drivers)
- Memory layout parsing
- Enhanced structure reports
"""

from pathlib import Path
from sidm2.siddecompiler import SIDdecompilerAnalyzer

# Test files
test_files = [
    'SIDSF2player/Broware.sid',  # Laxity file
    'SIDSF2player/Driver 11 Test - Arpeggio.sid',  # SF2 exported
]

output_dir = Path('output/phase2_test')
output_dir.mkdir(parents=True, exist_ok=True)

print("="*80)
print("Phase 2 Enhancement Testing")
print("="*80)
print()

analyzer = SIDdecompilerAnalyzer()

for sid_path in test_files:
    sid_file = Path(sid_path)
    if not sid_file.exists():
        print(f"[SKIP] {sid_file.name} - File not found")
        continue

    print(f"Testing: {sid_file.name}")
    print("-" * 80)

    # Create subdirectory
    analysis_dir = output_dir / sid_file.stem / 'analysis'
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # Run enhanced analysis
    try:
        success, report = analyzer.analyze_and_report(sid_file, analysis_dir)

        if success:
            print("[OK] Analysis complete")
            print()

            # Show the enhanced report
            report_file = analysis_dir / f"{sid_file.stem}_analysis_report.txt"
            if report_file.exists():
                with open(report_file, 'r') as f:
                    content = f.read()
                print(content)
                print()
        else:
            print(f"[ERROR] Analysis failed")
            print(report)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

    print()

print("="*80)
print("Phase 2 Testing Complete")
print("="*80)
