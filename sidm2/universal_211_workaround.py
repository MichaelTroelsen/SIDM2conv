"""Universal SF2II upstream issue #211 workaround.

`Editor::DriverUtils::GetSIDWriteInformationFromDriver` in SF2II
(driver_utils.cpp:419) statically sweeps the C64-emulated memory at
[m_DriverCodeTop, +m_DriverCodeSize) for any ABX/ABY write to
$D400-$D406 (`STA $D40x,X` or `STA $D40x,Y`). If the sweep finds zero
matches, it dereferences `result.begin()->m_CycleOffset` UNGUARDED →
access violation on F10-load. Upstream declined to fix (collaborator:
"SF2II only officially supports SF2II-saved files"; tracked at
github.com/Chordian/sidfactory2 issue 211).

This module's `ensure_sid_write_in_scan_window_universal` applies a
SF2-side workaround that guarantees the sweep finds at least one
indexed $D40x write. Two cases:

1. **Trampoline path** (most files): every injection path emits a
   2-JMP trampoline at $1000 (`4C lo hi 4C lo hi`, 6 bytes). SF2II
   decodes JMP-abs as 3 bytes, so its linear sweep lands
   DETERMINISTICALLY at $1006. If $1006 is inert PRG gap (`00 00 00`),
   stamp a dead `STA $D400,X` (`9D 00 D4`) there. Never executed
   (playback uses DriverCommon InitAddress); just satisfies the scan.

2. **Alt-scan path** (Digidag, et al.): if $1000 is NOT a 2-JMP
   trampoline (binary itself loaded there), and a byte-level scan
   finds zero indexed $D40x writes in [$1000, $1900) (a conservative
   lower bound on what SF2II's opcode-aware sweep would find — if 0
   byte-matches exist, opcode sweep also finds 0), append a
   `9D 00 D4 60` scan-bait stub at end of file and patch Block 1's
   m_DriverCodeTop/m_DriverCodeSize to point at it. The scan window
   becomes 3 bytes containing the indexed write; sweep finds it.

The workaround is idempotent: re-running it on an already-stamped
file does nothing. Files with live code at $1000 that contain natural
indexed $D40x writes in the scan window are left untouched (they
already pass).

Extracted from sf2_writer.py at v3.5.36 refactor. The function takes
the SF2 output bytearray and modifies it in place; returns nothing.
"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# All 6502 opcodes that use absolute-indexed (abs,X or abs,Y)
# addressing. SF2II's scan looks for any of these targeting
# $D400-$D406.
_ABXY_OPS = (0x9D, 0xBD, 0xDD, 0x7D, 0x1D, 0x3D, 0x5D, 0xFD,  # abs,X
             0x99, 0xB9, 0xD9, 0x79, 0x19, 0x39, 0x59, 0xF9,  # abs,Y
             0xBE, 0xBC)


def ensure_sid_write_in_scan_window_universal(out: bytearray) -> Optional[bytearray]:
    """Apply the universal #211 workaround to the SF2 output.

    Modifies `out` in place (or extends it for the Digidag-class
    fallback) so SF2II's static scan at `[m_DriverCodeTop,+Size)`
    finds at least one ABX/ABY `$D40x` write.

    Returns the new bytearray reference (which may differ from `out`
    if the function extended it) or `None` if no change was needed.
    Callers should assign the returned value back to their output
    field if non-None.
    """
    if out is None or len(out) < 4:
        return None
    out = bytearray(out)
    load_base = out[0] | (out[1] << 8)
    o1000 = 0x1000 - load_base + 2
    if o1000 < 0 or o1000 + 9 > len(out):
        return None

    # Trampoline path: $1000 = 4C ?? ?? 4C ?? ?? + $1006 inert gap →
    # stamp at $1006.
    if (out[o1000] == 0x4C and out[o1000 + 3] == 0x4C):
        o1006 = o1000 + 6
        trio = out[o1006:o1006 + 3]
        if bytes(trio) == b"\x9d\x00\xd4":
            return None  # idempotent — already stamped
        if trio == b"\x00\x00\x00":
            out[o1006:o1006 + 3] = b"\x9d\x00\xd4"  # STA $D400,X
            logger.info(
                "  #211 workaround: stamped dead STA $D400,X at $1006 "
                "(post 2-JMP trampoline; SF2II driver_utils.cpp:419 "
                "derefs result.begin() unguarded — guarantees >=1 "
                "ABX/ABY $D40x write in the [$1000,$1900) static "
                "scan window)")
            return out
        return None  # trampoline present but $1006 is live code — leave alone

    # No trampoline (binary itself at $1000, e.g. Digidag PLA TYA PLA).
    # If the binary contains a natural ABX/ABY $D40x write byte pattern
    # in [$1000,$1900), SF2II's static sweep WILL find it (byte-scan is
    # a conservative lower bound on what the opcode-aware sweep finds:
    # if 0 byte-matches exist, the opcode sweep also finds 0). When
    # zero matches: redirect the scan window via the descriptor-block
    # m_DriverCodeTop override to a freshly-appended dead `STA $D400,X;
    # RTS` stub at the end of the file (Digidag-class architectural
    # workaround). Without this the file crashes at driver_utils:419.
    win_end = min(o1000 + 0x900, len(out))
    natural_hit = False
    for a in range(o1000, win_end - 2):
        if out[a] in _ABXY_OPS:
            tgt = out[a + 1] | (out[a + 2] << 8)
            if 0xD400 <= tgt <= 0xD406:
                natural_hit = True
                break
    if natural_hit:
        return None

    # No natural write — append stub + patch Block 1's DriverCodeTop/Size.
    # High-load guard: skip the Digidag-style append when stub_addr would
    # overflow 16-bit. High-load layouts (v3.5.55) place a scan bait at
    # $0F9E (outside the hardcoded [$1000, $1900) window above) and set
    # driver_code_top accordingly via the header generator — SF2II's
    # scanner finds the bait there. The hardcoded window's failure to
    # see it is a false positive for high-load files.
    stub_file_off = len(out)
    stub_addr = load_base + (stub_file_off - 2)
    if stub_addr > 0xFFFF:
        logger.info(
            "  #211 workaround: file already extends near $FFFF; the "
            "Digidag-style stub append would overflow 16-bit space. "
            "Skipping — caller is responsible for placing a scan bait "
            "and configuring driver_code_top (high-load layout does this).")
        return None
    stub = b"\x9D\x00\xD4\x60"   # STA $D400,X; RTS
    out.extend(stub)
    # Find Block 1 (Descriptor) in the chain at file offset 4. Body:
    # [Type:1][Size:2LE][Name+NUL:var][CodeTop:2LE][CodeSize:2LE]...
    o = 4
    patched = False
    while o + 2 <= len(out):
        bid = out[o]
        if bid == 0xFF:
            break
        bsz = out[o + 1]
        body_off = o + 2
        body_end = body_off + bsz
        if bid == 1 and body_end <= len(out):
            # Skip Type(1)+Size(2); then null-terminated Name.
            p = body_off + 3
            while p < body_end and out[p] != 0:
                p += 1
            p += 1  # past NUL
            if p + 4 <= body_end:
                out[p:p + 2] = stub_addr.to_bytes(2, "little")
                out[p + 2:p + 4] = (len(stub) - 1).to_bytes(2, "little")
                patched = True
            break
        o = body_end
    if patched:
        logger.info(
            f"  #211 workaround: appended STA $D400,X scan-bait stub at "
            f"${stub_addr:04X} and redirected Block 1 m_DriverCodeTop "
            f"there (binary at $1000 with no natural ABX/ABY $D40x "
            f"write — Digidag-class architectural fallback)")
        return out
    else:
        logger.warning(
            "  #211 workaround: could not locate Block 1 to patch "
            "m_DriverCodeTop; file may crash on F10-load")
        return out
