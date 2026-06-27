"""Future Composer V1.0 module writer — the inverse of ``fc_parser``.

Serializes a song (per-voice FCNote streams + instruments) back into a native FC
V1.0 module: a PRG loaded at $1800 = the player + data, exactly what the editor's
SAVE routine writes ($1800..end, RE'd from the decrunched editor at $cd82). This is
the foundation for the SF2->FC round-trip (load converted/edited songs back into the
real C64 Future Composer editor).

Layout (addresses honoured because the player hardcodes them; read from the player
template via the same code-operand offsets fc_parser uses, so it's relocation-safe):
- $1800..instr_base: player code + freq table + arp/drum tables + pointer SLOTS,
  copied verbatim from a template module (these are constant across songs).
- instr_base ($2188): instruments, 8 bytes each (32 slots reserved).
- after instruments: one block per voice (the voice's full note stream).
- after blocks: one orderlist per voice = [block#, $ff(loop)].
- voice orderlist ptrs ($1ea1 lo / $1ea4 hi) and the block-ptr table ($1ea7) are
  filled to point at the above.

This first version emits ONE block per voice (no orderlist compression / repeats /
per-block transpose); it round-trips the note sequence faithfully, which is what an
edited score needs. Glides are not re-emitted (fc_parser doesn't retain them).
"""

from __future__ import annotations

from typing import List

from .fc_parser import (FCSong, FCNote, _u16,
                        _OFF_VOICE_LO, _OFF_VOICE_HI, _OFF_BLOCKPTR,
                        _OFF_INSTR_AD)

INSTR_SLOTS = 32        # the player masks instrument # to 5 bits
MAX_BLOCK = 250         # block index $2124,x is 8-bit -> a block must be < 256 B
MAX_BLOCKS = 64         # orderlist block# is 6-bit ($40 bit = repeat, $80 = transp)


def encode_voice_blocks(notes: List[FCNote]) -> List[bytes]:
    """Encode a voice's FCNote stream into one or more FC blocks (each ends $ff,
    each < 256 bytes since the player's in-block index is 8-bit). The orderlist
    chains them. Instrument/duration state THREADS across blocks (the player and
    fc_parser both carry it), so a token's command bytes simply land in whichever
    block they fall in. Per row: set-instr ($c0|n) / set-dur ($80|n) on change, a
    tie marker ($f0) before tied notes, then the note byte ($00-$7f)."""
    blocks: List[bytes] = []
    cur = bytearray()
    cur_instr = -1
    cur_dur = -1
    for n in notes:
        tok = bytearray()
        if n.instr != cur_instr:
            tok.append(0xC0 | (n.instr & 0x1F))
        if n.dur != cur_dur:
            tok.append(0x80 | (n.dur & 0x3F))
        if n.tie:
            tok.append(0xF0)
        tok.append(min(n.note, 0x7F))          # keep high bit clear (= a note)
        if cur and len(cur) + len(tok) + 1 > MAX_BLOCK:   # +1 for the $ff
            cur.append(0xFF)
            blocks.append(bytes(cur))
            cur = bytearray()
        cur += tok
        cur_instr = n.instr
        cur_dur = n.dur
    cur.append(0xFF)
    blocks.append(bytes(cur))
    return blocks


def write_fc(song: FCSong) -> bytes:
    """Serialize ``song`` to a native FC V1.0 PRG (2-byte load $1800 + data).

    Uses ``song._mem`` (the parsed source's memory image) as the player template,
    so the player code, frequency table and arp/drum tables are byte-exact."""
    tmpl = song._mem
    base = song.base
    voice_lo_tbl = _u16(tmpl, base + _OFF_VOICE_LO)     # $1ea1
    voice_hi_tbl = _u16(tmpl, base + _OFF_VOICE_HI)     # $1ea4
    block_ptr_tbl = _u16(tmpl, base + _OFF_BLOCKPTR)    # $1ea7
    instr_base = _u16(tmpl, base + _OFF_INSTR_AD) - 2   # $2188

    mem = bytearray(0x10000)
    # Player + tables + pointer slots, verbatim up to the instrument table.
    mem[base:instr_base] = tmpl[base:instr_base]

    # Instruments (8 bytes each), 32 slots reserved so blocks start at a fixed spot.
    for i, ins in enumerate(song.instruments[:INSTR_SLOTS]):
        rec = bytes(ins.raw)
        mem[instr_base + i * 8: instr_base + i * 8 + 8] = rec
    addr = instr_base + INSTR_SLOTS * 8

    # Encode each voice into chunked blocks; assign global block indices and lay
    # the block data out after the instruments.
    block_addrs = []                       # global block# -> address
    voice_block_idx = [[], [], []]         # per voice, the global block# sequence
    gi = 0
    for v in range(3):
        for blk in encode_voice_blocks(song.voices[v] if v < len(song.voices) else []):
            if gi >= MAX_BLOCKS:
                break
            voice_block_idx[v].append(gi)
            block_addrs.append(addr)
            mem[addr:addr + len(blk)] = blk
            addr += len(blk)
            gi += 1

    # Block pointer table (lo/hi per block#).
    for i, ba in enumerate(block_addrs):
        mem[block_ptr_tbl + i * 2] = ba & 0xFF
        mem[block_ptr_tbl + i * 2 + 1] = (ba >> 8) & 0xFF

    # Orderlists: voice v plays its block sequence, then $ff = restart.
    ol_addrs = []
    for v in range(3):
        ol_addrs.append(addr)
        for idx in voice_block_idx[v]:
            mem[addr] = idx & 0xFF
            addr += 1
        mem[addr] = 0xFF
        addr += 1

    # Voice orderlist pointers.
    for v in range(3):
        mem[voice_lo_tbl + v] = ol_addrs[v] & 0xFF
        mem[voice_hi_tbl + v] = (ol_addrs[v] >> 8) & 0xFF

    end = addr
    return bytes([base & 0xFF, (base >> 8) & 0xFF]) + bytes(mem[base:end])
