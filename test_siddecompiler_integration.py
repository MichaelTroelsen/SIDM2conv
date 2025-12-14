#!/usr/bin/env python3
"""
Quick test of SIDdecompiler integration in the pipeline.
Tests Step 1.6 on a single SID file.
"""

from pathlib import Path
from sidm2.siddecompiler import SIDdecompilerAnalyzer

# Test on a single file
sid_file = Path('SIDSF2player/Broware.sid')
output_dir = Path('output/test_siddecompiler_integration')
output_dir.mkdir(parents=True, exist_ok=True)

print("Testing SIDdecompiler Integration")
print("=" * 80)
print(f"Input: {sid_file}")
print(f"Output: {output_dir}")
print()

# Create analysis directory
analysis_dir = output_dir / 'analysis'
analysis_dir.mkdir(parents=True, exist_ok=True)

# Run SIDdecompiler analysis
print("Running SIDdecompiler analysis...")
try:
    analyzer = SIDdecompilerAnalyzer()
    success, report = analyzer.analyze_and_report(sid_file, analysis_dir)

    if success:
        print("[OK] Analysis complete")
        print()
        print("Generated files:")
        for f in analysis_dir.glob('*'):
            print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

        # Extract player info and tables
        basename = sid_file.stem
        asm_file = analysis_dir / f'{basename}_siddecompiler.asm'
        if asm_file.exists():
            player_info = analyzer.detect_player(asm_file, "")
            detected_tables = analyzer.extract_tables(asm_file)

            print()
            if player_info:
                print(f"Player Type: {player_info.type}")
                if player_info.init_addr:
                    print(f"Init Address: ${player_info.init_addr:04X}")
                if player_info.play_addr:
                    print(f"Play Address: ${player_info.play_addr:04X}")

            if detected_tables:
                print(f"\nDetected Tables: {len(detected_tables)}")
                for name, table in detected_tables.items():
                    print(f"  - {name}: ${table.address:04X}")

        print()
        print("[SUCCESS] Integration test passed")

    else:
        print("[ERROR] Analysis failed")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
