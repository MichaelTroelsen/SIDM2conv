"""Extract per-voice note streams from 1988 2000 A.D. cluster files.

This is the v3.5.59 extractor that pairs with `vibrants_2000ad_detector`
to feed the SF2 editor view for Echo_Beat + Galax_it_y. Detection alone
is not enough — the player's byte-stream format is NOT NP21-compatible
(orderlist+pattern model instead of NP21's flat per-voice stream), so
the extractor synthesizes a near-equivalent NP21-shaped stream per voice
for editor display.

# What the extractor produces

For each of 3 voices, walks:

    voice_orderlist[v]  : sequence of pattern indices and commands
    pattern_ptr_table   : maps pattern index → pattern start address
    pattern[i]          : sequence of (duration, note) byte pairs

and emits a synthesized NP21-format byte stream:

    $A0                          ; instrument-set marker (lets segmenter
                                   split each 2000 A.D. pattern into its
                                   own SF2 sub-pattern in the editor view)
    note_byte                    ; $00 = rest, $01-$6F = chromatic note
    $80 | (low_4_bits_of_duration) ; NP21 duration byte
    ... repeat ...
    (no explicit terminator — caller appends $FF $00)

The note byte is chromatically mapped: 2000 A.D. byte 2 = N corresponds
to semitone N from C-0 (verified v3.5.61 by decoding the freq LUT at
load+$10F and confirming it holds the standard SID PAL chromatic table).
NP21 uses 1-based chromatic notation ($01 = C-0), so the mapping is
`NP21_note = byte_2 + 1`, clamped to $6F (SF2 editor max).

`byte_2 = 0` retains its 2000 A.D. semantics of "rest / gate off" and
maps to NP21 $00 (no-event); the LUT's entry-0 freq value (C-0) is
unreachable in the player because the gate-off code path runs first.

Per-pattern transpose is applied (v3.5.62): orderlist command bytes
$80-$9F set the per-voice transpose at runtime via the simple rule
`transpose = command_byte & $1F` (mask low 5 bits). The freq-resolution
path then adds that transpose to byte_2 before the LUT lookup, so each
orderlist iteration of the same pattern plays at a different absolute
pitch. The extractor mirrors this: each voice's walk tracks a current
transpose (initialized to 0), updates it on each $80-$FE orderlist
command, and pre-shifts each pattern note by that transpose before
emitting. Result: editor sub-patterns now show correct absolute pitch
labels, not raw pre-transpose values.

byte_2 = 0 is unaffected by transpose because the gate-off code path
runs before the transpose+LUT lookup; it always maps to NP21 $00 (rest).

The duration byte's bit 5 in 2000 A.D. is an "upper octave" flag and
bits 0-4 are tick count. NP21 duration uses bits 0-3 for tick count
(max 15) so we clamp. Long notes get visually shortened in the editor
but the pattern walks remain coherent.

# What this does NOT enable

* F1 edit propagation: the embedded 2000 A.D. binary keeps reading its
  own pattern data at runtime; nothing the user types in the editor
  alters playback. The wave-copy / shadow-buffer translator pipeline
  doesn't apply (different byte format, different player code).
* Note name display: lacking the freq LUT decode.
* Commands ($80-$FE byte 1) are dropped — their semantics aren't RE'd.

# Safety

The extractor is defensive: every read is bounds-checked, every walk
has an iteration cap, and a malformed binary returns empty streams
rather than corrupting the edit area. The detector already guarantees
in-range pattern_ptr table + voice orderlist ptrs, so the only ways to
fall off in the inner walks are mid-pattern data corruption.

See `memory/vibrants-2000ad-cluster-re.md` for the RE detail.
"""
from __future__ import annotations
from typing import List

from .vibrants_2000ad_detector import Vibrants2000ADLayout


# Limits keep editor streams bounded — the segmenter caps individual
# segments at 200B (sequence slot is 256B with $7F end marker overhead).
# The wider stream cap lets the segmenter produce multiple sub-patterns
# per voice (one per 2000 A.D. pattern, via the $A0 markers).
_MAX_ORDERLIST_STEPS  = 64
_MAX_PATTERN_PAIRS    = 128
_MAX_STREAM_BYTES     = 600   # enough for several short patterns per voice


def extract_2000ad_voice_streams(
    c64_data: bytes,
    sid_la: int,
    layout: Vibrants2000ADLayout,
) -> List[bytes]:
    """Walk per-voice orderlists + patterns, return NP21-shape streams.

    Args:
        c64_data: The 2000 A.D. binary bytes.
        sid_la:   The binary's C64 load address.
        layout:   A `Vibrants2000ADLayout` from `detect_2000ad_layout`.

    Returns:
        List of 3 byte strings (one per voice). Each stream is the body
        portion (no $FF terminator); the caller appends the loop marker
        when feeding the standard NP21 pattern pipeline.
    """
    pat_lo_off = layout.pattern_ptr_lo_addr - sid_la
    pat_hi_off = layout.pattern_ptr_hi_addr - sid_la

    streams: List[bytes] = []
    for v in range(3):
        streams.append(_walk_voice(
            c64_data,
            sid_la,
            ol_addr=layout.voice_orderlist_addrs[v],
            pat_lo_off=pat_lo_off,
            pat_hi_off=pat_hi_off,
        ))
    return streams


def _walk_voice(
    c64_data: bytes,
    sid_la: int,
    *,
    ol_addr: int,
    pat_lo_off: int,
    pat_hi_off: int,
) -> bytes:
    """Walk one voice's orderlist + patterns, emit one NP21-shape stream.

    Tracks a running `transpose` value that orderlist commands $80-$FE
    update via `transpose = command_byte & $1F`. The transpose is added
    to each pattern note before chromatic mapping. Initialized to 0
    (matches the C64 RAM init state for $XXEF+X scratch).
    """
    ol_off = ol_addr - sid_la
    if not (0 <= ol_off < len(c64_data)):
        return b''

    stream = bytearray()
    ol_idx = 0
    ol_steps = 0
    transpose = 0

    while (ol_off + ol_idx < len(c64_data)
           and ol_steps < _MAX_ORDERLIST_STEPS
           and len(stream) < _MAX_STREAM_BYTES):
        b = c64_data[ol_off + ol_idx]
        if b == 0xFE or b == 0xFF:
            # $FE = stop, $FF = loop. Either way, end emission here —
            # the SF2 editor doesn't loop the displayed pattern, so
            # truncating at the first end-or-loop is correct.
            break
        if b >= 0x80:
            # Orderlist command: `transpose = command_byte & $1F`
            # (handler at body+$0443: `AND #$1F; STA $XXEF,X`). The
            # value applies to all subsequent pattern notes until the
            # next command. Continue to read the next orderlist byte
            # (the actual pattern index).
            transpose = b & 0x1F
            ol_idx += 1
            continue
        pat_idx = b
        pat_addr = _read_pattern_addr(c64_data, pat_lo_off, pat_hi_off, pat_idx)
        if pat_addr is None:
            break
        pat_off = pat_addr - sid_la
        if not (0 <= pat_off < len(c64_data)):
            break
        # Emit instrument-set marker so the segmenter splits at this
        # boundary (each 2000 A.D. pattern → one SF2 sub-pattern).
        stream.append(0xA0)
        _walk_pattern(c64_data, pat_off, stream, transpose=transpose)
        ol_idx += 1
        ol_steps += 1

    return bytes(stream)


def _read_pattern_addr(
    c64_data: bytes,
    pat_lo_off: int,
    pat_hi_off: int,
    pat_idx: int,
) -> int:
    """Dereference pattern index → absolute pattern start address.

    Returns the address, or None if the index is out-of-bounds.
    """
    if (pat_lo_off + pat_idx >= len(c64_data) or
            pat_hi_off + pat_idx >= len(c64_data) or
            pat_lo_off + pat_idx < 0 or
            pat_hi_off + pat_idx < 0):
        return None
    return c64_data[pat_lo_off + pat_idx] | (c64_data[pat_hi_off + pat_idx] << 8)


def _walk_pattern(
    c64_data: bytes,
    pat_off: int,
    stream: bytearray,
    *,
    transpose: int = 0,
) -> None:
    """Walk a single 2000 A.D. pattern and append NP21 bytes to `stream`.

    `transpose` is added to byte_2 before chromatic mapping (the player
    does `CLC; ADC $XXEF,X` between byte_2 read and the LUT lookup, so
    pre-shifting here mirrors what plays). byte_2 = 0 (rest) bypasses
    the transpose because the gate-off code path runs first.

    Stops at $FF (end of pattern), out-of-bounds, the per-pattern pair
    cap, or the global stream cap.
    """
    q = pat_off
    pairs = 0
    while (q < len(c64_data)
           and pairs < _MAX_PATTERN_PAIRS
           and len(stream) < _MAX_STREAM_BYTES):
        b1 = c64_data[q]
        if b1 == 0xFF:
            return
        if b1 >= 0x80:
            # Command with payload byte — skip both.
            if q + 1 >= len(c64_data):
                return
            q += 2
            continue
        # (duration, note) pair
        if q + 1 >= len(c64_data):
            return
        b2 = c64_data[q + 1]
        # Chromatic mapping: NP21_note = (byte_2 + transpose) + 1,
        # clamped to $6F. byte_2 = 0 stays as NP21 $00 (rest/gate-off);
        # see module docstring for the LUT + transpose rationale.
        if b2 == 0x00:
            stream.append(0x00)
        else:
            np21_note = b2 + transpose + 1
            if np21_note > 0x6F:
                np21_note = 0x6F
            elif np21_note < 0x01:
                # Transpose could in theory be negative if we ever
                # extend handling beyond AND-$1F; defend against $00
                # falling into "rest" semantics by clamping low.
                np21_note = 0x01
            stream.append(np21_note)
        # Emit NP21 duration ($80 | low 4 bits of ticks).
        ticks = b1 & 0x1F
        stream.append(0x80 | min(ticks, 0x0F))
        q += 2
        pairs += 1
