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


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Tel_Jeroen", "Hawkeye.sid")
    sub = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    d, la, _ = load_sid(sid)
    m = MON(d, la, sub)
    used = mon_to_sf2.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = mon_to_sf2.build_instruments(m, used)
    sequences, orderlists = mon_to_sf2.build_structured(m, 0, idx_map)

    # per-voice packed sequences in PLAY order (orderlist expanded)
    segs = [[sequences[idx] for idx in orderlists[v]] or [bytes([0x7F])] for v in range(3)]
    # native instrument = (AD, SR, waveform); wave program = held waveform; pulse = static
    instrs = [(ir.ad, ir.sr, (wave_table[ir.wave_idx][0] or 0x41)
               if ir.wave_idx < len(wave_table) else 0x41)
              for ir in instr_rows]
    wave_programs = [RN._wave_program(wave_table, ir.wave_idx) for ir in instr_rows]
    pulse_programs = [static_pulse((ir.pulse_width & 0x0F) << 8) for ir in instr_rows]

    # redirect the shared build pipeline at the MoN driver copy
    B.GAL = MON_DIR
    B.TEMPO = m.speed + 1                       # native driver frames/row = tick frames
    print(f"{os.path.basename(sid)} sub{sub}: load=${la:04X} segs/voice={[len(s) for s in segs]} "
          f"instr={len(instrs)} tempo={B.TEMPO}")

    gen, edit, mdp, seq0 = RN.gen_includes_song(segs, instrs, wave_programs, pulse_programs)
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
