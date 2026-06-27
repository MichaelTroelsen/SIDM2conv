"""Future Composer (C64, "The Beat-Machine" FC 1.0 / V4.1) song extractor.

Reverse-engineered from the player embedded in the Fun_Fun SID rips (player at
$1800, init $1800, play $1806). The player is a per-voice pattern interpreter:

    orderlist (per voice)  ->  block numbers (+ transpose / repeat control)
    block (pattern)        ->  a stream of commands + note rows
    instrument ("sound")   ->  8-byte record (pulse, waveform, AD, SR, ... )
    freq table             ->  96-entry PAL frequency table indexed by note

All table addresses are read from fixed *code* operand sites (relocation-safe:
the song-data positions vary per tune, but the player code layout is constant),
keyed off the detected player base.

Block / orderlist byte semantics (RE'd from the $1806 play routine):

  Orderlist byte (read at ($voiceptr),y):
    $fe              -> stop song
    $ff              -> restart (loop)
    b & $80          -> set transpose = b & $1f   (added to following notes)
    b & $40          -> set repeat   = b & $3f   (next block plays 1+n times)
    else ($00-$3f)   -> block number

  Block byte (read at ($blockptr),y):
    b & $f0 == $f0   -> tie: next byte is a note, played without retrigger
    b & $f0 == $e0   -> glide/portamento command (consumes 2 param bytes)
    b & $e0 == $c0   -> set instrument = b & $1f
    b & $c0 == $80   -> set duration   = b & $3f
    $ff              -> end of block
    else ($00-$7f)   -> note row (freq-table index; >= 96 -> effective rest)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# --- fixed code-site offsets from the player base (load address) -------------
# Each is the offset of the 16-bit operand of an absolute,(x|y) instruction.
_OFF_VOICE_LO   = 0x05a   # $1859: LDA $1ea1,x  -> voice orderlist ptr lo[3]
_OFF_VOICE_HI   = 0x05f   # $185e: LDA $1ea4,x  -> voice orderlist ptr hi[3]
_OFF_BLOCKPTR   = 0x0c4   # $18c3: LDA $1ea7,y  -> block ptr table (lo/hi pairs)
_OFF_FREQ_LO    = 0x168   # $1967: LDA $1d64,y  -> freq table lo
_OFF_FREQ_HI    = 0x16c   # $196b: LDA $1dc4,y  -> freq table hi
_OFF_INSTR_AD   = 0x191   # $1990: LDA $218a,x  -> instr_base + 2 (AD column)
_OFF_SPEED      = 0x91d   # $211d byte = master speed (referenced at $1854 etc.)
# Drum tables: per-drumtype pointers to a waveform sequence and a pitch sequence
# (operands of the LDA $1e3e/$1e40/$1e42/$1e44,x sites at $1c8b/$1c91/$1c97/$1c9d).
_OFF_DRUM_WFLO  = 0x48c   # $1c8c: -> $1e3e  (drum waveform-table addr lo[dt])
_OFF_DRUM_WFHI  = 0x492   # $1c92: -> $1e40  (drum waveform-table addr hi[dt])
_OFF_DRUM_PLO   = 0x498   # $1c98: -> $1e42  (drum pitch-table addr lo[dt])
_OFF_DRUM_PHI   = 0x49e   # $1c9e: -> $1e44  (drum pitch-table addr hi[dt])

DRUM_LEN = 14            # the drum plays its first 14 player frames ($2142 < $0f)
DRUM_PITCH_BIAS = 0x0D   # freq_hi = pitch_seq[i] + $0d (absolute path at $1cd6)

NUM_NOTES = 96            # freq table entries ($00-$5f valid; >= 96 = rest)


@dataclass
class FCInstrument:
    """An 8-byte Future Composer 'sound' record."""
    index: int
    pulse: int          # [0] initial pulse level
    waveform: int       # [1] initial waveform/control byte
    ad: int             # [2] attack/decay -> $d405
    sr: int             # [3] sustain/release -> $d406
    unused: int         # [4]
    vibrato: int        # [5] vibrato / drumtype
    arp: int            # [6] arpeggio ctrl
    mctrl: int          # [7] MCTRL ($01 filter, $04 arp, $10 drum, gate bits)

    @property
    def raw(self) -> List[int]:
        return [self.pulse, self.waveform, self.ad, self.sr,
                self.unused, self.vibrato, self.arp, self.mctrl]


@dataclass
class FCNote:
    """One decoded block row."""
    note: int           # freq-table index (>= NUM_NOTES means rest)
    dur: int            # duration in player ticks
    instr: int          # current instrument number
    tie: bool = False   # played without retrigger (portamento/legato)

    @property
    def is_rest(self) -> bool:
        return self.note >= NUM_NOTES


@dataclass
class FCSong:
    load: int
    base: int
    speed: int
    freq_lo: List[int]
    freq_hi: List[int]
    instruments: List[FCInstrument]
    voices: List[List[FCNote]] = field(default_factory=list)   # 3 flattened voices
    voice_blocks: List[List[List[FCNote]]] = field(default_factory=list)  # per-block
    block_ptrs: Dict[int, int] = field(default_factory=dict)
    _mem: bytes = b""
    _drum_tbls: Tuple[int, int, int, int] = (0, 0, 0, 0)

    def freq(self, idx: int) -> int:
        if 0 <= idx < NUM_NOTES:
            return self.freq_lo[idx] | (self.freq_hi[idx] << 8)
        return 0

    def drum_sequence(self, drumtype: int
                      ) -> List[Tuple[int, int]]:
        """Resolve a drum (mctrl & $10) into a per-frame (waveform, SID freq)
        sequence of length DRUM_LEN. drumtype = instrument byte [5] & $0f.
        freq = (pitch_seq[i] + $0d) << 8 (the absolute path at $1cd6, freq_lo=0)."""
        wflo, wfhi, plo, phi = self._drum_tbls
        m = self._mem
        dt = drumtype & 0x0F
        wf_addr = m[(wflo + dt) & 0xFFFF] | (m[(wfhi + dt) & 0xFFFF] << 8)
        pt_addr = m[(plo + dt) & 0xFFFF] | (m[(phi + dt) & 0xFFFF] << 8)
        out = []
        for i in range(DRUM_LEN):
            wf = m[(wf_addr + i) & 0xFFFF]
            pitch = m[(pt_addr + i) & 0xFFFF]
            freq = ((pitch + DRUM_PITCH_BIAS) & 0xFF) << 8
            out.append((wf, freq))
        return out


def _u16(mem: bytes, off: int) -> int:
    return mem[off] | (mem[off + 1] << 8)


def detect_player(data: bytes, load: int) -> bool:
    """Heuristic: the FC player begins with two JMPs then an LDA/CMP #$02."""
    # $1800: 4c .. .. 4c .. .. ad .. .. c9 02
    return (len(data) > 0x12 and data[0] == 0x4c and data[3] == 0x4c
            and data[6] == 0xad and data[9] == 0xc9 and data[10] == 0x02)


# ---------------------------------------------------------------------------
# Orderlist + block decoding
# ---------------------------------------------------------------------------

def _decode_voice(mem: bytes, order_addr: int, block_ptr_tbl: int,
                  max_blocks: int
                  ) -> Tuple[List[FCNote], List[List[FCNote]], Dict[int, int]]:
    """Walk one voice's orderlist, expanding blocks (with transpose/repeat).

    Returns (flat_notes, blocks, seen_blocks) where ``blocks`` is one FCNote list
    per orderlist block *instance* (so the SF2 emitter can keep FC's structure:
    each block -> one short sequence, the orderlist replays them). Instrument /
    duration state threads across blocks, matching the player. Stops at $fe/$ff
    or after a bounded number of orderlist steps (loop guard)."""
    notes: List[FCNote] = []
    blocks: List[List[FCNote]] = []
    seen_blocks: Dict[int, int] = {}
    transpose = 0
    repeat = 0
    oi = 0
    cur_instr = 0
    cur_dur = 1
    steps = 0
    MAX_ROWS = 65536                          # hard cap so repeats can't explode
    while steps < 4096 and len(notes) < MAX_ROWS:
        steps += 1
        b = mem[(order_addr + oi) & 0xFFFF]
        if b == 0xFE or b == 0xFF:           # stop / loop -> one pass done
            break
        if b & 0x80:                          # transpose
            transpose = b & 0x1F
            oi += 1
            continue
        if b & 0x40:                          # repeat the next block (1+n times)
            repeat = b & 0x3F
            oi += 1
            continue
        block = b
        if block >= max_blocks:
            oi += 1
            continue
        baddr = _u16(mem, block_ptr_tbl + block * 2)
        seen_blocks[block] = baddr
        plays = repeat + 1
        repeat = 0
        for _ in range(plays):
            rows, cur_instr, cur_dur = _decode_block(
                mem, baddr, transpose, cur_instr, cur_dur)
            notes.extend(rows)
            blocks.append(rows)
        oi += 1
    return notes, blocks, seen_blocks


def _decode_block(mem: bytes, addr: int, transpose: int,
                  cur_instr: int, cur_dur: int
                  ) -> Tuple[List[FCNote], int, int]:
    """Decode one block into note rows, threading instrument/duration state."""
    rows: List[FCNote] = []
    i = 0
    guard = 0
    while guard < 1024:
        guard += 1
        b = mem[(addr + i) & 0xFFFF]
        if b == 0xFF:                         # end of block
            break
        if (b & 0xF0) == 0xF0:                # tie -> next byte is the note
            i += 1
            note = mem[(addr + i) & 0xFFFF]
            rows.append(FCNote((note + transpose) & 0xFF, cur_dur,
                               cur_instr, tie=True))
            i += 1
            continue
        if (b & 0xF0) == 0xE0:                # glide command: 2 param bytes
            i += 2                            # skip cmd + param byte
            # next byte continues as a normal token (note/dur/etc.)
            continue
        if (b & 0xE0) == 0xC0:                # set instrument
            cur_instr = b & 0x1F
            i += 1
            continue
        if (b & 0xC0) == 0x80:                # set duration
            cur_dur = b & 0x3F
            i += 1
            continue
        # else: a note row ($00-$7f)
        rows.append(FCNote((b + transpose) & 0xFF, cur_dur, cur_instr))
        i += 1
    return rows, cur_instr, cur_dur


# ---------------------------------------------------------------------------
# Top-level parse
# ---------------------------------------------------------------------------

def parse_fc(data: bytes, load: int) -> FCSong:
    """Parse a Future Composer SID payload (player + song data) at `load`."""
    mem = bytearray(0x10000)
    mem[load:load + len(data)] = data
    base = load                               # player base == load for these rips

    voice_lo = _u16(mem, base + _OFF_VOICE_LO)
    voice_hi = _u16(mem, base + _OFF_VOICE_HI)
    block_ptr_tbl = _u16(mem, base + _OFF_BLOCKPTR)
    freq_lo_a = _u16(mem, base + _OFF_FREQ_LO)
    freq_hi_a = _u16(mem, base + _OFF_FREQ_HI)
    instr_base = _u16(mem, base + _OFF_INSTR_AD) - 2
    speed = mem[base + _OFF_SPEED]

    freq_lo = [mem[(freq_lo_a + i) & 0xFFFF] for i in range(NUM_NOTES)]
    freq_hi = [mem[(freq_hi_a + i) & 0xFFFF] for i in range(NUM_NOTES)]

    # voice orderlist pointers (3 voices, lo[3] then hi[3])
    voice_ptrs = []
    for v in range(3):
        lo = mem[(voice_lo + v) & 0xFFFF]
        hi = mem[(voice_hi + v) & 0xFFFF]
        voice_ptrs.append(lo | (hi << 8))

    # block count: scan orderlists for the max referenced block (bounded probe)
    max_blocks = _probe_block_count(mem, voice_ptrs)

    voices: List[List[FCNote]] = []
    voice_blocks: List[List[List[FCNote]]] = []
    all_blocks: Dict[int, int] = {}
    max_instr = 0
    for vp in voice_ptrs:
        rows, blocks, seen = _decode_voice(mem, vp, block_ptr_tbl, max_blocks)
        voices.append(rows)
        voice_blocks.append(blocks)
        all_blocks.update(seen)
        for r in rows:
            max_instr = max(max_instr, r.instr)

    instruments = []
    for n in range(max_instr + 1):
        rec = [mem[(instr_base + n * 8 + k) & 0xFFFF] for k in range(8)]
        instruments.append(FCInstrument(n, *rec))

    drum_tbls = (_u16(mem, base + _OFF_DRUM_WFLO),
                 _u16(mem, base + _OFF_DRUM_WFHI),
                 _u16(mem, base + _OFF_DRUM_PLO),
                 _u16(mem, base + _OFF_DRUM_PHI))

    return FCSong(load=load, base=base, speed=speed,
                  freq_lo=freq_lo, freq_hi=freq_hi,
                  instruments=instruments, voices=voices,
                  voice_blocks=voice_blocks,
                  block_ptrs=all_blocks, _mem=bytes(mem),
                  _drum_tbls=drum_tbls)


def _probe_block_count(mem: bytes, voice_ptrs: List[int]) -> int:
    """Find the highest block number referenced across the three orderlists."""
    hi = 0
    for vp in voice_ptrs:
        for i in range(4096):
            b = mem[(vp + i) & 0xFFFF]
            if b in (0xFE, 0xFF):
                break
            if not (b & 0x80) and not (b & 0x40):
                hi = max(hi, b)
    return hi + 1
