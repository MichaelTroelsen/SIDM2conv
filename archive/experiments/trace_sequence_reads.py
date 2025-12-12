#!/usr/bin/env python3
"""
Trace memory reads during SID playback to find sequence data locations.

This script uses our CPU emulator to:
1. Track all memory reads during playback
2. Focus on reads that happen just before SID frequency writes
3. Identify patterns in the memory addresses being read
4. Find the sequence data locations by correlation

Strategy:
- When a frequency write occurs (note triggered), look at recent memory reads
- Sequence data consists of 3-byte entries [Inst] [Cmd] [Note]
- The player reads these bytes sequentially from memory
- By tracking read patterns, we can find where sequences are stored
"""

import sys
sys.path.insert(0, '.')

from sidm2.sid_player import SIDPlayer

class SequenceTracer:
    """Extended SID player that tracks memory reads for sequence detection."""

    def __init__(self):
        self.player = None
        self.cpu = None
        self.recent_reads = []  # Buffer of recent memory reads
        self.max_recent = 20    # Keep last 20 reads
        self.freq_writes = []   # Track frequency writes with context

    def trace_sid_file(self, sid_file, frames=50):
        """Trace SID file execution and log memory reads."""
        print(f"Loading SID file: {sid_file}")

        self.player = SIDPlayer()
        header = self.player.load_sid(sid_file)
        self.cpu = self.player.cpu

        print(f"Load address: ${header.load_address:04X}")
        print(f"Init address: ${header.init_address:04X}")
        print(f"Play address: ${header.play_address:04X}\n")

        # Patch the CPU's read_byte method to track reads
        original_read = self.cpu.mem.__getitem__

        def tracked_read(addr):
            """Wrapper that logs memory reads."""
            value = original_read(addr)

            # Skip SID register and I/O reads
            if addr < 0xD000 or addr >= 0xE000:
                # Record this read
                self.recent_reads.append((addr, value, self.cpu.pc))

                # Keep buffer size limited
                if len(self.recent_reads) > self.max_recent:
                    self.recent_reads.pop(0)

            return value

        self.cpu.read_byte = tracked_read

        # Initialize
        print("Initializing...")
        self.cpu.call_routine(self.cpu.init_addr, 0)

        # Run frames
        print(f"Running {frames} frames...\n")

        for frame in range(frames):
            # Clear recent reads for this frame
            self.recent_reads = []

            # Call play routine
            self.cpu.call_routine(self.cpu.play_addr, 0)

            # Check for frequency writes (notes triggered)
            for voice in range(3):
                freq_lo_addr = 0xD400 + voice * 7
                freq_hi_addr = 0xD401 + voice * 7

                freq_lo = self.cpu.sid_state.get(freq_lo_addr, 0)
                freq_hi = self.cpu.sid_state.get(freq_hi_addr, 0)
                freq = freq_lo | (freq_hi << 8)

                # Check if this looks like a new note (non-zero frequency)
                if freq > 0 and frame < 10:  # Only analyze first 10 frames
                    # Record the recent reads that led to this frequency write
                    if self.recent_reads:
                        self.freq_writes.append({
                            'frame': frame,
                            'voice': voice,
                            'freq': freq,
                            'reads': list(self.recent_reads)
                        })

        # Analyze the results
        self.analyze_sequence_locations()

    def analyze_sequence_locations(self):
        """Analyze memory reads to find sequence data locations."""
        print("=" * 70)
        print("SEQUENCE LOCATION ANALYSIS")
        print("=" * 70 + "\n")

        if not self.freq_writes:
            print("No frequency writes detected!")
            return

        print(f"Analyzed {len(self.freq_writes)} frequency writes\n")

        # Track all memory regions that were read before notes
        read_regions = {}

        for write_info in self.freq_writes:
            frame = write_info['frame']
            voice = write_info['voice']
            freq = write_info['freq']
            reads = write_info['reads']

            print(f"Frame {frame}, Voice {voice}, Freq ${freq:04X}:")
            print(f"  Recent memory reads (addr, value, PC):")

            for addr, value, pc in reads[-10:]:  # Show last 10 reads
                # Track this address region
                region = addr & 0xFF00  # Group by page
                read_regions[region] = read_regions.get(region, 0) + 1

                print(f"    ${addr:04X}: {value:02X}  (from PC=${pc:04X})")

            print()

        # Find most frequently read regions
        print("=" * 70)
        print("MOST FREQUENTLY READ MEMORY REGIONS")
        print("=" * 70 + "\n")

        sorted_regions = sorted(read_regions.items(), key=lambda x: x[1], reverse=True)

        print("Region | Read Count | Potential Use")
        print("-------+------------+--------------")

        for region, count in sorted_regions[:15]:
            potential_use = self.classify_region(region)
            print(f"${region:04X}  | {count:10} | {potential_use}")

        print("\n")
        print("=" * 70)
        print("SEQUENCE DATA CANDIDATES")
        print("=" * 70 + "\n")

        # Look for regions in the $1800-$1B00 range (typical for sequence data)
        candidates = [r for r, _ in sorted_regions if 0x1800 <= r < 0x1B00]

        if candidates:
            print("Likely sequence data regions:")
            for region in candidates[:5]:
                count = read_regions[region]
                print(f"  ${region:04X}-${region+0xFF:04X} ({count} reads)")
                print(f"    File offset: 0x{0x7E + region - 0x1000:04X}")
        else:
            print("No clear sequence data candidates found.")
            print("Try analyzing more frames or check these regions manually:")
            for region, count in sorted_regions[:5]:
                if region >= 0x1000:
                    print(f"  ${region:04X} ({count} reads)")

    def classify_region(self, region):
        """Classify memory region by typical use."""
        if region < 0x0100:
            return "Zero Page"
        elif region < 0x0200:
            return "Stack"
        elif 0x1000 <= region < 0x1800:
            return "Player Code/Tables"
        elif 0x1800 <= region < 0x1B00:
            return "Sequence/Music Data ⭐"
        elif 0x1B00 <= region < 0x2000:
            return "Orderlists/Other Data"
        elif 0xD000 <= region < 0xE000:
            return "I/O Registers"
        else:
            return "Other"

def main():
    import sys

    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'
    frames = 20  # Analyze first 20 frames

    if len(sys.argv) > 1:
        sid_file = sys.argv[1]
    if len(sys.argv) > 2:
        frames = int(sys.argv[2])

    tracer = SequenceTracer()
    tracer.trace_sid_file(sid_file, frames)

if __name__ == '__main__':
    main()
