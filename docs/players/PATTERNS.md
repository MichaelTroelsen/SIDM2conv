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

### D10. Tolerance scoring separates a PHASE defect from a WRONG-CONTENT one
A strict per-frame column says *these frames disagree*. It cannot say **why**,
and the two causes need opposite fixes: a voice playing the right notes 2 frames
out of step scores identically to one playing different notes. Re-score the same
pair allowing the comparison to match any original frame within ±k, for k =
0, 2, 10, and read the SHAPE of the recovery:

- recovers at ±2 and gains **nothing** more at ±10 → **bounded per-note skew**.
  The content is exact; something is placing notes or starting captures late.
- keeps climbing through ±10 → a **wider or drifting** offset (D9's territory,
  or a tempo-model error).
- barely moves → genuinely **different content**. Tolerance cannot rescue it and
  no amount of alignment work will.

Unlike `shape_agreement` (D9) this works on `wf`, an enum where |difference| is
not a distance — which matters, because waveform is usually the column that
proves the content is right.

Live case (2026-08-15, DMC): the 49 sub-90 corpus voices had been bucketed as
"whole-build / pitch-only / mixed" from strict scores alone. Under tolerance,
**31 of the 49 are timing** — 24 recovered by ±2, 7 more by ±10 — and only 18
are content. `Roadblaster` v0 read `f58.6 w84.4 p62.5` strict and
`f96.9 w100.0 p100.0` at ±2 with a flat plateau to ±10; that plateau is what
identified F10 as a bounded ±2 capture-alignment bug rather than a decode
failure, and after the fix the strict score IS 96.9/100.0/100.0. Its v2 stayed
put (62.0 → 65.0 at ±10) and is a separate, still-open content defect — the same
file needed both diagnoses.

**Use it to classify, never to report.** A ±k score is not a fidelity number: it
credits agreement the listener does not get. Quote the strict column; quote the
tolerance column only beside it, and only to say which kind of defect is left.

**And the "content" bucket is an UPPER BOUND, not a verdict.** Tolerance can only
see offsets inside its own range, so a whole-timeline shift is indistinguishable
from wrong music — which is exactly what F11 produces. `Roadblaster` v2 moved
62.0 → 65.0 across ±10 and was classified content on that evidence; it was a
**491-frame** shift, and fixing F11 took it to 96.9/96.9 raw and **100.0/100.0/
100.0 audible** over n=6,265. Widening the tolerance is not the fix (at ±491 the
score means nothing); the check that *does* discriminate is the absolute onset
list — compare where each voice's first event lands, not how far apart the
frames are.

---

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

### F8. The artifact must record the window it was built for

**Symptom**: a scorer compares one part of a multi-part build against the
original and cannot say whether a mismatch is real, because past that part's end
our build LOOPS while the original plays on. The honest response is to refuse —
`passband_check` reported 41 builds UNCONFIRMED across two players — but a
refusal that needs a human to supply 41 numbers is a refusal that never gets
resolved. Those rows sat unestablished for two sessions.

**Detection**: the number was never unknown. Every native builder labels each
part `part N/M (A-Bs)` and **prints** it; nothing wrote it down. If a scorer is
asking a human for a figure the builder computed an hour earlier, the gap is
storage, not knowledge.

**Fix**: `emit_one` — the one emitter every native builder goes through — drops a
`.span` sidecar beside each artifact. Three properties earn their keep:

- **One-directional.** A recorded span may only NARROW the window, never widen it
  past `--seconds`. Over-run can only MANUFACTURE disagreement, so narrowing is
  safe in a way widening is not. (`window_for`, pinned.)
- **Absent ≠ zero.** No sidecar means the row stays UNCONFIRMED. An artifact
  built before the mechanism existed must not silently adopt a default.
- **It says so.** Rows measured over a derived window print `[Ns = its own part
  1]`, because a reader cannot otherwise tell which number they are looking at.

**Result on HardTrack**: 25 → **32 of 33**. Seven of the eight unconfirmed rows
were pure window artifacts — `Something_to_Eat` 68.7% → **100.0%** at its true
10 s, `Illmatic_end` 71.1% → **100.0%**, `Takisobie` 57.2% → **99.8%** — and the
eighth (`Fun_Factory`, 99.0%, 3 audible frames) is a real marginal difference
that the noise had been hiding.

⚠️ **The first run derived nothing, silently.** Half the players in `PLAYERS`
are keyed on the `.sid` PSID wrapper and half on the `.sf2`; the sidecar is
written beside the `.sf2`, so every HardTrack lookup missed and read as "no span
recorded" — indistinguishable from working correctly. A lookup that can fail
open needs a positive signal that it fired, which is what the `[Ns = its own
part 1]` marker became.

**Seen in**: HardTrack, SDI (`bin/build_mon_native_song.py` `_write_span`,
`pyscript/passband_check.py` `part_span`/`window_for`, pinned by
`pyscript/test_passband_check.py`).

---

### F9. A detector keyed on one register is blind to the same event in another

**Symptom**: a feature the original plainly performs is never reproduced, and
nothing upstream looks wrong — the sequencer is right, the capture is right, the
emitted program is right. The feature simply has no program attached.

**Detection**: dump the ORIGINAL's registers across the transition and ask which
one actually moved. `detect_filter_drives` finds filter-envelope restarts by
looking for a fast **cutoff** jump, because that is how almost every tune starts
one. `Juba-Jazz` starts its filter by writing `$D417` routing `00 -> $f4` and
`$D418` to LP+BP on a single note-on **while holding the cutoff at 0 for the
whole song**. The detector saw nothing, so no filter program was attached and the
build never left low-pass: 52.8% over 661 audible frames, the largest passband
defect in the corpus.

**Fix**: add the missing expression of the event — but make it **additive by
construction**, not by measurement. The first attempt triggered on any
`no-voice-routed -> some-voice-routed` transition, which 30 of 40 SDI, 29 of 40
HardTrack and 21 of 40 DMC files have; far too wide for a detector shared by
every player on this driver. The shipped version runs as a SECOND pass and only
credits an enable when the cutoff pass found nothing within ±4 frames, so a file
whose enables already coincide with a cutoff jump cannot change.

**Verify on the neighbours, not the target.** HardTrack: 31 of 33 builds
byte-identical; the 2 that moved bytes measure identically on passband AND on
freq/wf/pulse under an A/B against the previous builder. SDI: 12 sampled passing
files still pass, 13/13 with the target.

**Seen in**: SDI (`Juba-Jazz`), `bin/build_mon_native_song.py`
`detect_filter_drives`.

### F10. A "find the nearest X" search that returns the FIRST match
**Symptom**: purely ADDITIVE errors. Every event the original has is reproduced
at the right frame — nothing is missing, nothing is late — and yet the strict
columns are 40-60%, because extra events appear that the original does not have.
A whole-voice diagnosis ("the decode is wrong") follows, and it is wrong.

**Detection**: compute the event list from ONE source on both sides (gate rises
from `siddump_per_frame`'s `wf & 1`, not a helper whose frame numbering may
differ by one — two helpers here disagree by +1 and that cost an hour), then
split the comparison into *matched / ours-only / theirs-only*. `Roadblaster` v0:
**352 of 352 matched at delta 0, 0 missing, 93 spurious** — and the file has
exactly 93 two-frame notes. A 1:1 count against a structural feature of the
input is the tell; nothing about a genuine decode failure lands on a round
count.

**Fix**: `_snap_onset` snaps each note's capture onset to the real gate rise
within `fr-2 .. fr+3`, and scanned that window **left to right, returning the
first rise**. Whenever the previous note was ≤2 frames long, *its* rise sat at
`fr-2` and won: the capture began 2 frames early, replayed 2 frames of the
previous instrument, and the driver hard-restarted on top — one extra gate rise
per short note. Order the window by distance from `fr` instead. Ties break
**backward**, because the window exists for Hubbard, whose grid frame lands one
frame LATE. `SNAP_FIRST=1` restores the old order for an A/B.
`Roadblaster` v0 (n=15,996): **58.6/84.4/62.5 → 96.9/100.0/100.0**.

The general shape: any "search a window, take the first hit" is a *nearest*
query written as a *scan*. It is correct exactly while the window holds one
candidate, so it survives every test built from well-separated events and fails
only where the input gets dense — which is where the interesting music is.

**Verify on the neighbours, not the target.** `snap_gate` is opt-in and six
shims set it (DMC, Future Composer, HardTrack, Hubbard, SDI, Sound Monitor);
Matt Gray measured it OFF. Built both ways with `SNAP_FIRST`, the change is
**byte-neutral on every neighbour sampled**: HardTrack 33/33, SDI 41/41, Sound
Monitor 13/13, Future Composer 7/7, Hubbard 2/2 parts identical. Sound Monitor's
tracked corpus sweep was run as a full `SNAP_FIRST=1` A/B anyway and reads
**99.252 -> 99.252 (+0.000)** — 0 improved, 0 regressed, 0 part-moves, all 11
songs identical to the decimal, with the baseline reproducing the published
figure exactly, which is what makes a null result mean anything. Pinned in
`pyscript/test_snap_onset.py`, including the old order via the A/B switch so the
regression is asserted from both sides.

**A byte-diff against the SHIPPED artifact is not this A/B, and it lies in the
alarming direction.** The first pass diffed a rebuild against whatever `.sf2`
was on disk and reported Future Composer 0/12 identical and Sound Monitor 11/15
— both entirely artifacts of when those files were last built (FC's dated
2026-07-30). Every one of them is identical under the real control. That is
**F7 inside the verification harness**: the baseline is the same code with the
change switched off, built now — never the corpus you happen to be shipping.

**Seen in**: DMC (`Roadblaster`), `bin/build_mon_native_song.py` `_snap_onset`.

### F11. A gap-encoded timeline has no origin unless something records it
**Symptom**: a voice's content is exact and its whole timeline is shifted. The
shift is *constant per voice*, so a scorer that fits ONE global boot offset
absorbs whichever voice dominates the fit and reports the others as broken. What
you see is one voice at 100% beside two at 50-65% with byte-identical note
sequences.

**Detection**: compare the per-voice **first onset frame** against the tick the
shim actually places that voice's first event at. `Billie_Jean`'s first onsets
are `[2, 0, 962]`; all three voices started at tick 0. Voice 1 (first onset 0)
scored 100.0 and set the global fit; voices 0 and 2 were 2 and 962 frames early.

**The trap that hides it**: voice 2's 962-frame shift MEASURED as the same −2 as
voice 0, because that voice's phrase is periodic at 96 frames and
962 = 10×96 + 2. A shift of a whole number of phrase-lengths is invisible to
every per-frame column and to a gate-rise delta histogram alike. Only the
absolute onset list shows it — check the origin, not the residual.

**Fix**: the shim emits note durations as onset-to-onset **gaps**, so each
voice's tick timeline is relative to its own first onset. A leading rest of
`onsets[v][0]` ticks restores the origin. DMC already did this for its *legato*
voices, with a comment saying exactly why ("a leading rest lands the first note
at its absolute frame so a late-entering voice stays in sync") — it was simply
never applied to the gate schedule, which is what nearly every file builds with.
`DMC_LEAD_REST=0` restores the old behaviour for an A/B.
`Billie_Jean` v0 **63.3/50.1/81.2 → 99.9/99.9/99.9**; `Blue_Monday_88` v0
**65.8/60.0/8.1 → 98.8/99.8/99.4**.

**Expect the raw column to FALL on the voices it fixes.** A late-entering voice
now spends its pre-entry frames on rest rows, and the original spends them
holding whatever init left in `$D404`/`$D400`. Both are gated off and inaudible,
but they are not equal: `Billie_Jean` v2's raw wf went 94.2 → 49.3 while all 67
of its onsets became exact and every one of its 190 sounding frames is 100%.
That is why `dmc_native_sweep` grew an `[aud …]` column — printed only where it
differs from raw, so the first number does not stop being read.

**This is a REDISCOVERY, and the first sighting is already pinned by a test.**
HardTrack hit it in `Love_tune_2` (voices 1 and 2, "10 and 20 frames early, and
the fidelity metric shows it as a whole-voice failure rather than as a phase")
and `pyscript/test_hardtrack_native.py::test_event_timeline_is_contiguous_from_tick_zero`
has asserted the contract there ever since. The contract is stated in that
docstring — *`build_native_song` places event k at tick `sum(dur[:k])`* — and it
belongs to the SHARED builder, so it binds every shim. DMC's gate schedule
simply never had the assertion written for it. When a shared contract is pinned
in one player's test file, the pin does not travel: check the others in the same
commit, or add the test where it will be read.

**Seen in**: HardTrack (`Love_tune_2`, 2026-08), DMC (`Billie_Jean`,
`Blue_Monday_88`, 2026-08-15), `bin/build_dmc_native_song.py` `DMCShim.__init__`.
Future Composer, Hubbard, SDI and Sound Monitor encode durations the same way
and have NOT been checked.

### F12. Two corpus builders share more state than the one file you know about
**Symptom**: artifacts differ between runs of the same code, and the SET of
differing files CHANGES from run to run. (A *stable* set is not this — that is
a real behaviour difference, or a baseline built with different code.) Scores
can look perfect throughout: the DMC sweep printed `SCORES IDENTICAL` over 5
corrupted artifacts because it scores **part 1 only** and every corrupted file
was part 2 or later.

**Detection**: build the same few songs serially, then in parallel, **with the
same code on both sides**, and byte-compare the artifacts *and* the printed
scores. Both, because they fail independently: the builds can be correctly
locked while the SCORER races (one shared probe file moved the DMC corpus
median 99.5 → 96.4 with 1130 of 1194 artifacts byte-identical).

**The shared state is four things, not one.** Each one found only exposed the
next:
1. `drivers_src/mon/layout.inc` + `freqtable.inc` — written, then assembled from
2. `drivers_src/romuzak/layout.inc` — **hardcoded** path, rewritten per part
3. `out/romuzak_driver.prg` — assembler output, read straight back; the worst,
   because the PRG *is* the driver image
4. the scorer's scratch probe — a fixed `_*_probe.sid` shared by every song

**Fix**: a cross-process lock (`MON_BUILD_LOCK=1`, taken by `--jobs > 1`) around
the whole gen→copy→freqtable→assemble section as ONE unit; locking finer lets
another process overwrite a file between a write and its read. Everything
expensive — tracing, parsing, packing — stays outside it: DMC 3.5 h → 14 min at
-j16. Equivalence was verified on **4 songs / 71 artifacts at -j8, byte-identical
to serial on the same code** — not at corpus scale, and worth stating that way,
because 5 of 88 DMC songs are separately known to take different adaptive part
splits between runs (open, pre-existing, unrelated to the lock). Scratch probes
are named from their input
instead (`tempfile.mkstemp` is the other correct answer). Isolation — a private
copy of each shared file per process — also closes the race but CHANGED output
for reasons never established, so it was abandoned in favour of the lock.

**On Windows the lock itself has a trap**: a lock file whose last handle closed
while still pending deletion answers `O_CREAT|O_EXCL` with `ERROR_ACCESS_DENIED`,
not "exists". Catching only `FileExistsError` let a `PermissionError` escape and
killed one song's build per corpus run (78 escapes in a 20k-acquire stress);
the sweep recorded the error and carried on with a quietly smaller denominator,
which read as "one config builds more songs than the other". Catch both.

**Related but different**: F2 is about editing a module *while* a runner is
live. This is two runners racing each other with nobody editing anything.

**Seen in**: DMC, HardTrack, SDI (2026-08-16, `4d01910` / `3ffdadb` / `6ab60f3`
/ `722bcaf`). Before that the hazard was folklore — `whats-next.md` asserted it
and cited F2, which does not say it, and PATTERNS did not cover it at all.

---

## Adding an entry
One screenful max: symptom → detection → exploit/fix → players seen in.
If a technique is rediscovered in a new arc, add the sighting here *in the
same commit* as the fix.
