<original_task>
The session opened with **"read what next"** — i.e. read this file. The version found was itself
stale (written at HEAD `dee93ba`, claiming "Stage B not started" when Stage B had already shipped),
so the first act was to report that and re-derive real state from `docs/players/HARDTRACK.md`'s
`## Next steps`.

Everything after that came from the user repeatedly saying "cont"/"continue" plus these explicit
instructions, in order:

1. `read what next` — report state.
2. (user switched the model to Opus after I flagged the escalation for the filter work)
3. `push and commit` — the filter-engine arc.
4. `/subtask model sonnet: yes, update whats-next.md`
5. `cont` × many — I chose each next item and reported the choice.
6. `are we done with this new player?` — status question.
7. `rung 3` — run PLAYBOOK §4 rung 3.
8. `do 1.` — diagnose the (then-apparent) SF2II discrepancy.
9. `what next` × 2 — planning questions.
10. `/whats-next` — this document.

**Scope**: all work is HardTrack Composer (Longhair/Brush, Elysium 1992) except two
`sf2_viewer_core` bug fixes found while inspecting HardTrack's own output, and one DMC builder fix
that shares the defect found in HardTrack's.
</original_task>

<work_completed>

## End state
**HEAD `7e0ed22`**, version **3.25.0**, `origin/master` in sync (0/0). Tests **2,297 passed / 8
skipped / 2 xfailed / 0 failures** (2,307 collected). 25 commits this session.

| SHA | Subject |
|---|---|
| `1078eba` | feat(hardtrack): model the filter engine -- it is global, not per-voice |
| `a895820` | chore: bump to v3.25.0 |
| `554db9c` | docs(hardtrack): the filter registers, and the control that moved nothing |
| `ba922b2` | docs: refresh whats-next.md -- it had gone fourteen commits stale |
| `de0170d` | docs: re-stamp v3.25.0 -- the bump had missed the matrix and the CHANGELOG heading |
| `bd5a356` | feat(hardtrack): seed the second player build per-variable, from the consumers |
| `ac97d46` | fix(hardtrack): reproduce the second build's STA $D406,X -- it means ,Y |
| `beedacc` | docs(hardtrack): rung 4 -- the first listening pass, and its limits |
| `cffc51e` | fix(stageb): capture the $D418 passband -- HardTrack and DMC rebuilt low-pass |
| `d30a7d0` | fix(ci): sha256 in output_digest -- bandit B324 was failing every push *(not mine — see below)* |
| `122eb55` | fix(stageb): align HardTrack's filter capture -- it ran 3 frames early **← REVERTED** |
| `0ed5986` | Revert "fix(stageb): align HardTrack's filter capture..." |
| `651f004` | docs(hardtrack): re-measure the register table at the render's real offset |
| `b6f8a3d` | docs(hardtrack): prove hard_restart=1 is the WRONG fix for the ADSR residual |
| `32e8542` | docs(hardtrack): scope Stage C by measurement -- bundles bind, pulse cannot help |
| `8f800dc` | refactor(hardtrack): rename Instrument.hard_restart -> skip_filter_rearm |
| `3e6c9e9` | fix(sf2-viewer): the Laxity driver detector matched EVERY SF2 file |
| `80b5a72` | fix(sf2-viewer): Driver 11 orderlists came from a hardcoded Laxity file offset |
| `1dc51be` | docs: audit this cycle's published figures -- a retired lead was still live |
| `2fdee08` | docs(hardtrack): price Stage C's FM prong -- a 9x collapse, cheaper levers ruled out |
| `a4f5971` | fix(hardtrack): resolve out-of-range arp reads to live variables -- seeded pop hits 100% |
| `dfef319` | docs(hardtrack): rung 3 RAN -- and is inconclusive **← RETRACTED** |
| `a9d5ea8` | docs(hardtrack): CORRECTION -- ... Stage B FAILS it **← ALSO RETRACTED** |
| `848972e` | docs(hardtrack): CORRECTION 2 (final) -- rung 3 PASSES; SF2II matches our render |
| `7e0ed22` | docs: refresh whats-next.md |

---

## 1. The filter engine, modelled (`1078eba`, `554db9c`)

**Files**: `sidm2/hardtrack_parser.py`, `sidm2/hardtrack_synth.py`,
`pyscript/hardtrack_synth_validate.py`, `pyscript/test_hardtrack_synth.py`.

### The structural finding
The filter is **GLOBAL, not per-voice**. Instrument fields 6/7/12 are read *per voice* at note-on,
which invites a per-voice envelope, but the consuming engine sits **past the `dex / bmi` at
`$1583`** that ends the voice loop:

```
1583  DEX
1584  BMI l1589      ; all three voices done?
1586  JMP $10ef      ; no -> next voice
1589  DEC $16b2      ; <- the filter engine: ONCE PER FRAME
```

Its cursor / cutoff accumulator / delta / `$D418` mode nibble live in **self-modified operands**
(`$158F`, `$15B2`, `$15B5`, `$15BD`), which is why an operand scan for a table address never named
them — the addresses being written are inside the code.

Second consequence from the same bytes: voices are stepped **2, 1, 0** (`$10ed LDX #$02`). The
model had been stepping 0,1,2 — immaterial for per-voice registers, decisive for a global filter.
Fixed.

### Signatures added to `hardtrack_parser.py`
`_SIG_FILTPROG`, `_SIG_FILTACC`, `_SIG_FILTMODE`, `_SIG_FILTARM`, `_SIG_FILTOFF` — **all unique in
33/33** decodable files. New `HardTrackModule` attributes: `filter_table`, `filter_cursor`,
`filter_cutoff`, `filter_delta`, `filter_mode`, `filter_delay`, `filter_shadow`, `filter_volume`,
`filter_route_bits`, `filter_route_masks`, `filter_f6_table`, `filter_f7_table`, `filter_f12_table`,
plus `filter_program(cursor)`. Signature-derived f6/f7/f12 agree with stride-derived on **33/33**.

### Corrections to `docs/players/HARDTRACK_FILTER_AND_SLIDE.md`
- `f12 == 0` does not merely mean "not routed" — it **actively clears** the voice's routing bit at
  `$13cb` (`LDA $101F / AND $16DA,x / STA $101F / STA $D417`).
- The engine runs once per frame after the voice loop, not once per voice.

### Other facts established
- `init` resets **none** of the filter state — all seeded from the saved module image.
- `$16D7..D9 = $01,$02,$04` are the per-voice routing OR-bits; `$16DA..DC = $FE,$FD,$FB` their exact
  complements.
- Runtime volume comes from `init`'s `lda #$0f` store, **not** the image byte — recovered by
  searching for init's store to the signature-derived address, because `Tribute_to_Laxity` shifts
  that block by one instruction. 33/33 give `$0F`.
- **`$D415` has zero stores corpus-wide** — the cutoff is the 8-bit `$D416` alone.
- The accumulator is 8-bit and **wraps** (`CLC/ADC`, no clamp): `Love_tune_2` runs
  `$1a → $5a → $9a → $da → $1a`, and siddump agrees on every frame.

### Measured (`-t 20`, all 33 files)
| register | frames | byte-exact | files n/a |
|---|---|---|---|
| cutoff `$D416` | 32,967 | **100.00%** | 0 |
| resonance+routing `$D417` | 32,967 | **100.00%** | 0 |
| mode+volume `$D418` (bits 0–6) | 9,990 | **100.00%** | **23 of 33** |

### Five negative controls (because a uniform 100% is the shape this repo has been wrong about)
| deliberately broken | `$D416` | `$D417` |
|---|---|---|
| *(unmodified)* | 100.00% | 100.00% |
| cutoff clamped at 255 instead of wrapping | 24.75% | 100.00% |
| filter program never steps | 23.90% | 100.00% |
| `f12 == 0` skips instead of clearing routing | 100.00% | 48.28% |
| fields 6 and 7 swapped | 28.34% | 100.00% |
| **field-5 bit-4 re-arm gate ignored** | **100.00%** | **100.00%** |

The last row is a **negative result**, recorded as one: only **21 instruments** corpus-wide set the
bit and **one** of those has a filter to re-arm, so this corpus can neither confirm nor refute the
reading. Pinned by `test_field5_bit4_is_not_exercised_by_this_corpus`.

---

## 2. Second player build seeded per-variable (`bd5a356`)

Open item 4b asked for a second `_RAM` table. **Wrong shape twice**: the second build lays out its
*code* differently too (`$11bf` is mid-instruction there), so no positional table can follow it,
and `Tribute_to_Laxity` would need a third.

Instead: `HardTrackModule.voice_var_addrs()` recovers variables from **their own consumers** via
`_SIG_MODEVAR` (unique 33/33, self-checking — both operands appear twice) plus `_SIG_FREQ`.

**Which variables matter was measured, not guessed.** Per-variable ablation across the 18 build-1
files (26,569 voice-frames):

| zeroed | cost |
|---|---|
| `mode` | **−1.67 pts** |
| `freq_hi` / `freq_lo` | −0.20 / −0.18 |
| vibrato + slide tail | −0.01 to −0.05 each |

Signature-derived addresses agree with the `_RAM` layout on **18/18** where both exist.
Second-build frequency **99.15% → 99.68%**.

`seed_source(module)` returns `(resolve, label)` with labels `layout+sig` (18 files) / `signature`
(15) / `layout` / `none`. The validator's `seed` column is now that **source name**, not a bool.

⚠️ **The remainder was NOT a seeding gap**: restricting build 1 to the same five variables costs it
only **0.03 points** (99.976% → 99.946%), so the other 38 could not explain the rest.

---

## 3. A player bug reproduced (`ac97d46`)

Following that lead into `Shogoon-Rave` (worst second-build file, 96.5%) found a defect in the
**player**. Its `$62` (CMD_RESET) handler:

```
112F  LDA #$00
1131  STA $165a,x     ; waveform := 0
1134  BC A0 16  LDY $16a0,x     ; compute Y = this voice's SID slot...
1137  9D 06 D4  STA $d406,x     ; ...then store indexed by X anyway ($9D = abs,X)
113A  LDA #$01 / STA $168e,x
```

`$9D` is `STA abs,X`; the code plainly means `$99`, `STA abs,Y`. Zero lands at `$D406 + x`:

| x | address | what it hits |
|---|---|---|
| 0 | `$D406` | voice 0 sustain/release — right by accident |
| 1 | `$D407` | **voice 1 frequency LOW** |
| 2 | `$D408` | **voice 1 frequency HIGH** |

`STA $D4xx,X` occurs in exactly **two** places corpus-wide: `init`'s legitimate `$D400-$D41C` clear
loop, and this. The 15 files carrying it are **precisely** the 15 second-build files. Build 1's
handler writes variables only (`sta waveform,x / sta sr,x`) and is gated out via
`module.reset_pokes_sid`.

Result: `Shogoon-Rave` voice 1 **43 misses → 1**; second-build population **99.68% → 99.81%**.

**How it was found matters**: three static readings fitted the data and were all wrong (vibrato
depth — which really does live in a different place per build; the seed; the wave-program cursor).
What settled it was running the real playroutine under **py65** and logging which PC wrote the
register: every other frequency write came from `$152f`, that one from `$1137`.

---

## 4. Rung 4 — the first listening pass (`beedacc`) and the defect it found (`cffc51e`)

`Love_tune_2` part 1 (0–28 s), original vs Stage B render, via
`pyscript/audio_tightness_tool.py`.

**Control first**: original vs itself scores **exactly 0.0 on every feature** (deterministic
render), so deltas are real signal.

| | original | Stage B (before fix) | after fix |
|---|---|---|---|
| RMS (A-wtd) | −29.2 dBA | −28.5 (+0.7) | −29.6 (−0.4) |
| spectral centroid | 1994.0 Hz | 1894.7 (−99.3) | 1941.1 (**−51.4**) |
| rolloff (85%) | 4478.0 Hz | 4197.9 (−280.1) | 4287.4 (**−169.6**) |
| flatness | 0.494 | 0.479 (−0.015) | 0.491 (−0.003) |

Spectrogram (`out/hardtrack_native/lt2_spec.png`, read with the Read tool): **no gross defect** —
matching harmonic banding, rhythmic structure and section boundary; diff panel mostly neutral with
fine vertical striping = small time-alignment jitter.

### The defect: the `$D418` passband was never captured
`build_native_song` takes traces as `(per_frame, filter_trace, passband_trace)`. The HardTrack
builder passed a **2-tuple**, so `_filt_set_row` defaulted to `passband=1` (low-pass).
`Love_tune_2` selects **low+band on 100% of frames** and was rebuilt **low-only on 100%**.
Passband match **0.0% → 100.0%**.

It is a **known class the builder was missed by** — `passband_trace`'s own docstring names the
identical defect on MoN's `Cybernoid_II` (`$D418 = $3F`, "we wrote `$1F`") and says why it hides:
*"Inaudible in the freq/wf/pulse columns"*. That is exactly why it survived here — this builder's
fidelity report **scores frequency and nothing else**, so no headless number could have moved.

**Then checked across every native builder, measured not assumed** (an absent call is only a defect
if that player's originals select a non-low-pass passband):

| builder | its original selects | verdict |
|---|---|---|
| HardTrack | low+band 100% | **was wrong — fixed** |
| DMC (`Rockbuster`) | low+band 100% | **was wrong — fixed** |
| Future Composer, SDI | low 100% | default right by luck |
| Hubbard, Sound Monitor | none 100% | nothing to get wrong |

DMC has no `.sid` wrapper to render, so its fix was verified by **byte-diffing the emitted SF2
against a build with the change reverted: exactly 8 bytes differ, all filter SET rows, every one
`low → low+band` with its cutoff nibble untouched.**

⚠️ The per-voice sweep's SYNTHESIS/SEQUENCER verdicts (audio 73/67/47 vs floors 90/96/95) are **NOT
quotable**: the driver render fails the voice-isolation guard (8.6/9.1/13.2% shared energy vs the
original's 1.5/2.1/2.7%, tool prints `[WARN]`), and "register-exact but SYNTHESIS on every voice"
was already falsified once on MoN as metric noise (PATTERNS.md F5b; the tool's own rank test is
p=0.25 by chance).

---

## 5. Out-of-range arp reads → live variables (`a4f5971`)

Previously recorded as needing "a real memory array… a much larger change than the 0.099%
justifies". **That was an over-estimate.**

A wave program's arp offset can push the note index past the 96-entry frequency table
(`arp $33` on note 54 → 105). The tables sit directly in front of the player's variable block, so
`freq_hi_table + 105` = `$1651` = voice 0's `freq_lo`. The real player reads **live RAM**; an
image-based model reads the frozen byte.

The model needs only the addresses it can already **name**. `_var_addr_map(module, resolve)` inverts
the two seed sources into `{address: (attribute, voice)}`; `b_live` consults it, and the
frequency-table read uses it **only when `n >= NUM_NOTES`**.

| population | before | after |
|---|---|---|
| layout-seeded (43 mapped) | 99.98% — 13 misses | **100.00% — 0 of 53,569** |
| second build (5 mapped) | 99.81% — 84 misses | **99.89% — 47** |

**The split is the evidence**: fully-mapped goes to *exactly* 100.00% while partially-mapped keeps a
proportional remainder.

---

## 6. `hard_restart` → `skip_filter_rearm` (`8f800dc`)

`Instrument.hard_restart` (bit 4 of field 5) was documented as a misnomer in two places and never
renamed. Its only consumer is the guard in front of the filter block (`$137d`), meaning "on a
repeated note, skip the filter re-arm". Field 5 is read exactly three times per file, masked
`$03`/`$10`/`$80` in 33/33. **Zero callers**, so a clean rename. Docstring carries the disassembly,
the mask evidence, and why the corpus can't test it (21 instruments / 1 with a filter).

---

## 7. Two `sf2_viewer_core.py` bugs — both "a Laxity constant applied to every driver"

### (a) The detector matched every SF2 (`3e6c9e9`)
`_detect_laxity_driver()` tested `load_address == 0x0D7E` + "some non-zero byte at `$0E00`".
**`$0D7E` is the SF2 CONTAINER load address** — identical for Laxity and Driver 11 — and any
non-empty file satisfies the second clause. So it returned True for **every** file; Laxity parsed
fine afterwards so nothing looked wrong, while Driver 11 files fell into a fallback printing three
`invalid sequence address $0000` warnings.

Fixed by testing the **driver name** from block 1. Needed `_normalize_driver_name` because the name
ships in two encodings — **the first attempt regressed genuine Laxity files**:
```
Angular.sf2   L,$01,$18,$09,$14,$19   screen codes -> LAXITY
Balance.sf2   "Laxity"                plain ASCII
HardTrack     D,$12,$09,$16,$05,$12   -> DRIVER 11.00 - THE STANDARD...
```
`driver_info['name_normalized']` folds screen codes `$01-$1A` → A-Z. **17/17 correct** (12 Laxity +
5 Driver 11) vs the old detector's 12/17.

### (b) Driver 11 orderlists read from a Laxity file offset (`80b5a72`)
`_parse_music_data` derived column 1 as `load_address + (0x1766 - 4)`. `$1766` is a **Laxity** file
offset; on a Driver 11 file it resolves to `$24E0`, a run of zeros — so every orderlist position
exported as `A000` (transpose `$A0`, sequence 0) on all three tracks.

Real address is the **Music Data block's word at offset 12** (`$242A` on all five Driver 11 files).
Columns 2/3 at +`$100`/+`$200`, which the code already assumed.

Verified by an invariant the broken read cannot satisfy: the emitter numbers sequences 0..N with no
gaps, so a correct orderlist references exactly **max+1** distinct sequences. All five now do
(Zakplus 62/`$3D`, Love_tune_2 30/`$1D`, Love_tune_3 25/`$18`, Muminki 20/`$13`, Hopscotch 56/`$37`).
Two corroborations: Muminki's raw track ends with the `$FF` loop marker at exactly its unpacked
length, and every transpose reads `$A0` — matching Stage A's documented materialising of transposes
into duplicate sequences.

**Scope deliberately limited to non-Laxity files** — the hardcoded offset does not survive
inspection for Laxity either (the block word disagrees on all five tested), but Laxity has its own
working parse path and choosing needs ground truth this change did not have. Pinned by
`test_laxity_orderlist_address_is_deliberately_unchanged`.

---

## 8. Rung 3 — the instrumented SF2II capture: **PASSES** (`848972e`)

`bin/sf2ii_vs_real.py` runs `bin/SIDFactoryII_dbg.exe`, a patched editor that dumps
`SIDFR <frame> r0..r24` every frame.

**The decisive comparison** (which took three attempts to get right): our `.sid` wrapper and the
`.sf2` carry the *same* driver and data, so the question is whether the editor executes them the
same way — compare SF2II against **our own render**, not the original:

| voice | freq | waveform | pulse | n |
|---|---|---|---|---|
| 0 | **100.0%** | **100.0%** | **100.0%** | 294 |
| 1 | **100.0%** | **100.0%** | **100.0%** | 286 |
| 2 | **100.0%** | **100.0%** | **100.0%** | 82 |

At offset 0, exactly. **No SF2II-only hazard.** Script at `/tmp/sf2ii_vs_wrapper.py` (scratch — see
Critical Context).

---

## 9. Stage C priced (`32e8542`, `2fdee08`)

**Which cap binds** (`Love_tune_2`, growing the window from frame 0):

| window | bundles /63 | instr /32 | wave /256 | filter /256 | seq /120 |
|---|---|---|---|---|---|
| 0–1400 | 48 | 24 | 88 | 123 | 4 |
| 0–1700 | **79 ✗** | 30 | 104 | 129 | 6 |
| 0–2400 | **98 ✗** | **33 ✗** | 109 | 129 | 9 |
| 0–5865 | **262 ✗** | **54 ✗** | 165 | 161 | 19 |

Bundles bind first, instruments second; wave/filter/seq never come close.

**Bundle decomposition** (via the pre-existing `BUNDLE_DECOMPOSE=1` hook):

| window | pairs | distinct FM | distinct pulse |
|---|---|---|---|
| 0–1700 | 79 | **71** | 34 |

**Every cheaper lever ruled out by measurement**: `MON_PULSE_CANON` / `MON_WAVE_CANON` change
nothing (PULSE_CANON's gate only substitutes when `_pulse_unroll` is *identical* — strictly
lossless, which HardTrack's per-note sweeps rarely satisfy); `BUNDLE_TOL` swept **0/2/4/8/16/32**
stays at **79 at every setting**.

**The prize**: 286 note events in that window use 10 instruments and only **8 distinct arp
programs** when read as pitch-independent semitones from the wave program's arp column, vs **71**
Hz-delta unrolls. A ~9× collapse on exactly the binding axis. ⚠️ 8 is the FM side *alone*; pulse
stays at 34, so the resulting bundle count needs the implementation to settle.

---

## 10. Doc audit (`1dc51be`, `de0170d`)

- `de0170d`: the v3.25.0 bump had **missed** `ACCURACY_MATRIX.md`'s header stamp (still 3.24.0) and
  left everything under `## [Unreleased]` with no `## [3.25.0]` heading. CLAUDE.md explicitly names
  the matrix as the file a bump must re-stamp *because it has drifted before*.
- `1dc51be`: every headline figure re-run and reproduces exactly, including derived ones
  (17,982+14,985 = 32,967; 6,993+2,997 = 9,990; 13+84 = 97 of 53,569+44,237 = 97,806). **One real
  inconsistency**: CLAUDE.md and ACCURACY_MATRIX still carried a RETIRED lead ("the waveform match
  falling ~86% → 70-79%") four commits after the correction landed in HARDTRACK.md. Also two "runs
  all" test counts where only one had been maintained (`~2,295` and `~2,065`).

</work_completed>

<work_remaining>

Ranked. Note **item 0** — a concurrent session is editing the HardTrack builder right now, which
gates items 1 and 3.

### 0. Resolve the concurrent-session overlap (BLOCKING for 1 and 3)
`bin/build_hardtrack_native_song.py` is modified in the working tree by **another session**, adding
imports from a new untracked `sidm2/instrument_map.py`:
```python
from sidm2.fidelity_common import score_pct, siddump_frames_full
from sidm2.instrument_map import (
    InstrumentScores, frame_labels, instrument_labels, key_reliability,
    onsets_with_registers)
```
Untracked companions: `sidm2/instrument_map.py`, `pyscript/instrument_map_report.py`,
`pyscript/instrument_map_sweep.py`, `pyscript/test_instrument_map.py`, `instrument-map.bat`,
`docs/plans/INSTRUMENT_MAP_PLAN.md`. **Do not commit or revert these — they are not this session's
work.** Wait for them to land before touching that builder.

### 1. ~~Stage C's FM prong~~ — **IMPLEMENTED AND REVERTED**, the trade does not pay
Built end to end and measured; reverted on the evidence, not on difficulty. Full write-up in
`docs/players/HARDTRACK.md` ("IMPLEMENTED AND REVERTED"). Summary:
- The collapse is exactly as predicted — **1,028 of 1,327 note events → 8 distinct programs**.
- Under the existing `tol` guard: parts **6 → 4** (cap moves off bundles onto instruments, 32/32)
  but freq raw **92.8/92.9/95.1 → 84.7/85.8/88.1**, audible down to 58.5 on voice 1, per-voice
  misses roughly doubled — and **not** on the driver's note-on frame, so they are real.
- Exact-guarded (`tol = 0`): fidelity baseline to the frame, part count **still 6**, because only
  **148 of 8,526** substitutions survive (1.7%).
- Root cause: HardTrack's captured pitch almost never follows the pure table arp — vibrato,
  `$63`/`$64` slides and detune ride on nearly every note. **This is why Stage B captures rather
  than models**; the prong asks it to resume modelling the one dimension it stopped modelling.
- ⚠️ Three format readings taken from the table BYTES were all wrong and cost the first two
  attempts: `$FE` is a stepper **FREEZE** (not a jump), `$FF` is the jump (target in the arp
  column), and an arp byte with bit 7 set is an **absolute note** — every program opens with one
  (`$81`/`$cc`, a one-frame noise burst at note 76). The authority is `hardtrack_synth`'s `$1454`
  stepper, the model validated byte-exact, never the bytes.
- **To restart this**: the structural arp must COMPOSE with the per-note modulation (semitone arp
  plus captured residual), not replace it. The residual is most of the pitch signal, not noise.

### 2. ~~Per-voice offset in `bin/sf2ii_vs_real.py`~~ — **DONE**, and the diagnosis above was wrong
The prescribed fix (per-voice offset) was implemented, measured, and **reverted**: it picked
offsets 5/317/147 for three voices that in fact share −3, because a repetitive tune has many
spurious alignment peaks. The offset is genuinely global — it is one startup delay. The two real
defects, both now fixed:
1. `range(0, 400)` **cannot express a negative offset**, and the render leads the original by 3
   frames, so the true answer was never in the search space.
2. Offsets were ranked by **raw hit count**, which is confounded by how many captured frames an
   offset leaves inside the trace window — offset 157 beat −3 on hits (208+43+52) at a far worse
   rate (67/14/62%). Coverage is now a fairness *filter*; rate is maximised within it.

Verified: `Love_tune_2` part 1 now resolves to −3 by itself — freq **91/93/64%**, waveform / pulse /
AD/SR **100%** on all three voices (79/86/57% at the bogus offset), filter cutoff and routing 100%.
Control: MoN `out/mon/Cybernoid_II_sub0_part01.sf2` still resolves to offset 0 with every
per-metric figure byte-identical to the pre-fix run (984/987, 945/948, 126/126, cutoff 1000/1002).

### 3. SR-only `$7D` row (asm, shared driver)
ADSR is the weakest register in the audible window (88–94%) and the residual is systematic: AD
always agrees while the original writes SR = `$00` — HardTrack's pre-note-on hard restart, on frames
that **precede** the per-note capture window.
- ⚠️ `hard_restart = 1` is **provably wrong**: `_hr_rows` makes the driver's `$7D` row zero **AD and
  SR**, while HardTrack never touches `$D405` (AD differs on **0 / 10 / 20** of 1,397 frames).
- A correct fix needs an **SR-only** `$7D` variant in `drivers_src/mon/`, shared by seven players.
  Audible value **unproven** — the cutoff-alignment episode is a live example of a large register
  gain buying nothing audible.

### 4. ~~Second build's remaining 47 frames~~ — **DONE**, 47 → 18 (and it was not a mapping gap)
The premise was wrong. They were not "the variables the second build's layout does not expose":
every one of the 15 files lost exactly **3 frames, all on frame 3, one per voice** — the last
note-on pipeline frame, where the register still holds the module image's power-on value.

Cause: `vib_depth` is in **no** layout on either build, so it was the last variable seeded from a
**constant** (`load + $1C`) — the pattern this player breaks. Its bytes *were* the error:
`Shogoon-Rave` holds `$42 $23 $0b` there and its voices were wrong by exactly +66/+35/+11.
Masked on build 1 only because that build's other vibrato state is seeded and blocks the vibrato
before the first note.

Fixed by recovering it from the leg that reads it (`HardTrackModule.vibrato_var_addrs`): four
`LDA freq_lo,X / CLC|SEC / ADC|SBC amount,X` legs forming two operand-sharing pairs (slide, then
vibrato), unique and self-checking on **33/33**. Resolves to `$101c` on all 18 build-1 files —
the old constant, so they are byte-for-byte unchanged at exactly 100.00% — and to `$16bb`
(`$46bb`/`$a6bb` relocated, `$16ef` for `Tribute_to_Laxity`) on the other 15.
**Second build 99.89% → 99.96%**; Trance, Tribute_to_Laxity and What_Can_I_Say_Crap now exactly
100.00%. Pinned by `test_vib_depth_comes_from_its_consumer_not_a_constant`.

⚠️ **Open lead, left open on purpose.** On build 2 *alone*, seeding **nothing** scores better than
the correct address (10 misses vs 18), so the saved byte at `$16bb` is not quite the power-on
value — the address is unique 33/33, the byte is what is in doubt. Corpus-wide the recovered
address is still both best and principled (0+18 vs the constant's 0+47 and nothing's 13+10), and
taking the better-scoring seed is precisely how the constant being replaced got here. Clue:
`$16bb` is at **+109 from `freq_hi`**, which is `vib_dir`'s block offset on build 1 — the second
build's variable ORDER may differ.

### 5. ~~Laxity's orderlist address in `sf2_viewer_core.py`~~ — **DONE**; the ground truth existed
Recorded as needing "Laxity ground truth". It was available three ways, all agreeing that the
hardcoded `$1766` is wrong and the Music Data block word at offset 12 is right for Laxity too:

1. **Structure.** Across **53 files spanning both drivers** the block's words are laid out
   identically: `word16 − word12 = $300` (three tracks of `$100`), `word12 − word8 = $80`,
   `word8 − word6 = $80`. So word12 is the orderlist base and word16 its end, with no per-driver
   variation to special-case. The constant cannot be part of that layout — every Laxity file here
   loads at `$0d7e` so it is always `$24e0`, while word12 moves per file, and for **42 of 47** it
   does not even land inside `[word12, word16)`.
2. **The invariant that settled Driver 11.** All three tracks terminate and the orderlist
   references exactly max+1 distinct sequences: word12 **47/47**, the constant **0/47**.
3. **An independent decode.** `laxity_parser` reads Angular's source SID without touching the SF2.
   word12 gives `[0]` / `[1]` / `[2,3]` — transpose `$A0`, small sequence numbers, `$FE`
   terminator — against the source's `[0]` / `[2]` / `[1]`; the renumbering is the converter
   materialising transposes into duplicate sequences, which is documented. The constant gives
   **253 entries of sequence `$7F`**.

So "Laxity has its own parse path that currently works" was **wrong** — it was reading `$7F`/`$00`
filler and reporting a couple of hundred phantom orderlist positions. The special-case is removed;
both drivers now take the block word. `test_laxity_orderlist_address_is_deliberately_unchanged`
pinned the opposite and is replaced by `test_laxity_orderlist_comes_from_the_block_word_too`.

⚠️ Two measurement traps on the way, both mine: `blocks.get(5)` returns None because the dict is
keyed by `BlockType`, not `int` (I briefly concluded the Laxity block had no word 12); and reading
image bytes as `data[addr - load + 4]` disagrees with `self.memory[addr]` — the first made `$1fcb`
look like `fe ff ff`, the second shows the real `a0 00 fe`. **Use `parser.memory`.**

### 6. Remaining rung-4 brightness gap
About half is unexplained after the passband fix (windowed step from 12 s on, centroid
−58/−144/−70). ADSR/SR (item 3) is the best candidate. Note: the waveform lead was **retired** — see
Attempted Approaches.

</work_remaining>

<attempted_approaches>

## ⚠️ THREE wrong conclusions this session, ALL caused by alignment

**This is the single most important thing to carry forward.**

### (i) A filter-capture "fix" — SHIPPED then REVERTED (`122eb55` → `0ed5986`)
Over the 800 frames where the filter is routed in, the cutoff matched **0/800** at shift 0 and
**757/800 (94.6%) at −3**, and `onset_delay` for this player is exactly 3. Looked conclusive. I even
tested the obvious sign first (`onset + 3` made it *worse*: best −3 → −6, error 36.4 → 44.5) and
`onset − 3` "fixed" it (0/800 → 709/800, error 36.4 → 8.2).

**It was wrong.** The **whole part render sits at −3** — which is why `measure_voices` uses a
best-delay alignment. All three voices' frequency also peaks at −3 (96.1/95.7/77.1% within 50 cents,
vs 26.5/4.7/2.4% at shift 0). The cutoff's −3 was *already consistent*; forcing it to 0 desynced the
filter from the voices.

**The tell was in my own writeup and I ignored it**: a large register gain (0 → 88.6%) with **zero
audible change**. That is a reason to re-check the instrument, not a curiosity to publish.

### (ii) "Rung 3 is inconclusive — the tool is unreliable" — RETRACTED (`dfef319`)
Calibrated `sf2ii_vs_real.py` with `out/Cybernoid_II.sf2`, saw 0% frequency vs 99% waveform, and
concluded the tool's frequency column was untrustworthy. **`out/Cybernoid_II.sf2` is a Driver 11
Stage A build.** The byte-exact claim refers to the **native Stage B** build, which lives in
`out/mon/` and comes from `bin/build_mon_native_song.py`. Built properly it scores **100% on every
register of every voice** (890/890, 863/863, 114/114), cutoff 99%, routing 100%.

### (iii) "Stage B fails rung 3" — RETRACTED (`a9d5ea8`)
An artifact of the tool's single global offset. The same wrapper-vs-original comparison — same 20 s
window, same gating, same 1-semitone tolerance — done **per voice**:

| voice | at offset 0 | at shift −3 | tool reported |
|---|---|---|---|
| 0 | 23.6% | **91.2%** | 66% |
| 1 | 13.8% | **93.4%** | 21% |
| 2 | 4.3% | **64.1%** | 61% |

Every tool figure sits *between* the misaligned and correctly-aligned value.

### THE RULE
**A per-register or per-voice best-offset is meaningful only against the render's GLOBAL offset.**
This render sits at **−3**. `measure_voices` uses a best-delay alignment for exactly this reason;
`test_siddump_frame_alignment_is_zero_not_fitted` exists for the model side of the same rule.

---

## Other measurement traps hit this session

1. **A wrong test invariant**: asserted the three orderlist tracks are equal-length; Hopscotch is
   44/48/48. Voices loop at different points — the invariant was wrong, not the code. Replaced with
   sequence **contiguity** (references exactly max+1 distinct sequences).
2. **A `BUNDLE_TOL` sweep used the wrong env name** (`MON_BUNDLE_TOL`) and silently ran `tol=0` six
   times. The `effective@tolN` label in the output is what caught it.
3. **A test harness used `startswith('SF2/')`** where Windows `glob` returns `SF2\…` — reported 8
   false failures against correct code.
4. **Doc drift**: a RETIRED lead (the waveform one) survived in CLAUDE.md and ACCURACY_MATRIX four
   commits after the correction landed in HARDTRACK.md. I introduced that drift myself.
5. **Nearly added a `BUNDLE_DECOMPOSE` hook that already existed.** Checking first saved it.

## Leads investigated and RETIRED
- **"The waveform is the remaining brightness cause"** — retired. Its mismatch pairs are
  *symmetric* (`$40→$09` ×22 alongside `$09→$40` ×22; `$13→$12` ×40 alongside `$12→$13` ×38), which
  is a phase offset, not wrong content. At the correct −3 alignment the waveform is essentially
  exact (100.0/100.0/99.8%).
- **"`hard_restart = 1` fixes the ADSR residual"** — proven wrong (see Work Remaining item 3).
- **"The filter is not routed in for the first 12 s"** — *confirmed*, not retired: `$D417` routing
  bits read 0.00 then 0.79 → 1.00. That is why a +115 cutoff error over 0–12 s is inaudible and why
  the brightness step exists at all.

## Not pursued
- Giving `hardtrack_synth` a general memory array for the OOB reads — turned out unnecessary; only
  *nameable* addresses were needed (`_var_addr_map`).
- Changing the shared filter encoder to emit ADD-cutoff rows — the encoder **already** does
  run-length ADD encoding (`bin/build_mon_native_song.py:603-620`); my "9 static SET rows" inference
  was wrong ("filter=9" in the build log is 9 filter *programs*).

</attempted_approaches>

<critical_context>

## Reporting rules (do not violate)
- **Two fidelity columns, never averaged** — sequencer-pitch vs program-driven.
- **Always quote the match window** — it has **no plateau**.
- **Stage A > parser is an ARTIFACT** — quote retention (99.69%), not the diluted 91.34%.
- **`$D418`'s 100% rests on 10 of 33 files** — quote the file count or it reads as 3× the evidence.
- **The filter is GLOBAL** — never model it per-voice.
- **The render sits at −3** — judge any per-register alignment against that.

## Gotchas that cost real time
- **`out/<name>.sf2` is the Driver 11 Stage A build; native MoN builds live in `out/mon/`**, native
  HardTrack in `out/hardtrack_native/`, native FC in `out/fc_native/`. Using the wrong one as a
  byte-exact control produced retraction (ii).
- **Build-generated files get dirtied by every native build**: `drivers_src/mon/layout.inc`,
  `drivers_src/mon/freqtable.inc`, `drivers_src/romuzak/layout.inc`. They are auto-generated (header
  says so) and `bin/_sm_build_all.py` `git checkout`s them. Do the same; never commit them.
- **`bin/sf2ii_vs_real.py` overwrites `bin/SIDFactoryII_dbg.exe`** on every run by copying from
  `C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\x64\Release\SIDFactoryII.exe`. That
  tracked binary is currently modified (1,024,512 → 1,029,120 bytes) as a result. **Open question:
  is the newer build the one to commit?**
- **Python does not resolve `/tmp` on Windows** — Bash heredocs write to
  `C:/Users/mit/AppData/Local/Temp/`. Use the full path inside Python.
- **Grep on code files is blocked by a tokensave hook** when the pattern looks like a symbol;
  override with `TOKENSAVE_DISABLE_GREP_HOOK=1`.
- **`sf2_packer.py`'s `driver_top = 0x1000`** is the C64 *runtime* address, not an SF2 container
  address — its `orderlist_start = driver_top + 0x903` does **not** transfer to the container.

## Scratch files that WILL VANISH (promote if this work continues)
- `/tmp/sf2ii_vs_wrapper.py` — **the script that settled rung 3**. Captures SF2II and compares
  against our own `.sid` wrapper render rather than the original. This is the comparison rung 3
  actually needs and it does not exist in the repo. **Most worth promoting.**
- `/tmp/rave_pc.py` — py65 harness logging which PC writes `$D400-$D418` per frame. Found the
  `STA $D406,X` bug.
- `/tmp/ht_ablate.py` (per-variable seed ablation), `/tmp/ht_negctl.py` (the five filter negative
  controls), `/tmp/reg3.py` (register table at a given offset), `/tmp/bundle_split.py` (Stage C cap
  probe), `/tmp/filtshift.py` (the retracted shift experiment).

## Environment
- `SID/Shogoon/` and `bin/hardtrack composer/` are **tracked**, so tests run from a fresh clone.
- Full `pytest pyscript/` ≈ 175–180 s.
- `py -3` is the interpreter (Python 3.14.6, pytest 9.1.1).
- Useful env knobs: `BUNDLE_DECOMPOSE=1`, `BUNDLE_TOL=N`, `MON_PULSE_CANON=1`, `MON_WAVE_CANON=1`,
  `MON_ARP_STRUCT=1`, `FILT_DEBUG=1`, `HT_PIPE=N` (default 2).
- `pyscript/disasm6502.py` — `Disassembler6502(data, load, size).disassemble_instruction(addr)`
  returns a line with `.bytes`, `.instruction`, `.operand` (no `.size`; use `len(ln.bytes)`).

## Key references
- `docs/players/HARDTRACK.md` — the live per-player doc; its `## Next steps` is the real open list.
- `docs/players/HARDTRACK_FILTER_AND_SLIDE.md` — disassembly listings + RetroDebugger method.
- `docs/players/PLAYBOOK.md` §4 — the fidelity ladder (rungs 3 and 4).
- `docs/AUDIO_LISTENING_CALIBRATION.md` — onset match has **ordinal sensitivity but no absolute
  gate**; measure the floor per tune, never use as pass/fail.
- `sidm2/fidelity_common.py` — `score_pct` (None on n=0), `exercised()` (guards constant series).

</critical_context>

<current_state>

## Deliverables
| item | status |
|---|---|
| RE — format, all 13 instrument fields, filter engine, vibrato, slides | **complete** |
| `sidm2/hardtrack_parser.py` | **complete**, 32 tests |
| `sidm2/hardtrack_synth.py` — every register group predicted | **complete**, 47 tests |
| Register fidelity, layout-seeded population (18 files) | **frequency EXACTLY 100.00%** (0 of 53,569) |
| Register fidelity, second build (15 files) | 99.89% (47 of 44,237) |
| Stage A `bin/hardtrack_to_sf2.py` | complete — 99.69% retention over parser-resolved notes |
| Stage B `bin/build_hardtrack_native_song.py` | complete — 33/33 build |
| PLAYBOOK §4 rung 3 (instrumented SF2II) | **PASSED** — 100% vs our own render, all voices |
| PLAYBOOK §4 rung 4 (listening pass) | **run** — found + fixed the passband defect |
| `pyscript/sf2_viewer_core.py` detector + Driver 11 orderlist | **fixed**, 4 tests |
| Stage C | **not started** — priced at 71 → 8 FM programs |
| `DriverSelector` wiring | **not done, deliberately** — both stages are `bin/` tools |

## Repo
- HEAD **`7e0ed22`**, `origin/master` in sync (0/0), version **3.25.0**.
- Tests **2,297 passed / 8 skipped / 2 xfailed / 0 failures**; 2,307 collected.
- CHANGELOG has a stamped `## [3.25.0] - 2026-08-10` section; ACCURACY_MATRIX header re-stamped.

## ⚠️ Working tree is NOT clean — and most of it is not this session's work
```
 M bin/SIDFactoryII_dbg.exe            <- MINE (side effect of rung 3; see gotchas)
 M bin/build_hardtrack_native_song.py  <- NOT MINE (concurrent session)
 M drivers_src/mon/freqtable.inc       <- build artifact, git checkout it
 M drivers_src/mon/layout.inc          <- build artifact, git checkout it
 M drivers_src/romuzak/layout.inc      <- build artifact, git checkout it
?? docs/plans/INSTRUMENT_MAP_PLAN.md   <- NOT MINE
?? instrument-map.bat                  <- NOT MINE
?? pyscript/instrument_map_report.py   <- NOT MINE
?? pyscript/instrument_map_sweep.py    <- NOT MINE
?? pyscript/test_instrument_map.py     <- NOT MINE
?? sidm2/instrument_map.py             <- NOT MINE
```
A concurrent session is building an "instrument map" feature and has already edited the HardTrack
Stage B builder to import from it. **Do not commit or revert those.** Earlier in this session the
same thing happened with `sidm2/fidelity_common.py` + `pyscript/test_fidelity_common.py` (a
sha1→sha256 bandit B324 fix) — that one landed as `d30a7d0`, also not mine.

Untracked build scratch, safe to delete: `out/hardtrack_native/`, `out/mon/`, `out/dmc/`,
`output/*_export/`.

## Open questions
1. Should the newer `bin/SIDFactoryII_dbg.exe` (1,029,120 bytes) be committed, or restored?
2. Is the concurrent "instrument map" work expected to land before Stage C starts? It gates items 1
   and 3 in Work Remaining.
3. Promote `/tmp/sf2ii_vs_wrapper.py` into `pyscript/`? It is the comparison rung 3 actually needs
   and nothing in the repo does it.

</current_state>
