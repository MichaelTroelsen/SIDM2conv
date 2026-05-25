"""The b"META" trailer — encoder + decoder for SID round-trip metadata.

Extracted from sf2_writer.py + scripts/sf2_to_sid.py at the v3.5.41
refactor.

# The problem

SF2II's aux-chain id=5 ("Songs") block carries a single song name but
not full title/author/copyright. To make SID → SF2 → SID round-tripping
preserve all three PSID metadata fields, SIDM2 (since v3.5.17) appends
a small trailer past the official SF2 content:

    [b"META"] [pascal title] [pascal author] [pascal copyright]

Where each pascal string is `[u8 length] [length bytes latin-1]`.

SF2II ignores the trailer because the C64 memory location it would map
to lies past the SF2 file's natural end (LOAD + len) and isn't
referenced by any of its handlers. Round-trip readers find the magic
by reverse-scanning the file's tail.

Before v3.5.41 the encoder lived in `sf2_writer.py` and the decoder in
`scripts/sf2_to_sid.py`. Same format spec, scattered across two files,
no shared test. v3.5.41 unifies the encoder + decoder + their format
spec in this module.

# API

  encode_metadata_trailer(title, author, copyright) -> bytes
    Pure encoder. Latin-1, each string truncated to 255B.

  decode_metadata_trailer(sf2_bytes) -> Optional[Tuple[str, str, str]]
    Pure decoder. Returns (title, author, copyright) when a valid
    trailer is found in the last 2048B (reverse-scanned for b"META"
    + 3 pascal strings), None when missing or malformed.
"""
from __future__ import annotations
from typing import Optional, Tuple


METADATA_MAGIC = b"META"
MAX_PASCAL_LEN = 255  # pascal string length is one byte
TAIL_SCAN_WINDOW = 2048


def encode_metadata_trailer(
    title: str,
    author: str,
    copyright: str,
) -> bytes:
    """Encode title + author + copyright as a b"META" trailer.

    Each string is encoded latin-1 (with '?' for unencodable chars)
    and truncated to 255 bytes (pascal-string length limit).

    Args:
        title:     PSID song title (typically <= 32 chars).
        author:    PSID composer name.
        copyright: PSID copyright string.

    Returns:
        Bytes ready to be appended past the SF2 content.
    """
    out = bytearray(METADATA_MAGIC)
    for s in (title, author, copyright):
        s = (s or "").strip()
        b = s.encode('latin-1', errors='replace')[:MAX_PASCAL_LEN]
        out.append(len(b))
        out.extend(b)
    return bytes(out)


def decode_metadata_trailer(sf2_bytes: bytes) -> Optional[Tuple[str, str, str]]:
    """Decode a b"META" trailer from the tail of an SF2 file.

    Reverse-scans the last 2048 bytes for the b"META" magic, then
    reads 3 pascal strings. If the trailer is missing or malformed
    (e.g. a string's length runs past the file end), returns None
    so the caller can fall back to empty metadata.

    Args:
        sf2_bytes: The full SF2 file contents.

    Returns:
        (title, author, copyright) tuple on success; None when no
        valid trailer is found.
    """
    if len(sf2_bytes) < len(METADATA_MAGIC):
        return None

    # Reverse-scan a reasonable tail window for performance —
    # the trailer is always at file end.
    search = (sf2_bytes[-TAIL_SCAN_WINDOW:]
              if len(sf2_bytes) > TAIL_SCAN_WINDOW
              else sf2_bytes)
    idx = search.rfind(METADATA_MAGIC)
    if idx < 0:
        return None

    off = len(sf2_bytes) - len(search) + idx + len(METADATA_MAGIC)
    try:
        strs = []
        for _ in range(3):
            if off >= len(sf2_bytes):
                return None
            L = sf2_bytes[off]
            off += 1
            if off + L > len(sf2_bytes):
                return None    # length runs past file end
            strs.append(sf2_bytes[off:off + L].decode(
                'latin-1', errors='replace'))
            off += L
        if len(strs) == 3:
            return (strs[0], strs[1], strs[2])
        return None
    except Exception:
        return None
