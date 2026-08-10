"""HardTrack Composer -- the per-frame synth engine, modelled register-exact.

`hardtrack_parser.simulate()` stops at the sequencer: it says which note-on
happens on which frame. That is deliberately one level too high to score an
instrument whose field-5 bit 7 is set, because such an instrument writes
`$D400/$D401` from its own waveform/arpeggio program and the sequencer pitch
never reaches the frequency register at all. Measured that way the whole
program-driven column reads 2.6%, which is not a fidelity figure -- it is the
number you get for predicting the wrong thing.

`simulate_registers()` predicts the right thing: the SID register file, every
frame, as siddump would print it. It is a transcription of the play routine
rather than a model of it, so it can be checked line-by-line against the
disassembly:

  $10ef  per-voice entry, halted check         $12fd  note-on trigger
  $110d  row read (tempo phase 0)              $130a  note frequency from the table
  $1199  instrument byte ($00 hold, $6F legato) $133e  instrument record load
  $11bf  gate/hard-restart on mode change      $13ee  pulse-width sweep step
  $11fc  duration decrement (tempo phase 1)    $1454  waveform/arpeggio step
  $1204  orderlist walk                        $14a5  slide / vibrato
  $12a1  vibrato parameter load                $1553  write the SID registers

THE THREE-FRAME NOTE-ON PIPELINE
--------------------------------
A note does not sound on the frame its row is read. The row read only latches
the note ($16f5); the frame after that loads the vibrato parameters ($12a1);
the frame after *that* is the real note-on ($12fd -> $130a) and even it only
writes AD/SR and `$D404 = $09`. The frequency registers are first written on
the following frame, by the synth path at $1553. So the register a scorer is
looking for appears at onset + 2 frames at the earliest -- which is most of why
onset scoring needed a settle window at all.

WHY A RUNNING WAVE PROGRAM SUPPRESSES VIBRATO
---------------------------------------------
The waveform stepper at $1454 ends in `JMP $1553` -- straight to the register
write, bypassing the slide/vibrato block at $14a5. Vibrato and $63/$64 slides
therefore only reach the frequency at all once the wave program has stopped
itself with `$FE`, or been frozen by the pattern's `$62`. That is a structural
property of the player, not a modelling shortcut.

THE FILTER IS GLOBAL, NOT PER-VOICE
-----------------------------------
It is modelled here too, but it is not a fourth voice. The engine sits *past*
the `dex / bmi` at $1583 that ends the voice loop, so it runs ONCE PER FRAME
after all three voices have been stepped -- and its cursor, cutoff accumulator,
delta and $d418 mode nibble live in self-modified operands rather than in the
per-voice block. Instrument fields 6, 7 and 12 only seed it, at note-on: f6 the
program cursor, f7 the initial cutoff, f12 `(resonance << 4) | mode`.

Two consequences worth stating because both are easy to get wrong:

  * The voices are stepped 2, 1, 0 ($10ed `ldx #$02` ... $1583 `dex`). For the
    per-voice registers the order cannot matter, since each voice writes its
    own $d400+7v. For the filter it decides the whole frame -- three note-ons
    on one frame all write the same four operands and the LAST one wins.
  * f12 == 0 does not skip the re-arm, it CLEARS this voice's routing bit
    ($13cb). An instrument with no filter actively switches its voice out.

$d415 is never written by this player -- not once in any of the 33 decodable
modules -- so the cutoff is the 8-bit $d416 alone, accumulated with CLC/ADC and
no clamp. It wraps, audibly and by design: `Love_tune_2` runs $1a -> $5a -> $9a
-> $da -> $1a and siddump agrees on every frame.

NOT MODELLED
------------
Nothing in the register file is left unpredicted now. The one thing this does
not do is *reset* the filter state at init, because the player does not either:
`init` zeroes $d400-$d41c and the per-voice block but touches none of the
filter's operands, so they are seeded from the saved module image.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hardtrack_parser import (  # the private _SIG_*: see `ram_layout_base`
    CMD_GATE_OFF, CMD_PORTA, CMD_REST, CMD_RESET, CMD_SLIDE, CMD_TIE,
    HardTrackError, HardTrackModule, INSTR_HOLD, INSTR_LEGATO, ORDER_END,
    ORDER_HOLD, ORDER_JUMP, PATTERN_END, _SIG_ABSFLAG, _SIG_PULSEPROG,
    _SIG_WAVEPROG, _find, _word,
)

__all__ = ['FilterFrame', 'VoiceFrame', 'simulate_all', 'simulate_registers',
           'ram_layout_base']

# Instrument fields the synth engine reads, by consumer address.
F_AD, F_SR, F_PULSE, F_PULSECUR, F_WAVECUR, F_FLAGS = 0, 1, 2, 3, 4, 5
F_FILTPROG, F_FILTCUT = 6, 7            # $13b9 filter cursor / $13b3 cutoff
F_VIBRATO, F_VIBDEPTH = 8, 9            # $12b2 nibbles / $12c8
F_VIBINC, F_VIBLIMIT = 10, 11           # $12ce / $12d4
F_FILTER = 12                           # $138f (resonance << 4) | mode

_JUMP_GUARD = 64    # a $FF program row may only chain this many times per step

# The player's per-voice variables are 3-byte arrays in one contiguous block,
# with a single 1-byte song-global (the filter program's frame counter) wedged
# in after the 13th. `_RAM` is that block's running order, by index.
#
# THESE ARE NOT ZERO AT INIT. The block lives inside the loaded module image, so
# its power-on contents are whatever bytes the editor saved there -- the
# player's live state at the moment the tune was exported. Assuming zero costs
# real accuracy: it makes the first note of every voice take the wrong branch at
# $11bf/$12e2, which runs one extra vibrato tick and leaves that voice's vibrato
# a frame out of phase until the next note-on resyncs it.
_RAM = (
    'ad', 'sr', 'freq_hi', 'freq_lo', 'pulse_lo', 'pulse_hi', 'waveform',
    'new_pattern', 'cmd', 'slide_cmd', 'slide_dir', 'slide_amt', 'vib_done',
    # -- the 1-byte global sits here --
    'pulse_step', 'pulse_frames', 'abs_freq', 'pending_note', 'vib_ctr',
    'pulse_cur', 'vib_inc', 'vib_limit', 'legato', 'prev_mode', 'mode',
    'wave_freeze', None, None, 'note_latched', 'gate_mask', 'transpose', None,
    'halted', 'vib_phase2', 'pulse_dir', 'wave_cur', 'note_pending',
    'vib_delay', 'vib_reload', 'vib_dir', 'instr', 'prev_instr', 'duration',
    'active',
)
_RAM_GAP = 13       # index after which the 1-byte global shifts everything by 1


def _ram_addr(base: int, i: int) -> int:
    return base + 3 * i + (1 if i >= _RAM_GAP else 0)


def ram_layout_base(module: HardTrackModule):
    """The per-voice variable block, or None when the layout does not check out.

    Anchored on the abs-flag store's destination ($16b9 in an unrelocated file)
    and verified against the waveform and pulse steppers' cursor operands, which
    the parser locates by two other signatures entirely. Three independent
    addresses agreeing on one base is what makes seeding safe; if any disagrees
    this returns None and the caller starts from zeroes and says so, rather than
    seeding from a base it guessed.

    `_RAM` describes the layout of ONE of the two shipped player builds (15 of
    the corpus's 33 decodable files use the other, where everything past the
    abs-flag sits 3 lower and `vib_depth`/`pending_note` swap between the voice
    block and the module header -- so it is a different allocation, not an
    offset). Those files simply run unseeded: correct from their first note-on
    onward, with the startup transient described above. Do not pool a seeded and
    an unseeded score without saying which is which.
    """
    hits = _find(module.data, _SIG_ABSFLAG)
    if len(hits) != 1:
        return None
    base = _word(module.data, hits[0] + 6) - _ram_addr(0, 15)
    # Both stepper signatures open with `ldy CURSOR,x`, so their operand at +1
    # is the cursor variable -- a different address from the program table the
    # parser takes off the same match.
    for sig, idx in ((_SIG_WAVEPROG, 34), (_SIG_PULSEPROG, 18)):
        h = _find(module.data, sig)
        if len(h) != 1 or _word(module.data, h[0] + 1) != _ram_addr(base, idx):
            return None
    return base


@dataclass
class VoiceFrame:
    """One voice's SID register file at the end of one frame."""
    freq: int            # $D400/$D401 as a 16-bit value
    pulse: int           # $D402/$D403 as a 12-bit value
    waveform: int        # $D404
    ad: int              # $D405
    sr: int              # $D406
    instr: int           # the instrument the sequencer last selected
    note: int            # the transposed sequencer note driving it
    drives_freq: bool    # that instrument's field-5 bit 7
    started: bool        # a note has been triggered on this voice at least once


@dataclass
class FilterFrame:
    """The filter registers at the end of one frame. There is one, not three."""
    cutoff: int          # $D416 -- the 8-bit accumulator; $D415 is never written
    res_route: int       # $D417 -- (resonance << 4) | the three routing bits
    mode_vol: int        # $D418 -- (mode << 4) | volume


class _F:
    """Filter engine state: five self-modified operands and one shadow byte.

    `init` resets none of them, so they start from whatever the editor saved.
    `located` is False when the engine's signatures did not match, and then the
    caller is told rather than being handed a confident series of zeroes.
    """

    __slots__ = ('cursor', 'acc', 'delta', 'mode', 'delay', 'shadow',
                 'r_d417', 'located', 'bits', 'masks')

    def __init__(self, module):
        self.located = module.filter_table is not None
        self.bits = module.filter_route_bits or (1, 2, 4)
        self.masks = module.filter_route_masks or (0xFE, 0xFD, 0xFB)
        self.cursor = module.filter_cursor or 0
        self.acc = module.filter_cutoff or 0
        self.delta = module.filter_delta or 0
        self.mode = module.filter_mode or 0
        self.delay = module.filter_delay or 0
        self.shadow = module.filter_shadow or 0
        self.r_d417 = 0     # init's $d400-$d41c wipe DOES clear the register,
                            # even though it leaves the shadow alone


class _V:
    """Per-voice player state, named after the addresses it transcribes."""

    __slots__ = (
        'order_ptr', 'order_idx', 'pat_ptr', 'pat_idx', 'cur_note', 'vib_depth',
        'cmd', 'ad', 'sr', 'freq_hi', 'freq_lo', 'pulse_lo', 'pulse_hi',
        'waveform', 'new_pattern', 'slide_cmd', 'slide_dir', 'slide_amt',
        'vib_done', 'pulse_step', 'pulse_frames', 'abs_freq', 'pending_note',
        'vib_ctr', 'pulse_cur', 'vib_inc', 'vib_limit', 'legato', 'prev_mode',
        'mode', 'wave_freeze', 'note_latched', 'transpose', 'gate_mask',
        'halted', 'vib_phase2', 'pulse_dir', 'wave_cur', 'note_pending',
        'vib_delay', 'vib_reload', 'duration', 'instr', 'prev_instr', 'active',
        'vib_dir', 'r_freq', 'r_pulse', 'r_wf', 'r_ad', 'r_sr', 'started',
    )

    def __init__(self, order_ptr: int, sentinel: int, seed=None):
        # -- power-on state: the saved module image, where it is knowable -----
        for i, name in enumerate(_RAM):
            if name is not None:
                setattr(self, name, seed(i) if seed else 0)
        self.cur_note = seed('cur_note') if seed else 0     # $1007
        self.vib_depth = seed('vib_depth') if seed else 0   # $101c
        # -- init ($109d-$10d5) overwrites this much of it --------------------
        self.order_ptr = order_ptr
        self.order_idx = 0          # $1016
        self.pat_idx = 0            # $1019
        self.note_pending = 0       # $16f5
        self.halted = False         # $16e9
        self.transpose = 0          # $16e3
        self.note_latched = 0       # $16dd
        self.instr = 0              # $1701
        self.pat_ptr = sentinel     # $1010/$1013 -> a hardcoded $FF in the player
        self.gate_mask = 0xFE       # $16e0
        self.prev_instr = 1         # $1704
        self.wave_freeze = 1        # $16d4
        self.duration = 1           # $1707
        # -- the SID registers themselves, zeroed by init's $D400-$D41C loop
        self.r_freq = self.r_pulse = self.r_wf = self.r_ad = self.r_sr = 0
        self.started = False


def simulate_registers(module: HardTrackModule, subtune: int = 0,
                       frames: int = 1000) -> list[list[VoiceFrame]]:
    """The three voices' registers. See `simulate_all` for the filter as well."""
    return simulate_all(module, subtune, frames)[0]


def simulate_all(module: HardTrackModule, subtune: int = 0, frames: int = 1000
                 ) -> tuple[list[list[VoiceFrame]], list[FilterFrame]]:
    """Run the whole play routine. -> (frames[f][voice], frames[f]) .

    The second list is the filter, which is global rather than per-voice and so
    cannot live inside a `VoiceFrame`. It is empty when the filter engine did
    not match its signatures -- an empty list scores nothing, where a
    full-length list of zeroes would score a confident 100% against a tune that
    never filters.

    Raises `HardTrackError` when the file's program tables were not located,
    rather than running the engine against address 0 and returning a full-length
    series of confident-looking zeroes.
    """
    if module.wave_table is None or module.arp_table is None:
        raise HardTrackError(
            'waveform/arpeggio program table not located -- the synth engine '
            'cannot be modelled for this file')
    if module.pulse_table is None:
        raise HardTrackError(
            'pulse-sweep program table not located -- the synth engine cannot '
            'be modelled for this file')

    b = module.byte
    base, stride = module.instrument_base, module.num_instruments

    def field(k: int, n: int) -> int:
        return b(base + k * stride + n)

    def flags(n: int) -> int:
        """Field 5 read through the signature-derived address when there is one."""
        return b(module.flag_table + n) if module.flag_table is not None \
            else field(F_FLAGS, n)

    # $1010/$1013 are pointed at a hardcoded $FF byte inside the player, so the
    # first duration expiry falls straight through into the orderlist fetch.
    # Any address whose byte is $FF will do; the pattern-end path resets it.
    sentinel = module.load + module.data.find(b'\xff') if b'\xff' in module.data \
        else module.load

    ram = ram_layout_base(module)
    # $1007 / $101c are in the module header's runtime-state area, not the
    # per-voice block; $1007 is the operand _SIG_FREQ's `lda note,x` reads.
    hdr = {'cur_note': module.load + 0x07, 'vib_depth': module.load + 0x1C}

    def seeded(v: int):
        def seed(key):
            a = hdr[key] if isinstance(key, str) else _ram_addr(ram, key)
            return b(a + v)
        return seed

    voices = [_V(module.order_pointer(v, subtune), sentinel,
                 seeded(v) if ram is not None else None) for v in range(3)]
    filt = _F(module)
    speed = module.speed(subtune)
    ctr = 2                                     # init leaves $1100 at 2

    out: list[list[VoiceFrame]] = []
    fout: list[FilterFrame] = []
    for _ in range(frames):
        ctr -= 1                                # $10e3
        if ctr < 0:
            ctr = speed
        # $10ed `ldx #$02` down to $1583 `dex / bmi`: voice 2 first, voice 0
        # last. Immaterial for the per-voice registers, decisive for the
        # filter -- three note-ons on one frame write the same operands and the
        # last voice stepped is the one that survives into $d416/$d417/$d418.
        for vi in (2, 1, 0):
            _step(module, voices[vi], ctr, b, field, flags, filt, vi)
        out.append([
            VoiceFrame(v.r_freq, v.r_pulse, v.r_wf, v.r_ad, v.r_sr,
                       v.instr, v.cur_note,
                       bool(flags(v.instr) & 0x80), v.started)
            for v in voices
        ])
        if filt.located:
            _step_filter(module, filt, b)       # $1589, once, after the loop
            fout.append(FilterFrame(filt.acc, filt.r_d417,
                                    filt.mode | module.filter_volume))
    return out, fout


def _step_filter(module, f: _F, b) -> None:
    """$1589 -- the cutoff sweep. Runs once per frame, after all three voices."""
    f.delay = (f.delay - 1) & 0xFF                      # $1589 DEC
    if f.delay == 0:                                    # $158c BNE -> skip
        y = f.cursor
        for _ in range(_JUMP_GUARD):
            y = f.cursor                                # $158e LDY #cur
            f.cursor = (f.cursor + 1) & 0xFF            # $1590 INC curop
            val = b(module.filter_table + y)            # $1593
            if val != 0x80:                             # $1596 CMP #$80
                break
            # $159a: the jump target overwrites the INC that just happened
            f.cursor = b(module.filter_table + ((y + 1) & 0xFF))
        else:
            val = 0
        f.delta = val                                   # $15a4
        f.cursor = (f.cursor + 1) & 0xFF                # $15a8 INC curop
        f.delay = b(module.filter_table + ((y + 1) & 0xFF))     # $15ae
    # $15b1: CLC/ADC into an 8-bit operand, no clamp -- it wraps by design.
    f.acc = (f.acc + f.delta) & 0xFF



def _arm_filter(v: _V, vi: int, n: int, f: _F, field, flags) -> None:
    """$137d -- re-seed the filter envelope from instrument `n` at note-on.

    Field 5 bit 4 is NOT a hard restart, despite the parser's name for it. Its
    only consumer is the guard here, and it means "on a repeated note, leave
    the filter envelope running" -- it reaches nothing else in the player, so
    implementing it as a general restart would retrigger envelopes the original
    holds.
    """
    if (flags(n) & 0x10) and v.instr == v.prev_instr:       # $137d / $1384
        return
    f12 = field(F_FILTER, n)                                # $138f
    if not f12:
        # $13cb -- not "no filter for this note" but "switch this voice OUT".
        f.shadow &= f.masks[vi]
        f.r_d417 = f.shadow
        return
    f.mode = (f12 & 0x0F) << 4                              # $1395 -> $d418
    f.shadow = (f.shadow & 0x0F) | (f12 & 0xF0) | f.bits[vi]     # $139f-$13aa
    f.r_d417 = f.shadow                                     # $13ad / $13b0
    f.acc = field(F_FILTCUT, n)                             # $13b3 initial cutoff
    f.cursor = field(F_FILTPROG, n)                         # $13b9 program cursor
    f.delta = 0                                             # $13bf
    f.delay = 3                                             # $13c4


def _step(module, v: _V, ctr: int, b, field, flags, filt, vi) -> None:  # noqa: C901
    """One voice, one frame. `label` tracks the player's own control flow."""
    if v.halted:                                            # $10ef
        return
    if v.note_pending:                                      # $10f7
        label = 'pend'
    elif ctr == 0:                                          # $10ff
        label = 'row'
    elif ctr == 1:
        label = 'dur'
    else:
        label = 'trigger'

    for _ in range(4096):                                   # flow guard
        # -- $110d: read one pattern row -------------------------------------
        if label == 'row':
            if not v.active:                                # $1110
                label = 'synth'
                continue
            v.duration = 1                                  # $111f
            y = v.pat_idx                                   # $1124
            c = v.cmd
            if c == CMD_TIE:                                # $112a
                label = 'instr_byte'
            elif c == CMD_GATE_OFF:                         # $1131
                v.gate_mask = 0xFE
                label = 'instr_byte'
            elif c == CMD_RESET:                            # $113d
                v.waveform = 0
                v.sr = 0
                v.wave_freeze = 1
                label = 'instr_byte'
            elif c in (CMD_SLIDE, CMD_PORTA):               # $1151 / $1168
                v.slide_cmd = c
                v.slide_dir = 0 if c == CMD_SLIDE else c
                v.pat_idx += 1
                v.slide_amt = b(v.pat_ptr + y)
                label = 'synth'
            elif c == CMD_REST:                             # $117d
                v.active = 0
                v.pat_idx += 1
                v.duration = b(v.pat_ptr + y)
                label = 'synth'
            else:                                           # $1191
                v.pending_note = c & 0x7F
                v.note_pending = c & 0x7F
                label = 'instr_byte'
            continue

        # -- $1199: the instrument byte --------------------------------------
        if label == 'instr_byte':
            y = v.pat_idx
            v.pat_idx += 1
            a = b(v.pat_ptr + y)
            if a == INSTR_HOLD:                             # $11a1
                v.legato = 0
                label = 'check_note'
            elif a == INSTR_LEGATO:                         # $11a3
                v.legato = a
                label = 'synth'
            else:                                           # $11ad
                v.prev_instr = v.instr
                v.instr = a & 0x1F
                v.legato = 0
                label = 'check_note'
            continue

        # -- $11bf: gate handling on an instrument mode change ---------------
        if label == 'check_note':
            if not v.note_pending:
                label = 'synth'
                continue
            v.prev_mode = v.mode                            # $11d0
            v.mode = flags(v.instr) & 0x03
            if v.prev_mode != 2:                            # $11da
                v.gate_mask = 0xFE
                label = 'synth'
            else:                                           # $11e9
                v.r_sr = 0
                v.r_wf = v.waveform & 0xFE
                return
            continue

        # -- $11fc: note duration --------------------------------------------
        if label == 'dur':
            v.duration -= 1
            if v.duration != 0:
                label = 'synth'
                continue
            label = 'order'
            continue

        # -- $1204: next row, and the orderlist walk when the pattern ends ---
        if label == 'order':
            v.new_pattern = 0
            v.active = 1
            y = v.pat_idx
            v.pat_idx += 1
            a = b(v.pat_ptr + y)
            if a != PATTERN_END:                            # $1220
                v.cmd = a
                label = 'trigger'
                continue
            v.pat_idx = 0                                   # $122a
            for _ in range(512):                            # $1239
                y = v.order_idx
                v.order_idx += 1
                a = b(v.order_ptr + y)
                if a < 0x80:
                    break
                if a == ORDER_END:
                    v.new_pattern = a
                    v.order_idx = 0
                    continue
                if a == ORDER_HOLD:                         # $1251
                    v.halted = True
                    return
                if a == ORDER_JUMP:                         # $125d
                    v.new_pattern = a
                    v.order_idx = b(v.order_ptr + y + 1)
                    continue
                v.transpose = a & 0x7F                      # $1270
                v.order_idx += 1
                a = b(v.order_ptr + y + 1)
                break
            else:
                v.halted = True
                return
            v.pat_ptr = module.pattern_pointer(a)           # $127b
            v.pat_idx += 1                                  # $128e
            v.cmd = b(v.pat_ptr)
            if v.new_pattern:                               # $1296
                return
            label = 'trigger'
            continue

        # -- $12a1: latch the note, load the vibrato parameters --------------
        if label == 'pend':
            v.note_latched = 1
            v.note_pending = 0
            n = v.instr
            f8 = field(F_VIBRATO, n)                        # $12ae
            v.vib_ctr = v.vib_reload = f8 & 0x0F
            v.vib_phase2 = 1
            v.vib_delay = (f8 & 0xF0) >> 3
            v.vib_depth = field(F_VIBDEPTH, n)              # $12c8
            v.vib_inc = field(F_VIBINC, n)
            v.vib_limit = field(F_VIBLIMIT, n)
            if v.legato:                                    # $12da
                label = 'synth'
                continue
            if not v.prev_mode:                             # $12e2
                label = 'synth'
                continue
            v.r_sr = 0                                      # $12ea
            v.r_wf = v.waveform & 0xFE
            return

        # -- $12fd: the note-on itself, two frames after the row -------------
        if label == 'trigger':
            if not v.note_latched or not v.active:
                label = 'synth'
                continue
            v.note_latched = 0                              # $130a
            v.vib_dir = 0
            v.vib_done = 0
            v.slide_cmd = 0
            v.gate_mask = 0xFF
            v.cur_note = (v.pending_note + v.transpose) & 0x7F
            v.freq_hi = b(module.freq_hi_table + v.cur_note)
            v.freq_lo = b(module.freq_lo_table + v.cur_note)
            v.started = True
            if v.legato:                                    # $1336
                label = 'synth'
                continue
            n = v.instr                                     # $133e
            v.ad = field(F_AD, n)
            v.sr = field(F_SR, n)
            v.abs_freq = flags(n) & 0x80
            p = field(F_PULSE, n)                           # $1355
            v.pulse_hi = p & 0x0F
            v.pulse_lo = p & 0xF0
            v.wave_cur = field(F_WAVECUR, n)                # $1364
            v.pulse_cur = field(F_PULSECUR, n)
            v.wave_freeze = 0                               # $1370
            v.pulse_step = 0
            v.pulse_frames = 2
            if filt.located:
                _arm_filter(v, vi, n, filt, field, flags)    # $137d..$13d4
            v.r_sr = v.sr                                   # $13d7
            v.r_ad = v.ad
            v.r_wf = 0x09
            return

        # -- $13ee: the pulse-width sweep ------------------------------------
        if label == 'synth':
            v.pulse_frames = (v.pulse_frames - 1) & 0xFF
            if v.pulse_frames == 0:
                for _ in range(_JUMP_GUARD):                # $13f3
                    y = v.pulse_cur
                    v.pulse_cur = (v.pulse_cur + 1) & 0xFF
                    val = b(module.pulse_table + y)
                    if val != 0xFF:
                        break
                    v.pulse_cur = b(module.pulse_table + y + 1)
                else:
                    val = 0
                v.pulse_step = val & 0xFE                   # $140a
                v.pulse_dir = val & 0x01
                v.pulse_cur = (v.pulse_cur + 1) & 0xFF
                v.pulse_frames = b(module.pulse_table + y + 1)
            a = v.pulse_lo                                  # $1420
            if v.pulse_dir:
                a -= v.pulse_step
                v.pulse_lo = a & 0xFF
                if a < 0:
                    v.pulse_hi = (v.pulse_hi - 1) & 0xFF
            else:
                a += v.pulse_step
                v.pulse_lo = a & 0xFF
                if a > 0xFF:
                    v.pulse_hi = (v.pulse_hi + 1) & 0xFF
            label = 'wave'
            continue

        # -- $1454: the waveform / arpeggio program --------------------------
        if label == 'wave':
            if v.wave_freeze:                               # $144f
                label = 'slidevib'
                continue
            for _ in range(_JUMP_GUARD):
                y = v.wave_cur
                v.wave_cur = (v.wave_cur + 1) & 0xFF
                wf = b(module.wave_table + y)
                if wf != 0xFF:
                    break
                v.wave_cur = b(module.arp_table + y)        # $1461
            else:
                wf = 0xFE
            if wf == 0xFE:                                  # $146a
                v.wave_freeze = (v.wave_freeze - 1) & 0xFF
                label = 'slidevib'
                continue
            v.waveform = wf                                 # $1474
            arp = b(module.arp_table + y)
            if v.abs_freq:                                  # $1497
                v.freq_hi = arp
                v.freq_lo = 0
            else:
                # $147c: arp $80+ is an ABSOLUTE note, below it a relative
                # semitone added to the sounding note.
                n = arp if arp & 0x80 else arp + v.cur_note
                n &= 0x7F
                v.freq_hi = b(module.freq_hi_table + n)
                v.freq_lo = b(module.freq_lo_table + n)
            label = 'out'
            continue

        # -- $14a5: slide / portamento, else vibrato -------------------------
        if label == 'slidevib':
            if v.slide_cmd:
                if v.slide_dir:                             # $14c7 -- down
                    a = v.freq_lo - v.slide_amt
                    v.freq_lo = a & 0xFF
                    if a < 0:
                        v.freq_hi = (v.freq_hi - 1) & 0xFF
                else:                                       # $14af -- up
                    a = v.freq_lo + v.slide_amt
                    v.freq_lo = a & 0xFF
                    if a > 0xFF:
                        v.freq_hi = (v.freq_hi + 1) & 0xFF
                label = 'out'
                continue
            if v.vib_delay:                                 # $14df
                v.vib_delay -= 1
                label = 'out'
                continue
            if v.vib_dir:                                   # $153b -- up
                a = v.freq_lo + v.vib_depth
                v.freq_lo = a & 0xFF
                if a > 0xFF:
                    v.freq_hi = (v.freq_hi + 1) & 0xFF
            else:                                           # $14ef -- down
                a = v.freq_lo - v.vib_depth
                v.freq_lo = a & 0xFF
                if a < 0:
                    v.freq_hi = (v.freq_hi - 1) & 0xFF
            v.vib_ctr = (v.vib_ctr - 1) & 0xFF              # $14fb
            if v.vib_ctr == 0:
                v.vib_ctr = v.vib_reload                    # $1500
                v.vib_phase2 = (v.vib_phase2 - 1) & 0xFF
                if v.vib_phase2 == 0:
                    v.vib_phase2 = 2                        # $150b
                    if not v.vib_done:
                        v.vib_depth = (v.vib_depth + v.vib_inc) & 0xFF
                        if v.vib_depth >= v.vib_limit:
                            v.vib_done = (v.vib_done - 1) & 0xFF
                    v.vib_dir ^= 0xFF                       # $1527
            label = 'out'
            continue

        # -- $1553: write the SID registers ----------------------------------
        if label == 'out':
            v.r_pulse = ((v.pulse_hi & 0x0F) << 8) | v.pulse_lo
            v.r_freq = (v.freq_hi << 8) | v.freq_lo
            v.r_ad = v.ad
            v.r_sr = v.sr
            v.r_wf = v.waveform & v.gate_mask
            return

        raise AssertionError(f'unreachable label {label!r}')

    raise HardTrackError('synth engine did not settle within one frame')
