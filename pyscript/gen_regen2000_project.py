"""
gen_regen2000_project.py
========================
Generate a Regenerator 2000 .regen2000proj file from a PRG binary and
a set of labels/data-type annotations.

Usage:
    python gen_regen2000_project.py [--prg FILE] [--out FILE]

Defaults to Stinsens_Last_Night_of_89.prg → .regen2000proj in same dir.

The generated file can be loaded directly in Regenerator 2000 (headless or TUI).
No running Regenerator instance required.
"""

import argparse
import base64
import gzip
import json
import os
import struct
import sys

# ---------------------------------------------------------------------------
# NP21 fixed-offset labels (same offset from load address in every NP21 file)
# Confirmed for Stinsen and Unboxed via Regenerator 2000 + zig64.
# ---------------------------------------------------------------------------
NP21_LABELS = {
    0x1000: ("INIT",   "Laxity NP21 INIT entry - JMP to init routine"),
    0x1003: ("PLAY",   "Laxity NP21 PLAY entry - JMP to play routine (addr varies per song)"),

    0x1989: ("tbl_filter_seq",
             "Multi-program filter table. $7F=end-of-program; "
             "bit7=1 NEW_STEP (bits6-4=mode HP/BP/LP, bits3-0=loop target); "
             "bit7=0 HOLD. 26 entries."),
    0x19A3: ("tbl_filter_speed",
             "Cutoff sweep delta per HOLD frame (16-bit accumulator low byte). 26 entries."),
    0x19BD: ("tbl_filter_resonance",
             "Resonance ($D417) written at NEW_STEP activation. 26 entries."),

    0x1200: ("effect_handler",
             "Entry: load ch_fx_arg,x. If bit7 set -> cmd_with_arg, else skip"),
    0x120A: ("cmd_with_arg",
             "Mask fx_arg to 6 bits, lookup tbl_fx_category, patch smc_cmd_handler dispatch"),
    0x1222: ("fx_slide_down",
             "Portamento slide down: speed from tbl_fx_speed, target from tbl_fx_param"),
    0x1233: ("fx_slide_up",   "Portamento slide up"),
    0x1244: ("fx_portamento_dn", "Portamento down with target"),
    0x125D: ("fx_portamento_up", "Portamento up with target"),
    0x127B: ("fx_set_volume",
             "Set master volume (lower nibble of tbl_fx_param[y] -> a1785 / $D418 bits 0-3)"),
    0x1286: ("cmd_dispatch",
             "SMC dispatch: sec; bcs [smc_cmd_handler]. Branch offset at $1288 patched by effect_handler."),
    0x12AA: ("fx_set_adsr",   "Set ADSR: attack/decay from tbl_fx_speed, sustain/release from tbl_fx_param"),
    0x12B9: ("fx_note_offset", "Set note offset and attack/decay from tbl_fx_speed"),
    0x12C2: ("fx_arpeggio_step",
             "Set arpeggio step: base_freq_hi and sustain/release from tbl_fx_param"),
    0x12CE: ("fx_portamento_delay", "Set portamento counter from tbl_fx_param"),
    0x12D7: ("fx_set_filter",
             "Start filter program: step_cnt=$80, seek target=tbl_fx_param[y]-1, seq_idx=0. "
             "tbl_fx_param[y] is Y-index into 26-entry filter table."),
    0x12ED: ("fx_set_pulse",
             "Start pulse sequence: pulse_seq_idx from tbl_fx_param, pulse_step_cnt=0"),

    0x1875: ("tbl_fx_category",
             "4-byte table: maps (fx_arg & $3F) to effect category. "
             "Lower nibble = dispatch index into tbl_effect_type."),
    0x1896: ("tbl_fx_speed",
             "26-byte effect speed/direction table. "
             "Indexed by (fx_arg & $3F). Used as portamento speed; bit7=direction."),
    0x18B7: ("tbl_fx_param",
             "21-byte effect secondary parameter. "
             "Indexed by (fx_arg & $3F). Used as portamento target, filter seek, arpeggio step, etc."),
}

# Data-type regions: (start_addr, end_addr_exclusive, block_type)
# block_type must be a valid Regenerator 2000 BlockType variant name.
NP21_DATA_REGIONS = [
    (0x1989, 0x19A3, "DataByte"),   # tbl_filter_seq         (26 entries)
    (0x19A3, 0x19BD, "DataByte"),   # tbl_filter_speed        (26 entries)
    (0x19BD, 0x19D7, "DataByte"),   # tbl_filter_resonance    (26 entries)
    (0x1875, 0x1879, "DataByte"),   # tbl_fx_category         (4 entries)
    (0x1896, 0x18B7, "DataByte"),   # tbl_fx_speed            (26 entries + 1 padding)
    (0x18B7, 0x18CC, "DataByte"),   # tbl_fx_param            (21 entries)
]


def encode_raw_data(data: bytes) -> str:
    """gzip-compress then base64-encode, matching Regenerator's encode_raw_data_to_base64."""
    compressed = gzip.compress(data, compresslevel=6)
    return base64.b64encode(compressed).decode("ascii")


def compress_blocks(block_types: list[str]) -> list[dict]:
    """
    Run-length-encode a list of block type strings into Regenerator block ranges.
    Mirrors Regenerator's compress_block_types() in project.rs.
    """
    if not block_types:
        return []
    blocks = []
    start = 0
    current = block_types[0]
    for i, t in enumerate(block_types[1:], 1):
        if t != current:
            blocks.append({"start": start, "end": i - 1, "type_": current, "collapsed": False})
            start = i
            current = t
    blocks.append({"start": start, "end": len(block_types) - 1, "type_": current, "collapsed": False})
    return blocks


def generate_project(prg_path: str) -> dict:
    """Generate a ProjectState dict from a PRG file + NP21 annotations."""
    with open(prg_path, "rb") as f:
        prg = f.read()

    if len(prg) < 2:
        raise ValueError(f"PRG too short: {len(prg)} bytes")

    origin = struct.unpack_from("<H", prg, 0)[0]
    raw_data = prg[2:]
    size = len(raw_data)

    print(f"  PRG: {os.path.basename(prg_path)}")
    print(f"  Load address: ${origin:04X}")
    print(f"  Binary size:  {size} bytes (${size:04X})")

    # --- Build block_types list (indexed by byte offset from origin) ---
    block_types = ["Code"] * size

    for (start_addr, end_addr_excl, btype) in NP21_DATA_REGIONS:
        if start_addr < origin or end_addr_excl > origin + size:
            print(f"  [SKIP] Region ${start_addr:04X}-${end_addr_excl:04X} out of range")
            continue
        s = start_addr - origin
        e = end_addr_excl - origin
        for i in range(s, e):
            block_types[i] = btype
        print(f"  [DataByte] ${start_addr:04X}–${end_addr_excl - 1:04X}  ({e - s} bytes)")

    blocks = compress_blocks(block_types)
    print(f"  Compressed to {len(blocks)} block(s)")

    # --- Build labels dict (keyed by str(address)) ---
    labels: dict[str, list[dict]] = {}
    for addr, (name, cmt) in sorted(NP21_LABELS.items()):
        if addr < origin or addr >= origin + size:
            print(f"  [SKIP] Label {name} @ ${addr:04X} out of range")
            continue
        labels[str(addr)] = [{"name": name, "label_type": "UserDefined", "kind": "User"}]
        print(f"  [Label] {name} @ ${addr:04X}")

    # --- Build side comments dict ---
    side_comments: dict[str, str] = {}
    for addr, (name, cmt) in sorted(NP21_LABELS.items()):
        if addr < origin or addr >= origin + size:
            continue
        if cmt:
            side_comments[str(addr)] = cmt

    # --- Encode binary ---
    raw_b64 = encode_raw_data(raw_data)

    project = {
        "version": 1,
        "origin": origin,
        "raw_data_base64": raw_b64,
        "blocks": blocks,
        "labels": labels,
        "user_side_comments": side_comments,
        "user_line_comments": {},
        "immediate_value_formats": {},
        "bookmarks": {},
    }
    return project


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    default_prg = os.path.join(project_root, "SID", "Stinsens_Last_Night_of_89.prg")

    parser = argparse.ArgumentParser(
        description="Generate a Regenerator 2000 .regen2000proj from a PRG + NP21 labels"
    )
    parser.add_argument("--prg", default=default_prg, help="Input PRG file")
    parser.add_argument("--out", default=None,
                        help="Output .regen2000proj file (default: same dir/name as PRG)")
    args = parser.parse_args()

    prg_path = args.prg
    if not os.path.isfile(prg_path):
        print(f"ERROR: PRG not found: {prg_path}")
        sys.exit(1)

    out_path = args.out
    if out_path is None:
        base = os.path.splitext(prg_path)[0]
        out_path = base + ".regen2000proj"

    print(f"\n=== Regenerator 2000 Project Generator ===")
    project = generate_project(prg_path)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"\n  Wrote: {out_path} ({size_kb:.1f} KB)")
    print(f"\nLoad in Regenerator 2000:")
    print(f"  regenerator2000.exe \"{out_path}\" --mcp-server")
    print(f"  regenerator2000.exe \"{out_path}\" --headless --mcp-server --mcp-port 3000")


if __name__ == "__main__":
    main()
