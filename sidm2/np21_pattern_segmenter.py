"""Stage 2: split a flat NP21 voice byte stream into musically-sensible patterns.

The NP21 voice byte stream has two valid interpretations:
  - As-played by the NP21 player (one continuous event stream — notes,
    durations, instrument-set, commands, all walked linearly).
  - As an SF2 orderlist (with $A0-$BF bytes interpreted as transpose
    markers and $00-$7F as pattern indices into a separate seq table).

The first interpretation is what runs at audio time. The second is what
SF2II's editor wants for its display, since SF2II's editor model is
orderlist + multiple short patterns, not a flat per-voice event stream.

This segmenter does the SF2-side adaptation: it splits the flat stream
into chunks at "instrument prefix" boundaries ($A0-$BF) so the editor
shows multiple short patterns instead of one long ribbon. Each chunk
remains valid NP21 byte syntax (just sliced); concatenating all the
chunks of a voice in their original order yields the input byte stream
verbatim — which is the round-trip property the runtime translator
depends on for audio fidelity.
"""
from __future__ import annotations
from typing import NamedTuple


class Segment(NamedTuple):
    """A single segment carved out of a voice byte stream.

    bytes_:        the segment payload (subset of the input stream)
    src_offset:    starting offset in the original stream (for round-trip)
    is_transpose:  True if this segment starts with a transpose-only
                   instruction the editor interprets as orderlist
                   transposition; we still emit it as a pattern, but
                   document the type for diagnostics.
    """
    bytes_: bytes
    src_offset: int
    is_transpose: bool


def is_instrument_prefix(b: int) -> bool:
    """NP21 byte $A0-$BF = "set instrument" prefix. SF2 editor reads
    these in orderlist context as transpose markers."""
    return 0xA0 <= b <= 0xBF


def segment_voice_stream(body: bytes, *, max_segment_size: int = 200) -> list[Segment]:
    """Split a voice byte stream at instrument-prefix ($A0-$BF) boundaries.

    Each segment starts at an instrument-prefix byte (or at offset 0 if the
    stream doesn't begin with one) and runs until the next instrument-prefix
    byte or the end of the stream.

    `body` should be the body bytes (no $FF/$7F terminator); the caller
    re-attaches loop terminators to the shadow buffer.

    `max_segment_size` caps any individual segment length so the editor's
    fixed 256-byte sequence slot accommodates the chunk plus its $7F end
    marker. Default 200 leaves room for headroom.
    """
    if not body:
        return []

    segments: list[Segment] = []
    start = 0

    for i in range(1, len(body)):  # start from 1 so we don't split at offset 0
        if is_instrument_prefix(body[i]):
            chunk = bytes(body[start:i])
            if chunk:
                segments.append(Segment(
                    bytes_=chunk,
                    src_offset=start,
                    is_transpose=is_instrument_prefix(chunk[0]) if chunk else False,
                ))
            start = i

    # Tail
    chunk = bytes(body[start:])
    if chunk:
        segments.append(Segment(
            bytes_=chunk,
            src_offset=start,
            is_transpose=is_instrument_prefix(chunk[0]) if chunk else False,
        ))

    # Enforce max_segment_size by sub-splitting any oversize chunk at byte
    # boundaries. This is rare in practice but defensive.
    out: list[Segment] = []
    for seg in segments:
        if len(seg.bytes_) <= max_segment_size:
            out.append(seg)
            continue
        offset = 0
        while offset < len(seg.bytes_):
            piece = seg.bytes_[offset : offset + max_segment_size]
            out.append(Segment(
                bytes_=piece,
                src_offset=seg.src_offset + offset,
                is_transpose=seg.is_transpose if offset == 0 else False,
            ))
            offset += max_segment_size

    return out


def assemble_voice_stream(segments: list[Segment]) -> bytes:
    """Inverse of segment_voice_stream: concat all segments in order.

    Round-trip property: assemble_voice_stream(segment_voice_stream(body)) == body
    The runtime translator depends on this for audio fidelity.
    """
    return b"".join(seg.bytes_ for seg in segments)


def dedupe_segments(per_voice: list[list[Segment]]) -> tuple[list[bytes], list[list[int]]]:
    """Dedupe identical segment bodies across voices.

    Input:  per_voice[v] = list of Segments for voice v
    Output: (unique_patterns, per_voice_orderlists)
      unique_patterns       = list of distinct segment bodies (bytes)
      per_voice_orderlists  = list of int lists; entry [v][i] is the
                              index into unique_patterns for voice v's
                              i-th segment

    Patterns are listed in first-seen order across voices for stable
    output. The orderlist for each voice references those indices.
    """
    unique_patterns: list[bytes] = []
    by_bytes: dict[bytes, int] = {}
    per_voice_orderlists: list[list[int]] = []

    for voice_segments in per_voice:
        ol: list[int] = []
        for seg in voice_segments:
            if seg.bytes_ in by_bytes:
                ol.append(by_bytes[seg.bytes_])
            else:
                idx = len(unique_patterns)
                by_bytes[seg.bytes_] = idx
                unique_patterns.append(seg.bytes_)
                ol.append(idx)
        per_voice_orderlists.append(ol)

    return unique_patterns, per_voice_orderlists
