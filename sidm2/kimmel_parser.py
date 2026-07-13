"""Jeroen Kimmel SID player parser (a Rob-Hubbard-*derived* driver).

player-id.exe tags all four files in `SID/Red_kommel_jeroen/` with its own
signature **`Jeroen_Kimmel`** (VGMPF lists Kimmel as one of the scene
musicians who reused/hacked Rob Hubbard's driver — TDZ KB card
`6d4482a66ec4` rob-hubbard). Architecturally it is Hubbard-family (tables
low / play routine / init at the top of the image, self-modifying dispatch,
per-frame FM+pulse effects) but the *code idioms differ enough* that
`sidm2.hubbard_parser` does not decode it (its songs-copy / freq / instr
signatures miss). Hence this dedicated parser.

Engine (reverse-engineered from Think_Twice_V, EMULATION-verified — py65 /
sidm2.cpu6502_emulator — with onset-pitch cross-checked against siddump on
all four corpus files; see docs below):

  Per-voice state has a **7-byte stride** (X = 0, 7, 14 for voices 0/1/2;
  the play loop does `TXA / CLC / ADC #7 / TAX / CPX #$15`).

  Tempo: a global frame counter (`$1044` in TTV) is INC'd every frame; when it
  equals the tempo threshold cell (`$1001`, poked by init) a note-*tick* fires
  (`DEC dur,X`); on the tick the counter resets to 0. So **frames_per_tick =
  the threshold value** (TTV 6, Rhaa 3, Think_Twice_III 5, Radax 5).

  Note fetch (`$11FA`): per voice an **orderlist pointer** (`$101E/$101F,X`,
  copied from the song header at init) walks a list of **direct 2-byte
  pattern pointers** (lo,hi — NOT pattern numbers into a side table like
  Hubbard). An orderlist entry whose HI byte is 0 = loop-to-start; hi == 1 =
  stop (clears the voice-enable mask). Each pattern is a stream of **2-byte
  notes** `[pitch, dur|instr]`, terminated by a pitch byte of 0:
    - byte0 = pitch: a 0-95 index into the SPLIT freq tables (NOT interleaved).
    - byte1: bits0-4 = duration (note lasts dur+1 ticks), bits5-7 = instrument
      number 0-7 (record = `(byte1 & $E0) >> 5`, 8-byte stride).

  Freq tables (`$11E3`): SPLIT — HI table then LO table, each 96 entries,
  indexed by pitch. `freq = lo[pitch] | hi[pitch]<<8`.

  Instrument record (8 bytes, base resolved by init into a ZP pointer):
    [PWhi, wave_ctrl, AD, SR, pulse_speed, freq_slide_off, arp_off, fx]
    wave_ctrl -> $D404 (waveform+gate), AD -> $D405, SR -> $D406,
    PWhi -> $D403. fx byte bits drive the per-frame effects engine ($12CC):
    arpeggio (`arp_off` into a table), freq slide (`slide_off`), pulse-width
    sweep (`pulse_speed`), octave jump + waveform toggles, and drum (noise
    blip on the fetch frame). Effects run EVERY frame; they are Stage-B
    material — Stage A takes only pitch / duration / instrument (AD/SR/wave).

All table addresses are located by RELOCATION-SAFE code signatures (operands),
never hardcoded; the ZP-pointer bases (instrument table, orderlist pointers,
tempo threshold) are resolved by EMULATING init once and reading the runtime
RAM — this also transparently handles Radax's $6000 relocated/self-modifying
init and its multi-subtune dispatch.

Multi-subtune: Radax is a relocating multi-subtune init — subtune 0 runs the
original file image ($6000 tables) while subtunes 1-5 run a copy relocated to
$E000 whose orderlist cells the static file tables never see. KimmelModule
follows the (post-init, per-subtune-patched) play vector to the play core and
locates the ACTIVE tables in the post-init RAM image nearest that core
(``locate_mem``); it falls back to the static file-based ``locate`` when the
memory copy decodes no notes (subtune 0 and every single-subtune tune). So a
plain ``subtune=`` argument now decodes any of Radax's six songs correctly.

Status: DRAFT Stage-A decoder. Onset-pitch medians (siddump ground truth,
25 s window, exact-semitone, best global offset):
  Think_Twice_V   100 / 100 / 100
  Think_Twice_III 100 / 100 / 100
  Rhaa_Lovely_II  100 / 100 / 92.9 (voice 2, n=14 — one effect note)
  Radax sub0      100 / 100 / 100
  Radax sub1      100 / 100 / 100
  Radax sub2      100 / 100 / 100
  Radax sub3      100 /   -  / 90   (voice 1 silent in the real tune, decoded as
                                     rest-as-notes; voice 2 one effect note)
  Radax sub4      100 / 100 / 100
  Radax sub5      100 / 100 / 100
Open items: rest/gate-off notes are played as notes in Stage A (the reason
Radax sub3's runtime-muted voice 1 still decodes notes); the FM/pulse/arp
effects engine ($12CC) is not yet ported (Stage B); orderlist walk stops at the
first loop marker (one pass), not song-length aware for the looping tail.
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
class KimmelLayout:
    freqhi: int = 0        # HI freq table (96 entries, indexed by pitch)
    freqlo: int = 0        # LO freq table
    pitch_var: int = 0     # $101C,X current-pitch state base
    ord_lo: int = 0        # per-voice orderlist pointer LO base ($101E,X)
    ord_hi: int = 0        # per-voice orderlist pointer HI base ($101F,X)
    zp: int = 0            # ZP pair the player builds its pointers in ($FB)
    instr_lo_var: int = 0  # RAM var holding the instrument-table ptr LO ($1059)
    instr_hi_var: int = 0  # RAM var holding the instrument-table ptr HI ($105A)
    tempo_cell: int = 0    # tempo threshold cell ($1001); fpt = mem[cell]
    arp_tbl: int = 0       # arpeggio semitone-offset table ($1176) — 12-entry blocks
    stride: int = 7        # per-voice state stride


# ---- relocation-safe code signatures (operands give the tables) ----
# $11E3 set-freq: TYA / STA pitch,X / LDA freqhi,Y / STA $D401,X /
#                 STA _,X / LDA freqlo,Y / STA $D400,X
_FREQ_SIG = [0x98, 0x9D, None, None, 0xB9, None, None, 0x9D, 0x01, 0xD4,
             0x9D, None, None, 0xB9, None, None, 0x9D, 0x00, 0xD4]
# $11FF note fetch: LDA ordlo,X / STA zp / LDA ordhi,X / STA zp+1
_ORD_SIG = [0xBD, None, None, 0x85, None, 0xBD, None, None, 0x85, None]
# $1261 instrument ptr: LDA instrlo,X / STA zp / LDA instrhi (abs) / STA zp+1
_INSTR_SIG = [0xBD, None, None, 0x85, None, 0xAD, None, None, 0x85, None]
# play tempo compare: CMP tempo / BNE / DEC dur,X
_TEMPO_SIG = [0xCD, None, None, 0xD0, None, 0xDE, None, None]
# $12CC arp step: LDA pitch,X / CLC / ADC arptbl,Y / TAY  ->  arptbl operand
_ARP_SIG = [0xBD, None, None, 0x18, 0x79, None, None, 0xA8]


def locate(d, la):
    """Return a KimmelLayout, or None if the signatures don't match."""
    lay = KimmelLayout()
    hits = _find_all(d, _FREQ_SIG)
    if not hits:
        return None
    i = hits[0]
    lay.freqhi = d[i + 5] | (d[i + 6] << 8)
    lay.freqlo = d[i + 14] | (d[i + 15] << 8)
    lay.pitch_var = d[i + 2] | (d[i + 3] << 8)

    cand = [j for j in _find_all(d, _ORD_SIG)
            if d[j + 7] == d[j + 2] and d[j + 6] == d[j + 1] + 1
            and d[j + 9] == d[j + 4] + 1]
    if not cand:
        return None
    j = cand[0]
    lay.ord_lo = d[j + 1] | (d[j + 2] << 8)
    lay.ord_hi = d[j + 6] | (d[j + 7] << 8)
    lay.zp = d[j + 4]

    cand = [k for k in _find_all(d, _INSTR_SIG)
            if d[k + 4] == lay.zp and d[k + 9] == lay.zp + 1]
    if not cand:
        return None
    k = cand[0]
    lay.instr_lo_var = d[k + 1] | (d[k + 2] << 8)
    lay.instr_hi_var = d[k + 6] | (d[k + 7] << 8)

    for t in _find_all(d, _TEMPO_SIG):
        lay.tempo_cell = d[t + 1] | (d[t + 2] << 8)
        break
    for a in _find_all(d, _ARP_SIG):
        lay.arp_tbl = d[a + 5] | (d[a + 6] << 8)
        break
    return lay


def _find_all_mem(mem, sig, lo=0, hi=0x10000):
    """_find_all over a full 64 KB memory image (post-init RAM)."""
    out, n = [], len(sig)
    for i in range(lo, hi - n):
        if all(s is None or mem[i + k] == s for k, s in enumerate(sig)):
            out.append(i)
    return out


def _play_core(mem, play_addr, span=96):
    """Follow the play vector's JMP wrappers to the first JSR target (the real
    per-frame play core). Radax's per-subtune init patches this vector so the
    core lands in the relocated player copy ($E000 for subtunes 1-5)."""
    a, hops = play_addr, 0
    while a < play_addr + span and hops < 8:
        op = mem[a]
        if op == 0x20:                                  # JSR target = core
            return mem[a + 1] | (mem[a + 2] << 8)
        if op == 0x4C:                                  # JMP wrapper -> follow
            play_addr = mem[a + 1] | (mem[a + 2] << 8)
            a = play_addr
            span += 96
            hops += 1
            continue
        a += 1
    return play_addr


def _nearest(hits, core):
    return min(hits, key=lambda h: abs(h - core)) if hits else None


def locate_mem(mem, core):
    """Locate the ACTIVE player's tables in the post-init memory image, picking
    the signature copy nearest the play core. This follows Radax's relocation
    (subtunes 1-5 run a copy at $E000) where the static file-image tables are
    stale. Returns a KimmelLayout or None."""
    lay = KimmelLayout()
    i = _nearest(_find_all_mem(mem, _FREQ_SIG), core)
    if i is None:
        return None
    lay.freqhi = mem[i + 5] | (mem[i + 6] << 8)
    lay.freqlo = mem[i + 14] | (mem[i + 15] << 8)
    lay.pitch_var = mem[i + 2] | (mem[i + 3] << 8)

    oh = [j for j in _find_all_mem(mem, _ORD_SIG)
          if mem[j + 7] == mem[j + 2] and mem[j + 6] == mem[j + 1] + 1
          and mem[j + 9] == mem[j + 4] + 1]
    j = _nearest(oh, core)
    if j is None:
        return None
    lay.ord_lo = mem[j + 1] | (mem[j + 2] << 8)
    lay.ord_hi = mem[j + 6] | (mem[j + 7] << 8)
    lay.zp = mem[j + 4]

    ih = [k for k in _find_all_mem(mem, _INSTR_SIG)
          if mem[k + 4] == lay.zp and mem[k + 9] == lay.zp + 1]
    k = _nearest(ih, core)
    if k is None:
        return None
    lay.instr_lo_var = mem[k + 1] | (mem[k + 2] << 8)
    lay.instr_hi_var = mem[k + 6] | (mem[k + 7] << 8)

    t = _nearest(_find_all_mem(mem, _TEMPO_SIG), core)
    if t is not None:
        lay.tempo_cell = mem[t + 1] | (mem[t + 2] << 8)
    a = _nearest(_find_all_mem(mem, _ARP_SIG), core)
    if a is not None:
        lay.arp_tbl = mem[a + 5] | (mem[a + 6] << 8)
    return lay


@dataclass
class KimmelEvent:
    frame: int         # onset frame (tick * fpt) BEFORE the init offset
    dur_ticks: int     # note length in ticks
    note: int          # pitch index 0-95 (into the freq tables)
    instr: int         # instrument record number 0-7
    kind: str = "note"


class KimmelModule:
    """Decoded Kimmel module for one subtune.

    Resolves the runtime pointers (instrument base, orderlist pointers, tempo)
    by emulating init once, then statically walks the orderlist/patterns from
    the post-init RAM image (immune to Radax's relocating init)."""

    def __init__(self, path=None, d=None, la=None, init_addr=None,
                 play_addr=None, subtune=0):
        if path is not None:
            d, la, h = load_sid(path)
            init_addr = h.init_address
            play_addr = h.play_address
        self.d, self.la, self.subtune = d, la, subtune
        file_lay = locate(d, la)
        if file_lay is None:
            raise ValueError("not a located Kimmel rip")
        self.mem = self._emulate_init(init_addr, subtune)

        # Pick the ACTIVE layout. Radax is a relocating multi-subtune init:
        # subtune 0 runs the original file image ($6000 tables), subtunes 1-5
        # run a relocated copy ($E000) whose orderlist cells the static file
        # tables never see. Follow the (post-init, per-subtune-patched) play
        # vector to the play core and locate tables nearest it; if that copy
        # decodes no notes (the file image is the live one, e.g. sub 0 / all
        # single-subtune tunes) fall back to the proven file-based layout.
        self.lay = file_lay
        if play_addr is not None:
            core = _play_core(self.mem, play_addr)
            mem_lay = locate_mem(self.mem, core)
            if mem_lay is not None and self._live_note_count(mem_lay) > 0:
                self.lay = mem_lay

        self.fpt = self.mem[self.lay.tempo_cell] if self.lay.tempo_cell else 6
        self.fpt = max(1, self.fpt)
        self.instr_base = (self.mem[self.lay.instr_lo_var]
                           | (self.mem[self.lay.instr_hi_var] << 8))

    def _live_note_count(self, lay, cap=64):
        """Quick liveness probe: total notes the first orderlist entries of all
        three voices yield under `lay`. Used to reject a stale relocated copy."""
        total = 0
        for v in range(3):
            s = lay.stride * v
            optr = (self.mem[(lay.ord_lo + s) & 0xFFFF]
                    | (self.mem[(lay.ord_hi + s) & 0xFFFF] << 8))
            hi = self.mem[(optr + 1) & 0xFFFF]
            if hi <= 1:
                continue
            patptr = self.mem[optr & 0xFFFF] | (hi << 8)
            off = 0
            while off < cap * 2:
                if self.mem[(patptr + off) & 0xFFFF] == 0:
                    break
                total += 1
                off += 2
        return total

    def _emulate_init(self, init_addr, subtune, steps=1_000_000):
        from sidm2.cpu6502_emulator import CPU6502Emulator
        cpu = CPU6502Emulator()
        cpu.load_memory(bytes(self.d), self.la)
        cpu.mem[0x01] = 0x37
        cpu.reset(init_addr, subtune & 0xFF, 0, 0)
        for _ in range(steps):
            if not cpu.run_instruction():
                break
        return cpu.mem

    def note_freq(self, pitch):
        p = pitch & 0x7F
        return self.mem[(self.lay.freqlo + p) & 0xFFFF] \
            | (self.mem[(self.lay.freqhi + p) & 0xFFFF] << 8)

    def voice_instr_base(self, voice):
        """Per-voice instrument-table base. The note-on code builds the pointer
        from ``$1059,X`` (LO, X-indexed per voice) + ``$105A`` (HI, shared), so
        each voice can point at its OWN instrument bank — Radax/TT-III/Rhaa give
        voice 1 a bank $40 bytes (8 records) above voices 0/2. Reading every
        voice from voice 0's bank (the old behaviour) mis-timbres voice 1."""
        lo = self.mem[(self.lay.instr_lo_var + self.lay.stride * voice) & 0xFFFF]
        hi = self.mem[self.lay.instr_hi_var & 0xFFFF]
        return lo | (hi << 8)

    def instrument(self, n, voice=0):
        base = (self.voice_instr_base(voice) + (n & 0x07) * 8) & 0xFFFF
        r = [self.mem[(base + k) & 0xFFFF] for k in range(8)]
        return {"pwhi": r[0], "wave": r[1], "ad": r[2], "sr": r[3],
                "pulse_speed": r[4], "slide": r[5], "arp": r[6], "fx": r[7]}

    def arp_block(self, arp_off):
        """The 12-entry arpeggio block at ``arp_tbl + arp_off``. The $12CC engine
        adds ``block[frame_counter % 12]`` (a semitone offset) to the note's
        pitch index every frame, so a non-zero block IS the chord arpeggio. An
        all-zero block = no arp (a held note)."""
        if not self.lay.arp_tbl:
            return [0] * 12
        base = (self.lay.arp_tbl + (arp_off & 0xFF)) & 0xFFFF
        return [self.mem[(base + i) & 0xFFFF] for i in range(12)]

    def orderlist_ptr(self, voice):
        s = self.lay.stride * voice
        return self.mem[(self.lay.ord_lo + s) & 0xFFFF] \
            | (self.mem[(self.lay.ord_hi + s) & 0xFFFF] << 8)

    def decode_voice(self, voice, guard_max=6000):
        """Walk the orderlist/patterns -> [KimmelEvent] (onset in frames)."""
        optr = self.orderlist_ptr(voice)
        evs, tick, pos, guard = [], 0, 0, 0
        while guard < guard_max:
            guard += 1
            hi = self.mem[(optr + pos * 2 + 1) & 0xFFFF]
            if hi <= 1:                 # 0 = loop, 1 = stop
                break
            lo = self.mem[(optr + pos * 2) & 0xFFFF]
            patptr = lo | (hi << 8)
            off = 0
            while guard < guard_max:
                guard += 1
                pb = self.mem[(patptr + off) & 0xFFFF]
                if pb == 0:             # pitch 0 = end of pattern
                    break
                db = self.mem[(patptr + off + 1) & 0xFFFF]
                dur = (db & 0x1F) + 1
                instr = (db & 0xE0) >> 5
                evs.append(KimmelEvent(frame=tick * self.fpt, dur_ticks=dur,
                                       note=pb, instr=instr))
                tick += dur
                off += 2
            pos += 1
        return evs

    def events(self):
        return [self.decode_voice(v) for v in range(3)]
