"""Pure builders for SF2 auxiliary-block bodies.

Extracted from sf2_writer.py at the v3.5.39 Phase 5 refactor.

The SF2 file format has an auxiliary-data chain (located via a HARDCODED
pointer at C64 $0FFB) containing up to 5 block types:

  id=1  EditingPreferences  — 3B v1
  id=2  HardwarePreferences — 2B v1
  id=3  PlayMarkers         — variable v2
  id=4  TableText           — variable v2 (instrument + command names)
  id=5  Songs               — variable v2 (song description metadata)

This module covers the two non-trivial ones:

  build_table_text_data(instrument_names, command_names, instr_table_id,
                         cmd_table_id) -> bytes
    Builds the body for the id=4 TableText block. Format derived from
    SF2II's `auxilary_data_table_text.cpp:269`
    (AuxilaryDataTableText::RestoreFromSaveData).

  build_description_data(song_name) -> bytes
    Builds the body for the id=5 Songs block. Format derived from
    SF2II's `auxilary_data_songs.cpp:107`
    (AuxilaryDataSongs::RestoreFromSaveData).

Both functions are pure (parameter inputs, byte outputs) — no I/O,
no logging, no SF2Writer state. The thin orchestrator
`SF2Writer._inject_auxiliary_data` still owns the chain assembly
(TLV framing, $0FFB pointer write, low-load skip) because those
involve self.output mutation.
"""
from __future__ import annotations
import struct
from typing import List, Optional


# Magic numbers from SF2II's Block 3 layout (commands table = 64 rows,
# instruments = 32, the third "Mystery" entry = 256 rows of table ID 64).
# text_count MUST equal the table's row count or
# RestoreFromSaveData walks past the buffer and corrupts memory.
COMMANDS_ROWS = 64
INSTRUMENTS_ROWS = 32
EXTRA_TABLE_ID = 64
EXTRA_ROWS = 256


def build_description_data(song_name: Optional[str] = None) -> bytes:
    """Build the AuxilaryDataSongs body (used as aux block id=5).

    Format per `auxilary_data_songs.cpp:107`:
      [u8 song_count]
      [u8 selected_song]
      per song (when data_version == 2):
        [u8 string_length] [string_length bytes — pascal string]

    SIDM2 emits exactly one song, named after the PSID title (truncated
    to 16 chars). The reference Stinsen ships exactly one song named
    "Main"; we mirror that shape.

    Args:
        song_name: The song title. None / empty defaults to "Main".

    Returns:
        Bytes of the encoded Songs body, ready to wrap in a TLV.
    """
    name = (song_name or "Main").strip() or "Main"
    name = name[:16]
    name_bytes = name.encode('latin-1', errors='replace')

    out = bytearray()
    out.append(0x01)              # song_count = 1
    out.append(0x00)              # selected_song = 0
    out.append(len(name_bytes))   # pascal-string length
    out.extend(name_bytes)
    return bytes(out)


def build_table_text_data(
    instrument_names: List[str],
    command_names: List[str],
    instr_table_id: int = 1,
    cmd_table_id: int = 0,
) -> bytes:
    """Build the TableText body in version-2 format (aux block id=4).

    Format per `auxilary_data_table_text.cpp:269`:
      [u8 entry_count]
      per entry:
        [u32 LE table_id]
        [u16 LE layer_count]
        per layer:
          [u16 LE text_count]
          per text:
            [u8 string_length]
            [string_length bytes — string body]

    Reference Stinsen ships 3 entries:
      entry 0: table_id=cmd_table_id, 1 layer, 64 entries
      entry 1: table_id=instr_table_id, 1 layer, 32 entries
      entry 2: table_id=64 ("Mystery"/TableTextLines), 1 layer, 256 empty entries

    Args:
        instrument_names: Names to populate the Instruments table (32 slots).
            Excess names truncated; missing ones padded with "".
        command_names:    Names for the Commands table (64 slots; same rule).
        instr_table_id:   Block 3 ID for the Instruments table (default 1).
        cmd_table_id:     Block 3 ID for the Commands table (default 0).

    Returns:
        Bytes of the encoded TableText body, ready to wrap in a TLV.
    """
    commands_padded    = _pad_or_truncate(command_names,    COMMANDS_ROWS)
    instruments_padded = _pad_or_truncate(instrument_names, INSTRUMENTS_ROWS)

    out = bytearray()
    out.append(3)  # entry_count
    out.extend(_pack_entry(cmd_table_id,    [commands_padded]))
    out.extend(_pack_entry(instr_table_id,  [instruments_padded]))
    out.extend(_pack_entry(EXTRA_TABLE_ID,  [[""] * EXTRA_ROWS]))
    return bytes(out)


# ---------------------------------------------------------------------------
# Private helpers — same encoding rules used by SF2II's RestoreFromSaveData
# ---------------------------------------------------------------------------

def _pad_or_truncate(names: List[str], target_count: int) -> List[str]:
    out = list(names)[:target_count]
    while len(out) < target_count:
        out.append("")
    return out


def _pack_text(name: str) -> bytes:
    """[u8 length][length bytes] — pascal string, max 255B."""
    b = name.encode('latin-1', errors='replace')[:255]
    return bytes([len(b)]) + b


def _pack_layer(texts: List[str]) -> bytes:
    """[u16 LE text_count][repeated _pack_text]."""
    out = bytearray()
    out.extend(struct.pack('<H', len(texts)))
    for t in texts:
        out.extend(_pack_text(t))
    return bytes(out)


def _pack_entry(table_id: int, layer_text_lists: List[List[str]]) -> bytes:
    """[u32 LE table_id][u16 LE layer_count][repeated _pack_layer]."""
    out = bytearray()
    out.extend(struct.pack('<I', table_id))   # u32 LE — was '<i' (signed) in
                                              # an early implementation; SF2II
                                              # treats this as unsigned so the
                                              # signed packing accidentally
                                              # worked for table_id < 0x80000000.
    out.extend(struct.pack('<H', len(layer_text_lists)))
    for layer in layer_text_lists:
        out.extend(_pack_layer(layer))
    return bytes(out)
