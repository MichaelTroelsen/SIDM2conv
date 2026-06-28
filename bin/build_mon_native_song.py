"""Stage B (native driver) — emit a Hawkeye/MoN tune as a native-driver .sf2.

Feeds the RE'd + validated MoN decode (sidm2/mon_parser.py + bin/mon_to_sf2.py)
into the from-scratch native SF2 driver (drivers_src/mon/, a copy of the
ROMUZAK/Galway engine: SF2 sequencer + wave/pulse/filter runners + per-frame FM
pitch program + the song's OWN freq table). The engine is player-agnostic; the
MoN-specific work is the extraction here.

Milestone B1: notes + MoN's own freq table (correct tuning) + AD/SR/waveform +
static pulse width, played through the native driver, loadable in stock SF2II.
PWM / filter sweeps / per-frame slides / the gate envelope follow (B2+).

Usage:  py -3 bin/build_mon_native_song.py [SID/Tel_Jeroen/Hawkeye.sid] [subtune]
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_romuzak_driver_full as B
import build_romuzak_native_song as RN
import mon_to_sf2
from sidm2.mon_parser import load_sid, MON

MON_DIR = os.path.join(ROOT, "drivers_src", "mon")
ROM_DIR = os.path.join(ROOT, "drivers_src", "romuzak")


def write_mon_freqtable(m):
    """MoN's own note->freq table ($8337, 2 bytes/note) -> mon/freqtable.inc, so the
    native driver's frequencies match the original byte-for-byte (fixes the ~0.35
    semitone tuning gap vs Driver-11's PAL table). Indexed by note byte ($00=C-0)."""
    words = [m.note_freq(i) & 0xFFFF for i in range(0x70)]
    with open(os.path.join(MON_DIR, "freqtable.inc"), "w") as f:
        f.write("; MoN $8337 note->freq table (exact tuning, for byte fidelity)\n")
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k + 8]) + "\n")


def static_pulse(pw):
    """Milestone-B1 pulse program: hold the instrument's base width (no PWM yet).
    Format: 8X XX = set width (X|XX) for 1 frame; 7f = freeze."""
    return [(0x80 | ((pw >> 8) & 0x0F), pw & 0xFF, 1), (0x7F, 0, 0)]


from sidm2.galway_to_driver11 import D11Row, SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON
from sidm2.galway_driver11_emitter import segment_track

FM_CAP = 128                                       # max frames of FM captured per note


def fm_program_for(frames, v, onset, dur_f, base):
    """Per-note FM program (B2): reproduce the original's exact per-frame freq for
    this note. offset[k] = (trace_freq[onset+k] - base) & $FFFF; the driver's FM
    runner accumulates per-frame deltas, so emit delta[k]=offset[k]-offset[k-1] as
    (lo,hi,run) RLE entries + a freeze. Handles BOTH portamento slides (constant
    delta) and arps (per-frame deltas) byte-exactly. base = the note's freqtable
    value (== the driver's vfreq), so offset[0]=0 (frame 0 plays at base)."""
    targ, hold = [], 0
    for k in range(min(dur_f, FM_CAP)):
        idx = onset + k
        tf = frames[idx][0][v]['freq'] if idx < len(frames) else None
        hold = ((tf - base) & 0xFFFF) if tf is not None else hold
        targ.append(hold)
    # The driver's pr_note holds base pitch on the TRIGGER frame (FM_CNT=1/FM_OFF=0),
    # so FM entries apply from frame 1 onward — drop delta[0] (frame 0 = base).
    deltas = [(targ[k] - targ[k - 1]) & 0xFFFF for k in range(1, len(targ))]
    prog, run, rl = [], None, 0
    for delta in deltas:
        if delta == run:
            rl += 1
        else:
            if run is not None:
                prog.append((run & 0xFF, (run >> 8) & 0xFF, rl))
            run, rl = delta, 1
    if run is not None:
        prog.append((run & 0xFF, (run >> 8) & 0xFF, rl))
    if not prog or all(e[0] == 0 and e[1] == 0 for e in prog):
        return [(0, 0, 0)]                          # flat -> program 0 (freeze)
    prog.append((0, 0, 0))                          # hold the last offset
    return prog


def pulse_program_for(frames, v, onset, dur_f):
    """Per-note PULSE program (B3 PWM): reproduce the original's per-frame pulse
    width. 8X = set width frame 0; 0X = add per-frame delta (12-bit) for `run`
    frames; 7f = freeze. The driver restarts the pulse program per note (PPTR=
    VIPUL/VPC=0), so frame 0 sets the base — no 1-frame offset (unlike FM)."""
    targ, hold = [], None
    for k in range(min(dur_f, FM_CAP)):
        idx = onset + k
        pv = frames[idx][0][v]['pul'] if idx < len(frames) else None
        if pv is not None:
            hold = pv
        targ.append(hold if hold is not None else 0x800)
    prog = [(0x80 | ((targ[0] >> 8) & 0x0F), targ[0] & 0xFF, 1)]   # 8X set frame 0
    prev, run, rl = targ[0], None, 0
    for k in range(1, len(targ)):
        delta = (targ[k] - prev) & 0xFFF                          # 12-bit signed add
        prev = targ[k]
        if delta == run:
            rl += 1
        else:
            if run is not None:
                prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
            run, rl = delta, 1
    if run is not None:
        prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
    prog.append((0x7F, 0, 0))                                     # freeze (hold last)
    return prog


def extract_wave_programs(m, sid, sub, idx_map, instr_rows, frames):
    """Per-instrument WAVE program (B3 gate envelope): wave_step advances one row per
    FRAME and writes col0 to $D404 (gate bit preserved, VGMASK=$ff on a note). Sample
    the original's per-frame waveform over a note that uses each instrument, hold the
    last change point, and loop there — reproduces the $43->$42 / $41->$40 gate-off
    (note release) mid-note. col1 = 0 (pitch comes from the FM program, not semitones).
    Returns {slot: [(wf,0),...,(7f,loop_row)]}."""
    fpt = m.frames_per_tick
    progs = {}
    for v in range(3):
        fr = 0
        for ev in m.voices[v]:
            slot = idx_map.get(ev.instr, 0)
            dur_f = ev.dur * fpt
            if ev.retrig and slot not in progs and dur_f >= 2:
                wfs, last = [], 0x41
                for k in range(min(dur_f, 32)):
                    idx = fr + k
                    w = frames[idx][0][v]['wf'] if idx < len(frames) else None
                    last = w if w is not None else last
                    wfs.append(last & 0xFF)
                settle = max((k for k in range(1, len(wfs)) if wfs[k] != wfs[k - 1]),
                             default=0)
                prog = [(wfs[k], 0x00) for k in range(settle + 1)]
                prog.append((0x7F, settle))               # loop on the settled waveform
                progs[slot] = prog
            fr += dur_f
    return progs


def _wave_prog_for(frames, v, onset, dur_f):
    """Per-note WAVE program (waveform/gate envelope) sampled per FRAME from the
    trace, trimmed to the settle point. MoN's waveform attack varies per note (the
    $7x wprog), so it's captured per note, not per instrument."""
    wfs, last = [], 0x41
    for k in range(min(dur_f, 32)):
        idx = onset + k
        w = frames[idx][0][v]['wf'] if idx < len(frames) else None
        last = w if w is not None else last
        wfs.append(last & 0xFF)
    settle = max((k for k in range(1, len(wfs)) if wfs[k] != wfs[k - 1]), default=0)
    return tuple(wfs[:settle + 1])


def build_native_song(m, sid, sub, idx_map, instr_rows):
    """Walk the MoN song -> per-voice packed sequences. Each note carries:
      - an INSTRUMENT byte ($a0-$bf) = a distinct (AD/SR/waveform + per-note WAVE
        program) — captures the waveform attack/gate envelope, which varies per note
        via the $7x wprog (so per-note, deduped into <=32 instruments);
      - a COMMAND byte ($c0-$ff) = an (FM, pulse) bundle = the note's per-frame pitch
        (slide/arp) + PWM from the trace.
    Returns (segs, bundles, instrs, wave_programs)."""
    import mon_fidelity as F
    frames = F.per_frame(sid, [f'-a{sub}', '-t10'])
    fpt = m.frames_per_tick
    rev = {slot: mon_i for mon_i, slot in idx_map.items()}
    bundles, bidx = [], {}
    instrs, iidx, wave_programs = [], {}, []

    def bundle_of(fp, pp):
        k = (tuple(fp), tuple(pp))
        if k not in bidx:
            bidx[k] = len(bundles)
            bundles.append((fp, pp))
        return bidx[k]

    def instr_of(mon_i, wp):
        ins = m.instrument(mon_i)
        ad, sr, raw = ins['ad'], ins['sr'], ins['waveform'] or 0x41
        key = (ad, sr, raw, wp)
        if key not in iidx:
            iidx[key] = len(instrs)
            instrs.append((ad, sr, raw))
            wave_programs.append([(w, 0x00) for w in wp] + [(0x7F, len(wp) - 1)])
        return iidx[key]

    segs = [[] for _ in range(3)]
    for v in range(3):
        fr = 0
        for _pat, events in m._voice_blocks(v):
            rows = []
            cur_inst = cur_cmd = None
            for ev in events:
                dur_f = ev.dur * fpt
                base = m.note_freq(ev.note)
                slot = instr_of(ev.instr, _wave_prog_for(frames, v, fr, dur_f))
                cmd = bundle_of(fm_program_for(frames, v, fr, dur_f, base),
                                pulse_program_for(frames, v, fr, dur_f))
                note = max(SF2_NOTE_MIN, min(ev.note, SF2_NOTE_MAX))
                rows.append(D11Row(note=note,
                                   instrument=slot if slot != cur_inst else None,
                                   command=cmd if cmd != cur_cmd else None))
                cur_inst, cur_cmd = slot, cmd
                rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, ev.dur - 1)))
                fr += dur_f
            for pk in segment_track(rows):
                segs[v].append(pk)
    return segs, bundles, instrs, wave_programs


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Tel_Jeroen", "Hawkeye.sid")
    sub = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    d, la, _ = load_sid(sid)
    m = MON(d, la, sub)
    used = mon_to_sf2.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = mon_to_sf2.build_instruments(m, used)

    # B2/B3: per-note FM+pulse bundles ($c0-$ff command) AND per-note WAVE programs
    # (distinct instruments, $a0-$bf) — both extracted from the original trace.
    segs, bundles, instrs, wave_programs = build_native_song(m, sid, sub, idx_map, instr_rows)
    pulse_programs = [static_pulse(0x800) for _ in instrs]   # unused (command owns pulse)

    # redirect the shared build pipeline at the MoN driver copy
    B.GAL = MON_DIR
    B.TEMPO = m.speed + 1                       # native driver frames/row = tick frames
    print(f"{os.path.basename(sid)} sub{sub}: load=${la:04X} segs/voice={[len(s) for s in segs]} "
          f"instr={len(instrs)} bundles={len(bundles)} tempo={B.TEMPO}")
    if len(bundles) > 64:
        print(f"  WARNING: {len(bundles)} bundles > 64 (command cap) — needs clustering")
    if len(instrs) > 32:
        print(f"  WARNING: {len(instrs)} instruments > 32 — needs clustering")

    gen, edit, mdp, seq0 = RN.gen_includes_song(segs, instrs, wave_programs,
                                                pulse_programs, bundles=bundles)
    # gen_includes_song writes ROM_DIR/layout.inc (hardcoded) — copy to the MoN driver
    shutil.copyfile(os.path.join(ROM_DIR, "layout.inc"), os.path.join(MON_DIR, "layout.inc"))
    write_mon_freqtable(m)

    prg = B.assemble()
    names = [f"instr {i}" for i in range(len(instrs))]
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)
    out = os.path.join(ROOT, "out", "mon",
                       os.path.splitext(os.path.basename(sid))[0] + f"_sub{sub}_native.sf2")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes); tables top ~${gen.filter_addr:04X}")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    pla = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${pla:04X} tracks={di.track_count}",
          "OK" if pla == B.LOAD_BASE else "FAIL")

    # headless: each voice should reproduce its first sequence's note freqs (MoN table)
    exp = [[m.note_freq(n) for n in RN.playing_notes(segs[v][0])] for v in range(3)]
    B.N_ROWS = 24
    rows = B.headless_audio(prg, edit)
    bad = 0
    print("  row:  V0      V1      V2     (expected, MoN tuning)")
    for r in range(min(B.N_ROWS, *[len(e) for e in exp])):
        e = [exp[v][r] for v in range(3)]
        g = rows[r]
        good = all(abs(g[v] - e[v]) <= 0x40 or e[v] == 0 for v in range(3))
        bad += 0 if good else 1
        if r < 12:
            print(f"  {r}: " + " ".join(f"${g[v]:04X}" for v in range(3))
                  + "  (" + "/".join(f"${e[v]:04X}" for v in range(3)) + ") "
                  + ("ok" if good else "X"))
    print("SONG NOTES OK on native driver" if bad == 0 else f"NOTE MISMATCH ({bad} rows)")


if __name__ == "__main__":
    main()
