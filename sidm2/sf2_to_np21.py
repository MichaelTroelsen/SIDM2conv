"""SF2 packed sequence -> NP21 sequence translator.

Pure-Python reference for the 6502 translator that will be emitted at
$0F0E by the laxity SF2 driver (criterion-3 work, see
docs/criterion3_plan.md and docs/criterion3_step0_findings.md).

The 6502 translator MUST match this function byte-for-byte; this module
is the spec.

After the v3.2.2 byte-mapping fix, the only non-identity transform the
translator does is rewriting SF2's `0x7F` end-of-sequence into NP21's
`0xFF / loop_target` loop-to-Y marker. Every other byte passes through.

Mapping (inverse of `_build_np21_sf2_edit_area` per-byte loop):

    SF2 0x00       -> NP21 0x00          (no event / gate off)
    SF2 0x01-0x6F  -> NP21 0x01-0x6F     (notes; 0x01 is the lowest pitch)
    SF2 0x7E       -> NP21 0x7E          (tie / note-on)
    SF2 0x7F       -> NP21 0xFF, <loop>  (end-of-seq -> loop-to-Y marker)
    SF2 0x80-0xFF  -> NP21 0x80-0xFF     (durations, instruments, commands)

Bytes 0x70-0x7D are not produced by the v3.2.2 encoder (high NP21 notes
are clamped to 0x6F there). If the SF2 editor lets a user type one,
the translator passes it through identity to NP21 — the embedded NP21
player accepts the full 0x01-0x7D note range.
"""

NP21_LOOP_MARKER = 0xFF
SF2_END_MARKER = 0x7F


def sf2_to_np21(sf2_bytes: bytes, loop_target: int = 0) -> bytes:
    """Translate one SF2 packed sequence into NP21 sequence format.

    Args:
        sf2_bytes: SF2 packed sequence body. Read up to (and including) the
            first 0x7F terminator; any padding after that is ignored.
        loop_target: Y-index to loop back to in NP21 convention. 0 means
            loop from the start of the sequence.

    Returns:
        NP21 sequence bytes terminated by ``0xFF, loop_target``.
    """
    out = bytearray()
    for b in sf2_bytes:
        if b == SF2_END_MARKER:
            out.append(NP21_LOOP_MARKER)
            out.append(loop_target & 0xFF)
            return bytes(out)
        out.append(b)
    # No 0x7F found in the input. Emit a defensive loop terminator so the
    # NP21 player won't run off the end of the buffer. This path should not
    # be reached with a well-formed SF2 sequence (the editor always writes
    # a 0x7F end marker).
    out.append(NP21_LOOP_MARKER)
    out.append(loop_target & 0xFF)
    return bytes(out)
