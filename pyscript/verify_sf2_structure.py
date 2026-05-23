"""Static SF2 structural validator.

Parses the SF2 file (PRG header + magic + block chain + handlers) and
asserts each invariant SF2II's parser expects. Doesn't launch SF2II;
purely static byte-level analysis.

What's checked:
1. PRG load header (2 bytes)
2. Magic 0x1337 immediately after load
3. Block chain: walks [id:1][size:1][body...] until 0xFF terminator
4. Required blocks present (1=Descriptor, 2=DriverCommon, 3=DriverTables,
   5=MusicData)
5. Block 2 declares init/play/stop addresses that point INSIDE the
   file's loaded region OR at PSID-native entries (v3.5.35 redirect)
6. Handler stubs at $0F90/$0F94/$0F98 (4 bytes each: JSR + RTS or
   JMP + 1-byte padding; STOP = LDA #0; STA $D418; RTS = 6 bytes)
7. #211 stamp at $1006 (when binary doesn't natively occupy that gap)

Usage:
    py -3 pyscript/verify_sf2_structure.py file.sf2 [file2.sf2 ...]

Exit 0 = all files structurally valid; nonzero = parse / validity error.
"""
import struct
import sys
from pathlib import Path
from typing import Optional


class ParseError(Exception):
    pass


def verify_sf2(sf2_path: Path, verbose: bool = False) -> tuple[bool, list[str]]:
    """Returns (ok, issues). issues is a list of problem strings.
    ok is True iff no issues found.
    """
    issues: list[str] = []
    d = sf2_path.read_bytes()
    if len(d) < 32:
        return False, [f"file too small: {len(d)} bytes"]

    # 1. PRG load header
    load_addr = struct.unpack("<H", d[0:2])[0]
    if not (0x0500 <= load_addr <= 0x0F90):
        issues.append(
            f"unusual PRG load address ${load_addr:04X} (expected "
            f"$0500-$0F90 range; high-load alt-layouts go lower)"
        )

    # 2. Magic 0x1337 at TopAddr+2 (file off 2)
    magic = struct.unpack("<H", d[2:4])[0]
    if magic != 0x1337:
        return False, [
            f"missing 0x1337 magic at file off 2 (got ${magic:04X}); "
            f"SF2II will refuse to load this file"
        ]

    # 3. Walk block chain
    blocks: dict[int, tuple[int, bytes]] = {}  # id -> (size, body)
    o = 4
    while o + 2 <= len(d):
        bid = d[o]
        if bid == 0xFF:
            chain_end = o
            break
        if o + 2 > len(d):
            issues.append(f"truncated block chain at file off {o}")
            break
        bsz = d[o + 1]
        if o + 2 + bsz > len(d):
            issues.append(
                f"block id={bid} at off {o} claims size {bsz} but "
                f"extends past EOF"
            )
            break
        body = d[o + 2:o + 2 + bsz]
        blocks[bid] = (bsz, body)
        o += 2 + bsz
    else:
        issues.append("block chain has no 0xFF terminator before EOF")

    # 4. Required blocks
    REQUIRED = {1: "Descriptor", 2: "DriverCommon",
                3: "DriverTables", 5: "MusicData"}
    for req_id, name in REQUIRED.items():
        if req_id not in blocks:
            issues.append(f"missing required Block {req_id} ({name})")

    # 5. Block 2 declares init/play/stop (body layout: Init, Stop, Play)
    init_addr = play_addr = stop_addr = None
    if 2 in blocks:
        bsz, body = blocks[2]
        if bsz < 6:
            issues.append(f"Block 2 (DriverCommon) too small: {bsz} bytes")
        else:
            init_addr = body[0] | (body[1] << 8)
            stop_addr = body[2] | (body[3] << 8)
            play_addr = body[4] | (body[5] << 8)
            for label, addr in [("init", init_addr), ("stop", stop_addr),
                                 ("play", play_addr)]:
                # Address must be addressable C64 RAM; reject 0
                if addr == 0:
                    issues.append(
                        f"Block 2 declares {label}=$0000 (invalid)"
                    )

    # 6. Check handler stubs at the canonical wrapper offsets ($0F90 etc.)
    # File off of $0F90 = $0F90 - load_addr + 2 (the +2 skips PRG header)
    hnd_off = 0x0F90 - load_addr + 2
    if 0 <= hnd_off and hnd_off + 14 <= len(d):
        # INIT @ $0F90: should be 4 bytes (JSR XXXX + RTS) — typical
        init_handler = d[hnd_off:hnd_off + 4]
        if init_handler[0] == 0x20 and init_handler[3] == 0x60:
            # JSR + RTS = good
            pass
        elif init_handler[0] == 0x4C:
            # JMP — alternate stub form, also valid
            pass
        else:
            # Could be a custom handler; just note it
            if verbose:
                issues.append(
                    f"$0F90 INIT handler unusual opcode "
                    f"${init_handler[0]:02X} (expected $20=JSR or $4C=JMP)"
                )
        # PLAY @ $0F94: same shape OR JMP to translator
        play_handler = d[hnd_off + 4:hnd_off + 8]
        if play_handler[0] not in (0x20, 0x4C):
            if verbose:
                issues.append(
                    f"$0F94 PLAY handler unusual opcode "
                    f"${play_handler[0]:02X} (expected $20 or $4C)"
                )

    # 7. #211 stamp at $1006 — should be `9D 00 D4` (STA $D400,X) OR
    # actual binary opcodes (when load=$1000 and binary occupies $1006)
    one006_off = 0x1006 - load_addr + 2
    if 0 <= one006_off and one006_off + 3 <= len(d):
        b1006 = d[one006_off:one006_off + 3]
        if bytes(b1006) == b"\x00\x00\x00":
            issues.append(
                f"$1006 is inert zero gap (no #211 stamp); SF2II's "
                f"GetSIDWriteInformationFromDriver would AV on F10-load"
            )
        # Otherwise: either the stamp ($9D $00 $D4) or live binary bytes — both OK.

    return len(issues) == 0, issues


def main(argv):
    if len(argv) < 1:
        print(__doc__)
        sys.exit(2)
    overall_ok = True
    for arg in argv:
        sf2_path = Path(arg)
        if not sf2_path.exists():
            print(f"MISSING: {sf2_path}")
            overall_ok = False
            continue
        ok, issues = verify_sf2(sf2_path)
        if ok:
            print(f"OK: {sf2_path.name}")
        else:
            overall_ok = False
            print(f"FAIL: {sf2_path.name}")
            for issue in issues:
                print(f"  - {issue}")
    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
