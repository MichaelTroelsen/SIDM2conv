"""Stage A — map a flattened Galway 1st-gen tune onto SID Factory II Driver 11
tables, producing an editable + playable (sound-approximated) SF2.

Design spec: ``docs/analysis/GALWAY_TO_DRIVER11_MAPPING.md``. Parent plan:
``docs/analysis/GALWAY_SF2_DRIVER_PLAN.md``.

This module is **pure data** — it turns the extractor's output
(``GalwayChannelState`` + flattened ``GalwayEvent`` voices + ``GalwayInstrument``
list, all from ``sidm2.galway_1stgen_extractor``) into a ``GalwayDriver11Song``
intermediate representation. Serialising that IR into a Driver 11 ``.sf2`` (via
``SF2Writer`` / ``driver11_section_injectors``) is a later Stage A1 step; keeping
the IR separate makes the mapping unit-testable without the C64 emission path.

Empirically (probe over Wizball/Terra/Commando/Parallax, 2026-05-29):
  * Galway's ``LoFrq/HiFrq`` tables are the standard PAL frequency table at the
    SAME note indices → pitch BASE is 0 (we still calibrate + assert per file).
  * Raw stream duration bytes are already musical frame counts (Wizball
    ``[4,6,8,12,16,24,32]``), so a GCD-derived row clock reproduces the rhythm
    without needing to resolve the player's IDRT table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import gcd
from typing import Dict, List, Optional, Tuple

from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI
from sidm2.galway_1stgen_extractor import (
    GalwayChannelState, GalwayEvent, GalwayInstrument,
    flatten_all_channels, extract_instruments,
)

# Standard PAL frequency table, C-0 .. B-7 (96 semitones).
_PAL_FREQ: List[int] = [FREQ_TABLE_LO[i] | (FREQ_TABLE_HI[i] << 8)
                        for i in range(96)]

# Driver 11 sequence note column (authoritative: SF2II datasource_sequence.cpp):
#   $00 = note off ('---'), $01-$6F = notes, $7E = note on / sustain ('+++'),
#   $7F = end of sequence. So a playable note byte = galway_index + 1 (index 0
#   maps to $01; $00 is reserved for note-off).
SF2_NOTE_MIN = 0x01
SF2_NOTE_MAX = 0x6F
SF2_GATE_ON = 0x7E   # '+++' note-on / sustain row
SF2_GATE_OFF = 0x00  # '---' note-off / rest row

# Normalised gate-on waveform bytes by dominant SID waveform bit.
_WAVE_GATE_ON = {0x10: 0x11, 0x20: 0x21, 0x40: 0x41, 0x80: 0x81}

# Sensible bounds for the derived row clock and per-note row counts so a stray
# huge/zero raw duration can't produce a degenerate pattern.
_TICK_MIN, _TICK_MAX = 1, 8
_ROWS_MAX = 64


# ---------------------------------------------------------------------------
# Driver 11 song intermediate representation
# ---------------------------------------------------------------------------

@dataclass
class D11Instrument:
    """One Driver 11 instrument row (column-major [AD,SR,Flags,Filter,Pulse,
    Wave]) plus the single wave-table row index it points at."""
    ad: int
    sr: int
    flags: int
    filter_idx: int
    pulse_idx: int
    wave_idx: int


@dataclass
class D11Row:
    """One sequence row. ``instrument`` / ``command`` are None when unchanged
    (the packer emits the $80 'no change' marker)."""
    note: int                       # SF2 note byte, $7E (+++), or $80 (---)
    instrument: Optional[int] = None
    command: Optional[int] = None
    tie: bool = False               # '**' tie marker (no retrigger)


# Default pulse program (Driver 11.00, 3 cols): set pulse to $800 (50% duty —
# a full square wave) for 1 frame, then jump back, holding it. Without this a
# pulse ($41) voice has width $000 and is SILENT — which is why Galway's
# pulse-heavy leads produced no sound until this was added. Format:
# [$8X, XX, frames] = set pulse $X·XX; [$7F, --, target] = jump.
DEFAULT_PULSE_PROGRAM: List[Tuple[int, int, int]] = [
    (0x88, 0x00, 0x01),    # set pulse $800 for 1 frame -> advance
    (0x7F, 0x00, 0x00),    # jump back to row 0
]


@dataclass
class GalwayDriver11Song:
    """Driver 11 song IR produced from a Galway tune."""
    instruments: List[D11Instrument] = field(default_factory=list)
    wave_table: List[Tuple[int, int]] = field(default_factory=list)  # (wf,note-off)/(7F,jmp)
    pulse_table: List[Tuple[int, int, int]] = field(default_factory=list)
    tracks: List[List[D11Row]] = field(default_factory=list)         # 3 voices, flat rows
    tempo: int = 4                  # frames per row (TICK)
    pitch_base: int = 0
    subtune: int = 0

    @property
    def note_count(self) -> int:
        return sum(1 for t in self.tracks for r in t
                   if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX)


# ---------------------------------------------------------------------------
# Pitch calibration
# ---------------------------------------------------------------------------

def _nearest_pal(freq: int) -> Tuple[int, int]:
    best, bi = 1 << 30, -1
    for i, f in enumerate(_PAL_FREQ):
        d = abs(freq - f)
        if d < best:
            best, bi = d, i
    return bi, best


def calibrate_pitch_base(ram, lofrq_addr: int, hifrq_addr: int,
                         tol: int = 8) -> int:
    """Determine the constant offset between Galway note indices and SF2 note
    bytes by matching the file's LoFrq/HiFrq entries to the standard PAL table.

    Returns the modal ``(pal_index - galway_index)`` offset (0 for every file
    probed so far). Falls back to 0 if no entries match within ``tol``.
    """
    from collections import Counter
    offs = Counter()
    for i in range(90):
        f = ram[(lofrq_addr + i) & 0xFFFF] | (ram[(hifrq_addr + i) & 0xFFFF] << 8)
        if f == 0:
            continue
        ni, dist = _nearest_pal(f)
        if dist < tol:
            offs[ni - i] += 1
    return offs.most_common(1)[0][0] if offs else 0


# ---------------------------------------------------------------------------
# Tempo / duration
# ---------------------------------------------------------------------------

def derive_tick(durs: List[int]) -> int:
    """Pick a frames-per-row clock = GCD of the *common* durations, bounded to
    [_TICK_MIN, _TICK_MAX].

    A plain GCD is fragile: a single odd duration (Wizball has a lone ``3`` and
    a couple of ``5``/``9`` among hundreds of ``4``/``6``/``8``/``12``/``32``)
    would collapse it to 1 and explode every pattern. So we only fold a duration
    into the GCD if it occurs often enough (>= 2% of events and at least twice),
    which keeps the musical base unit (Wizball/Terra -> 2; Commando, a genuinely
    fast tune dominated by 1s and 2s, -> 1).
    """
    from collections import Counter
    hist = Counter(d for d in durs if _TICK_MIN <= d <= 0x40)
    if not hist:
        return 4
    total = sum(hist.values())
    threshold = max(2, total * 0.02)
    common = [d for d, n in hist.items() if n >= threshold]
    if not common:                       # all durations are rare → use them all
        common = list(hist)
    g = 0
    for v in common:
        g = gcd(g, v)
    return max(_TICK_MIN, min(g or 1, _TICK_MAX))


def _dur_to_rows(dur: int, tick: int) -> int:
    frames = dur if dur > 0 else tick      # treat 0 as one row
    rows = round(frames / tick)
    return max(1, min(rows, _ROWS_MAX))


# ---------------------------------------------------------------------------
# Instruments + wave table
# ---------------------------------------------------------------------------

def _norm_waveform(ctrl: int) -> int:
    """Map a Galway VWF control byte to a gate-on Driver 11 waveform byte,
    picking the dominant waveform bit (pulse > saw > tri > noise priority is
    arbitrary; most Galway leads are pulse/saw)."""
    for bit in (0x40, 0x20, 0x10, 0x80):
        if ctrl & bit:
            return _WAVE_GATE_ON[bit]
    return 0x41                              # default pulse+gate


def _pulse_program(width: int, base_row: int) -> List[Tuple[int, int, int]]:
    """A 2-row Driver 11.00 pulse program: set a 12-bit pulse `width` and hold.
    `base_row` is this program's own first row (the jump target)."""
    w = width & 0x0FFF
    if w < 0x100:            # PINIT this thin is meant to be PWM-swept; a static
        w = 0x800            # value would be near-silent, so use a neutral 50%.
    return [(0x80 | ((w >> 8) & 0x0F), w & 0xFF, 0x01),   # set pulse, 1 frame
            (0x7F, 0x00, base_row)]                       # jump back


def build_instruments(
    instruments: List[GalwayInstrument],
) -> Tuple[List[D11Instrument], List[Tuple[int, int]],
           List[Tuple[int, int, int]], Dict[int, int]]:
    """Build Driver 11 instrument rows + wave table + pulse table, and return the
    ``GalwayInstrument.ptr -> instrument index`` map used to resolve the
    sequence instrument column.

    Each instrument gets: one wave program (``[waveform,$00]`` then ``[$7F,loop]``)
    and its own pulse program set from the instrument's PINIT pulse width — so
    pulse voices aren't silent AND distinct instruments keep distinct timbres
    (a uniform width made them all sound like the same square wave). Flags $80 =
    hard-restart enable (Galway has no Driver 11 flag concept).
    """
    instr_rows: List[D11Instrument] = []
    wave_table: List[Tuple[int, int]] = []
    pulse_table: List[Tuple[int, int, int]] = []
    ptr_to_idx: Dict[int, int] = {}

    for gi in instruments[:32]:              # Driver 11 has 32 instrument slots
        wave_row = len(wave_table)
        wave_table.append((_norm_waveform(gi.ctrl), 0x00))
        wave_table.append((0x7F, wave_row))  # loop on the single waveform
        pulse_row = len(pulse_table)
        pulse_table.extend(_pulse_program(gi.pinit or 0x800, pulse_row))
        idx = len(instr_rows)
        instr_rows.append(D11Instrument(
            ad=gi.ad, sr=gi.sr, flags=0x80,
            filter_idx=0x00, pulse_idx=pulse_row, wave_idx=wave_row,
        ))
        ptr_to_idx[gi.ptr] = idx

    if not instr_rows:                       # no instruments extracted → default
        wave_table = [(0x41, 0x00), (0x7F, 0x00)]
        pulse_table = list(DEFAULT_PULSE_PROGRAM)
        instr_rows = [D11Instrument(0x09, 0x00, 0x80, 0, 0, 0)]
    return instr_rows, wave_table, pulse_table, ptr_to_idx


# ---------------------------------------------------------------------------
# Sequences (per voice)
# ---------------------------------------------------------------------------

def build_track(events: List[GalwayEvent], ptr_to_idx: Dict[int, int],
                base: int, tick: int) -> List[D11Row]:
    """Convert one flattened voice into Driver 11 sequence rows.

    Note event -> a note row (instrument set if it changed) + (rows-1) '+++'
    sustain rows. Rest -> 'rows' '---' rows. Tie notes carry the '**' marker.
    Instrument/code/end/desync events update state or terminate.
    """
    rows: List[D11Row] = []
    cur_instr: Optional[int] = None
    pending_instr: Optional[int] = None      # set by instr/fload, applied to next note

    for e in events:
        if e.kind in ('instr', 'fload'):
            if e.value in ptr_to_idx:
                pending_instr = ptr_to_idx[e.value]
            continue
        if e.kind == 'note':
            # +1: note byte $01 is the lowest note ($00 = note-off).
            note = max(SF2_NOTE_MIN, min(e.pitch + base + 1, SF2_NOTE_MAX))
            inst = None
            if pending_instr is not None and pending_instr != cur_instr:
                inst = pending_instr
                cur_instr = pending_instr
            pending_instr = None
            rows.append(D11Row(note=note, instrument=inst, tie=e.tie))
            for _ in range(_dur_to_rows(e.dur, tick) - 1):
                rows.append(D11Row(note=SF2_GATE_ON))
        elif e.kind == 'rest':
            for _ in range(_dur_to_rows(e.dur, tick)):
                rows.append(D11Row(note=SF2_GATE_OFF))
        elif e.kind == 'code':
            # Inline native code (an effect we can't represent in tables) —
            # skip it but keep transcribing the rest of the voice. Galway tunes
            # interleave the occasional Code with a long melody; breaking here
            # would discard everything after it.
            continue
        elif e.kind in ('end', 'desync'):
            break                        # clean end, or flatten lost sync (terminal)
    return rows


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

def galway_to_driver11(state: GalwayChannelState) -> GalwayDriver11Song:
    """Build a Driver 11 song IR from a recovered Galway channel state.

    Raises nothing for empty voices; the caller decides (via
    ``GalwayDriver11Song.note_count``) whether the result is usable or should
    fall back to the embed path.
    """
    voices, _ = flatten_all_channels(state)
    instruments = extract_instruments(state.ram, voices)

    base = calibrate_pitch_base(state.ram, state.layout.lofrq_addr,
                                state.layout.hifrq_addr)
    all_durs = [e.dur for v in voices for e in v if e.kind in ('note', 'rest')]
    tick = derive_tick(all_durs)

    instr_rows, wave_table, pulse_table, ptr_to_idx = build_instruments(instruments)
    tracks = [build_track(v, ptr_to_idx, base, tick) for v in voices]

    return GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table,
        pulse_table=pulse_table, tracks=tracks,
        tempo=tick, pitch_base=base, subtune=state.subtune,
    )
