"""Detect Vibrants V20 (pre-NP21) player files.

The 14 Class-C all-notes files in the Laxity corpus use 5+ distinct
pre-NP21 player variants from 1987-1990 (Wizax, Yield Point Music,
2000 A.D., Zetrex, Flexible Arts, Laxity-1990). See
`memory/vibrants-v20-findings.md`.

These files have:
- NO valid NP21 ch_seq_ptr table at the canonical `$0A1C/$0A1F`
  offsets (typically because the file is too small OR the bytes
  there are unrelated to voice sequence pointers).
- ch_seq_ptr autodetector finds NO valid table (returns None).
- Per-voice frequency lookup tables + small note byte streams (each
  variant at different addresses; no shared encoding).

Conversion-time advisory only — the detector returns a short label
that the caller logs at info level. No code path changes.

We use a simple set of heuristics that match the empirical inventory:
- copyright contains one of the Vibrants-class year/label strings
- AND file size is < $2000 (typical V20 binaries are 1.6–3 KB,
  while NP21 binaries are 8 KB+)

These heuristics are loose and may match other small SIDs not in
the V20 inventory. That's OK — the message is informational, not a
behavior change.
"""
from __future__ import annotations
from typing import Optional


# Copyright substrings observed in the 14 Class-C inventory.
# Order: most-common first.
V20_COPYRIGHT_HINTS = (
    'Wizax',
    'Yield Point',
    '2000 A.D.',
    'Zetrex',
    'Flexible Arts',
)


# Below this binary size, NP21 is implausible (NP21 driver code +
# data is typically 8 KB+). V20 binaries are 1.5–3.5 KB.
V20_MAX_SIZE = 0x1000


# Signature bytes for the 1988 2000 A.D. player (Galax_it_y + Echo_Beat).
# After the 6-byte JMP-table prefix, the player has this fixed pattern.
# RE'd 2026-05-12 — see `memory/vibrants-v20-findings.md`. Stream
# extraction notes (Galax_it_y only — Echo_Beat has different offsets):
#   - per-voice freq LUT at $150F (lo) / $1510 (hi), 2-byte cells
#   - V0 note stream at $17A4-$17A6 (3 bytes)
#   - V1 note stream at $1795-$17A3 (15 bytes; cmd + value pairs)
#   - V2 stream minimal ($1788, $178E only)
#   - Per-voice freq scratches at $14C5/$14C8 (V0)
_AD_2000_SIG_OFFSET = 6
_AD_2000_SIG_BYTES = bytes([0x2C, 0xA3])   # BIT $A3XX
_AD_2000_SIG_PATTERN_AFTER = bytes([0x30, 0x01, 0x60, 0xA9, 0x00, 0x8D, 0x0E])


def _is_2000_ad_cluster(c64_data: bytes) -> bool:
    """Player signature match for 1988 2000 A.D. cluster (Galax_it_y +
    Echo_Beat share the same player at different loads). James_Bond
    has a different player and won't match."""
    if len(c64_data) < 0x20:
        return False
    if c64_data[_AD_2000_SIG_OFFSET : _AD_2000_SIG_OFFSET + 2] != _AD_2000_SIG_BYTES:
        return False
    # Pattern after the load-addr-dependent high byte at offset +2
    if c64_data[_AD_2000_SIG_OFFSET + 3 : _AD_2000_SIG_OFFSET + 3 + len(_AD_2000_SIG_PATTERN_AFTER)] != _AD_2000_SIG_PATTERN_AFTER:
        return False
    return True


def detect_vibrants_v20(c64_data: bytes, load_addr: int,
                         copyright_str: str = '') -> Optional[str]:
    """Return a short variant label (e.g., "1988 2000 A.D.") if the
    file matches Vibrants V20 heuristics, else None.

    Args:
        c64_data: raw c64 binary payload (sans 2-byte PRG header)
        load_addr: PRG load address
        copyright_str: PSID copyright string (often "1987 Wizax 2004"
            or similar)

    The label includes a cluster suffix when the player signature
    matches a specifically-RE'd cluster (currently only "1988 2000 A.D."
    — Galax_it_y + Echo_Beat). See `memory/vibrants-v20-findings.md`
    for per-cluster notes.
    """
    if not copyright_str:
        return None

    # Must contain at least one V20-class label.
    matched_label = None
    for hint in V20_COPYRIGHT_HINTS:
        if hint in copyright_str:
            matched_label = hint
            break
    if matched_label is None:
        return None

    # Must be a small binary (NP21 is too big to plausibly fit here).
    if len(c64_data) > V20_MAX_SIZE:
        return None

    base = f"{copyright_str.strip()} (label: {matched_label})"

    # Cluster signature: 1988 2000 A.D. player (Galax + Echo_Beat).
    # When matched, append a hint so the conversion log mentions partial
    # RE is available for this specific player.
    if _is_2000_ad_cluster(c64_data):
        return f"{base} — 1988 2000 A.D. cluster (player signature matched; partial RE in memory/vibrants-v20-findings.md)"

    return base
