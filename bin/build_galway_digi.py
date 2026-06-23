"""Galway DIGI capture -> sample bank + trigger sequence (asm data).

Galway's "4th channel" samples ($D418 volume digi) live in the RSID rips but are
driven by a fast IRQ/main-loop that py65/zig64 don't emulate. VICE does. This
tool:
  1. renders the tune through VICE with -sounddev dump (the full SID register
     stream, cycle-accurate),
  2. filters $D418 (reg 24), segments the nibble stream into bursts (drum hits),
  3. FUZZY-dedupes the bursts into a small unique sample bank,
  4. emits an asm include (digi_data.inc): the packed-as-1-nibble/byte bank, the
     per-sample offset/length index, and a per-onset trigger list (frame, sid).

The native Galway driver streams the active sample to $D418 from do_play (proven
to play in stock SF2II — no separate IRQ needed).

Usage: py -3 bin/build_galway_digi.py <SID name> [seconds] [tune]
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VSID = r"C:/winvice/bin/vsid.exe"
PAL = 985248
CYC_PER_FRAME = PAL // 50          # 19704
BANK_ADDR = 0x8000                 # sample bank base (free above the edit area)


def dump_d418(sidpath, seconds, tune):
    """Render via VICE, return the $D418 nibble stream as [(abs_cycle, nibble)]."""
    dump = os.path.join(ROOT, "out", "_digi.dump")
    try:                                   # vsid runs forever; timeout-kill is expected
        subprocess.run([VSID, "-console", "-sounddev", "dump", "-soundarg", dump,
                        "-tune", str(tune), sidpath],
                       capture_output=True, timeout=seconds + 2)
    except subprocess.TimeoutExpired:
        pass
    cum = 0
    out = []
    for line in open(dump):
        p = line.split()
        if len(p) != 3:
            continue
        try:
            c, r, v = int(p[0]), int(p[1]), int(p[2])
        except ValueError:
            continue
        cum += c
        if r == 24:
            out.append((cum, v & 0x0F))
    os.remove(dump)
    return out


def segment(writes, gap=3000, minlen=24):
    """Split the stream into bursts (a drum hit = a run of close-spaced writes).
    gap must exceed the music IRQ's mid-drum pause (~1-2k cycles on Arkanoid's
    2-raster player) so a single hit isn't fragmented, yet stay well below the
    inter-drum spacing (tens of thousands of cycles)."""
    bursts, cur = [], [writes[0]]
    for i in range(1, len(writes)):
        if writes[i][0] - writes[i - 1][0] > gap:
            if len(cur) >= minlen:
                bursts.append(cur)
            cur = []
        cur.append(writes[i])
    if len(cur) >= minlen:
        bursts.append(cur)
    return bursts


def fuzzy_dedupe(pcms, len_tol=12, diff_tol=1.4):
    """Greedy-cluster near-identical sample PCMs. Returns (bank, sid_per_pcm).
    Two samples match if their lengths are within len_tol and the mean per-sample
    abs difference over the overlap is below diff_tol (4-bit scale 0..15)."""
    bank, sids = [], []
    for pcm in pcms:
        best = None
        for sid, rep in enumerate(bank):
            if abs(len(rep) - len(pcm)) > len_tol:
                continue
            n = min(len(rep), len(pcm))
            d = sum(abs(rep[i] - pcm[i]) for i in range(n)) / n
            if d < diff_tol and (best is None or d < best[1]):
                best = (sid, d)
        if best is not None:
            sids.append(best[0])
        else:
            sids.append(len(bank))
            bank.append(pcm)
    return bank, sids


DRIVER_RATE = 9566.0          # the NCO engine's $D418 write rate (gap ~103 cyc)


def nco_incr_table(writes):
    """Per video-frame, measure the $D418 SAWTOOTH pitch and convert it to the
    driver NCO's 8-bit phase increment. Arkanoid's digi is a continuous sawtooth
    LEAD (phase += step each nibble, written every `gap` cycles); pitch = the per-
    frame (step/gap). incr = round(freq * 256 / DRIVER_RATE); 0 = rest (the music
    IRQ took the whole frame -> leave the master volume to the music)."""
    import numpy as np
    fr = {}
    for c, n in writes:
        fr.setdefault(c // CYC_PER_FRAME, []).append((c, n))
    nframes = max(fr) + 1
    incrs = []
    for f in range(nframes):
        items = fr.get(f, [])
        if len(items) < 8:
            incrs.append(0)                     # rest
            continue
        cs = [c for c, _ in items]
        ns = [n for _, n in items]
        gaps = np.diff(cs)
        inner = gaps[gaps < 1000]               # within-frame write spacing
        g = np.median(inner) if len(inner) else np.median(gaps)
        ds = [((ns[i] - ns[i - 1]) % 16) for i in range(1, len(ns))]
        ds = [d - 16 if d > 8 else d for d in ds]
        from collections import Counter
        step = Counter(ds).most_common(1)[0][0]
        if step == 0 or g <= 0:
            incrs.append(0)
            continue
        freq = abs(step) / 16.0 * 985248.0 / g
        incr = int(round(freq * 256.0 / DRIVER_RATE))
        incrs.append(max(0, min(255, incr)) if incr >= 1 else 0)
    return incrs


def emit_nco(name, tune, writes):
    incrs = nco_incr_table(writes)
    voiced = sum(1 for i in incrs if i)
    print(f"  NCO melody: {len(incrs)} frames, {voiced} voiced "
          f"({100*voiced//max(1,len(incrs))}%), incr range "
          f"{min([i for i in incrs if i], default=0)}-{max(incrs)}")
    blob = bytes(incrs) + bytes((0,))           # trailing 0 = end/rest
    open(os.path.join(ROOT, "out", "digi_blob.bin"), "wb").write(blob)
    inc = os.path.join(ROOT, "drivers_src", "galway", "digi_addrs.inc")
    with open(inc, "w") as f:
        f.write(f"; auto-generated NCO digi melody for {name} (tune {tune}); "
                f"data in out/digi_blob.bin @ ${BANK_ADDR:04x}\n")
        f.write(f"DIGI_NCO_FRAMES = {len(incrs)}\n")
        f.write(f"DIGI_BLOB_ADDR = ${BANK_ADDR:04x}\n")
        f.write(f"digi_nco_tab   = ${BANK_ADDR:04x}\n")
    print(f"  wrote {inc} + out/digi_blob.bin ({len(blob)} B @ ${BANK_ADDR:04x})")


def main():
    name = sys.argv[1]
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    tune = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    sidpath = os.path.join(ROOT, "SID", "Galway_Martin", name + ".sid")

    print(f"VICE dump of {name} ({seconds}s, tune {tune})...")
    writes = dump_d418(sidpath, seconds, tune)
    if os.environ.get("GALWAY_DIGI_NCO"):
        emit_nco(name, tune, writes)
        return
    bursts = segment(writes)
    pcms = [[n for _, n in b] for b in bursts]
    onsets = [b[0][0] // CYC_PER_FRAME for b in bursts]   # onset video frame
    bank, sids = fuzzy_dedupe(pcms)

    # representative bank: the LONGEST member of each cluster (most complete hit)
    reps = [max((pcms[i] for i in range(len(pcms)) if sids[i] == s), key=len)
            for s in range(len(bank))]
    total = sum(len(r) for r in reps)
    print(f"  {len(bursts)} hits -> {len(reps)} unique samples, "
          f"{total} nibbles ({total/1024:.1f} KB @ 1 nibble/byte)")
    print(f"  trigger frames: {len(onsets)} onsets over {max(onsets)} frames")

    # Build a single BINARY blob (the build injects it high, separate from the
    # driver PRG): [bank nibbles][off_lo][off_hi][len_lo][len_hi][triggers].
    # The driver just gets the addresses (digi_addrs.inc, equates only) — keeping
    # the 3.7 KB bank out of the compact driver PRG / edit-area layout.
    n = len(reps)
    flat = bytearray(b for r in reps for b in r)
    offs, cur = [], 0
    for r in reps:
        offs.append(cur)
        cur += len(r)
    off_lo = bytes((BANK_ADDR + o) & 0xFF for o in offs)
    off_hi = bytes(((BANK_ADDR + o) >> 8) & 0xFF for o in offs)
    len_lo = bytes(len(r) & 0xFF for r in reps)
    len_hi = bytes((len(r) >> 8) & 0xFF for r in reps)
    trig = bytearray()
    prev = 0
    for fr, sid in sorted(zip(onsets, sids)):
        delta = fr - prev
        while delta > 254:
            trig += bytes((0xFE, 0xFE))     # wait 254, no-op
            delta -= 254
        trig += bytes((delta & 0xFF, sid & 0xFF))
        prev = fr
    trig += bytes((0x00, 0xFF))             # end marker

    blob = bytes(flat) + off_lo + off_hi + len_lo + len_hi + bytes(trig)
    a_bank = BANK_ADDR
    a_offlo = a_bank + len(flat)
    a_offhi = a_offlo + n
    a_lenlo = a_offhi + n
    a_lenhi = a_lenlo + n
    a_trig = a_lenhi + n
    open(os.path.join(ROOT, "out", "digi_blob.bin"), "wb").write(blob)
    inc = os.path.join(ROOT, "drivers_src", "galway", "digi_addrs.inc")
    with open(inc, "w") as f:
        f.write(f"; auto-generated digi addresses for {name} (tune {tune}); "
                f"data in out/digi_blob.bin @ ${BANK_ADDR:04x}\n")
        f.write(f"DIGI_NSAMP    = {n}\n")
        f.write(f"DIGI_BLOB_ADDR = ${a_bank:04x}\n")
        f.write(f"DIGI_BLOB_LEN  = {len(blob)}\n")
        f.write(f"digi_bank     = ${a_bank:04x}\n")
        f.write(f"digi_off_lo   = ${a_offlo:04x}\n")
        f.write(f"digi_off_hi   = ${a_offhi:04x}\n")
        f.write(f"digi_len_lo   = ${a_lenlo:04x}\n")
        f.write(f"digi_len_hi   = ${a_lenhi:04x}\n")
        f.write(f"digi_triggers = ${a_trig:04x}\n")
    print(f"  wrote {inc} + out/digi_blob.bin ({len(blob)} B @ ${BANK_ADDR:04x}-${BANK_ADDR+len(blob):04x})")


if __name__ == "__main__":
    main()
