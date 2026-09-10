# Driver 11 — SF2-exported files & safe default

**Player:** SID Factory II's own Driver 11 (any SF2-exported file)
**Registry key:** `driver11`
**Driver:** `sf2driver11_00.prg`
**Accuracy:** **UNEVIDENCED for SF2-exported files** — the "100% by construction" claim is RETRACTED (2026-09-09); **safe default** otherwise. See "The 100% claim" below.
for unknown players. Canonical figures: `docs/reference/ACCURACY_MATRIX.md`.
**Corpus:** round-trip test files; the fallback for anything unrecognised

When a SID was **exported from SID Factory II**, it already uses Driver 11's structure — so converting it back to SF2 with Driver 11 should preserve the exact tables. THAT SENTENCE IS NOT EVIDENCE FOR A NUMBER, and the **100%** it used to assert is retracted (2026-09-09). Two measurements say why. FIRST, the population is empty: of 46 tree SIDs carrying the $1337 marker, 37 pass the gate and **all 37 got driver11 from the FALLBACK DEFAULT** (reason string "Standard SF2 driver for maximum compatibility") — **zero** were positively identified as SF2-exported. They are native rips (Hubbard 14, Bjerregaard/DMC 5, Gray 3, Shogoon/HardTrack 3, Gallefoss 3, Tel 2). SECOND, the mechanism the sentence names is not running: sequence extraction was measured byte-for-byte on 3 files with the parser returning garbage versus nothing, and the output was IDENTICAL (17,957 / 25,566 / 19,542 bytes) — so it is now quarantined. Whatever fidelity this path has on a genuine export, no file in this tree demonstrates it. Driver 11 remains the **safe default** when the player cannot be identified.

---

## player-id strings → Driver 11
`SidFactory_II` · `SidFactory` · `SF2_Exported` · `Driver_11`
…plus the **author-Laxity SF2 exports** `SidFactory_II/Laxity` and `SidFactory/Laxity` (exported *by* Laxity, but Driver 11 internally).

> Critical: `SidFactory_II/Laxity` ≠ native Laxity. "SidFactory" in the player-id → Driver 11; `Laxity_NewPlayer_V21` → the Laxity driver.

---

## Driver 11 versions
| Version | Changes |
|---------|---------|
| 11.00 | Original default driver (the template used here) |
| 11.01 | + fret-slide command |
| 11.02 | + pulse/tempo/volume commands |
| 11.03 | + additional filter-enable flag |
| 11.04 | + note-event delay |
| 11.05 | fret-slide removed, HR table 16→8 rows, skip-pulse-reset flag |

Driver `.prg` files live in `bin/drivers/sf2driver11_0X.prg`; F12 command overlays in `bin/overlay/<os>_driver11_0X.png`.

---

## The `$16CC` command byte — and why the first play call plays nothing

**This section is repo-wide, not player-specific.** It was found in the HardTrack
arc but is a property of Driver 11 itself, so it applies to every Stage A
transpile here.

Driver 11's three entry points are not init/play/stop in the usual sense. They
are a **command protocol** over one byte at `$16CC`; all the work happens in the
per-frame tick at `$1006`.

| entry | what it does | command left in `$16CC` |
|---|---|---|
| `$1000` init (A = subtune) | `STA $16CD` / `LDA #$00` / `STA $16CC` | **`$00`** — "state not initialised" |
| `$1003` stop | `LDA #$40` / `STA $16CC` | **`$40`** |
| `$1006` **tick** | dispatches on `$16CC` — **this is the per-frame call** | — |

```
1006: LDA #$00
1008: BIT $16CC
100B: BMI $1051   ; $80 -> play one row/frame          (the steady state)
100D: BVS $1047   ; $40 -> STOP: STA $D404/$D40B/$D412 (gate off), RTS
100F: ...         ; $00 -> INITIALISE: clear $16CD-$1740, seed from $1744/$1764,
1041: LDA #$80    ;        set the command to $80, RTS
1043: STA $16CC   ;        -- and play NO row this call
```

So after `$1000`, the **first `$1006` call is spent initialising** and touches no
SID register; the first row sounds on the **second** call. Every Driver 11 render
starts exactly **one frame later** than a native player whose play call plays a
row immediately.

Measured on the shipped template `G5/examples/Driver 11 Test - Arpeggio.sf2`:
tick 0 changes **0** SID registers and 35 bytes of `$16C0-$1750` (`$16CC`
`$00`→`$80`); tick 1 makes the first 7 SID writes. Pinned by
`pyscript/test_driver11_startup_frame.py`.

**Who this affects.** Every fidelity harness that wraps a Driver 11 SF2 as a PSID
probe with `init=$1000, play=$1006` — `bin/hardtrack_to_sf2.py`,
`bin/deenen_sf2_validate.py`, `bin/fc_validate.py`, `bin/mon_sf2_validate.py`,
`bin/romuzak_validate.py`, `bin/soundmonitor_sf2_validate.py`. Against a
**native-player** original, every note lands one frame late.

**Who it does not.** The repo's own native drivers declare their own jump table —
`init $1000`, **`play $1003`**, `stop $1006` (`DRV_INIT/DRV_PLAY/DRV_STOP` in
`bin/build_*_driver_full.py`) — and their first play call does play a row
(measured: 16 SID registers change on tick 0). Nor does it affect a Driver 11
file compared against another Driver 11 file: both sides carry the same frame.

**How to handle it.** Do **not** patch `$16CC` in the emitted file — the driver
would never initialise. A uniform 20 ms offset of the whole song is not a fidelity
defect; it only breaks frame-indexed comparison. Subtract the known phase in the
*validator* (`pyscript/hardtrack_stagea_validate.py --lag 1` is the reference
implementation) and quote the lag with the score.

> **Correction.** An earlier writeup (v3.24.0) attributed this to the template
> shipping `$16CC = $40`, with `BVS $1047` taking a "state-init path". The stored
> byte *is* `$40`, but `init` overwrites it with `$00` before the first tick, and
> `$1047` is the **stop** path (gate off), not init. The one-frame effect was
> measured correctly; the mechanism was read off the file at rest instead of from
> a run, and is corrected here. See PATTERNS.md **F6**.

**Unrelated use of the same address:** `$16CC-$1702` is also SF2II's pinned
playback-state region, which native drivers must keep clear
([NATIVE_DRIVER.md](NATIVE_DRIVER.md), `sidm2/sf2_caps.py`). `$16CC` is the
command byte *because* it is the first byte of that state block.

---

## Convert
```bash
sid-to-sf2.bat input.sid out.sf2 --driver driver11
```

It is also the foundation the **Galway** Stage-A transpile targets (see [GALWAY.md](GALWAY.md)) and the table format the native Galway driver reuses.

**Tables (SF2 Driver 11):** `SEQ=$0903`, `INST=$0A03`, `WAVE=$0B03`, `PULSE=$0D03`, `FILTER=$0F03`. Format spec: `docs/reference/SF2_FORMAT_SPEC.md`.

---

## The extractor is INERT on this path — measured 2026-09-03

`analyze_sid_file` picks between three extractors, and for a file that takes the
SF2-export branch the answer turns out not to matter: **whichever extractor runs,
the emitted `.sf2` is byte-identical.**

Forcing the SF2 branch on and off over three Rob Hubbard rips (the shape of the
37 files that used to reach it — see below):

| file | misrouted (SF2PlayerParser) | correct (Laxity table extraction) |
|---|---|---|
| `Commodore_64_Music_Examples` | 17,957 B | 17,957 B — **identical** |
| `Chimera` | 52,658 B | 52,658 B — **identical** |
| `Delta_Mix-E-Load_loader` | 52,214 B | 52,214 B — **identical** |

That is not because the two extractors agree. They hand downstream materially
different data for the same file:

| field | SF2PlayerParser | Laxity extraction |
|---|---|---|
| `sequences` | **0** | **3** |
| `instruments` | **0** | **8** |
| `orderlists` | 3 | 3 |

**Three sequences and eight instruments make no difference to a single output
byte.** So `ExtractedData.sequences` and `.instruments` do not reach the writer
on this path at all; the music in the output comes from somewhere else, and the
extraction stage is decorative for these files.

Two consequences, and the second is the one that matters:

1. **The 2026-09-03 detector fix changed no output.** `has_sf2_magic` was a
   two-byte substring search that fired on 46 of 1,524 tree SIDs and routed 37
   native rips into this branch; replacing it with `has_sf2_structure` corrected
   the routing and the log line — the `.sf2` bytes are unchanged, verified
   above. Nothing in `out/` needs rebuilding on account of it.
2. **"100% by construction" is not evidenced by this path.** The claim in this
   file's header, and `ACCURACY_MATRIX.md`'s "Guaranteed 100%", rest on
   "converting it back to SF2 with Driver 11 preserves the exact tables". The
   preservation cannot be happening through `sequences` or `instruments`,
   because those are demonstrably ignored. Whatever fidelity this path has, it
   is not delivered by the mechanism the sentence describes. Tracked as
   `sf2-exported-100pct-fork-decision`, which is a decision for a human: either
   quarantine the sequence-extraction path and restate the claim, or authorise
   the repair in `sf2-player-parser-locate-then-decode-then-duration`.

Reproduce by monkeypatching `conversion_pipeline.has_sf2_structure` to a
constant and converting the same file twice; do NOT read the emitted sequences
back with `sf2_viewer_core.SF2Parser` to check this — its fallback readers
over-read (they report 71,236 entries across 12 sequences in the 17,957-byte
file above), which is `unbounded-laxity-fallback-readers-emit-13k-entry-sequences`
and would give a confidently wrong answer here.
