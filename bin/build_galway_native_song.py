"""Stage B4 (first cut) — emit a REAL Galway tune as a native-Galway-driver .sf2.

Reuses the test-pattern build pipeline (bin/build_galway_driver_full.py) but
replaces the synthetic test data with a real SID's extracted music: convert via
the Stage A IR (galway_to_driver11), pack the first sequence of each of the 3
voices (galway_driver11_emitter.segment_track), and use the real instruments.
The result plays the opening of each voice's part, looping, through the
from-scratch native driver — the proof that a real Galway tune runs on it.

Usage:  py -3 bin/build_galway_native_song.py [SID/Galway_Martin/Wizball.sid]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_galway_driver_full as B
from sidm2.sid_parser import SIDParser
from sidm2.galway_1stgen_extractor import recover_channels
from sidm2.galway_to_driver11 import galway_to_driver11, SF2_NOTE_MIN, SF2_NOTE_MAX
from sidm2.galway_driver11_emitter import segment_track, unpack_sequence
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI


# FM region lives above the relocated wave/pulse/filter tables (which end $3FFF).
# Per-instrument FM-start address tables (lo/hi, 32 each) point into FMTAB, a
# ROW-major list of 3-byte entries (offset_lo, offset_hi, dur). Row-major + the
# 16-bit driver pointer removes the old 256-entry cap so full-length Galway
# slides fit. dur 0 = freeze terminator.
IFMLO_ADDR = 0x4000
IFMHI_ADDR = 0x4020
FMTAB_ADDR = 0x4040


def gen_includes_song(segs, instrs, fm_data=None, filter_lead=True,
                      wave_programs=None, fm_programs=None, multispeed=1,
                      pulse_programs=None, pulse_by_cmd=None,
                      filter_program=None, filter_instr_set=None):
    """Build a multi-pattern native-driver edit area from packed voice patterns.
    segs[v] = list of packed sequences for voice v. Returns (gen, edit, mdp, seq0)
    and writes drivers_src/galway/layout.inc.

    fm_data: optional (vfmstart[3], entries) where entries is a list of
    (offset_lo, offset_hi, dur) FM rows; None -> no FM (all freeze).
    filter_lead: flag instruments 0/1 to start the filter program (v3.9.0); the
    trace build sets False (its filter sweep would close on a single long note).
    wave_programs: optional list (indexed by instrument) of custom wave programs;
    each entry is a list of (col0_waveform, col1_semitone) rows, or None for the
    default 2-row [wf,+0][7f,loop]. col1 of a $7f (jump) row is the loop target
    RELATIVE to the program's start; col1 of any other row is the signed semitone
    offset the driver applies (one row per frame) — see wave_step. Programs are
    laid out sequentially into the 256-row, 2-column WAVE table (SF2II's native
    Wave layout); the trace build uses this to carry the per-frame pitch envelope
    (the real Galway slide/vibrato) in SF2II-native, editor-loaded, editable
    form. Long notes fit via the settled-tail loop + body trimming."""
    from sidm2.sf2_header_generator import SF2HeaderGenerator
    from sidm2 import placeholder_edit_area
    gen = SF2HeaderGenerator()
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = B.DRV_INIT, B.DRV_PLAY, B.DRV_STOP
    # Point the Block-2 playback-state contract at the native Galway driver's
    # own state bytes so SF2II's start/stop + follow-play work (ST_STATE/ST_TCNT
    # in galway_driver.asm). Instance copy so we don't mutate the class default.
    gen.PLAYER_ADDRESSES = dict(gen.PLAYER_ADDRESSES)
    gen.PLAYER_ADDRESSES["driver_state"] = 0x16D0   # $80 playing / $40 stopped
    gen.PLAYER_ADDRESSES["tempo_counter"] = 0x16D1  # 0 on each new row (follow)
    gen.driver_name = "Galway"
    gen.driver_version_major = 17     # own F12 overlay slot (bin/overlay/*_driver17_00.png)
    gen.driver_version_minor = 0
    gen.driver_code_top = 0x1000
    # voice_streams that segment into len(segs[v]) patterns per voice (content
    # is overwritten; only the segment COUNT + orderlist structure matters).
    vstreams = [bytes([0x01]) + bytes([0xA0, 0x01]) * (len(segs[v]) - 1)
                for v in range(3)]
    edit, mdp = placeholder_edit_area.build_placeholder_edit_area(
        B.EDIT_BASE, gen, voice_streams=vstreams)
    edit = bytearray(edit)
    seq0 = mdp['seq00_addr']
    # overwrite each pattern slot with its packed sequence
    off = 0
    for v in range(3):
        for s, pk in enumerate(segs[v]):
            p = off + s
            o = (seq0 + p * 0x100) - B.EDIT_BASE
            edit[o:o + len(pk)] = pk
        off += len(segs[v])
    # column-major instruments + wave table. Wave/pulse/filter live in the
    # full-stride relocated region (see B.relocate_driver_tables) — the
    # placeholder packs them only a few rows apart, which a 256-byte column
    # stride would read straight through.
    io = gen.instr_addr - B.EDIT_BASE
    wo, po, fo = B.relocate_driver_tables(gen, edit)
    wave_cursor = 0                 # sequential WAVE-row allocator
    pulse_cursor = 0                # sequential PULSE-row allocator
    for i, ins in enumerate(instrs[:32]):
        ad, sr, wf = ins[0], ins[1], ins[2]
        pw = (ins[3] if len(ins) > 3 else 0x08) & 0x0F
        edit[io + 0 * 32 + i] = ad
        edit[io + 1 * 32 + i] = sr
        # Flag $40 (re)starts the global filter program at row 0 on note-on. For a
        # trace build it's set on the ROUTED voice's instruments (filter_instr_set,
        # from $D417's routing); the legacy filter_lead path flags instruments 0/1.
        flag_filter = (i in filter_instr_set) if filter_instr_set is not None \
            else (filter_lead and i in (0, 1))
        if flag_filter:
            edit[io + 2 * 32 + i] = 0x40   # col2 flags: start filter program
            edit[io + 3 * 32 + i] = 0x00   # col3: filter-program start row
        # Wave program (standard SF2II 2-col: col0 waveform, col1 semitone).
        # Default = 2-row [wf,+0][7f,loop]; custom = per-frame semitone program
        # (trace build). Instrument col5 = the program start row.
        wp = None
        if wave_programs is not None and i < len(wave_programs):
            wp = wave_programs[i]
        if wp is None:
            wp = [(wf or 0x41, 0x00), (0x7f, 0)]            # loop -> own start
        start = wave_cursor
        for r, row in enumerate(wp):
            c0, c1 = row[0], row[1]
            edit[wo + 0 * 256 + start + r] = c0 & 0xFF
            # $7f jump row: col1 = loop target (relative-to-start -> absolute);
            # any other row: col1 = signed semitone offset (used as-is).
            edit[wo + 1 * 256 + start + r] = ((start + c1) if c0 == 0x7f else c1) & 0xFF
        edit[io + 5 * 32 + i] = start & 0xFF
        wave_cursor += len(wp)
        if wave_cursor > 256:
            raise ValueError(
                f"WAVE table overflow: {wave_cursor} rows > 256 "
                f"(reduce per-voice envelope length / loop sooner)")
        # (pulse is no longer per-instrument — see the per-command PULSE section
        #  below; the instrument's col4 pulse pointer is left 0/unused.)

    # --- Per-command PULSE programs (decoupled from the instrument, like FM) ---
    # The sequence command ($c0-$ff) selects BOTH the FM and the pulse program.
    # Distinct pulse programs (dedup by content) are laid ROW-major into PULSETAB
    # (below, after FMTAB) and walked via a 16-bit pointer like FM, so the cap is
    # the memory wall — not 256 rows — and a full-length song's pulse envelopes
    # fit at full resolution. Absent pulse_by_cmd (legacy/test builds), a single
    # generic ramp at index 0 serves every note.
    DEFAULT_PULSE = [(0x80, 0x00, 1), (0x00, 0x08, 0xFF), (0x7F, 0x00, 2)]
    pcmd = list(pulse_by_cmd) if pulse_by_cmd else [DEFAULT_PULSE]
    pcmd = [p if p else DEFAULT_PULSE for p in pcmd][:64]
    PULSE_ROW_CAP = 1024                           # generous; the real bound is $CF00
    distinct = []
    pidx = {}                                      # tuple(prog) -> distinct slot
    for p in pcmd:
        k = tuple(p)
        if k not in pidx:
            pidx[k] = len(distinct)
            distinct.append(list(p))
    while sum(len(p) for p in distinct) > PULSE_ROW_CAP:
        j = max(range(len(distinct)), key=lambda t: len(distinct[t]))
        if len(distinct[j]) <= 3:
            break
        keep = len(distinct[j]) - 2
        distinct[j] = distinct[j][:keep - 1] + [(0x7F, 0, 0)]   # freeze early

    # Filter program (row 0), restarted by each flag-$40 note. `filter_program` (a
    # trace build) carries the tune's REAL per-frame cutoff envelope as SET rows;
    # absent it, fall back to the measured Wizball filter (LP, cutoff $890, res $F,
    # route voice 1, sweep down). Col-major 256x3, ends in a $7f self-jump freeze.
    fr = 256
    fprog = filter_program if filter_program else [
        (0x98, 0x90, 0xF1), (0x0F, 0xF4, 0xFF), (0x7F, 0x00, 0x01)]
    for r, (b0, b1, b2) in enumerate(fprog[:fr]):
        edit[fo + 0 * fr + r] = b0 & 0xFF
        edit[fo + 1 * fr + r] = b1 & 0xFF
        # $7f freeze row: col2 = self row index (self-jump); other rows: as given.
        edit[fo + 2 * fr + r] = (r if (b0 & 0xFF) == 0x7F else b2) & 0xFF

    # FM region: per-instrument FM-start tables (IFM_LO/IFM_HI) + a row-major
    # FMTAB of 3-byte (offset_lo, offset_hi, dur) entries. Each instrument's
    # program is laid sequentially and ends with a (0,0,0) freeze terminator;
    # instruments with no FM get a lone terminator (freeze -> freq = vfreq).
    # Place the FM region ABOVE the relocated wave/pulse/filter (which are above
    # the edit area), so it never collides with the instrument table / sequences
    # on big songs (a fixed $4000 base does).
    NFM = 64                                       # FM-program table stride (cmd 0..63)
    ifmlo_addr = gen.filter_addr + 3 * 256
    ifmhi_addr = ifmlo_addr + NFM
    ipulse_lo_addr = ifmhi_addr + NFM              # per-command pulse start addr lo
    ipulse_hi_addr = ipulse_lo_addr + NFM          # per-command pulse start addr hi
    fmtab_addr = ipulse_hi_addr + NFM
    # FM programs are selected PER NOTE via the sequence command channel
    # ($c0-$ff -> index), DECOUPLED from the instrument. fm_programs is the master
    # list indexed by that command (index 0 = flat/freeze, the default). This lets
    # a long song carry many distinct slide shapes without inflating the <=32
    # instrument table. Absent fm_programs (non-trace builds), a lone flat program
    # at index 0 makes every note default to no modulation.
    fmprogs = list(fm_programs) if fm_programs else [[(0, 0, 0)]]
    fmtab = bytearray()
    ifm = []                                       # (lo, hi) start addr per FM program
    for i in range(min(len(fmprogs), NFM)):
        start = fmtab_addr + len(fmtab)
        prog = list(fmprogs[i]) if fmprogs[i] else []
        if not prog or prog[-1][2] != 0:
            prog = prog + [(0, 0, 0)]              # ensure freeze terminator
        for lo, hi, dur in prog:
            fmtab += bytes([lo & 0xFF, hi & 0xFF, dur & 0xFF])
        ifm.append((start & 0xFF, (start >> 8) & 0xFF))
    fm_end = fmtab_addr + len(fmtab)
    # PULSETAB: distinct pulse programs ROW-major (3 bytes/entry) after FMTAB,
    # each command's start address recorded in IPULSE_LO/HI. The driver walks it
    # with a 16-bit pointer (pulse_step), so no 256-row cap.
    pulsetab_addr = fm_end
    pulsetab = bytearray()
    dstart = []                                    # start ADDR of each distinct program
    for prog in distinct:
        dstart.append(pulsetab_addr + len(pulsetab))
        for b0, b1, c2 in prog:
            # $7f = freeze: byte2 unused in the pointer model; zero it.
            c2b = 0 if (b0 & 0xFF) == 0x7F else (c2 & 0xFF)
            pulsetab += bytes([b0 & 0xFF, b1 & 0xFF, c2b])
    pulsetab_end = pulsetab_addr + len(pulsetab)
    ipulse_addr = [dstart[pidx[tuple(p)]] for p in pcmd]   # per-cmd start addr
    if pulsetab_end > 0xCF00:
        raise ValueError(f"PULSETAB overflow: ends ${pulsetab_end:04X} (> $CF00)")
    need = pulsetab_end - B.EDIT_BASE
    if len(edit) < need:
        edit.extend(bytearray(need - len(edit)))
    ilo = ifmlo_addr - B.EDIT_BASE
    ihi = ifmhi_addr - B.EDIT_BASE
    for i, (lo, hi) in enumerate(ifm):
        edit[ilo + i] = lo
        edit[ihi + i] = hi
    iplo = ipulse_lo_addr - B.EDIT_BASE            # IPULSE_LO/HI[cmd] = start addr
    iphi = ipulse_hi_addr - B.EDIT_BASE
    for i, a in enumerate(ipulse_addr[:NFM]):
        edit[iplo + i] = a & 0xFF
        edit[iphi + i] = (a >> 8) & 0xFF
    fmo = fmtab_addr - B.EDIT_BASE
    edit[fmo:fmo + len(fmtab)] = fmtab
    pto = pulsetab_addr - B.EDIT_BASE
    edit[pto:pto + len(pulsetab)] = pulsetab

    with open(os.path.join(ROOT, "drivers_src", "galway", "layout.inc"), "w") as f:
        f.write("; auto-generated (native song) by build_galway_native_song.py\n")
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


def load_song(sid_path):
    h = SIDParser(sid_path).parse_header()
    d = open(sid_path, 'rb').read()[h.data_offset:]
    la = h.load_address
    if la == 0 and len(d) >= 2:
        la = d[0] | (d[1] << 8); d = d[2:]
    st = recover_channels(d, la, h.init_address,
                          songs=getattr(h, 'songs', 1) or 1,
                          start_song=getattr(h, 'start_song', 1) or 1)
    if st is None:
        raise SystemExit("channel recovery failed for " + sid_path)
    return galway_to_driver11(st)


def playing_notes(packed):
    """Per-row freq-determining note byte. The driver changes the SID frequency
    only on a real note; sustains/gate-offs leave it, so the freq = the last
    real note byte (0 before any note)."""
    out, last = [], 0
    for n in unpack_sequence(packed):
        if SF2_NOTE_MIN <= n <= SF2_NOTE_MAX:
            last = n
        out.append(last)
    return out


def freq_of(note):
    return 0 if note == 0 else (FREQ_TABLE_LO[note - 1] | (FREQ_TABLE_HI[note - 1] << 8))


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Galway_Martin", "Wizball.sid")
    song = load_song(sid)
    print(f"song: {song.note_count} notes, {len(song.instruments)} instruments, "
          f"tick {song.tempo}")

    # Pack every voice into its patterns. The cap controls the edit-area size:
    # build_placeholder lays tables AFTER the sequences, and the old (Oct-2023)
    # SF2II release only tolerates tables up to ~$2106, so a low cap (1) keeps
    # the file compatible with it; the newer build handles the full 30.
    MAXPAT_PER_VOICE = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    segs = [segment_track(song.tracks[v])[:MAXPAT_PER_VOICE] or [bytes([0x7F])]
            for v in range(3)]
    out_name = ("galway_native_song.sf2" if MAXPAT_PER_VOICE >= 30
                else "galway_native_song_compat.sf2")
    print(f"patterns per voice: {[len(s) for s in segs]} (total {sum(len(s) for s in segs)})")

    instrs = []
    for gi in song.instruments[:32]:
        wf = song.wave_table[gi.wave_idx][0] if gi.wave_idx < len(song.wave_table) else 0x41
        # pulse-width base (hi nibble) from the instrument's pulse program
        # (program byte0 = $80 | width_hi).
        if gi.pulse_idx < len(song.pulse_table):
            pw = song.pulse_table[gi.pulse_idx][0] & 0x0F
        else:
            pw = 0x08
        instrs.append((gi.ad, gi.sr, wf or 0x41, pw or 0x08))
    if not instrs:
        instrs = [(0x09, 0x00, 0x41, 0x08)]

    B.TEST_INSTR = instrs
    B.TEMPO = max(1, song.tempo)
    B.N_ROWS = 24

    # Instrument names (id=4 TableText aux) so the editor's F2 list isn't blank.
    def _wftag(wf):
        for bit, t in ((0x80, "noise"), (0x40, "pulse"), (0x20, "saw"), (0x10, "tri")):
            if wf & bit:
                return t
        return "inst"
    names = [f"{_wftag(ins[2])} {i + 1:02d}" for i, ins in enumerate(instrs)]

    gen, edit, mdp, seq0 = gen_includes_song(segs, instrs)
    prg = B.assemble()
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)
    out = os.path.join(ROOT, "out", out_name)
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes); top table addr ~${gen.instr_addr:04X}")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${la:04X} tracks={di.track_count}",
          "OK" if la == 0x0D7E else "FAIL")

    # headless: the driver should reproduce each voice's note frequencies
    # (each voice starts on its first pattern = segs[v][0]).
    exp = [playing_notes(segs[v][0]) for v in range(3)]
    rows = B.headless_audio(prg, edit)
    bad = 0
    print("  row:  V0      V1      V2     (expected)")
    for r in range(min(B.N_ROWS, *[len(e) for e in exp])):
        e = [freq_of(exp[v][r]) for v in range(3)]
        g = rows[r]
        # tolerate vibrato (held notes wobble +-~64 around the base)
        good = all(abs(g[v] - e[v]) <= 0x80 for v in range(3))
        bad += 0 if good else 1
        if r < 12:
            print(f"  {r}: " + " ".join(f"${g[v]:04X}" for v in range(3))
                  + "  (" + "/".join(f"${e[v]:04X}" for v in range(3)) + ") "
                  + ("ok" if good else "X"))
    print(("SONG AUDIO OK — real Galway notes play through the native driver"
           if bad == 0 else f"AUDIO MISMATCH ({bad} rows)"))


if __name__ == "__main__":
    main()
