<original_task>
This file previously described a mid-arc state (HEAD `dee93ba`, "Stage B not started") and went
stale: **fourteen commits landed after it was written**, including the whole of Stage B. It is
rewritten here against HEAD `554db9c`.

The session that produced this rewrite began with "read what next" — which surfaced the staleness
— and then ran one directive:

1. "read what next" → report state. Found the handoff stale; reported the real open threads from
   `docs/players/HARDTRACK.md` § *Next steps*.
2. **"model the filter"** (chosen from those threads after I flagged it as an Opus-grade task:
   the fields that seed it are read per-voice, the engine that consumes them is global, and
   getting that ordering wrong yields a plausible, register-shaped, silently-wrong model).
3. "push and commit"
4. "update whats-next.md" ← this file

Everything before item 2 in the git log below came from earlier sessions and is summarised, not
re-litigated.
</original_task>

<work_completed>

## End state: HEAD `554db9c`, `origin/master` in sync (0/0), working tree clean.
Version **3.24.0 → 3.25.0**. Tests **2,117 → 2,284 passing**, 8 skipped, 2 xfailed, 0 failures.

### This session (3 commits)

| SHA | Subject |
|---|---|
| `1078eba` | feat(hardtrack): model the filter engine -- it is global, not per-voice |
| `a895820` | chore: bump to v3.25.0 |
| `554db9c` | docs(hardtrack): the filter registers, and the control that moved nothing |

### Earlier, and NOT covered by the previous version of this file (10 commits;
### `dee93ba` itself was already the previous file's HEAD, listed here only for continuity)

| SHA | Subject |
|---|---|
| `dee93ba` | docs: explain the last 16 Stage A losses -- and RETRACT a wrong refutation *(previous file's own HEAD)* |
| `c328c3c` | docs: update whats-next.md for the full HardTrack arc *(the stale version)* |
| `a7abd39` | feat: promote the loss-attribution tool; close the CHANGELOG/STORY gap |
| `bd25647` | docs: identify instrument fields 6, 7 and 12 -- they are the filter |
| `c81b38c` | docs(driver11): the startup frame is repo-wide -- and its published cause was wrong |
| `2c9db2d` | docs: second pass on the fields -- and bit 4 is not a hard restart |
| `57ae0a4` | feat: model the synth engine -- program-driven column 2.6% -> 100% |
| `cd41e12` | fix: field 7 is the initial cutoff, not the resonance |
| `28dcd66` | feat: Stage B -- a native build that replays the synth engine |
| `4aeae28` | docs: fold the field corrections into the canonical docs |
| `6eab1d9` | feat: track the parser-residual attribution tool |

---

## The filter engine (this session, `1078eba`)

`simulate_registers()` predicted every register group except the filter. It now predicts that
too, so **nothing in this player's SID register file is unmodelled**.

### The shape was the question, not the code

Instrument fields 6/7/12 are read **per voice** at note-on, which invites a per-voice filter
envelope. The engine that consumes them is **global**, and the player settles it in three bytes:

```
1583  DEX
1584  BMI l1589      ; all three voices done?
1586  JMP $10ef      ; no -> next voice
1589  DEC $16b2      ; <- the filter engine: ONCE PER FRAME, past the voice loop
```

Its cursor, cutoff accumulator, delta and `$D418` mode nibble live in **self-modified operands**
(`$158f`, `$15b2`, `$15b5`, `$15bd`) rather than in the per-voice block — which is exactly why an
operand scan for a table address had never named them: the addresses being written are inside the
code. `init` resets **none** of them, so they seed from the saved module image.

The same three bytes showed the voice loop runs **2, 1, 0** where the model ran **0, 1, 2**
(`$10ed LDX #$02`). Immaterial for per-voice registers; decisive for a global filter, since three
note-ons on one frame write the same operands and the last voice stepped wins.

### Measured (20 s, all 33 decodable files, byte-exact vs siddump)

| | frames | byte-exact | files n/a |
|---|---|---|---|
| cutoff `$D416` | 32,967 | **100.00%** | 0 |
| resonance + routing `$D417` | 32,967 | **100.00%** | 0 |
| mode + volume `$D418` (bits 0-6) | 9,990 | **100.00%** | **23 of 33** |

⚠️ **`$D418` is exercised by only 10 of 33 files.** The other 23 hold one constant on both sides
and are withheld by `exercised()` rather than scoring `0 == 0` — the identical shape
`docs/players/HUBBARD.md` had to retract a published "filter 100%" for, arriving in the same
player's docs one release later. **Quote the file count beside that column.**

`$D415` is excluded because the player **never writes it** — 0 stores corpus-wide — so the cutoff
is the 8-bit `$D416` alone. `$D418` bit 7 is modelled but **unverifiable here**: siddump prints
only `(D418 >> 4) & 7`.

The filter is 100% on the **unseeded** second-build files too, which the frequency column is not.
Not luck — its state lives in code operands recovered by signature, so that build's different
per-voice allocation never touches it.

### Negative controls — four bite, one does not

A uniform 100.00% across 33 files is the shape this project has twice been wrong about, so each
assumption was broken on purpose (6 s window, corpus-wide):

| deliberately broken | `$D416` | `$D417` |
|---|---|---|
| *(unmodified)* | 100.00% | 100.00% |
| cutoff clamped at 255 instead of wrapping | 24.75% | 100.00% |
| filter program never steps | 23.90% | 100.00% |
| `f12 == 0` skips instead of clearing routing | 100.00% | 48.28% |
| fields 6 and 7 swapped | 28.34% | 100.00% |
| **field-5 bit-4 re-arm gate ignored** | **100.00%** | **100.00%** |

The f6/f7 row is worth keeping: the swap costs 71 points, so the field identities are now
confirmed **by the metric**, independently of how they were read off the code.

**The last row is a negative result, recorded as one.** Ignoring the bit-4 gate changes nothing
measurable because only **21 instruments** corpus-wide set the bit and just **one** of those has a
filter to re-arm. The reading rests on the bit's only consumer in the disassembly; this corpus can
neither confirm nor refute it. `test_field5_bit4_is_not_exercised_by_this_corpus` pins both counts
so the claim can be upgraded if a file ever exercises it.

### Two corrections found by re-reading consumers, not by measuring

- **`f12 == 0` does not mean "skip the re-arm"** — it **actively clears this voice's routing bit**
  (`$13cb`, `AND $16da,x`). Reading it as a no-op costs 52 points of `$D417`.
- **The runtime volume is what `init` stores (`#$0f`), not what the image saved.** Recovered by
  searching for init's own store to the signature-derived address, because `Tribute_to_Laxity`
  shifts that block by one instruction and a fixed offset hands back a neighbouring variable.

### Files

`sidm2/hardtrack_parser.py` (5 new signatures, all **unique in 33/33**; `filter_program()`;
`filter_*` attributes) · `sidm2/hardtrack_synth.py` (`FilterFrame`, `simulate_all()`;
`simulate_registers()` keeps its exact signature) · `pyscript/hardtrack_synth_validate.py` (three
filter columns, each `exercised()`-guarded separately) · `pyscript/test_hardtrack_synth.py`
(22 → 37) · `docs/players/HARDTRACK.md` · `HARDTRACK_FILTER_AND_SLIDE.md` (marked folded-in) ·
`ACCURACY_MATRIX.md` · `CLAUDE.md` · `CHANGELOG.md` · `STORY.md`.

The signature-derived f6/f7/f12 table addresses are cross-checked against the stride-derived ones
and **agree on 33/33** — two recoveries sharing no inputs.

---

## Earlier in the arc (summarised — full detail in the commits and `docs/players/HARDTRACK.md`)

- **Stage B** (`28dcd66`, `bin/build_hardtrack_native_song.py`) — no new driver, a MoN-compatible
  shim into the shared engine. The synth programs are **CAPTURED, not modelled**, which dissolves
  every Stage A loss class at once; `$6F` legato needs no mechanism at all. All 33 files build.
  Per-frame freq raw **91.04%** / audible **88.25%** (60 s, 195 parts) — but **15,575 of 24,840
  misses are the driver's own note-on frame**, which cannot match, and **15,203 of those carry the
  SID TEST bit** (silent). Net **96.66%**. The attribution is *reported, never excluded*.
- **Synth engine** (`57ae0a4`) — the program-driven column went **2.64% → 100.00%**. It was never
  a fidelity figure; it was the score for predicting the wrong thing.
- **Parser residual resolved** (`6eab1d9`, `pyscript/hardtrack_residual.py`) — the wave program's
  arp column owns `$D400/$D401`. Of 652 lost notes, **630 predicted frame-exactly**; the same
  model also holds on **97.7% of KEPT notes**, which a model fitted to the losses would not. For
  **344 of 652 the bare table value is never written at all**. 22 (0.38%) unexplained.
- **Driver 11 startup frame** (`c81b38c`) — promoted to `docs/players/DRIVER11.md` as a repo-wide
  property, **and its published cause was found wrong on the way**: `init` overwrites the
  template's `$16CC = $40` before the first tick reads it, and `$1047` is the *stop* path. The real
  cause is the `$00` fall-through. The *effect* (one silent first frame) was always measured
  correctly. Recorded as PATTERNS.md **F6**: a self-consistent branch story assembled from the
  binary **at rest**, when the flag's value **at the call** decides the branch.
- **Loss-attribution tool promoted** (`a7abd39`) — `simulate()`'s onsets now carry `.raw`,
  `.pattern`, `.transpose`, `.pat_index` (still unpacking as the historical 2-tuple), so
  attribution is exact by construction rather than re-derived by a cursor heuristic — the heuristic
  is what produced a false refutation on `Walk_to_Soul`. A correction fell out: the `$6F` legato fix
  is **25 → 0**, not 25 → 3.
- **Fields 6/7/12 identified** (`bd25647`, `2c9db2d`) — reached independently by three passes.
  Fields 8-11 are the vibrato engine. `$63`/`$64` are slide **UP/DOWN**, not slide vs portamento —
  a continuous per-frame ramp with **no target note**, ended by the next note-on.
- **Field-5 bit 4 is NOT a hard restart** (`2c9db2d`) — the parser still exposes it as
  `hard_restart`. Field 5 is masked with only `$03`/`$10`/`$80` in 33/33; bit 4's single consumer
  gates the filter re-arm on a repeated note and reaches nothing else.

</work_completed>

<work_remaining>

Nothing requested was left incomplete. The items below are open threads recorded in
`docs/players/HARDTRACK.md` § *Next steps*; none was requested this session.

1. **Stage C — emit HardTrack's own looping programs instead of Stage B's unrolled per-note
   captures.** Stage B's part count is pure capture *density*, and `hardtrack_synth` now predicts
   the complete register file, so there is a reference model to check a structural emitter against.
   The same "structural, not trace" step MoN's Supremacy work names.
2. **Rungs 3-4 of the PLAYBOOK §4 ladder on Stage B** — an instrumented SF2II capture and a
   listening pass. **Never run.** Everything measured so far is headless, and headless metrics have
   overstated in this repo before (Galway's "37 faithful" became 30/40 under the objective metric).
3. **Map the second player build's `_RAM` variable block** (item 4b) — 15 files run unseeded at
   frequency 99.15% vs 99.98% seeded. **This session shrank the problem**: the filter is 100% on
   those files too, because its state lives in code operands, so 4b is now strictly about the
   per-voice variables. Their allocation genuinely differs (not an offset), so it needs its own
   `_RAM` table.
4. **`pyscript/sf2_to_text_exporter.py` misreads these files** ("invalid sequence address `$0000`",
   all three orderlists printed as sequence 00). The emitted SF2 is correct — verified through
   `sf2_parser`. A separate bug, **not** a HardTrack problem.
5. **Rename `hard_restart`** in `hardtrack_parser.py`. It is documented as a misnomer in two
   places but never renamed, because the tree held sibling forks' work at the time.
6. **`DriverSelector` is untouched, deliberately** — both stages are `bin/` tools.

</work_remaining>

<attempted_approaches>

### Falsified this session
1. **"The filter might be per-voice."** Settled by `$1583 DEX / BMI` — the engine is past the voice
   loop, so once per frame. Reading the *seeding* fields (per-voice) rather than the *consumer*
   (global) is what makes this a trap.
2. **"A 100% needs no defending."** Five negative controls were run precisely because it was 100%
   on 33 of 33 files. Four broke it; that is what makes the number evidence rather than a claim.

### Falsified earlier in the arc — DO NOT RE-ADOPT
3. **"Cross-pattern gate state causes the Stage A losses."** `Zakplus` v2 (worst loss) has ZERO
   ambiguous patterns; `Love_tune_2` has THREE and scores 100.0%.
4. **"The hard-restart flag causes the +1 lag."** Flags `$80`/`$00`/`$40` give identical histograms.
5. **"The PSID wrapper calls the wrong play address."** `$1006` is correct; `$1003` is silent.
6. **"Instrument fields 3/4 can be told apart by plausibility."** A "do these look like SID control
   values?" check scored BOTH readings at ~91.6%. *A plausibility test both hypotheses pass is not
   evidence.* Reading the CONSUMERS settled it.
7. **"The template's `$16CC = $40` causes the Driver 11 startup frame."** Self-consistent and wrong
   — `init` overwrites it first. See `c81b38c`.
8. **"The editor is the strongest untapped lever."** **Spent, and it was not.** `-HARDTRACK 1.PRG`
   boots (two-stage self-relocator) but its main screen is unlabelled hex whose only words are
   `SPEED`, `SONG`, `OCT` and the title. **Do not pick this lever up a third time.**

### ⚠️ A FALSIFICATION THAT WAS ITSELF FALSE
9. **"`$62`-freeze is refuted"** was published for two commits and is **RETRACTED**. It came from a
   tagger already flagged as unreliable, whose output was used anyway because the answer was
   convenient. Recording the **pattern byte-index at note time** made the test exact and reversed
   it (25× enrichment). *An unreliable instrument does not become reliable because its answer is
   convenient.*

### Measurement traps hit across the arc
10. **Matching siddump's note-NAME column scored a CORRECT model at 0.0%** — every instrument opens
    with a one-frame attack transient, so siddump reports `E-6` as the onset row for nearly every
    note. Comparing the raw frequency register turned 0% into 100% without touching the decoder.
11. **The 8-frame window was one frame too short** for arpeggiated instruments, manufacturing an
    entire "loss". The window has **no plateau**, so widening it to improve a number would be
    laundering.
12. **Validators counted unscoreable notes as misses** (window past the end of the trace).
13. **`pulse_table` was read from signature +6** (the opcode) rather than +7 (its operand), so it
    pointed outside the module on **every** file and `pulse_program()` returned zeroes that read
    exactly like a program holding the pulse width still. Nothing caught it because nothing scored
    `$D402/3`.

### Tooling gotchas
14. `retro_load` does **not** clear RAM and still reports `"loaded"`. Without a preceding
    `retro_reset` you debug the previous session's program. Compare bytes at the load address.
15. `mcp__tdz-c64-knowledge__search_docs` hung for 1800 s once; `list_docs` exceeds the token cap.
16. Grep on code files is blocked by a tokensave hook when the pattern looks like a symbol —
    override with `TOKENSAVE_DISABLE_GREP_HOOK=1`.
17. `pyscript/disasm6502.py` is in the repo and works; `DisassembledLine` has `.bytes`/`.instruction`
    /`.operand` (no `.size` — use `len(ln.bytes)`), and `d.lines` is keyed by address.

</attempted_approaches>

<critical_context>

### Reporting rules (do not violate)
- **Two fidelity columns, never averaged**: sequencer-pitch vs program-driven. *(Now largely
  historical — the register-level metric supersedes it — but any onset figure still splits.)*
- **Always quote the match window.** It has **no plateau**.
- **Stage A > parser is an ARTIFACT**, meaningful only in the LOSING direction. Quote **retention
  over parser-resolved notes: 99.69%**, not the diluted 91.34%.
- **Quote `$D418`'s file count (10 of 33)**, or it reads as three times the evidence it is.
- **Stage B: quote raw AND audible, never net alone**, and never drop the note-on frame silently.

### The measurement discipline that this arc keeps vindicating
`sidm2/fidelity_common.py` — `score_pct()` returns **None** on `n == 0`; `exercised()` returns
False when both series are the same single constant. **Both are load-bearing here**: siddump
force-displays every register on its first row, so a tune that never filters yields a full-length
non-None series of zeroes on both sides and scores a confident 100%.

### Environment
- `SID/Shogoon/` (mixed-player: **38 of 150** files) and `bin/hardtrack composer/` are **TRACKED**,
  so every test and sweep runs from a fresh clone.
- Full `pytest` run ≈ 172 s.
- Refusals are deliberate: 6 of 38 files (5 wrapped/multi-instance rips + `Dune_Cover`, PSID init
  `$4000` ≠ entry `$0900`). A refusal count needs the **right denominator** — the sweep once
  reported "117 refused" by counting non-HardTrack files in a mixed-player directory.

</critical_context>

<current_state>

| item | status |
|---|---|
| `sidm2/hardtrack_parser.py` | **complete**, 31 tests |
| `sidm2/hardtrack_synth.py` (incl. the filter) | **complete**, 37 tests |
| `bin/hardtrack_to_sf2.py` (Stage A) | **complete**, 20 tests |
| `bin/build_hardtrack_native_song.py` (Stage B) | **complete**, 22 tests |
| `pyscript/hardtrack_{validate,stagea_validate,synth_validate,attribute,residual,player_xref}.py` | **complete** |
| `docs/players/HARDTRACK.md` + `HARDTRACK_FILTER_AND_SLIDE.md` | **complete + current** |
| ACCURACY_MATRIX / CLAUDE.md / CHANGELOG / STORY | **complete + current** at v3.25.0, all four header-stamped. The matrix header and the `## [3.25.0]` heading were **missed by the bump and caught by a review pass** — CLAUDE.md names the matrix as the file a bump must re-stamp precisely because it has drifted before |
| Stage C | **not started** |
| SF2II play-test + listening pass (PLAYBOOK §4 rungs 3-4) | **not started** |
| `DriverSelector` wiring | **not done, deliberately** |

- HEAD `554db9c`, **`origin/master` in sync (0/0)**, working tree **clean**.
- Version **3.25.0**; tests **2,284 passing / 8 skipped / 2 xfailed / 0 failures**.
- `out/hardtrack/` and `output/Love_tune_2_export/` may hold untracked build scratch — safe to delete.

### Standing caveats a fresh context must not lose
- The filter is **global**, runs **once per frame after the voice loop**, and the voice order is
  **2, 1, 0**.
- **`$D418` is only exercised by 10 of 33 files** — never quote it bare.
- The **+1 frame** is a Driver 11 property affecting EVERY Stage A builder here, and its *cause* was
  corrected once already.
- **`SID/Shogoon/` is mixed-player: 38 of 150 files.**
- Across this arc **eight hypotheses were falsified and one falsification was itself false.** Every
  one failed the same way — a measurement that had not itself been verified. **Verify the
  instrument before trusting its verdict, especially when the verdict is convenient.**

</current_state>
