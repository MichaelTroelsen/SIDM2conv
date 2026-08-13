# The Technique Catalog — named patterns from eight player arcs

Companion to [PLAYBOOK.md](PLAYBOOK.md) (the *method*). This is the *pattern
library*: recurring player mechanisms, diagnostic techniques, and failure
classes, each named so the next arc can look them up instead of rediscovering
them. Every entry lists where it has already appeared — if your symptom
matches, read that arc's doc/memory before writing new code.

Sources: Laxity NP21, Galway, ROMUZAK, MoN (Jeroen Tel), Hubbard V1/V2, DMC
(Bjerregaard), Sound Monitor (Hülsbeck), SDI (Gallefoss/Tjelta) + the NP21
clusters. *Created 2026-07-12 (v3.19.0 era).*

---

## Part I — Player mechanisms (what the 6502 is actually doing)

### P1. The pitch-carrying instrument
**The single most-rediscovered pattern (5 independent finds).** The sequence's
note byte is NOT the heard pitch: the instrument's wave/synth program carries
a semitone offset (melodic) or an absolute semitone (drums), applied per frame.
Sequences can play a *constant* note while the music moves.

- **Symptom:** windowed pitch score ≫ strict score; onset deltas **constant
  per instrument** (see D1).
- **Where the pitch lives — differs per player, get this right:**
  - SDI A: wfprg **row 1** arg (row 0 = the `($01,0)` init/test row).
  - SDI D: the walk's **resting row** (3-byte rows; `$FE` parks on the last
    row — the onset frame itself carries the raw note, attack rows spike past).
  - SDI E: wfprg **row 0**, applied to the SID **on the note-on frame** by the
    set-instrument tail (`lda f-1,y / bmi / adc note,x`).
  - SDI V: instrument **octave nibble** (freq word doubled `oct-1` times =
    `+12*(oct-1)` semis) + per-note instrument in the row's fx byte.
  - DMC: the wavetable byte `$80|note` = absolute semitone (the freq-table row
    IS the wavetable value).
  - Galway: chord arps inside the driver-internal FM (ported to editable wave
    programs, `GALWAY_ARP_WAVE`).
- **Trap:** applying the offset at the wrong walk phase **regresses** files
  whose onset frame is clean (SDI C: Bahbar 94.3→81.4). When sub-classes
  disagree, gate the application until the walk phase is settled by emulation.

### P2. Tie vs retrigger (gate semantics)
Every player distinguishes "new note" from "pitch change under a held gate",
and every wrong guess costs a debugging day.
- Hubbard V1: no-release (bit5) chains are **ties**, not retriggers (the
  2-frame bass chop bug). MoN: `$FB` = tie flag (was decoded as 27-tick rest —
  a whole-subtune desync). SDI E: note bit7 **SET = tie** (the draft had it
  inverted; every calibration scored 0 until flipped). Galway Wizball: fully
  legato voices — gate-based note detection collapses to ~2 notes/voice.
- **Runtime Driver 11 cannot parse `$90-$9F` tie bytes** (editor-only feature;
  emitting them desyncs playback — Sound Monitor lesson, locked by test).
- **Validation note:** ties produce no gate rise, so onset validators skip
  them; but Stage A/B must model them (re-gate in cut 1, exact legato in B).

### P3. The wrapper / self-installed-IRQ class (`play=$0000`)
The rip's INIT installs its own raster/CIA handler (vector at `$0314` or
`$FFFE`), never RTSes (CLI + `JMP *` spin), and PSID `play=0`.
- Seen: 6 Galway tunes (Arkanoid, Game Over…), SDI variant V (the `VE-2x/4x`
  files — the wrapper drives a 3-JMP module 2x/4x per frame).
- **Handling:** bounded init emulation — run until the vector installs or the
  PC hits a JMP-to-self; derive the handler; the multiplier is usually a
  literal compare in the wrapper (`LDA counter / CMP #$02`). zig64 has the
  full path (simulated IRQ per frame); py65 suffices for locate-only.
- Often the module + data are **in-file** and only scratch state is
  runtime-built — check before building an emulation pipeline (SDI V needed
  none).

### P4. Multispeed (Nx play calls per video frame)
Filename hints (`_VE-4x`, `2x`), CIA-timer speed bits, or wrapper counters.
The decoder's tick domain is *play calls*; the trace's frame domain is *video
frames* — divide, don't guess. DMC multispeed variants gate the within-frame
onset default (P5). A 1x decoder against a 4x file scores ~0 on both metrics.

### P5. Within-frame retriggers (gate OFF+ON in one play call)
A state scan that samples the gate once per frame is **blind** to a retrigger
completing inside a single call (DMC: 24/88 files; Balloon wf 0→100 after the
fix). Capture gate *events* (every `$D404` write), not end-of-frame state.

### P6. Feature-flag assembly (one source, many binaries)
The editor assembles the player per song with features compiled in/out (SDI's
`rem@` flags; the 2.1 source explains the rip clusters). Consequences: byte
signatures must **wildcard across the optional blocks**, addresses shift per
song, and "the same variant" can have structurally different code paths.
Locate by *idiom* (short, distinctive instruction runs), never by offset.

### P7. Column-major zN instrument tables
Instruments as parallel byte *columns* indexed by sound#, not row-major
records (SDI z0-z9, Stinsen `$1808/$181C`, SDI V stride-31 columns). The read
site tells you the layout: `LDA table,Y` with Y = sound# = column-major;
`LDA table,Y` with Y = instr*stride = row-major records. Confirm the stride
before claiming a format (the DRAX v3.5.67→68 mislabel).

### P8. The state-block engine
Per-voice state as fixed-size blocks (`$0400+v*$40`, X = 0/$40/$80) instead of
parallel arrays (X = voice). Signature: `LDA/STA $04xx,X` with block-stride X
setup at init. Track position, row counters, transpose all live at fixed
block offsets — decode needs the offsets, not the addresses.

### P9. Track-conductor with independent row stream (tracker class)
SDI V: the track entry runs for `length_tbl[seq#]` **ticks** and advances on
expiry — *independent* of the row stream inside the seq (rows just keep a
countdown). Sequence overrun/underrun is normal, not a decode bug. Contrast
with the A-D class where the seq's END byte drives the track.

---

## Part II — Diagnostic techniques (how to find the above)

### D1. The delta histogram (the pitch-class detector)
For every real onset (gate rise in siddump), find our nearest decoded note
(±4 frames) and record `freq_to_semi(real) − freq_to_semi(ours)` at samples
`fr+{0,2,3,5}`. Read the histogram:
- **Constant per instrument** → pitch carrier (P1). Port it.
- **Huge at fr+0, settling to a constant** → attack rows spiking past; the
  sustained pitch = a later walk row (SDI D's resting row).
- **Scatter ±2..7** → glides/vibrato/arps mid-flight (extend the sample
  window to confirm: if strict rises with `fr+{8,12,16,20}`, it's slides).
- **Wrong stream entirely** (deltas look like a different melody) → false
  locate (D2) or voice-mapping error before anything else.

### D2. The false-locate zero
**A variant scoring 0.0 on BOTH metrics is a mis-locate until proven
otherwise.** Dump the extracted operands and check they point at sane file
offsets *before* touching the decoder. Paid for twice in one day (SDI V: the
"D" pattern matched a wrapper; identical operands across different songs =
matching invariant player code, not per-song data).

**The dormant-copy variant (does NOT score zero):** an image can embed a
SECOND, never-executed player copy whose patterns match and whose tables
point at the *same song data* — the decode then half-works (SDI
Tanks_3000: 64% windowed from the dormant `$25xx` copy while the live
player runs at `$1000`; the play vector was `JMP $1003`). Moderate
windowed + collapsed strict can be THIS, not a pitch carrier. Detector:
follow the init/play JMP chain and check the matched pattern's PC is
reachable from the live entry (a py65 PC-breakpoint that never fires =
dormant code).

### D3. Content-verified table location
Don't trust a lone byte pattern for data tables — verify the *content*: freq
tables = two abs,Y read targets exactly `$60` apart whose combined words
double per octave (`_freq_scan`); pulse tables = plausible PW ranges; track
pointer arrays = addresses inside the file. A pattern match with garbage
content is a false locate (D2).

### D4. Strict + windowed dual metrics, and vacuous acceptance
Always report BOTH: windowed (0..+37 semis, arp-tolerant) and strict
(delta==0). The gap *is* the pitch-carrier signal. And test every tolerance
against a known-bad case: the 0..37 window happily passed +2-semitone errors
for months; a `secs=0` fidelity window measured a silent SF2 as perfect
(Hubbard's vacuous-100 bug); an arp tolerance of `max(4, dur//8)` against 3
compared frames accepted garbage (SM drums).

**Two guards, not one — this was learned twice in one day (2026-08-07).**
`sidm2.fidelity_common` now carries both, because they answer different
questions and either alone leaves a hole:

- `score_pct(ok, tot)` → **None** when `tot == 0`. *Were there any frames?*
- `exercised(a, b)` → **False** when both series are the same single constant.
  *Did those frames carry any information?*

`score_pct` alone is not sufficient, and the reason is siddump-specific and
easy to miss: **siddump force-displays every register on its first row**
whether or not the playroutine wrote it. So a tune that never touches the
filter still yields a full-length, entirely non-`None` series of zeroes on
*both* sides — a nonzero denominator, `ok == tot`, and a confident 100.0 that
means only "neither side did anything". Measured twice after the "fix" was in:
Commando (Hubbard never writes a cutoff) reported `Filter Accuracy: 100.00%`
in `sidm2/accuracy.py`, and again through `sidm2/validation.py`. Both were
caught by *running the tool*, not by the tests.

`exercised` is deliberately two-sided: two *different* constants (a permanently
wrong `$D418`, say) stay in and score ~0%, so a register that is constantly
wrong cannot hide in `n/a` either.

The scale of the class: five separate copies of the same weighted-accuracy
scheme existed in this repo (`sidm2/accuracy.py`, `scripts/validate_sid_accuracy.py`,
`sidm2/validation.py`, `pyscript/trace_comparator.py`, and the heatmap
generator), each independently broken, one of them scoring **two identical
captures at 50%**. If you are writing a new scorer, route it through
`fidelity_common` instead. For a swept register, add the
phase-invariant companion in **D9** next to the strict number.

### D9. For a SWEPT register, per-frame equality is mostly a phase question
`pulse%` and `cutoff%` are scored as "same value on frame i". For a register
that *sweeps*, that question is dominated by alignment: a sweep with the right
rate, depth and direction that starts a few frames late disagrees on nearly
every frame. Live case (2026-08-08): `5_Title_Tunes_song0_part01` osc3 scored
**pulse 4.5%** — one unbroken 596-frame residual run, the signature of a dead
engine — and it is a **-3-frame offset**, 90.6% at that lag. The pulse engine
was right all along.

The per-voice delay refinement these tools already run does not catch it:
it aligns each voice by **freq** agreement, so a voice whose pulse writes sit
a few frames from its own freq writes stays misaligned in that column only.
The ±1-frame skew-tolerant column does not reach a multi-frame offset either. How
long this has been costing: `bin/_sm_measure_direct.py` exists *only* to work
around it ("mon_part_fidelity's freq-tuned per-voice delay misreports per-frame
pulse"), an entire duplicate scorer written instead of a companion metric.

Companion metric, phase-invariant because it is computed from consecutive
DIFFERENCES: `fidelity_common.shape_agreement(a, b)` → movement count (how
many times the value changed) and travel (sum of |delta|), each as
smaller/larger via `score_pct`. The 4.5% case reads **moves 279/279, travel
35712/35712** — identical motion, wrong phase.

**Necessary, not sufficient, and never quote it alone.** Equal totals do not
mean equal shapes (up-then-down and down-then-up travel identically), so it can
only say *the motion is the right size*. Print it BESIDE the strict number:
strict low + shape high = alignment; both low = the engine really is producing
different motion. Same D4 discipline applies — neither side moving is `0/0` →
**None**, never 100.0, because a flat pulse on both sides is not evidence the
pulse engine works. Not meaningful for `wf` (an enum) or `$D417`/`$D418`
(bitfields), where |difference| is not a distance.

### D5. Timing-model calibration by strict agreement
When the tempo conductor is unresolved (E's dual-row condition, V's global
tempo commands), select the tick→frame mapper **per file by strict
pitch+onset score** over a small candidate set (flat fpt 1-8 + extracted
tempo programs). Selecting by windowed onsets picks wrong mappers (Kirby
16.5→71.0 from calibration alone). This is calibration, not cheating: the
pitch comparison stays exact.

### D6. Flow-following disasm + raw-binary greps (use BOTH)
Linear disassembly derails on embedded data (state cells between routines).
Flow-following (worklist over branch/JMP/JSR targets) fixes that — but it
**misses paths behind unfollowed dispatch** (SDI V's per-note instrument at
`$1669`). Complement: grep the raw binary for *state-cell writes* (`9D 04 04`
= `STA $0404,X`) to enumerate every writer of a cell you care about.

### D7. Bounded init emulation
For wrapper/relocating players: py65-step INIT with (a) vector-change
detection, (b) JMP-to-self spin detection, (c) a step cap. Vectors often
install *before* the module init runs — stop on the spin, not the first
vector write (SDI V: stopping early left voices 1/2 unset). Myth: full
emulation extraction (intercept the freq lookup) when the player relocates.

### D8. Per-file confirmation before generalizing
Never generalize a table layout from one file (DRAX $1B8A: "wave table" →
actually 8-byte instrument records; two releases to unwind). Confirm the
record stride + one decoded field against a second file, then generalize.

---

## Part III — Infrastructure failure classes

### F1. The capture CPU poisons everything downstream
A byte-exact metric with audibly wrong sound = suspect the *capture* CPU, not
the driver (siddump SBC-carry bug broke 16-bit chains project-wide — the
Cybernoid vibrato defect). Fix in one place; every player inherits it.

### F2. Don't edit builder modules while a corpus runner is live
Corpus runners spawn subprocesses that re-import the module mid-run — a
half-edited file corrupts random builds (nearly lost Fun_Mix). Edit after the
run, or run the corpus after the edit.

### F3. Silent-caps and swallowed exceptions
A bare `except Exception` swallowed a `NameError` for nine releases while a
safety gate stayed bypassed (v3.5.63). Narrow excepts in extract+rewrite
blocks; if a build bounds coverage (top-N, truncation), log what was dropped.

### F4. Boundary/label artifacts masquerading as fidelity loss
Rounded-seconds part labels strict-collapsed grid-aligned parts (SM: a 58.66%
"regression" that was a *parsing* artifact); per-voice-delay metrics masked an
inter-voice desync that global-delay metrics caught immediately (Dance
part05). Label parts in exact frames; measure later parts with global delay.

### F5. The measurement tool is not deterministic (compare a file to ITSELF)
**Symptom**: scores that wander between runs of the same command, or a
suspicious floor of "extra"/"missing" events nobody can attribute.
**Detection**: the one-line test — run the comparison with the SAME file on
both sides. It must come back exact. `pyscript/audio_tightness_tool.py` scored
Commando against Commando at **148/157 onsets with 18 spurious extras**.
**Cause seen**: `sidplayfp`'s `--delay` (power-on delay) defaults to **random**
— documented only in `--help-debug` — shifting the whole render by a random
offset of up to ~8 ms, the same order as the millisecond onset deltas the tool
reports. Three renders of one file with identical arguments gave onset counts
152/159/156 and `rms(difference)/rms ~= 1.2`, i.e. two runs of the same file
differed as much as the signal itself. Pinning `--delay=0` gives 156/156/156
and `~0.0003`, and the self-comparison becomes exact.
**Rule**: a comparison tool owes you a **reflexive identity** — `f(x, x)` is a
perfect score, or the tool is measuring its own noise. Check it before
believing any number the tool produces, and pin every randomized knob in the
renderer/emulator (seed, power-on delay, RAM pattern) rather than averaging
over them. Related to D4: this is the *other* way a score can be meaningless —
D4 catches comparisons with no information in them, F5 catches comparisons
whose information is the tool's own jitter.
**Seen in**: sidplayfp (all audio paths, fixed 2026-08-08 in
`sidm2/sidplayfp_wrapper.py`, `power_on_delay=0` by default).

### F5b. `f(x, x)` is necessary but NOT sufficient — re-render, then compare
**Symptom**: a tool that passes the F5 check still gives a confident wrong
answer on two *different* binaries, and its verdict flips between runs.
**Detection**: F5 as usually run compares a WAV against **the same WAV**,
which is exact by construction and proves nothing about the pipeline that
produced it. The real test is `f(x, x')` where `x'` is **re-rendered** from
the same input, and then again with a knob perturbed that legitimately differs
between the two things you actually want to compare.
**Cause seen** (Cybernoid_II, 2026-08-08): the registers×audio cross-tab called
all three voices SYNTHESIS — registers exact, audio 71-85%. Neither term was a
driver defect:
- **Metric noise.** Two `--delay=0` renders of one file are the same signal to
  within `r = 1.0000`, `rms(diff)/rms ~ 0.001`. On the **full mix** the onset
  detector does not move (38/38, 100% across all six pairings). On a
  **voice-isolated** render that inaudible dither moves the onset count
  101/88/98 and the pairwise match rate across **84.2-96.9%** — muting two
  voices leaves a large population of onsets on the detector threshold.
- **Phase.** Free-running oscillator and noise-LFSR state differ because an
  original and a driver build reach their first play call through different
  init code. Perturbing the power-on delay on the ORIGINAL ALONE, note data
  untouched, spans the same band the driver was being blamed for.
**Rule**: before reading any cross-binary audio number, measure the floor the
file produces **against itself** — one plain re-render (metric noise) plus N
perturbed ones (phase) — and withhold the diagnosis inside it. Three further
rules fall out, all learned the hard way here:
1. "Driver is worse than all N self-samples" is a **rank test**: its
   false-positive rate is `1/(N+1)`. At N=3 a clean voice is condemned one run
   in four. Quote the p, and pick N from the claim you intend to make.
2. The floor is a **minimum over noisy point estimates**, so widen it by the
   replicate shortfall. Without that margin the verdict flipped between two
   runs of the identical command (85% vs a 77% floor, then 70% vs 71%).
3. A partition with no **inconclusive** outcome will always name a culprit.
   Add the cell before trusting any of the others.
**Seen in**: `pyscript/audio_tightness_tool.py` (`--repeat-floor`, default 9,
`measure_repeatability_floor`; tests in
`pyscript/test_audio_tightness_repeat_floor.py`).

### F6. The target driver's own startup frame (and reading a flag at rest)
**Symptom**: a Stage A transpile scores *below* its own parser, with the loss
concentrated in arpeggiated/fast-attack instruments, and the offset histogram
shows a **constant** `+1` frame — the same in every third of the song, no drift.
**Detection**: two-part. (a) An offset histogram, not a score: drift is a timing
bug, a constant offset is a **phase**. (b) Re-score with the phase removed
(`--lag 1`); if files land *exactly* on the parser's own number they were never
losses. HardTrack: `Zakplus` 87.6→99.0 = parser 99.0; `Hopscotch` 56.8→72.2 =
parser 72.2, while the two genuine losses did not move at all.
**Cause seen**: Driver 11 is a **command protocol**, not an init/play pair —
`$1000` leaves `$16CC = $00`, and the per-frame tick at `$1006` treats `$00` as
"clear and seed the state block, then arm `$80`, and play NO row". The first
tick after init is spent initialising, so every render starts one frame late.
This is the **target driver's** property, shared by every Stage A build that
targets it, not the builder's bug — three builder-side explanations (wrapper play
address, hard-restart flag, row layout) were falsified before it was found.
**The second trap** is how it was first explained: `$16CC` **is** `$40` in the
file at rest, and `BVS $1047` is right there in the dispatch — a self-consistent
story assembled from the binary **at rest**, published, and wrong. `init`
overwrites that byte before the first tick, and `$1047` is the *stop* path. A
flag's value on disk is not its value when the code reads it: **run it and print
the flag at the call**, don't infer the branch from a static byte.
**Rule**: don't patch the driver to remove its startup frame (Driver 11 would
never initialise) and don't widen the match window until it hides — a uniform
20 ms offset of a whole song is not a fidelity defect. Subtract the known phase
in the **validator**, and quote the lag next to the score.
**Seen in**: Driver 11 / every Stage A transpile in this repo
([DRIVER11.md](DRIVER11.md) has the dispatch and the affected builder list);
`pyscript/hardtrack_stagea_validate.py --lag`, pinned by
`pyscript/test_driver11_startup_frame.py`.

### F7. A fix in the BUILDER is not a fix in the CORPUS
**Symptom**: a player doc states a register at 100.00% byte-exact and the files
on disk disagree with it — because the doc is describing the builder and nobody
measured the artifacts. Found **three times in one session**, on three players,
each by a session that had fixed the code and never regenerated the output:

| player | builder fixed | shipped artifacts wrong |
|---|---|---|
| MoN | 2026-08-08 (`464406a`, where `passband_trace` was WRITTEN) | 8 of 19 |
| HardTrack | 2026-08-10 (`cffc51e`) | 21 of 33 |
| DMC | 2026-08-10 (same commit) | 26 of 57 |

**Detection**: a cheap check that reads the **artifact**, not the source —
siddump the shipped file and the original and compare the register directly
(`pyscript/passband_check.py`). Do **not** rebuild first: a sweep that
regenerates before measuring answers "is the builder right", which was never in
doubt, and reports the corpus healthy. Cross-checking the *code* across builders
is what missed it three times — HARDTRACK.md records "the same gap was then
checked across every native builder", and that audit read call sites.
**Why it hides**: the per-player fidelity scorers are structurally blind to the
register. HardTrack's builder "scores frequency and nothing else";
`bin/_dmc_fidelity.py` scores freq/wf/pulse. `$D418` is in neither, so no
headless number could move — `Balloon` re-measures **byte-identical** before and
after the fix. A scorer cannot report a register it does not read.
**Second trap — severity is not the same question as correctness.** Three DMC
files differed on `$D418` and were reported as failures three separate times;
all three have `$D417 = $00`, so **no voice is routed into the filter** and the
passband selects among silent outputs. Report the routed fraction beside the
mode match, or a true statement gets filed as a defect.
**Third trap — check the reference is alive.** The same tool applied to
Blackbird produced "16/16 pass", then "16 originals never route a voice", then
"our builds filter where the original does not" — all against `SID/LFT/*.sid`,
which siddump **cannot drive at all** (0 frames with any freq or waveform,
`$D418` = 0). An all-zero trace is byte-identical to "never filters" and to
"silent". See F1 and the `zig64` empty-vs-empty gate: **assert evidence exists
before comparing**.
**Rule**: when a fix lands in a shared builder, the artifacts it already
produced are now wrong, and nothing in this repo notices. Re-run the artifact
check, not the test suite.
**Seen in**: MoN, HardTrack, DMC ([MON.md](MON.md), [HARDTRACK.md](HARDTRACK.md),
[DMC.md](DMC.md)); `pyscript/passband_check.py`, pinned by
`pyscript/test_passband_check.py`.

---

## Adding an entry
One screenful max: symptom → detection → exploit/fix → players seen in.
If a technique is rediscovered in a new arc, add the sighting here *in the
same commit* as the fix.
