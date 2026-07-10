"""Rob Hubbard v1 player parser (the C=Hacking #5 "Monty on the Run" routine).

Engine (RE'd from Anthony McSweeney's commented disassembly, saved at
docs/analysis/hubbard/chacking5_monty_disassembly.txt; used with slight mods in
~30 tunes: Confuzion, Thing on a Spring, Monty, Action Biker, Crazy Comets,
Commando, Chimera, The Last V8, Master of Magic, One Man & His Droid, Thrust,
International Karate, Spellbound, ...):

- `songs` table: 6 bytes per song = the 3 per-voice TRACK pointers, stored as
  the two 3-byte halves the init copy loop fills (`currtrkhi[0..2]` then
  `currtrklo[0..2]` — NB the labels are swapped vs their ZP use: the "hi" half
  feeds the POINTER LOW byte).
- TRACK = list of pattern numbers; `$ff` = loop the song, `$fe` = play once
  (halt). Position = index into this list.
- PATTERN = note stream, `$ff`-terminated. Note spec 1-3 bytes:
    byte0: bits0-4 = length in note-ticks (note lasts length+1 ticks);
           bit5 = no release; bit6 = APPEND (tie: no re-gate, keeps pitch
           bytes out — the note continues with new length); bit7 = a second
           byte follows.
    byte1 (iff bit7): +ve = instrument number, -ve = portamento speed
           (bit0 = direction, 1 = down; the rest = per-frame freq delta).
    byte2 (unless APPEND): pitch semitone (0 = C-0, via the interleaved
           16-bit freq table at `frequenzlo`, indexed pitch*2).
- INSTRUMENT = 8 bytes: [PW lo, PW hi, ctrl, AD, SR, vibrato depth,
  pulse speed, fx]. fx bits: 0 = drum, 1 = skydive, 2 = octave arpeggio
  (later routines add more).
- TEMPO: play runs at 50Hz; `speed` cycles resetspd..0; note ticks happen on
  frames where speed == resetspd -> one note-tick every (resetspd+1) frames.

Table locations are found by RELOCATION-SAFE code signatures (playbook rule:
per-file confirmed, never hardcoded):
  songs   : the init copy loop  BD ll hh 99 ll hh E8 C8 C0 06 D0
  patterns: getnotedata         A8 B9 ll hh 85 zz B9 ll hh 85 zz
  freq    : getpitch            0A A8 B9 ll hh 8D ?? ?? B9 (ll+1) hh'
  instr   : appendnote          0A 0A 0A AA BD ll hh   (operand = instr+2)
  speed   : contplay            CE ll hh 10 ?? AD mm nn 8D ll hh
"""
from dataclasses import dataclass, field

from sidm2.sid_parser import SIDParser


def load_sid(path):
    """PSID/RSID -> (data bytes, load address, header). Handles load=0."""
    raw = open(path, "rb").read()
    h = SIDParser(path).parse_header()
    d = raw[h.data_offset:]
    la = h.load_address
    if la == 0 and len(d) >= 2:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la, h


def _find_all(d, sig):
    """All offsets where the byte pattern matches (None = wildcard)."""
    out = []
    n = len(sig)
    for i in range(len(d) - n):
        if all(s is None or d[i + k] == s for k, s in enumerate(sig)):
            out.append(i)
    return out


@dataclass
class HubbardLayout:
    songs: int = 0            # 6-byte-per-song track-pointer table
    songs_split: bool = False  # v2 (Thing_on_a_Spring class): songs/track ptrs
                               # are SPLIT lo/hi tables indexed X=song*3+voice;
                               # `songs` = lo base, `songs_hi` = hi base
    songs_hi: int = 0
    trk_ptr_a: int = 0        # currtrk half A (feeds ZP pointer LOW)
    patptl: int = 0           # pattern pointer table lo
    patpth: int = 0           # pattern pointer table hi
    freq: int = 0             # interleaved lo,hi 16-bit freq table (pitch*2)
    instr: int = 0            # 8-byte instrument records
    speed_addr: int = 0
    resetspd_addr: int = 0
    zp_trk: int = 0           # ZP pair for the track pointer
    zp_pat: int = 0           # ZP pair for the pattern pointer
    swallow_addr: int = 0     # v2 fractional tempo: a second countdown; on
    swallow_period: int = 0   #   expiry (every `period` frames) the player
                              #   SKIPS the speed dec — one tick stretches by
                              #   a frame (Sanxion 109, Delta 5, Thundercats 4)
    v2_notes: bool = False    # v2 note format (Delta class): $60-len = 1-byte
                              #   rest, 4-byte porta, pitch bit7 = no-fetch
    instrnr_addr: int = 0     # per-voice CURRENT instrument array (the fetch's
                              #   LDA instrnr,X) — init seeds per-voice defaults
                              #   that notes without an instrument byte inherit
    pulsespeed_tbl: int = 0   # SPLIT per-instrument pulse-speed array (the
                              #   transposed-track revisions keep speed in a
                              #   separate stride-8 table, not record[6])
    trk_transpose: int = 0    # track bit7-byte TRANSPOSE encoding: 0 = none (V1 —
                              #   tracks are plain pattern numbers), 1 = one-byte
                              #   ($80|semis, transpose = b & $7F; Shockway/
                              #   Star_Paws/Saboteur_II), 2 = two-byte ($80 nn,
                              #   transpose = the NEXT byte; Auf_Wiedersehen).
                              #   Without this the $8x bytes decode as pattern
                              #   numbers 128+ -> garbage patterns -> one voice
                              #   "decodes" 10x too long -> a 4013s span -> 638
                              #   SF2 parts of repeats (Shockway).


SONGS_COPY_SIG = [0xBD, None, None, 0x99, None, None, 0xE8, 0xC8, 0xC0, 0x06, 0xD0]


class HubbardModule:
    """Detected + decoded Hubbard v1 module (all songs).

    Compilation rips (e.g. 5_Title_Tunes) embed SEVERAL complete players in one
    file; `module` selects which one — every code-signature search is windowed
    to that module's region (between the neighbouring songs-copy hits)."""

    def __init__(self, d, la, module=0):
        self.d, self.la, self.module = d, la, module
        self.lay = self._locate(module)

    @staticmethod
    def module_count(d):
        return len(_find_all(d, SONGS_COPY_SIG))

    @staticmethod
    def module_hits(d):
        return _find_all(d, SONGS_COPY_SIG)

    def _u8(self, addr):
        off = addr - self.la
        return self.d[off] if 0 <= off < len(self.d) else 0

    def _u16(self, addr):
        return self._u8(addr) | (self._u8(addr + 1) << 8)

    # ---------------- detection ----------------
    def _locate(self, module=0):
        d = self.d
        lay = HubbardLayout()
        # songs copy loop: LDA songs,X / STA trk,Y / INX / INY / CPY #6 / BNE
        mhits = _find_all(d, SONGS_COPY_SIG)
        if mhits:
            if module >= len(mhits):
                raise ValueError(f"module {module} of {len(mhits)}")
            i = mhits[module]
            # Rob's module layout = [play code ... init (songs-copy loop)]:
            # the code signatures PRECEDE their module's songs-copy hit.
            # Window = (previous module's songs-copy, this one]; single-module
            # files use the whole image (some rips rearrange init).
            if len(mhits) == 1:
                w_lo, w_hi = 0, len(d)
            else:
                w_lo = 0 if module == 0 else mhits[module - 1] + 1
                w_hi = i + 1
            lay.songs = d[i + 1] | (d[i + 2] << 8)
            lay.trk_ptr_a = d[i + 4] | (d[i + 5] << 8)
        else:
            # v2 (Thing_on_a_Spring class): no copy loop — per-voice track
            # pointers load from SPLIT lo/hi tables straight into a ZP pair:
            # LDA lo,X / STA zp / LDA hi,X / STA zp+1
            w_lo, w_hi = 0, len(d)
            hits = _find_all(d, [0xBD, None, None, 0x85, None,
                                 0xBD, None, None, 0x85, None])
            cand = [j for j in hits if d[j + 9] == d[j + 4] + 1]
            if not cand:
                raise ValueError("no Hubbard songs-copy signature")
            j = cand[0]
            lay.songs_split = True
            lay.songs = d[j + 1] | (d[j + 2] << 8)
            lay.songs_hi = d[j + 6] | (d[j + 7] << 8)

        def first_in(cands):
            inw = [c for c in cands if w_lo <= c < w_hi]
            return inw[0] if inw else None

        # pattern ptr load: TAY / LDA patptl,Y / STA zp / LDA patpth,Y / STA zp
        hits = _find_all(d, [0xA8, 0xB9, None, None, 0x85, None,
                             0xB9, None, None, 0x85, None])
        # disambiguate from other TAY/LDA abs,Y pairs by requiring consecutive
        # ZP stores (a pointer pair)
        i = first_in([j for j in hits if d[j + 10] == d[j + 5] + 1])
        if i is None:
            raise ValueError("no Hubbard pattern-pointer signature")
        lay.patptl = d[i + 2] | (d[i + 3] << 8)
        lay.patpth = d[i + 7] | (d[i + 8] << 8)
        lay.zp_pat = d[i + 5]

        # freq: LDA freq,Y / STA / LDA freq+1,Y — an interleaved lo,hi pair.
        # v1 uses STA abs ($8D) with a leading ASL/TAY; later revisions use
        # STA abs,X ($9D — Delta) or STA zp ($85). Prefer the strict v1 form,
        # fall back to the relaxed pair scans.
        def freq_scan(sig, off_lo, off_hi):
            cand = []
            for j in _find_all(d, sig):
                lo = d[j + off_lo] | (d[j + off_lo + 1] << 8)
                hi = d[j + off_hi] | (d[j + off_hi + 1] << 8)
                if hi == lo + 1 and lo >= 0x100:
                    cand.append((j, lo))
            return cand
        i = None
        for sig, off_lo, off_hi in (
                ([0x0A, 0xA8, 0xB9, None, None, 0x8D, None, None,
                  0xB9, None, None], 3, 9),                       # v1 strict
                ([0xB9, None, None, 0x8D, None, None, 0xB9, None, None], 1, 7),
                ([0xB9, None, None, 0x9D, None, None, 0xB9, None, None], 1, 7),
                ([0xB9, None, None, 0x85, None, 0xB9, None, None], 1, 6)):
            cand = freq_scan(sig, off_lo, off_hi)
            j = first_in([c for c, _ in cand])
            if j is not None:
                lay.freq = dict(cand)[j]
                i = j
                break
        if i is None:
            raise ValueError("no Hubbard freq-table signature")

        # instr: ASL ASL ASL TAX / LDA instr+2,X
        i = first_in(_find_all(d, [0x0A, 0x0A, 0x0A, 0xAA, 0xBD, None, None]))
        if i is None:
            raise ValueError("no Hubbard instrument signature")
        lay.instr = (d[i + 5] | (d[i + 6] << 8)) - 2

        # speed: DEC speed / BPL / LDA resetspd / STA speed
        hits = _find_all(d, [0xCE, None, None, 0x10, None, 0xAD, None, None,
                             0x8D, None, None])
        for j in hits:
            if not (w_lo <= j < w_hi):
                continue
            sp = d[j + 1] | (d[j + 2] << 8)
            if (d[j + 9] | (d[j + 10] << 8)) == sp:
                lay.speed_addr = sp
                lay.resetspd_addr = d[j + 6] | (d[j + 7] << 8)
                break

        # v2 fractional tempo (the swallow counter): DEC abs / BPL / LDA #v /
        # STA same-abs / JMP — on expiry the speed dec is skipped one frame
        for j in _find_all(d, [0xCE, None, None, 0x10, None, 0xA9, None,
                               0x8D, None, None, 0x4C]):
            if not (w_lo <= j < w_hi):
                continue
            if d[j + 1] == d[j + 8] and d[j + 2] == d[j + 9]:
                lay.swallow_addr = d[j + 1] | (d[j + 2] << 8)
                lay.swallow_period = d[j + 6] + 1
                break

        # v2 note format: the pattern parser tests len-byte bits 5+6 together
        # (AND #$60 / CMP #$60 / BNE) — 1-byte rests, 4-byte porta, pitch
        # bit7 no-fetch (Delta class)
        lay.v2_notes = any(w_lo <= j < w_hi
                           for j in _find_all(d, [0x29, 0x60, 0xC9, 0x60, 0xD0]))

        # per-voice current-instrument array: LDA instrnr,X / STX tmp /
        # ASL ASL ASL / TAX (the note fetch) — init seeds per-voice defaults
        j = first_in(_find_all(d, [0xBD, None, None, 0x8E, None, None,
                                   0x0A, 0x0A, 0x0A, 0xAA]))
        if j is not None:
            lay.instrnr_addr = d[j + 1] | (d[j + 2] << 8)

        # SPLIT pulse-speed table (the transposed-track revisions): the instrument
        # fetch pushes pulse state as LDA field,X / PHA — pwlo (instr+0) and pwhi
        # (instr+1) plus a THIRD push from a base OUTSIDE the 8-byte record
        # (Shockway $F2F1 vs instr $F286) = a separate per-instrument pulse-SPEED
        # array (stride 8, same X). V1 keeps speed in record[6].
        j = first_in(_find_all(d, [0xBD, None, None, 0x8E, None, None,
                                   0x0A, 0x0A, 0x0A, 0xAA]))
        if j is not None and lay.instr:
            for k in range(j, min(j + 0x50, len(d) - 4)):
                if d[k] == 0xBD and d[k + 3] == 0x48:      # LDA abs,X / PHA
                    b = d[k + 1] | (d[k + 2] << 8)
                    if not (lay.instr <= b < lay.instr + 8):
                        lay.pulsespeed_tbl = b
                        break

        # track bit7 TRANSPOSE commands (the later swallow revisions; ROM-verified
        # on Shockway $ED99 / Saboteur_II $F09A / Auf_Wiedersehen $E49D):
        #   LDA (trk),Y / BPL pattern / CMP #$FF / BEQ loop [/ CMP #$FE / BEQ halt]
        # then either  AND #$7F / STA transpose,X          (one-byte: $80|semis)
        # or           INY / LDA (trk),Y -> transpose      (two-byte: $80 nn)
        if any(True for _ in _find_all(d, [0xB1, None, 0x10, None, 0xC9, 0xFF,
                                           0xF0, None, 0x29, 0x7F])) or \
           any(True for _ in _find_all(d, [0xB1, None, 0x10, None, 0xC9, 0xFF,
                                           0xF0, None, 0xC9, 0xFE, 0xF0, None,
                                           0x29, 0x7F])):
            lay.trk_transpose = 1
        elif any(True for _ in _find_all(d, [0xB1, None, 0x10, None, 0xC9, 0xFF,
                                             0xF0, None, 0xC9, 0xFE, 0xF0, None,
                                             0xC8, 0xB1, None])):
            lay.trk_transpose = 2
        return lay

    # ---------------- decode ----------------
    @property
    def resetspd(self):
        return self._u8(self.lay.resetspd_addr) if self.lay.resetspd_addr else 1

    @property
    def frames_per_tick(self):
        """One note-tick every resetspd+1 frames (speed cycles resetspd..0)."""
        return self.resetspd + 1

    def note_freq(self, pitch):
        return self._u16(self.lay.freq + (pitch & 0x7F) * 2)

    def instrument(self, n):
        base = self.lay.instr + (n & 0x1F) * 8
        b = [self._u8(base + k) for k in range(8)]
        speed = b[6]
        if self.lay.pulsespeed_tbl:              # transposed-track revisions keep
            speed = self._u8(self.lay.pulsespeed_tbl + (n & 0x1F) * 8)
        return {"pwlo": b[0], "pwhi": b[1], "ctrl": b[2], "ad": b[3],
                "sr": b[4], "vibdepth": b[5], "pulsespeed": speed, "fx": b[7]}

    def track_ptrs(self, song):
        """The 3 per-voice track pointers for a song. v1: 6-byte record = the
        two 3-byte halves of the init copy (half A feeds the ZP LOW byte).
        v2 (songs_split): separate lo/hi tables indexed song*3+voice."""
        if self.lay.songs_split:
            return [self._u8(self.lay.songs + song * 3 + v)
                    | (self._u8(self.lay.songs_hi + song * 3 + v) << 8)
                    for v in range(3)]
        base = self.lay.songs + song * 6
        return [self._u8(base + v) | (self._u8(base + 3 + v) << 8)
                for v in range(3)]

    def track_patterns(self, song, voice, with_transpose=False):
        """Pattern-number list until $ff (loop) / $fe (halt).
        Returns (patterns, loops); with_transpose=True returns
        ([(pattern, transpose)], loops) instead.

        v2 tracks (Delta class) interleave REPEAT counts: [pat0 (1x),
        cnt1, pat1 (cnt1 x), cnt2, pat2, ...] — the ROM inits the repeat
        counter to 1, plays the pattern at pos, and on expiry reads the
        next byte as the count for the FOLLOWING pattern.

        The later swallow revisions (lay.trk_transpose) use bit7 track
        bytes as TRANSPOSE commands (1 = `$80|semis`, 2 = `$80 nn`),
        applied to following patterns' pitches. Without this they decode
        as pattern numbers 128+ (garbage patterns -> a 10x-long voice)."""
        ptr = self.track_ptrs(song)[voice]
        tmode = getattr(self.lay, 'trk_transpose', 0)
        pats, i, trans = [], 0, 0

        def done(loops):
            return (pats if with_transpose
                    else [p for p, _ in pats]), loops
        if getattr(self.lay, 'v2_notes', False):
            count = 1
            while i < 512:
                b = self._u8(ptr + i)
                if b == 0xFF:
                    return done(True)
                if b == 0xFE:
                    return done(False)
                pats.extend([(b, 0)] * max(1, count))
                i += 1
                nxt = self._u8(ptr + i)
                if nxt in (0xFF, 0xFE):
                    continue
                count = nxt
                i += 1
            return done(False)
        while i < 512:
            b = self._u8(ptr + i)
            if b == 0xFF:
                return done(True)
            if b == 0xFE:
                return done(False)
            if b >= 0x80 and tmode == 1:      # $80|semis -> transpose
                trans = b & 0x7F
                i += 1
                continue
            if b >= 0x80 and tmode == 2:      # $80 nn -> transpose = nn
                trans = self._u8(ptr + i + 1)
                i += 2
                continue
            pats.append((b, trans))
            i += 1
        return done(False)


@dataclass
class HubbardNote:
    ticks: int                # duration in note-ticks (length+1)
    pitch: int = -1           # semitone (-1 for append rows)
    instr: int = -1           # instrument set on this note (-1 = keep)
    porta: int = 0            # signed portamento byte (0 = none)
    append: bool = False      # tie: no re-gate, keeps previous pitch
    no_release: bool = False  # bit5
    no_fetch: bool = False    # v2 pitch bit7: pitch change WITHOUT the
                              #   instrument fetch (no PW/ADSR write, no gate
                              #   edge) — a tie with a pitch update


def decode_pattern(m, pat):
    """Pattern -> [HubbardNote]. Follows getnotedata exactly.

    v2 note format (Delta class, detected via the parser's AND #$60 check):
    len bits5+6 BOTH set = a 1-byte REST/hold note; a NEGATIVE 2nd byte
    (porta) carries an EXTRA parameter byte (4-byte spec — reading it as
    3 bytes desyncs the whole stream); pitch bit7 = NO-FETCH (pitch change
    without re-fetching instrument/PW/ADSR = a tie with a pitch update)."""
    v2 = getattr(m.lay, 'v2_notes', False)
    ptr = m._u8(m.lay.patptl + pat) | (m._u8(m.lay.patpth + pat) << 8)
    out, y, guard = [], 0, 0
    while guard < 1024:
        guard += 1
        b0 = m._u8(ptr + y)
        if b0 == 0xFF:
            break
        length = b0 & 0x1F
        no_rel = bool(b0 & 0x20)
        append = bool(b0 & 0x40)
        if v2 and (b0 & 0x60) == 0x60:
            # 1-byte REST/hold: keeps the current output, no pitch/fetch
            out.append(HubbardNote(ticks=length + 1, append=True,
                                   no_release=True))
            y += 1
            continue
        note = HubbardNote(ticks=length + 1, append=append, no_release=no_rel)
        y += 1
        if append:
            # append consumes ONLY the length byte (getnotedata: bit6 -> skip
            # both the 2nd byte and the pitch, keep current pitch/instr)
            out.append(note)
            continue
        if b0 & 0x80:
            b1 = m._u8(ptr + y)
            y += 1
            if b1 & 0x80:
                note.porta = b1
                if v2:
                    y += 1               # v2 porta: extra parameter byte
            else:
                note.instr = b1
        pb = m._u8(ptr + y)
        if v2 and (pb & 0x80):
            note.no_fetch = True         # pitch change, NO instrument fetch
        note.pitch = pb & 0x7F if v2 else pb
        y += 1
        out.append(note)
    return out


def decode_song(m, song=0, expand_loops=True):
    """Song -> per-voice flat [(tick, HubbardNote)] streams + per-voice total
    ticks. A LOOPING track shorter than the longest voice is repeated to cover
    the full song span (e.g. a short ostinato track against long melody
    tracks — 5_Title_Tunes module 4's V1 is an 18-tick loop)."""
    import dataclasses
    voices, totals, loops = [], [], []
    for v in range(3):
        pats, looped = m.track_patterns(song, v, with_transpose=True)
        tk, evs = 0, []
        for p, trans in pats:
            for n in decode_pattern(m, p):
                if trans and n.pitch >= 0:   # track transpose: shift real notes
                    n = dataclasses.replace(n, pitch=n.pitch + trans)
                evs.append((tk, n))
                tk += n.ticks
        voices.append(evs)
        totals.append(tk)
        loops.append(looped)
    if expand_loops:
        span = max(totals)
        for v in range(3):
            base = list(voices[v])
            period = totals[v]
            if not loops[v] or period <= 0 or period >= span:
                continue
            tk = period
            while tk < span:
                for otk, n in base:
                    if tk + otk >= span:
                        break
                    voices[v].append((tk + otk, n))
                tk += period
            totals[v] = span
    return voices, totals


def initial_instruments(d, la, init_addr, song, lay):
    """Per-voice instrument defaults after INIT (before the first fetch) —
    notes without an instrument byte inherit them (Last_V8's V2 played rom
    instr 3's PW; our decoder assumed 0 -> the HP engine used instr 0's)."""
    if not lay.instrnr_addr:
        return [0, 0, 0]
    from sidm2.cpu6502_emulator import CPU6502Emulator
    cpu = CPU6502Emulator()
    cpu.load_memory(bytes(d), la)
    cpu.mem[0x01] = 0x37
    cpu.reset(init_addr, song & 0xFF, 0, 0)
    for _ in range(1_000_000):
        if not cpu.run_instruction():
            break
    return [cpu.mem[lay.instrnr_addr + v] & 0x1F for v in range(3)]


def swallow_state(d, la, init_addr, song, lay):
    """Post-init value of the v2 fractional-tempo (swallow) counter — the
    schedule's phase: skips land on frames C, C+period, C+2*period, ..."""
    if not lay.swallow_addr:
        return 0
    from py65.devices.mpu6502 import MPU
    mpu = MPU()
    for k, b in enumerate(d):
        mpu.memory[(la + k) & 0xFFFF] = b
    mpu.a, mpu.x, mpu.y = song & 0xFF, 0, 0
    mpu.pc = init_addr
    mpu.memory[0x1FF] = 0xFF
    mpu.memory[0x1FE] = 0xFE
    mpu.sp = 0xFD
    for _ in range(2_000_000):
        if mpu.pc == 0xFFFF:
            break
        mpu.step()
    return mpu.memory[lay.swallow_addr]


def ticks_to_frames(t, fpt, period=0, ctr0=0):
    """Frame index of tick t under the v2 fractional tempo: every `period`
    frames one frame is DEAD (the speed dec is skipped; first dead frame =
    ctr0, the counter's post-init value). period=0 = pure v1 grid."""
    base = t * fpt
    if not period:
        return base
    f = base
    while True:
        dead = 0 if f < ctr0 else (f - ctr0) // period + 1
        f2 = base + dead
        if f2 == f:
            return f
        f = f2


def measure_tick_schedule(d, la, init_addr, play_addr, speed_addr, frames,
                          song=0):
    """GROUND-TRUTH tick grid: replay the ROM and record the frame of every
    tick (= every frame the speed counter RELOADS upward). Immune to tempo-
    mechanism idioms (swallow counters, funktempo, skip gates) — it observes
    the schedule instead of modelling the code. Returns tick_frame where
    tick_frame[t] = frame index of tick t.

    Uses the siddump CPU (raster fake + banking) — some rips' play routines
    crash on a bare py65 (Tarzan needs $D012 to move)."""
    from sidm2.cpu6502_emulator import CPU6502Emulator
    cpu = CPU6502Emulator()
    cpu.load_memory(bytes(d), la)
    cpu.mem[0x01] = 0x37
    cpu.reset(init_addr, song, 0, 0)
    for _ in range(1_000_000):
        if not cpu.run_instruction():
            break

    ticks = []
    prev = cpu.mem[speed_addr]
    for fr in range(frames):
        cpu.mem[0xD012] = (cpu.mem[0xD012] + 1) & 0xFF   # fake raster
        if (cpu.mem[0xD012] == 0
                or ((cpu.mem[0xD011] & 0x80) and cpu.mem[0xD012] >= 0x38)):
            cpu.mem[0xD011] ^= 0x80
            cpu.mem[0xD012] = 0x00
        cpu.reset(play_addr, 0, 0, 0)
        for _ in range(1_000_000):
            if not cpu.run_instruction():
                break
        cur = cpu.mem[speed_addr]
        if cur > prev:            # reload = a tick fired this frame
            ticks.append(fr)
        prev = cur
    return ticks


def detect_module_map(d, la, init_addr, nsongs):
    """Compilation rips: map PSID song index -> embedded module index.

    Each PSID song's INIT pokes a $40 'music on' flag into ITS module's
    variable block (and clears the others'). Replay init per song via py65,
    find the address that is $40 only for that song, and rank it against the
    module songs-copy hits (the flag precedes its module's player code)."""
    from py65.devices.mpu6502 import MPU
    hits = [la + i for i in _find_all(d, SONGS_COPY_SIG)]
    imgs = []
    for s in range(nsongs):
        mpu = MPU()
        for k, b in enumerate(d):
            mpu.memory[(la + k) & 0xFFFF] = b
        mpu.a, mpu.x, mpu.y = s, 0, 0
        mpu.pc = init_addr
        mpu.memory[0x1FF] = 0xFF
        mpu.memory[0x1FE] = 0xFE
        mpu.sp = 0xFD
        for _ in range(2_000_000):
            if mpu.pc == 0xFFFF:
                break
            mpu.step()
        imgs.append(bytes(mpu.memory[la:la + len(d)]))
    mapping = {}
    for s in range(nsongs):
        flags = [la + a for a in range(len(d))
                 if imgs[s][a] == 0x40
                 and all(imgs[t][a] != 0x40 for t in range(nsongs) if t != s)]
        mod = None
        if len(flags) == 1:
            f = flags[0]
            above = [k for k, h in enumerate(hits) if h > f]
            if above:
                mod = above[0]
        mapping[s] = mod if mod is not None else 0
    return mapping
