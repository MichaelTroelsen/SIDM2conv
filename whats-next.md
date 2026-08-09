<original_task>
The conversation opened with "read what next" (read the prior session's `whats-next.md`). That
prior handoff described a FULLY CLOSED-OUT session (v3.23.0 audio-listening tooling + calibration
+ a docs audit), so nothing was inherited. Every phase below came from an explicit instruction.

1. "read what next" → report state (prior session was closed; nothing open).
2. "what players have we converted and how many sids per palyer?"
3. "i have created a repository called sid-reference and the output has been load into the
   TDZ-knowledge. can you list the top 10 most used players by number of SID files."
4. `/subtask` "please rerun the generator" → re-run `sid-reference-project`'s coverage generator.
5. **"lets work on hardtrack composer."** + the editor PRG path + "there should be SID files in
   `SID/Shogoon` some might be other players." ← THE MAIN ARC; everything after is HardTrack.
6. (user switched the model to Opus after I flagged the escalation)
7. "bump version and continue"
8. "yes, build stage A"
9. "yes, test the gate-state hypothesis"
10. "find where the +1 frame lag comes from"
11. "push and commit"
12. "fix the $6F legato in stage A"
13. "look into the 18 unattributed losses"
14. "continue" (after a rejected tool call — re-ran the doc updates, then continued the analysis)
15. "update whats-next.md" ← this file

Nothing was self-initiated scope. All bug-fix commits arose from following up anomalies met while
executing 7-14.
</original_task>

<work_completed>

## End state: 11 commits, ALL PUSHED. `origin/master` in sync (0/0), working tree clean.
Version **3.23.0 → 3.24.0**. Tests **2,069 → 2,117 passing**, 8 skipped, 2 xfailed, 0 failures.

| SHA | Subject |
|---|---|
| `9e51306` | feat: RE the HardTrack Composer module format + validated parser |
| `b27a734` | chore: bump to v3.24.0 |
| `3a994d6` | fix: instrument stride is per-file, and fields 3/4 were swapped |
| `318e73c` | feat: Stage A -- editable Driver 11 SF2 transpile |
| `113c975` | docs: the Stage A gate-state hypothesis is FALSIFIED; real cause is a +1 frame lag |
| `c31279a` | fix: root-cause the +1 frame lag -- it is the shared Driver 11 template |
| `abc2999` | docs: session handoff (superseded by this file) |
| `72097d2` | docs: attribute the remaining Stage A losses -- 58% are the `$6F` legato |
| `991b0cb` | feat: reproduce the `$6F` legato in Stage A -- losses 43 → 21 |
| `e79e117` | fix: a measurement bug accounted for 5 of the 18 "unattributed" losses |
| `dee93ba` | docs: explain the last 16 Stage A losses -- and RETRACT a wrong refutation |

---

## Phases 1-4 (pre-HardTrack, no commits)

**Players converted** — from `docs/SF2.md`'s generated inventory: **587 songs / 2,195 SF2 files
across 10 native players** in `out/`, plus the production pipeline (Laxity 286, SF2-exported 32,
NP20). Per-player: SDI 348→348, Hubbard 61→589, DMC 57→944, Galway 40→40, MoN 26→201,
Blackbird 16→20, Deenen 15→15, Sound Monitor 11→27, Kimmel 9→9, ROMUZAK 4→4. Caveat reported: a
windowed song counts as 1 song but N files (DMC `Cant Stop` = 1 song / 114 files).

**Top-10 players by SID count** — the TDZ KB has NO ranked list (only per-player cards with a
one-line count). `search_docs` HUNG for 1800 s and was killed by the MCP idle timeout — do not
retry blind. Ran `sid-reference-project`'s own `scripts/dev/gen-coverage.js` grouping logic
locally against `data/composers/*.json`:

DMC 10,491 · GoatTracker 8,420 · Music_Assembler 6,127 · JCH_NewPlayer 3,497 · FutureComposer
3,398 · SoundMonitor/MusicMaster 1,922 · **HardTrack Composer 1,126** · Hermit/SidWizard 988 ·
Geir_Tjelta/SIDDuzz'It 979 · SoedeSoft/Soundmaster 852. Total 54,608 files / 605 tags / 540
families. **Lower bound** — HVSC `MUSICIANS/` only, `GAMES/` invisible (hence no Hubbard/Galway).

**Generator re-run**: `knowledge/COVERAGE.md` already current (520 cards, 100.0%). No diff.

---

## Phase 5+: HardTrack Composer

### Recon
- `SID/Shogoon/` (150 files) is **mixed-player**: 38 HardTrack, 78 GoatTracker, 23 DMC, 3
  Music_Assembler, 2 Hermit/FlexSID, 3 singles, 3 unidentified.
- Editor `bin/hardtrack composer/-HARDTRACK 1.PRG` (22,223 bytes, load `$0801`) is **crunched** —
  only text literals are visible; a static scan yields no table addresses. Must be RUN.
- Prior art: `sid-reference-project` KB card had load/entry/ZP but `data_format` entirely TODO.

### Format decoded (`sidm2/hardtrack_parser.py`)
- Head: `load+$000` JMP init, `+$003` JMP play, `+$006` volume, `+$007..+$01F` runtime state,
  `+$020..+$05F` 64 bytes text, `+$060` init.
- **Two variants** (play at `init+$78` or `+$7d`); a third shape once (`Tribute_to_Laxity`).
- **Orderlist**: `$00-$7F` pattern · `$80-$FC` transpose (`&$7F`, applied to the FOLLOWING
  pattern, **signed mod 128** — `$F4` = −12) · `$FD n` jump · `$FE` halt · `$FF` restart.
- **Pattern**: a byte STREAM. `$FF` end · `$67 n` rest for n rows (**this is note length**) ·
  `$63/$64` slide/porta · `$60/$61/$62` tie/gate-off/**freeze** · else note (`&$7F`) + an
  instrument byte.
- **Instrument byte**: `$00` = keep instrument AND restart its programs; **`$6F` = LEGATO**, keep
  AND do **not** restart (sets `$16CB`, which makes note-on skip the instrument reload).
  `$6F` carries **24.7% of all note events** (4,353/17,628, every decodable file).
- **Tempo**: one self-modified divider; a row lands every `speed+1` frames; the counter is a
  phase selector (0 = read row, 1 = decrement duration, else = synth only). `AND #$07` → 8 subtunes.
- **Instruments**: 13 parallel tables of `num_instruments` bytes. 0 AD→`$D405` · 1 SR→`$D406` ·
  2 pulse (HIGH nibble→`$D402`, LOW→`$D403`) · 3 pulse-sweep cursor · 4 wave/arp cursor ·
  5 flags (bit7 = program drives freq absolutely, bit4 = hard restart, bits0-1 = mode) ·
  8 nibbles→counters · 9 → param block · 10,11 synth params. **6, 7, 12 unidentified.**
- **Synth programs**: wave/arp = two parallel tables, one cursor; `$FF`→jump (target in arp col);
  **`$FE` = STOP stepping**; arp col `$00-$7F` relative semitone, `$80+` ABSOLUTE note.
  Pulse sweep = `[value][frames]`, `&$FE` magnitude, **bit 0 = direction**. Global filter sweep =
  song-level `[cutoff][delay]` + `$80 <idx>` jump → `$D416`; cursor is self-modified code and
  **`init` does NOT reset it**.
- **Freq tables**: two 96-byte tables, entry 0 = C-0 (`$0116`), PAL to within 19 cents.

### Relocation safety
The editor **patches absolute operands per file** (same table at `$198b` / `$1a35` / `$17ab` in
three tunes; two files don't load at `$1000`). Every address is recovered by byte-signature match:
`_SIG_INIT`, `_SIG_PATPTR`, `_SIG_FREQ`, `_SIG_INSTR`, `_SIG_ABSFLAG`, `_SIG_WAVEPROG`,
`_SIG_PULSEPROG`. `load + constant` is wrong by construction.

### Files
`sidm2/hardtrack_parser.py` · `bin/hardtrack_to_sf2.py` (Stage A) ·
`pyscript/hardtrack_validate.py` (parser) · `pyscript/hardtrack_stagea_validate.py` (Stage A,
`--lag`) · `pyscript/test_hardtrack_parser.py` (28) · `pyscript/test_hardtrack_to_sf2.py` (20) ·
`docs/players/HARDTRACK.md` · tracked `SID/Shogoon/` + `bin/hardtrack composer/` · rows in
ACCURACY_MATRIX / players README / CLAUDE.md.

### Two parser bugs fixed (`3a994d6`)
1. **Instrument count is PER-FILE (3-32), not 32.** Hardcoding 32 read every field but the first
   from the wrong address on 17/33 files, returning plausible bytes. Now derived two ways —
   `(flag_table−base)/5` and `(wave_table−base)/13` — and required to agree (32/33 agree;
   `Tribute_to_Laxity` flagged via `instrument_count_verified == False`). Found because
   `Altered_States_Tune_1`'s wave table sat at `base+$104` = 13×20, not a multiple of 32.
2. **Fields 3 and 4 were SWAPPED** (3 = pulse sweep, 4 = wave/arp).
   No measured figure moved — `instrument_drives_freq()` reads the signature-derived flag address,
   never through the stride. Verified by re-running.

### Stage A (`318e73c`, `991b0cb`)
Transfers exactly: notes+timing (`tempo = speed`) and the whole wave/arp table transliterated 1:1
(both formats are 2-column with a jump row AND share the col-1 rule, so indices are preserved and
each instrument keeps its own cursor). Does NOT transfer (all logged): pulse sweep, slide/porta,
global filter sweep, loop point; orderlist transpose is materialised into duplicate sequences
because the shared emitter hardcodes `$A0`.

Three bugs found by measuring, each producing a playable file:
1. **D11 note byte = the semitone index ITSELF**, not `index+1` as the shared IR's comment says —
   `index+1` put every note exactly one semitone sharp.
2. A rest before a pattern's first note emitted `+++`, gating a voice with no pitch → freq `$0000`.
3. The wave table emitted `$FF`/`$FE` as literal waveforms and masked col 1 with `$7F`, destroying
   the absolute-note encoding.
Also fixed: `Instrument.pulse_hi`/`pulse_lo` were inverted.

**`$6F` legato fix** (`991b0cb`): a `$6F` note now selects a **duplicate instrument slot whose
`wave_idx` points at the step the wave program SETTLES on** (`settled_cursor()`: the `$FF` jump
target, or the last step before `$FE`). Driver 11 always restarts a wave program and **cannot
express a tie at all**, so a second instrument is the only route. `legato_instruments()` walks
each voice's orderlist in play order so a `$6F` note inherits an instrument set in an earlier
pattern. Result: `$6F` losses **25 → 3**, plain-note losses **unchanged at 18** (the regression
check). `Love_tune_3` 93.4 → 98.3%.

### The +1 frame lag — root-caused (`c31279a`)
`$16CC` in the shipped template `G5/examples/Driver 11 Test - Arpeggio.sf2` is **`$40`**; bit 6
sends `BVS` at `$100D` into a state-init path, so Driver 11 spends its **first play call
initialising** instead of playing a row. A **template** property (the emitted file is
byte-identical to the template across `$16CC-$1702`), so **every Driver 11 Stage A build in this
repo starts one frame late**. Constant, not drift (median +1 in every song third).
`--lag 1` removes exactly that phase; default is 0.

### A measurement bug in my own validators (`e79e117`)
Notes at frames 996-997 whose 9-frame window ran past a 1,000-frame trace scored as misses.
Both validators now drop notes whose window doesn't fit, using a **`max(lag, 1)` margin** so
`--lag 0` and `--lag 1` exclude the SAME notes and stay comparable.

### Final measured state (all at an 8-frame window, 20 s)
| | notes | value |
|---|---|---|
| parser sequencer-pitch | 5,784 | **88.73%** (5132) |
| parser program-driven (field-5 bit 7) | 1,062 | **2.64%** (28) |
| Stage A `--lag 0` | 5,784 | **91.34%** |
| Stage A `--lag 1` | 5,784 | **92.08%** |
| **Stage A retention over parser-resolved notes** | 5,132 | **99.69%** (16 lost) |

8 of 33 decodable files at exactly 100.0% (parser); 5 of 38 refused.

### The last 16 losses — both groups explained (`dee93ba`)
- **`Walk_to_Soul` (5)** — `$62` sets `$16D4`, which makes the player skip the wave stepper
  thereafter; its note 21 is followed by `$62` on the next row, freezing the program before it
  ramps away so the base note written at note-on survives. Exact: notes followed by `$62` lose
  **5.49% (5/91) vs 0.22% (11/5041)** — a **25× enrichment**. Not sufficient alone (86 of 91 kept).
- **`Ritual_II_tune_2` (6)** — the decode is provably right (an independent search over EVERY
  cursor matched the instrument's own field-4 program **9/9 steps**); the program returns to base
  only at ~+16 frames, outside the window, and the original scores only off HardTrack's note-on
  base-frequency write, which Driver 11 has no equivalent of.
- 5 scattered singles.
- **Neither is fixable in Stage A** — both are Stage B material. 16 notes = 0.31%.

</work_completed>

<work_remaining>

**Nothing requested was left incomplete.** All 15 instructions were carried to pushed, verified
commits. The items below are open threads I identified and documented; none was requested.

1. **Stage B (native driver)** — not started. It is now the *named* home for the two remaining
   loss classes: Driver 11 has neither `$62`'s stepper freeze nor a pre-program base-note write.
   Would also bring the pulse sweep and the slide/portamento engine.
2. **Resolve the parser's own ~11.3% residual.** Flat over time (no drift), not explained by
   instrument flag bits 0-1/4/5/6. Untested hypothesis: `$63`/`$64` slide plus wave-program pitch
   modulation moving the register off the exact table value.
3. **Model the synth programs in `simulate()`.** `wave_program()`/`pulse_program()` decode them but
   `simulate()` does not run them — that is what would let any score cover the program-driven
   column (currently 2.64% by construction).
4. **Identify instrument fields 6, 7, 12**; confirm the global filter sweep's un-reset cursor.
5. **Run the editor under RetroDebugger** — still the strongest untapped lever for fields 6/7/12
   and the slide semantics. The PRG is crunched, so it must be RUN and RAM dumped.
6. **`pyscript/sf2_to_text_exporter.py` misreads these files** (reports "invalid sequence address
   $0000", prints all three orderlists as sequence 00). The emitted file is correct — verified by
   reading orderlist bytes through `sf2_parser`. Possibly a real bug in that exporter, worth
   filing separately. NOT a HardTrack problem.
7. **Consider documenting the Driver 11 `$16CC` startup frame repo-wide** — it affects every Stage
   A builder here and no other player's doc mentions it.
8. **`--lag` is Stage-A-only.** If another player's Stage A gets the same treatment, that flag (or
   the finding behind it) should be shared rather than reimplemented.

</work_remaining>

<attempted_approaches>

### Falsified hypotheses — DO NOT RE-ADOPT
1. **"Cross-pattern gate state causes the Stage A losses."** FALSIFIED: `Zakplus` v2 (worst loss)
   has ZERO ambiguous patterns; `Love_tune_2` has THREE and scores 100.0% everywhere. Pinned by
   `test_pattern_gate_ambiguity_does_not_predict_stage_a_loss`.
2. **"The hard-restart flag causes the +1 lag."** FALSIFIED: flags `$80`/`$00`/`$40` give
   identical offset histograms and scores.
3. **"The PSID wrapper calls the wrong play address."** FALSIFIED: `$1006` is correct; forcing
   `$1003` gives TOTAL SILENCE.
4. **"Instrument fields 3/4 can be told apart by plausibility."** A check asking "do these bytes
   look like SID control values?" scored BOTH readings at ~91.6% — it discriminated NOTHING.
   Reading the CONSUMERS settled it. *A plausibility test both hypotheses pass is not evidence.*
5. **"The note-on base-frequency write explains the residual losses."** Enrichment only, not a
   separation: 44% of lost vs 25% of kept notes had an early (d≤2) original hit, and 1,281 kept
   notes also hit early. Contributing factor, not mechanism.

### ⚠️ A FALSIFICATION THAT WAS ITSELF FALSE
6. **"`$62`-freeze is refuted"** was published in ACCURACY_MATRIX.md and HARDTRACK.md for two
   commits and is **RETRACTED**. It came from a tagger that mapped onsets onto pattern events with
   a cursor heuristic, which mis-aligned on the exact file in question — and I had already flagged
   that tagger as unreliable and used its output anyway. Recording the **pattern byte-index at note
   time** made the test exact and reversed the result (25× enrichment). Lesson: an unreliable
   instrument does not become reliable because its answer is convenient.

### Measurement traps hit (each produced a plausible-but-wrong number)
7. **Matching siddump's note-NAME column scored a CORRECT model at 0.0%**, three files running —
   every instrument opens with a one-frame attack transient, so siddump reports `E-6` as the onset
   row for nearly every note. Comparing the raw frequency register turned 0% into 100% on the first
   file *without changing a line of the decoder*.
8. **The 8-frame window was one frame too short** for arpeggiated instruments, manufacturing the
   entire Zakplus/Hopscotch "loss". The window has NO plateau, so widening it to improve a number
   would be laundering — measured the sensitivity and published it instead.
9. **Stage A scoring above the parser is an artifact** (Stage A is simpler, so it hits notes the
   modulated original misses).
10. **My own validators counted unscoreable notes as misses** (window past the end of the trace) —
    5 of 18 "losses".

### Dead ends / tooling failures
11. `mcp__tdz-c64-knowledge__search_docs` **hung for 1800 s**; `list_docs` exceeds the token cap
    (read the persisted file). `get_document_by_card_id` + `get_document` work.
12. `tools/SIDdecompiler.exe` leaves "unreferenced data" holes on untaken branches — wrote a linear
    disassembler instead.
13. A heredoc containing a Python triple-quoted string collided with `<<'PYEOF'` (SyntaxError) —
    use the Edit tool for those.
14. Naming a scratchpad file `dis.py` **shadowed the stdlib `dis` module** → renamed `dis6502.py`.

### Considered but not pursued
- Extending `galway_driver11_emitter` to emit `$A0+transpose` — rejected, shared by 8 players.
- Clearing `$16CC` to remove the startup frame — rejected, the driver would never initialise.

</attempted_approaches>

<critical_context>

### Reporting rules (do not violate)
- **Two fidelity columns, never averaged**: sequencer-pitch (88.73%) vs program-driven (2.64%,
  instrument field 5 bit 7). The second is the unimplemented synth engine; a pooled figure would
  drift with a tune's drum/melody mix.
- **Always quote the match window.** It has NO plateau (parser 81.06→93.17%, Stage A 37.05→95.79%
  for windows 4→24). All figures use **8 frames**.
- **Stage A > parser is an ARTIFACT**, meaningful only in the LOSING direction.
- The most informative Stage A number is **retention over parser-resolved notes: 99.69%**, not the
  diluted 91.34%.

### The Driver 11 startup frame (repo-wide, not HardTrack-specific)
Template `G5/examples/Driver 11 Test - Arpeggio.sf2` carries `$16CC = $40`; bit 6 → `BVS $1047` at
`$100D` → the FIRST play call goes to a state-init path. **Every Driver 11 Stage A build in this
repo starts one frame late.** Constant phase, inaudible, only breaks measurement.

### Driver 11 conventions learned the hard way
- **Note byte = the C-0 semitone index ITSELF**, not `index+1`, despite the comment in
  `sidm2/galway_to_driver11.py`.
- Wave table col 1: `$00-$7F` relative semitone, **`$80+` absolute note** — same rule as
  HardTrack's arp column, so it transliterates verbatim. Masking with `$7F` destroys it.
- `$7E` (`+++`) gates a voice; with no pitch yet it plays frequency `$0000`.
- A wrapped SF2's PSID play address is `$1006`, NOT `$1003` (which is silent).
- **Runtime Driver 11 cannot parse `$90-$9F` tie durations** — editor-only, desyncs the driver;
  `test_no_tie_bytes_emitted` locks them out. That is why `$6F` legato needed a second instrument.

### Environment / tooling
- `SID/Shogoon/` and `bin/hardtrack composer/` are TRACKED, so tests run from a clone.
- `tools/player-id.exe "GLOB"` — pass the glob as ONE quoted argument for the summary table.
- Grep on code files is blocked by a tokensave hook when the pattern looks like a symbol; override
  with `TOKENSAVE_DISABLE_GREP_HOOK=1`.
- Scratchpad helpers (NOT in the repo, WILL VANISH):
  `<scratchpad>/dis6502.py` (linear 6502 disassembler) and
  **`<scratchpad>/gatetest.py`** — the instrumented sequencer walk that records, per onset,
  `(frame, voice, note, instr, pattern, transpose, RAW INSTRUMENT BYTE, PATTERN BYTE-INDEX)`.
  Those last two fields are what made the `$6F` and `$62` attributions exact. **Worth promoting
  into the repo** if this work continues — every attribution in this arc depended on it.
- Full `pytest` run ≈ 160 s.

### Refusals are deliberate
`HardTrackModule` raises `HardTrackError` for 5 of 38 files (4 multi-instance rips: Eternal,
Fruitmania, Miecze_Valdgira_2, Zone_of_Darkness; 1 PSID-init mismatch: Commercial_Fake). Before
the guard the simulator ran away, emitting a note on EVERY frame of EVERY voice (2,997 phantom
onsets against the wrong song).

### Sources
- `sid-reference-project` KB card `knowledge/players/hardtrack-composer.md` (authorship, CSDb
  74928). Its `data_format` was entirely TODO before this arc.
- `docs/players/PLAYBOOK.md` §1 (RE → Stage A → Stage B), §3 (SF2II caps), §4 (fidelity ladder).
- `sidm2/fidelity_common.py` — `score_pct` returns None on n=0, `exercised()` guards constant
  series. Both used.

</critical_context>

<current_state>

### Deliverables
| item | status |
|---|---|
| `sidm2/hardtrack_parser.py` | **complete**, 28 tests |
| `bin/hardtrack_to_sf2.py` (Stage A, incl. `$6F` legato) | **complete**, 20 tests |
| `pyscript/hardtrack_validate.py` / `hardtrack_stagea_validate.py` | **complete**, both boundary-guarded |
| `docs/players/HARDTRACK.md` | **complete + current**, incl. the retraction |
| ACCURACY_MATRIX / players README / CLAUDE.md rows | **complete + current** |
| CHANGELOG / STORY v3.24.0 | **complete** (written at the RE stage; Stage A is NOT in them) |
| Stage B (native driver) | **not started** |
| `DriverSelector` wiring | **not done, deliberately** — Stage A is a `bin/` tool |

### Repo
- HEAD = `dee93ba`, **`origin/master` in sync (0/0)**, working tree **clean**.
- Version **3.24.0**; tests **2,117 passing / 8 skipped / 2 xfailed / 0 failures**.
- `out/hardtrack/` and `output/Love_tune_2_export/` hold untracked build scratch — safe to delete.

### ⚠️ One known documentation gap
`CHANGELOG.md` and `STORY.md`'s v3.24.0 entries were written at the **RE stage** (`b27a734`) and
describe the parser only. Everything since — Stage A, the `$6F` legato fix, the `$16CC` lag
root-cause, the two validator fixes — is documented in `docs/players/HARDTRACK.md` and
`ACCURACY_MATRIX.md` but **not** in CHANGELOG/STORY. Either amend those entries or fold the work
into a v3.25.0 entry at the next bump.

### Open questions for the user
1. Next thread: **Stage B**, the parser's ~11.3% residual, modelling the synth programs in
   `simulate()`, or RetroDebugger on the editor?
2. Should `CHANGELOG.md`/`STORY.md` v3.24.0 be amended to cover Stage A (see the gap above)?
3. Should `gatetest.py` be promoted from the scratchpad into `pyscript/`?

### Standing caveats a fresh context must not lose
- Never average the two fidelity columns; never quote a percentage without its window.
- Stage A > parser is an artifact; quote **retention (99.69%)**, not 91.34%.
- The `+1` frame is a Driver 11 **template** property affecting EVERY Stage A builder here.
- `SID/Shogoon/` is mixed-player: 38 of 150 files.
- **Five hypotheses were falsified this arc and one falsification was itself false.** Every one
  failed the same way — a measurement that had not been verified. Verify the instrument before
  trusting its verdict, especially when the verdict is convenient.

</current_state>
