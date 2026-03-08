"""
regen2000_label_laxity_np21.py
================================
Apply Laxity NewPlayer v21 (NP21) memory map labels to a Regenerator 2000
MCP instance. Works with any port (default 3000).

Usage:
    python regen2000_label_laxity_np21.py [--port PORT] [--verify-only]

Requirements:
    pip install requests

The Laxity NP21 driver has two regions:
  - Fixed-offset tables (same offset from load address in every NP21 file)
  - Song-specific data (varies per file)

This script labels only the FIXED-OFFSET tables, which are the same
regardless of which NP21 SID file is loaded.
"""

import argparse
import json
import uuid
import sys

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Laxity NP21 fixed-offset constants (relative to load address $1000)
# Confirmed via Regenerator 2000 disassembly of two different NP21 SID files:
#   - Stinsens_Last_Night_of_89 (Stinsen)
#   - Unboxed_Ending_8580       (DRAX/Laxity)
# ---------------------------------------------------------------------------
NP21_LABELS = {
    # Player entry points (always at $1000 and $1003)
    0x1000: ("INIT",   "Laxity NP21 INIT entry - JMP to init routine"),
    0x1003: ("PLAY",   "Laxity NP21 PLAY entry - JMP to play routine (addr varies per song)"),

    # Filter sequencer tables (confirmed identical offset in all NP21 files)
    0x1989: ("tbl_filter_seq",        "Multi-program filter table. $7F=end-of-program; bit7=1 NEW_STEP (bits6-4=mode, bits3-0=loop target); bit7=0 HOLD. 26 entries."),
    0x19A3: ("tbl_filter_speed",      "Cutoff sweep delta per HOLD frame (16-bit accumulator low byte). 26 entries."),
    0x19BD: ("tbl_filter_resonance",  "Resonance ($D417) written at NEW_STEP activation. 26 entries."),

    # Effect/command dispatch tables (fixed offset in NP21, Stinsen-verified)
    0x1200: ("effect_handler",    "Entry: load ch_fx_arg,x. If bit7 set -> cmd_with_arg, else skip"),
    0x120A: ("cmd_with_arg",      "Mask fx_arg to 6 bits, lookup tbl_fx_category, patch smc_cmd_handler dispatch"),
    0x1222: ("fx_slide_down",     "Portamento slide down: speed from tbl_fx_speed, target from tbl_fx_param"),
    0x1233: ("fx_slide_up",       "Portamento slide up"),
    0x1244: ("fx_portamento_dn",  "Portamento down with target"),
    0x125D: ("fx_portamento_up",  "Portamento up with target"),
    0x127B: ("fx_set_volume",     "Set master volume (lower nibble of tbl_fx_param[y] -> a1785 / $D418 bits 0-3)"),
    0x1286: ("cmd_dispatch",      "SMC dispatch: sec; bcs [smc_cmd_handler]. Branch offset at $1288 patched by effect_handler."),
    0x12AA: ("fx_set_adsr",       "Set ADSR: attack/decay from tbl_fx_speed, sustain/release from tbl_fx_param"),
    0x12B9: ("fx_note_offset",    "Set note offset and attack/decay from tbl_fx_speed"),
    0x12C2: ("fx_arpeggio_step",  "Set arpeggio step: base_freq_hi and sustain/release from tbl_fx_param"),
    0x12CE: ("fx_portamento_delay", "Set portamento counter from tbl_fx_param"),
    0x12D7: ("fx_set_filter",     "Start filter program: step_cnt=$80, seek target=tbl_fx_param[y]-1, seq_idx=0. tbl_fx_param[y] is Y-index into 26-entry filter table."),
    0x12ED: ("fx_set_pulse",      "Start pulse sequence: pulse_seq_idx from tbl_fx_param, pulse_step_cnt=0"),

    # Effect parameter tables
    0x1875: ("tbl_fx_category",   "4-byte table: maps (fx_arg & $3F) to effect category. Lower nibble = dispatch index into tbl_effect_type."),
    0x1896: ("tbl_fx_speed",      "26-byte effect speed/direction table. Indexed by (fx_arg & $3F). Used as portamento speed; bit7=direction."),
    0x18B7: ("tbl_fx_param",      "21-byte effect secondary parameter. Indexed by (fx_arg & $3F). Used as portamento target, filter seek, arpeggio step, etc."),
}

NP21_DATA_REGIONS = [
    # (start, end_exclusive, description)
    (0x1989, 0x19A3, "byte"),   # tbl_filter_seq         (26 entries)
    (0x19A3, 0x19BD, "byte"),   # tbl_filter_speed        (26 entries)
    (0x19BD, 0x19D7, "byte"),   # tbl_filter_resonance    (26 entries)
    (0x1875, 0x1879, "byte"),   # tbl_fx_category         (4 entries)
    (0x1896, 0x18B6, "byte"),   # tbl_fx_speed            (26 entries, last byte $18B6 is $00 padding)
    (0x18B7, 0x18CC, "byte"),   # tbl_fx_param            (21 entries)
]


class RegenMCP:
    def __init__(self, port=3000):
        self.base = f"http://127.0.0.1:{port}/mcp"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self.session_id = None

    def connect(self):
        r = requests.post(
            self.base,
            json={
                "jsonrpc": "2.0",
                "id": "init",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "regen2000_label_laxity_np21", "version": "1.0"},
                },
            },
            headers=self.headers,
            stream=True,
            timeout=10,
        )
        self.session_id = r.headers.get("mcp-session-id")
        if not self.session_id:
            raise RuntimeError("No session ID returned from MCP server")
        for line in r.iter_lines(decode_unicode=True):
            if line.startswith("data:"):
                d = json.loads(line[5:])
                info = d.get("result", {}).get("serverInfo", {})
                print(f"Connected to: {info.get('name')} {info.get('version')}")
        # Send initialized notification
        requests.post(
            self.base,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers={**self.headers, "mcp-session-id": self.session_id},
            timeout=5,
        )

    def call(self, name, args=None):
        h = {**self.headers, "mcp-session-id": self.session_id}
        r = requests.post(
            self.base,
            json={
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {"name": name, "arguments": args or {}},
            },
            headers=h,
            stream=True,
            timeout=15,
        )
        for line in r.iter_lines(decode_unicode=True):
            if line.startswith("data:"):
                d = json.loads(line[5:])
                if "result" in d:
                    content = d["result"].get("content", [])
                    return content[0].get("text", "") if content else ""
                elif "error" in d:
                    return f"ERR: {d['error']['message']}"
        return "NO_RESPONSE"

    def binary_info(self):
        return self.call("r2000_get_binary_info")

    def set_label(self, addr, name):
        return self.call("r2000_set_label_name", {"address": addr, "name": name})

    def set_comment(self, addr, text, ctype="line"):
        return self.call("r2000_set_comment", {"address": addr, "comment": text, "type": ctype})

    def set_dtype(self, start, end, dtype):
        return self.call("r2000_set_data_type", {
            "start_address": start,
            "end_address": end,
            "data_type": dtype,
        })

    def read_region(self, start, end):
        return self.call("r2000_read_region", {"start_address": start, "end_address": end})

    def save(self):
        return self.call("r2000_save_project")


def verify_np21_offsets(mcp):
    """Read filter tables and confirm they look like NP21 data."""
    print("\n--- Verifying NP21 filter table offsets ---")
    issues = []

    for start, end, _ in NP21_DATA_REGIONS:
        raw = mcp.read_region(start, end)
        # Check that $7F appears (end-of-program marker used in NP21 filter seq)
        label = NP21_LABELS.get(start, (hex(start),))[0]
        if "$7f" in raw.lower() or "7f" in raw.lower():
            print(f"  [OK ] {label} @ ${start:04X}: contains $7F markers")
        else:
            print(f"  [WARN] {label} @ ${start:04X}: no $7F marker found - may not be NP21")
            issues.append(start)

    return len(issues) == 0


def apply_np21_labels(mcp, verify=True):
    print("\n--- Applying Laxity NP21 labels ---")

    # Binary info
    info = mcp.binary_info()
    print(f"Binary: {info}")

    if verify:
        ok = verify_np21_offsets(mcp)
        if not ok:
            print("\nWARNING: Some offsets may not match NP21 structure. Continuing anyway.")

    # Mark data regions
    print("\n--- Marking data regions ---")
    for start, end, dtype in NP21_DATA_REGIONS:
        result = mcp.set_dtype(start, end, dtype)
        status = "OK" if "ERR" not in result else "FAIL"
        print(f"  [{status}] dtype ${start:04X}-${end:04X} -> {dtype}: {result[:50]}")

    # Apply labels and comments
    print("\n--- Applying labels ---")
    for addr, (name, cmt) in NP21_LABELS.items():
        r1 = mcp.set_label(addr, name)
        r2 = mcp.set_comment(addr, cmt)
        ok1 = "ERR" not in r1
        ok2 = "ERR" not in r2
        status = "OK" if ok1 and ok2 else "FAIL"
        print(f"  [{status}] ${addr:04X} -> {name}")

    # Save
    print("\n--- Saving project ---")
    result = mcp.save()
    if "ERR" in result or "No active project" in result:
        print(f"  [NOTE] {result}")
        print("  To save: use File -> Save As in the Regenerator 2000 TUI window.")
    else:
        print(f"  [OK] {result}")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="Apply Laxity NP21 labels to Regenerator 2000")
    parser.add_argument("--port", type=int, default=3000, help="MCP server port (default: 3000)")
    parser.add_argument("--verify-only", action="store_true", help="Only verify, don't label")
    args = parser.parse_args()

    mcp = RegenMCP(port=args.port)
    try:
        mcp.connect()
    except Exception as e:
        print(f"ERROR: Cannot connect to Regenerator 2000 on port {args.port}: {e}")
        sys.exit(1)

    if args.verify_only:
        verify_np21_offsets(mcp)
    else:
        apply_np21_labels(mcp)


if __name__ == "__main__":
    main()
