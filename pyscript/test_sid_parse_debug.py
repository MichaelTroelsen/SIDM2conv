#!/usr/bin/env python3
"""
Debug script to diagnose SID parsing failures.
"""

import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_packer import SF2Packer
from pyscript.sidtracer import SIDTracer
import tempfile

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_pack_and_parse(sf2_file: Path):
    """Test packing and parsing a single SF2 file."""
    print(f"\n{'='*70}")
    print(f"Testing: {sf2_file.name}")
    print(f"{'='*70}\n")

    # Step 1: Pack SF2 to SID
    print("[1/4] Packing SF2 to SID...")
    packer = SF2Packer(str(sf2_file))
    sid_data, init_addr, play_addr = packer.pack(dest_address=0x1000)

    print(f"  Packed size: {len(sid_data):,} bytes")
    print(f"  Init addr: ${init_addr:04X}")
    print(f"  Play addr: ${play_addr:04X}")

    # Step 2: Examine SID header
    print(f"\n[2/4] Examining PSID header...")
    print(f"  Magic: {sid_data[0:4]}")
    version = (sid_data[4] << 8) | sid_data[5]
    data_offset = (sid_data[6] << 8) | sid_data[7]
    load_address = (sid_data[8] << 8) | sid_data[9]
    print(f"  Version: {version}")
    print(f"  Data offset: {data_offset} (0x{data_offset:04X})")
    print(f"  Load address: ${load_address:04X}")
    print(f"  Total size: {len(sid_data)} bytes")
    print(f"  Data size: {len(sid_data) - data_offset} bytes")

    # Step 3: Save to temp file
    print(f"\n[3/4] Saving to temp file...")
    with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as f:
        f.write(sid_data)
        temp_path = Path(f.name)
    print(f"  Saved to: {temp_path}")

    # Step 4: Parse with SIDTracer
    print(f"\n[4/4] Parsing with SIDTracer...")
    try:
        tracer = SIDTracer(temp_path, verbose=2)  # Verbose mode
        print(f"  [SUCCESS] Parse succeeded!")
        print(f"    Name: {tracer.header.name}")
        print(f"    Load: ${tracer.header.load_address:04X}")
        print(f"    Init: ${tracer.header.init_address:04X}")
        print(f"    Play: ${tracer.header.play_address:04X}")
        print(f"    SID data: {len(tracer.sid_data)} bytes")
        return True
    except ValueError as e:
        print(f"  [FAILED] ValueError: {e}")
        return False
    except Exception as e:
        print(f"  [ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        temp_path.unlink()

if __name__ == '__main__':
    # Test one file
    test_file = Path('G5/examples/Driver 11 Test - Arpeggio.sf2')

    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)

    success = test_pack_and_parse(test_file)
    sys.exit(0 if success else 1)
