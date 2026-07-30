# SIDM2 Full Toolchain & Player Code Review — 2026-07-30

**Method**: code reading only — no sweeps were re-run for this review. Numbers taken
from docs/logs rather than re-measured this session are marked **✻**. Every finding
carries at least one `file:line` or doc citation verified against the working tree
(branch `mattgray-driller-stage-a`) on 2026-07-30.

**Relationship to [ROADMAP.md](ROADMAP.md)**: the ROADMAP remains the strategic
document. This review re-verified its open items against current code, folded in the
seven player arcs that landed after it was written (Blackbird Stage B, SDI, DMC,
Sound Monitor, Hubbard V2, Deenen, Matt Gray), and packages everything as
executable items. A ROADMAP cross-reference table is at the end.

**Audience**: a Sonnet or Opus session executing one item at a time. Each item names
its evidence, a fix sketch reusing existing utilities, a verification recipe, and
the known traps. **Suggested model**: Sonnet = mechanical/parameterized work with a
byte-diff or regression gate; Opus = RE, design, or falsification work.

**Priorities**: `P0` audible fidelity · `P1` part-count / files-per-song ·
`P2` correctness & infrastructure debt · `P3` hygiene.

---

## Executive summary — top items by leverage

| # | Item | Why it leads |
|---|------|--------------|
| R5 | Blackbird E3c(a): the last 40 hard-restart retriggers | ROADMAP's own "highest remaining audible payoff" |
| R6 | Galway/ROMUZAK `cmp #$90` SF2II hazard | their filter sweeps are **broken in the real editor today**, invisible to every headless metric |
| R1–R3 | Driver + builder unification, caps module | every fidelity fix currently needs 3–4 patches; every new player re-forks ~1,300 lines |
| R17 | Stage C structural synth-table RE | the **only proven lossless** part-count reduction (Supremacy 70 parts → single digits ✻) |
| R20 | Memory-wall audit for time-split parts | Driller splits into 2 files while using 41/120 sequences — the wall, not the caps, binds; nobody has measured the slack |
| R24 | Universal trace-first fallback (D1) | turns "any SID" from per-player RE into a default path |
| R21 | Reproducible corpus sweeps (SM first) | a headline number that dies with a scratch file isn't a result |
| R4 | Wire the 11 `bin/`-only players into the pipeline | "we have the tech" vs "the tool converts it" |
| R9/R10 | SDI + Matt Gray Stage B | the two largest corpora currently shipping knowingly-wrong timbre |
| R23 | Fix the `probe_once()` crash oracle | it corrupts every long play-test across all players |

---

## Track 1 — Consolidation (P2; enables most fidelity and part-count work)

### R1. Unify the four native-driver ASM copies — P2 · M · Sonnet (Opus for the Blackbird merge decision)
**Evidence** (measured this session):
- `drivers_src/galway/galway_driver.asm` 1,317 lines ↔ `drivers_src/romuzak/romuzak_driver.asm` 1,357 lines: **40 diff lines total**.
- `drivers_src/mon/romuzak_driver.asm` 2,004 lines (misnamed, CRLF endings): 777 diff lines vs romuzak.
- `drivers_src/blackbird/blackbird_driver.asm` 1,725 lines: 1,962 diff lines vs romuzak — **heavily diverged** (hard-restart sentinel, prepare-stage ordering, third filter-row type, RLE waves).

ROADMAP A1 proposed a 3-way merge; a fourth copy has since appeared. A driver bug of the
SF2II-CMP class now needs up to four patches.
**Fix sketch**: merge galway+romuzak+mon first into `drivers_src/common/sf2_native_driver.asm`
with 64tass `-D` feature flags (`FEAT_DRUM_ROWS`, `FEAT_SEEK_PULSE`, `FEAT_WAVE_RLE`,
`FEAT_FILTER_ENV`, `FEAT_PULSE16`, `FEAT_DIGI_*` — the digi flags already work this way ✻).
Evaluate Blackbird as a second step: its deltas (restart sentinel, filter row grammar
`1M DD RB`, prepare1/2/3 semantics) are feature-shaped but large — an Opus pass should
decide merge vs. "shares the common core via include".
**Verification**: byte-compare each flag combination's assembled output against the current
per-player driver **before** switching any builder over (the `assemble()` state-region and
edit-area guards already exist ✻). Then one full corpus sweep per player (Galway
`bin/build_galway_corpus.py`, Blackbird `py -3 pyscript/blackbird_sweep.py <label> --compare`).
**Traps**: SF2II's 6510 emulator (PATTERNS/PLAYBOOK §5): never `cmp` values >$7F apart; never
branch on carry after `cpx/cpy`. `pyscript/test_sf2ii_emulator_hazards.py` lints this — keep it green.

### R2. One caps module + one `fits()` — P2 · S · Sonnet
**Evidence** (measured): `CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100`
re-declared in `bin/build_dmc_native_song.py:263`, `build_hubbard_native_song.py:407`,
`build_mon_native_song.py:1954`, `build_myth_native_song.py:210`, `build_sdi_native_song.py:41`,
`build_soundmonitor_native_song.py:360`; Blackbird declares its own variant
(`build_blackbird_native_song.py:2704`, deliberately `CAP_B=96` — see its comment block at
2659–2704). `def fits(` exists in **7 builders** + `bin/_bundle_phase1.py`. `sidm2/sf2_caps.py`
does not exist (the only match for "sf2_caps" is ROADMAP.md itself).
**Fix sketch**: create `sidm2/sf2_caps.py` (63 bundles / 32 instruments / 256 rows / 120
sequences / 960-event `_SEQ_EVENT_LIMIT` / $D000 wall / state region $16CC–$1702), import it
everywhere; extract the shared adaptive-window loop (caps probe → window split) as
`sidm2/native_build/pack_adaptive_windows()` with a per-player `fits` predicate. **Keep
Blackbird's intentional `CAP_B=96` as an explicit override, not a silent fork.**
**Verification**: for each player, rebuild one known song and byte-diff the emitted `.sf2`
against pre-refactor output; part counts must be identical.
**Traps**: the 960-event limit exists because SF2II's 1024-event `Unpack` has **no bounds
check** — overflow is heap corruption, not an error. Never relax it.

### R3. Shared native-build library — P2 · M · Sonnet
**Evidence** (measured): `def gen_includes_song` copy exists in `bin/build_galway_native_song.py`,
`build_romuzak_native_song.py`, `build_blackbird_native_song.py` (MoN imports ROMUZAK's ✻);
`bin/build_galway_driver_full.py` vs `bin/build_romuzak_driver_full.py` differ by **12 lines**
(confirmed — all name substitutions ✻).
**Fix sketch**: per ROADMAP A2 — extract header/Block-2 state pinning, vstream orderlists,
sequence-slot writes, wave-program dedup, FM/PULSE row-major layout, `layout.inc` writer into
`sidm2/native_build/`; parameterize `build_*_driver_full.py` into one script with `player=`.
**Verification**: byte-diff every player's driver `.prg` and one song `.sf2` pre/post.
**Traps**: `drivers_src/*/{layout,freqtable}.inc` are regenerated every build — `git checkout`
before committing (PLAYBOOK §5).

### R4. Wire the `bin/` players into the default pipeline — P2 · M · Sonnet, with an Opus pass on routing policy
**Evidence** (measured): `sidm2/driver_selector.py:53` `PLAYER_REGISTRY` holds only
`laxity`, `driver11`, `np20`, `galway`; `sidm2/conversion_pipeline.py:109`
`_make_player_converters()` registers only `laxity` and `galway`. **Eleven ported players**
(ROMUZAK, MoN/Myth/Supremacy, Hubbard V1/V2, Kimmel, Deenen, FC, DMC, Sound Monitor,
Blackbird, SDI, Matt Gray) are unreachable from `sid-to-sf2.bat`.
**Fix sketch**: add registry entries (player-id strings per player doc) + thin converter
adapters calling the `bin/` builders; native builds behind `--native` (default where the
corpus is ✅ in [reference/ACCURACY_MATRIX.md](reference/ACCURACY_MATRIX.md), e.g. Blackbird,
MoN, ROMUZAK), Stage A otherwise. Registry docstring at `driver_selector.py:41-52` already
describes the 4-step procedure — follow it.
**Verification**: `sid-to-sf2.bat` on one file per player; `DriverSelector` unit tests;
confirm unknown players still fall through to Driver 11.
**Traps**: locators must **refuse loudly** on unknown variants (the Matt Gray `verify()`
pattern ✻) — auto-routing a mis-located variant produces garbage with a confident filename.
"SidFactory_II/Laxity" must keep routing to Driver 11, not Laxity.

---

## Track 2 — Fidelity (P0 unless noted)

### R5. Blackbird E3c(a): the remaining 40 unarmed retriggers — P0 · M · **Opus** (design)
**Evidence**: `bin/build_blackbird_native_song.py:96` names the "one-command-byte-per-row"
collision; the gate sites are at `:2929` (measured collisions per file — "common, not an edge
case"), `:3027` (one command slot, two signals), `:3100`. `RESTART_ARM_FX = 63` at `:94`.
Glyptodont register note-ons 122/162 armed ✻; the missing 40 are single-tick steps whose only
row already carries a genuine fx change.
**Fix sketch** (options from ROADMAP E3c(a), unevaluated): a second sentinel in an unused
instrument-column value; widening the row format (**risky** — the real SF2II parser shaped
B25's whole design); splitting the step so the sentinel gets its own row (costs sequence
space and shifts timing). An Opus session should prototype all three against the real
editor's parser before committing.
**Verification**: register note-on count **and** `audio-tightness.bat` (the register % barely
moves even when the audible fix is large — the reason this defect survived to B25 ✻); full
16-file sweep `py -3 pyscript/blackbird_sweep.py <label> --compare` with zero regressions;
SF2II play-test via `probe_once()` (after R23).
**Traps**: dedup/verify against the *simulator* is one inference step from the SID —
spot-check one file against a raw zig64 trace too.

### R6. Galway + ROMUZAK `fp_dec` `cmp #$90` — filter ADD rows run as SET in the real editor — P0 · S per driver · Sonnet
**Evidence** (measured): `pyscript/test_sf2ii_emulator_hazards.py:57-58` allowlists
`galway_driver.asm:cmp #$90` and `romuzak_driver.asm:cmp #$90` as "genuine, still-unfixed".
Mechanism (ROADMAP E3d): SF2II's CMP carry is wrong for |A−op|>$7F; ADD rows carry byte0 in
[$00,$0F], >128 below $90 → **every filter ADD row executes as a SET row in the editor**.
Blackbird had the identical bug and fixed it (B24, `cmp #$80` + build-time asserts ✻).
**Fix sketch**: port Blackbird's split-on-high-bit dispatch to both drivers; remove the two
allowlist entries. If R1 lands first, this becomes one fix in the common driver.
**Verification**: offline fidelity must be **byte-identical** (the change is a no-op under
correct 6502) — so the offline gate proves non-regression only. The actual fix is verifiable
only in-editor: `bin/sf2ii_vs_real.py` on a filter-sweep tune per driver (needs the
instrumented `SIDFactoryII_dbg.exe`, see `bin/sf2ii_vs_real.py:24`), or minimally the lint
going green plus an ear check via `pyscript/sf2_open_in_editor.py`.
**Traps**: this class is invisible to py65/zig64/Python-sim — do not claim it fixed from
headless numbers.

### R7. Galway pulse-PWM extraction gap — P0 · M · Opus
**Evidence** ✻: the one *shared* residual behind 10/40 not-objectively-clean: real PW sweeps
extracted flat for Commando / Street_Hawk / Match_Day / Highlander (ROADMAP B2).
**Fix sketch**: emit `0X`-add pulse rows from the trace's PW deltas (the 16-bit pulse pointer
/ 573-row PWM machinery already exists in the Galway driver ✻).
**Verification**: `bin/sf2ii_vs_real.py` per-voice pulse % on the four tunes; corpus
`bin/batch_validate_galway.py` no regressions.

### R8. Hubbard V2: model the pulse engine; finish the laggard classes — P0/P2 · M-L · Opus
**Evidence** ✻: Delta's "pulse 100%" is **captured, not modelled** (`hp_engine=0` — replays a
stream captured from the original's trace; a round-trip result). Swallow-class state-region
relocation, spin-class, and note-format laggards open ([players/HUBBARD.md](players/HUBBARD.md),
ACCURACY_MATRIX row). The wf 85–97 residual is pure ±1-frame skew (skew-tolerant reads 100 ✻)
— a scoring-presentation item, not an engine item.
**Fix sketch**: reverse the V2 pulse program format (V1's per-instrument engine is already
modelled, `hp_engine=1` — start from its extractor); then the swallow-class relocation.
Consider quoting skew-tolerant wf alongside strict in `bin/hubbard_validate.py` output.
**Verification**: `bin/hubbard_validate.py` per register; the modelled engine must match the
*original's* output (as V1 does), not merely replay the capture.

### R9. SDI Stage B + de-risk the fitted timing models — P0 · L · Opus
**Evidence** ✻: 274/324 Stage A files ship **some default instrument data** ("0 failures" =
emitted, not fidelity); only variants A and D are unfitted — C/E/DELTA/V pick a timing model
best-of-N against the reference, which is a falsification risk the matrix itself flags.
Native Stage B proven on 2 files ✻ ([players/SDI.md](players/SDI.md)).
**Fix sketch**: (1) extend the native Stage B beachhead per SDI.md's plan (after R1–R3 the
driver side is nearly free); (2) for each fitted variant, hold out files: fit the timing
model on half the bucket, score the other half — a model that only wins in-sample is a
measurement artifact.
**Verification**: the existing 324-file sweep, strict medians per variant, zero regressions;
run `sidm2-fidelity-falsify` on any new headline (but verify its output — it has produced
one false finding ✻).

### R10. Matt Gray: Stage B synth engine; Deliverance/Quedex locate — P0 · L · **Opus** (RE)
**Evidence**: Stage A knowingly omits slide/arp/PWM/drums — output "will NOT sound like the
original" (CLAUDE.md row; `whats-next.md`). Deliverance: shim found, track-pointer locate
fails (the 6-consecutive-`LDA abs,y` signature doesn't hold in the 1990 build); Quedex has no
shim at all — needs a second entry-point strategy (`sidm2/mattgray_parser.py`
`_find_play_voice` raises without it ✻). Also outstanding: LN2/Tusker Stage A never
play-tested; full pytest suite not re-run since `eae7325` ✻.
**Fix sketch**: follow the step list already written in `whats-next.md` (work_remaining §1–2)
— it is current and detailed. Stage B: the instrument field map is complete in
[players/MATTGRAY.md](players/MATTGRAY.md); the engine is his own from-scratch design, so
expect per-game refinement.
**Verification**: `py -3 bin/mattgray_validate.py <sid> --subtune N --frames 6000` — **do not
trust a parse that merely succeeds** (the first LN2 decode looked sensible and scored 11–22%
pitch ✻). Keep the plain/modulated split — the modulated bucket cannot falsify the timing
model (vacuous-100 class).
**Traps**: siddump's default display hides same-value re-triggers — the validator's
`-w/--written` flag is load-bearing, do not remove ✻. PSID `load=0`; Tusker's blobs relocate
under KERNAL ROM.

### R11. Mainstream MoN/Tel: finish validator calibration; open the 85-file bucket — P0 · M · Opus
**Evidence** ✻: Monitor_Madness_2 and Trying_Out_2 sit below their theoretical max because
`bin/mon_validate.py`'s brute-force offset search finds a locally-good, not optimal, offset;
the 85-file no-copy bucket is untouched (CLAUDE.md row; `memory/mainstream-mon-tel.md`).
**Fix sketch**: widen the joint search (offset × per-voice leading-artifact drop) or make it
exhaustive over the plausible range; then apply the existing B1-indirect machinery to the
no-copy bucket.
**Verification**: verify against the FULL bucket **and** the 5-check byte-exact gate
(Hawkeye/Cybernoid must stay byte-exact) — one earlier round regressed Cybernoid sub1
mid-session before being caught ✻.

### R12. Deenen: 9/19 unlocated; Astro residual — P0 · M · Opus
**Evidence** ✻: 10/19 located; Astro 77.4/91.5 ([players/DEENEN.md](players/DEENEN.md)).
**Fix sketch**: extend the locator per DEENEN.md; keep the builder's refuse-implausible-decode
behavior. **Verification**: `bin/deenen_sf2_validate.py` per-voice audio validator; the 7
clean wins must stay at their scores.

### R13. Future Composer Stage B — P0 · M · Sonnet after R1–R3 (else Opus)
**Evidence** ✻: the only ported player with no native driver (Stage A, $1800 variant = 5/20
files). ROADMAP B4 flags it as the cheapest Stage B and **the first test that the
consolidated pipeline generalizes** — sequence it right after R1–R3 as their validation.
**Verification**: `bin/fc_validate.py` onsets; per-frame fidelity vs zig64.

### R14. DMC: standard measurement window + measure parts ≥2 — P2 · S-M · Sonnet
**Evidence** ✻: "every DMC % is window-dependent and the window is a free parameter"
(Thunder_Force part01: 100/89/95 @6 s vs 44/38/39 @20 s); Rockbuster's number is part 1 of
16 — "the tool always compares from frame 0", so parts 2–16 have **no measurement**
(ACCURACY_MATRIX row).
**Fix sketch**: give the DMC validator a canonical window (full part length, as the Balloon
400 s number does) and a `--part N` mode that fast-forwards the original to part N's start
frame before comparing; report per-part scores in the sweep.
**Verification**: re-derive Balloon's 100×3 (should reproduce ✻); publish per-part Rockbuster.
**Traps**: window-dependence is *the* DMC trap — never quote a % without its window.

### R15. Laxity NP21: name the 0.07% — P2 · S · Sonnet (investigation)
**Evidence**: the flagship path is "99.93–100%" (ACCURACY_MATRIX quick reference) and no doc
names the residual mechanism. **Fix sketch**: run the trace comparison on a 99.93% file,
classify the mismatching frames (which register, which musical event), and either fix or
document the mechanism. A named residual is fine; an unexplained one is a small standing risk.
**Verification**: `scripts/validate_sid_accuracy.py` / trace-compare on 2–3 corpus files.

### R16. Filter-state carry across window seams — P0/P1 · M · Opus
**Evidence** ✻: part-boundary filter restarts cost ~25% filter fidelity on windowed tunes
(Hawkeye sub0 13 parts, filter ~75% at seams — ACCURACY_MATRIX; ROADMAP C4; Myth sub0 part1
filter 77%).
**Fix sketch**: when emitting part N+1's first filter program, seed it with the filter
engine's state (envelope phase, current cutoff) at the cut frame instead of restarting from
the program head.
**Verification**: `bin/mon_part_fidelity.py` filter % on Hawkeye sub0 / Myth sub0 seam parts;
non-seam parts must not move.

---

## Track 3 — Part-count / files-per-song (P1; lossless only — user standing rule)

### R17. Stage C structural synth-table RE — P1 · L · **Opus** (flagship)
**Evidence** ✻: the quantified Supremacy conclusion (PLAYBOOK §3): dense tunes blow
bundles+instruments+wave-rows **simultaneously**; no trace-based method compresses the
player's unrolled looping tables losslessly. The structural path collapses 87 instruments →
~5 and 178 bundles → ~16 arp programs, byte-exact from ROM; Supremacy's engines are cracked
and the arp parser committed ✻. Targets: Supremacy sub2 70 parts → single digits; Myth sub0
7 → 1–2; then evaluate for DMC/SDI bundle-bound files.
**Fix sketch**: per ROADMAP C1 / `whats-next.md`-era scoping: emit the player's own compact
looping arp/wave tables + selectors as SF2 looping programs instead of trace-unrolled rows.
**Verification**: byte-exact register match must be **preserved** (the tables come from the
player's own ROM data — any mismatch means the selector model is wrong, not an acceptable
loss); part count is the success metric only after byte-exactness holds.

### R18. Port the wave-RLE win as a feature flag — P1 · S after R1 · Sonnet
**Evidence** ✻: MoN's RLE wave rows (col1 = frame count) cut Cybernoid 18 → 11 parts,
proven byte-identical (ROADMAP C2). Blackbird's driver has its own RLE variant already.
**Fix sketch**: after R1, `FEAT_WAVE_RLE` becomes available to Galway/ROMUZAK/others;
evaluate on any wave-row-bound tune. **Verification**: byte-identical registers, lower part
count, per-player sweep.

### R19. Cross-part program dedup — P1 · M · Sonnet
**Evidence** ✻: windowed parts rebuild programs per window; identical programs recur across
parts (ROADMAP C3). Won't reduce part *count* (caps are per file) but shrinks each file and
stabilizes seams — and it is a prerequisite for honest seam-state work (R16).
**Verification**: byte-diff of emitted registers per part; file sizes strictly ≤ before.

### R20. Memory-wall audit for time-split parts — P1 · M · Sonnet (measurement) then Opus (layout)
**Evidence** (measured): Matt Gray splits purely on time — `bin/mattgray_to_sf2.py:42`
`MAX_PART_FRAMES = 24_000`, with the comment at `:187` citing the SF2II memory wall; Driller
uses **41 of 120 sequences** ✻ and still becomes 2 files. The wall is doc'd as "tables <
$D000 ≈ 27,650 play-calls ≈ 9.2 min" (PLAYBOOK §3), yet the Stage A path splits at 24,000
frames — a conservative default nobody has audited. Long-song splitting (Driller 11:05,
Balloon 400 s) is a **different problem** from cap-bound splitting (Supremacy) and may be much
cheaper to improve.
**Fix sketch**: (1) instrument one long Stage A build and one native build: dump the actual
end-of-tables address vs $D000 — how much slack exists, and what consumes the space
(sequence events? orderlists? padding?); (2) raise `MAX_PART_FRAMES` to the measured bound
per song rather than a global constant (the emitter knows its own table sizes — make the
split adaptive like the native builders' `fits()` probe); (3) lossless sequence-side wins:
transpose-reuse of repeated patterns (`TRANSPOSE=0xA0` exists in the format) and orderlist
compression reduce events per part, moving the wall further out in *time*.
**Verification**: rebuilt Driller must round-trip byte-exact sequences (the existing
6000/6000 check ✻) and pass the SF2II play-test at full duration; the 960-event and 120-seq
caps must still be respected per part.
**Traps**: the 1024-event `Unpack` heap-corruption hazard (R2) — adaptive splitting must
still honor `_SEQ_EVENT_LIMIT`; a part that loads but corrupts the heap can pass a short
play-test.

---

## Track 4 — Measurement & verification infrastructure (P2)

### R21. Make every headline reproducible — Sound Monitor first — P2 · S · Sonnet
**Evidence** (measured): `bin/_opt_sweep_corpus.py` exists on disk but is **untracked** (git
confirms); ACCURACY_MATRIX states SM's 99.23% "is produced by untracked scratch tooling and
no tracked test asserts it: not reproducible from a fresh clone". The only tracked corpus
sweep is `pyscript/blackbird_sweep.py` (+ `test_blackbird_sweep.py`).
**Fix sketch**: promote `_opt_sweep_corpus.py` → `pyscript/soundmonitor_sweep.py` using
`blackbird_sweep.py` as the structural template (label + `--compare` + a test asserting the
headline); then do the same audit for Hubbard (`bin/hubbard_build_all.py`), DMC
(`bin/dmc_build_all.py` ✻), SDI, Deenen — anything whose matrix row quotes a corpus number.
**Verification**: fresh-clone run reproduces the matrix number to the digit; add the sweep to
the test suite (skip cleanly without the corpus, per the `HVSC_ROOT` pattern ✻).
**Traps**: restore Dance part01 to the sweep (its omission understates the headline ✻).

### R22. Universalize the objective SF2II metric — P2 · M · Sonnet
**Evidence** (measured): `bin/sf2ii_vs_real.py:22` imports `sidm2.galway_trace_extract` —
still Galway-coupled; `:24` hardcodes a user-specific `DBG_SRC` path. It is the metric that
exposed the Galway "37 faithful → 30/40" overstatement ✻ and the only automated check that
sees SF2II-only behavior (R6's whole bug class).
**Fix sketch**: replace the galway_trace dependency with `fidelity_common`'s player-agnostic
trace helpers; make `DBG` location/config a documented setting; gate every player's ✅ claim
on it (ROADMAP B3).
**Verification**: reproduce a known Galway result, then run one MoN and one Blackbird build
through it.

### R23. Fix the `probe_once()` crash oracle — P2 · S · Sonnet
**Evidence** (measured): `pyscript/blackbird_crash_probe.py:206-217` — `alive =
_is_alive(pid)` then `return "SURVIVED" if alive else "CRASHED"`: a user closing the window
during a long trial is indistinguishable from a crash (a 492 s Driller trial was voided this
way ✻). The probe is player-agnostic and used by Blackbird and Matt Gray play-tests.
**Fix sketch**: record the process **exit code** (clean close ≠ crash) and take periodic
screenshots during the window, not only at the end (both proposed in `whats-next.md`).
**Verification**: unit tests in `pyscript/test_blackbird_crash_probe.py`; simulate a clean
close and assert it is not reported as CRASHED.

### R24. Universal trace-first fallback (D1) — P2 · L · **Opus**
**Evidence** ✻: `build_native_song` already accepts external traces (Myth's shim proved it);
Galway's gate/legato note extractor is player-agnostic (ROADMAP D1). This is the mission's
biggest lever: any unknown SID → trace → note extraction → native build at ~95–100%
per-register fidelity, with per-player RE becoming an *upgrade*, not a prerequisite.
**Fix sketch**: per ROADMAP D1; ship as the "unknown player" fallback above Driver 11 in the
registry (pairs with R4). Sequence after R1–R3 so it targets the common driver.
**Verification**: run it on 3–5 players that were *never* RE'd, measure per-register
fidelity vs zig64; must refuse loudly when the trace fails (fail-closed, per the zig64-gate
lesson: an equality check over evidence must first assert the evidence exists ✻).

### R25. Audio-domain verification track (E1/E2/E4) — P2 · M · Sonnet
**Evidence** ✻: ROADMAP E — VICE exposes no per-voice mute (E1: patch the local WinVICE,
reusing the `siddetector` build); SidWiz/Corrscope oscilloscope video blocked on E1 + ffmpeg
(E2); `audio-tightness.bat` detector defaults are provisional (E4).
**Why it matters**: B25 shipped a register-exact improvement that did **not** fix the audible
problem — the E track exists because ears caught what the register metric couldn't ✻.
**Verification**: E1 gate — cross-check patched-VICE per-voice render against SID2WAV `-m`
on a file both can handle (e.g. `SID/Angular.sid`) before trusting it ✻.

### R26. Signature-scan framework + RE toolkit promotion (D2/D4) — P2 · M · Sonnet
**Evidence** ✻: every port hand-rolls relocation-safe signatures (now ~12 locators:
`sidm2/*_detector.py` families, `mattgray_parser.locate()`, `locate_blackbird`, MoN/SDI/DMC
locators); the scratch RE tools (`bin/_mon_disasm.py` write-PC probes, `_mon_cpu_diff.py`
lockstep diff that found the siddump SBC bug ✻) get recreated each session.
**Fix sketch**: ROADMAP D2 (small pattern DSL + self-modified-pointer resolution +
per-file confirmation reports) and D4 (`bin/re_toolkit/` + a short guide).
**Verification**: re-express one existing locator (e.g. DRAX) in the DSL and confirm
identical results on its corpus.

---

## Track 5 — Hygiene & docs (P3)

### R27. `bin/` archive sweep + production index — P3 · S · Sonnet
**Evidence** (measured): `bin/` holds **2,360 files, 2,284 of them `_`-prefixed scratch**
(up from ROADMAP's ~2,200). **Fix sketch**: archive per the archive-before-explain protocol
(explain every batch before moving ✻); write `bin/README.md` naming the production entry
points per player (the ACCURACY_MATRIX "Entry point" column is the seed list). Run
`update-inventory.bat` after.
**Traps**: several "scratch" files are load-bearing (`bin/_opt_sweep_corpus.py` is the SM
headline source — R21 must land first or move it in the same change).

### R28. Doc drift — P3 · S · Sonnet
**Evidence** (measured):
- `docs/reference/ACCURACY_MATRIX.md` (v3.22.0, "all 12 ported players") has **no Matt Gray
  row**, while CLAUDE.md's Known Limitations table does — the matrix is the self-declared
  source of truth and is behind.
- `drivers_src/mon/romuzak_driver.asm` still misnamed with CRLF endings (moot after R1;
  rename now if R1 is deferred).
- ROADMAP A3 is done but A-track intro still says "the Stage-B path … carries ~3,200
  redundant lines" without noting the 4th (Blackbird) copy.
**Fix sketch**: add the Matt Gray matrix row (Stage A, sequencer 100%/100% plain-instrument
scope, timbre-not-claimed caveat — copy the honest framing from `whats-next.md`); consider
running the `audit-docs` skill for a full pass.

### R29. Outstanding test/validation debt — P3 · S · Sonnet
**Evidence** ✻ (`whats-next.md` current_state): full suite last green at `eae7325` (1,693
passed) — **not re-run** after the LN2/Tusker/trampoline commits; LN2/Tusker Stage A SF2s
never play-tested in SF2II.
**Fix sketch**: `py -3 -m pytest pyscript/ -q`; play-test one LN2 and one Tusker SF2 via
`probe_once()` (after R23 to make long trials trustworthy).

### R30. Broad-except audit on extract/rewrite paths — P3 · S · Sonnet
**Evidence** (measured): 27 `except`/`except Exception:` sites across `sidm2/` (top:
`sf2_editor_automation.py` 7 — UI code, acceptable; `report_generator.py` 3;
`np21_edit_area_builder.py` 3; `sf2_writer.py`, `laxity_raw_np21_builder.py`,
`galway_driver11_emitter.py` 1 each). The F3 lesson: a bare except around an extract+rewrite
block swallowed a `NameError` for 9 releases ✻.
**Fix sketch**: review only the sites inside extract/rewrite/build paths (writer, builders,
emitter); narrow to specific exceptions or log-and-reraise. Leave UI/automation sites alone.
**Verification**: full test suite; one Laxity corpus conversion smoke test.

---

## Explicit non-goals

- **Trace-replay cycle floor** (~0.17 VICE spectral distance on high-resonance voices) —
  fundamental; write-order reproduction does not close it. Do not chase ✻.
- **Lossy size reduction** of any kind — violates the standing user rule.
- ROADMAP items already ✅ (A3 fidelity_common, E3, E3b, E3c(c), Blackbird E4/E5/E6) — not
  re-opened here.

## ROADMAP cross-reference

| ROADMAP item | Status here |
|---|---|
| A1 driver unification | carried → **R1** (grew: 4 copies now) |
| A2 build lib + caps | carried → **R2, R3** (grew: 7 `fits()` copies) |
| A3 fidelity_common | ✅ done, not re-opened |
| A4 registry wiring | carried → **R4** (grew: 11 players unwired) |
| A5 bin/ hygiene | carried → **R27** (grew: 2,284 scratch files) |
| B1 MoN structural rebuild | merged into **R17** (same work as C1) |
| B2 Galway residual | carried → **R7** |
| B3 universal objective metric | carried → **R22** |
| B4 FC Stage B | carried → **R13** |
| B5 small residuals | noted in R16 (Myth filter); ROMUZAK drum octave stays parked |
| C1 structural RE | carried → **R17** (flagship) |
| C2 wave-RLE port | carried → **R18** |
| C3 cross-part dedup | carried → **R19** |
| C4 filter seams | carried → **R16** |
| D1 trace-first fallback | carried → **R24** |
| D2 signature framework | carried → **R26** |
| D3 Hubbard kickoff | superseded — Hubbard V1/V2 shipped; remainder → **R8** |
| D4 RE toolkit | carried → **R26** |
| E1/E2/E4 audio infra | carried → **R25** |
| E3c(a) retrigger signal | carried → **R5** |
| E3d fp_dec hazard | carried → **R6** |

## Suggested execution order (dependency-aware)

| Wave | Items | Rationale |
|------|-------|-----------|
| 1 | **R6** (fp_dec), **R23** (probe oracle), **R21** (SM sweep), **R29** (test debt), **R28** (doc drift) | Small, independent, de-risk everything after; R6 is a today-broken editor behavior |
| 2 | **R2** (caps) → **R3** (build lib) → **R1** (driver merge) | Consolidation in increasing risk order; each gated by byte-diffs |
| 3 | **R13** (FC Stage B) | Validates wave 2's consolidation on a real port |
| 4 | **R5** (Blackbird retriggers), **R16** (filter seams), **R7** (Galway PWM) | P0 fidelity on the consolidated base |
| 5 | **R20** (memory-wall audit), **R18** (RLE flag), **R19** (dedup) | Part-count: cheap wins first |
| 6 | **R17** (Stage C structural RE) | Flagship part-count work, Opus |
| 7 | **R4** (registry) + **R24** (trace-first fallback) | Ship the pipeline: wire everything, add the universal fallback |
| 8 | **R8–R12, R14, R15** (per-player residuals), **R22, R25, R26** | Ongoing per-player + infra depth |

---

*Review conducted 2026-07-30, code-reading only, on branch `mattgray-driller-stage-a`.
Doc-claimed (not re-measured) numbers are marked ✻ throughout.*
