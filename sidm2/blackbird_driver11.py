"""Stage A -- map a decoded Blackbird (Linus Åkesson / "lft") song onto SID
Factory II Driver 11 tables, producing a real, editable + playable SF2, via
the SHARED Stage-A IR (``GalwayDriver11Song``/``D11Row``/``D11Instrument``
from ``galway_to_driver11.py``) and the shared emitter
(``galway_driver11_emitter.emit_driver11_sf2``) -- neither of those modules
is modified here, per ``docs/players/PLAYBOOK.md``'s "Stage A is cheap once
the parser exists" method (section 1/6).

Builds on ``sidm2.blackbird_parser`` (locate + decompression, shipped
2026-07-19 -- see ``docs/players/BLACKBIRD.md``). This module adds the
Stage-A-specific note/timing decisions; the compression/scheduling work is
entirely reused, not reimplemented.

## Tick model (Phase 1 finding, this session)

``blackbird_parser.decode_streams()``'s ``frame`` loop-iteration counter is
NOT a 1:1 real-PAL-frame count. Empirically confirmed against both live-CPU
ground-truth captures (``SID/blackbird_fargo_trace_4199_5371.json``,
``SID/blackbird_glyptodont_trace_4248_5026.json``): pieces sharing the SAME
iteration value are always exactly 1 real frame apart (11/11 and matching
pairs in Glyptodont), while pieces in DIFFERENT iterations show
real-frame-delta / iteration-delta ratios clustering at 3-10 (mean ~6.0 for
Fargo) -- exactly the documented tempo/groove range (5, 6, 7 real frames per
cycle; see BLACKBIRD.md's tempo section). Reading ``player.s`` directly
explains why: ``prepare1``/``prepare2``/``prepare3`` (the note-event fetch
pipeline) are dispatched ONLY from ``unpackvoice``'s tail (``preparejmp``),
which is itself only reachable on the (up to 3) real frames per cycle where
the ``zp_master`` countdown lands on 14/7/0 -- so each stage runs EXACTLY
ONCE per ``execute()``-to-``execute()`` cycle, i.e. one
``decode_streams()`` loop iteration = one TICK (one full cycle), not one
real frame. A tick's real-frame length is ``zp_tempo / 7`` (the alternating
pair) -- a separate, coarser concept from the tick grid itself. See
``docs/players/BLACKBIRD.md``'s Phase-1 addendum for the full derivation
and the reproducible cross-check script.

The practical payoff: ticks are already the note grid Blackbird composes
on, and a Driver 11 row is also a fixed-tick grid -- so no real-frame
simulation is needed to get note order/duration right for Stage A. A tick
IS a Driver-11 row (1:1, no GCD rounding). Each decoded note/delay byte's
own duration in ticks is recovered directly from ``player.s``'s own
``v_trtimer`` preload arithmetic (``prepare3``'s ``got_delay: ora #$f0``):
a note byte's LSB delay-bit gives 1 tick (set) or 2 ticks (clear); a delay
byte's low nibble ``m`` gives ``16 - m`` ticks. No new decoding pass is
needed -- this reads straight off the already-decoded, already-tested byte
stream (``blackbird_parser``'s ``real_events``/``.real(voice)``).

## What's flat for Stage A (per PLAYBOOK.md's ladder: "notes/timing/
envelope exact; timbre modulation flat")

- Arpeggio (``$C9-$F8``) and OOB (``$F9-$FF``) bytes are consumed (to keep
  the byte walk in sync) but do not affect the emitted rows.
- Tempo: real Blackbird tempo ALTERNATES between two values and CHANGES
  several times per song (BLACKBIRD.md documents 22 tempo records in
  Fargo alone). Driver 11's tempo table supports a repeating 2-value
  CHAIN -- the same mechanism this codebase already uses for Deenen's
  fractional-average tempo (see ``galway_to_driver11.GalwayDriver11Song
  .tempo`` docstring) -- which maps naturally onto Blackbird's own
  alternation. This module extracts the FIRST tempo/groove OOB pair
  actually present in the compressed stream and uses it as a single
  song-wide chain; LATER tempo changes are not tracked. This is a real,
  named Stage-A limitation, not silently assumed away.
- Pitch: **calibrated and empirically verified** (fixed after a user listen
  test reported the first build sounding ~an octave flat). ``player.s``
  (~line 435-439) shows ``v_basepitch,x = note << 2`` (multiply by 4), fed
  into a fractional-interpolation routine (~line 221-267) that decomposes
  the sum back into a table index ``y`` plus a 2-bit slide-phase selector;
  for the no-slide case (phase ``00``, the steady-state landing pitch) it
  reads ``freq_lsb+24,y`` / ``freq_msb+24,y`` with ``y = note`` directly
  (NOT ``note*4`` -- the ``*4``/interpolation machinery is for smooth
  arpeggio/portamento *between* notes, the steady pitch is a flat ``+24``
  offset lookup). Comparing the actual ``freq_lsb``/``freq_msb`` table
  bytes (extracted from the compiled template) against this project's
  standard PAL frequency table confirms, with ZERO mismatches across the
  full 0-63 note-index range: ``PAL_semitone_index = note_index + 8``, so
  ``SF2 note = note_index + 9`` (not ``+1``). The interpolation
  sub-positions themselves (mid-slide pitches) are still not modelled --
  only the steady-state landing pitch is calibrated -- so pitch *slides*
  will still be flat/instant rather than swept, but the resting note of
  every held tone should now be correct.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from sidm2.blackbird_parser import (
    classify_byte, decode_file, load_sid, locate_blackbird,
    _Reader, _Voice, _run_prep1, _run_prep2, _run_prep3, _emit_piece,
)
from sidm2.galway_to_driver11 import (
    GalwayDriver11Song, D11Instrument, D11Row,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    DEFAULT_PULSE_PROGRAM,
)

# Fallback frames/tick if the stream has no tempo OOB record at all (should
# not happen on a real song, but keeps this module total).
DEFAULT_TICK_FRAMES = 6


# ---------------------------------------------------------------------------
# Byte -> tick-duration arithmetic (ported straight from player.s's own
# v_trtimer preload, see module docstring "Tick model")
# ---------------------------------------------------------------------------
def _note_ticks(b: int) -> int:
    return 1 if (b & 1) else 2


def _delay_ticks(b: int) -> int:
    return 16 - (b & 0x0F)


# ---------------------------------------------------------------------------
# Per-voice byte stream -> steps -> Driver 11 rows
# ---------------------------------------------------------------------------
@dataclass
class BlackbirdStep:
    kind: str                       # 'note' | 'rest'
    note: Optional[int]             # raw 0-63 Blackbird note index, or None
                                     # for a 'note'-kind sustain/hold step
    instrument: Optional[int]
    tie: bool
    ticks: int


def steps_for_voice(byte_stream: bytes) -> List[BlackbirdStep]:
    """Group one decoded voice byte-stream (``blackbird_parser``'s
    ``real_events(voice)``/``.real(voice)``) into steps: zero-or-more
    prefix tokens (arp/oob ignored for Stage A; gate-off/legato/instrument
    tracked) followed by a mandatory note-or-delay terminal whose own raw
    byte value gives this step's tick duration -- see module docstring.
    """
    steps: List[BlackbirdStep] = []
    pending_instr: Optional[int] = None
    pending_tie = False
    gate_is_off = False           # sticky until the next real note
    had_note_yet = False

    for b in byte_stream:
        kind = classify_byte(b)
        if kind in ('oob', 'arp', 'unknown'):
            continue                          # Stage A: timbre/tempo flat
        if kind == 'instrument':
            # Blackbird allows up to 48 instruments (1-based, byte - 0x82);
            # Driver 11's instrument table has only 32 slots (PLAYBOOK.md's
            # hard-caps table). Clamp rather than let the packer's `& 0x1F`
            # silently ALIAS a high index onto an unrelated low slot.
            pending_instr = min(b - 0x82, 31)
            continue
        if kind == 'gate_off':
            gate_is_off = True
            continue
        if kind == 'legato':
            pending_tie = True
            gate_is_off = False
            continue
        if kind == 'note':
            note = b >> 1
            steps.append(BlackbirdStep('note', note, pending_instr,
                                        pending_tie, _note_ticks(b)))
            pending_instr = None
            pending_tie = False
            gate_is_off = False
            had_note_yet = True
            continue
        if kind == 'delay':
            ticks = _delay_ticks(b)
            if gate_is_off or not had_note_yet:
                steps.append(BlackbirdStep('rest', None, None, False, ticks))
            else:
                # Plain wait with no preceding gate-off/legato: extend
                # whatever is currently sounding (no retrigger).
                steps.append(BlackbirdStep('note', None, None, False, ticks))
            continue
    return steps


def steps_to_rows(steps: List[BlackbirdStep]) -> List[D11Row]:
    """Ticks map 1:1 onto Driver 11 rows -- no GCD/rounding needed (see
    module docstring "Tick model")."""
    rows: List[D11Row] = []
    cur_instr: Optional[int] = None
    for s in steps:
        n = max(1, s.ticks)
        if s.kind == 'rest':
            rows.extend(D11Row(note=SF2_GATE_OFF) for _ in range(n))
        elif s.kind == 'note' and s.note is None:
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(n))
        else:
            # SF2 note = note_index + 9, empirically calibrated against the
            # real freq_lsb/freq_msb table (see module docstring "Pitch").
            note = max(SF2_NOTE_MIN, min(s.note + 9, SF2_NOTE_MAX))
            inst = None
            if s.instrument is not None and s.instrument != cur_instr:
                inst = s.instrument
                cur_instr = s.instrument
            rows.append(D11Row(note=note, instrument=inst, tie=s.tie))
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(n - 1))
    if not rows:
        rows = [D11Row(note=SF2_GATE_OFF)]
    return rows


# ---------------------------------------------------------------------------
# Instruments (flat/default wave+pulse programs -- Stage A: timbre flat)
# ---------------------------------------------------------------------------
def build_instruments(d: bytes, la: int, lay) -> Tuple[
        List[D11Instrument], List[Tuple[int, int]], List[Tuple[int, int, int]]]:
    """Read AD/SR straight out of the located ``ins_ad``/``ins_sr`` tables
    (byte-exact -- these are plain data reads, no modelling involved).
    ``ins_wave``/``ins_filt`` index Blackbird's OWN looping wave/filter
    envelope engine, which Stage A does not model (timbre flat per the
    fidelity ladder) -- every instrument instead gets one flat default
    wave program (pulse + gate-on) so voices are audible and distinct only
    by AD/SR, not by waveform/filter envelope.
    """
    def rd(addr: int, i: int) -> int:
        off = addr - la + i
        return d[off] if 0 <= off < len(d) else 0

    # Blackbird allows up to 48 instruments (grammar docstring:
    # "$83-$B2 instrument select, 1-based, 48 max"); Driver 11's own
    # instrument table only has 32 slots (PLAYBOOK.md's hard-caps table)
    # -- cap here so every built row has a real, in-range slot rather than
    # relying on the sequence packer's `& 0x1F` mask (which would silently
    # ALIAS instrument 32+ onto an unrelated low instrument).
    nins = max(0, min(lay.nins, 32))
    instr_rows: List[D11Instrument] = []
    wave_table: List[Tuple[int, int]] = []
    pulse_table: List[Tuple[int, int, int]] = list(DEFAULT_PULSE_PROGRAM)

    for i in range(nins):
        ad = rd(lay.ins_ad, i)
        sr = rd(lay.ins_sr, i)
        wave_row = len(wave_table)
        wave_table.append((0x41, 0x00))       # flat pulse+gate-on waveform
        wave_table.append((0x7F, wave_row))   # loop on itself
        instr_rows.append(D11Instrument(
            ad=ad, sr=sr, flags=0x80,
            filter_idx=0x00, pulse_idx=0x00, wave_idx=wave_row,
        ))

    if not instr_rows:
        wave_table = [(0x41, 0x00), (0x7F, 0x00)]
        instr_rows = [D11Instrument(0x09, 0x00, 0x80, 0, 0, 0)]
    return instr_rows, wave_table, pulse_table


# ---------------------------------------------------------------------------
# Tempo: recover the FIRST real tempo/groove OOB pair from the compressed
# stream (song-wide single chain -- see module docstring's named limitation)
# ---------------------------------------------------------------------------
def extract_tempo_pairs(d: bytes, la: int, streamstart: int,
                        max_pairs: int = 4,
                        max_frames: int = 200_000,
                        variant: str = 'v1.2') -> List[Tuple[int, int]]:
    """Re-run ``blackbird_parser``'s own tested scheduling internals
    (``_Reader``/``_Voice``/``_run_prep1-3``/``_emit_piece``, imported
    verbatim -- NOT reimplemented) purely to recover the tempo/groove OOB
    byte pairs in stream order. ``blackbird_parser.decode_streams()``
    deliberately discards these two bytes (it only needs to keep the
    physical stream pointer in sync for the NEXT voice's decode) -- this
    is a thin instrumentation pass over the same tested logic, stopping
    early once enough pairs are found (a full decode is not needed here).

    Per BLACKBIRD.md's tempo section: the pair is ``(b1, b1 ^ b2)`` --
    ``b1`` is the immediately-following ``zp_tempo`` value, ``b2`` is the
    ``m_groove`` XOR mask, so the alternate value is ``b1 ^ b2``. Real
    frames per tick = ``value // 7 + 1`` (confirmed empirically during the
    Stage-B native driver work, 2026-07-19, by dumping the validated
    per-frame simulator's own ``zp_master`` at every real row-boundary
    commit -- committed ``zp_master=35`` measured exactly 6 real frames to
    the next tick, ``=28`` measured exactly 5, matching ``//7+1`` and NOT
    the naive ``//7`` this docstring stated until that fix -- see
    BLACKBIRD.md's "B2 shipped" section for the full derivation. The ``+1``
    comes from the dispatch loop's fixed 3-frame prepare1/2/3 reservation
    (``cpx #3*7``), independent of the tempo value.
    """
    rd = _Reader(d, la, streamstart)
    voices = [_Voice(), _Voice(), _Voice()]
    pieces: list = []
    pairs: List[Tuple[int, int]] = []

    _emit_piece(rd, voices[1], 1, pieces, variant=variant)
    _emit_piece(rd, voices[0], 0, pieces, variant=variant)

    freeze_frame = None
    for frame in range(max_frames):
        if len(pairs) >= max_pairs:
            break
        if freeze_frame is not None and frame - freeze_frame >= 10:
            break
        pend_oob = [0]
        if (len(voices[2].out) - voices[2].rpos) < 128:
            _emit_piece(rd, voices[2], 2, pieces, variant=variant)
        for i in (2, 1, 0):
            _run_prep1(voices[i], i, pend_oob)
        if (len(voices[1].out) - voices[1].rpos) < 128:
            _emit_piece(rd, voices[1], 1, pieces, variant=variant)
        for i in (2, 1, 0):
            _run_prep2(voices[i])
        if (len(voices[0].out) - voices[0].rpos) < 128:
            _emit_piece(rd, voices[0], 0, pieces, variant=variant)
        for i in (2, 1, 0):
            _run_prep3(voices[i])
        if pend_oob[0] & 0x02:
            b1 = rd.next()
            b2 = rd.next()
            pairs.append((b1, b1 ^ b2))
        if pend_oob[0] & 0x04 and rd.loop_addr is None:
            # Song-loop OOB — mirrors sidm2.blackbird_parser.decode_streams()'s
            # own fix: freeze `rd` here (peek, don't follow, the jump target)
            # rather than reading past it, since this is a third independent
            # copy of the same frame loop. See BLACKBIRD.md's REPEAT=1
            # root-cause section.
            off_hi = rd.ptr - rd.la
            off_lo = (rd.ptr - 1) - rd.la
            hi = rd.data[off_hi] if 0 <= off_hi < len(rd.data) else 0xc0
            lo = rd.data[off_lo] if 0 <= off_lo < len(rd.data) else 0xc0
            rd.loop_addr = (hi << 8) | lo
            if not rd.frozen:
                rd.frozen = True
                rd.freeze_addr = rd.ptr
        if rd.frozen and freeze_frame is None:
            freeze_frame = frame
    return pairs


def estimate_tempo_chain(d: bytes, la: int, lay) -> List[int]:
    """The song's first tempo/groove pair, as a Driver 11 tempo CHAIN
    (frames/row per entry) -- falls back to a flat default if no tempo OOB
    record is found early in the stream."""
    pairs = extract_tempo_pairs(d, la, lay.streamstart, variant=lay.variant)
    if not pairs:
        return [DEFAULT_TICK_FRAMES]
    a, b = pairs[0]
    # +1: real frames/tick = tempo_byte // 7 + 1, not // 7 -- see
    # extract_tempo_pairs' docstring (fixed 2026-07-19, was silently off by
    # one frame per row in every Stage-A build before this).
    chain = [max(1, a // 7 + 1), max(1, b // 7 + 1)]
    if chain[0] == chain[1]:
        return [chain[0]]
    return chain


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------
def build_blackbird_driver11_song(path: str) -> GalwayDriver11Song:
    """Locate + decode a v1.2-exact Blackbird rip (via
    ``blackbird_parser.decode_file``) and build a Driver 11 song IR. Raises
    ``ValueError`` (propagated from ``decode_file``/``locate_blackbird``)
    if the file isn't a located v1.2-exact rip.
    """
    lay, result = decode_file(path)
    d, la, h = load_sid(path)

    instr_rows, wave_table, pulse_table = build_instruments(d, la, lay)

    tracks: List[List[D11Row]] = []
    for v in range(3):
        stream = result.real(v)
        steps = steps_for_voice(stream)
        tracks.append(steps_to_rows(steps))

    tempo = estimate_tempo_chain(d, la, lay)

    return GalwayDriver11Song(
        instruments=instr_rows,
        wave_table=wave_table,
        pulse_table=pulse_table,
        tracks=tracks,
        tempo=tempo,
        pitch_base=0,
        subtune=0,
    )
