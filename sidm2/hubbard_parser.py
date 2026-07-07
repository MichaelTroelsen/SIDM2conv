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
    trk_ptr_a: int = 0        # currtrk half A (feeds ZP pointer LOW)
    patptl: int = 0           # pattern pointer table lo
    patpth: int = 0           # pattern pointer table hi
    freq: int = 0             # interleaved lo,hi 16-bit freq table (pitch*2)
    instr: int = 0            # 8-byte instrument records
    speed_addr: int = 0
    resetspd_addr: int = 0
    zp_trk: int = 0           # ZP pair for the track pointer
    zp_pat: int = 0           # ZP pair for the pattern pointer


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
        if not mhits:
            raise ValueError("no Hubbard songs-copy signature")
        if module >= len(mhits):
            raise ValueError(f"module {module} of {len(mhits)}")
        i = mhits[module]
        # Rob's module layout = [play code ... init (songs-copy loop)]: the
        # code signatures PRECEDE their module's songs-copy hit. Window =
        # (previous module's songs-copy, this one]; single-module files use
        # the whole image (some rips rearrange init).
        if len(mhits) == 1:
            w_lo, w_hi = 0, len(d)
        else:
            w_lo = 0 if module == 0 else mhits[module - 1] + 1
            w_hi = i + 1

        def first_in(cands):
            inw = [c for c in cands if w_lo <= c < w_hi]
            return inw[0] if inw else None
        lay.songs = d[i + 1] | (d[i + 2] << 8)
        lay.trk_ptr_a = d[i + 4] | (d[i + 5] << 8)

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

        # freq: ASL / TAY / LDA freq,Y / STA abs / LDA freq+1,Y
        hits = _find_all(d, [0x0A, 0xA8, 0xB9, None, None, 0x8D, None, None,
                             0xB9, None, None])
        cand = []
        for j in hits:
            lo = d[j + 3] | (d[j + 4] << 8)
            hi = d[j + 9] | (d[j + 10] << 8)
            if hi == lo + 1:
                cand.append(j)
        i = first_in(cand)
        if i is None:
            raise ValueError("no Hubbard freq-table signature")
        lay.freq = d[i + 3] | (d[i + 4] << 8)

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
        return {"pwlo": b[0], "pwhi": b[1], "ctrl": b[2], "ad": b[3],
                "sr": b[4], "vibdepth": b[5], "pulsespeed": b[6], "fx": b[7]}

    def track_ptrs(self, song):
        """The 3 per-voice track pointers for a song. The 6-byte record is the
        two 3-byte halves of the init copy: half A feeds the ZP LOW byte."""
        base = self.lay.songs + song * 6
        return [self._u8(base + v) | (self._u8(base + 3 + v) << 8)
                for v in range(3)]

    def track_patterns(self, song, voice):
        """Pattern-number list until $ff (loop) / $fe (halt).
        Returns (patterns, loops)."""
        ptr = self.track_ptrs(song)[voice]
        pats, i = [], 0
        while i < 512:
            b = self._u8(ptr + i)
            if b == 0xFF:
                return pats, True
            if b == 0xFE:
                return pats, False
            pats.append(b)
            i += 1
        return pats, False


@dataclass
class HubbardNote:
    ticks: int                # duration in note-ticks (length+1)
    pitch: int = -1           # semitone (-1 for append rows)
    instr: int = -1           # instrument set on this note (-1 = keep)
    porta: int = 0            # signed portamento byte (0 = none)
    append: bool = False      # tie: no re-gate, keeps previous pitch
    no_release: bool = False  # bit5


def decode_pattern(m, pat):
    """Pattern -> [HubbardNote]. Follows getnotedata exactly."""
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
            else:
                note.instr = b1
        note.pitch = m._u8(ptr + y)
        y += 1
        out.append(note)
    return out


def decode_song(m, song=0, expand_loops=True):
    """Song -> per-voice flat [(tick, HubbardNote)] streams + per-voice total
    ticks. A LOOPING track shorter than the longest voice is repeated to cover
    the full song span (e.g. a short ostinato track against long melody
    tracks — 5_Title_Tunes module 4's V1 is an 18-tick loop)."""
    voices, totals, loops = [], [], []
    for v in range(3):
        pats, looped = m.track_patterns(song, v)
        tk, evs = 0, []
        for p in pats:
            for n in decode_pattern(m, p):
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
