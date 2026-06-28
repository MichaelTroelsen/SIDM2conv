"""Future Composer SID -> editable Driver 11 SF2 (Stage A).

Parses a Future Composer tune (sidm2.fc_parser) and transpiles its score onto a
standard SF2 **Driver 11** module, reusing the Galway Driver-11 IR + emitter so
the result opens, plays (F1), and is editable in SID Factory II.

Usage:  py -3 bin/fc_to_sf2.py SID/Fun_Fun/Triangle_Intro.sid [out.sf2]
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sid_parser import SIDParser
from sidm2.fc_parser import parse_fc, detect_player, NUM_NOTES
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _nearest_pal, _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2


def load_sid(path):
    """Load a SID rip or a raw C64 PRG (native FC module). Returns (data, load)."""
    raw = open(path, 'rb').read()
    if raw[:4] in (b'PSID', b'RSID'):
        h = SIDParser(path).parse_header()
        d = raw[h.data_offset:]
        la = h.load_address
        if la == 0 and len(d) >= 2:            # PSID load=0 -> embedded load word
            la = d[0] | (d[1] << 8)
            d = d[2:]
        return d, la
    # raw PRG: 2-byte load word + data
    return raw[2:], raw[0] | (raw[1] << 8)


def calibrate_base(freq_lo, freq_hi, tol=12):
    """Modal (pal_index - fc_index) offset matching FC freqs to the PAL table."""
    offs = Counter()
    for i in range(NUM_NOTES):
        f = freq_lo[i] | (freq_hi[i] << 8)
        if f < 8:
            continue
        ni, dist = _nearest_pal(f)
        if dist < tol:
            offs[ni - i] += 1
    return offs.most_common(1)[0][0] if offs else 0


def _pwm_program(base_row, init=0x400, step=0x080, span=10, hold=2):
    """A triangle pulse-width-modulation program (Driver 11 pulse table).

    FC leads sweep the pulse width per frame (byte [6] sweep at $1b75); a static
    thin width is near-silent, so pulse-waveform instruments get a moving PWM.
    Rows: set init, then +step*span up, -step*span down, loop (excluding the
    one-shot set row so the sweep is continuous). `step`/`hold` shape the rate.
    """
    prog = [(0x80 | ((init >> 8) & 0x0F), init & 0xFF, hold)]
    for _ in range(span):
        prog.append((0x00, step & 0xFF, hold))            # + step
    neg = (-step) & 0xFFF
    for _ in range(span):
        prog.append(((neg >> 8) & 0x0F, neg & 0xFF, hold))  # - step
    prog.append((0x7F, 0x00, base_row + 1))               # loop after the set row
    return prog


def _drum_note(freq, base):
    """Map a drum SID frequency to a Driver 11 absolute semitone (0-95)."""
    idx, _ = _nearest_pal(freq)
    return max(0, min(idx + base + 1, 95))


def _instr_change(n_instr, cur_instr):
    """Return the instrument to SET for this note (or None for no change) and the
    updated current instrument. Plain note path — instr 0 is handled earlier as a
    sustain (see _block_rows), so here a 0 simply means no change."""
    if n_instr != 0 and n_instr != cur_instr:
        return n_instr, n_instr
    return None, cur_instr


def _trace_pulse_programs(sid_data, la, fc):
    """Trace the ORIGINAL FC SID and capture each pulse instrument's real per-frame
    pulse-width sweep, returned as {instr_idx: [(col0,col1,col2), ...]} Driver-11
    pulse programs. FC sweeps the pulse width per note (e.g. $100->$4A0 in an
    8-frame cycle); the hardcoded triangle PWM can't match it, so replay the real
    trajectory. An instrument is identified in the trace by its initial pulse value
    (byte [0] << 8), which the player reloads on each note-on with that instrument.
    """
    import subprocess
    from scripts.sf2_to_sid import PSIDHeader
    h = PSIDHeader(load_address=la, init_address=la, play_address=la + 6)
    h.songs = 1
    h.start_song = 1
    tmp = os.path.join('out', '_pulsetrace.sid')
    os.makedirs('out', exist_ok=True)
    open(tmp, 'wb').write(h.to_bytes() + sid_data)
    txt = subprocess.run(['py', '-3', 'pyscript/siddump_complete.py', tmp, '-t8'],
                         capture_output=True, text=True).stdout
    V = {0: [], 1: [], 2: []}                          # per voice: (pulse12, ctl)
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        for vi in range(3):
            t = c[2 + vi].split()
            V[vi].append((t[-1] if t else '...', t[3] if len(t) > 3 else '..'))

    def capture(target_hi):
        for vi in range(3):
            seq = V[vi]
            for i in range(1, len(seq) - 18):
                pul, ctl = seq[i]
                try:
                    pv = int(pul, 16)
                except ValueError:
                    continue
                if (pv >> 8) == target_hi and ctl not in ('..', '00'):
                    traj = []
                    for j in range(i, i + 18):
                        p = seq[j][0]
                        try:
                            traj.append(int(p, 16))
                        except ValueError:
                            traj.append(traj[-1] if traj else pv)
                    return traj
        return None

    progs = {}
    for idx, ins in enumerate(fc.instruments):
        if not (ins.waveform & 0x40) or ins.pulse == 0:
            continue
        traj = capture(ins.pulse)
        if not traj:
            continue
        # one cycle = up to where the width returns near the initial (the per-note
        # reset), else the whole captured window held at the end.
        clen = len(traj)
        for k in range(1, len(traj)):
            if abs(traj[k] - traj[0]) <= 0x40:
                clen = k
                break
        rows = [(0x80 | ((traj[0] >> 8) & 0x0F), traj[0] & 0xFF, 0x01)]
        for k in range(clen - 1):
            dv = (traj[k + 1] - traj[k]) & 0xFFF
            rows.append(((dv >> 8) & 0x0F, dv & 0xFF, 0x01))
        progs[idx] = rows                              # caller appends + adds the $7F loop
    return progs


def _trace_filter_program(sid_data, la, fc):
    """Trace the ORIGINAL FC SID's global filter and return a Driver-11 filter
    program (list of (col0,col1,col2) rows) or None. FC filter instruments
    (mctrl & $01) sweep the cutoff per note (e.g. low-pass, res $B, voice-1
    routing, cutoff $600 -> $280, reset each note). Format (per DRIVER11 docs):
    set `XY YY RB` (X=passband 9-F, YYY=12-bit cutoff, R=res, B=channel bitmask);
    add `0X XX YY` (XXX=signed add, YY=frames); `7F .. idx` jump."""
    if not any(ins.mctrl & 0x01 for ins in fc.instruments):
        return None
    import subprocess
    from scripts.sf2_to_sid import PSIDHeader
    h = PSIDHeader(load_address=la, init_address=la, play_address=la + 6)
    h.songs = 1
    h.start_song = 1
    tmp = os.path.join('out', '_filtertrace.sid')
    os.makedirs('out', exist_ok=True)
    open(tmp, 'wb').write(h.to_bytes() + sid_data)
    txt = subprocess.run(['py', '-3', 'pyscript/siddump_complete.py', tmp, '-t8'],
                         capture_output=True, text=True).stdout
    rows = []                                          # (cut12, rc, typ) per frame
    last_rc, last_typ = 0x00, 'Low'
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        f = c[5].split()                               # FCut RC Typ V
        try:
            cut = int(f[0], 16)
        except (ValueError, IndexError):
            cut = None
        if len(f) > 1 and f[1] not in ('..', ''):
            last_rc = int(f[1], 16)
        if len(f) > 2 and f[2] not in ('...', ''):
            last_typ = f[2]
        rows.append((cut, last_rc, last_typ))
    # find the cutoff sweep: a run starting at the max cutoff, descending to a reset
    starts = [i for i, (cut, rc, _) in enumerate(rows)
              if cut and rc and (rc & 0x0F) and i + 1 < len(rows)
              and rows[i + 1][0] and rows[i + 1][0] < cut]
    if not starts:
        return None
    i0 = starts[0]
    init_cut, rc, typ = rows[i0]
    traj = [rows[i0][0]]
    for j in range(i0 + 1, min(i0 + 24, len(rows))):
        cut = rows[j][0]
        if cut is None:
            break
        if abs(cut - init_cut) <= 0x40 and j > i0 + 1:  # reset to start = cycle end
            break
        traj.append(cut)
    passband = {'Low': 0x9, 'Band': 0xA, 'High': 0xC}.get(typ, 0x9)
    res, bitmask = (rc >> 4) & 0x0F, rc & 0x0F
    prog = [((passband << 4) | ((init_cut >> 8) & 0x0F), init_cut & 0xFF,
             (res << 4) | bitmask)]                     # set
    for k in range(len(traj) - 1):
        dv = (traj[k + 1] - traj[k]) & 0xFFF
        prog.append(((dv >> 8) & 0x0F, dv & 0xFF, 0x01))  # add, 1 frame
    return prog


def build_instruments(fc, base, pulse_progs=None, filter_prog=None):
    """FC 8-byte sound records -> Driver 11 instrument rows + wave/pulse tables.

    Three timbre classes are reproduced as Driver 11 wave programs (col1 $00-$7f
    = relative semitone added to the note, $80-$df = absolute semitone for drums):
    - Drum  (mctrl [7] & $10): a 14-frame (waveform, absolute-pitch) sequence
      from the drum tables (FC $1c7b engine), then a gate-off settle row.
    - Arp   (mctrl [7] & $04, byte [5] != 0): cycle [0, [5]>>4, [5]&$0f] one row
      per frame (FC $1d25 phase counter) -> a chord.
    - Plain: a single waveform held.
    """
    fc_instruments = fc.instruments
    pulse_progs = pulse_progs or {}
    instr_rows, wave_table, pulse_table = [], [], []
    for idx, ins in enumerate(fc_instruments[:32]):
        wf = _norm_waveform(ins.waveform)
        wave_row = len(wave_table)
        if ins.mctrl & 0x10:                          # drum
            # FC plays the note's OWN pitch on the trigger frame, then the drum
            # table from frame 1 (the engine indexes $1e56/$1e46 by frame-1 at
            # $1cad). Verified vs trace: real osc3 = B-3 (the note) then $2000…
            # So lead with one root frame before the absolute drum pitches.
            wave_table.append((_norm_waveform(ins.waveform), 0x00))
            for dwf, dfreq in fc.drum_sequence(ins.vibrato):
                wave_table.append((dwf, 0x80 | _drum_note(dfreq, base)))
            settle = len(wave_table)
            wave_table.append((0x10, 0x00))           # gate-off hold (decay)
            wave_table.append((0x7F, settle))
        elif (ins.mctrl & 0x04) and ins.vibrato:      # arpeggio enabled
            hi, lo = ins.vibrato >> 4, ins.vibrato & 0x0F
            # FC phase counter $2161 runs 2->1->0 after the note triggers at the
            # root, so the played offsets are root, +lo, +hi (verified vs trace:
            # real cycles root,+8,+5 for [5]=$58, not root,+5,+8).
            wave_table.append((wf, 0x00))             # root (trigger frame)
            wave_table.append((wf, lo & 0x7F))        # + low-nibble semitones
            wave_table.append((wf, hi & 0x7F))        # + high-nibble semitones
            wave_table.append((0x7F, wave_row))       # loop the 3-step arp
        else:
            wave_table.append((wf, 0x00))
            wave_table.append((0x7F, wave_row))
        pulse_row = len(pulse_table)
        traced = pulse_progs.get(idx)
        if traced is not None:                   # trace-driven: replay the real sweep
            pulse_table.extend(traced)
            pulse_table.append((0x7F, 0x00, pulse_row))   # loop the captured cycle
        elif ins.waveform & 0x40:                # pulse waveform -> hardcoded PWM sweep
            pulse_table.extend(_pwm_program(pulse_row))
        else:
            pulse_table.extend(_pulse_program(0x800, pulse_row))
        # D15 uses a static pulse byte (hi of 12-bit width) -> 50% for pulse voices
        pw = 0x08 if (ins.waveform & 0x40) else 0x00
        flags = 0x80
        if filter_prog and (ins.mctrl & 0x01):   # filter instrument: start the
            flags |= 0x40                         # global filter program (row 0)
        instr_rows.append(D11Instrument(
            ad=ins.ad, sr=ins.sr, flags=flags,
            filter_idx=0x00, pulse_idx=pulse_row, wave_idx=wave_row,
            pulse_width=pw))
    filter_table = []
    if filter_prog:
        # loop back to row 0 (re-sets cutoff + re-sweeps) — FC resets the cutoff
        # each note; the program only restarts on instrument-set (per block), so
        # looping keeps the cutoff sweeping ~per note instead of holding.
        filter_table = list(filter_prog) + [(0x7F, 0x00, 0x00)]
    if not instr_rows:
        wave_table = [(0x41, 0x00), (0x7F, 0x00)]
        pulse_table = list(_pulse_program(0x800, 0))
        instr_rows = [D11Instrument(0x09, 0x00, 0x80, 0, 0, 0)]
    return instr_rows, wave_table, pulse_table, filter_table


def _block_rows(block_notes, base, cur_instr, silent_idx=None):
    """Convert one FC block's notes to Driver 11 rows, threading instrument state
    (returns updated cur_instr). Same note/rest/tie/anchor logic as build_track,
    but per-block so the block stays its own short sequence. Callers pass
    cur_instr=None per block so each sequence sets its own instrument on the first
    note — the sequences are de-duplicated and replayed from different orderlist
    positions, so a sequence that relied on a threaded instrument would sound with
    the wrong (or silent-anchor) timbre in some positions."""
    out = []
    rest_run = 0
    for n in block_notes:
        nrows = max(1, n.dur + 1)
        if n.is_rest:
            for _ in range(nrows):
                if silent_idx is not None and rest_run >= _MAX_REST_RUN:
                    out.append(D11Row(note=1, instrument=silent_idx))
                    cur_instr = silent_idx
                    rest_run = 0
                else:
                    out.append(D11Row(note=SF2_GATE_OFF))
                    rest_run += 1
            continue
        rest_run = 0
        if n.instr == 0:
            # FC instrument 0 = HOLD (sustain the current note — see build_track).
            out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows))
            continue
        note = max(SF2_NOTE_MIN, min(n.note + base + 1, SF2_NOTE_MAX))
        inst, cur_instr = _instr_change(n.instr, cur_instr)
        out.append(D11Row(note=note, instrument=inst, tie=n.tie))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows - 1))
    # An all-note-off sequence stalls the D11 orderlist (it never advances past
    # the rests); anchor the last row so the orderlist moves on.
    if silent_idx is not None and out and all(r.note == SF2_GATE_OFF for r in out):
        out[-1] = D11Row(note=1, instrument=silent_idx)
    return out, cur_instr


def build_structured(fc, base, silent_idx=None, merge_rests=True):
    """Preserve FC's block/orderlist structure: emit one (deduplicated) Driver 11
    sequence per FC block instance, and a per-voice orderlist that replays them —
    so the SF2 editor shows the song's real patterns. ``silent_idx`` enables the
    rest-run / all-rest anchors (see _block_rows) that keep long silent intros and
    rest blocks from stalling the voice.

    FC voices stagger their entries with a short rest block repeated many times
    (e.g. the lead is silent for 6x block-0). With ``merge_rests`` the rest-only
    blocks are folded into the following content sequence; without it each rest
    block stays a short separate sequence replayed by the orderlist.
    """
    from sidm2.galway_driver11_emitter import segment_track
    seq_index = {}
    sequences = []
    orderlists = [[], [], []]

    def add(rows, v):
        for pk in segment_track(rows):
            idx = seq_index.get(pk)
            if idx is None:
                idx = len(sequences)
                seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)

    for v in range(3):
        pending = []                                 # deferred rest-only blocks
        for block_notes in fc.voice_blocks[v]:
            # cur_instr=None per block: each sequence is self-contained (sets its
            # own instrument) so de-dup + replay can't carry a stale instrument.
            rows, _ = _block_rows(block_notes, base, None, silent_idx)
            if merge_rests and all(b.is_rest for b in block_notes):
                pending += rows
                continue
            add(pending + rows, v)
            pending = []
        if pending:
            add(pending, v)
    return sequences, orderlists


# A long unbroken run of note-off rows (a voice with a long silent intro, e.g.
# Triangle_Intro's lead is silent for ~288 ticks) STALLS playback in stock SID
# Factory II: the voice never advances past the rests, so it stays silent the
# whole song (the bundled driver's note-off hold counter, INC'd by every $00,
# suppresses sequence advance). The raw driver run by siddump plays it fine, so
# the data is correct — it is an SF2II-side stall. We break any rest run longer
# than this many rows with a SILENT anchor note (a real note event on a
# waveform-$00 instrument: it makes no sound but resets the hold counter so
# playback advances). USER-CONFIRMED to un-stall the lead in real SF2II.
_MAX_REST_RUN = 64


def _append_silent_instrument(instr_rows, wave_table, pulse_table):
    """Append a silent instrument (wave program writes $00 to the control reg =
    gate off / no waveform = no sound) for rest-run anchors. Returns its index."""
    wrow = len(wave_table)
    wave_table.append((0x00, 0x00))            # silent: no waveform, gate off
    wave_table.append((0x7F, wrow))
    idx = len(instr_rows)
    instr_rows.append(D11Instrument(ad=0x00, sr=0x00, flags=0x80, filter_idx=0x00,
                                    pulse_idx=0, wave_idx=wrow, pulse_width=0x00))
    return idx


def _has_long_rest_run(notes):
    """True if a voice has a contiguous note-off run >= _MAX_REST_RUN rows (which
    would stall it in SF2II — see _MAX_REST_RUN)."""
    run = 0
    for n in notes:
        if n.is_rest:
            run += max(1, n.dur + 1)
            if run >= _MAX_REST_RUN:
                return True
        else:
            run = 0
    return False


def build_track(rows, base, silent_idx=None):
    """Flatten FCNote rows -> Driver 11 sequence rows (note + sustain/rest rows).

    An FC note of duration ``dur`` plays for ``dur+1`` player ticks (the counter
    runs dur..0..-1), so it maps to ``dur+1`` Driver 11 rows. One row == one
    player tick; the master-speed frames/tick is carried by the song tempo.

    When ``silent_idx`` is given, runs of more than ``_MAX_REST_RUN`` note-off
    rows are broken with a silent anchor note (see _MAX_REST_RUN) so a long
    silent intro doesn't stall the voice in SF2II.
    """
    out = []
    cur_instr = None
    rest_run = 0
    for n in rows:
        nrows = max(1, n.dur + 1)
        if n.is_rest:
            for _ in range(nrows):
                if silent_idx is not None and rest_run >= _MAX_REST_RUN:
                    out.append(D11Row(note=1, instrument=silent_idx))
                    cur_instr = silent_idx          # next note re-asserts its own
                    rest_run = 0
                else:
                    out.append(D11Row(note=SF2_GATE_OFF))
                    rest_run += 1
            continue
        rest_run = 0
        if n.instr == 0:
            # instr 0 = HOLD the current note (sustain, no retrigger — see
            # _block_rows); at song start this is silence.
            out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows))
            continue
        note = max(SF2_NOTE_MIN, min(n.note + base + 1, SF2_NOTE_MAX))
        inst, cur_instr = _instr_change(n.instr, cur_instr)
        out.append(D11Row(note=note, instrument=inst, tie=n.tie))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows - 1))
    return out


def fc_to_song(fc, sid_data=None):
    # -1: the PAL-table calibration lands a semitone high vs Driver 11's own
    # freq table (confirmed by a clean from-INIT siddump: FC note 24 must emit
    # SF2 note B-1 / $0430, not C-2). So nudge the modal base down one.
    base = calibrate_base(fc.freq_lo, fc.freq_hi) - 1
    # One Driver 11 row == one FC player tick; each tick is (speed+1) video
    # frames (the master-speed divider reloads from $211d). SF2II's Driver 11
    # tempo value V holds each row V+1 frames (measured: V=2 -> 3 frames/row), so
    # to get (speed+1) frames/row we set tempo == speed.
    tempo = max(1, fc.speed)
    # With the original SID data, trace each pulse instrument's real per-frame
    # width sweep and the global filter cutoff sweep and replay them (much closer
    # than the hardcoded triangle PWM / no filter at all).
    pulse_progs = _trace_pulse_programs(sid_data, fc.load, fc) if sid_data else None
    filter_prog = _trace_filter_program(sid_data, fc.load, fc) if sid_data else None
    instr_rows, wave_table, pulse_table, filter_table = build_instruments(
        fc, base, pulse_progs, filter_prog)
    # Always append the silent anchor instrument (LAST instrument) so both the flat
    # and structured paths can break long rest runs / all-rest blocks that would
    # otherwise stall a voice in SF2II (see _MAX_REST_RUN). Unused if a tune has no
    # long rests. main() reads its index as len(instruments) - 1.
    silent_idx = _append_silent_instrument(instr_rows, wave_table, pulse_table)
    tracks = [build_track(v, base, silent_idx) for v in fc.voices]
    return GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        filter_table=filter_table, tracks=tracks, tempo=tempo,
        pitch_base=base, subtune=0)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    d, la = load_sid(path)
    if not detect_player(d, la):
        print(f"ERROR: {os.path.basename(path)} is not the supported Future "
              f"Composer $1800 player variant (load=${la:04X}); skipping.")
        return 2
    use_d15 = '--d15' in sys.argv
    fc = parse_fc(d, la)
    song = fc_to_song(fc, d)                           # d -> trace-driven pulse sweeps
    silent_idx = len(song.instruments) - 1            # the appended silent anchor
    # Structured emit (both drivers): one sequence per FC block + a real per-voice
    # orderlist, so the SF2 editor shows the song's actual patterns. Anchors un-stall
    # long silent intros / rest blocks; the emitter lays sequences in fixed editor
    # slots. USER-CONFIRMED: orderlist matches the song and it plays.
    sequences, orderlists = build_structured(fc, song.pitch_base, silent_idx,
                                             merge_rests=False)
    print(f"load=${la:04X} instruments={len(fc.instruments)} base={song.pitch_base} "
          f"tempo={song.tempo} driver={'15' if use_d15 else '11'} sequences={len(sequences)}")
    if use_d15:
        tpl = 'G5/examples/Driver 15 Test - Mood.sf2'
        sf2 = emit_driver11_sf2(song, template_path=tpl, sequences=sequences,
                                orderlists=orderlists, instr_layout='d15')
    else:
        sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
