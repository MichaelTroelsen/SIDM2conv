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
    0x1989: ("tbl_filter_seq",        "$7F = end-of-program; cutoff control + mode bits per step"),
    0x19A3: ("tbl_filter_speed",      "Cutoff sweep delta per step"),
    0x19BD: ("tbl_filter_resonance",  "Resonance value per step"),
}

NP21_DATA_REGIONS = [
    # (start, end_exclusive, description)
    (0x1989, 0x199D, "byte"),   # tbl_filter_seq    (20 entries max)
    (0x19A3, 0x19B7, "byte"),   # tbl_filter_speed  (20 entries max)
    (0x19BD, 0x19D1, "byte"),   # tbl_filter_resonance (20 entries max)
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

    def set_comment(self, addr, text):
        return self.call("r2000_set_comment", {"address": addr, "comment": text})

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
