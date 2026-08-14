"""HardTrack Composer (Longhair/Brush, Elysium 1992) SID -> native SF2 (Stage B).

Stage A (bin/hardtrack_to_sf2.py) transpiles to stock Driver 11 and, measured
over the notes the parser itself resolves, retains 99.69% of them. The 0.31% it
loses is not a decode error -- it is everything Driver 11 has no way to express,
and docs/players/HARDTRACK.md names all of it:

  * `$62` freezes the player's wave stepper, so a note's pitch HOLDS where the
    program left it (Walk_to_Soul, 28x loss enrichment);
  * HardTrack writes the bare note frequency at note-on and lets the wave
    program overwrite it from the next frame -- Driver 11 applies wave row 0
    immediately and never sounds the base pitch (Ritual_II_tune_2);
  * the pulse SWEEP (Driver 11's pulse table is set-and-hold), the $63/$64
    slide/portamento, and the global filter sweep, none of which Stage A ports;
  * the program-driven column -- instrument field 5 bit 7, 1,062 notes whose
    pitch the wave program writes ABSOLUTELY. Stage A scores 2.64% there BY
    CONSTRUCTION, because the sequencer note never reaches $D400 at all.

A trace-driven native build dissolves that entire list at once, which is the
point of Stage B: the per-frame wave / pulse / FM / filter programs are CAPTURED
from the original's own siddump output rather than modelled, so whatever the
synth engine did -- freeze, absolute-pitch drum, sweep, slide -- is what the
driver replays. Nothing here re-implements HardTrack's synth engine; it replays
it. (PLAYBOOK Sec.2's "parse statically, trace the synth side" split.)

Like the Future Composer builder this adds NO new driver: a MON-compatible shim
feeds bin/build_mon_native_song.build_native_song, the same engine behind
Hawkeye / Hubbard / DMC / Sound Monitor / SDI / FC, and emit_one assembles MoN's
driver. The shim is DECODE-driven (notes/durations from hardtrack_parser), which
is the right mode here because the sequencer walk is the validated part: its
match rate is FLAT across 1,000 frames in 33 files, i.e. no drift.

  py -3 bin/build_hardtrack_native_song.py [SID/Shogoon/Love_tune_2.sid] [secs|auto] [sub]

Output: out/hardtrack_native/<name>_part<NN>.sf2
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent
from sidm2.hardtrack_parser import HardTrackModule, HardTrackError, voice_events
from sidm2.fidelity_common import score_pct, siddump_frames_full
from sidm2.instrument_map import (
    InstrumentScores, frame_labels, instrument_labels, key_reliability,
    onsets_with_registers)
from sidm2.sf2_caps import CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP
import build_mon_native_song as BM

SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "SID", "Shogoon", "Love_tune_2.sid")
WARG = sys.argv[2] if len(sys.argv) > 2 else "auto"
SUB = int(sys.argv[3]) if len(sys.argv) > 3 else 0

# How far to run the sequencer while looking for the orderlist loop point. A
# HardTrack song runs forever ($FF restart / $FD jump), so "the song length" is
# one pass through the orderlist; 120s is well past every tune in the corpus.
SCAN_FRAMES = 6000
OUT_DIR = os.path.join(ROOT, "out", "hardtrack_native")

# NOTE_PIPE: frames between a row's DISPATCH and the note reaching the SID.
# HardTrack's note-on is a pipeline -- the row dispatched on frame G leaves the
# previous note's frequency in $D400 on G and G+1, gates on G+2 and only then
# lets the wave program run. For a re-triggered note `snap_gate` finds that gate
# rise on its own, so the value is a no-op there; it matters for a note the
# window RE-ENTERS mid-flight, which has no gate rise to snap to and would
# otherwise replay its capture 2 frames early for the note's whole length
# (Love_tune_2 voice 1, a 200-frame arpeggio, every frame wrong by exactly a
# 2-frame shift while the waveform stayed byte-exact).
PIPE = int(os.environ.get('HT_PIPE', '2'))


class HardTrackShim:
    """MON-compatible view of a decoded HardTrack song.

    Only the SEQUENCER crosses this boundary: notes, tick durations, instrument
    indices. Every timbre decision (waveform steps, pulse width, pitch
    modulation, filter cutoff) is left to build_native_song's per-note capture,
    which is precisely why the Stage A loss classes do not survive into Stage B.
    """

    tempo_toggle = False      # one global divider, no swing grid
    hard_restart = 0          # HardTrack's field-5 bit 4 is its OWN hard restart,
                              # already in the capture. B.HARD_RESTART is the
                              # Hubbard kill-ADSR engine and would add a behaviour
                              # this player does not have.
    snap_gate = True          # snap each capture to the real gate rise (+-2 frames)
    hp_engine = 0             # pulse sweeps are captured, not modelled
    filter_tie = 0
    # Per-note SR restart. HardTrack writes SR=$00 at ROW DISPATCH and the
    # instrument AD/SR when the note reaches the SID PIPE frames later, leaving
    # exactly two frames of SR=0 before every note (measured: 68/68/108 SR
    # mismatches on Love_tune_2, every one of them on a gate-OFF frame, ours=$3a
    # -> orig=$00). See sr_pre in drivers_src/mon/romuzak_driver.asm and the
    # rung-4 section of docs/players/HARDTRACK.md for what it is and is not
    # worth. HT_SR_PREKILL=N overrides; 0 disables.
    sr_prekill = int(os.environ.get('HT_SR_PREKILL', '0'))
    # HardTrack percussion produces real per-frame Hz deltas in $40xx-$43xx
    # (Love_tune_2 voice 2: a $4300 drum dive), which is exactly the range the
    # driver's SCALED-vibrato entry marker claims. Leaving the marker on froze
    # that note's whole tail at the wrong absolute frequency while its waveform
    # stayed byte-exact. Same collision Hubbard hit; see _fm_scale_ok.
    no_fm_scale = 1

    def __init__(self, mod, subtune=0, frames=SCAN_FRAMES):
        self.mod = mod
        self.subtune = subtune
        self.speed = mod.speed(subtune)
        # A song row lands every speed+1 frames (docs/players/HARDTRACK.md
        # "Tempo"): the divider counts speed..0 and the row is dispatched on 0.
        self._fpt = self.speed + 1
        # init leaves the divider at 2, so the very first row is dispatched on
        # frame 1, not frame 0 -- a real one-frame phase, asserted below against
        # the walk's own recorded frames rather than assumed.
        self.onset_delay = 1
        self.events, self.loops = voice_events(mod, subtune, frames)
        first = [e for evs in self.events for e in evs[:1]]
        if first:
            d = {e.frame - e.tick * self._fpt for e in first}
            if d != {1}:                # never silently keep a wrong phase
                self.onset_delay = min(d)
                print(f"  NOTE: first-row phase is {sorted(d)}, not 1 -- "
                      f"using {self.onset_delay}")
        # ...plus the note-on PIPELINE. The row dispatch is not the frame the
        # note reaches the SID: the gate rises PIPE frames later (see NOTE_PIPE).
        self.onset_delay += PIPE
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            out = self.voices[v]
            for e in self.events[v]:
                if e.kind == 'gate_off':
                    # $61 gates the voice off -- but HardTrack goes on stepping
                    # the wave program through the release, so the voice keeps
                    # ARPEGGIATING while it rings out (Love_tune_2 v1 spends 150
                    # frames per phrase doing exactly that, wf $40, gate clear).
                    # Emitting a rest here throws that tail away and idles the
                    # voice; folding the gate-off into the preceding note instead
                    # leaves it inside that note's CAPTURE, where the gate bit is
                    # just another $D404 byte and the release replays verbatim.
                    # Only a gate-off with nothing before it is a real rest.
                    if out:
                        out[-1].dur += e.dur
                        continue
                out.append(MONEvent(
                    note=(0 if e.kind == 'gate_off' else e.note),
                    dur=e.dur,
                    instr=e.instr,
                    wprog=0,
                    # $6F legato is a note-on like any other HERE: the driver
                    # restarts a wave program per note, but the program it
                    # restarts is this note's OWN capture, which begins wherever
                    # the original's program had got to. Stage A needed a
                    # duplicate instrument slot for exactly this; Stage B does
                    # not need the concept at all.
                    retrig=(e.kind == 'note'),
                    tie=False,
                    rest=(e.kind == 'gate_off')))

    # -- MON tick/frame protocol --------------------------------------------
    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks * self._fpt

    def frame_to_tick(self, frame):
        return max(0, frame // self._fpt)

    def _voice_blocks(self, v):
        """One flat block per voice, as SDI/DMC/Sound Monitor/FC do. HardTrack
        patterns ARE reusable blocks, and feeding them through would let repeated
        patterns share sequences; that is a part-count optimisation, not a
        correctness one, so it is left as a follow-up."""
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        """The player's OWN frequency table (PLAYBOOK: never the generic PAL
        table). Entry 0 is C-0. The table holds 96 notes and MoN's freqtable.inc
        wants 112, so the top octaves are extrapolated by doubling rather than
        read off the end of the table into whatever data follows it."""
        if note < 0:
            return 0
        if note < 96:
            return self.mod.freq(note)
        f = self.mod.freq(note - 12 * ((note - 84) // 12 + 1))
        for _ in range((note - 84) // 12 + 1):
            f = min(0xFFFF, f * 2)
        return f

    def instrument(self, idx):
        """AD/SR + a base waveform for the instrument-slot dedup key.

        The waveform is the FIRST step of the instrument's own wave program --
        HardTrack has no static waveform byte, the program supplies $D404. It
        only ever seeds the key and the driver's idle row; the sounding waveform
        comes from the per-note capture.
        """
        n = idx & 0x1F
        ins = self.mod.instrument(n)
        wp = self.mod.wave_program(ins.wave_cursor)
        return {'ad': ins.ad, 'sr': ins.sr,
                'waveform': (wp[0][0] if wp else 0) or 0x41,
                'pw': ins.pulse_width or 0x800, 'pulseval': 0, 'fx': 0,
                'wave_prog': 0, 'flags': ins.flags, 'raw': list(ins.raw)}


def song_span_frames(shim):
    """One pass through the orderlist, in frames.

    A HardTrack song never ends -- $FF restarts the orderlist and $FD jumps to
    the loop point -- so the span is the frame at which the LAST voice first
    wraps. A voice that halts ($FE) or that never wrapped inside the scan
    contributes its own event span instead, and that case is reported rather
    than silently treated as "the song is this long".
    """
    spans, unwrapped = [], []
    for v in range(3):
        if shim.loops[v] is not None:
            spans.append(shim.loops[v])
        elif shim.events[v]:
            e = shim.events[v][-1]
            spans.append(shim.tick_to_frame(e.tick + e.dur) + shim.onset_delay)
            unwrapped.append(v)
    if unwrapped:
        print(f"  NOTE: voice(s) {unwrapped} never looped within "
              f"{SCAN_FRAMES}f -- using their event span")
    return max(spans) if spans else 0


def build_song(shim, base_name, traces, span, emit=True):
    """Adaptive part-split + build, same policy as the DMC/SM/FC builders."""
    os.makedirs(OUT_DIR, exist_ok=True)

    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, SUB, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)

    bounds, t0 = [], 0
    maxp = int(os.environ.get('HT_MAX_PARTS', '0')) or 10 ** 9
    while t0 < span and len(bounds) < maxp:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    print(f"  packed into {len(bounds)} adaptive part(s)")
    parts = []
    for part, (t0, t1) in enumerate(bounds, 1):
        out = os.path.join(OUT_DIR, f"{base_name}_part{part:02d}.sf2")
        if emit:
            br = BM.build_native_song(shim, SID, SUB, {}, [], win=(t0, t1),
                                      traces=traces)
            BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                        f"({t0 // 50}-{t1 // 50}s, {t0}-{t1}f)")
        parts.append((out, t0, t1))
    if emit:
        BM.prune_stale_parts(os.path.join(OUT_DIR, base_name), len(bounds))
    return parts


def measure_voices(parts, traces, per_instr=None):
    """Per-voice per-frame freq% vs the original, over every part.

    Returns [(raw_pct, raw_n, audible_pct, audible_n, trig_miss, miss,
    trig_miss_silent), ...].
    Ported from the FC/Sound-Monitor builders (same metric, same best-delay
    alignment), plus one attribution column of its own.

    BOTH percentage columns, because they answer different questions and the
    AUDIBLE one is the honest headline: `raw` counts every frame either side has
    a frequency on, including gate-OFF frames where a register nothing can hear
    disagrees; `audible` counts only frames where the ORIGINAL's gate was on. A
    voice with no comparable frames scores None (score_pct), never 100.0 -- an
    empty comparison is "no test ran", not a pass.

    `per_instr` (an `InstrumentScores`) additionally splits the SAME comparison
    by the instrument sounding in the ORIGINAL on each frame, so a residual can
    name a record instead of a voice. It is fed from the identical `m` the voice
    totals use and nothing else, which is what makes the split sum back.

    `trig_miss` / `miss` attribute the residual rather than explaining it away.
    A driver note-on frame CANNOT match here and it is not a decode error: the
    driver holds the note's base pitch on its trigger frame, while HardTrack's
    pipeline still has the PREVIOUS note's frequency in $D400 for two more
    frames. One frame per note, on the frame where the original is playing a
    gate+test transient. Reported, not excluded -- excluding frames picked by a
    rule that correlates with mismatch is how a metric launders itself.
    """
    import bin.mon_sf2_validate as V
    import mon_fidelity as F
    from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
    orig = traces[0]
    ok, tot = [0, 0, 0], [0, 0, 0]
    aok, atot = [0, 0, 0], [0, 0, 0]
    tmiss, miss, tsil = [0, 0, 0], [0, 0, 0], [0, 0, 0]
    for pf, t0, t1 in parts:
        if not os.path.exists(pf):
            continue
        sf2 = bytearray(open(pf, "rb").read())
        info = SF2DriverInfo()
        sla = parse_sf2_blocks(sf2, info)
        probe = pf[:-4] + ".sid"
        open(probe, "wb").write(V._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003))
        dur = t1 - t0
        prb = F.per_frame(probe, [f"-t{dur // 50 + 2}"])
        n = min(len(prb), dur, len(orig) - t0) - 4
        if n <= 0:
            continue

        def sc(dly):
            s = 0
            for i in range(0, n, 3):
                for v in range(3):
                    if 0 <= t0 + dly + i < len(orig):
                        a = orig[t0 + dly + i][0][v]['freq']
                        b = prb[i][0][v]['freq']
                        if a and b and F._semi(a) == F._semi(b):
                            s += 1
            return s
        dly = max(range(-6, 10), key=sc)
        for v in range(3):
            for i in range(n):
                j = t0 + dly + i
                if not (0 <= j < len(orig)):
                    continue
                o = orig[j][0][v]
                a, b = o['freq'], prb[i][0][v]['freq']
                if a is None and b is None:
                    continue
                m = bool(a and b and F._semi(a) == F._semi(b))
                tot[v] += 1
                ok[v] += m
                if per_instr is not None:
                    per_instr.add(v, j, m)
                if (o['wf'] or 0) & 1:      # ORIGINAL's gate on == audible frame
                    atot[v] += 1
                    aok[v] += m
                if not m:
                    miss[v] += 1
                    pw = prb[i][0][v]['wf'] or 0
                    pw0 = prb[i - 1][0][v]['wf'] or 0 if i else 0
                    if (pw & 1) and not (pw0 & 1):     # driver note-on frame
                        tmiss[v] += 1
                        # is the frame actually silent? bit 3 is the SID TEST
                        # bit: it resets the oscillator, so a pitch difference
                        # under it produces no sound at all. Counted rather
                        # than asserted -- "inaudible" is a claim with a number.
                        if (o['wf'] or 0) & 0x08:
                            tsil[v] += 1
    return [(score_pct(ok[v], tot[v]), tot[v],
             score_pct(aok[v], atot[v]), atot[v], tmiss[v], miss[v], tsil[v])
            for v in range(3)]


def main():
    try:
        mod = HardTrackModule.from_sid(SID)
    except HardTrackError as e:
        sys.exit(f"REFUSING: {os.path.basename(SID)}: {e}")
    shim = HardTrackShim(mod, SUB)
    base = os.path.splitext(os.path.basename(SID))[0]
    if SUB:
        base += f"_sub{SUB}"
    span = song_span_frames(shim)
    if not span:
        sys.exit(f"REFUSING: {base} decoded no events -- nothing to build")
    notes = [sum(1 for e in shim.voices[v] if not e.rest) for v in range(3)]
    rests = [sum(1 for e in shim.voices[v] if e.rest) for v in range(3)]
    lega = [sum(1 for e in shim.events[v] if e.legato) for v in range(3)]
    print(f"{base}: speed={shim.speed} fpt={shim.frames_per_tick} "
          f"span={span // 50}s ({span}f) notes={notes} gate-offs={rests} "
          f"legato={lega} instr={mod.num_instruments}"
          f"{'' if mod.instrument_count_verified else ' (UNVERIFIED count)'}")

    import mon_fidelity as F
    if WARG.lower() not in ("auto", "a"):
        span = min(span, int(WARG) * 50)
    secs = span // 50 + 4
    print(f"  tracing {secs}s once...")
    # The THIRD element is the $D418 passband. Without it `_filt_set_row`
    # defaults to low-pass, so every render came out low-pass whatever the tune
    # actually selected -- `Love_tune_2` uses low+band on 100% of frames and was
    # rebuilt as low-only on 100% of them. It is inaudible to this builder's own
    # fidelity report, which scores frequency and nothing else, and it survived
    # until the rung-4 listening pass measured the render as consistently darker
    # (centroid -99 Hz, rolloff -280 Hz). The identical defect was found and
    # fixed on MoN once already -- see `passband_trace`'s docstring, which names
    # Cybernoid_II dropping its band exactly this way.
    # HT_NO_PASSBAND=1 reproduces the PRE-cffc51e 2-tuple on purpose, so the
    # passband's effect can be A/B'd against today's builder on BOTH sides. The
    # first attempt at that A/B compared 2026-08-09 artifacts with 2026-08-12
    # ones and folded three days of unrelated builder changes into the deltas.
    traces = (F.per_frame(SID, [f'-a{SUB}', f'-t{secs}']),
              BM.filter_trace(SID, SUB, secs))
    if os.environ.get("HT_NO_PASSBAND") != "1":
        traces = traces + (BM.passband_trace(SID, SUB, secs),)
    shim.main_vol = BM.master_volume(SID, SUB, secs)

    parts = build_song(shim, base, traces, span)

    # Per-instrument attribution: label every ORIGINAL frame with the record
    # sounding on it, keyed by ADSR against HardTrack's own instrument table.
    # Its own trace, not `traces[0]`: `mon_fidelity.per_frame` is the PROJECTION
    # of `siddump_frames_full` that drops $D405/$D406, which is the very pair
    # this key is built on. Same siddump, same window, one extra run.
    full = siddump_frames_full(SID, [f'-a{SUB}', f'-t{secs}'])
    on = onsets_with_registers(full)
    kv = key_reliability(on, full)
    declared = {}
    for i in range(mod.num_instruments):
        ins = mod.instrument(i)
        declared.setdefault((ins.ad << 8) | ins.sr, []).append(i)
    per_instr = InstrumentScores(
        frame_labels(on, instrument_labels(declared, on), len(full))[0]
    ) if kv.usable else None

    res = measure_voices(parts, traces, per_instr)
    print("  FIDELITY (per-frame freq semitone vs original, all parts):")
    print("    voice |  raw  (n)      | AUDIBLE gate-on (n) | misses on the "
          "driver's note-on frame")
    for i, (raw, rn, aud, an, tm, ms, ts) in enumerate(res):
        rs = f"{raw:5.1f}%" if raw is not None else "  n/a "
        as_ = f"{aud:5.1f}%" if aud is not None else "  n/a "
        print(f"      {i}   | {rs} ({rn:5d}) | {as_} ({an:5d})     | "
              f"{tm:4d} of {ms:4d} ({ts} under the SID TEST bit)")
    if per_instr is not None:
        agg = per_instr.totals()
        sums_back = all(agg.get(v, (0, 0))[1] == res[v][1] for v in range(3))
        print(f"  PER INSTRUMENT (same comparison, split by the record sounding "
              f"in the ORIGINAL; ADSR key: {kv.verdict})")
        print(f"    voice instr    freq%      n     (split sums back to the "
              f"per-voice n: {sums_back})")
        for v, lab, pct, okn, n in per_instr.rows():
            ps = f"{pct:5.1f}%" if pct is not None else "  n/a "
            note = "  <- frames before the first note-on" if lab == "-" else ""
            print(f"      {v}   {lab:>6}   {ps} {n:6d}{note}")
        print("    a label that is a letter is an envelope HardTrack's own "
              "instrument table does not\n    declare -- the player writes it "
              "from somewhere else, and no record owns those frames.")
    print("    the note-on column is a driver/player structural difference, not "
          "a decode error:\n    the driver holds base pitch on its trigger "
          "frame where HardTrack still has the\n    previous note's frequency "
          "(one frame per note, under a gate+test transient).")


if __name__ == "__main__":
    main()
