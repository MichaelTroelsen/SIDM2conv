"""Pure builders for SF2 auxiliary-block bodies + chain assembly.

Extracted from sf2_writer.py at the v3.5.39 Phase 5 refactor (the two
non-trivial body builders) and extended at the v3.5.51 refactor with
`assemble_aux_chain` + `inject_aux_chain_into_sf2` (the chain framing
and $0FFB-pointer injection that were the remaining half of the old
`_inject_auxiliary_data` method).

The SF2 file format has an auxiliary-data chain (located via a HARDCODED
pointer at C64 $0FFB) containing up to 5 block types:

  id=1  EditingPreferences  — 3B v1
  id=2  HardwarePreferences — 2B v1
  id=3  PlayMarkers         — variable v2
  id=4  TableText           — variable v2 (instrument + command names)
  id=5  Songs               — variable v2 (song description metadata)

This module covers the two non-trivial body builders + the chain
assembly + pointer-injection helpers:

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


# ---------------------------------------------------------------------------
# Chain assembly + pointer injection (added at the v3.5.51 refactor)
# ---------------------------------------------------------------------------

# Reference-bundled minimal bodies for the aux blocks that DO NOT carry
# converter-derived payloads (id=1/2/3). These match values found in all
# 67 bundled SF2II reference files surveyed. Verbatim PlayMarkers /
# HardwarePreferences / EditingPreferences with rich payloads would
# require addresses + states matching our SF2 layout — diverging bodies
# crash RestoreFromSaveData — so we emit minimal-valid versions.

_BODY3_PLAY_MARKERS         = bytes([0x01, 0x00])         # 1 layer, 0 markers
_BODY1_EDITING_PREFS        = bytes([0x00, 0x00, 0x04])   # Sharp notation, hl 0, interval 4


def _hardware_prefs_body(sid_model: int = 8580, region: str = "PAL") -> bytes:
    """HardwarePreferences body (aux id=2): [SIDModel, Region], MOS6581=0 / MOS8580=1,
    PAL=0 / NTSC=1. SF2II reads this PER SONG (else the config default). Galway tunes
    are 6581 — wrong model = wrong filter curve, so the model must be carried here."""
    return bytes([0x00 if sid_model == 6581 else 0x01,
                  0x01 if region == "NTSC" else 0x00])

_AUX_CHAIN_END_MARKER       = bytes([0x00, 0x00, 0x00, 0x00, 0x00])

# Hardcoded $0FFB aux-pointer location — read by SF2II's
# `ParseAuxilaryData` at the constant `driver_info.h:
# AuxilaryDataPointerAddress`. NOT configurable per-file.
AUX_POINTER_C64_ADDR = 0x0FFB


def _make_aux_block(bid: int, param: int, body: bytes) -> bytes:
    """Wrap a body in a TLV aux-block frame.

    Frame: [u8 id][u16 LE param][u16 LE length][body]
    """
    return bytes([bid]) + struct.pack('<H', param) + struct.pack('<H', len(body)) + body


def assemble_aux_chain(
    table_text_body: bytes,
    desc_body: Optional[bytes] = None,
    sid_model: int = 8580,
) -> bytes:
    """Assemble the SF2 aux chain in bundled order [3, 2, 1, 4, 5, END].

    Matches all 67 bundled SF2II reference files. Each block is a
    TLV frame `[u8 id][u16 LE param][u16 LE length][body]` and the
    chain is terminated by 5 zero bytes.

    Args:
        table_text_body: Body for aux block id=4 (TableText). Built
            via `build_table_text_data`.
        desc_body: Body for aux block id=5 (Songs). Built via
            `build_description_data`. If None or empty, the id=5
            block is omitted from the chain entirely (matches the
            pre-v3.5.51 behavior).

    Returns:
        Bytes of the complete chain ready to be appended past the
        SF2 content. Caller is responsible for writing the chain's
        starting C64 address to the $0FFB pointer slot — see
        `inject_aux_chain_into_sf2` for that step.
    """
    out = bytearray()
    out.extend(_make_aux_block(3, 2, _BODY3_PLAY_MARKERS))             # PlayMarkers
    out.extend(_make_aux_block(2, 1, _hardware_prefs_body(sid_model))) # HardwarePreferences
    out.extend(_make_aux_block(1, 1, _BODY1_EDITING_PREFS))            # EditingPreferences
    out.extend(_make_aux_block(4, 2, table_text_body))                 # TableText
    if desc_body:
        out.extend(_make_aux_block(5, 2, desc_body))                   # Songs
    out.extend(_AUX_CHAIN_END_MARKER)
    return bytes(out)


def inject_aux_chain_into_sf2(
    output: bytearray,
    aux_chain: bytes,
) -> Optional[int]:
    """Append the aux chain past the SF2 content and write its address
    to the $0FFB pointer slot.

    The PRG load address comes from `output[0:2]` (little-endian word).
    Use the SF2 file's PRG load address (typically $0D7E) — NOT the
    SID's PSID load address (often $0000), which would mis-compute the
    pointer offset.

    Args:
        output: The SF2 buffer (mutated in place — extended with
            `aux_chain` and patched at the $0FFB pointer slot).
        aux_chain: Bytes from `assemble_aux_chain`.

    Returns:
        The C64 address where the aux chain was placed (i.e. what was
        written to $0FFB), or None if the pointer slot doesn't fit
        within the buffer (the chain is then NOT appended either).
    """
    if len(output) < 2:
        return None
    sf2_prg_load = output[0] | (output[1] << 8)
    aux_chain_offset_in_file = len(output)
    aux_chain_c64_addr = sf2_prg_load + (aux_chain_offset_in_file - 2)

    aux_pointer_offset = AUX_POINTER_C64_ADDR - sf2_prg_load + 2
    if 0 <= aux_pointer_offset and aux_pointer_offset + 2 <= len(output):
        output[aux_pointer_offset]     = aux_chain_c64_addr & 0xFF
        output[aux_pointer_offset + 1] = (aux_chain_c64_addr >> 8) & 0xFF
        output.extend(aux_chain)
        return aux_chain_c64_addr
    return None
