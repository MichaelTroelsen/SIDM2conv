"""Stage B1 — emit a REAL ROMUZAK tune as a native-ROMUZAK-driver .sf2.

Feeds the existing (RE'd + validated) ROMUZAK decode in bin/romuzak_to_sf2.py
into the native driver's editable tables: per-voice orderlist -> packed SECTOR
sequences, the 8-byte SOUND -> instrument + wave program (held waveform / arp /
drum), reusing the native build pipeline (bin/build_romuzak_driver_full.py).

B1 goal: melody + arps play note-faithfully through the from-scratch native
driver (proof the real tune runs on it). Drums (the freq-high-byte mode), exact
$2CA2 freq table, SEEK/pulse and vibrato follow in B2-B3.

Usage:  py -3 bin/build_romuzak_native_song.py [SID/Fun_Fun/Delirious_9_tune_1.sid]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_romuzak_driver_full as B
from sidm2.sf2_header_generator import SF2HeaderGenerator
from sidm2 import placeholder_edit_area
from sidm2.galway_driver11_emitter import unpack_sequence
from sidm2.galway_to_driver11 import SF2_NOTE_MIN, SF2_NOTE_MAX
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI
from romuzak_to_sf2 import (
    load_sid, RMZ, calibrate_base, find_tempo, build_instruments,
    build_structured, _append_silent_instrument,
)


def write_freqtable(d, la):
    """Write drivers_src/romuzak/freqtable.inc from the rip's OWN note->freq table
    (`$2CA2`, 2 bytes/note) so the native driver's frequencies match the original
    byte-for-byte. Indexed directly by note byte i = raw ROMUZAK note ($00=c-0);
    [0] forced to 0 (note byte 0 = rest). The generic PAL table the driver builder
    emits is both 1-semitone-misaligned (it uses PAL(i-1)) AND slightly detuned vs
    ROMUZAK's table ($2CA2[$30]=$1167 not PAL $1168). Located via the note-setup
    signature `BD 45 2C 0A A8 B9 lo hi` (LDA note,X; ASL; TAY; LDA freqtab,Y)."""
    ft = None
    for i in range(len(d) - 8):
        if d[i] == 0xBD and d[i + 3] == 0x0A and d[i + 4] == 0xA8 and d[i + 5] == 0xB9:
            ft = d[i + 6] | (d[i + 7] << 8)
            break
    if ft is None:
        return False                              # leave the PAL fallback in place
    def fz(n):
        a = (ft + n * 2) - la
        return (d[a] | (d[a + 1] << 8)) if 0 <= a + 1 < len(d) else 0
    words = [0] + [fz(i) for i in range(1, 0x70)]
    with open(os.path.join(ROOT, "drivers_src", "romuzak", "freqtable.inc"), "w") as f:
        f.write("; ROMUZAK $2CA2 note->freq table (exact, for byte-100% fidelity)\n")
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k + 8]) + "\n")
    return True


def _wave_program(wave_table, start):
    """Extract instrument's wave program (rows start..first $7f inclusive) as a
    list of (col0, col1) with the $7f jump target made RELATIVE to `start`
    (gen_includes_song re-absolutises it)."""
    prog = []
    i = start
    while i < len(wave_table):
        c0, c1 = wave_table[i]
        if c0 == 0x7F:
            prog.append((0x7F, c1 - start))     # absolute loop target -> relative
            break
        prog.append((c0 & 0xFF, c1 & 0xFF))
        i += 1
    return prog or [(0x41, 0x00), (0x7F, 0)]


def drum_wave_program(rmz, b4, b6, wf):
    """Native drum program: onset row (note pitch, kept) + one row per drum-table
    entry carrying the freq HIGH byte (driver's drum mode), then a $7f loop on the
    whole cycle. The driver keeps the note's freq LOW byte, so freq = drum_hi<<8 |
    note_lo. The played HIGH byte = drum_table_value + B6 (the sound's byte 6, the
    'freq-drum' offset) -- verified vs trace: snd 02 B6=$04 -> table+4 = $2C/$0A/...,
    snd 04 B6=$00 -> table unchanged = $40/$08/..."""
    prog = [(wf or 0x11, 0x00)]                       # onset: keep note pitch 1 frame
    for dwf, dval in (rmz.drum_sequence(b4) or [(wf, 0)]):
        prog.append((dwf & 0xFF, (dval + b6) & 0xFF))  # freq HIGH byte = table + B6
    prog.append((0x7F, 0))                            # loop the WHOLE cycle (onset +
    return prog                                       #   table repeats, per the trace)


def gen_includes_song(segs, instrs, wave_programs, drum_set=frozenset(), multispeed=1):
    """Native ROMUZAK edit area: per-voice packed SECTOR sequences + column-major
    instruments + per-instrument wave programs. Writes drivers_src/romuzak/layout.inc.
    (Adapted from build_galway_native_song.gen_includes_song; pulse/FM left default
    for B1 — drums/SEEK/vibrato come in B2-B3.)"""
    gen = SF2HeaderGenerator()
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = B.DRV_INIT, B.DRV_PLAY, B.DRV_STOP
    gen.PLAYER_ADDRESSES = dict(gen.PLAYER_ADDRESSES)
    gen.PLAYER_ADDRESSES["driver_state"] = 0x16D0
    gen.PLAYER_ADDRESSES["tempo_counter"] = 0x16D1
    gen.driver_name = "Romuzak"
    gen.driver_version_major = 17
    gen.driver_version_minor = 0
    gen.driver_code_top = 0x1000
    vstreams = [bytes([0x01]) + bytes([0xA0, 0x01]) * (len(segs[v]) - 1)
                for v in range(3)]
    edit, mdp = placeholder_edit_area.build_placeholder_edit_area(
        B.EDIT_BASE, gen, voice_streams=vstreams)
    edit = bytearray(edit)
    seq0 = mdp['seq00_addr']
    off = 0
    for v in range(3):
        for s, pk in enumerate(segs[v]):
            o = (seq0 + (off + s) * 0x100) - B.EDIT_BASE
            edit[o:o + len(pk)] = pk
        off += len(segs[v])
    io = gen.instr_addr - B.EDIT_BASE
    wo, po, fo = B.relocate_driver_tables(gen, edit)
    wave_cursor = 0
    wave_dedup = {}
    for i, ins in enumerate(instrs[:32]):
        ad, sr, wf = ins[0], ins[1], ins[2]
        edit[io + 0 * 32 + i] = ad
        edit[io + 1 * 32 + i] = sr
        if i in drum_set:
            edit[io + 2 * 32 + i] = 0x20      # col2 flag $20 -> drum (col1 = freq hi)
        wp = wave_programs[i] if i < len(wave_programs) else [(wf or 0x41, 0), (0x7F, 0)]
        wkey = tuple(wp)
        if wkey in wave_dedup:
            edit[io + 5 * 32 + i] = wave_dedup[wkey] & 0xFF
            continue
        start = wave_cursor
        for r, (c0, c1) in enumerate(wp):
            edit[wo + 0 * 256 + start + r] = c0 & 0xFF
            edit[wo + 1 * 256 + start + r] = ((start + c1) if c0 == 0x7F else c1) & 0xFF
        edit[io + 5 * 32 + i] = start & 0xFF
        wave_dedup[wkey] = start
        wave_cursor += len(wp)
        if wave_cursor > 256:
            raise ValueError(f"WAVE overflow: {wave_cursor} rows > 256")

    # default pulse (index 0) + flat FM; per-command tables minimal (B3 wires SEEK)
    NFM = 64
    ifmlo_addr = gen.filter_addr + 3 * 256
    ifmhi_addr = ifmlo_addr + NFM
    ipulse_lo_addr = ifmhi_addr + NFM
    ipulse_hi_addr = ipulse_lo_addr + NFM
    fmtab_addr = ipulse_hi_addr + NFM
    fmtab = bytes([0, 0, 0])                       # lone freeze terminator (no FM)
    pulsetab_addr = fmtab_addr + len(fmtab)
    pulsetab = bytes([0x80, 0x00, 1, 0x00, 0x08, 0xFF, 0x7F, 0x00, 0])  # generic ramp
    need = pulsetab_addr + len(pulsetab) - B.EDIT_BASE
    if len(edit) < need:
        edit.extend(bytearray(need - len(edit)))
    for i in range(NFM):                           # all commands -> flat FM / ramp pulse
        edit[(ifmlo_addr - B.EDIT_BASE) + i] = fmtab_addr & 0xFF
        edit[(ifmhi_addr - B.EDIT_BASE) + i] = (fmtab_addr >> 8) & 0xFF
        edit[(ipulse_lo_addr - B.EDIT_BASE) + i] = pulsetab_addr & 0xFF
        edit[(ipulse_hi_addr - B.EDIT_BASE) + i] = (pulsetab_addr >> 8) & 0xFF
    edit[fmtab_addr - B.EDIT_BASE:fmtab_addr - B.EDIT_BASE + len(fmtab)] = fmtab
    edit[pulsetab_addr - B.EDIT_BASE:pulsetab_addr - B.EDIT_BASE + len(pulsetab)] = pulsetab

    with open(os.path.join(ROOT, "drivers_src", "romuzak", "layout.inc"), "w") as f:
        f.write("; auto-generated (native song) by build_romuzak_native_song.py\n")
        for v in range(3):
            f.write(f"SEQ{v}  = ${seq0 + v * 0x100:04x}\n")
            f.write(f"OL{v}   = ${mdp['ol_track1_addr'] + v * mdp['ol_size']:04x}\n")
        f.write(f"SEQPTRLO = ${mdp['seq_ptr_lo_addr']:04x}\n")
        f.write(f"SEQPTRHI = ${mdp['seq_ptr_hi_addr']:04x}\n")
        f.write(f"TEMPO = {B.TEMPO}\n")
        f.write(f"INSTR = ${gen.instr_addr:04x}\n")
        f.write(f"WAVE  = ${gen.wave_addr:04x}\n")
        f.write(f"PULSE = ${gen.pulse_addr:04x}\n")
        f.write(f"FILTER = ${gen.filter_addr:04x}\n")
        f.write(f"FMTAB = ${fmtab_addr:04x}\n")
        f.write(f"PULSETAB = ${pulsetab_addr:04x}\n")
        f.write(f"IFM_LO = ${ifmlo_addr:04x}\n")
        f.write(f"IFM_HI = ${ifmhi_addr:04x}\n")
        f.write(f"IPULSE_LO = ${ipulse_lo_addr:04x}\n")
        f.write(f"IPULSE_HI = ${ipulse_hi_addr:04x}\n")
        f.write(f"MULTISPEED = {max(1, int(multispeed))}\n")
    return gen, bytes(edit), mdp, seq0


def freq_of(note):
    return 0 if note == 0 else (FREQ_TABLE_LO[note - 1] | (FREQ_TABLE_HI[note - 1] << 8))


def playing_notes(packed):
    out, last = [], 0
    for n in unpack_sequence(packed):
        if SF2_NOTE_MIN <= n <= SF2_NOTE_MAX:
            last = n
        out.append(last)
    return out


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Fun_Fun", "Delirious_9_tune_1.sid")
    d, la = load_sid(sid)
    rmz = RMZ(d, la)
    base = calibrate_base(rmz)
    instr_rows, wave_table, pulse_table = build_instruments(rmz)
    silent_idx = _append_silent_instrument(instr_rows, wave_table, pulse_table)
    sequences, orderlists = build_structured(rmz, base, silent_idx)
    # expand each voice's orderlist into per-occurrence packed sequences (play order)
    segs = [[sequences[idx] for idx in orderlists[v]] or [bytes([0x7F])]
            for v in range(3)]
    instrs = [(ir.ad, ir.sr, (wave_table[ir.wave_idx][0] or 0x41)
               if ir.wave_idx < len(wave_table) else 0x41)
              for ir in instr_rows]
    wave_programs = [_wave_program(wave_table, ir.wave_idx) for ir in instr_rows]
    # Drums (B7 bit0): override the Stage-A nearest-semitone wave program with the
    # native high-byte drum program + flag the instrument so wave_step uses drum mode.
    drum_set = set()
    for i in range(min(len(instr_rows), 32)):
        s = rmz.sounds[i]
        if s != (0xFF,) * 8 and (s[7] & 0x01):
            wave_programs[i] = drum_wave_program(rmz, s[4], s[6], instrs[i][2])
            drum_set.add(i)

    B.TEMPO = find_tempo(d) + 1          # native driver: frames/row = tick frames
    print(f"{os.path.basename(sid)}: load=${la:04X} segs/voice={[len(s) for s in segs]} "
          f"instr={len(instrs)} drums={sorted(drum_set)} tempo={B.TEMPO}")

    gen, edit, mdp, seq0 = gen_includes_song(segs, instrs, wave_programs, drum_set)
    if not write_freqtable(d, la):
        print("  WARNING: $2CA2 freq table not located — using PAL fallback")
    prg = B.assemble()
    names = [f"snd {i:02d}" for i in range(len(instrs))]
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)
    out = os.path.join(ROOT, "out", "romuzak",
                       os.path.splitext(os.path.basename(sid))[0] + "_native.sf2")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes); tables top ~${gen.filter_addr:04X}")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    pla = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${pla:04X} tracks={di.track_count}",
          "OK" if pla == 0x0D7E else "FAIL")

    # headless: each voice should reproduce its first sector's note frequencies
    exp = [playing_notes(segs[v][0]) for v in range(3)]
    B.N_ROWS = 24
    rows = B.headless_audio(prg, edit)
    bad = 0
    print("  row:  V0      V1      V2     (expected)")
    for r in range(min(B.N_ROWS, *[len(e) for e in exp])):
        e = [freq_of(exp[v][r]) for v in range(3)]
        g = rows[r]
        good = all(abs(g[v] - e[v]) <= 0x80 or e[v] == 0 for v in range(3))
        bad += 0 if good else 1
        if r < 12:
            print(f"  {r}: " + " ".join(f"${g[v]:04X}" for v in range(3))
                  + "  (" + "/".join(f"${e[v]:04X}" for v in range(3)) + ") "
                  + ("ok" if good else "X"))
    print("SONG AUDIO OK — real ROMUZAK notes play through the native driver"
          if bad == 0 else f"AUDIO MISMATCH ({bad} rows)")


if __name__ == "__main__":
    main()
