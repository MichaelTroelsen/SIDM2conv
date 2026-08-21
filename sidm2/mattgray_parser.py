"""Matt Gray (C64) song extractor.

Reverse-engineered from the player embedded in the Driller SID rip
(load $0900, init $15E0, play $0E46).  Matt Gray wrote this driver from
scratch -- it is *not* derived from Hubbard or Galway -- and refined it
per game, so treat the Driller layout as one confirmed build rather than
a canonical map.

The player is a three-voice pattern interpreter.  `music_play` is a thin
shim that calls one shared `play_voice` routine three times with
X = $00/$07/$0E, so every per-voice state array has a stride of 7 and is
indexed by that X:

    tune            -> per-voice track pointer + tempo
    track           -> a list of pattern numbers  ($ff loop, $fe stop)
    pattern         -> a byte stream of control codes + note rows
    instrument      -> TWO parallel 8-byte records (tables A0 and A1)
    freq table      -> 96-entry lo/hi pair, the player's own (not PAL-generic)

Pattern byte semantics (RE'd from the `read_note_or_ctrl` loop at $09e0 and
confirmed against a siddump of the real rip):

    >= $fd  ($fd/$fe)  -> set duration; next byte is the duration value.
                          Duration is *sticky* -- it applies to every
                          following note until changed.
    $fc                -> slide/portamento type 2; next byte is the rate
    $fb                -> slide/portamento type 1; next byte is the rate
    $fa                -> set instrument;  next byte is the instrument index
    $00                -> REST (note-off): the driver restores the previous
                          note and ANDs the gate bit out of the waveform
    $01-$f9            -> note; index into the 96-entry freq table
    $ff                -> end of pattern (consumed after a note, not here)

Track byte semantics (checked at $0ad6 after each note):

    $ff  -> restart this voice's track at index 0
    $fe  -> stop the tune
    else -> pattern number

Tempo model (confirmed empirically -- onsets land on frames 1, 257, 513 ...
for Driller's opening duration of $3f):

    `tempo_ctr` counts down once per frame and reloads with `tempo` when it
    goes negative, so a row tick happens once every (tempo + 1) frames.
    On each row tick a voice decrements its own duration counter, and fetches
    the next pattern event when that counter goes negative.  A duration byte
    of D therefore holds a note for (D + 1) row ticks.

All table addresses are recovered by *backward dataflow from the code
operands* (every site is an `LDA abs,y` = opcode $b9), never from absolute
addresses, so the parser survives relocation to a different load address.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- code-site offsets from the play_voice base ------------------------------
# Each value is the offset of the 16-bit operand; the byte before it must be
# $b9 (LDA abs,y).  Verified against the Driller rip, where play_voice = $0900.
_SITE_V1_TRK_LO = 0x0075   # $0974: lda voice1_tune_trackptr_lo,y
_SITE_V1_TRK_HI = 0x007B   # $097a
_SITE_V2_TRK_LO = 0x0081   # $0980
_SITE_V2_TRK_HI = 0x0087   # $0986
_SITE_V3_TRK_LO = 0x008D   # $098c
_SITE_V3_TRK_HI = 0x0093   # $0992
_SITE_TEMPO     = 0x0099   # $0998: lda tune_tempo,y
_SITE_PAT_LO    = 0x00C7   # $09c6: lda pattern_lobytes,y
_SITE_PAT_HI    = 0x00CC   # $09cb: lda pattern_hibytes,y
_SITE_INSTR_A0  = 0x012D   # $0a2c: lda instr_a0,y
_SITE_FRQ_HI    = 0x018D   # $0a8c: lda frq_hi,y
_SITE_FRQ_LO    = 0x0199   # $0a98: lda frq_lo,y
_SITE_INSTR_A1_4 = 0x020A  # $0b09: lda instr_a1+4,y   (so A1 = operand - 4)
_SITE_ARP_TABLE = 0x028D   # $0b8c: lda arpeggio_table,y

_ALL_SITES = (
    _SITE_V1_TRK_LO, _SITE_V1_TRK_HI, _SITE_V2_TRK_LO, _SITE_V2_TRK_HI,
    _SITE_V3_TRK_LO, _SITE_V3_TRK_HI, _SITE_TEMPO, _SITE_PAT_LO, _SITE_PAT_HI,
    _SITE_INSTR_A0, _SITE_FRQ_HI, _SITE_FRQ_LO, _SITE_INSTR_A1_4,
    _SITE_ARP_TABLE,
)

NUM_NOTES = 96          # freq table entries
INSTR_SIZE = 8          # bytes per record, in each of the two parallel tables
VOICE_X = (0x00, 0x07, 0x0E)   # the X values music_play passes to play_voice

# pattern control codes
PC_PARAM = 0xF9         # LN2 only: 2-byte code, stores a per-note parameter
PC_INSTR = 0xFA
PC_SLIDE1 = 0xFB
PC_SLIDE2 = 0xFC
PC_DUR = 0xFD           # $fd and $fe both take this path (>= $fd)
PC_PAT_END = 0xFF
TRK_LOOP = 0xFF
TRK_STOP = 0xFE
NOTE_REST = 0x00


class MattGrayError(Exception):
    """Raised when a file does not look like a Matt Gray player."""


@dataclass
class MattGrayInstrument:
    """One instrument: the two parallel 8-byte records, A0 and A1.

    Field names follow what the driver actually *does* with each byte; the
    ones still unconfirmed keep a neutral name rather than a guessed one.
    """
    index: int
    a0: List[int]
    a1: List[int]

    # --- table A0 (the byte offsets the driver reads) ---
    @property
    def pulse(self) -> int:
        """A0[0]: hi nibble -> $d402, lo nibble -> $d403 (12-bit pulse width)."""
        return self.a0[0]

    @property
    def pulse_width(self) -> int:
        """The 12-bit pulse value the driver actually programs."""
        return ((self.a0[0] & 0x0F) << 8) | (self.a0[0] & 0xF0)

    @property
    def waveform(self) -> int:
        """A0[1]: sustained waveform, ANDed with the gate mask -> $d404."""
        return self.a0[1]

    @property
    def ad(self) -> int:
        """A0[2] -> $d405 attack/decay."""
        return self.a0[2]

    @property
    def sr(self) -> int:
        """A0[3] -> $d406 sustain/release."""
        return self.a0[3]

    @property
    def pulse_sweep(self) -> int:
        """A0[4]: per-frame pulse-width delta (0 = no PWM)."""
        return self.a0[4]

    @property
    def arp_ctrl(self) -> int:
        """A0[5]: nonzero enables the arpeggio path.

        lo nibble = arpeggio-table index, hi nibble = arpeggio length.
        """
        return self.a0[5]

    @property
    def attack_waveform(self) -> int:
        """A0[6]: waveform written on the note-attack frame."""
        return self.a0[6]

    @property
    def flags(self) -> int:
        """A0[7]: bit0 = drum/effect path, bit1 = pulse reset on note,
        bit2 = two-frame attack-waveform swap."""
        return self.a0[7]

    # --- table A1 ---
    @property
    def slide_rate(self) -> int:
        """A1[0]: nonzero enables the automatic pitch slide."""
        return self.a1[0]

    @property
    def slide_period(self) -> int:
        """A1[1]: slide step reload period."""
        return self.a1[1]

    @property
    def alt_waveform(self) -> int:
        """A1[2]: waveform used by the two-frame swap and the drum path."""
        return self.a1[2]

    @property
    def auto_effect_rate(self) -> int:
        """A1[3]: rate used when A1[4] auto-starts an effect."""
        return self.a1[3]

    @property
    def auto_effect(self) -> int:
        """A1[4]: nonzero auto-starts slide effect type N on every note."""
        return self.a1[4]

    @property
    def drum_len(self) -> int:
        """A1[5]: drum/effect repeat length (compared against a counter)."""
        return self.a1[5]

    @property
    def raw(self) -> List[int]:
        return list(self.a0) + list(self.a1)


@dataclass
class MattGrayNote:
    """One decoded note event from the sequencer simulation."""
    frame: int          # frame the driver writes the note on
    tick: int           # row tick index (frame = first_tick + tick*(tempo+1))
    voice: int          # 0..2
    note: int           # freq-table index; 0 = rest / note-off
    instrument: int     # instrument index in effect
    duration: int       # duration byte in effect (holds duration+1 ticks)
    track_index: int
    pattern: int
    # A $fb/$fc slide command consumed during THIS note's fetch, as
    # (type, rate) with type 1 = $fb, 2 = $fc; None if the note is unslid.
    # The driver clears the effect slot at the top of every fetch (L09b6), so
    # a slide only ever applies to the note that immediately follows it.
    slide: Optional[Tuple[int, int]] = None

    @property
    def is_rest(self) -> bool:
        return self.note == NOTE_REST


@dataclass
class MattGraySong:
    """A parsed Matt Gray tune."""
    load_addr: int
    init_addr: int
    play_addr: int
    play_voice: int
    subtune: int
    tempo: int
    tracks: List[List[int]] = field(default_factory=list)         # per voice
    patterns: List[List[int]] = field(default_factory=list)
    pattern_addrs: List[int] = field(default_factory=list)
    instruments: List[MattGrayInstrument] = field(default_factory=list)
    freq_lo: List[int] = field(default_factory=list)
    freq_hi: List[int] = field(default_factory=list)
    arp_table_addr: int = 0
    table_addrs: Dict[str, int] = field(default_factory=dict)
    layout: str = "unknown"
    # Duration encoding. None = Driller style ($fd nn, a two-byte code).
    # An int D = Last Ninja 2 style: a pattern byte >= D IS the duration,
    # value (byte - D), sticky; only bytes < D are notes.
    duration_base: Optional[int] = None
    truncated_patterns: int = 0   # patterns cut short by the relocating copy   # 'driller' = validated fast path, 'signature' = located but UNVALIDATED
    # The PSID song index for this subtune -- what siddump's `-a` wants.
    # NOT the same number as `subtune`: `subtune` indexes the track-pointer
    # TABLE, whose entry 0 is null on most builds, while `-a` counts the songs
    # that actually exist from 0. Passing `subtune` straight to siddump traces
    # the WRONG TUNE on every such file (see docs/players/MATTGRAY.md).
    psid_song: int = 0

    @property
    def frames_per_tick(self) -> int:
        """A row tick happens once every (tempo + 1) frames."""
        return self.tempo + 1

    def freq(self, note: int) -> int:
        """The 16-bit SID frequency the player programs for a note index."""
        if not 0 <= note < len(self.freq_lo):
            return 0
        return self.freq_lo[note] | (self.freq_hi[note] << 8)


def _u16(buf: bytes, off: int) -> int:
    return buf[off] | (buf[off + 1] << 8)


# --- 6502 instruction lengths, legal opcodes only (0 = illegal/undefined) ----
# Built from the standard opcode matrix.  Illegal opcodes are 0 so the code
# walk STOPS there rather than silently mis-aligning, which is the classic way
# a linear disassembler wanders into a data table and invents instructions.
def _build_oplen() -> List[int]:
    L = [0] * 256
    for op, n in {
        0x00: 1, 0x08: 1, 0x0A: 1, 0x18: 1, 0x28: 1, 0x2A: 1, 0x38: 1,
        0x40: 1, 0x48: 1, 0x4A: 1, 0x58: 1, 0x60: 1, 0x68: 1, 0x6A: 1,
        0x78: 1, 0x88: 1, 0x8A: 1, 0x98: 1, 0x9A: 1, 0xA8: 1, 0xAA: 1,
        0xB8: 1, 0xBA: 1, 0xC8: 1, 0xCA: 1, 0xD8: 1, 0xE8: 1, 0xEA: 1,
        0xF8: 1,
    }.items():
        L[op] = n
    # 2-byte: immediate, zp, zp,x, zp,y, (zp,x), (zp),y, relative
    for op in (0x01, 0x05, 0x06, 0x09, 0x11, 0x15, 0x16, 0x21, 0x24, 0x25,
               0x26, 0x29, 0x31, 0x35, 0x36, 0x41, 0x45, 0x46, 0x49, 0x51,
               0x55, 0x56, 0x61, 0x65, 0x66, 0x69, 0x71, 0x75, 0x76, 0x81,
               0x84, 0x85, 0x86, 0x91, 0x94, 0x95, 0x96, 0xA0, 0xA1, 0xA2,
               0xA4, 0xA5, 0xA6, 0xA9, 0xB1, 0xB4, 0xB5, 0xB6, 0xC0, 0xC1,
               0xC4, 0xC5, 0xC6, 0xC9, 0xD1, 0xD5, 0xD6, 0xE0, 0xE1, 0xE4,
               0xE5, 0xE6, 0xE9, 0xF1, 0xF5, 0xF6,
               0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0):
        L[op] = 2
    # 3-byte: absolute, abs,x, abs,y, indirect
    for op in (0x0D, 0x0E, 0x19, 0x1D, 0x1E, 0x20, 0x2C, 0x2D, 0x2E, 0x39,
               0x3D, 0x3E, 0x4C, 0x4D, 0x4E, 0x59, 0x5D, 0x5E, 0x6C, 0x6D,
               0x6E, 0x79, 0x7D, 0x7E, 0x8C, 0x8D, 0x8E, 0x99, 0x9D, 0xAC,
               0xAD, 0xAE, 0xB9, 0xBC, 0xBD, 0xBE, 0xCC, 0xCD, 0xCE, 0xD9,
               0xDD, 0xDE, 0xEC, 0xED, 0xEE, 0xF9, 0xFD, 0xFE):
        L[op] = 3
    return L


_OPLEN = _build_oplen()
_BRANCHES = {0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0}
_STOP = {0x40, 0x60, 0x6C, 0x4C}        # RTI, RTS, JMP (ind), JMP abs
_JMP_ABS, _JSR = 0x4C, 0x20


def _cluster(values: List[int], gap: int) -> List[List[int]]:
    """Group a sorted list into runs whose neighbours are <= `gap` apart."""
    out: List[List[int]] = []
    for v in values:
        if out and v - out[-1][-1] <= gap:
            out[-1].append(v)
        else:
            out.append([v])
    return out


class MattGrayParser:
    """Locate and decode a Matt Gray player inside a PSID/PRG image."""

    def __init__(self, data: bytes, load_addr: int, init_addr: int,
                 play_addr: int) -> None:
        self.layout = "unknown"
        self.truncated_patterns = 0
        self.data = data
        self.load = load_addr
        self.init = init_addr
        self.play = play_addr
        self.play_voice = self._find_play_voice()

    # --- memory helpers ------------------------------------------------
    def _off(self, addr: int) -> int:
        off = addr - self.load
        if not 0 <= off < len(self.data):
            raise MattGrayError(
                f"address ${addr:04x} outside image "
                f"${self.load:04x}-${self.load + len(self.data) - 1:04x}")
        return off

    def byte(self, addr: int) -> int:
        return self.data[self._off(addr)]

    def word(self, addr: int) -> int:
        return _u16(self.data, self._off(addr))

    def slice(self, addr: int, n: int) -> bytes:
        o = self._off(addr)
        return self.data[o:o + n]

    # --- location ------------------------------------------------------
    def _find_play_voice(self) -> int:
        """`music_play` is `ldx #$00 / jsr play_voice / ldx #$07 / jsr ... `.

        Read the JSR operand rather than assuming play_voice sits at the
        load address -- that only happens to be true for the Driller rip.
        """
        try:
            head = self.slice(self.play, 16)
        except MattGrayError as exc:
            raise MattGrayError(f"play address unreadable: {exc}") from exc
        if len(head) < 5 or head[0] != 0xA2 or head[2] != 0x20:
            # Some builds put a trampoline at the PSID play address (Quedex:
            # `lda flag / bne`; Deliverance: `jsr ...`).  Scan the image for
            # the shim's unmistakable 15-byte body instead of giving up:
            # ldx #$00 / jsr pv / ldx #$07 / jsr pv / ldx #$0e / jsr pv.
            found = self._scan_for_shim()
            if found is not None:
                return found
            raise MattGrayError(
                f"play $%04x is not a Matt Gray music_play shim "
                f"(got {head[:5].hex(' ')}, expected 'a2 00 20 lo hi')"
                % self.play)
        pv = head[3] | (head[4] << 8)
        # the shim must call the same routine three times, with X = 0/7/14
        for i, x in enumerate(VOICE_X):
            base = i * 5
            if head[base] != 0xA2 or head[base + 1] != x:
                raise MattGrayError(
                    f"music_play voice {i} does not load X=${x:02x}")
            if head[base + 2] != 0x20 or (head[base + 3] | (head[base + 4] << 8)) != pv:
                raise MattGrayError(
                    f"music_play voice {i} does not jsr ${pv:04x}")
        return pv

    def _scan_for_shim(self) -> Optional[int]:
        """Find `ldx #$00/$07/$0e / jsr pv` x3 anywhere in the image."""
        d = self.data
        for i in range(len(d) - 15):
            if d[i] != 0xA2 or d[i + 1] != 0x00 or d[i + 2] != 0x20:
                continue
            pv = d[i + 3] | (d[i + 4] << 8)
            if all(d[i + k * 5] == 0xA2 and d[i + k * 5 + 1] == x
                   and d[i + k * 5 + 2] == 0x20
                   and (d[i + k * 5 + 3] | (d[i + k * 5 + 4] << 8)) == pv
                   for k, x in enumerate(VOICE_X)):
                return pv
        return None

    def _site(self, off: int, what: str) -> int:
        """Read a table address from an `LDA abs,y` operand at play_voice+off."""
        addr = self.play_voice + off
        opcode = self.byte(addr - 1)
        if opcode != 0xB9:
            raise MattGrayError(
                f"{what}: expected LDA abs,y ($b9) at ${addr - 1:04x}, "
                f"got ${opcode:02x} -- not a known Matt Gray build")
        return self.word(addr)

    def verify(self) -> None:
        """Check every code site looks like the expected instruction."""
        for off in _ALL_SITES:
            if self.byte(self.play_voice + off - 1) != 0xB9:
                raise MattGrayError(
                    f"code site +${off:04x} is not LDA abs,y -- "
                    f"unsupported Matt Gray variant")

    # --- variant-tolerant location -------------------------------------
    def _code_map(self, roots: Optional[List[int]] = None) -> List[int]:
        """Recursive-descent walk from the entry points -> sorted instruction
        addresses.

        A flat byte scan is NOT good enough here: the player interleaves code
        and data (Driller's per-voice state arrays sit at $0cce, right in the
        middle of the play_voice code region), so a linear sweep wanders into a
        table and invents instructions from data bytes.  Following branches and
        stopping at RTS/JMP/illegal opcodes keeps the map to real code.
        """
        lo_addr = self.load
        hi_addr = self.load + len(self.data)

        def inside(a: int) -> bool:
            return lo_addr <= a < hi_addr

        roots = roots or [self.play_voice, self.play]
        seen: set = set()
        queue = [r for r in roots if r and inside(r)]
        while queue:
            pc = queue.pop()
            while inside(pc) and pc not in seen:
                op = self.data[pc - lo_addr]
                n = _OPLEN[op]
                if n == 0 or not inside(pc + n - 1):   # illegal -> not code
                    break
                seen.add(pc)
                if op in _BRANCHES:
                    rel = self.data[pc + 1 - lo_addr]
                    tgt = pc + 2 + (rel - 256 if rel > 127 else rel)
                    if inside(tgt):
                        queue.append(tgt)
                elif op in (_JSR, _JMP_ABS):
                    tgt = _u16(self.data, pc + 1 - lo_addr)
                    if inside(tgt):
                        queue.append(tgt)
                    if op == _JMP_ABS:
                        break
                elif op in _STOP:
                    break
                pc += n
        return sorted(seen)

    def _b9_sites(self) -> List[Tuple[int, int]]:
        """Every real `LDA abs,y` instruction, as (address, operand).

        Matt Gray refined the driver per game, so the *offsets* of these sites
        move between builds (Driller 1987 and Last Ninja 2 1988 share only the
        play_voice prologue).  The set of tables does not move, so locate by
        the shape of the site list rather than by fixed offsets.
        """
        return [(pc, self.word(pc + 1))
                for pc in self._code_map() if self.byte(pc) == 0xB9]

    def locate(self) -> Dict[str, int]:
        """Find every table by signature.  Raises if any is not identifiable."""
        sites = self._b9_sites()
        ops = [a for _, a in sites]
        found: Dict[str, int] = {}

        # 6 consecutive sites whose operands step by a CONSTANT: the per-voice
        # track pointer lo/hi tables (v1lo v1hi v2lo v2hi v3lo v3hi).
        #
        # The stride was hard-coded to 2, which is Last Ninja 2's and Tusker's.
        # It is not universal -- the same six-table shape appears at stride 3
        # (Pogo_Stick_Olympics), 4 (Hyperion_2), 5 (KGB_Superspy, Motocross)
        # and 6 (Maze_Mania), and hard-coding 2 refused all of them. Requiring
        # the step to be CONSTANT is what identifies the tables; its particular
        # value is a per-build layout detail, exactly like the site offsets the
        # comment above already says move between builds.
        for i in range(len(sites) - 6):
            win = [sites[i + k][1] for k in range(6)]
            step = win[1] - win[0]
            if step <= 0 or step > 64:
                continue          # descending or absurd: not a table row group
            if all(win[k + 1] - win[k] == step for k in range(5)):
                found["trk_v1_lo"], found["trk_v1_hi"] = win[0], win[1]
                found["trk_v2_lo"], found["trk_v2_hi"] = win[2], win[3]
                found["trk_v3_lo"], found["trk_v3_hi"] = win[4], win[5]
                # tune_tempo is the next distinct table referenced after them
                # -- but it is chosen AFTER the pattern table, not here. On
                # Pogo_Stick_Olympics and Warriors the very next distinct site
                # IS the pattern lo-table, so picking tempo first claimed it and
                # left the pattern search nothing but an arpeggio-style pair one
                # byte wide, which read as a one-pattern song.
                tempo_scan = (i + 6, win)
                break
        if "trk_v1_lo" not in found:
            raise MattGrayError("could not locate the track-pointer tables")

        # freq lo/hi: a pair of operands exactly NUM_NOTES apart, confirmed by
        # a 12-semitone octave rollover in the candidate hi table.
        for lo in ops:
            hi = lo + NUM_NOTES
            if hi in ops and self._looks_like_freq_table(lo, hi):
                found["frq_lo"], found["frq_hi"] = lo, hi
                break
        if "frq_lo" not in found:
            raise MattGrayError("could not locate the frequency table")

        # instruments: the driver reads many fields of one record, so each
        # table shows up as a CLUSTER of operands within 8 bytes of its base.
        # Two such clusters whose bases differ by a multiple of 8 are A0/A1.
        clusters = _cluster(sorted(set(ops)), gap=8)
        cands = [c[0] for c in clusters if len(c) >= 3]
        pair = None
        for i, a0 in enumerate(cands):
            for a1 in cands[i + 1:]:
                d = a1 - a0
                if d > 0 and d % INSTR_SIZE == 0 and d // INSTR_SIZE <= 64:
                    pair = (a0, a1)
                    break
            if pair:
                break
        if not pair:
            raise MattGrayError("could not locate the instrument tables")
        found["instr_a0"], found["instr_a1"] = pair

        # pattern lo/hi pointer tables, located LAST and only from operands no
        # other table has claimed.  Done earlier it reliably mis-fires: two
        # adjacent *instrument field* reads (LN2's $461a / $4620, six apart)
        # look exactly like a lo/hi pointer pair with a six-pattern song.
        n_instr = max(1, (found["instr_a1"] - found["instr_a0"]) // INSTR_SIZE)
        claimed = [
            (found["instr_a0"], found["instr_a0"] + n_instr * INSTR_SIZE),
            (found["instr_a1"], found["instr_a1"] + n_instr * INSTR_SIZE),
            (found["frq_lo"], found["frq_lo"] + NUM_NOTES),
            (found["frq_hi"], found["frq_hi"] + NUM_NOTES),
            (found["trk_v1_lo"], found["trk_v3_hi"] + 2),
        ]

        def free(a: int) -> bool:
            return not any(s <= a < e for s, e in claimed)

        # TAKE THE WIDEST PAIR, not the first. `a2 - a1` IS the pattern count
        # (the lo-table is immediately followed by the hi-table), so a pair one
        # byte apart claims a one-pattern song -- which is what Pogo and
        # Warriors got, while their tracks referenced 22 and 23. Every file that
        # already decoded picks the SAME table under this rule, because the real
        # pattern table is the widest candidate in all nine of them; the narrow
        # runners-up are arpeggio-style lo/hi pointer pairs (distance 1-3).
        cands = [(a1, a2) for (o1, a1), (o2, a2) in zip(sites, sites[1:])
                 if 0 < o2 - o1 <= 8 and 0 < a2 - a1 < 256
                 and free(a1) and free(a2)]
        if not cands:
            raise MattGrayError("could not locate the pattern pointer tables")
        found["pattern_lobytes"], found["pattern_hibytes"] = max(
            cands, key=lambda c: c[1] - c[0])

        # arpeggio table: a pair of sites one byte apart (lo/hi of a pointer)
        for (_o1, a1), (_o2, a2) in zip(sites, sites[1:]):
            if a2 - a1 == 1 and free(a1):
                found["arpeggio_table"] = a1
                break
        found.setdefault("arpeggio_table", 0)

        # tempo, NOW that the pattern table is known: the next distinct site
        # after the track group that is not inside the pattern table itself.
        pat_lo = found["pattern_lobytes"]
        pat_end = found["pattern_hibytes"] + (found["pattern_hibytes"] - pat_lo)
        j0, win = tempo_scan
        for j in range(j0, len(sites)):
            a = sites[j][1]
            # It must be free of EVERY table already placed, not just the
            # pattern one. Without the `free(a)` test it landed on `instr_a0`
            # for Pogo_Stick_Olympics and Warriors and read a tempo of 129 --
            # 130 frames per tick, a row every 2.6 seconds, where every file
            # that decodes reads 2-5. A silently wrong tempo is worse than a
            # refusal: it makes every note in the song land at the wrong time
            # while the decode still looks like it worked.
            arp = found.get("arpeggio_table") or 0
            if (a not in win and not (pat_lo <= a < pat_end) and free(a)
                    and not (arp and a in (arp, arp + 1))):
                found["tune_tempo"] = a
                break
        if "tune_tempo" not in found:
            raise MattGrayError(
                "could not locate the tempo table: every indexed-read site is "
                "claimed by another table, and the only free pair is the "
                "arpeggio pointer table (pattern table at $%04x/%d located "
                "OK)" % (pat_lo, found["pattern_hibytes"] - pat_lo))

        return found

    def _duration_base(self) -> Optional[int]:
        """Find the LN2-style duration split, if this build uses one.

        The idiom is unmistakable and is emitted right where the note byte is
        classified:  cmp #N / bcc note / sbc #N / sta duration.  Driller has no
        such split -- it spends a whole $fd control code on duration instead.
        """
        for pc in self._code_map():
            if self.byte(pc) != 0xC9:
                continue
            n = self.byte(pc + 1)
            if not 0x40 <= n <= 0xF0:
                continue
            if self.byte(pc + 2) in (0x90, 0xB0) and self.byte(pc + 4) == 0xE9                     and self.byte(pc + 5) == n:
                return n
        return None

    def _looks_like_freq_table(self, lo: int, hi: int) -> bool:
        """A real freq table's hi bytes rise and roughly double each octave."""
        try:
            h = self.slice(hi, NUM_NOTES)
        except MattGrayError:
            return False
        if len(h) < NUM_NOTES or not all(h[i] <= h[i + 1] for i in range(len(h) - 1)):
            return False
        # an octave up doubles the frequency; check a few octave pairs
        good = 0
        for n in range(0, NUM_NOTES - 12, 12):
            a, b = h[n], h[n + 12]
            if a and abs(b - 2 * a) <= 2:
                good += 1
        return good >= 4

    # --- decode --------------------------------------------------------
    def parse(self, subtune: int = 1) -> MattGraySong:
        # Fast path: the exact Driller-era layout, where every table sits at a
        # known offset.  Otherwise fall back to locating by signature, which
        # also handles the restructured Last Ninja 2 (1988) build.
        try:
            self.verify()
            tabs = {
                "pattern_lobytes": self._site(_SITE_PAT_LO, "pattern_lobytes"),
                "pattern_hibytes": self._site(_SITE_PAT_HI, "pattern_hibytes"),
                "instr_a0": self._site(_SITE_INSTR_A0, "instr_A0"),
                "instr_a1": self._site(_SITE_INSTR_A1_4, "instr_A1") - 4,
                "frq_lo": self._site(_SITE_FRQ_LO, "frq_lo"),
                "frq_hi": self._site(_SITE_FRQ_HI, "frq_hi"),
                "tune_tempo": self._site(_SITE_TEMPO, "tune_tempo"),
                "arpeggio_table": self._site(_SITE_ARP_TABLE, "arpeggio_table"),
                "trk_v1_lo": self._site(_SITE_V1_TRK_LO, "trackptr_lo"),
                "trk_v1_hi": self._site(_SITE_V1_TRK_HI, "trackptr_hi"),
                "trk_v2_lo": self._site(_SITE_V2_TRK_LO, "trackptr_lo"),
                "trk_v2_hi": self._site(_SITE_V2_TRK_HI, "trackptr_hi"),
                "trk_v3_lo": self._site(_SITE_V3_TRK_LO, "trackptr_lo"),
                "trk_v3_hi": self._site(_SITE_V3_TRK_HI, "trackptr_hi"),
            }
            self.layout = "driller"
        except MattGrayError:
            tabs = self.locate()
            self.layout = "signature"

        pat_lo, pat_hi = tabs["pattern_lobytes"], tabs["pattern_hibytes"]
        instr_a0, instr_a1 = tabs["instr_a0"], tabs["instr_a1"]
        frq_lo, frq_hi = tabs["frq_lo"], tabs["frq_hi"]
        tempo_tab, arp_tab = tabs["tune_tempo"], tabs["arpeggio_table"]
        trk_tabs = [(tabs["trk_v1_lo"], tabs["trk_v1_hi"]),
                    (tabs["trk_v2_lo"], tabs["trk_v2_hi"]),
                    (tabs["trk_v3_lo"], tabs["trk_v3_hi"])]

        # The lo-table is immediately followed by the hi-table, so their
        # distance is the number of tunes.  Same trick for the pattern table.
        n_tunes = trk_tabs[0][1] - trk_tabs[0][0]
        if n_tunes <= 0:
            raise MattGrayError("could not size the tune table")
        if not 0 <= subtune < n_tunes:
            raise MattGrayError(
                f"subtune {subtune} out of range (file has {n_tunes})")

        n_patterns = pat_hi - pat_lo
        if n_patterns <= 0:
            raise MattGrayError("could not size the pattern table")
        n_instr = max(0, (instr_a1 - instr_a0) // INSTR_SIZE)
        if n_instr <= 0:
            raise MattGrayError("could not size the instrument table")

        # --- the PSID song index for this subtune.
        # An entry whose voice-1 pointer is null/out-of-image is not a tune --
        # `subtune` indexes the TABLE, siddump's `-a` indexes the tunes that
        # exist. The k-th valid entry is song k, which is right whether the
        # table starts at 0 (Last Ninja 2, Tusker) or at 1 (every other build
        # located so far). Derived, not assumed to be an offset of one:
        # `Driller` declares 2 songs for 1 valid entry, so a blind -1 is wrong.
        lo0, hi0 = trk_tabs[0]
        psid_song = 0
        for k in range(subtune):
            b = self.byte(lo0 + k) | (self.byte(hi0 + k) << 8)
            if b and self.load <= b < self.load + len(self.data):
                psid_song += 1

        # --- tracks (orderlists), one per voice
        tracks: List[List[int]] = []
        for lo_tab, hi_tab in trk_tabs:
            base = self.byte(lo_tab + subtune) | (self.byte(hi_tab + subtune) << 8)
            tracks.append(self._read_track(base))

        # --- patterns
        pattern_addrs = [self.byte(pat_lo + i) | (self.byte(pat_hi + i) << 8)
                         for i in range(n_patterns)]
        # THE TRACKS KNOW HOW MANY PATTERNS THERE ARE, so ask them before
        # decoding one. On `Pogo_Stick_Olympics` and `Warriors` the table is
        # mis-located: it declares ONE pattern whose address lands in the
        # player's own code ($1517 is ten bytes ahead of Pogo's play routine at
        # $1557, and reads `a0 18 a9 00 99 18 d4 88 d0 fa 60` -- the clear-SID
        # loop), while the tracks reference 15+. Without this the failure
        # surfaced 512 bytes later as "pattern at $1517 has no $ff terminator",
        # which accuses the WALK of a locate bug and sends the reader to the
        # wrong file. The invariant is exact on every rip that decodes: across
        # all 26 (file, subtune) pairs the highest track reference is always
        # < n_patterns, and usually == n_patterns - 1.
        # A SINGLE out-of-range reference is LEGAL and must not refuse: the
        # sequencer itself treats `pat_no >= len(patterns)` as end-of-track
        # (`st.stopped = True`), and a real rip in the test corpus carries a
        # lone $fd in a track. What is not legal is a table so small that most
        # of the song cannot be reached -- so require a MAJORITY of the distinct
        # references to be unreachable before calling the locate wrong.
        refs = {b for t in tracks for b in t if b < TRK_STOP}
        oor = {b for b in refs if b >= n_patterns}
        if refs and len(oor) * 2 > len(refs):
            raise MattGrayError(
                f"pattern table mis-located: {len(oor)} of {len(refs)} distinct "
                f"track references are unreachable (highest {max(oor)}) but the "
                f"table at ${pat_lo:04x}/${pat_hi:04x} declares only "
                f"{n_patterns} (first entry ${pattern_addrs[0]:04x})")
        patterns = [self._read_pattern(a) for a in pattern_addrs]

        # --- instruments
        instruments = [
            MattGrayInstrument(
                index=i,
                a0=list(self.slice(instr_a0 + i * INSTR_SIZE, INSTR_SIZE)),
                a1=list(self.slice(instr_a1 + i * INSTR_SIZE, INSTR_SIZE)),
            )
            for i in range(n_instr)
        ]

        song = MattGraySong(
            load_addr=self.load,
            init_addr=self.init,
            play_addr=self.play,
            play_voice=self.play_voice,
            subtune=subtune,
            psid_song=psid_song,
            tempo=self.byte(tempo_tab + subtune),
            tracks=tracks,
            patterns=patterns,
            pattern_addrs=pattern_addrs,
            instruments=instruments,
            freq_lo=list(self.slice(frq_lo, NUM_NOTES)),
            freq_hi=list(self.slice(frq_hi, NUM_NOTES)),
            arp_table_addr=arp_tab,
            table_addrs={
                "play_voice": self.play_voice,
                "pattern_lobytes": pat_lo, "pattern_hibytes": pat_hi,
                "instr_a0": instr_a0, "instr_a1": instr_a1,
                "frq_lo": frq_lo, "frq_hi": frq_hi,
                "tune_tempo": tempo_tab, "arpeggio_table": arp_tab,
            },
        )
        song.layout = self.layout
        song.duration_base = self._duration_base()
        song.truncated_patterns = self.truncated_patterns
        return song

    def _read_track(self, base: int, cap: int = 512) -> List[int]:
        out: List[int] = []
        for i in range(cap):
            b = self.byte(base + i)
            out.append(b)
            if b in (TRK_LOOP, TRK_STOP):
                return out
        raise MattGrayError(f"track at ${base:04x} has no $ff/$fe terminator")

    def _read_pattern(self, base: int, cap: int = 512) -> List[int]:
        """Decode one pattern.  Runs are terminated by $ff.

        A pattern that runs off the end of the image is returned truncated
        rather than raising.  Last Ninja 2's relocating wrapper genuinely
        copies less than the full data block for some subtunes (subtune 7's
        final pattern ends `af 30 00` with no terminator), and reading every
        pattern eagerly would otherwise make one unreachable pattern fatal for
        an entire tune that plays perfectly well.
        """
        out: List[int] = []
        i = 0
        while i < cap:
            try:
                b = self.byte(base + i)
            except MattGrayError:
                self.truncated_patterns += 1
                return out + [PC_PAT_END]
            out.append(b)
            if b == PC_PAT_END:
                return out
            # control codes consume one parameter byte; that parameter must
            # not be mistaken for an $ff terminator
            if b >= PC_INSTR:
                i += 1
                try:
                    out.append(self.byte(base + i))
                except MattGrayError:
                    self.truncated_patterns += 1
                    return out + [PC_PAT_END]
            i += 1
        raise MattGrayError(f"pattern at ${base:04x} has no $ff terminator")


# --------------------------------------------------------------------------
# Sequencer simulation
# --------------------------------------------------------------------------

@dataclass
class _VoiceState:
    track: List[int]
    track_index: int = 0
    pattern_index: int = 0
    duration: int = 0        # sticky duration byte
    counter: int = 0         # ctrl2 countdown
    instrument: int = 0
    stopped: bool = False
    last_note: int = 0
    looped: bool = False       # track hit its $ff and wrapped to index 0


def simulate(song: MattGraySong, frames: int = 3000,
             stop_on_loop: bool = False) -> List[List[MattGrayNote]]:
    """Run the sequencer for `frames` frames and return per-voice note events.

    This mirrors the driver's control flow exactly: `tempo_ctr` ticks once per
    frame; on a tick each voice decrements its duration counter and fetches the
    next pattern event when the counter goes negative (an 8-bit `dec` + `bmi`).

    Only the *sequencer* is modelled -- the synth side (slides, arpeggios,
    PWM, the drum path) is deliberately out of scope for Stage A.
    """
    voices = [_VoiceState(track=song.tracks[v]) for v in range(3)]
    out: List[List[MattGrayNote]] = [[], [], []]

    # reset_voices leaves tempo_ctr = 1, all counters and indices zeroed
    tempo_ctr = 1
    tick = 0

    for frame in range(frames):
        if tempo_ctr == 0:
            for vi, st in enumerate(voices):
                if st.stopped:
                    continue
                st.counter = (st.counter - 1) & 0xFF
                if st.counter & 0x80:            # bmi -> fetch next event
                    ev = _fetch(song, st, vi, frame, tick)
                    if ev is not None:
                        out[vi].append(ev)
                    if stop_on_loop and st.looped:
                        st.stopped = True
            tick += 1
        # voice_done runs the tempo counter once per frame, after voice 3
        tempo_ctr = (tempo_ctr - 1) & 0xFF
        if tempo_ctr & 0x80:
            tempo_ctr = song.tempo
        if all(v.stopped for v in voices):
            break
    return out


def _fetch(song: MattGraySong, st: _VoiceState, vi: int,
           frame: int, tick: int) -> Optional[MattGrayNote]:
    """One pass of `read_note_or_ctrl`, ending when a note row is consumed."""
    # L09b6 re-derives the pattern pointer from the track on every fetch
    pat_no = st.track[st.track_index] if st.track_index < len(st.track) else 0
    if pat_no >= len(song.patterns):
        st.stopped = True
        return None
    pattern = song.patterns[pat_no]

    # L09b6 zeroes the effect slot on every fetch, so a slide seen here applies
    # only to the note this fetch is about to consume.
    slide: Optional[Tuple[int, int]] = None

    guard = 0
    while guard < 1024:
        guard += 1
        if st.pattern_index >= len(pattern):
            st.stopped = True
            return None
        b = pattern[st.pattern_index]

        # A control code takes one parameter byte.  A pattern truncated by the
        # relocating copy (LN2 subtune 7) can end mid-code, so bail out rather
        # than index past it.
        if (song.duration_base is not None and b == PC_PARAM
                and st.pattern_index + 1 < len(pattern)):
            # LN2's fourth control code ($418d: cmp #$f9).  It consumes a
            # parameter byte and plays NO note.  Because $f9 >= the $70
            # duration base, mistaking it for a duration also turns its
            # parameter into a spurious note -- which is exactly how this
            # showed up: one invented note per occurrence, then realignment.
            st.pattern_index += 2
            continue

        if b >= PC_INSTR and st.pattern_index + 1 >= len(pattern):
            st.stopped = True
            return None

        if song.duration_base is None and b >= PC_DUR:   # $fd/$fe: duration
            st.duration = pattern[st.pattern_index + 1]
            st.pattern_index += 2
            continue
        if b >= PC_SLIDE1:                    # $fb/$fc: slide, one param byte
            slide = (1 if b == PC_SLIDE1 else 2, pattern[st.pattern_index + 1])
            st.pattern_index += 2
            continue
        if b >= PC_INSTR:                     # $fa: set instrument
            st.instrument = pattern[st.pattern_index + 1]
            st.pattern_index += 2
            continue

        if song.duration_base is not None and b >= song.duration_base:
            # LN2 style: the byte IS the duration (sticky), not a note
            st.duration = b - song.duration_base
            st.pattern_index += 1
            continue

        # --- a plain note row
        note = b
        st.counter = st.duration
        ev = MattGrayNote(
            frame=frame, tick=tick, voice=vi, note=note,
            instrument=st.instrument, duration=st.duration,
            track_index=st.track_index, pattern=pat_no, slide=slide,
        )
        if note != NOTE_REST:
            st.last_note = note
        st.pattern_index += 1

        # end-of-pattern / track advance, checked right after the note
        if st.pattern_index < len(pattern) and pattern[st.pattern_index] == PC_PAT_END:
            st.pattern_index = 0
            st.track_index += 1
            if st.track_index >= len(st.track):
                st.stopped = True
            else:
                tb = st.track[st.track_index]
                if tb == TRK_LOOP:
                    st.track_index = 0
                    st.looped = True
                elif tb == TRK_STOP:
                    st.stopped = True
        return ev

    raise MattGrayError(f"pattern {pat_no} did not yield a note row")


# --------------------------------------------------------------------------
# PSID front door
# --------------------------------------------------------------------------

def load_sid(path: str) -> Tuple[bytes, int, int, int, int, int]:
    """Return (body, load, init, play, songs, startsong) for a PSID/RSID file.

    Handles the `load == 0` quirk, where the real load address is the first
    two bytes of the data block rather than the header field.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:4] not in (b"PSID", b"RSID"):
        raise MattGrayError(f"{path}: not a PSID/RSID file")
    _ver, doff, load, init, play, songs, start = struct.unpack(">HHHHHHH", raw[4:18])
    body = raw[doff:]
    if load == 0:
        load = _u16(body, 0)
        body = body[2:]
    return body, load, init, play, songs, start


# A relocating-compilation wrapper (Last Ninja 2, 1988): `init` copies the
# selected subtune's self-contained player+data blob to a fixed address before
# anything can be parsed, so `play` points at zeroed memory in the file itself.
# The init prologue is distinctive:
#     tax / lda $01 / pha / lda #$36 / sta $01 / lda src_lo,x ...
_WRAP_PROLOGUE = bytes([0xAA, 0xA5, 0x01, 0x48, 0xA9, 0x36, 0x85, 0x01, 0xBD])
_WRAP_SRC_LO, _WRAP_SRC_HI = 9, 14      # operand offsets from init
_WRAP_DST_LO, _WRAP_DST_HI = 19, 23     # immediate operands
_WRAP_TAIL, _WRAP_PAGES = 27, 32


def relocating_subtunes(body: bytes, load: int, init: int,
                        songs: int) -> Optional[List[Tuple[bytes, int]]]:
    """If this file is a relocating compilation, return one (blob, dst) per
    subtune; otherwise None.

    Length is `pages * 256 + tail`, matching the driver's page loop followed by
    a tail loop (a tail of 0 means a full extra page, since the compare happens
    after the increment).
    """
    off = init - load
    if off < 0 or body[off:off + len(_WRAP_PROLOGUE)] != _WRAP_PROLOGUE:
        return None
    src_lo = _u16(body, off + _WRAP_SRC_LO) - load
    src_hi = _u16(body, off + _WRAP_SRC_HI) - load
    tail_t = _u16(body, off + _WRAP_TAIL) - load
    page_t = _u16(body, off + _WRAP_PAGES) - load
    dst = body[off + _WRAP_DST_LO] | (body[off + _WRAP_DST_HI] << 8)

    out: List[Tuple[bytes, int]] = []
    for i in range(songs):
        src = body[src_lo + i] | (body[src_hi + i] << 8)
        tail, pages = body[tail_t + i], body[page_t + i]
        n = pages * 256 + (tail or 256)
        start = src - load
        out.append((body[start:start + n], dst))
    return out


# A second wrapper shape (Tusker, 1989): a self-modifying copy loop, sources
# page-aligned so only a hi-byte table exists, and a destination of $e000 --
# under KERNAL ROM, which is why its PSID play address is $e002.
#   sei / tax / lda #$00 / sta lo / sta lo / lda src_hi,x / sta hi / lda #$e0
_WRAP2_PROLOGUE = bytes([0x78, 0xAA, 0xA9, 0x00, 0x8D])


def relocating_subtunes_v2(body: bytes, load: int, init: int,
                           songs: int) -> Optional[List[Tuple[bytes, int]]]:
    """Tusker-style wrapper: page-aligned blobs copied to a fixed page."""
    off = init - load
    if off < 0 or body[off:off + len(_WRAP2_PROLOGUE)] != _WRAP2_PROLOGUE:
        return None
    # lda #$e0 supplies the destination page; the two lda abs,x are the
    # source-hi and page-count tables.
    dst_page = None
    tabs: List[int] = []
    for i in range(off, min(off + 48, len(body) - 2)):
        if body[i] == 0xA9 and body[i + 2] == 0x8D and body[i + 1] not in (0x00,):
            dst_page = body[i + 1]
        elif body[i] == 0xBD:
            tabs.append(_u16(body, i + 1) - load)
    if dst_page is None or len(tabs) < 2:
        return None
    src_hi_t, page_t = tabs[0], tabs[1]
    out: List[Tuple[bytes, int]] = []
    for i in range(songs):
        src = body[src_hi_t + i] << 8
        n = body[page_t + i] * 256
        start = src - load
        if start < 0 or n <= 0:
            return None
        out.append((body[start:start + n], dst_page << 8))
    return out


def parse_sid(path: str, subtune: int = 1) -> MattGraySong:
    """Parse a Matt Gray SID straight from disk.

    Handles both the plain layout (Driller) and the relocating compilation
    (Last Ninja 2), where `subtune` selects which blob to materialise.
    """
    body, load, init, play, songs, _start = load_sid(path)
    blobs = (relocating_subtunes(body, load, init, songs)
             or relocating_subtunes_v2(body, load, init, songs))
    if blobs is not None:
        if not 0 <= subtune < len(blobs):
            raise MattGrayError(
                f"subtune {subtune} out of range (file has {len(blobs)})")
        blob, dst = blobs[subtune]
        # each blob is a self-contained tune; its own tune index is 1
        song = MattGrayParser(blob, dst, dst, dst + 2).parse(subtune=1)
        # On this path `subtune` selects the BLOB, so it already is the PSID
        # song index -- the inner parse only ever sees its own index 1 and
        # would otherwise report song 0 for every subtune.
        song.subtune = subtune
        song.psid_song = subtune
        return song
    return MattGrayParser(body, load, init, play).parse(subtune=subtune)
