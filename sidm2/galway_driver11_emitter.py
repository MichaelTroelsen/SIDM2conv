"""Stage A1 (emission) — serialise a ``GalwayDriver11Song`` into a real,
playable SID Factory II **Driver 11** ``.sf2`` by overwriting the music data
of the bundled ``Driver 11 Test - Arpeggio.sf2`` template.

Unlike the embed path (audio from an embedded player, editor view display-only),
the output here is a genuine Driver 11 file: the Driver 11 binary in the
template reads the tables/sequences we write, so the editor can edit them and
playback reflects the edits.

Packed sequence format is authoritative, ported from SF2II's
``datasource_sequence.cpp`` (``Pack``/``Unpack``):

    00       note off ('---')      01-6f  notes          7e  note on / sustain
    7f       end of sequence       80-8f  duration        90-9f duration + tie
    a0-bf    set instrument(0-1f)  c0-ff  set command(0-3f)

Per event, in order, each emitted only on change: ``[command][instrument]
[duration][note]``. Duration is a run-length over following sustain ($7e) /
note-off ($00) rows, capped at 15. Tables (instruments 6x32, wave 2x256, …) are
column-major. Spec: ``docs/analysis/GALWAY_TO_DRIVER11_MAPPING.md``.
"""
from __future__ import annotations

import os
from typing import List, Optional

from .models import SF2DriverInfo
from . import sf2_parser
from . import sf2_aux_bodies
from .galway_to_driver11 import GalwayDriver11Song, D11Row

_TEMPLATE_REL = os.path.join("G5", "examples", "Driver 11 Test - Arpeggio.sf2")
_SEQ_BYTE_LIMIT = 0xFA      # leave room for the 0x7F end marker (< 0xFF cap)
_MAX_SEQUENCES = 128        # seq-pointer tables hold 128 entries


# ---------------------------------------------------------------------------
# Packed sequence encoding (mirrors SF2II datasource_sequence.cpp)
# ---------------------------------------------------------------------------

# SF2II's DataSourceSequence::Unpack expands duration bytes into individual
# events in a fixed buffer of MaxEventCount=1024 — with NO bounds check. A
# packed sequence that unpacks to more than that overflows the buffer and
# corrupts the heap (intermittent load crash). So a sequence is also capped by
# its UNPACKED event count, well under 1024, not just its packed byte length.
_SEQ_EVENT_LIMIT = 960


def _event_tokens(rows: List[D11Row]) -> List[tuple]:
    """Group a per-tick row list into self-contained packed tokens, one per
    musical event. Returns (token_bytes, unpacked_event_span) pairs, where the
    span is how many editor rows the token expands to (note + its sustain run).

    Each token is ``[cmd?][instr?][duration][note]``. The duration byte is
    always emitted (so tokens are independent and can be re-binned into
    sequences freely).
    """
    tokens: List[tuple] = []
    i, n = 0, len(rows)
    while i < n:
        r = rows[i]
        note = r.note
        dur = 0
        j = i + 1
        while j < n:
            nr = rows[j]
            if nr.instrument is not None or nr.command is not None:
                break
            if note == 0x00:
                if nr.note != 0x00:
                    break
            else:
                if nr.note != 0x7E:
                    break
            dur += 1
            if dur >= 0x0F:
                break
            j += 1
        tok = bytearray()
        if r.command is not None:
            tok.append(0xC0 | (r.command & 0x3F))
        if r.instrument is not None:
            tok.append(0xA0 | (r.instrument & 0x1F))
        tok.append((dur | 0x80) | (0x10 if r.tie else 0x00))
        tok.append(note)
        tokens.append((bytes(tok), dur + 1))
        i += dur + 1
    return tokens


def segment_track(rows: List[D11Row]) -> List[bytes]:
    """Pack one track's rows into one or more packed sequences, each under BOTH
    the SF2 byte-size cap AND the editor's unpacked-event-count cap (so SF2II's
    fixed 1024-event Unpack buffer never overflows). Returns packed byte strings
    (each ending in $7F)."""
    tokens = _event_tokens(rows)
    seqs: List[bytes] = []
    cur = bytearray()
    cur_events = 0
    for t, span in tokens:
        if cur and (len(cur) + len(t) + 1 > _SEQ_BYTE_LIMIT
                    or cur_events + span > _SEQ_EVENT_LIMIT):
            cur.append(0x7F)
            seqs.append(bytes(cur))
            cur = bytearray()
            cur_events = 0
        cur.extend(t)
        cur_events += span
    if cur:
        cur.append(0x7F)
        seqs.append(bytes(cur))
    if not seqs:                       # empty track → one empty sequence
        seqs = [bytes([0x7F])]
    return seqs


def unpack_sequence(packed: bytes) -> List[int]:
    """Reference unpacker (port of SF2II Unpack) → flat list of per-tick note
    bytes ($00 off, $01-$6F notes, $7E sustain). For round-trip testing."""
    notes: List[int] = []
    i, n = 0, len(packed)
    duration = 0
    while i < n:
        value = packed[i]; i += 1
        if value == 0x7F:
            break
        if value >= 0xC0:              # command
            value = packed[i]; i += 1
        if value >= 0xA0:              # instrument
            value = packed[i]; i += 1
        if value >= 0x80:              # duration (+ optional tie)
            duration = value & 0x0F
            value = packed[i]; i += 1
        notes.append(value)            # the note this tick
        for _ in range(duration):
            notes.append(0x7E if value != 0x00 else 0x00)
    return notes


# ---------------------------------------------------------------------------
# Template emission
# ---------------------------------------------------------------------------

def _template_path() -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, _TEMPLATE_REL)


def emit_driver11_sf2(song: GalwayDriver11Song,
                      template_path: Optional[str] = None) -> bytes:
    """Build a Driver 11 ``.sf2`` from the song IR using the bundled template.

    Writes the instrument/wave/tempo/init tables (column-major), the three
    orderlists + pointers, and the packed sequences + pointers, growing the
    file to hold the sequence data, then rebuilds the aux chain so the
    ``$0FFB`` pointer stays valid after the music region moved.
    """
    template_path = template_path or _template_path()
    out = bytearray(open(template_path, 'rb').read())

    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(out, di)
    if la is None:
        raise ValueError("could not parse Driver 11 template header")

    def off(addr: int) -> int:
        return addr - la + 2

    def w8(addr: int, val: int) -> None:
        o = off(addr)
        if 0 <= o < len(out):
            out[o] = val & 0xFF

    tbl = di.table_addresses

    # --- Instruments (column-major 6 x 32): [AD,SR,Flags,Filter,Pulse,Wave] ---
    if 'Instruments' in tbl:
        ia = tbl['Instruments']['addr']
        nrows = tbl['Instruments']['rows']           # 32
        for r, ins in enumerate(song.instruments[:nrows]):
            cols = [ins.ad, ins.sr, ins.flags,
                    ins.filter_idx, ins.pulse_idx, ins.wave_idx]
            for c, val in enumerate(cols):
                w8(ia + c * nrows + r, val)

    # --- Wave (column-major 2 x 256): col0 = waveform/$7F-jump, col1 = note/jmp
    if 'Wave' in tbl:
        wa = tbl['Wave']['addr']
        wrows = tbl['Wave']['rows']                  # 256
        for r, (c0, c1) in enumerate(song.wave_table[:wrows]):
            w8(wa + 0 * wrows + r, c0)
            w8(wa + 1 * wrows + r, c1)

    # --- Pulse (column-major 3 x 256): default program so pulse voices have a
    # width (else $41 voices are silent). Galway leads are pulse-heavy. ---
    if 'Pulse' in tbl:
        pa = tbl['Pulse']['addr']
        prows = tbl['Pulse']['rows']                 # 256
        pcols = tbl['Pulse']['columns']              # 3
        for r, row in enumerate(song.pulse_table[:prows]):
            for c in range(min(pcols, len(row))):
                w8(pa + c * prows + r, row[c])

    # --- HR (column-major 2 x 16): row 0 = $0F 00 (standard hard-restart) ---
    if 'HR' in tbl:
        ha = tbl['HR']['addr']
        hrows = tbl['HR']['rows']
        w8(ha + 0 * hrows + 0, 0x0F)
        w8(ha + 1 * hrows + 0, 0x00)

    # --- Tempo (1 x 256): [tick][$7F][$00] = constant speed, wrap to row 0 ---
    if 'Tempo' in tbl:
        ta = tbl['Tempo']['addr']
        w8(ta + 0, song.tempo)
        w8(ta + 1, 0x7F)
        w8(ta + 2, 0x00)

    # --- Init (2 x 32): row 0 = (tempo row 0, main volume $0F) ---
    if 'I' in tbl or 'Init' in tbl:
        ent = tbl.get('Init') or tbl.get('I')
        iaddr = ent['addr']; irows = ent['rows']
        w8(iaddr + 0 * irows + 0, 0x00)              # tempo table row index
        w8(iaddr + 1 * irows + 0, 0x0F)              # main volume = max

    # --- Sequences: segment each track, assign global indices ---
    track_seq_indices: List[List[int]] = [[], [], []]
    packed_sequences: List[bytes] = []
    for v in range(3):
        rows = song.tracks[v] if v < len(song.tracks) else []
        for pk in segment_track(rows):
            if len(packed_sequences) >= _MAX_SEQUENCES:
                break
            track_seq_indices[v].append(len(packed_sequences))
            packed_sequences.append(pk)
        if len(packed_sequences) >= _MAX_SEQUENCES:
            break
    for v in range(3):                               # ensure every track has ≥1 seq
        if not track_seq_indices[v]:
            track_seq_indices[v].append(len(packed_sequences))
            packed_sequences.append(bytes([0x7F]))

    # Write packed sequences contiguously from sequence_start, growing the file.
    seq_lo = off(di.sequence_ptrs_lo)
    seq_hi = off(di.sequence_ptrs_hi)
    cur_addr = di.sequence_start
    cur_off = off(cur_addr)
    for idx, pk in enumerate(packed_sequences):
        if cur_off + len(pk) > len(out):
            out.extend(bytearray(cur_off + len(pk) - len(out)))
        out[cur_off:cur_off + len(pk)] = pk
        out[seq_lo + idx] = cur_addr & 0xFF
        out[seq_hi + idx] = (cur_addr >> 8) & 0xFF
        cur_addr += len(pk)
        cur_off += len(pk)
    seq_end_addr = cur_addr
    # Null out unused sequence pointers so stale template pointers can't be hit.
    for idx in range(len(packed_sequences), _MAX_SEQUENCES):
        out[seq_lo + idx] = 0x00
        out[seq_hi + idx] = 0x00

    # --- Orderlists: [A0+trans (on change)][seq&0x7F]… FF 00 ---
    ol_lo = off(di.orderlist_ptrs_lo)
    ol_hi = off(di.orderlist_ptrs_hi)
    for v in range(3):
        ol_addr = di.orderlist_start + v * di.orderlist_size
        o = off(ol_addr)
        out[ol_lo + v] = ol_addr & 0xFF
        out[ol_hi + v] = (ol_addr >> 8) & 0xFF
        body = bytearray()
        last_trans = -1
        for s in track_seq_indices[v]:
            if last_trans != 0xA0:
                body.append(0xA0)                    # transpose 0
                last_trans = 0xA0
            body.append(s & 0x7F)
        body += bytes([0xFF, 0x00])                  # end → loop to start
        # clear the slot then write (orderlist slots are 256 bytes apart)
        for k in range(di.orderlist_size):
            if o + k < len(out):
                out[o + k] = 0x00
        out[o:o + len(body)] = body

    # --- Rebuild aux chain past the (now larger) sequence region + repoint $0FFB
    # The template's aux/name data sat just above the demo sequences; our larger
    # sequences overwrote it, so re-emit a minimal chain at the end of the file.
    try:
        table_text = sf2_aux_bodies.build_table_text_data([], [], 1, 0)
        desc = sf2_aux_bodies.build_description_data(None)
        aux_chain = sf2_aux_bodies.assemble_aux_chain(table_text, desc)
        sf2_aux_bodies.inject_aux_chain_into_sf2(out, aux_chain)
    except Exception:
        pass                                          # aux is non-fatal for playback

    return bytes(out)
