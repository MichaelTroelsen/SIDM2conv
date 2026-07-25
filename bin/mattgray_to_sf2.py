"""Matt Gray SID -> editable Driver 11 SF2 (Stage A).

Parses a Matt Gray tune (sidm2.mattgray_parser) and transpiles its score onto a
standard SF2 **Driver 11** module, reusing the shared Galway Driver-11 IR +
emitter so the result opens, plays (F1), and is fully editable in stock
SID Factory II.

Stage A scope (deliberate -- see docs/players/PLAYBOOK.md §1):
notes, note order, durations, tempo, and the per-instrument ADSR / waveform /
pulse *setup* are carried over exactly.  The synth side that moves a value
per frame -- pitch slides ($fb/$fc and the automatic A1[0]/A1[4] slides),
arpeggios (A0[5]), pulse-width sweep (A0[4]) and the drum path (A0[7] bit0) --
is NOT modelled here; those are Stage B.  Instruments using them still sound,
they just hold a static timbre.

Usage:
    py -3 bin/mattgray_to_sf2.py <file.sid> [out.sf2] [--subtune N]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.mattgray_parser import (  # noqa: E402
    NUM_NOTES, MattGrayError, parse_sid, simulate,
)
from sidm2.galway_to_driver11 import (  # noqa: E402
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _nearest_pal, _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2  # noqa: E402

MAX_D11_INSTR = 32          # SF2II cap ($a0-$bf)
# The SF2II memory wall: tables must stay under $d000, which works out at
# roughly 27,650 play-calls (~9.2 min).  Stay comfortably inside it.
MAX_PART_FRAMES = 24_000


def calibrate_base(song, tol: int = 12) -> int:
    """Modal (pal_index - mattgray_index) offset for this file's freq table.

    Matt Gray ships his own frequency table per build, so never assume the
    generic PAL table -- match his entries against it and take the modal
    offset (PLAYBOOK §5, "always emit the player's own freq table").
    """
    offs: Counter = Counter()
    for i in range(NUM_NOTES):
        f = song.freq(i)
        if f < 8:
            continue
        ni, dist = _nearest_pal(f)
        if dist < tol:
            offs[ni - i] += 1
    return offs.most_common(1)[0][0] if offs else 0


def build_instruments(song, base: int):
    """Map Matt Gray instruments onto Driver 11 instrument/wave/pulse rows."""
    instr_rows, wave_table, pulse_table = [], [], []
    filter_table = [(0x00, 0x00, 0x00)]

    for ins in song.instruments[:MAX_D11_INSTR]:
        # --- wave: hold the instrument's sustained waveform.
        # A0[6] is the attack-frame waveform and A0[1] the sustained one; when
        # they differ, spend one row on the attack waveform then hold A0[1].
        wave_row = len(wave_table)
        sustain_wf = _norm_waveform(ins.waveform)
        attack_wf = _norm_waveform(ins.attack_waveform)
        if attack_wf and attack_wf != sustain_wf:
            wave_table.append((attack_wf, 0x00))
        hold = len(wave_table)
        wave_table.append((sustain_wf, 0x00))
        wave_table.append((0x7F, hold))          # loop on the sustained row

        # --- pulse: A0[0] packs the 12-bit width as hi-nibble -> $d402,
        # lo-nibble -> $d403.  A width of 0 is SILENT on a pulse waveform, so
        # fall back to a 50% square rather than emitting an inaudible voice.
        pulse_row = len(pulse_table)
        width = ins.pulse_width or 0x800
        pulse_table.extend(_pulse_program(width, pulse_row))

        instr_rows.append(D11Instrument(
            ad=ins.ad, sr=ins.sr, flags=0x80, filter_idx=0x00,
            pulse_idx=pulse_row, wave_idx=wave_row,
        ))

    if not instr_rows:                            # degenerate file
        wave_table = [(0x41, 0x00), (0x7F, 0x00)]
        pulse_table = list(_pulse_program(0x800, 0))
        instr_rows = [D11Instrument(0x09, 0x00, 0x80, 0, 0, 0)]
    return instr_rows, wave_table, pulse_table, filter_table


def build_tracks(song, events, base: int, n_instr: int,
                 tick_lo: int = 0, tick_hi: int | None = None):
    """Expand the per-voice note events onto the Driver 11 per-tick row grid.

    Rows between events are $7e (sustain), which is what the driver does: a
    note holds until the voice's duration counter runs out and the next
    pattern event is fetched.  ``tick_lo``/``tick_hi`` window the grid so a
    long tune can be split into parts (see the memory wall, PLAYBOOK §3).
    """
    tracks = []
    clipped = 0
    for vi in range(3):
        evs = sorted(events[vi], key=lambda e: e.tick)
        if not evs:
            tracks.append([D11Row(note=SF2_GATE_OFF)])
            continue
        end = max(e.tick + e.duration + 1 for e in evs)
        hi = end if tick_hi is None else min(tick_hi, end)
        if hi <= tick_lo:
            tracks.append([D11Row(note=SF2_GATE_OFF)])
            continue

        grid = {}
        for e in evs:
            grid[e.tick] = e

        # Carry the instrument in effect at the window start, so a part that
        # begins mid-note still selects the right instrument on its first row.
        cur_instr = None
        for e in evs:
            if e.tick < tick_lo and not e.is_rest:
                cur_instr = e.instrument if e.instrument < n_instr else 0
        prime = cur_instr

        rows = [D11Row(note=SF2_GATE_ON) for _ in range(hi - tick_lo)]
        for t in range(tick_lo, hi):
            e = grid.get(t)
            if e is None:
                continue
            if e.is_rest:
                rows[t - tick_lo] = D11Row(note=SF2_GATE_OFF)
                continue
            n = e.note + base
            if not SF2_NOTE_MIN <= n <= SF2_NOTE_MAX:
                n = max(SF2_NOTE_MIN, min(n, SF2_NOTE_MAX))
                clipped += 1
            instr = e.instrument if e.instrument < n_instr else 0
            rows[t - tick_lo] = D11Row(
                note=n, instrument=instr if instr != cur_instr else None)
            cur_instr = instr
        # force an explicit instrument select on the window's first note row
        if prime is not None:
            for r in rows:
                if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX:
                    if r.instrument is None:
                        r.instrument = prime
                    break
        tracks.append(rows)
    return tracks, clipped


def convert(sid_path: str, out_path: str, subtune: int = 1,
            max_frames: int = 400_000, max_part_frames: int = MAX_PART_FRAMES,
            force: bool = False) -> int:
    song = parse_sid(sid_path, subtune=subtune)

    # Only the Driller-era layout is validated (onset 100% / pitch 100%).  A
    # file located by signature parses and looks entirely plausible -- sensible
    # pattern, instrument and note counts -- while decoding WRONG: Last Ninja 2
    # scores 11-22% pitch against siddump because the 1988 build's byte
    # semantics differ.  Refuse rather than emit a confident-looking bad SF2.
    if getattr(song, "layout", None) != "driller" and not force:
        raise MattGrayError(
            f"{os.path.basename(sid_path)} uses a Matt Gray build whose byte "
            f"semantics are NOT yet validated (tables located by signature). "
            f"Converting it would produce a plausible but wrong SF2 -- see "
            f"docs/players/MATTGRAY.md. Re-run with --force only to "
            f"experiment, never to ship.")
    events = simulate(song, frames=max_frames, stop_on_loop=True)
    base = calibrate_base(song)

    instr_rows, wave_table, pulse_table, filter_table = build_instruments(song, base)

    total_ticks = max(
        (max(e.tick + e.duration + 1 for e in events[vi]) if events[vi] else 0)
        for vi in range(3))
    if total_ticks == 0:
        raise MattGrayError("no notes decoded -- refusing to emit an empty SF2")

    # The SF2II memory wall caps a single module at roughly MAX_PART_FRAMES
    # play-calls; a longer tune must be split into parts rather than silently
    # truncated (standing preference: never ship lossy output silently).
    ticks_per_part = max(1, max_part_frames // song.frames_per_tick)
    n_parts = (total_ticks + ticks_per_part - 1) // ticks_per_part

    stem, ext = os.path.splitext(out_path)
    print(f"{os.path.basename(sid_path)} subtune {subtune}")
    print(f"  tempo {song.tempo} ({song.frames_per_tick} frames/row)  "
          f"pitch base {base:+d}")
    print(f"  {len(song.patterns)} patterns, {len(song.instruments)} instruments "
          f"({len(instr_rows)} emitted)")
    print(f"  song loops at {total_ticks} rows = "
          f"{total_ticks * song.frames_per_tick} frames = "
          f"{total_ticks * song.frames_per_tick / 50.0:.1f}s")
    if n_parts > 1:
        print(f"  -> {n_parts} parts (SF2II memory wall is ~{max_part_frames} "
              f"play-calls per module)")

    total_notes = 0
    for part in range(n_parts):
        lo = part * ticks_per_part
        hi = min(total_ticks, lo + ticks_per_part)
        tracks, clipped = build_tracks(song, events, base, len(instr_rows),
                                       tick_lo=lo, tick_hi=hi)
        d11 = GalwayDriver11Song(
            instruments=instr_rows,
            wave_table=wave_table,
            pulse_table=pulse_table,
            filter_table=filter_table,
            tracks=tracks,
            # Both formats mean the same thing: value + 1 frames per row.
            tempo=song.tempo,
            pitch_base=base,
            subtune=subtune,
        )
        path = out_path if n_parts == 1 else f"{stem}_part{part + 1:02d}{ext}"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(emit_driver11_sf2(d11))
        n_notes = sum(1 for t in tracks for r in t
                      if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX)
        total_notes += n_notes
        print(f"  {os.path.basename(path)}: rows {lo}-{hi} "
              f"({[len(t) for t in tracks]}), {n_notes} note rows"
              + (f", {clipped} clipped" if clipped else ""))

    print(f"  total {total_notes} note rows emitted")
    if len(song.instruments) > MAX_D11_INSTR:
        print(f"  NOTE: {len(song.instruments) - MAX_D11_INSTR} instruments "
              f"dropped (SF2II cap is {MAX_D11_INSTR})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sid")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--subtune", type=int, default=1)
    ap.add_argument("--part-frames", type=int, default=MAX_PART_FRAMES,
                    help="max play-calls per emitted SF2 part")
    args = ap.parse_args()
    out = args.out or os.path.join(
        "out", os.path.splitext(os.path.basename(args.sid))[0] + ".sf2")
    try:
        return convert(args.sid, out, args.subtune,
                       max_part_frames=args.part_frames)
    except MattGrayError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
