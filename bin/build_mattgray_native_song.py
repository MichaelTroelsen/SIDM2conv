"""Matt Gray (own from-scratch engine) SID -> native SF2 (Stage B).

Stage A (`bin/mattgray_to_sf2.py`) transpiles the SCORE onto stock Driver 11
and gets it exactly right -- sequencer onset 100% / pitch 100% on all 18 tunes
-- but only on *plain* instruments, and `docs/players/MATTGRAY.md` is blunt
about the rest: it "knowingly omits the slide/arp/PWM/drum engine, so timbre is
NOT claimed and the audio will not sound like the originals."

That doc lists Stage B as "the slide engine ($fb/$fc + A1[0]/A1[4]), the
arpeggio table, the A0[4] pulse sweep, and the A0[7] bit0 drum path" -- i.e. as
four more engines to reverse-engineer. **It does not need any of them.** A
trace-driven native build CAPTURES the synth side per frame from the original's
own siddump output, so whatever those four engines did is simply what the
driver replays. This is the same move that dissolved every Stage A loss class
for HardTrack at once, and it adds NO new driver: a MON-compatible shim feeds
`build_mon_native_song.build_native_song`, the engine already behind Hawkeye /
Hubbard / DMC / Sound Monitor / SDI / FC / HardTrack.

What crosses the shim boundary is only the SEQUENCER -- notes, durations,
instrument indices -- which is precisely the part Stage A validated to 100%.

  py -3 bin/build_mattgray_native_song.py [SID/Gray_Matt/Last_Ninja_2.sid] [secs|auto] [sub]

Output: out/mattgray_native/<name>_sub<NN>_part<NN>.sf2
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent
from sidm2.mattgray_parser import MattGrayError, parse_sid, simulate
from sidm2.sf2_caps import CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP
import build_mon_native_song as BM

def _argv(i, default, cast=str):
    """argv element i, or `default` if absent OR not parseable.

    These are read at IMPORT time, so anything that imports this module
    inherits whatever argv it happens to be running under. `int(sys.argv[3])`
    raised ValueError under pytest (argv[3] is a test path), which took out
    every test that imports the builder -- including tests about entirely
    unrelated things. Falling back to the default keeps import a pure
    operation; the real CLI path passes proper values.
    """
    if len(sys.argv) <= i:
        return default
    try:
        return cast(sys.argv[i])
    except (TypeError, ValueError):
        return default


SID = _argv(1, os.path.join("SID", "Gray_Matt", "Last_Ninja_2.sid"))
WARG = _argv(2, "auto")
SUB = _argv(3, 0, int)

SCAN_FRAMES = 6000
OUT_DIR = os.path.join(ROOT, "out", "mattgray_native")


class MattGrayShim:
    """MON-compatible view of a decoded Matt Gray tune.

    Only the sequencer crosses this boundary. Every timbre decision -- the
    slide engine, the arpeggio table, the pulse sweep, the drum path -- is left
    to `build_native_song`'s per-note capture, which is exactly why none of
    them has to be modelled here.
    """

    tempo_toggle = False      # one global divider; the engine has no swing grid
    hard_restart = 0          # no Hubbard kill-ADSR engine in this player
    # Snap each capture to the real gate rise (+-2 frames). HardTrack wants
    # this; Matt Gray does NOT, and the difference is measured rather than
    # assumed -- see MG_SNAP below and the sweep in docs/players/MATTGRAY.md.
    snap_gate = os.environ.get('MG_SNAP', '0') == '1'
    hp_engine = 0             # the A0[4] pulse sweep is captured, not modelled
    filter_tie = 0
    # Matt Gray's drum path and slide engine write real per-frame Hz deltas
    # that can land in $40xx-$43xx, which is the range the driver's SCALED-FM
    # entry marker claims. Hubbard and HardTrack both had to disable it for the
    # same reason; leaving it on freezes such a note at the wrong absolute
    # frequency for its whole tail while its waveform stays byte-exact.
    no_fm_scale = 1
    # Gate-off frames write this instrument's RELEASE waveform verbatim instead
    # of the driver's default `program & $fe`. Matt Gray needs it: the player
    # writes $00 -- no waveform bits at all, so the oscillator is SILENT -- on
    # the gate-off frames of some instruments, while others really do keep
    # `waveform & $fe`. Measured on Last_Ninja_2 sub 0, gate-off frames:
    # voice 0 is $00 x193, voice 1 is $00 x193 + $40 x97, voice 2 is $10 x624.
    # A single constant cannot express that; a per-instrument byte can.
    # Derived from the trace by `release_waveforms()`, never from a flag bit.
    release_wf = 1

    def __init__(self, song, frames=SCAN_FRAMES):
        self.song = song
        self.subtune = song.subtune
        self._fpt = song.frames_per_tick
        self.events = simulate(song, frames)
        # The driver's own phase: `reset_voices` leaves tempo_ctr = 1, so the
        # first row lands a frame in. Derived from the walk's recorded frames
        # rather than assumed -- if the file disagrees, say so instead of
        # silently keeping a wrong phase (the same guard HardTrack's shim uses,
        # which is what caught its first-row offset).
        self.onset_delay = 1
        first = [e for evs in self.events for e in evs[:1]]
        if first:
            d = {e.frame - e.tick * self._fpt for e in first}
            if d != {1}:
                self.onset_delay = min(d)
                print(f"  NOTE: first-row phase is {sorted(d)}, not 1 -- "
                      f"using {self.onset_delay}")

        self.voices = [[] for _ in range(3)]
        for v in range(3):
            out = self.voices[v]
            evs = self.events[v]
            for i, e in enumerate(evs):
                # Duration in TICKS: the gap to the next event on this voice,
                # taken from the walk itself rather than from the duration byte,
                # so a sticky duration that the sequencer re-used is already
                # accounted for.
                nxt = evs[i + 1].tick if i + 1 < len(evs) else e.tick + e.duration + 1
                dur = max(1, nxt - e.tick)
                out.append(MONEvent(
                    note=(0 if e.is_rest else e.note),
                    dur=dur,
                    instr=e.instrument,
                    wprog=0,
                    retrig=not e.is_rest,
                    tie=False,
                    rest=e.is_rest))

    # -- MON tick/frame protocol --------------------------------------------
    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks * self._fpt

    def frame_to_tick(self, frame):
        return max(0, frame // self._fpt)

    def _voice_blocks(self, v):
        """One flat block per voice, as the SDI/DMC/SM/FC/HardTrack shims do."""
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        """The player's OWN frequency table -- never the generic PAL table.

        The table holds 96 entries and MoN's freqtable.inc wants 112, so the top
        octaves are extrapolated by doubling rather than read off the end of the
        table into whatever data follows it.
        """
        if note < 0:
            return 0
        n = len(self.song.freq_lo)
        if note < n:
            return self.song.freq(note)
        oct_up = (note - (n - 12)) // 12 + 1
        f = self.song.freq(note - 12 * oct_up)
        for _ in range(oct_up):
            f = min(0xFFFF, f * 2)
        return f

    def instrument(self, idx):
        """AD/SR + a base waveform for the instrument-slot dedup key.

        Only seeds the key and the driver's idle row; the sounding waveform
        comes from the per-note capture.
        """
        ins = self.song.instruments[idx % len(self.song.instruments)] \
            if self.song.instruments else None
        if ins is None:
            return {'ad': 0x00, 'sr': 0xF0, 'waveform': 0x41, 'pw': 0x800,
                    'pulseval': 0, 'fx': 0, 'wave_prog': 0, 'flags': 0, 'raw': []}
        return {'ad': ins.ad, 'sr': ins.sr,
                'waveform': ins.waveform or 0x41,
                'pw': ins.pulse_width or 0x800, 'pulseval': 0, 'fx': 0,
                'wave_prog': 0, 'flags': ins.flags, 'raw': list(ins.raw),
                # falls back to the driver's default when the trace never showed
                # this instrument releasing (see release_waveforms)
                'release_wf': getattr(self, '_relwf', {}).get(
                    idx % max(1, len(self.song.instruments)),
                    (ins.waveform or 0x41) & 0xFE)}


def merge_sounding_rests(shim, per_frame):
    """Absorb a REST into the preceding note while the original is still SOUNDING.

    A rest is emitted as bare GATE-OFF rows carrying no wave, pulse or FM
    program (`build_mon_native_song`, the `ev.rest` branch), so the pitch
    FREEZES on whatever the previous note left in the register. Matt Gray's
    arpeggio does not stop at the gate fall -- it keeps stepping through the
    release, an octave cycle on a still-ringing triangle.

    Measured on Last_Ninja_2 sub 0, splitting every sounding gate-off run by
    the event that owns it: all 313 runs that live inside a NOTE's own span are
    byte-exact, and all 276 that land in a REST are wrong -- ours frozen on one
    constant, the original cycling (79% of the wrong frames are an exact x2,
    x4, /2 or /4 of the original). The per-note capture already reproduces the
    313; this puts the other 276 back inside it instead of adding an engine.

    Only rests the original actually sounds through are merged, and only while
    the note stays inside FM_CAP -- past that `fm_program_for` freezes anyway,
    so the merge would buy nothing and still cost the program space.
    """
    from dataclasses import replace
    merged = span = 0
    for v in range(3):
        out, starts, tk = [], [], 0
        for ev in shim.voices[v]:
            if ev.rest and out and not out[-1].rest:
                p_tk = starts[-1]
                comb = out[-1].dur + ev.dur
                dur_f = (shim.tick_to_frame(p_tk + comb)
                         - shim.tick_to_frame(p_tk))
                if dur_f <= BM.FM_CAP and _rest_sounds(shim, per_frame, v,
                                                       tk, ev.dur):
                    out[-1] = replace(out[-1], dur=comb)
                    tk += ev.dur
                    merged += 1
                    span += ev.dur
                    continue
            out.append(ev)
            starts.append(tk)
            tk += ev.dur
        shim.voices[v] = out
    return merged, span


def _rest_sounds(shim, per_frame, v, tk, dur):
    """True iff the original has a gated-OFF but still audible frame in this
    rest -- waveform bits set (the oscillator has a shape) and a non-zero
    frequency (it is advancing). A rest the player silences with $00 is left
    alone: nothing is heard through it, so a capture would only cost space."""
    f0 = shim.tick_to_frame(tk) + shim.onset_delay
    f1 = shim.tick_to_frame(tk + dur) + shim.onset_delay
    for f in range(f0, min(f1, len(per_frame))):
        st = per_frame[f][0][v]
        if st['wf'] is None or (st['wf'] & 1):
            continue
        if (st['wf'] & 0xF0) and st['freq']:
            return True
    return False


def release_waveforms(shim, per_frame):
    """{instrument: release waveform byte}, measured from the original's trace.

    Stage B captures rather than models, and this is the same idea one level
    up: instead of hunting for the instrument-record bit that decides whether a
    voice is silenced on release, look at what the player ACTUALLY wrote to
    $D404 while each instrument was ringing out.

    For every note the sequencer decoded, walk the frames from its gate fall to
    the next note on that voice and take the modal gate-off waveform. A voice
    that is never released under an instrument contributes nothing, and that
    instrument keeps the driver's default (`waveform & $fe`) rather than being
    assigned a guessed byte.
    """
    import collections
    votes = collections.defaultdict(collections.Counter)
    for v in range(3):
        evs = shim.events[v]
        for i, e in enumerate(evs):
            if e.is_rest:
                continue
            start = e.frame
            end = evs[i + 1].frame if i + 1 < len(evs) else start + 200
            for f in range(start, min(end, len(per_frame))):
                wf = per_frame[f][0][v]['wf']
                if wf is None or (wf & 1):
                    continue                 # still gated on -- not a release
                votes[e.instrument][wf] += 1
    out = {}
    for instr, c in votes.items():
        wf, n = c.most_common(1)[0]
        # only accept a byte the instrument actually spends its releases on;
        # a near-tie means the release depends on something this does not
        # model, and the default is safer than a coin flip.
        if n >= 0.6 * sum(c.values()):
            out[instr] = wf
    return out


def song_span_frames(shim):
    """The decoded span, in frames -- the last event end across the voices."""
    spans = []
    for v in range(3):
        if shim.events[v]:
            e = shim.events[v][-1]
            spans.append(shim.tick_to_frame(e.tick + e.duration + 1)
                         + shim.onset_delay)
    return max(spans) if spans else 0


def build_song(shim, base_name, traces, span, emit=True):
    """Adaptive part-split + build, same policy as the sibling builders."""
    os.makedirs(OUT_DIR, exist_ok=True)

    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, SUB, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)

    bounds, t0 = [], 0
    maxp = int(os.environ.get('MG_MAX_PARTS', '0')) or 10 ** 9
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


def measure_voices(parts, traces):
    """Per-voice per-frame freq% vs the original, over every part.

    Reuses the HardTrack builder's metric verbatim -- same two columns, same
    best-delay alignment, same refusal to score an empty comparison as 100%.
    Quote BOTH: `raw` counts every frame either side has a frequency on;
    `audible` counts only frames where the ORIGINAL's gate was on.

    ** `audible` is the WRONG name on this player, and believing it cost a
    release.** A gate-off frame is only inaudible when the waveform has no bits
    set; Matt Gray releases with $10/$40/$80 still selected, so a voice in
    RELEASE is sounding and its pitch is heard. Scoring gate-on frames only,
    this column read 99.5-100% on sub 0 while the release tails of 236 rests
    played a frozen note against the original's arpeggio -- see the rung-4
    section of docs/players/MATTGRAY.md. The defect lived entirely in the
    column this one discards.
    """
    import build_hardtrack_native_song as HT
    return HT.measure_voices(parts, traces)


def main():
    try:
        song = parse_sid(SID, subtune=SUB)
    except MattGrayError as e:
        print(f"REFUSED: {e}")
        return 1
    # REFUSE an incomplete decode rather than emit a plausible-looking SF2 from
    # it. The relocating compilation can cut a pattern short (`_read_pattern`
    # reports it via `truncated_patterns`), and the sequencer then walks data
    # that simply is not there. On Last_Ninja_2 subtune 7 -- the ONLY subtune of
    # the 13 with a truncated pattern -- that renders voice 0 at 1.9% audible
    # while the other twelve sit at 92-100%. A 1:1 correlation with a named
    # cause is not a residual to report in a table; it is a file we cannot
    # build, and saying so is cheaper than a reader trusting the output.
    if song.truncated_patterns and os.environ.get('MG_ALLOW_TRUNCATED') != '1':
        print(f"REFUSED: {song.truncated_patterns} pattern(s) truncated by the "
              f"relocating copy -- the decode is incomplete, so the build would "
              f"be wrong in a way this report cannot see. "
              f"Set MG_ALLOW_TRUNCATED=1 to build it anyway (for investigation).")
        return 1
    if song.layout != 'driller':
        print(f"  NOTE: tables located by {song.layout} (not the validated "
              f"'driller' fast path) -- the decode is unverified for this file")

    shim = MattGrayShim(song)
    base = f"{os.path.splitext(os.path.basename(SID))[0]}_sub{SUB:02d}"
    span = song_span_frames(shim)
    notes = [sum(1 for e in shim.voices[v] if not e.rest) for v in range(3)]
    rests = [sum(1 for e in shim.voices[v] if e.rest) for v in range(3)]
    print(f"{base}: tempo={song.tempo} fpt={shim.frames_per_tick} "
          f"span={span // 50}s ({span}f) notes={notes} rests={rests} "
          f"instr={len(song.instruments)}")
    if span <= 0:
        print("REFUSED: the sequencer decoded no events")
        return 1

    import mon_fidelity as F
    global WARG
    if WARG.lower() not in ("auto", "a"):
        span = min(span, int(WARG) * 50)
    secs = span // 50 + 4
    print(f"  tracing {secs}s once...")
    # The third element is the $D418 passband. Omitting it silently rebuilds
    # every render low-pass whatever the tune selected -- the defect the
    # rung-4 listening pass caught on HardTrack, and that MoN's Cybernoid_II
    # had before it.
    # siddump's `-a` indexes the songs that EXIST; SUB indexes the track-pointer
    # TABLE, whose entry 0 is null on most builds. They agree on Last Ninja 2 and
    # Tusker and differ by one everywhere else, so passing SUB straight through
    # traced the WRONG TUNE on every newly-located file -- Motocross scored
    # 30.6%/62.0% against a tune it was not playing. Derived by the parser
    # (`psid_song`), never assumed to be an offset.
    a = song.psid_song
    if a != SUB:
        print(f"  NOTE: subtune {SUB} is PSID song {a} "
              f"(track-table entry 0 is not a tune) -- tracing -a{a}")
    traces = (F.per_frame(SID, [f'-a{a}', f'-t{secs}']),
              BM.filter_trace(SID, a, secs),
              BM.passband_trace(SID, a, secs))
    shim.main_vol = BM.master_volume(SID, a, secs)
    shim._relwf = release_waveforms(shim, traces[0])
    if os.environ.get('MG_NO_REST_MERGE') != '1':
        nm, ns = merge_sounding_rests(shim, traces[0])
        if nm:
            print(f"  merged {nm} sounding rest(s) into the preceding note "
                  f"({ns} ticks) -- the arpeggio keeps running through the "
                  f"release, and a bare rest row would freeze it")
    if shim._relwf:
        import collections as _c
        dist = _c.Counter(f"${w:02x}" for w in shim._relwf.values())
        print(f"  release waveforms: {len(shim._relwf)} instrument(s) "
              f"{dict(dist)}")

    parts = build_song(shim, base, traces, span)

    res = measure_voices(parts, traces)
    print("  FIDELITY (per-frame freq semitone vs original, all parts):")
    print("    voice |  raw  (n)      | AUDIBLE gate-on (n) | misses on the "
          "driver's note-on frame")
    for i, (raw, rn, aud, an, tm, ms, ts) in enumerate(res):
        rs = f"{raw:5.1f}%" if raw is not None else "  n/a "
        as_ = f"{aud:5.1f}%" if aud is not None else "  n/a "
        print(f"      {i}   | {rs} ({rn:5d}) | {as_} ({an:5d})     | "
              f"{tm:4d} of {ms:4d} ({ts} under the SID TEST bit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
