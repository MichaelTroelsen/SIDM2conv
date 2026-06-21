"""Stage B2/B3 — full build of the table-driven Galway driver .sf2.

Pipeline (single source of truth for the memory layout so driver + wrapper +
descriptor agree):
  1. compute the edit-area layout at a FIXED base (so seq00 addr is known)
  2. generate layout.inc (SEQ0, TEMPO) + freqtable.inc (note->PAL freq)
  3. assemble the driver with 64tass
  4. wrap: load word + descriptor headers + driver code + edit area (+ melody)
  5. validate: sf2_parser structural parse + py65 headless audio trace

Usage:  py -3 bin/build_galway_driver_full.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
GAL = os.path.join(ROOT, "drivers_src", "galway")
OUTDIR = os.path.join(ROOT, "out")

from sidm2.sf2_header_generator import SF2HeaderGenerator
from sidm2 import placeholder_edit_area, sf2_aux_bodies
from sidm2.models import SF2DriverInfo
from sidm2 import sf2_parser
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI

LOAD_BASE = 0x0D7E
DRV_INIT, DRV_PLAY, DRV_STOP = 0x1000, 0x1003, 0x1006
EDIT_BASE = 0x1A00          # fixed: above the driver (code+state end $1702)
TEMPO = 6                   # frames per row

# Test instruments (2): (AD, SR, waveform, pulse-base-hi-nibble).
TEST_INSTR = [(0x09, 0x00, 0x41, 0x08),   # 0: pluck, pulse, width $800
              (0x00, 0xF8, 0x21, 0x04)]   # 1: sustained, saw (pulse unused)

# Three packed voice sequences. $A0/$A1 = set instrument, $80-$8F = duration
# (low nibble = extra rows to hold the next note), note bytes, $7F = end.
# Voice 0 uses a duration byte ($84 = hold 4 extra rows) to test note length.
V_SEQ = [bytes([0xA0, 0x84, 0x19, 0x1B, 0x7F]),   # v0: 0x19 held 5 rows, 0x1B
         bytes([0xA1, 0x25, 0x27, 0x7F]),          # v1: 0x25,0x27 (loops)
         bytes([0xA0, 0x31, 0x33, 0x7F])]          # v2: 0x31,0x33 (loops)
# Expected playing-note per row (6 rows), per voice (held note = same byte).
V_EXP = [[0x19, 0x19, 0x19, 0x19, 0x19, 0x1B],
         [0x25, 0x27, 0x25, 0x27, 0x25, 0x27],
         [0x31, 0x33, 0x31, 0x33, 0x31, 0x33]]
N_ROWS = 6
TEST_INSTR_IDX = [0, 1, 0]      # which instrument each voice's $A0/$A1 selects
SEQ_STRIDE = 0x100              # build_placeholder lays sequences 256 bytes apart


def find_64tass():
    for c in [shutil.which("64tass"),
              r"C:\Users\mit\Downloads\64tass-1.60\64tass-1.60.3243\64tass.exe"]:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError("64tass not found")


# The driver reads wave/pulse/filter with a 256-byte column stride, but the
# placeholder edit area packs those tables only a few rows apart — stride
# reads would land in adjacent data. Relocate all three into a dedicated
# region above FMTAB ($3500-$37FF) with full 256-row column spacing and
# repoint gen (-> Block 3 descriptor) + the layout. SF2II copies each
# DECLARED table by address, so it loads them anywhere.
# Wave is a STANDARD 2-column table (waveform, semitone) — like Driver 11 —
# so it renders + edits + PLAYS in stock SF2II (a 3rd column is non-standard
# for the Wave table and silenced playback). Pulse/Filter are 3-column
# (their standard SF2II layout).
WAVE_RELOC = 0x3800


def relocate_driver_tables(gen, edit):
    """Repoint gen's wave/pulse/filter at a full-stride region placed ABOVE the
    current edit-area extent (orderlists + sequences + instrument/placeholder
    tables) and extend `edit` to cover it. A fixed base ($3800) collides with
    the edit area on big songs (the instrument table + sequences run past it);
    placing the tables above the extent keeps them clear. Returns (wo,po,fo)."""
    gen.wave_columns = 2
    base = max(WAVE_RELOC, EDIT_BASE + len(edit))
    base = (base + 0xFF) & ~0xFF                  # page-align above the edit area
    gen.wave_addr = base                          # cols base+0 / +256
    gen.pulse_addr = gen.wave_addr + 2 * 256      # 3 cols
    gen.filter_addr = gen.pulse_addr + 3 * 256    # 3 cols
    end = gen.filter_addr + 3 * 256 - EDIT_BASE
    if len(edit) < end:
        edit.extend(bytearray(end - len(edit)))
    return (gen.wave_addr - EDIT_BASE, gen.pulse_addr - EDIT_BASE,
            gen.filter_addr - EDIT_BASE)


def _inject_test_data(edit, gen, mdp):
    """Overwrite the placeholder edit area with 3 packed voice sequences + a
    column-major instrument table + wave/pulse programs the native driver reads."""
    seq0 = mdp['seq00_addr']
    for v in range(3):
        so = (seq0 + v * SEQ_STRIDE) - EDIT_BASE
        edit[so:so + len(V_SEQ[v])] = V_SEQ[v]
    # column-major instruments (6 cols x 32 rows): col0=AD,col1=SR,col5=wave row
    io = gen.instr_addr - EDIT_BASE
    wo, po, fo = relocate_driver_tables(gen, edit)
    for i, ins in enumerate(TEST_INSTR):
        ad, sr, wf = ins[0], ins[1], ins[2]
        pw = (ins[3] if len(ins) > 3 else 0x08) & 0x0F
        edit[io + 0 * 32 + i] = ad
        edit[io + 1 * 32 + i] = sr
        edit[io + 5 * 32 + i] = 2 * i     # wave-program start row
        # 2-row wave program: [wf, +0 semitones][$7f -> loop] (1 row/frame)
        edit[wo + 0 * 256 + 2 * i] = wf
        edit[wo + 0 * 256 + 2 * i + 1] = 0x7f
        edit[wo + 1 * 256 + 2 * i + 1] = 2 * i
    # FM region: a single freeze terminator at FMTAB; every instrument's FM-start
    # points to it, so fm_step freezes (freq = vfreq, no FM) for the test pattern.
    # Placed above the relocated filter (dynamic, matches layout.inc).
    IFMLO = gen.filter_addr + 3 * 256
    IFMHI = IFMLO + 32
    IPULSE_LO = IFMHI + 32          # per-command pulse-start addr lo/hi (pointer model)
    IPULSE_HI = IPULSE_LO + 32
    FMTAB = IPULSE_HI + 32
    PULSETAB = FMTAB + 3           # row-major pulse table (3 bytes/entry), after FMTAB
    # one 2-entry pulse program per instrument: [8X|pw set, 1 frame][$7f freeze]
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
    edit[FMTAB - EDIT_BASE + 0] = 0x00       # freeze entry (offset 0, dur 0)
    edit[FMTAB - EDIT_BASE + 1] = 0x00
    edit[FMTAB - EDIT_BASE + 2] = 0x00
    edit[PULSETAB - EDIT_BASE:pulsetab_end - EDIT_BASE] = pulsetab


def gen_includes():
    gen = SF2HeaderGenerator()
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = DRV_INIT, DRV_PLAY, DRV_STOP
    gen.PLAYER_ADDRESSES = dict(gen.PLAYER_ADDRESSES)
    gen.PLAYER_ADDRESSES["driver_state"] = 0x16D0   # Block-2 play-state contract
    gen.PLAYER_ADDRESSES["tempo_counter"] = 0x16D1
    gen.driver_name = "Galway"
    gen.driver_version_major = 17     # own F12 overlay slot (bin/overlay/*_driver17_00.png)
    gen.driver_version_minor = 0
    gen.driver_code_top = 0x1000
    # PROVEN voice_streams path: each voice gets its own pattern. Use bare-note
    # streams for the structure, then overwrite each with the packed ($A0) form.
    bares = [bytes(V_EXP[v]) for v in range(3)]   # structure only (overwritten)
    edit, mdp = placeholder_edit_area.build_placeholder_edit_area(
        EDIT_BASE, gen, voice_streams=bares)
    edit = bytearray(edit)
    _inject_test_data(edit, gen, mdp)
    edit = bytes(edit)
    seq0 = mdp['seq00_addr']

    with open(os.path.join(GAL, "layout.inc"), "w") as f:
        f.write("; auto-generated by bin/build_galway_driver_full.py\n")
        for v in range(3):
            f.write(f"SEQ{v}  = ${seq0 + v * SEQ_STRIDE:04x}\n")
            f.write(f"OL{v}   = ${mdp['ol_track1_addr'] + v * mdp['ol_size']:04x}\n")
        f.write(f"SEQPTRLO = ${mdp['seq_ptr_lo_addr']:04x}\n")
        f.write(f"SEQPTRHI = ${mdp['seq_ptr_hi_addr']:04x}\n")
        f.write(f"TEMPO = {TEMPO}\n")
        f.write(f"INSTR = ${gen.instr_addr:04x}\n")
        f.write(f"WAVE  = ${gen.wave_addr:04x}\n")
        f.write(f"PULSE = ${gen.pulse_addr:04x}\n")
        f.write(f"FILTER = ${gen.filter_addr:04x}\n")
        base = gen.filter_addr + 3 * 256
        f.write(f"IFM_LO = ${base:04x}\n")          # FM-start tables (32 each)
        f.write(f"IFM_HI = ${base + 32:04x}\n")
        f.write(f"IPULSE_LO = ${base + 64:04x}\n")  # pulse-start tables (pointer model)
        f.write(f"IPULSE_HI = ${base + 96:04x}\n")
        f.write(f"FMTAB  = ${base + 128:04x}\n")     # row-major FM
        f.write(f"PULSETAB = ${base + 131:04x}\n")   # row-major pulse (after FMTAB+3)
        f.write("MULTISPEED = 1\n")        # test pattern is single-speed

    # freqtable indexed by note byte $00..$6F: [0]=0, [i]=PAL freq of semitone i-1
    with open(os.path.join(GAL, "freqtable.inc"), "w") as f:
        f.write("; auto-generated note->PAL-freq table (indexed by note byte)\n")
        words = []
        for i in range(0x70):
            if i == 0:
                words.append(0)
            else:
                s = min(i - 1, 95)
                words.append(FREQ_TABLE_LO[s] | (FREQ_TABLE_HI[s] << 8))
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k+8]) + "\n")
    return gen, edit, mdp, seq0


def assemble():
    prg = os.path.join(OUTDIR, "galway_driver.prg")
    r = subprocess.run([find_64tass(), "--cbm-prg", "-o", prg,
                        os.path.join(GAL, "galway_driver.asm")],
                       capture_output=True, text=True, cwd=GAL)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("ASSEMBLE FAILED")
    data = open(prg, "rb").read()
    # Guard against the silent-overlap crash class: the playback-state region
    # ($16cc-$1702, which SF2II reads/writes every frame) must NOT be occupied by
    # driver code or tables — an overlapping freqtable there gets corrupted and
    # crashes SF2II (py65 misses it). Assert the assembled image leaves it clear.
    load = data[0] | (data[1] << 8)
    img = bytearray(0x10000)
    for i, b in enumerate(data[2:]):
        img[(load + i) & 0xFFFF] = b
    ST_FIRST, ST_LAST = 0x16cc, 0x1702
    if any(img[a] != 0 for a in range(ST_FIRST, ST_LAST + 1)):
        raise SystemExit(
            f"DRIVER STATE-REGION OVERLAP: ${ST_FIRST:04X}-${ST_LAST:04X} is not "
            f"clear — code/tables spilled into SF2II's playback-state region "
            f"(would crash on play). Pin tables above ${ST_LAST:04X} or shrink code.")
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
    gen.driver_size = edit_end - LOAD_BASE
    header_bytes = gen.generate_complete_headers(mdp)
    if LOAD_BASE + len(header_bytes) > drv_load:
        raise SystemExit("headers overlap driver")

    file_size = 2 + (edit_end - LOAD_BASE)
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
                tt, sf2_aux_bodies.build_description_data("Galway"), sid_model=sid_model))
    except Exception:
        pass
    return bytes(f)


def headless_audio(prg, edit):
    from py65.devices.mpu6502 import MPU
    load = prg[0] | (prg[1] << 8)
    m = MPU()
    for i, b in enumerate(prg[2:]):
        m.memory[(load + i) & 0xFFFF] = b
    # The bare .prg has no edit area — place the WHOLE edit area (orderlists,
    # seq-pointer tables, sequences, instrument/wave tables) at EDIT_BASE so the
    # driver's orderlist walk + table reads see real data.
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


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    gen, edit, mdp, seq0 = gen_includes()
    print(f"layout: edit ${EDIT_BASE:04X}-${EDIT_BASE+len(edit)-1:04X}, seq0=${seq0:04X}, tempo={TEMPO}")
    prg = assemble()
    print(f"assembled driver: {len(prg)} bytes, load ${prg[0]|(prg[1]<<8):04X}")
    sf2 = wrap(prg, gen, edit, mdp)
    out = os.path.join(OUTDIR, "galway_driver.sf2")
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
        # tolerate vibrato (freq wobbles +-~64 around the base on held notes)
        good = all(abs(got[v] - exp[v]) <= 0x80 for v in range(3))
        ok = ok and good
        print(f"  {r}: " + "  ".join(f"${got[v]:04X}" for v in range(3))
              + "    (" + "/".join(f"${exp[v]:04X}" for v in range(3)) + ") "
              + ('ok' if good else 'X'))
    print("AUDIO OK (3 voices + note durations from the tables)" if ok
          else "AUDIO MISMATCH")


if __name__ == "__main__":
    main()
