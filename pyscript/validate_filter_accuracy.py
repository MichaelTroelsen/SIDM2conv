"""
validate_filter_accuracy.py - Filter accuracy validation for Laxity NP21 SID files.

Compares filter tables extracted from the SID binary against ground-truth
SID register writes captured by the zig64 cycle-accurate tracer.

Usage:
    python pyscript/validate_filter_accuracy.py [options]

Options:
    --sid FILE          SID file (default: SID/Stinsens_Last_Night_of_89.sid)
    --prg FILE          PRG file (default: SID/Stinsens_Last_Night_of_89.prg)
    --csv FILE          zig64 trace CSV (default: SID/stinsen_sid_trace_300frames.csv)
    --load-addr ADDR    Load address in hex (default: 1000)
    --verbose           Show full table dumps
"""

import argparse
import csv
import os
import sys


# Laxity NP21 fixed offsets from load address (confirmed via Regenerator 2000 + zig64)
NP21_SEQ_OFFSET  = 0x0989   # tbl_filter_seq:       cutoff control + mode bits per step
NP21_SPD_OFFSET  = 0x09A3   # tbl_filter_speed:     cutoff sweep delta per step
NP21_RES_OFFSET  = 0x09BD   # tbl_filter_resonance: resonance/routing value per step
NP21_MAX_ENTRIES = 26        # Maximum entries per filter program
NP21_END_MARKER  = 0x7F     # End-of-program marker in tbl_filter_seq
SID_HEADER_SIZE  = 0x7C     # 124 bytes


# zig64 CSV column names for filter registers
FILTER_REGISTERS = {
    'filter_res_control',   # $D417: resonance + voice routing
    'filter_freq_hi',       # $D416: filter cutoff high byte (STY in NP21)
    'filter_freq_lo',       # $D415: filter cutoff low byte
    'filter_mode_volume',   # $D418: filter mode + master volume
}


def load_prg_data(prg_path: str, sid_path: str) -> tuple[bytes, int]:
    """Load PRG data. Returns (data_bytes, load_addr)."""
    if os.path.exists(prg_path):
        with open(prg_path, 'rb') as f:
            data = f.read()
        # PRG: first 2 bytes = load address (little-endian)
        load_addr = data[0] | (data[1] << 8)
        return data[2:], load_addr
    elif os.path.exists(sid_path):
        with open(sid_path, 'rb') as f:
            raw = f.read()
        # SID header: offset 8-9 = load address (big-endian)
        sid_load = (raw[8] << 8) | raw[9]
        data = raw[SID_HEADER_SIZE:]
        if sid_load == 0:
            # PRG-embedded: first 2 bytes of data are the actual load address
            load_addr = data[0] | (data[1] << 8)
            return data[2:], load_addr
        return data, sid_load
    else:
        raise FileNotFoundError(f"Neither {prg_path} nor {sid_path} found")


def extract_filter_tables(data: bytes, load_addr: int, full: bool = False) -> dict:
    """Extract the three NP21 filter tables from binary data.

    The NP21 filter table is a collection of PROGRAMS at different Y indices,
    separated by $7F markers. The 'steps' list stops at the first $7F (first
    program boundary). 'all_steps' contains all 26 entries for cross-program search.
    """
    seq_off  = NP21_SEQ_OFFSET
    spd_off  = NP21_SPD_OFFSET
    res_off  = NP21_RES_OFFSET

    # Validate bounds
    needed = res_off + NP21_MAX_ENTRIES
    if needed > len(data):
        raise ValueError(
            f"Data too short: need {needed} bytes from load addr, have {len(data)}"
        )

    steps = []       # first program only (stops at $7F)
    all_steps = []   # full 26-entry table (all programs)
    for i in range(NP21_MAX_ENTRIES):
        seq = data[seq_off + i]
        spd = data[spd_off + i]
        res = data[res_off + i]
        all_steps.append({'idx': i, 'seq': seq, 'spd': spd, 'res': res})
        if not steps or steps[-1]['seq'] != NP21_END_MARKER:
            steps.append({'idx': i, 'seq': seq, 'spd': spd, 'res': res})
            if seq == NP21_END_MARKER:
                pass  # keep going for all_steps but steps is now "done"

    return {
        'load_addr': load_addr,
        'tbl_filter_seq_addr':       load_addr + seq_off,
        'tbl_filter_speed_addr':     load_addr + spd_off,
        'tbl_filter_resonance_addr': load_addr + res_off,
        'steps': steps,
        'all_steps': all_steps,
    }


def parse_filter_trace(csv_path: str) -> list[dict]:
    """Parse zig64 CSV and return only filter-register rows."""
    rows = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['register'] in FILTER_REGISTERS:
                rows.append({
                    'frame':    int(row['frame']),
                    'cycle':    int(row['cycle']),
                    'register': row['register'],
                    'old':      int(row['old_val'].lstrip('$'), 16),
                    'new':      int(row['new_val'].lstrip('$'), 16),
                })
    return rows


def group_filter_events(trace: list[dict]) -> list[dict]:
    """Group filter writes by frame for easier analysis."""
    events = {}
    for row in trace:
        frame = row['frame']
        if frame not in events:
            events[frame] = {}
        events[frame][row['register']] = row['new']
    return events


def decode_np21_seq_byte(seq: int) -> str:
    """Decode a tbl_filter_seq byte into a human-readable description."""
    if seq == NP21_END_MARKER:
        return "END ($7F)"
    if seq & 0x80:
        mode_bits  = (seq >> 4) & 0x07
        target_idx = seq & 0x0F
        mode_str = []
        if mode_bits & 0x04: mode_str.append("LP")
        if mode_bits & 0x02: mode_str.append("BP")
        if mode_bits & 0x01: mode_str.append("HP")
        return f"NEW_STEP mode=[{'|'.join(mode_str) or 'off'}] target={target_idx}"
    else:
        return f"HOLD duration={seq}"


def print_table_dump(tables: dict, verbose: bool = False) -> None:
    """Print a formatted dump of the three filter tables."""
    print("\n=== Laxity NP21 Filter Tables (from binary) ===")
    print(f"  tbl_filter_seq      @ ${tables['tbl_filter_seq_addr']:04X}")
    print(f"  tbl_filter_speed    @ ${tables['tbl_filter_speed_addr']:04X}")
    print(f"  tbl_filter_resonance@ ${tables['tbl_filter_resonance_addr']:04X}")
    print()

    steps = tables['steps']
    if not verbose and len(steps) > 8:
        display = steps[:8]
        truncated = True
    else:
        display = steps
        truncated = False

    print(f"  {'#':>3}  {'seq':>5}  {'spd':>5}  {'res':>5}  interpretation")
    print(f"  {'---':>3}  {'---':>5}  {'---':>5}  {'---':>5}  ---")
    for i, s in enumerate(display):
        interp = decode_np21_seq_byte(s['seq'])
        print(f"  {i:>3}  ${s['seq']:02X}     ${s['spd']:02X}     ${s['res']:02X}     {interp}")

    if truncated:
        print(f"  ... ({len(steps) - 8} more entries, use --verbose to see all)")


def print_trace_summary(events: dict) -> None:
    """Print a summary of observed filter activity from the trace."""
    frames = sorted(events.keys())
    if not frames:
        print("\n  No filter writes found in trace.")
        return

    print(f"\n=== Observed Filter Activity (zig64 trace) ===")
    print(f"  Filter-register frames: {len(frames)}")
    print(f"  First filter write:     frame {frames[0]}")
    print()

    # Find key events
    activation = None
    program_steps = []
    for frame in frames:
        ev = events[frame]
        if 'filter_res_control' in ev and activation is None:
            activation = (frame, ev)
            program_steps.append(frame)
        elif 'filter_mode_volume' in ev and frame != frames[0]:
            # Mode change = new filter program step
            if frame not in program_steps:
                program_steps.append(frame)

    print(f"  {'Frame':>6}  {'res_ctrl':>9}  {'freq_hi':>8}  {'freq_lo':>8}  {'mode_vol':>9}  event")
    print(f"  {'------':>6}  {'--------':>9}  {'-------':>8}  {'-------':>8}  {'--------':>9}  -----")

    printed = set()
    for frame in sorted(events.keys()):
        ev = events[frame]
        # Print activation frame and each program step change
        is_key = ('filter_res_control' in ev or
                  'filter_mode_volume' in ev or
                  frame in program_steps)
        if is_key and frame not in printed:
            res  = f"${ev.get('filter_res_control', 0):02X}" if 'filter_res_control' in ev else "  --"
            fhi  = f"${ev.get('filter_freq_hi', 0):02X}"      if 'filter_freq_hi'     in ev else "  --"
            flo  = f"${ev.get('filter_freq_lo', 0):02X}"      if 'filter_freq_lo'     in ev else "  --"
            mvol = f"${ev.get('filter_mode_volume', 0):02X}"  if 'filter_mode_volume' in ev else "  --"
            note = ""
            if 'filter_res_control' in ev:
                note = "<-- filter ON"
            elif 'filter_mode_volume' in ev and frame != frames[0]:
                note = "<-- mode change"
            print(f"  {frame:>6}  {res:>9}  {fhi:>8}  {flo:>8}  {mvol:>9}  {note}")
            printed.add(frame)

    # Also show sweep range
    hi_vals = [ev['filter_freq_hi'] for ev in events.values() if 'filter_freq_hi' in ev]
    if hi_vals:
        print(f"\n  Freq_hi sweep range: ${min(hi_vals):02X}..${max(hi_vals):02X}")
        # Estimate delta
        frames_with_hi = [(f, events[f]['filter_freq_hi'])
                          for f in sorted(events.keys())
                          if 'filter_freq_hi' in events[f]]
        if len(frames_with_hi) >= 2:
            deltas = [abs(frames_with_hi[i][1] - frames_with_hi[i-1][1])
                      for i in range(1, min(6, len(frames_with_hi)))
                      if abs(frames_with_hi[i][0] - frames_with_hi[i-1][0]) == 1]
            if deltas:
                avg_delta = sum(deltas) / len(deltas)
                print(f"  Observed sweep delta per frame: ~{avg_delta:.1f}")


def validate(tables: dict, events: dict) -> list[str]:
    """Cross-validate extracted tables against trace data. Returns a list of result lines."""
    results = []
    frames = sorted(events.keys())
    if not frames:
        return ["SKIP: no filter writes in trace"]

    steps = tables['steps']
    if not steps:
        return ["SKIP: no filter steps extracted from binary"]

    # Find key trace events
    first_res_frame = next((f for f in frames if 'filter_res_control' in events[f]), None)
    mode_change_frame = next(
        (f for f in frames
         if 'filter_mode_volume' in events[f] and f > (first_res_frame or 0)),
        None
    )

    # --- Check 1: Resonance value ---
    # All NP21 filter steps with the same resonance value write it to $D417.
    # The first write at filter activation should match tbl_filter_resonance[0].
    if first_res_frame is not None:
        observed_res = events[first_res_frame]['filter_res_control']
        extracted_res = steps[0]['res']
        match = "OK" if observed_res == extracted_res else "MISMATCH"
        results.append(
            f"[{match}] Resonance[0]: binary=${extracted_res:02X}, "
            f"trace=${observed_res:02X} at frame {first_res_frame}"
        )

    # --- Check 2: Sweep speed ---
    # NP21 tbl_filter_speed = 11-bit cutoff decrement per frame.
    # freq_hi occupies the upper 3 bits of the 11-bit cutoff:
    #   11-bit cutoff = (freq_hi << 3) | (freq_lo >> 5)
    # So observed freq_hi delta per frame ≈ spd / 8.
    #
    # Step 0 in the binary often has spd=0 (init/setup entry with target=15).
    # The first real sweep step is step 1. We find the best-matching step.
    frames_with_hi = [(f, events[f]['filter_freq_hi'])
                      for f in sorted(events.keys())
                      if 'filter_freq_hi' in events[f]]
    # Measure delta during the first sweep segment (before first mode change)
    sweep_pairs = [(f, v) for f, v in frames_with_hi
                   if (first_res_frame is None or f >= first_res_frame)
                   and (mode_change_frame is None or f < mode_change_frame)]
    if len(sweep_pairs) >= 2:
        consecutive_deltas = [
            abs(sweep_pairs[i][1] - sweep_pairs[i-1][1])
            for i in range(1, len(sweep_pairs))
            if sweep_pairs[i][0] - sweep_pairs[i-1][0] == 1
        ]
        if consecutive_deltas:
            avg_delta = sum(consecutive_deltas) / len(consecutive_deltas)
            # Find which extracted step best explains the observed delta (spd/8 ≈ avg_delta)
            best_step_idx = None
            best_step_err = float('inf')
            for i, s in enumerate(steps):
                if s['seq'] == NP21_END_MARKER:
                    break
                expected = s['spd'] / 8.0
                err = abs(expected - avg_delta)
                if err < best_step_err:
                    best_step_err = err
                    best_step_idx = i
            if best_step_idx is not None:
                bs = steps[best_step_idx]
                expected = bs['spd'] / 8.0
                match = "OK" if best_step_err <= 1.5 else "APPROX"
                results.append(
                    f"[{match}] Sweep speed: step[{best_step_idx}].spd=${bs['spd']:02X} "
                    f"(~{expected:.1f} freq_hi/frame), observed ~{avg_delta:.1f} freq_hi/frame"
                )

    # --- Check 3: Filter mode per program step ---
    # VERIFIED: NP21 seq_byte bit7=1 = NEW_STEP. Bits 6-4 (seq & $70) map directly to
    # SID $D418 bits 6-4 (bit6=HP, bit5=BP, bit4=LP). No further decoding needed.
    # The active filter program may start at a Y index > 0 (e.g. Y=19 for Stinsen).
    # We search all_steps for any NEW_STEP entry whose mode bits match each observed event.
    mode_frames = [f for f in frames if 'filter_mode_volume' in events[f]
                   and f >= (first_res_frame or 0)]
    all_steps = tables.get('all_steps', tables['steps'])
    for frame in mode_frames:
        mode_vol = events[frame]['filter_mode_volume']
        obs_mode = (mode_vol >> 4) & 0x07
        matching = [s for s in all_steps
                    if (s['seq'] & 0x80) and s['seq'] != NP21_END_MARKER
                    and ((s['seq'] & 0x70) >> 4) == obs_mode]
        if matching:
            m = matching[0]
            results.append(
                f"[OK] Mode frame {frame}: D418=${mode_vol:02X} mode=0b{obs_mode:03b}, "
                f"matched by all_steps[{m['idx']}] seq=${m['seq']:02X} "
                f"(seq&$70=${m['seq'] & 0x70:02X})"
            )
        else:
            results.append(
                f"[MISMATCH] Mode frame {frame}: D418=${mode_vol:02X} mode=0b{obs_mode:03b}, "
                f"no matching NEW_STEP found in table"
            )

    # --- Check 4: Address sanity ---
    # Verify the three table addresses are correct by checking resonance match
    # (already done in Check 1). Also confirm data offset is non-trivial.
    load_addr = tables['load_addr']
    results.append(
        f"[INFO] Addresses: seq=${tables['tbl_filter_seq_addr']:04X}, "
        f"spd=${tables['tbl_filter_speed_addr']:04X}, "
        f"res=${tables['tbl_filter_resonance_addr']:04X} "
        f"(offsets $0989/$09A3/$09BD from load ${load_addr:04X})"
    )

    # --- Check 5: Filter program steps count ---
    mode_changes = [f for f in frames
                    if 'filter_mode_volume' in events[f]
                    and f > (first_res_frame or 0)]
    observed_steps = 1 + len(mode_changes)
    extracted_steps = len([s for s in steps if s['seq'] != NP21_END_MARKER])
    results.append(
        f"[INFO] Program size: binary={extracted_steps} non-END entries, "
        f"trace={observed_steps} mode-activation events"
    )

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate SIDM2 filter accuracy against zig64 trace")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sid_dir = os.path.join(project_root, 'SID')

    parser.add_argument('--sid',       default=os.path.join(sid_dir, 'Stinsens_Last_Night_of_89.sid'))
    parser.add_argument('--prg',       default=os.path.join(sid_dir, 'Stinsens_Last_Night_of_89.prg'))
    parser.add_argument('--csv',       default=os.path.join(sid_dir, 'stinsen_sid_trace_300frames.csv'))
    parser.add_argument('--load-addr', default='1000',
                        help='Load address in hex (default: 1000, auto-detected from PRG header)')
    parser.add_argument('--verbose',   action='store_true', help='Show full table dumps')
    args = parser.parse_args()

    print("=== SIDM2 Filter Accuracy Validator ===")
    print(f"  SID:  {args.sid}")
    print(f"  PRG:  {args.prg}")
    print(f"  CSV:  {args.csv}")

    # Load binary
    try:
        data, load_addr = load_prg_data(args.prg, args.sid)
        print(f"\n  Load address: ${load_addr:04X}")
        print(f"  Binary size:  {len(data)} bytes (${len(data):04X})")
    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract filter tables
    try:
        tables = extract_filter_tables(data, load_addr)
    except (ValueError, IndexError) as e:
        print(f"\nERROR extracting filter tables: {e}", file=sys.stderr)
        sys.exit(1)

    print_table_dump(tables, verbose=args.verbose)

    # Load trace
    if not os.path.exists(args.csv):
        print(f"\nWARN: CSV trace not found: {args.csv}")
        print("  Run zig64 tracer first to generate ground truth data.")
        print("  See memory/zig64.md for instructions.")
        sys.exit(0)

    trace = parse_filter_trace(args.csv)
    events = group_filter_events(trace)
    print_trace_summary(events)

    # Cross-validate
    print("\n=== Validation Results ===")
    results = validate(tables, events)
    all_ok = all(r.startswith('[OK]') or r.startswith('[INFO]') for r in results)
    for r in results:
        print(f"  {r}")

    print()
    if all_ok:
        print("  OVERALL: PASS - Filter tables match ground-truth trace data.")
    else:
        print("  OVERALL: WARNING - Some checks did not match. Review above.")

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
