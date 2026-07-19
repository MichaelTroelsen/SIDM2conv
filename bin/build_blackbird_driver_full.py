"""Stage B — full build harness for the table-driven Blackbird driver .sf2.

Mirrors bin/build_romuzak_driver_full.py's shape (per docs/players/PLAYBOOK.md
§2/§6, every native Stage-B driver in this project shares this pipeline):
  1. compute the edit-area layout at a FIXED base (so seq00 addr is known)
  2. generate layout.inc (SEQ0, TEMPO) + freqtable.inc (note->freq)
  3. assemble the driver with 64tass
  4. wrap: load word + descriptor headers + driver code + edit area
  5. validate: sf2_parser structural parse + py65 headless audio trace

This module supplies the reusable assemble()/wrap()/headless_audio()/
relocate_driver_tables() primitives; bin/build_blackbird_native_song.py is
the real-song builder that calls into it (same split as
build_romuzak_driver_full.py / build_romuzak_native_song.py).

Usage (skeleton self-test): py -3 bin/build_blackbird_driver_full.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BB = os.path.join(ROOT, "drivers_src", "blackbird")
OUTDIR = os.path.join(ROOT, "out")

from sidm2.sf2_header_generator import SF2HeaderGenerator
from sidm2 import placeholder_edit_area, sf2_aux_bodies
from sidm2.models import SF2DriverInfo
from sidm2 import sf2_parser
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI

LOAD_BASE = 0x0D7E
DRV_INIT, DRV_PLAY, DRV_STOP = 0x1000, 0x1003, 0x1006
EDIT_BASE = 0x1A00          # fixed: above the driver (code+state end $1702)
TEMPO = 6                   # frames per row (overwritten per-song)

# Test instruments (2): (AD, SR, waveform, pulse-base-hi-nibble) -- skeleton
# self-test only, not used by the real-song build.
TEST_INSTR = [(0x09, 0x00, 0x41, 0x08),
              (0x00, 0xF8, 0x21, 0x04)]

V_SEQ = [bytes([0xA0, 0x84, 0x19, 0x1B, 0x7F]),
         bytes([0xA1, 0x25, 0x27, 0x7F]),
         bytes([0xA0, 0x31, 0x33, 0x7F])]
V_EXP = [[0x19, 0x19, 0x19, 0x19, 0x19, 0x1B],
         [0x25, 0x27, 0x25, 0x27, 0x25, 0x27],
         [0x31, 0x33, 0x31, 0x33, 0x31, 0x33]]
N_ROWS = 6
SEQ_STRIDE = 0x100

WAVE_RELOC = 0x3800


def find_64tass():
    for c in [shutil.which("64tass"),
              r"C:\Users\mit\Downloads\64tass-1.60\64tass-1.60.3243\64tass.exe"]:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError("64tass not found")


def relocate_driver_tables(gen, edit):
    """Repoint gen's wave/pulse/filter at a full-stride region placed ABOVE the
    current edit-area extent, matching build_romuzak_driver_full.py exactly."""
    gen.wave_columns = 2
    base = max(WAVE_RELOC, EDIT_BASE + len(edit))
    base = (base + 0xFF) & ~0xFF
    gen.wave_addr = base
    gen.pulse_addr = gen.wave_addr + 2 * 256
    gen.filter_addr = gen.pulse_addr + 3 * 256
    end = gen.filter_addr + 3 * 256 - EDIT_BASE
    if len(edit) < end:
        edit.extend(bytearray(end - len(edit)))
    return (gen.wave_addr - EDIT_BASE, gen.pulse_addr - EDIT_BASE,
            gen.filter_addr - EDIT_BASE)


def _inject_test_data(edit, gen, mdp):
    seq0 = mdp['seq00_addr']
    for v in range(3):
        so = (seq0 + v * SEQ_STRIDE) - EDIT_BASE
        edit[so:so + len(V_SEQ[v])] = V_SEQ[v]
    io = gen.instr_addr - EDIT_BASE
    wo, po, fo = relocate_driver_tables(gen, edit)
    for i, ins in enumerate(TEST_INSTR):
        ad, sr, wf = ins[0], ins[1], ins[2]
        edit[io + 0 * 32 + i] = ad
        edit[io + 1 * 32 + i] = sr
        edit[io + 5 * 32 + i] = 2 * i
        edit[wo + 0 * 256 + 2 * i] = wf
        edit[wo + 0 * 256 + 2 * i + 1] = 0x7f
        edit[wo + 1 * 256 + 2 * i + 1] = 2 * i
    IFMLO = gen.filter_addr + 3 * 256
    IFMHI = IFMLO + 32
    IPULSE_LO = IFMHI + 32
    IPULSE_HI = IPULSE_LO + 32
    FMTAB = IPULSE_HI + 32
    PULSETAB = FMTAB + 3
    pulsetab = bytearray()
    pstart = []
    for i, ins in enumerate(TEST_INSTR):
        pw = (ins[3] if len(ins) > 3 else 0x08) & 0x0F
        pstart.append(PULSETAB + len(pulsetab))
        pulsetab += bytes([0x80 | pw, 0x00, 0x01, 0x7F, 0x00, 0x00])
    pulsetab_end = PULSETAB + len(pulsetab)
    need = pulsetab_end - EDIT_BASE
    if len(edit) < need:
        edit.extend(bytearray(need - len(edit)))
    for i in range(len(TEST_INSTR)):
        edit[IFMLO - EDIT_BASE + i] = FMTAB & 0xFF
        edit[IFMHI - EDIT_BASE + i] = (FMTAB >> 8) & 0xFF
        edit[IPULSE_LO - EDIT_BASE + i] = pstart[i] & 0xFF
        edit[IPULSE_HI - EDIT_BASE + i] = (pstart[i] >> 8) & 0xFF
    edit[FMTAB - EDIT_BASE + 0] = 0x00
    edit[FMTAB - EDIT_BASE + 1] = 0x00
    edit[FMTAB - EDIT_BASE + 2] = 0x00
    edit[PULSETAB - EDIT_BASE:pulsetab_end - EDIT_BASE] = pulsetab


def gen_includes():
    gen = SF2HeaderGenerator()
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = DRV_INIT, DRV_PLAY, DRV_STOP
    gen.PLAYER_ADDRESSES = dict(gen.PLAYER_ADDRESSES)
    gen.PLAYER_ADDRESSES["driver_state"] = 0x16D0
    gen.PLAYER_ADDRESSES["tempo_counter"] = 0x16D1
    gen.driver_name = "Blackbird"
    gen.driver_version_major = 17
    gen.driver_version_minor = 0
    gen.driver_code_top = 0x1000
    bares = [bytes(V_EXP[v]) for v in range(3)]
    edit, mdp = placeholder_edit_area.build_placeholder_edit_area(
        EDIT_BASE, gen, voice_streams=bares)
    edit = bytearray(edit)
    _inject_test_data(edit, gen, mdp)
    edit = bytes(edit)
    seq0 = mdp['seq00_addr']

    with open(os.path.join(BB, "layout.inc"), "w") as f:
        f.write("; auto-generated by bin/build_blackbird_driver_full.py\n")
        for v in range(3):
            f.write(f"SEQ{v}  = ${seq0 + v * SEQ_STRIDE:04x}\n")
            f.write(f"OL{v}   = ${mdp['ol_track1_addr'] + v * mdp['ol_size']:04x}\n")
        f.write(f"SEQPTRLO = ${mdp['seq_ptr_lo_addr']:04x}\n")
        f.write(f"SEQPTRHI = ${mdp['seq_ptr_hi_addr']:04x}\n")
        f.write(f"TEMPO = {TEMPO}\n")
        f.write(f"TEMPO2 = {TEMPO}\n")
        f.write("TEMPO_SCHED_LEN = 0\n")   # B3: skeleton self-test has no mid-song
                                            # tempo changes -- see build_blackbird_
                                            # native_song.py's extract_tempo_schedule()
                                            # for the real-song path.
        f.write(f"INSTR = ${gen.instr_addr:04x}\n")
        f.write(f"WAVE  = ${gen.wave_addr:04x}\n")
        f.write(f"PULSE = ${gen.pulse_addr:04x}\n")
        f.write(f"FILTER = ${gen.filter_addr:04x}\n")
        base = gen.filter_addr + 3 * 256
        f.write(f"IFM_LO = ${base:04x}\n")
        f.write(f"IFM_HI = ${base + 32:04x}\n")
        f.write(f"IPULSE_LO = ${base + 64:04x}\n")
        f.write(f"IPULSE_HI = ${base + 96:04x}\n")
        f.write(f"FMTAB  = ${base + 128:04x}\n")
        f.write(f"PULSETAB = ${base + 131:04x}\n")
        f.write("MULTISPEED = 1\n")
        f.write("FILT_INIT_ROW = 0\n")

    # B3: empty tempo schedule (TEMPO_SCHED_LEN=0 above means do_row's
    # `cpx #TEMPO_SCHED_LEN; bcs sk_sched` always skips before reading these --
    # zero-length .inc files are enough for the labels to exist.
    for name in ("tempo_sched_row_lo.inc", "tempo_sched_row_hi.inc",
                 "tempo_sched_t1.inc", "tempo_sched_t2.inc"):
        with open(os.path.join(BB, name), "w") as f:
            f.write("; auto-generated by bin/build_blackbird_driver_full.py -- empty "
                     "(skeleton self-test has TEMPO_SCHED_LEN=0)\n")

    with open(os.path.join(BB, "freqtable.inc"), "w") as f:
        f.write("; auto-generated note->PAL-freq table (indexed by note byte)\n")
        words = []
        for i in range(0x70):
            if i == 0:
                words.append(0)
            else:
                s = min(i - 1, 95)
                words.append(FREQ_TABLE_LO[s] | (FREQ_TABLE_HI[s] << 8))
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k + 8]) + "\n")
    return gen, edit, mdp, seq0


def assemble():
    prg = os.path.join(OUTDIR, "blackbird_driver.prg")
    r = subprocess.run([find_64tass(), "--cbm-prg", "-o", prg,
                        os.path.join(BB, "blackbird_driver.asm")],
                       capture_output=True, text=True, cwd=BB)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("ASSEMBLE FAILED")
    data = open(prg, "rb").read()
    load = data[0] | (data[1] << 8)
    img = bytearray(0x10000)
    for i, b in enumerate(data[2:]):
        img[(load + i) & 0xFFFF] = b
    ST_FIRST, ST_LAST = 0x16cc, 0x1702
    if any(img[a] != 0 for a in range(ST_FIRST, ST_LAST + 1)):
        raise SystemExit(
            f"DRIVER STATE-REGION OVERLAP: ${ST_FIRST:04X}-${ST_LAST:04X} is not "
            f"clear — code/tables spilled into SF2II's playback-state region.")
    drv_end = load + len(data) - 2
    if drv_end >= EDIT_BASE:
        raise SystemExit(
            f"DRIVER OVERRUNS EDIT AREA: ends ${drv_end:04X} >= ${EDIT_BASE:04X}")
    return data


def wrap(driver_prg, gen, edit, mdp, instr_names=None, sid_model=6581):
    drv_load = driver_prg[0] | (driver_prg[1] << 8)
    drv_code = driver_prg[2:]
    assert drv_load == 0x1000
    edit_end = EDIT_BASE + len(edit)
    file_top = edit_end
    gen.driver_size = file_top - LOAD_BASE
    header_bytes = gen.generate_complete_headers(mdp)
    if LOAD_BASE + len(header_bytes) > drv_load:
        raise SystemExit("headers overlap driver")

    file_size = 2 + (file_top - LOAD_BASE)
    f = bytearray(file_size)
    f[0], f[1] = LOAD_BASE & 0xFF, LOAD_BASE >> 8
    f[2:2 + len(header_bytes)] = header_bytes
    doff = 2 + (drv_load - LOAD_BASE)
    f[doff:doff + len(drv_code)] = drv_code
    eoff = 2 + (EDIT_BASE - LOAD_BASE)
    f[eoff:eoff + len(edit)] = edit
    try:
        tt = sf2_aux_bodies.build_table_text_data(instr_names or [], [], 1, 0)
        sf2_aux_bodies.inject_aux_chain_into_sf2(
            f, sf2_aux_bodies.assemble_aux_chain(
                tt, sf2_aux_bodies.build_description_data("Blackbird"), sid_model=sid_model))
    except Exception:
        pass
    return bytes(f)


def headless_audio(prg, edit):
    from py65.devices.mpu6502 import MPU
    load = prg[0] | (prg[1] << 8)
    m = MPU()
    for i, b in enumerate(prg[2:]):
        m.memory[(load + i) & 0xFFFF] = b
    for i, b in enumerate(edit):
        m.memory[(EDIT_BASE + i) & 0xFFFF] = b

    def call(addr):
        SENT = 0x4000
        r = (SENT - 1) & 0xFFFF
        m.memory[0x1FF] = r >> 8; m.memory[0x1FE] = r & 0xFF
        m.sp = 0xFD; m.pc = addr
        for _ in range(20000):
            if m.pc == SENT:
                return
            m.step()
    call(0x1000)
    sid = [0xD400, 0xD407, 0xD40E]
    rows = []
    for _row in range(N_ROWS):
        for _ in range(TEMPO):
            call(0x1003)
        rows.append([m.memory[b] | (m.memory[b + 1] << 8) for b in sid])
    return rows


def headless_trace(prg, edit, n_frames):
    """Run the assembled driver headless for n_frames real PAL frames
    (init once, then do_play once per frame — no row-batching), returning
    the full $D400-$D418 register snapshot after each frame. Used by
    build_blackbird_native_song.py to compare against the validated Python
    simulator's own per-frame register trace for the SAME file."""
    from py65.devices.mpu6502 import MPU
    load = prg[0] | (prg[1] << 8)
    m = MPU()
    for i, b in enumerate(prg[2:]):
        m.memory[(load + i) & 0xFFFF] = b
    for i, b in enumerate(edit):
        m.memory[(EDIT_BASE + i) & 0xFFFF] = b

    def call(addr, budget=20000):
        SENT = 0x4000
        r = (SENT - 1) & 0xFFFF
        m.memory[0x1FF] = r >> 8; m.memory[0x1FE] = r & 0xFF
        m.sp = 0xFD; m.pc = addr
        for _ in range(budget):
            if m.pc == SENT:
                return
            m.step()
    call(0x1000)
    frames = []
    for _ in range(n_frames):
        call(0x1003)
        frames.append([m.memory[0xD400 + r] for r in range(25)])
    return frames


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    gen, edit, mdp, seq0 = gen_includes()
    print(f"layout: edit ${EDIT_BASE:04X}-${EDIT_BASE+len(edit)-1:04X}, seq0=${seq0:04X}, tempo={TEMPO}")
    prg = assemble()
    print(f"assembled driver: {len(prg)} bytes, load ${prg[0]|(prg[1]<<8):04X}")
    sf2 = wrap(prg, gen, edit, mdp)
    out = os.path.join(OUTDIR, "blackbird_driver.sf2")
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes)")

    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${la:04X} tracks={di.track_count} tables={len(di.table_addresses)}",
          "OK" if la == LOAD_BASE else "FAIL")

    rows = headless_audio(prg, edit)
    ok = True
    print("  row:  V0 freq  V1 freq  V2 freq    (expected V0/V1/V2)")
    for r in range(N_ROWS):
        exp = [FREQ_TABLE_LO[V_EXP[v][r] - 1] | (FREQ_TABLE_HI[V_EXP[v][r] - 1] << 8)
               for v in range(3)]
        got = rows[r]
        good = all(abs(got[v] - exp[v]) <= 0x80 for v in range(3))
        ok = ok and good
        print(f"  {r}: " + "  ".join(f"${got[v]:04X}" for v in range(3))
              + "    (" + "/".join(f"${exp[v]:04X}" for v in range(3)) + ") "
              + ('ok' if good else 'X'))
    print("AUDIO OK (skeleton self-test)" if ok else "AUDIO MISMATCH")


if __name__ == "__main__":
    main()
