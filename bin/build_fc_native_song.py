"""Future Composer ($1800 V1.0) SID -> native SF2 (Stage B).

R13 / ROADMAP B4. FC was the last ported player with no native driver -- Stage A
(bin/fc_to_sf2.py) transpiles to stock Driver 11, which is where FC's headline
defect lives: SF2II's Driver 11 mishandles BOTH all-rest sequences AND long rest
prefixes, so Triangle_Intro's lead (silent for 288 ticks, then enters) will not
gate. See docs/players/FUTURECOMPOSER.md's "Open issues". A native driver writes
its own sequencer, so that constraint simply does not exist here.

This is the CHEAPEST Stage B in the project and deliberately so -- it is the
test that the R1-R3 consolidated pipeline generalises to a new player. It adds
NO new driver: a MON-compatible shim feeds bin/build_mon_native_song's
build_native_song, the same trace-driven engine behind Hawkeye / Hubbard / DMC /
Sound Monitor / SDI, and emit_one assembles MoN's driver. So FC's arps, drums and
PWM come out of the per-frame CAPTURE rather than being modelled -- exactly the
PLAYBOOK Sec.2 "parse statically, trace the synth side" split, which is the right
mode for FC because its parser is validated byte-exact (fc_validate: 25/27
voices note-accurate; the FC->FC round-trip is byte-identical in siddump).

  py -3 bin/build_fc_native_song.py [SID/Fun_Fun/Triangle_Intro.sid] [secs|auto]

Output: out/fc/<name>_part<NN>.sf2
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent
from sidm2.fc_parser import parse_fc, detect_player, NUM_NOTES
from sidm2.fidelity_common import score_pct
from sidm2.sf2_caps import CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP
from fc_to_sf2 import load_sid
import build_mon_native_song as BM

SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "SID", "Fun_Fun", "Triangle_Intro.sid")
warg = sys.argv[2] if len(sys.argv) > 2 else "auto"


class FCShim:
    """MON-compatible view of a decoded Future Composer song.

    DECODE-driven (notes/durations/instruments from fc_parser), not
    onset-aligned like the SDI/DMC shims: FC's static decode is trustworthy
    (see the module docstring), so there is no reason to re-derive note
    placement from trace gate-rises -- and doing so would LOSE the rests,
    which is the whole point of building FC natively.
    """

    tempo_toggle = False      # FC has one master speed, no swing/toggle grid
    hard_restart = 0          # FC re-gates via its own waveform/gate bits; the
                              # per-frame capture reproduces them
    snap_gate = True
    hp_engine = 0             # FC pulse/PWM comes from captured programs, not a
                              # modelled engine (see PLAYBOOK: captured != modelled)

    def __init__(self, fc):
        self.fc = fc
        self.speed = fc.speed
        # FC's master-speed counter reloads from $211d, so the player processes a
        # row every (speed+1) frames; a duration byte D runs D..0..-1 = D+1 ticks
        # (docs/players/FUTURECOMPOSER.md "Timing"). Both +1s are real: dropping
        # the duration one makes dur5:dur2 read 5:2 instead of the true 6:3.
        self._fpt = fc.speed + 1
        self.onset_delay = 0
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            cur = 0
            out = self.voices[v]
            for n in fc.voices[v]:
                # FC instrument 0 means "no change" -- the player carries the
                # current sound (Stage A's _instr_change does the same, and
                # sf2_to_fc records that getting this wrong resets instruments
                # to 0 mid-song). Thread it forward.
                if n.instr:
                    cur = n.instr
                out.append(MONEvent(
                    note=(0 if n.is_rest else n.note),
                    dur=max(1, n.dur + 1),
                    instr=cur,
                    wprog=0,
                    retrig=not n.tie,
                    tie=n.tie,
                    rest=n.is_rest))

    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks * self._fpt

    def frame_to_tick(self, frame):
        return max(0, frame // self._fpt)

    def _voice_blocks(self, v):
        """One flat block per voice -- the same first-cut shape SDI/DMC/Sound
        Monitor use. FC's parser DOES expose voice_blocks (51/41/51 blocks on
        Triangle_Intro), and feeding those through instead would let repeated
        blocks share sequences and cut the sequence count; that is a part-count
        optimisation, not a correctness one, so it is left as a follow-up."""
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        """FC's OWN freq table, per PLAYBOOK: never the generic PAL table (which
        is a semitone off and detuned vs real players -- Stage A hit exactly this
        and had to calibrate_base()-1)."""
        return self.fc.freq(note)

    def instrument(self, idx):
        insts = self.fc.instruments
        if 0 <= idx < len(insts):
            ins = insts[idx]
            # ins.waveform is FC byte [1]. NOTE the field named `arp` (byte [6])
            # is NOT the arp on V1.0 -- V1.0 reads arp offsets from byte [5]
            # (the field named `vibrato`); the dataclass names follow the V4.1
            # manual, which docs/players/FUTURECOMPOSER.md flags as wrong here.
            # Irrelevant for Stage B (arps/drums arrive via the capture) but a
            # live trap for anyone extending this.
            return {'ad': ins.ad, 'sr': ins.sr,
                    'waveform': ins.waveform or 0x41,
                    'pw': 0x800, 'pulseval': 0, 'fx': 0,
                    'wave_prog': 0, 'flags': 0, 'raw': list(ins.raw)}
        return {'ad': 0x09, 'sr': 0x00, 'waveform': 0x41,
                'pw': 0x800, 'pulseval': 0, 'fx': 0,
                'wave_prog': 0, 'flags': 0, 'raw': []}


def song_span_frames(shim):
    """Total frames, from the tick total. All three FC voices are expected to
    span the SAME tick count (Triangle_Intro: 2448 each) -- a mismatch means a
    mis-decode, so report it rather than silently using the max."""
    spans = [sum(e.dur for e in shim.voices[v]) for v in range(3)]
    if len(set(s for s in spans if s)) > 1:
        print(f"  NOTE: voice tick spans differ {spans} -- using the longest "
              f"(all three normally match; a mismatch can mean a mis-decode)")
    return shim.tick_to_frame(max(spans))


def build_song(shim, base_name, traces, span, emit=True):
    """Adaptive part-split + build. Same policy as the DMC/Sound-Monitor
    builders, using the caps shared via sidm2.sf2_caps (R2)."""
    out_dir = os.path.join(ROOT, "out", "fc")
    os.makedirs(out_dir, exist_ok=True)

    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, 0, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)

    bounds, t0 = [], 0
    maxp = int(os.environ.get('FC_MAX_PARTS', '0')) or 10 ** 9
    while t0 < span and len(bounds) < maxp:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    print(f"  packed into {len(bounds)} adaptive part(s)")
    parts = []
    for part, (t0, t1) in enumerate(bounds, 1):
        out = os.path.join(out_dir, f"{base_name}_part{part:02d}.sf2")
        if emit:
            br = BM.build_native_song(shim, SID, 0, {}, [], win=(t0, t1),
                                      traces=traces)
            BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                        f"({t0 // 50}-{t1 // 50}s, {t0}-{t1}f)")
        parts.append((out, t0, t1))
    if emit:
        BM.prune_stale_parts(os.path.join(out_dir, base_name), len(bounds))
    return parts


def measure_voices(parts, traces):
    """Per-voice per-frame freq% vs the original, over every part.

    Returns [(raw_pct, raw_n, audible_pct, audible_n), ...] per voice.

    BOTH numbers, deliberately. Ported from
    build_soundmonitor_native_song.measure_song_voices (same metric, same
    best-delay alignment) but reporting an extra AUDIBLE column, because the raw
    number is actively misleading for FC and it took a measurement to see why:

    An FC rest is note index >= 96, which the player resolves by reading PAST its
    96-entry freq table -- so during a rest the original leaves a near-zero
    **$0002** in $D400 with the **gate OFF**. This build emits a real rest, so
    every one of those frames counts as a freq "mismatch" on a register nothing
    can hear. On Triangle_Intro voice 1 that is 636 of 1496 frames: raw 57.8%,
    audible 100.0%. Quoting the raw figure alone would report a broken lead that
    is in fact frame- and pitch-exact wherever it sounds.

    The inverse trap is just as real, so the audible column carries its own n:
    FC gates briefly (percussive envelopes), so a voice may only be audible for
    70 of 1496 frames. 100% of 70 is a real but SMALL sample -- never quote it
    bare. A voice with no comparable frames scores None (score_pct), never
    100.0: an empty comparison is "no test ran".
    """
    import bin.mon_sf2_validate as V
    import mon_fidelity as F
    from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
    orig = traces[0]
    ok, tot = [0, 0, 0], [0, 0, 0]
    aok, atot = [0, 0, 0], [0, 0, 0]
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
                if (o['wf'] or 0) & 1:      # ORIGINAL's gate on == audible frame
                    atot[v] += 1
                    aok[v] += m
    return [(score_pct(ok[v], tot[v]), tot[v],
             score_pct(aok[v], atot[v]), atot[v]) for v in range(3)]


def main():
    d, la = load_sid(SID)
    if not detect_player(d, la):
        sys.exit(f"REFUSING: {os.path.basename(SID)} is not the $1800 FC V1.0 "
                 f"player this builder supports (detect_player said no). The "
                 f"other Fun_Fun rips use a second player (init $C000) or Sound "
                 f"Monitor -- see docs/players/FUTURECOMPOSER.md.")
    fc = parse_fc(d, la)
    shim = FCShim(fc)
    base = os.path.splitext(os.path.basename(SID))[0]
    span = song_span_frames(shim)
    notes = [len(shim.voices[v]) for v in range(3)]
    rests = [sum(1 for e in shim.voices[v] if e.rest) for v in range(3)]
    print(f"{base}: speed={fc.speed} fpt={shim.frames_per_tick} "
          f"span={span // 50}s ({span}f) notes={notes} rests={rests} "
          f"instr={len(fc.instruments)}")

    import mon_fidelity as F
    secs = span // 50 + 4
    print(f"  tracing full song ({secs}s) once...")
    traces = (F.per_frame(SID, [f'-t{secs}']), BM.filter_trace(SID, 0, secs))

    if warg.lower() not in ("auto", "a"):
        span = min(span, int(warg) * 50)
    parts = build_song(shim, base, traces, span)

    res = measure_voices(parts, traces)
    print("  FIDELITY (per-frame freq semitone vs original, all parts):")
    print("    voice |  raw  (n)      | AUDIBLE gate-on (n)")
    for i, (raw, rn, aud, an) in enumerate(res):
        rs = f"{raw:5.1f}%" if raw is not None else "  n/a "
        as_ = f"{aud:5.1f}%" if aud is not None else "  n/a "
        print(f"      {i}   | {rs} ({rn:5d}) | {as_} ({an:5d})")
    print("    raw counts gate-OFF frames, where FC parks a near-zero $0002 in "
          "$D400\n    (note>=96 reads past its freq table) and this build emits a "
          "real rest --\n    an inaudible divergence. See measure_voices'"
          " docstring for both traps.")


if __name__ == "__main__":
    main()
