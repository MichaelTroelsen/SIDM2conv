"""HardTrack Composer (Longhair/Brush, Elysium 1992) — module parser.

Decodes the sequencer side of a HardTrack Composer `.sid`: subtune table,
per-voice orderlists, patterns, the 13-field instrument records and the
player's own note-frequency table.

RELOCATION SAFETY
-----------------
The player code is a fixed layout, but the *data* table addresses are patched
per file (the editor packs song data of varying size and rewrites the absolute
operands). Two shipped player variants exist, differing by 5 bytes in `init`
(play sits at init+$78 or init+$7d). So every table address here is recovered
by matching a byte signature against the player's own code rather than by
adding a constant to the load address -- see `_SIG_*` below.

WHAT IS AND IS NOT MODELLED
---------------------------
`simulate()` reproduces the player's sequencer state machine: tempo divider,
orderlist walk (pattern / transpose / jump / hold / end), pattern stream
(note+instrument pairs, rests, commands) and note duration. It does NOT model
the wave/pulse/filter programs. That matters for fidelity scoring: an
instrument with bit 7 set in instrument field 5 drives `$D400/$D401`
*absolutely* from its own program table, so for those notes the sequencer
pitch never reaches the frequency register at all. `instrument_drives_freq()`
exposes that flag so a scorer can separate "the parser is wrong" from "the
synth engine owns this register" instead of averaging the two into one
meaningless number.

The per-frame synth engine those programs describe is modelled one level down,
in `sidm2.hardtrack_synth` -- see `simulate_registers()`.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = [
    'HardTrackError', 'HardTrackModule', 'Instrument',
    'ORDER_END', 'ORDER_HOLD', 'ORDER_JUMP',
    'CMD_TIE', 'CMD_GATE_OFF', 'CMD_RESET', 'CMD_SLIDE', 'CMD_PORTA',
    'CMD_REST', 'PATTERN_END', 'INSTR_HOLD', 'INSTR_LEGATO',
    'Onset', 'next_pattern_event', 'simulate', 'Event', 'voice_events',
]

# --- orderlist bytes -------------------------------------------------------
ORDER_END = 0xFF     # restart the orderlist from index 0
ORDER_HOLD = 0xFE    # halt this voice
ORDER_JUMP = 0xFD    # next byte = new orderlist index (song loop point)
# $80..$FC -> transpose = value & $7F, applied to the FOLLOWING pattern

# --- pattern stream bytes --------------------------------------------------
PATTERN_END = 0xFF   # end of pattern -> fetch the next orderlist entry
CMD_TIE = 0x60       # keep sounding; still consumes an instrument byte
CMD_GATE_OFF = 0x61  # gate off
CMD_RESET = 0x62     # reset the per-voice synth cursors
CMD_SLIDE = 0x63     # + 1 arg byte
CMD_PORTA = 0x64     # + 1 arg byte
CMD_REST = 0x67      # + 1 arg byte = rest length in rows
INSTR_HOLD = 0x00    # instrument byte 0 = keep the instrument, RESTART its programs
# Instrument byte $6F = LEGATO: the pitch changes but the instrument's wave and
# pulse programs are NOT restarted ($16CB is set, which makes the note-on path
# skip the instrument reload). Distinct from $00, which keeps the same
# instrument but does restart it. 24.7% of note events in the Shogoon corpus
# carry it, so it is a core feature, not an edge case.
INSTR_LEGATO = 0x6F

# The pattern reader masks the instrument byte with $1F, so an index is 0..31.
# The number of instruments actually STORED is per-file, though, and it sets the
# stride of the parallel tables -- see HardTrackModule.num_instruments.
MAX_INSTRUMENTS = 32
INSTRUMENT_FIELDS = 13     # 13 parallel tables, each num_instruments bytes
NUM_NOTES = 96             # 8 octaves, freq table entry 0 == C-0
MAX_SUBTUNES = 8           # init does AND #$07

_W = None  # signature wildcard


class HardTrackError(ValueError):
    """Raised when a file is not a decodable single-instance HardTrack module."""


# init: and #$07 / tax / (lda ABS,x / sta $xx..) x7
_SIG_INIT = [0x29, 0x07, 0xAA] + [0xBD, _W, _W, 0x8D, _W, _W] * 7
# pattern pointer tables: tay / lda LO,y / sta $x010,x / sta $fb / lda HI,y / sta $x013,x
_SIG_PATPTR = [0xA8, 0xB9, _W, _W, 0x9D, _W, _W, 0x85, 0xFB, 0xB9, _W, _W, 0x9D, _W, _W]
# note -> frequency:
#   lda note,x / clc / adc transpose,x / and #$7f / sta cur,x / tay
#   lda FREQHI,y / sta freqhi,x / lda FREQLO,y / sta freqlo,x
_SIG_FREQ = [0xBD, _W, _W, 0x18, 0x7D, _W, _W, 0x29, 0x7F, 0x9D, _W, _W, 0xA8,
             0xB9, _W, _W, 0x9D, _W, _W, 0xB9, _W, _W, 0x9D, _W, _W]
# instrument record load: ldy instr,x / lda F0,y / sta ad,x / lda F1,y / sta sr,x
_SIG_INSTR = [0xBC, _W, _W, 0xB9, _W, _W, 0x9D, _W, _W, 0xB9, _W, _W, 0x9D, _W, _W]
# the "program drives frequency absolutely" flag: lda F5,y / and #$80 / sta abs,x
_SIG_ABSFLAG = [0xB9, _W, _W, 0x29, 0x80, 0x9D, _W, _W]
# waveform/arpeggio program stepper:
#   ldy cur,x / inc cur,x / lda WAVE,y / cmp #$ff / bne / lda ARP,y
_SIG_WAVEPROG = [0xBC, _W, _W, 0xFE, _W, _W, 0xB9, _W, _W, 0xC9, 0xFF, 0xD0, _W,
                 0xB9, _W, _W]
# pulse-sweep program stepper: ldy cur,x / inc cur,x / lda PULSE,y / cmp #$ff
_SIG_PULSEPROG = [0xBC, _W, _W, 0xFE, _W, _W, 0xB9, _W, _W, 0xC9, 0xFF, 0xD0, _W,
                  0xC8, 0xB9, _W, _W]


def _find(data: bytes, pat) -> list[int]:
    n = len(pat)
    out = []
    for i in range(len(data) - n + 1):
        for j, p in enumerate(pat):
            if p is not None and data[i + j] != p:
                break
        else:
            out.append(i)
    return out


def _word(data: bytes, off: int) -> int:
    return struct.unpack('<H', data[off:off + 2])[0]


@dataclass(frozen=True)
class Instrument:
    """One instrument record: the 13 parallel-table bytes for a given index.

    Field roles confirmed from the player's own register writes; the ones still
    marked unknown are named `fN` deliberately rather than guessed at.
    """
    index: int
    raw: tuple

    @property
    def ad(self) -> int:            # -> $D405
        return self.raw[0]

    @property
    def sr(self) -> int:            # -> $D406
        return self.raw[1]

    @property
    def pulse_lo(self) -> int:
        """$D402. The player stores it in the HIGH nibble of field 2."""
        return self.raw[2] & 0xF0

    @property
    def pulse_hi(self) -> int:
        """$D403 (pulse-width bits 8-11). The LOW nibble of field 2."""
        return self.raw[2] & 0x0F

    @property
    def pulse_width(self) -> int:
        """The 12-bit initial pulse width this instrument starts at."""
        return (self.pulse_hi << 8) | self.pulse_lo

    @property
    def pulse_cursor(self) -> int:
        """Start index into the pulse-sweep program (field 3 -> $16c2)."""
        return self.raw[3]

    @property
    def wave_cursor(self) -> int:
        """Start index into the waveform/arpeggio program (field 4 -> $16f2)."""
        return self.raw[4]

    @property
    def flags(self) -> int:
        return self.raw[5]

    @property
    def drives_freq(self) -> bool:
        """Bit 7: the wave program writes $D400/$D401 absolutely.

        For such an instrument the sequencer note selects nothing in the
        frequency register -- percussion and fixed-pitch effects. Measured
        across the Shogoon corpus this flag separates 2.6%-matching notes from
        88.4%-matching ones, so it is the right gate for any pitch metric.
        """
        return bool(self.raw[5] & 0x80)

    @property
    def hard_restart(self) -> bool:
        return bool(self.raw[5] & 0x10)

    @property
    def mode(self) -> int:
        return self.raw[5] & 0x03


class HardTrackModule:
    """A parsed HardTrack Composer module."""

    def __init__(self, load: int, data: bytes, subtunes: int = 1,
                 psid_init: int | None = None, psid_play: int | None = None):
        self.load = load
        self.data = data
        self.subtunes = max(1, min(subtunes, MAX_SUBTUNES))

        hits = _find(data, _SIG_INIT)
        if not hits:
            raise HardTrackError('no HardTrack Composer init signature found')
        if len(hits) > 1:
            raise HardTrackError(
                f'{len(hits)} player instances in one file -- this is a wrapped or '
                f'multi-module rip, not a single HardTrack module. Refusing rather '
                f'than decoding instance 0 and reporting it as the song.')
        o = hits[0]
        self.init_off = o
        # A HardTrack module is entered through its own `JMP init` / `JMP play`
        # pair at load+0/+3. When the PSID header points somewhere else the file
        # is a wrapper around the module (extra loader, relocator or several
        # tunes), and decoding from load+0 would silently describe the wrong
        # song -- so refuse instead of guessing.
        if psid_init is not None and psid_init != load:
            raise HardTrackError(
                f'PSID init ${psid_init:04x} is not the module entry ${load:04x}: '
                f'wrapped rip, refusing to decode')
        if psid_play is not None and psid_play != load + 3:
            raise HardTrackError(
                f'PSID play ${psid_play:04x} is not the module entry ${load + 3:04x}: '
                f'wrapped rip, refusing to decode')
        self._order_lo = (_word(data, o + 4), _word(data, o + 16), _word(data, o + 28))
        self._order_hi = (_word(data, o + 10), _word(data, o + 22), _word(data, o + 34))
        self.speed_table = _word(data, o + 40)

        h = _find(data, _SIG_PATPTR)
        if len(h) != 1:
            raise HardTrackError(f'pattern-pointer signature matched {len(h)}x, expected 1')
        self.pattern_lo = _word(data, h[0] + 2)
        self.pattern_hi = _word(data, h[0] + 10)

        h = _find(data, _SIG_FREQ)
        if len(h) != 1:
            raise HardTrackError(f'frequency-table signature matched {len(h)}x, expected 1')
        self.freq_hi_table = _word(data, h[0] + 14)
        self.freq_lo_table = _word(data, h[0] + 20)

        h = _find(data, _SIG_INSTR)
        if not h:
            raise HardTrackError('instrument-table signature not found')
        self.instrument_base = min(_word(data, x + 4) for x in h)

        h = _find(data, _SIG_ABSFLAG)
        self.flag_table = _word(data, h[0] + 1) if len(h) == 1 else None

        h = _find(data, _SIG_WAVEPROG)
        if len(h) == 1:
            self.wave_table = _word(data, h[0] + 7)    # -> $D404 waveform steps
            self.arp_table = _word(data, h[0] + 14)    # paired arpeggio / abs freq
        else:
            self.wave_table = self.arp_table = None

        # +7, not +6: index 6 of the signature is the `lda ABS,y` OPCODE, its
        # operand starts at 7 -- same shape as _SIG_WAVEPROG's +7/+14. Reading
        # the opcode byte as the low half of the address put this table outside
        # the module on every file in the corpus, so `pulse_program()` returned
        # a full-length series of zeroes that looked like a decoded program.
        h = _find(data, _SIG_PULSEPROG)
        self.pulse_table = _word(data, h[0] + 7) if len(h) == 1 else None

        # How many instruments are STORED sets the stride of the 13 parallel
        # tables, and it is per-file (3..32 across the corpus) -- not a constant
        # 32. Derive it two independent ways and require agreement: field 5 is
        # the flag table, field 13 is one past the block. Getting this wrong
        # reads every field but the first from the wrong address, which is
        # exactly the kind of error that still yields plausible-looking bytes.
        self.num_instruments = MAX_INSTRUMENTS
        self.instrument_count_verified = False
        n5 = n13 = None
        if self.flag_table is not None:
            d = self.flag_table - self.instrument_base
            if d > 0 and d % 5 == 0:
                n5 = d // 5
        if self.wave_table is not None:
            d = self.wave_table - self.instrument_base
            if d > 0 and d % INSTRUMENT_FIELDS == 0:
                n13 = d // INSTRUMENT_FIELDS
        if n5 and n13 and n5 == n13 and 0 < n5 <= MAX_INSTRUMENTS:
            self.num_instruments = n5
            self.instrument_count_verified = True
        elif n5 and 0 < n5 <= MAX_INSTRUMENTS:
            self.num_instruments = n5

    # -- construction -------------------------------------------------------
    @classmethod
    def from_sid(cls, path) -> 'HardTrackModule':
        raw = open(path, 'rb').read()
        if raw[:4] not in (b'PSID', b'RSID'):
            raise HardTrackError(f'{path}: not a PSID/RSID file')
        doff = struct.unpack('>H', raw[6:8])[0]
        load = struct.unpack('>H', raw[8:10])[0]
        init = struct.unpack('>H', raw[10:12])[0]
        play = struct.unpack('>H', raw[12:14])[0]
        subs = struct.unpack('>H', raw[14:16])[0]
        pay = raw[doff:]
        if load == 0:
            load = struct.unpack('<H', pay[0:2])[0]
            pay = pay[2:]
        return cls(load, pay, subs, psid_init=init, psid_play=play)

    # -- primitives ---------------------------------------------------------
    def byte(self, addr: int) -> int:
        i = addr - self.load
        return self.data[i] if 0 <= i < len(self.data) else 0

    def speed(self, subtune: int = 0) -> int:
        """Tempo divider. A song row lands every speed+1 frames."""
        return self.byte(self.speed_table + subtune)

    def order_pointer(self, voice: int, subtune: int = 0) -> int:
        return (self.byte(self._order_lo[voice] + subtune)
                | (self.byte(self._order_hi[voice] + subtune) << 8))

    def pattern_pointer(self, n: int) -> int:
        return self.byte(self.pattern_lo + n) | (self.byte(self.pattern_hi + n) << 8)

    def freq(self, note: int) -> int:
        """The player's own 16-bit frequency for a note index (0 == C-0)."""
        return (self.byte(self.freq_lo_table + note)
                | (self.byte(self.freq_hi_table + note) << 8))

    def instrument(self, n: int) -> Instrument:
        base, stride = self.instrument_base, self.num_instruments
        return Instrument(n, tuple(self.byte(base + k * stride + n)
                                   for k in range(INSTRUMENT_FIELDS)))

    def wave_program(self, cursor: int, limit: int = 64):
        """[(waveform, arp)] steps from `cursor`, stopping at the $FF jump.

        $D404 waveform bytes with a paired value that is an arpeggio offset
        added to the note -- or, when the instrument's bit 7 is set, the
        absolute frequency high byte.
        """
        if self.wave_table is None:
            return []
        out = []
        for i in range(limit):
            wf = self.byte(self.wave_table + cursor + i)
            if wf == 0xFF:
                break
            out.append((wf, self.byte(self.arp_table + cursor + i)))
        return out

    def pulse_program(self, cursor: int, limit: int = 64):
        """[(step, frames)] pulse-width sweep steps from `cursor`.

        `step` is signed: the player masks the value with $FE for the magnitude
        and uses bit 0 as the direction (0 = up, 1 = down).
        """
        if self.pulse_table is None:
            return []
        out, i = [], 0
        while i < limit * 2:
            v = self.byte(self.pulse_table + cursor + i)
            if v == 0xFF:
                break
            mag = v & 0xFE
            out.append((-mag if v & 0x01 else mag,
                        self.byte(self.pulse_table + cursor + i + 1)))
            i += 2
        return out

    def instrument_drives_freq(self, n: int) -> bool:
        if self.flag_table is None:
            return self.instrument(n).drives_freq
        return bool(self.byte(self.flag_table + n) & 0x80)

    # -- structure ----------------------------------------------------------
    def orderlist(self, voice: int, subtune: int = 0, limit: int = 512) -> list[tuple]:
        """[(kind, value)] with kind in {pat, transpose, jump, hold, end}."""
        p = self.order_pointer(voice, subtune)
        out: list[tuple] = []
        i = 0
        while i < limit:
            v = self.byte(p + i)
            if v < 0x80:
                out.append(('pat', v)); i += 1
            elif v == ORDER_END:
                out.append(('end', 0)); break
            elif v == ORDER_HOLD:
                out.append(('hold', 0)); i += 1
            elif v == ORDER_JUMP:
                out.append(('jump', self.byte(p + i + 1))); break
            else:
                out.append(('transpose', v & 0x7F)); i += 1
        return out

    def pattern(self, n: int, limit: int = 4096) -> list[tuple]:
        """[(kind, a, b)] in stream order; kind in {note, rest, cmdXX, end}."""
        p = self.pattern_pointer(n)
        out: list[tuple] = []
        i = 0
        while i < limit:
            v = self.byte(p + i); i += 1
            if v == PATTERN_END:
                out.append(('end', 0, 0)); break
            if v == CMD_REST:
                out.append(('rest', self.byte(p + i), 0)); i += 1
            elif v in (CMD_SLIDE, CMD_PORTA):
                out.append((f'cmd{v:02x}', self.byte(p + i), 0)); i += 1
            elif v in (CMD_TIE, CMD_GATE_OFF, CMD_RESET):
                out.append((f'cmd{v:02x}', self.byte(p + i), 0)); i += 1
            else:
                out.append(('note', v & 0x7F, self.byte(p + i))); i += 1
        return out

    def patterns_used(self, subtune: int = 0) -> list[int]:
        return sorted({v for vo in range(3)
                       for k, v in self.orderlist(vo, subtune) if k == 'pat'})


class _Voice:
    __slots__ = ('order_ptr', 'order_idx', 'pat_ptr', 'pat_idx', 'transpose',
                 'cmd', 'dur', 'active', 'note', 'instr', 'halted', 'trigger',
                 'pattern')

    def __init__(self, order_ptr: int):
        self.order_ptr = order_ptr
        self.order_idx = 0
        # init points every voice's pattern pointer at a hardcoded $FF byte
        # inside the player's own code, so the first duration expiry falls
        # straight through into the orderlist fetch. None models that sentinel.
        self.pat_ptr = None
        self.pat_idx = 0
        self.transpose = 0
        self.cmd = 0
        self.dur = 1
        self.active = 1
        self.note = 0
        self.instr = 0
        self.halted = False
        self.trigger = False
        self.pattern = None


class Onset(tuple):
    """A note-on with everything needed to attribute it later.

    Unpacks as the historical ``(note, instrument)`` 2-tuple so existing callers
    keep working, while exposing the fields that make an attribution EXACT:

      * ``raw`` -- the pattern's instrument byte, which distinguishes $00 (keep
        the instrument, RESTART its programs) from $6F (keep it and do NOT).
      * ``pattern`` / ``transpose`` / ``pat_index`` -- where in the score the
        note came from, so a scorer can look at what surrounds it (e.g. whether
        the next event is the $62 that freezes the wave stepper).

    Attributing losses by re-deriving these with a cursor heuristic instead
    produced a mis-aligned tagging that reversed a real result, so they are
    carried from the walk itself.
    """
    def __new__(cls, note, instrument, raw=None, pattern=None, transpose=0,
                pat_index=None):
        return super().__new__(cls, (note, instrument))

    def __init__(self, note, instrument, raw=None, pattern=None, transpose=0,
                 pat_index=None):
        self.note = note
        self.instrument = instrument
        self.raw = raw
        self.pattern = pattern
        self.transpose = transpose
        self.pat_index = pat_index


def next_pattern_event(module: HardTrackModule, pattern: int, byte_index: int):
    """The first non-rest event kind at or after `byte_index` in a pattern.

    Needed to ask "is this note immediately followed by $62?" -- $62 sets $16D4,
    which makes the player skip the wave stepper from then on.
    """
    p = module.pattern_pointer(pattern)
    i = byte_index
    for _ in range(64):
        v = module.byte(p + i)
        if v == PATTERN_END:
            return 'end'
        if v == CMD_REST:
            i += 2
            continue
        if v in (CMD_SLIDE, CMD_PORTA, CMD_TIE, CMD_GATE_OFF, CMD_RESET):
            return f'cmd{v:02x}'
        i += 2
    return None


@dataclass
class Event:
    """One sequencer event a voice actually SOUNDS: a note-on or a gate-off.

    `dur` is in ticks and is filled in by `voice_events` once the following
    event is known, so it absorbs the ticks spent on events that do not
    interrupt the sounding note ($67 rests, $60 tie, $62 reset, $63/$64
    slide/porta). A HardTrack note length is exactly that: the note's own tick
    plus the `$67 n` rest that follows it.
    """
    tick: int                  # row index; frame == onset_delay + tick*(speed+1)
    frame: int                 # the frame the player dispatched it on
    kind: str                  # 'note' | 'gate_off'
    note: int = 0              # transposed + masked exactly as the player does
    instr: int = 0
    raw: int = 0               # the pattern's instrument byte ($00 hold, $6F legato)
    dur: int = 1               # ticks until the next event on this voice
    pattern: int | None = None
    transpose: int = 0

    @property
    def legato(self) -> bool:
        """$6F: the pitch changes but the instrument's programs do NOT restart."""
        return self.raw == INSTR_LEGATO


def voice_events(module: HardTrackModule, subtune: int = 0, frames: int = 1000):
    """Per-voice `Event` lists plus each voice's first orderlist-loop frame.

    Returns `(events, loop_frames)` — `events[v]` in play order with durations
    resolved, `loop_frames[v]` the frame at which that voice first restarted or
    jumped in its orderlist (None if it never did within `frames`).

    This runs the SAME state machine as `simulate()` rather than a second copy
    of it: a duplicated sequencer walk is exactly what mis-attributed the Stage A
    losses once already.

    Each voice's list is made CONTIGUOUS from tick 0 -- a voice whose pattern
    opens with a rest gets a leading `gate_off` covering it, and the last event
    runs to the end of the scanned window. A consumer that walks the list
    accumulating durations (which is what every native builder does) would
    otherwise slide a late-entering voice forward to tick 0: on Love_tune_2 that
    is voices 1 and 2 starting 10 and 20 frames early, for the whole song.
    """
    log: list[list[Event]] = [[], [], []]
    loops: list[int | None] = [None, None, None]
    simulate(module, subtune, frames, _log=log, _loops=loops)
    fpt = module.speed(subtune) + 1
    # init leaves the divider at 2, so rows are dispatched on frames 1, 1+fpt,
    # 1+2*fpt ... -- that is how many rows fit in the scanned window.
    total = max(0, -(-(frames - 1) // fpt))
    for evs in log:
        for i, e in enumerate(evs):
            nxt = evs[i + 1].tick if i + 1 < len(evs) else max(total, e.tick + 1)
            e.dur = max(1, nxt - e.tick)
        if evs and evs[0].tick > 0:
            evs.insert(0, Event(0, evs[0].frame - evs[0].tick * fpt, 'gate_off',
                                dur=evs[0].tick, pattern=evs[0].pattern))
    return log, loops


def simulate(module: HardTrackModule, subtune: int = 0, frames: int = 1000,
             _log=None, _loops=None):
    """Run the sequencer state machine.

    Returns frames[f][voice] = an `Onset` on a note-on, else None. `Onset`
    unpacks as `(note, instrument)`; `note` is already transposed and masked
    exactly as the player does it.

    `_log` / `_loops` are the `voice_events` hooks — call that, not these.
    """
    voices = [_Voice(module.order_pointer(v, subtune)) for v in range(3)]
    speed = module.speed(subtune)
    ctr = 2  # init leaves the tempo divider at 2
    tick = -1
    f = 0

    def next_pattern(v: _Voice) -> bool:
        for _ in range(512):
            a = module.byte(v.order_ptr + v.order_idx)
            v.order_idx += 1
            if a < 0x80:
                pass
            elif a == ORDER_END:
                v.order_idx = 0
                if _loops is not None and _loops[voices.index(v)] is None:
                    _loops[voices.index(v)] = f
                continue
            elif a == ORDER_HOLD:
                v.halted = True
                return False
            elif a == ORDER_JUMP:
                v.order_idx = module.byte(v.order_ptr + v.order_idx)
                if _loops is not None and _loops[voices.index(v)] is None:
                    _loops[voices.index(v)] = f
                continue
            else:
                v.transpose = a & 0x7F
                a = module.byte(v.order_ptr + v.order_idx)
                v.order_idx += 1
            v.pat_ptr = module.pattern_pointer(a)
            v.pattern = a
            v.cmd = module.byte(v.pat_ptr)
            v.pat_idx = 1
            return True
        v.halted = True
        return False

    out = []
    for f in range(frames):
        ctr -= 1
        if ctr < 0:
            ctr = speed
        if ctr == 0:
            tick += 1
        row = []
        for vi, v in enumerate(voices):
            on = None
            if v.halted:
                row.append(None)
                continue
            if ctr == 0:
                if not v.active:
                    row.append(None)
                    continue
                v.dur = 1                       # reset before dispatch
                c = v.cmd
                if c in (CMD_SLIDE, CMD_PORTA):
                    v.pat_idx += 1
                    row.append(None)
                    continue
                if c == CMD_REST:
                    v.active = 0
                    v.dur = module.byte(v.pat_ptr + v.pat_idx)
                    v.pat_idx += 1
                    row.append(None)
                    continue
                if c not in (CMD_TIE, CMD_GATE_OFF, CMD_RESET):
                    v.note = c & 0x7F
                    v.trigger = True
                a = module.byte(v.pat_ptr + v.pat_idx)
                v.pat_idx += 1
                if a not in (INSTR_HOLD, INSTR_LEGATO):
                    v.instr = a & 0x1F
                if v.trigger:
                    on = Onset((v.note + v.transpose) & 0x7F, v.instr,
                               raw=a, pattern=v.pattern, transpose=v.transpose,
                               pat_index=v.pat_idx)
                    v.trigger = False
                    if _log is not None:
                        _log[vi].append(Event(
                            tick, f, 'note', note=on.note, instr=v.instr,
                            raw=a, pattern=v.pattern, transpose=v.transpose))
                elif c == CMD_GATE_OFF and _log is not None:
                    _log[vi].append(Event(tick, f, 'gate_off', instr=v.instr,
                                          raw=a, pattern=v.pattern,
                                          transpose=v.transpose))
            elif ctr == 1:
                v.dur -= 1
                if v.dur == 0:
                    v.active = 1
                    a = (PATTERN_END if v.pat_ptr is None
                         else module.byte(v.pat_ptr + v.pat_idx))
                    v.pat_idx += 1
                    if a == PATTERN_END:
                        v.pat_idx = 0
                        if not next_pattern(v):
                            row.append(None)
                            continue
                    else:
                        v.cmd = a
            row.append(on)
        out.append(row)
    return out
