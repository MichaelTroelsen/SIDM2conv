# Handoff — SIDM2 session, 2026-08-14/15

<original_task>
Opened with **"read what next"**, then a series of short directives: **"do the
task on the list"** (twice), **"turn it on by default and rebuild the corpus"**,
one `/subtask` fork to review the **h2g** project, **"do 2"**, **"do 3 and do
5"**, **"do 1 and 5"**, and **"push"** several times. No pre-set scope beyond the
filed list.
</original_task>

<work_completed>

**5 commits on SIDM2**, `a8626e8..HEAD`, pushed. Suite **2,455+**. Plus one
commit on **h2g** (`0275c5a`), a separate repo the user has designated
**reference-only — do not modify it**.

## The through-line: the comparison window was wrong in FOUR tools

Every scorer that compares one *part* of a windowed build against the original
needs to know where that part ENDS. Past it our build LOOPS while the original
plays on, and the difference scores as a defect. This session found that error
in four places, corrected three published figures, and then removed the class.

**The durable fix**: `emit_one` — the one emitter every native builder goes
through — now writes a `.span` sidecar beside each artifact, and
`part_span`/`window_for` live in `sidm2/fidelity_common.py`. Written up as
`PATTERNS.md` **F8**.

| tool | verdict |
|---|---|
| `passband_check` | 41 UNCONFIRMED rows → **0** |
| `dmc_native_sweep` | **live defect**; corpus freq median 94.7 → **97.3** |
| `soundmonitor_sweep` | **latent hazard**, guarded; corpus unmoved at 99.252% |
| `hardtrack_native_sweep` | immune — builds *to* the window instead of guessing |
| `sdi_native_sweep`, `mon_part_fidelity`, `blackbird_sweep` | already safe |

## Commit by commit

### `7c89ab5` — the HardTrack per-note SR lookahead, built and measured
The rung-4 experiment `HARDTRACK.md` had left open. `SR_PREKILL` in
`drivers_src/mon/romuzak_driver.asm`. Registers improved corpus-wide but
`Love_tune_2` — the one file the brightness gap was about — got **darker**
(−57.9 → −101.4 Hz centroid). Answer to the filed question: **no**.

### `d0ec20c` — the selector is instrument **mode 2**, shipped ON
Both of the player's `LDA #$00 / STA $D406,y` sites are guarded by the
**PREVIOUS** frame's mode (disassembly in `HARDTRACK.md`). Keyed on the note that
is **ENDING**: `Teekkno` 242/242, `Love_tune_2` 158/158, `Muminki` 375/375, **0
false positives in 1,260 note-ons**. Corpus **12,397 → 1,794** mismatching
`$D406` frames over 33 files, worse on 0. Gate it on the ending note or `Teekkno`
goes 42 → **468**. Corpus rebuilt: 33/33, 313 parts.

### `4f9b47c` — SDI's V path: half a builder gap, half a bad reference
`v_traces` now records `$D418`. But the 0.0% was **not** a build defect:
siddump calls a V rip's player **once** per frame where its own IRQ runs
`v_mult` (4), so the two sample different instants of a passband that alternates
*within* the frame — 375 of 400 frames BP against 303 ending on LP. Proven by
running the same tracer at `mult=1`, which reproduces siddump exactly.
`passband_check` gained a per-**FILE** `sdi_v` reference. **0/4 → 5/5**, corpus
237 → 241.

### `0ae0738` — the artifact records the window it was built for
HardTrack **25 → 32 of 33**, SDI **241 → 258 of 281**, 41 UNCONFIRMED → 0.
Failures ROSE 3 → 7 on SDI, and that is the mechanism working: over-run
manufactures disagreement but never conceals it.

### `0df2d99` — a quarter of the DMC tail was the window
`part1_span` re-parsed the builder's stdout and `re.search` took the FIRST
`part 1/N` line — which belongs to a **legato A/B probe build over a 90 s head**
(`_abg`/`_abl`), not to the part being scored. `Happy_Jingle`'s 7 s part 1 was
scored over 90 s: read **23.4/16.1/8.1**, is **98.3/100.0/98.8 with zero presence
mismatch**. `Depeche_Mode_Songs` 37.9/31.6/29.0 → **100.0/100.0/94.5**. Both
RETRACTED.

</work_completed>

<attempted_approaches>

## Retracted or corrected this session

1. **"87 of 216 DMC frequency voices below 90, large and unexplained."** A
   quarter was the window; the rest splits three ways (below). The work it
   implied — hunt one pitch mechanism — was the wrong shape.
2. **`Happy_Jingle` 23.4/16.1/8.1 and `Depeche_Mode_Songs` 37.9/31.6/29.0.**
   Both are ~98-100% over their own parts.
3. **`Filthy_Hit_VE-4x` "0.0%, the last real SDI passband gap."** The reference
   could not drive the tune. It is 100.0%.
4. **My own "discarded trial split"** in `0df2d99`'s message — it is a legato
   A/B *probe build*, corrected in the code comments.

## Traps worth carrying

- **A lookup that fails open reads exactly like one that worked.** The first
  `.span` run derived **nothing**: half the players are keyed on the `.sid` PSID
  wrapper and half on the `.sf2`, and the sidecar sits beside the `.sf2`. Hence
  the `[Ns = its own part 1]` marker — a positive signal that it fired.
- **`SR=$00` zeroes SUSTAIN as well as release.** The envelope falls to zero and
  only a gate RISE re-attacks it, so one mistimed kill silences the rest of a
  held note **while every later register still reads correct**. 4 such frames
  cost −24 dB.
- **Never run two corpus builders at once.** They all assemble through
  `drivers_src/mon/layout.inc`; concurrent runs race and produce artifacts that
  look fine and are wrong (`PATTERNS.md` F2).
- **The heredoc backslash trap, twice more.** `<<'PY'` ate `\r\n` into literal
  newlines, and `"bin\\build_x.py"` became `bin\x08uild_x.py`. **Write patch
  scripts with the Write tool and use forward slashes.**
- `drivers_src/mon/romuzak_driver.asm` is **CRLF**.

</attempted_approaches>

<critical_context>

- **`.span` sidecars**: written by `emit_one` for every part; `out/` is
  gitignored, so an artifact built before this session has none — and **absent
  must stay distinguishable from zero**, which is why a file without one is
  still refused rather than defaulted.
- **A recorded span may only NARROW a window**, never widen it past `--seconds`.
- **h2g is reference-only.** `C:\Users\mit\claude\h2g`, v0.5.254, suite 979/0
  after GoatTracker 2.77 was installed to
  `C:\Users\mit\Downloads\GoatTracker_2.77\` and `siddump-rt` was built with
  `zig cc`. Its three generated artefacts reproduce byte-for-byte.
- Rebuild scripts: `pyscript/hardtrack_native_rebuild.py`,
  `bin/build_sdi_native_song.py`, `pyscript/dmc_native_sweep.py --build`.

</critical_context>

<current_state>

Suite 2,455 passing, version unchanged at 3.27.0 (this session's cadence).

## The DMC tail, split by cause — the queue that replaces "87 of 216"

64 frequency voices below 90, over 222 voices / 74 songs:

| class | voices | songs |
|---|---:|---|
| **underpowered** (`n` below the 250-frame floor) | 22 | not a score at all |
| **pitch-only** (wf & pulse ≥ 99.5) | **6** | 5 |
| **whole-build** (wf & pulse also < 90) | **22** | 17 |
| mixed | 14 | |

**Open work, ranked:**

1. **The DMC pitch residual — 6 voices, 5 songs.** *Opus, main.* `Balloon` v0
   **80.6 over n=19,996** is the one to solve: flagship build, enormous sample,
   and wf/pulse are both ≥99.5 on that voice, so it isolates a pure pitch
   mechanism. Then `Namnam_Special` 81.0/88.8, `Again_Its_JB` 81.8, `Blobby`
   88.9, `DMC_Demo_IV_tune_2` 88.7.
2. **`Juba-Jazz` — 52.8% passband over 661 audible frames.** *Delegable.* The
   largest real passband defect known; its part 1 spans 72 s so nothing about it
   is a window artifact.
3. **`Flimbos_Quest_main` — a silent build.** *Delegable.* 589 frames where the
   original sounds and we never write a frequency, on every voice, at every
   offset −40…+400. Head of the 17-song whole-build queue.
4. **The other new passband failures**: `Tanks_3000` (static vs 12 changes, 72
   audible), `Arabia` 98.2%, `Funk_Facet` 99.0%/12 audible, HardTrack's
   `Fun_Factory` 99.0%/3 audible. *Delegable, small.*
5. **The 14 MIXED DMC voices** — unclassified; likely splits again.
6. **HardTrack #16 is CLOSED as posed.** `Love_tune_2`'s darkness is now
   understood as the cost of modelling the player's own release kill. Anyone
   reopening it should start from the loud frames (−1.87 → −2.26 dB), not the
   tails.

**Older, still open:** `Coming_Soon` (90.9%) and `Lederhosen`; `Bahbar_v` has no
original; `Altered_States_Tune_2`'s 47-frame first-filter-row latency
(inaudible, unexplained); a startup-latency generalisation discarded as
under-controlled.

</current_state>
