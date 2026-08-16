# Handoff — SIDM2 session, 2026-08-14/15

<original_task>
Opened with **"read what next"**, then short directives throughout: **"do the
task on the list"**, **"turn it on by default and rebuild the corpus"**, **"do
2"**, **"do 3 and do 5"**, **"do 1 and 5"**, **"do the DMC pitch residual"**,
**"do Juba-Jazz"**, **"do Flimbos_Quest_main"**, and **"push"** repeatedly. One
`/subtask` fork reviewed the **h2g** project, which the user then designated
**reference-only — do not modify it**.
</original_task>

<work_completed>

**10 commits on SIDM2**, `a8626e8..a6980f3`, all pushed. Suite **2,457**. Plus
one commit on **h2g** (`0275c5a`), a separate reference-only repo.

## Two through-lines

**1. The comparison window was wrong in four tools.** Every scorer comparing one
*part* of a windowed build against the original needs to know where that part
ENDS; past it our build LOOPS while the original plays on. Fixed by making the
artifact record its own window (`.span` sidecar from `emit_one`,
`part_span`/`window_for` in `fidelity_common`) — `PATTERNS.md` **F8**.

**2. Three published figures were measurement artifacts, not defects.** Each
looked like a builder bug and was not: a reference that could not drive the tune,
a window that over-ran, and a scorer scoring a build that never plays a note.

## Commit by commit

| commit | what |
|---|---|
| `7c89ab5` | HardTrack per-note SR lookahead built. Registers improve corpus-wide but `Love_tune_2` gets **darker** — answer to the filed brightness question: **no** |
| `d0ec20c` | The selector is instrument **mode 2**, tested on the note that is **ENDING** (242/242, 158/158, 375/375, 0 false positives in 1,260). Shipped ON; corpus 12,397 → 1,794 mismatching `$D406` frames, worse on 0 |
| `4f9b47c` | SDI V path: `v_traces` now records `$D418` — but the 0.0% was a **reference** defect. siddump calls a V rip's player once per frame where its IRQ runs `v_mult`(4). Per-**file** `sdi_v` reference; 0/4 → **5/5** |
| `0ae0738` | The `.span` sidecar. HardTrack **25 → 32/33**, SDI **241 → 258/281**, 41 UNCONFIRMED → **0**. Failures ROSE 3 → 7, which is the guard working |
| `0df2d99` | A quarter of the DMC tail was the window: `part1_span` took the FIRST `part 1/N` line, which belongs to a **legato A/B probe build** over a 90 s head. `Happy_Jingle` 23.4/16.1/8.1 → **98.3/100.0/98.8** |
| `a8e7e7e` | Audited every remaining scorer. SM's `parse_parts` had the same latent hazard (probe builds), guarded; corpus unmoved at 99.252% |
| `ca9678c` | **DMC pitch residual solved.** Third player to collide with the driver's `$40–$43` SCALED-vibrato marker — `Balloon`'s two-octave arp emits `+16833 = $41C1`. `Balloon` v0 **80.6 → 100.0** (n=19,996) |
| `5c5c357` | **`Juba-Jazz` 52.8 → 100.0.** Its filter is enabled by `$D417`+`$D418` with the **cutoff held at 0**, and `detect_filter_drives` keys on cutoff jumps — `PATTERNS.md` **F9** |
| `1498c3b` | `Flimbos_Quest_main` was never a fidelity defect: the parser decodes **no notes**. `build_native_song` refuses a decode with no note on any voice |
| `a6980f3` | That guard catches **three** files, not two — `Nightdawn` was scoring a **vacuous 100** |

## Corpus movement

| | start | end |
|---|---:|---:|
| DMC freq median | 94.7 | **98.7** |
| DMC freq voices below 90 | 89 | **47** |
| SDI passband | 237/281 | **258/281**, 0 unconfirmed |
| HardTrack passband | 25/33 | **32/33**, 0 unconfirmed |
| HardTrack `$D406` frames wrong | 12,397 | **1,794** |

</work_completed>

<attempted_approaches>

## Retracted or corrected — six, four of them my own

1. **"87 of 216 DMC frequency voices below 90, large and unexplained."** A
   quarter was the window; the rest splits by cause.
2. **`Happy_Jingle` 23.4/16.1/8.1**, **`Depeche_Mode_Songs` 37.9/31.6/29.0** —
   both ~98-100% over their own parts.
3. **`Filthy_Hit_VE-4x` "0.0%, the last real SDI passband gap"** — the reference
   could not drive the tune. It is 100.0%.
4. **My "discarded trial split"** — it is a legato A/B *probe build*.
5. **My "20 of 88 DMC files decode to silence"** — that probe bypassed the
   builder's phase selection.
6. **My "exactly two silent builds"** — missed `Nightdawn`, whose silent build
   reads freq **100.0/97.8** because a constant held on BOTH sides over 46 frames
   scores a vacuous 100. Only building the corpus with the guard got it right.

## Traps worth carrying

- **A lookup that fails open reads exactly like one that worked.** The first
  `.span` run derived nothing — half the players are keyed on the `.sid` wrapper
  and half on the `.sf2`. Hence the `[Ns = its own part 1]` marker.
- **`SR=$00` zeroes SUSTAIN as well as release**: one mistimed kill silences the
  rest of a held note while every later register still reads correct (−24 dB).
- **Gate-off is not silent.** DMC's pitch mismatches are all gate-off, but the
  release nibble is 11 (~750 ms), so they ring out audibly. I inferred
  "inaudible" and withdrew it after measuring.
- **Corpus builders may now run CONCURRENTLY** — `--jobs N` takes a
  cross-process lock (`PATTERNS.md` **F12**). The old rule said they share
  `drivers_src/mon/layout.inc` and cited F2, which is a different hazard
  (editing a module mid-run) and never said this; the real contention was
  three files plus the scorer's probe, all now closed.
- **Verify a shared-detector change on the NEIGHBOURS**, not the target: F9's
  fix was proven by HardTrack being 31/33 byte-identical with the other 2
  measuring identically.
- **The heredoc backslash trap**, twice more. Use the Write tool, forward slashes.

</attempted_approaches>

<critical_context>

- **`.span` sidecars** are written by `emit_one` for every part; `out/` is
  gitignored, so pre-session artifacts have none — and **absent must stay
  distinguishable from zero**.
- **A recorded span may only NARROW a window**, never widen it.
- **`no_fm_scale` is a per-shim opt-out three players have now had to discover
  the hard way** (Hubbard, HardTrack, DMC). The durable fix — disable the
  `$40-$43` marker automatically when a song's own offsets collide with it — is
  NOT done, because legitimate scaled entries use the same encoding.
- **h2g is reference-only.** v0.5.254, suite 979/0 after GoatTracker 2.77 was
  installed and `siddump-rt` built with `zig cc`.
- Rebuild scripts: `pyscript/hardtrack_native_rebuild.py`,
  `pyscript/dmc_native_sweep.py --build`, `bin/build_sdi_native_song.py`.

</critical_context>

<current_state>

Suite 2,457, version 3.27.0 (unchanged — this session's cadence).

**Open work, ranked:**

1. **The DMC whole-build queue.** *Opus, main.* `Roadblaster` v0/v2 **58.6/62.0
   over n=15,996** is the largest and best-evidenced. The class is defined:
   freq AND wf AND pulse all below 90 on the same voice, ~17 songs. Note that
   `Happy_Jingle` and `Depeche_Mode_Songs` left this class once their windows
   were honest, so re-derive membership from `out/dmc_sweep4.json` before
   assuming a file belongs.
2. **The 14 MIXED DMC voices** — neither pitch-only nor whole-build; likely
   splits again. *Delegable measurement pass.*
3. **Small passband residuals.** *Delegable.* `Tanks_3000` (static vs 12
   changes, 72 audible), `Arabia` 98.2%, `Funk_Facet` 99.0%/12 audible,
   HardTrack's `Fun_Factory` 99.0%/3 audible.
4. **Make the `$40-$43` marker self-disabling** rather than a per-shim opt-out —
   see critical context. *Main; needs care.*
5. **`Flimbos_Quest_main`/`Kamikaze`/`Nightdawn` decodes** — now honestly
   refused, but the variant is undecoded. A parser question, not a fidelity one.

**Older, still open:** `Coming_Soon` (90.9%), `Lederhosen`; `Bahbar_v` has no
original; `Altered_States_Tune_2`'s 47-frame first-filter-row latency
(inaudible, unexplained); a startup-latency generalisation discarded as
under-controlled.

**Closed this session:** HardTrack #16 (the brightness gap — `Love_tune_2`'s
darkness is the cost of modelling the player's own release kill), the SDI V-path
passband, the 41 UNCONFIRMED rows, and the DMC pitch residual.

</current_state>
