"""SID Duzz' It (SDI, Geir Tjelta & Glenn Rune Gallefoss) — parser for the
1992 `play = init+3` generation (the dominant 222-file cluster in
SID/Gallefoss_Glenn/).

Ground truth: the authors' own commented player source (SDI 2.1 n49,
`bin/SIDDuzz/extracted/sdi21-n49.asm`, extracted from the user-staged d64s)
gives the SEMANTICS; the rip generation differs in memory layout (state in
page $03, split arrays) so every table address is extracted from the rip's
own CODE OPERANDS via byte-pattern signatures (relocation-safe like DMC /
Hubbard — the editor assembles the player per song, so addresses shift).
Decode map (RE'd from 30seconds.sid, cross-checked against the source; see
memory/gallefoss-sdi-player.md):

  HEADER   +0 jmp init / +3 jmp play / text (version slot)
  INIT     copies an 8-byte block -> state: track lo x3, track hi x3,
           tempo reload, spare; row step period = reload+1 frames
  TRACK    $ff = LOOP (next byte = new track position)
           $fd = flag/tempo byte (consumes none here)
           $c0-$fc = TRANSPOSE (value + $20, signed 8-bit add to notes)
           $80-$bf = sequence REPEAT count (& $3f)
           $00-$7f = SEQUENCE number
  SEQ      a row = [prefix]* + ONE terminal (RTS/row-end in the code):
           prefixes: $80-$bf = DURATION (& $3f, rows last dur+1 ticks;
                     loops for more bytes), $60-$7d = SOUND set (& $1f)
           terminals:
           $f0-$ff = RELEASE/GATE-OFF row (nibble -> release; dur ticks)
           $c1-$ef = GLIDE row (2-nibble speed + target-note byte)
           $c0     = TIE-NOTE row (next byte = note; no re-gate)
           $7f     = sequence END (honour track repeat, else track advance)
           $7e     = TIE row (re-apply instrument + next byte note)
           $5f     = REST row, next byte & $3f = NEW dur (persists)
           $00-$5e = NOTE row (retrigger; + resolved transpose)
  INSTR    column-major tables, stride = per-song instrument count
           (wfprg-start / AD / SR / flags[bit0 = ignore transpose] /
            pulse-speed / pulse-period / vib x2 / filter x3 / filt-route)
  FREQ     hi table + lo table, 96 notes (hi = lo - $60 in 30seconds)
"""
from dataclasses import dataclass, field
from typing import Optional
import struct


def load_sid(path):
    """(data_at_load, load_addr, header) — PSID/RSID, embedded-load aware."""
    raw = open(path, "rb").read()
    dataoff = struct.unpack(">H", raw[6:8])[0]
    load = struct.unpack(">H", raw[8:10])[0]
    init = struct.unpack(">H", raw[0x0A:0x0C])[0]
    play = struct.unpack(">H", raw[0x0C:0x0E])[0]
    data = raw[dataoff:]
    if load == 0:
        load = data[0] | (data[1] << 8)
        data = data[2:]

    class H:
        init_address = init
        play_address = play
    return bytes(data), load, H


def _find(d, pat):
    """First offset of `pat` in d; pat = list of ints, -1 = wildcard."""
    n = len(pat)
    for i in range(len(d) - n):
        ok = True
        for k, b in enumerate(pat):
            if b >= 0 and d[i + k] != b:
                ok = False
                break
        if ok:
            return i
    return None


def _w(d, off):
    return d[off] | (d[off + 1] << 8)


@dataclass
class SDILayout:
    """Table addresses extracted from the rip's own code operands."""
    variant: str = 'A'        # 'A' = init-copy gen (30seconds); 'B' = the
                              #  per-voice-array gen (Airwalk: $ff=restart,
                              #  any other >=$80 = transpose, no repeats)
    state: int = 0            # $0334-family base (track lo x3 from here)
    init_block: int = 0       # A: the 8-byte init copy source
    track_lo_arr: int = 0     # B: per-voice track ptr lo array (3)
    track_hi_arr: int = 0     # B: per-voice track ptr hi array (3)
    tempo_imm: int = -1       # B: tempo reload immediate (poked)
    seq_lo: int = 0
    seq_hi: int = 0
    freq_lo: int = 0
    freq_hi: int = 0
    ad_col: int = 0           # instrument AD column (SR = ad_col + stride)
    sr_col: int = 0
    stride: int = 0           # = per-song instrument count
    wfprg_start_col: int = 0  # per-instrument wf-program start index
    wf_col: int = 0           # wf-program waveform column
    wfarg_col: int = 0        # wf-program arg column ($7f rows: loop target)
    flags_col: int = 0        # bit0 = ignore track transpose


def locate(d, la):
    """Extract the layout from code patterns (operands wildcarded — the
    editor assembles the player per song, addresses are NOT fixed)."""
    lay = SDILayout()
    # variant A INIT copy: LDX #$07 / LDA $xxxx,X / STA $yyyy,X / DEX / BPL
    i = _find(d, [0xA2, 0x07, 0xBD, -1, -1, 0x9D, -1, -1, 0xCA, 0x10, 0xF7])
    if i is not None:
        lay.init_block = _w(d, i + 3)
        lay.state = _w(d, i + 6)
    else:
        # variant B track read: LDA $lo,X / STA zp / LDA $hi,X / STA zp /
        #   LDY $pos,X / LDA (zp),Y  (per-voice pointer ARRAYS, stride 3)
        i = _find(d, [0xBD, -1, -1, 0x85, -1, 0xBD, -1, -1, 0x85, -1,
                      0xBC, -1, -1, 0xB1, -1])
        if i is None:
            return None
        lay.variant = 'B'
        lay.track_lo_arr = _w(d, i + 1)
        lay.track_hi_arr = _w(d, i + 6)
        lay.state = _w(d, i + 11)
        # tempo reload immediate: DEC $t / BPL +n / LDA #imm / STA $t —
        # but init POKES the immediate from a song byte (LDA $src / STA
        # $imm_addr), so follow the poke; the static byte is pre-poke junk
        j = _find(d, [0xCE, -1, -1, 0x10, -1, 0xA9, -1, 0x8D, -1, -1])
        if j is not None:
            lay.tempo_imm = d[j + 6]
            imm_addr = la + j + 6
            k = _find(d, [0xAD, -1, -1, 0x8D, imm_addr & 0xFF,
                          (imm_addr >> 8) & 0xFF])
            if k is not None:
                src = _w(d, k + 1)
                if 0 <= src - la < len(d):
                    lay.tempo_imm = d[src - la]
        # instrument records (interleaved 8-byte): the sound-set tail
        #   ASL x3 / STA $x,X / TAY / LDA $base,Y / AND #$F0
        j = _find(d, [0x0A, 0x0A, 0x0A, 0x9D, -1, -1, 0xA8,
                      0xB9, -1, -1, 0x29, 0xF0])
        if j is not None:
            lay.ad_col = _w(d, j + 8)            # record base (byte 0)
            lay.stride = 8
        # arp records: ASL x3 / STA $x,X / TAY / LDA $base,Y / JMP
        j = _find(d, [0x0A, 0x0A, 0x0A, 0x9D, -1, -1, 0xA8,
                      0xB9, -1, -1, 0x4C])
        if j is not None:
            lay.wfprg_start_col = _w(d, j + 8)   # arp record base
        # freq tables: the two abs,Y read targets exactly $60 apart whose
        # combined words double per octave (content-verified — robust
        # against the per-song code shifts)
        reads = set()
        k = 0
        raw = bytes(d)
        while True:
            k = raw.find(b"\xb9", k)
            if k < 0 or k + 2 >= len(raw):
                break
            a = raw[k + 1] | (raw[k + 2] << 8)
            if la <= a < la + len(d) - 0x60:
                reads.add(a)
            k += 1
        for a in sorted(reads):
            for lo_a, hi_a in ((a + 0x60, a), (a, a + 0x60)):
                if lo_a not in reads or hi_a not in reads:
                    continue
                f = [(d[lo_a - la + n] | (d[hi_a - la + n] << 8))
                     for n in range(96)]
                hits = sum(1 for n in range(36, 60)
                           if f[n] and abs(f[n + 12] / f[n] - 2) < 0.02)
                if hits >= 20:
                    lay.freq_lo, lay.freq_hi = lo_a, hi_a
                    break
            if lay.freq_lo:
                break
    # SEQ ptr tables (both variants): TAY / LDA $llll,Y / STA zp / ...
    i = _find(d, [0xA8, 0xB9, -1, -1, 0x85, -1, 0xB9, -1, -1, 0x85, -1])
    if i is None:
        return None
    lay.seq_lo = _w(d, i + 2)
    lay.seq_hi = _w(d, i + 7)
    if lay.variant == 'B':
        return lay
    # FREQ tables via the glide compare:
    #   LDY $tgt,X / SEC / LDA $lo,Y / CMP $cur,X / LDA $hi,Y / SBC $cur+3,X
    i = _find(d, [0xBC, -1, -1, 0x38, 0xB9, -1, -1, 0xDD, -1, -1,
                  0xB9, -1, -1, 0xFD, -1, -1])
    if i is not None:
        lay.freq_lo = _w(d, i + 5)
        lay.freq_hi = _w(d, i + 11)
    # AD/SR columns + stride from the $D405/$D406 write:
    #   LDA $sr,Y / AND #$F0 / ORA $rel,X / LDX zp / STA $D406,X
    #   ... LDA $ad,Y / STA $D405,X
    i = _find(d, [0xB9, -1, -1, 0x29, 0xF0, 0x1D, -1, -1, 0xA6, -1,
                  0x9D, 0x06, 0xD4])
    if i is not None:
        lay.sr_col = _w(d, i + 1)
        j = _find(d[i:i + 40], [0xB9, -1, -1, 0x9D, 0x05, 0xD4])
        if j is not None:
            lay.ad_col = _w(d, i + j + 1)
            lay.stride = lay.sr_col - lay.ad_col
    # wf program: LDA $wprgstart,Y (via ADC) ... LDA $wf,Y / CMP #$7F /
    #   BNE +8 / LDA $arg,Y / STA $pos,X / BPL
    i = _find(d, [0x79, -1, -1, 0xA8, 0xB9, -1, -1, 0xC9, 0x7F, 0xD0, -1,
                  0xB9, -1, -1])
    if i is not None:
        lay.wfprg_start_col = _w(d, i + 1)
        lay.wf_col = _w(d, i + 5)
        lay.wfarg_col = _w(d, i + 12)
    # flags column: LDA $flags,Y / AND #$01 / EOR #$01
    i = _find(d, [0xB9, -1, -1, 0x29, 0x01, 0x49, 0x01])
    if i is not None:
        lay.flags_col = _w(d, i + 1)
    return lay


def is_sdi_play3(d, la, h):
    """The play = init+3 generation: jmp/jmp header + the init-copy and
    seq-pointer signatures present."""
    if h.play_address != h.init_address + 3:
        return False
    if len(d) < 8 or d[0] != 0x4C or d[3] != 0x4C:
        return False
    return locate(d, la) is not None


@dataclass
class SDIEvent:
    frame: int
    kind: str                 # 'note' | 'tie' | 'glide' | 'rest' | 'off'
    note: Optional[int] = None
    instr: int = 0
    dur_ticks: int = 1


class SDIModule:
    """Decoded song: per-voice event streams with the play routine's frame
    clock (row step every tempo_reload+1 frames, first step at frame 0)."""

    def __init__(self, d, la):
        self.d = d
        self.la = la
        self.lay = locate(d, la)
        if self.lay is None:
            raise ValueError("not an SDI play+3 rip (signatures missing)")
        if self.lay.variant == 'A':
            blk = self.lay.init_block - la
            self.track_ptrs = [(d[blk + v] | (d[blk + 3 + v] << 8))
                               for v in range(3)]
            self.tempo_reload = d[blk + 6]
        else:                                    # B: per-voice arrays
            lo, hi = self.lay.track_lo_arr - la, self.lay.track_hi_arr - la
            self.track_ptrs = [(d[lo + v] | (d[hi + v] << 8))
                               for v in range(3)]
            self.tempo_reload = max(0, self.lay.tempo_imm)
        self.fpt = self.tempo_reload + 1

    def _u8(self, addr):
        off = addr - self.la
        return self.d[off] if 0 <= off < len(self.d) else 0

    def seq_addr(self, num):
        return (self._u8(self.lay.seq_lo + num)
                | (self._u8(self.lay.seq_hi + num) << 8))

    def note_freq(self, note):
        n = note & 0x7F
        return (self._u8(self.lay.freq_lo + n)
                | (self._u8(self.lay.freq_hi + n) << 8))

    def instr_flags(self, instr):
        return self._u8(self.lay.flags_col + (instr % max(1, self.lay.stride)))

    def decode_voice(self, v, max_ticks=40000):
        """Walk track+sequences -> [SDIEvent] (frames on the tick grid)."""
        lay = self.lay
        tpos = 0
        transpose = 0
        repeat = 0
        tick = 0
        instr = 0
        events = []
        guard = 0
        track = self.track_ptrs[v]
        seen_loop = set()
        vb = self.lay.variant == 'B'
        while tick < max_ticks and guard < 100000:
            guard += 1
            b = self._u8(track + tpos)
            if b == 0xFF:
                if vb:                           # B: song RESTART -> stop
                    break
                new = self._u8(track + tpos + 1)  # A: LOOP to position
                if (tpos, new) in seen_loop:
                    break                        # full track loop -> stop
                seen_loop.add((tpos, new))
                tpos = new
                continue
            if not vb and b == 0xFE:             # A: track STOP
                break
            if not vb and b == 0xFD:             # A: flag/tempo byte
                tpos += 1
                continue
            if b >= (0x80 if vb else 0xC0):      # transpose (+$20, signed)
                transpose = (b + 0x20) & 0xFF
                if transpose >= 0x80:
                    transpose -= 0x100
                tpos += 1
                continue
            if b >= 0x80:                        # A: sequence repeat count
                repeat = b & 0x3F
                tpos += 1
                continue
            # sequence number
            seq = self.seq_addr(b)
            plays = repeat + 1
            repeat = 0
            for _ in range(plays):
                tick = self._play_seq(v, seq, tick, transpose, events,
                                      max_ticks)
                if tick >= max_ticks:
                    break
            tpos += 1
        return events

    def _play_seq_b(self, v, seq, tick, transpose, events, max_ticks):
        """Variant B row model: $80-$bf dur (b-$80; $3f -> next byte) /
        $c0-$df instrument (& $1f, 8-byte records) / $e0-$ff arp select
        (records; byte0 redirects the instrument) / $60-$6f sustain-modify
        — all CONTINUE; terminals: $70-$7f gate-off row, $5f dur2+note,
        $00-$5e note (+transpose, unconditional). $60 at ROW START = seq
        end. Row lasts dur+1 ticks."""
        instr = getattr(self, "_cur_instr", [0, 0, 0])
        pos = 0
        dur = 0
        guard = 0
        row_start = True
        while tick < max_ticks and guard < 20000:
            guard += 1
            b = self._u8(seq + pos)
            if row_start and b == 0x60:          # sequence END marker
                break
            pos += 1
            row_start = False
            if 0x80 <= b <= 0xBF:                # duration prefix
                dur = b - 0x80
                if dur == 0x3F:
                    dur = self._u8(seq + pos) & 0x3F
                    pos += 1
                continue
            if 0xC0 <= b <= 0xDF:                # instrument set
                instr[v] = b & 0x1F
                self._cur_instr = instr
                continue
            if b >= 0xE0:                        # arp select (instr redirect)
                continue
            if 0x70 <= b <= 0x7F:                # gate-off/release row
                events.append(SDIEvent(tick * self.fpt, 'off', None,
                                       instr[v], dur + 1))
                tick += dur + 1
                row_start = True
                continue
            if 0x61 <= b <= 0x6F:                # sustain-modify (mid-row)
                continue
            if b == 0x5F:                        # gate-time + note row
                pos += 1                         # gate-time byte (unused here)
                note = (self._u8(seq + pos) + transpose) & 0xFF
                pos += 1
                events.append(SDIEvent(tick * self.fpt, 'note', note,
                                       instr[v], dur + 1))
                tick += dur + 1
                row_start = True
                continue
            # NOTE row (transpose is unconditional in B)
            note = (b + transpose) & 0xFF
            events.append(SDIEvent(tick * self.fpt, 'note', note,
                                   instr[v], dur + 1))
            tick += dur + 1
            row_start = True
        return tick

    def _play_seq(self, v, seq, tick, transpose, events, max_ticks):
        if self.lay.variant == 'B':
            return self._play_seq_b(v, seq, tick, transpose, events,
                                    max_ticks)
        lay = self.lay
        pos = 0
        dur = 0
        instr = getattr(self, "_cur_instr", [0, 0, 0])
        rel = 0
        guard = 0
        while tick < max_ticks and guard < 20000:
            guard += 1
            b = self._u8(seq + pos)
            pos += 1
            if b >= 0xF0:                       # RELEASE/GATE-OFF row
                rel = b & 0x0F
                events.append(SDIEvent(tick * self.fpt, 'off', None,
                                       instr[v], dur + 1))
                tick += dur + 1
                continue
            if b >= 0xC1:                       # glide cmd + target byte
                tgt = self._u8(seq + pos)
                pos += 1
                note = (tgt + self._transpose_for(v, transpose)) & 0xFF
                events.append(SDIEvent(tick * self.fpt, 'glide', note,
                                       instr[v], dur + 1))
                tick += dur + 1
                continue
            if b == 0xC0:                       # tie-note (no re-gate)
                note = (self._u8(seq + pos)
                        + self._transpose_for(v, transpose)) & 0xFF
                pos += 1
                events.append(SDIEvent(tick * self.fpt, 'tie', note,
                                       instr[v], dur + 1))
                tick += dur + 1
                continue
            if b >= 0x80:                       # duration
                dur = b & 0x3F
                continue
            if b == 0x7F:                       # sequence end
                break
            if b == 0x7E:                       # TIE (re-apply instr + note)
                note = (self._u8(seq + pos)
                        + self._transpose_for(v, transpose)) & 0xFF
                pos += 1
                events.append(SDIEvent(tick * self.fpt, 'tie', note,
                                       instr[v], dur + 1))
                tick += dur + 1
                continue
            if b >= 0x60:                       # sound set
                instr[v] = b & 0x1F
                self._cur_instr = instr
                continue
            if b == 0x5F:                       # REST row + new persistent dur
                dur = self._u8(seq + pos) & 0x3F
                pos += 1
                events.append(SDIEvent(tick * self.fpt, 'rest', None,
                                       instr[v], dur + 1))
                tick += dur + 1
                continue
            # NOTE (retrigger)
            note = (b + self._transpose_for(v, transpose)) & 0xFF
            events.append(SDIEvent(tick * self.fpt, 'note', note,
                                   instr[v], dur + 1))
            tick += dur + 1
        return tick

    def _transpose_for(self, v, transpose):
        # instrument flag bit0 = ignore track transpose; instrument is
        # per-voice current — approximate with the voice's running instr
        cur = getattr(self, "_cur_instr", [0, 0, 0])[v]
        if self.lay.flags_col and (self.instr_flags(cur) & 1):
            return 0
        return transpose

    def events(self):
        self._cur_instr = [0, 0, 0]
        return [self.decode_voice(v) for v in range(3)]
