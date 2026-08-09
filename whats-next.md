<original_task>
The conversation opened with "read what next" (read the prior session's `whats-next.md` handoff).
That prior handoff described a FULLY CLOSED-OUT session — v3.23.0 audio-listening tooling +
calibration + a docs audit, everything committed and pushed, nothing open. So there was no
inherited work; every phase below came from an explicit user instruction in this conversation.

Sequence of user instructions, verbatim scope:

1. "read what next" → read the handoff, report state. (No work; prior session was closed.)
2. "what players have we converted and how many sids per palyer?" → report from the repo's own
   generated build indices.
3. "i have created a repository called sid-reference and the output has been load into the
   TDZ-knowledge. can you list the top 10 most used players by number of SID files."
4. `/subtask` "please rerun the generator" → re-run `sid-reference-project`'s coverage generator.
5. **"lets work on hardtrack composer."** + the editor PRG path
   (`bin/hardtrack composer/-HARDTRACK 1.PRG`) + "there should be SID files in
   `SID/Shogoon` some might be other players." ← THE MAIN ARC. Everything after this is HardTrack.
6. (user switched model to Opus after I flagged the escalation)
7. "bump version and continue"
8. "yes, build stage A"
9. "yes, test the gate-state hypothesis"
10. "find where the +1 frame lag comes from"

Nothing was self-initiated scope. The two bug-fix commits (`3a994d6`, and the corrections inside
`318e73c`/`c31279a`) arose from following up anomalies encountered while executing 7–10, not from
inventing new work.
</original_task>

<work_completed>

## End state: 6 commits, all on `master`, NONE PUSHED (0 behind / 6 ahead of `origin/master`).
Version **3.23.0 → 3.24.0**. Tests **2,069 → 2,110 passing**, 8 skipped, 2 xfailed, 0 failures.
Working tree clean except `whats-next.md` (this file).

| SHA | Subject |
|---|---|
| `9e51306` | feat(hardtrack): RE the HardTrack Composer module format + validated parser |
| `b27a734` | chore: bump to v3.24.0 (HardTrack Composer RE stage) |
| `3a994d6` | fix(hardtrack): instrument stride is per-file, and fields 3/4 were swapped |
| `318e73c` | feat(hardtrack): Stage A -- editable Driver 11 SF2 transpile |
| `113c975` | docs(hardtrack): the Stage A gate-state hypothesis is FALSIFIED; real cause is a +1 frame lag |
| `c31279a` | fix(hardtrack): root-cause the +1 frame lag -- it is the shared Driver 11 template |

---

## Phase 1–4 (pre-HardTrack, no commits)

**Players converted / SID counts** — answered from `docs/SF2.md`'s generated inventory
(`pyscript/gen_sf2_index.py`) and `docs/SID_TO_SF2_CONVERSIONS.md`. Headline: **587 songs /
2,195 SF2 files across 10 native players** in `out/`, plus the production pipeline (Laxity 286,
SF2-exported round-trip 32, NP20). Per-player: SDI 348→348, Hubbard 61→589, DMC 57→944, Galway
40→40, MoN 26→201, Blackbird 16→20, Deenen 15→15, Sound Monitor 11→27, Kimmel 9→9, ROMUZAK 4→4.
Caveat surfaced and reported: a long tune split into windowed "parts" counts as 1 song but N
files (DMC `Cant Stop` = 1 song / 114 files), and some players count subtunes as separate songs.

**Top-10 players by SID-file count** — the TDZ knowledge base has NO single doc with this ranking
(only per-player cards each carrying a one-line count). `mcp__tdz-c64-knowledge__search_docs`
HUNG for 1800s and was killed by the MCP idle timeout — do not retry it blind. Instead I ran the
`sid-reference-project`'s OWN aggregation logic (`scripts/dev/gen-coverage.js`, family grouping
copied exactly) against `data/composers/*.json` locally:

| # | family | files | | # | family | files |
|--:|---|--:|---|--:|---|--:|
| 1 | DMC | 10,491 | | 6 | SoundMonitor/MusicMaster | 1,922 |
| 2 | GoatTracker | 8,420 | | 7 | HardTrack Composer | 1,126 |
| 3 | Music_Assembler | 6,127 | | 8 | Hermit/SidWizard | 988 |
| 4 | JCH_NewPlayer | 3,497 | | 9 | Geir_Tjelta/SIDDuzz'It | 979 |
| 5 | FutureComposer | 3,398 | | 10 | SoedeSoft/Soundmaster | 852 |

Total 54,608 tagged files / 605 raw tags / 540 families. **Lower bound** — the dump covers HVSC's
`MUSICIANS/` tree only, so `GAMES/` is invisible (which is why Hubbard/Galway/Laxity/MoN do not
appear despite being SIDM2's headline players).

**Generator re-run** (`/subtask`): `node scripts/dev/gen-coverage.js` in
`C:\Users\mit\claude\sid-reference-project` → `knowledge/COVERAGE.md` was already up to date
(520 cards cover 54,607 of 54,608 files = 100.0%; 1 uncarded family, 1 file). No diff, nothing
committed.

---

## Phase 5+: HardTrack Composer (the whole rest of the session)

### Recon
- `tools/player-id.exe "SID/Shogoon/*.sid"` on the 150-file folder: **38 HardTrack_Composer**,
  78 GoatTracker_V2.x, 23 DMC, 3 Music_Assembler, 2 Hermit/FlexSID, 1 each Chubrocker_V3.x /
  Comer/Digi / JammicroV1, 3 unidentified. **The folder is mixed-player — never assume otherwise.**
- The editor PRG (`bin/hardtrack composer/-HARDTRACK 1.PRG`, 22,223 bytes, load `$0801`) is
  **crunched**. The player template and the two default text lines (`PLAYER 1.0 BY
  LONGHAIR/ELYSIUM!`, `- MUSIC DONE BY YOU! -`) appear as literal runs, but the surrounding code
  is packed — a static scan gives no table addresses. Using it requires running it and dumping RAM.
- Prior art found in the separate `sid-reference-project` KB card
  (`knowledge/players/hardtrack-composer.md`): load `$1000`, ZP `$FB-$FC`, entry `+0/+3`,
  single-speed, **`data_format` entirely TODO**. That card also wrongly implies init/play offsets
  vary because a metadata block varies; in fact they are essentially fixed (see below).

### RE method
`tools/SIDdecompiler.exe` gave a trace-based disassembly with "unreferenced data" holes, so I
wrote a linear disassembler (scratchpad `dis6502.py`) for full coverage of `$1060-$16A3`, then
read the player code directly and cross-checked every table against the actual bytes.

### Format decoded (all in `sidm2/hardtrack_parser.py`)
- **Module head**: `load+$000` JMP init, `+$003` JMP play, `+$006` volume, `+$007..+$01F` runtime
  per-voice state, `+$020..+$05F` 64 bytes of display text (2×32), `+$060` init.
- **Two player variants**, differing by 5 bytes in init: play at `init+$78` (16 files) or
  `init+$7d` (17). A third shape once (`Tribute_to_Laxity`, init at `load+$061`).
- **Orderlist**: `$00-$7F` pattern · `$80-$FC` transpose (`&$7F`, applied to the FOLLOWING
  pattern) · `$FD n` jump to orderlist index n · `$FE` halt voice · `$FF` restart from 0.
  Transpose is `(note+t)&$7F` = **signed mod 128** (`$F4` → −12 semitones, not +116).
- **Pattern**: a byte STREAM, not a row grid. `$FF` end · `$67 n` rest for n rows (this is how
  note LENGTH is expressed) · `$63 a`/`$64 a` slide/porta · `$60`/`$61`/`$62` tie/gate-off/reset
  (each still consumes an instrument byte) · anything else = note (`&$7F`) followed by an
  instrument byte. Instrument byte `$00` = keep current, which is why the editor writes `$80` for
  instrument 0.
- **Tempo**: one self-modified global divider (operand of `lda #` at play+$F9-ish, reload operand
  at play+$E2-ish), reloaded from an 8-entry per-subtune speed table. **A row lands every
  `speed+1` frames.** Within a beat the counter is a phase selector: 0 = read a row, 1 = decrement
  note duration, else = run synth programs only. `init` does `AND #$07` → **8 subtunes max**.
- **Instruments**: 13 parallel tables, each `num_instruments` bytes. Confirmed fields:
  0 AD→`$D405` · 1 SR→`$D406` · 2 pulse (HIGH nibble→`$D402`, LOW nibble→`$D403`) ·
  3 pulse-sweep cursor · 4 waveform/arpeggio cursor · 5 flags (bit7 = program drives freq
  absolutely, bit4 = hard restart, bits0-1 = mode) · 8 nibbles→two synth counters ·
  9 → per-voice param block · 10,11 synth params. **Fields 6, 7, 12 unidentified** (deliberately
  unnamed in `Instrument.raw`).
- **Synth programs**: waveform/arp = two parallel tables one cursor, `$FF`→jump (target in arp
  col), **`$FE` = STOP stepping** (sets a flag that skips the stepper thereafter, holding the last
  waveform); arp col `$00-$7F` = relative semitone added to note, `$80+` = ABSOLUTE note.
  Pulse sweep = `[value][frames]`, `value&$FE` = magnitude, **bit 0 = direction** (0 up, 1 down).
  Global filter sweep = song-level `[cutoff][delay]` with `$80 <idx>` jump → `$D416`; its cursor
  is self-modified code and **`init` does NOT reset it**.
- **Frequency tables**: two 96-byte tables (lo, hi) inside the player code, entry 0 = C-0
  (`$0116`). Verified PAL to within 19 cents (worst at note 95). 2 distinct tables in the corpus.

### Relocation safety (load-bearing)
The player code is fixed-layout but the editor **patches the absolute operands per file** — the
same table is at `$198b` in `Love_tune_2`, `$1a35` in `Teekkno`, `$17ab` in `Jazzloor`; two files
don't load at `$1000` (`Timsoft_Intro` `$4000`, `Trance` `$a000`). Every address is recovered by
byte-signature match against the player's own code: `_SIG_INIT`, `_SIG_PATPTR`, `_SIG_FREQ`,
`_SIG_INSTR`, `_SIG_ABSFLAG`, `_SIG_WAVEPROG`, `_SIG_PULSEPROG`. `load + constant` is wrong by
construction.

### Files created
- `sidm2/hardtrack_parser.py` — parser + `simulate()` sequencer state machine.
- `pyscript/hardtrack_validate.py` — parser validator (byte-exact freq register vs siddump).
- `pyscript/hardtrack_stagea_validate.py` — Stage A validator (+ `--lag N`).
- `bin/hardtrack_to_sf2.py` — Stage A Driver 11 transpile.
- `pyscript/test_hardtrack_parser.py` (28 tests), `pyscript/test_hardtrack_to_sf2.py` (13 tests).
- `docs/players/HARDTRACK.md`.
- Tracked `SID/Shogoon/` (150 files) + `bin/hardtrack composer/` — repo convention is to track
  corpora (1,379 SIDs) and editor binaries (49 PRG/D64), and it makes the tests run from a clone.
- Rows added to `docs/reference/ACCURACY_MATRIX.md`, `docs/players/README.md`, CLAUDE.md's
  Known Limitations.

### Measurement — the parser
Metric: a modelled note-on counts when the player's OWN freq-table value for that note reaches
`$D400/$D401` within 8 frames. **Reported as two columns, never averaged:**

| | notes | match |
|---|---|---|
| sequencer-pitch (instrument field 5 bit 7 CLEAR) | 5,846 | **88.39%** |
| program-driven (bit 7 SET) | 1,074 | **2.61%** |

The split is justified by a sharply BIMODAL per-instrument breakdown: 180 (file,instrument) pairs
at 99.49%, 76 at 0.61%, only 19 in between. 8 of 33 decodable files at exactly 100.0%.
5 of 38 files REFUSED (4 multi-instance rips, 1 PSID init ≠ module entry).
Residual characterised: flat 87.1–90.2% across all ten 100-frame buckets (no drift); flag bits
0-1/4/5/6 each tested, none partitions it. Remaining hypothesis (slide + wave-program pitch
modulation) written down AS a hypothesis, untested.

### Version bump (`b27a734`)
`sidm2/__init__.py` 3.23.0→3.24.0, CHANGELOG entry, STORY entry + current-version line,
ACCURACY_MATRIX re-stamped, CLAUDE.md header. Also corrected the matrix's provenance paragraph,
which said "That release altered no conversion path" against a `3e42a8c..HEAD` range that would
have silently absorbed this release into a claim only verified for v3.23.0 — now pinned to
`3e42a8c..0498d05` with a separate v3.24.0 sentence.

### Two parser bugs found and fixed (`3a994d6`)
1. **Instrument count is PER-FILE (3–32), not 32.** The 13 tables are `num_instruments` bytes
   each. The shipped parser hardcoded 32, so on 17 of 33 files every field but the first was read
   from the wrong address — returning entirely plausible bytes. Now derived two ways and required
   to agree: `(flag_table−base)/5` and `(wave_table−base)/13`; they agree on 32/33 files;
   `Tribute_to_Laxity` does not and is flagged via `instrument_count_verified == False`.
   Found because `Altered_States_Tune_1`'s wave table sat at `base+$104` — not a multiple of 32,
   but exactly 13×20.
2. **Instrument fields 3 and 4 were SWAPPED** (3 = pulse sweep, 4 = waveform/arp).
   *No measured figure moved* — `instrument_drives_freq()` reads the flag table at its
   signature-derived address, never through the broken stride, so the headline was insulated.
   Verified by re-running, not assumed.

### Stage A (`318e73c`)
`bin/hardtrack_to_sf2.py` → editable Driver 11 SF2 via the shared `GalwayDriver11Song` +
`galway_driver11_emitter`. Transfers exactly: notes+timing (`tempo = speed`, one row to one row)
and the whole waveform/arpeggio table transliterated 1:1 (both formats are 2-column with a jump
row AND share the col-1 rule `$00-$7F` relative / `$80+` absolute, so indices are preserved and
each instrument keeps its own cursor as `wave_idx`). Max wave table in corpus 253 vs the 256 cap.
Does NOT transfer (all logged): pulse sweep, slide/porta, global filter sweep, loop point.
Orderlist transpose is MATERIALISED into duplicate sequences because the shared emitter hardcodes
`$A0` (transpose 0) and changing it would touch a path 8 other players use.

Three bugs found by measuring, each of which produced a playable file:
1. The **Driver 11 note byte is the semitone index ITSELF**, not `index+1` as the shared IR's own
   comment says — `index+1` put every note exactly one semitone sharp (`$0F82` vs `$0E93`).
2. A rest before a pattern's first note was emitted as `+++`, gating a voice with no pitch →
   Driver 11 plays frequency `$0000`. Voices 1 and 2 were mute in the first build.
3. The wave table emitted `$FF`/`$FE` as literal `$D404` waveforms and masked col 1 with `$7F`,
   destroying the absolute-note encoding.
Also fixed: `Instrument.pulse_hi`/`pulse_lo` were inverted.

Stage A: **90.64%** vs the parser's 88.39% at the same 8-frame window.
⚠️ Stage A scoring ABOVE the parser is a **measurement artifact, not an improvement** — where the
original's wave program bends a note off the exact table value the original MISSES and Stage A,
which doesn't port that modulation, HITS. Comparison is only meaningful in the LOSING direction.
6 of the 8 parser-100% files are Stage A 100.0%.

### Gate-state hypothesis FALSIFIED (`113c975`)
The `318e73c` docs named a hypothesis (per-sequence vs per-voice gate state) for the
Zakplus/Hopscotch losses. Tested and **wrong on both sides**: Zakplus voice 2 (worst loss, 63.5%)
has ZERO ambiguous patterns; Love_tune_2 has THREE and scores 100.0% on every voice including
100% inside those patterns. Added `test_pattern_gate_ambiguity_does_not_predict_stage_a_loss` to
pin both halves so the dead hypothesis is not re-adopted.
Real cause identified instead: a systematic **+1 frame lag** (68.9% of notes; +0 on 8.9%), with
the two renders playing the IDENTICAL arpeggio one frame apart.
Also published **window sensitivity**: NO plateau — parser 81.06→93.17%, Stage A 37.05→95.79% as
the window widens 4→24 frames. So no window is "correct" and every figure must quote its window.

### +1 frame lag ROOT-CAUSED (`c31279a`)
`$16CC` in the shipped template `G5/examples/Driver 11 Test - Arpeggio.sf2` is **`$40`**:
```
1006: lda #$00 / 1008: bit $16cc / 100b: bmi $1051 (not taken) / 100d: bvs $1047 (TAKEN)
```
Driver 11 spends its **first play call initialising its own state** (clearing `$16CD..$1740`)
instead of playing a row. It is a **template** property — the emitted file is byte-identical to
the template across `$16CC-$1702` (15 non-zero bytes, same values), the region CLAUDE.md already
flags as "must stay clear". **It applies to every Driver 11 Stage A build in this repo.**
Constant, not drift: median +1 in every song third (68.6/71.5/66.8%).
`--lag 1` added to the Stage A validator (**default 0**, so the reported figure is unchanged):

| file | Stage A | `--lag 1` | parser |
|---|---|---|---|
| Zakplus | 87.6% | **99.0%** | 99.0% |
| Hopscotch | 56.8% | **72.2%** | 72.2% |
| Love_tune_3 | 93.4% | 93.4% | 99.2% |
| Walk_to_Soul | 57.6% | 57.6% | 63.5% |

Zakplus and Hopscotch land EXACTLY on the parser — they were never losses.
Corpus-wide the correction is worth only **+0.62 pp** (90.64→91.26%). My own prior estimate of
"~91.5%" was superseded by the measured 91.26%.

</work_completed>

<work_remaining>

**Nothing requested was left incomplete.** Every instruction 1–10 was carried to a verified,
committed state. The items below are open threads I identified and documented, none requested.

1. **PUSH THE 6 COMMITS.** `origin/master` is 6 behind. The user has not asked me to push and I
   have not. This is the only "pending" mechanical action.

2. **`whats-next.md` was already modified before this session began** (uncommitted, from the
   prior session's close-out). I left it alone all session and flagged it twice; this file now
   overwrites it. Decide whether to commit it.

3. **Explain the two GENUINE Stage A losses** — the sharpest open question, now cleanly isolated:
   - `Love_tune_3` 93.4% vs parser 99.2% (−5.8 pp)
   - `Walk_to_Soul` 57.6% vs parser 63.5% (−5.9 pp)
   Both are **unaffected by `--lag`**, so the Driver 11 startup phase is NOT the cause. Everything
   else (gate state, hard-restart flag, wrapper play address, caps) has been tested and refuted.
   Start with a per-voice + per-instrument breakdown as in
   `scratchpad/gatetest.py`'s `report()`.

4. **Resolve the parser's own 11.6% residual.** Flat over time (no drift), not explained by
   instrument flag bits 0-1/4/5/6. Untested hypothesis: the `$63`/`$64` slide/portamento commands
   plus wave-program pitch modulation moving the register off the exact table value. Instrument
   the slide commands.

5. **Identify instrument fields 6, 7, 12** and confirm the global filter sweep's un-reset cursor
   on hardware.

6. **Model the synth programs in `simulate()`.** `wave_program()` / `pulse_program()` decode them
   but `simulate()` does not run them — doing so is what would let a score cover the
   program-driven column at all (currently 2.61% by construction).

7. **Stage B** (native driver) — not started. Would need the pulse sweep + slide engines.

8. **Run the editor under RetroDebugger.** Still the strongest untapped lever for fields 6/7/12
   and slide semantics: load `-HARDTRACK 1.PRG`, build a one-note tune, diff memory. The PRG is
   crunched so it MUST be run, not scanned.

9. **`pyscript/sf2_to_text_exporter.py` misreads these files** — reports "invalid sequence address
   $0000" and prints all three orderlists as sequence 00. The emitted file is correct (verified by
   reading orderlist bytes through `sf2_parser`). Possibly a real bug in that exporter worth
   filing separately; NOT a HardTrack problem.

10. **Consider whether the Driver 11 `$16CC` startup frame should be documented repo-wide** — it
    affects every Stage A builder here, not just HardTrack, and no other player's doc mentions it.

</work_remaining>

<attempted_approaches>

### Falsified hypotheses — DO NOT RE-ADOPT
1. **"Cross-pattern gate state causes the Stage A losses"** (one pattern = one sequence, so
   "is this voice sounding at pattern start" is per-sequence while the player decides per voice).
   FALSIFIED: Zakplus v2 (worst loss) has ZERO ambiguous patterns; Love_tune_2 has THREE and
   scores 100.0% everywhere. Pinned by
   `test_pattern_gate_ambiguity_does_not_predict_stage_a_loss`.
2. **"The instrument hard-restart flag causes the +1 lag."** FALSIFIED: rebuilding with flags
   `$80`, `$00`, `$40` gives identical offset histograms AND identical scores.
3. **"The PSID wrapper calls the wrong play address."** FALSIFIED: `$1006` is correct. Forcing
   `play=$1003` (the other JMP at the module head) gives TOTAL SILENCE.
4. **"Instrument fields 3/4 can be told apart by plausibility."** A check asking "do the bytes
   these cursors point at look like SID control values?" scored BOTH readings at ~91.6% — it
   discriminated NOTHING. Reading the CONSUMERS settled it. Generalisable lesson: a plausibility
   test that both hypotheses pass is not evidence.

### Measurement traps hit (each produced a plausible-but-wrong number)
5. **Matching siddump's note-NAME column scored a CORRECT model at 0.0%**, three files running.
   Every HardTrack instrument opens with a one-frame attack transient, so siddump reports `E-6` as
   the onset row for essentially every note whatever its pitch. The model's frames were already
   exactly right, offset by a constant 3 frames of attack. Switching to a byte-exact comparison
   against the raw frequency register turned 0% into 100% on the first file **without changing a
   line of the decoder**. Same class as the documented Matt Gray slide traps.
6. **The 8-frame match window was one frame too short** for arpeggiated instruments, which is what
   manufactured the entire Zakplus/Hopscotch "loss". The window has NO plateau, so widening it to
   improve a number would be laundering — measured the sensitivity and published it instead.
7. **Stage A scoring above the parser is an artifact**, not an improvement (Stage A is simpler, so
   it hits notes the modulated original misses). Documented everywhere the number appears.

### Dead ends / tooling failures
8. `mcp__tdz-c64-knowledge__search_docs` **hung for 1800 s** and was killed by the MCP idle
   timeout. `list_docs` returns 156 KB (over the token cap) and must be read from the persisted
   file. `get_document_by_card_id` + `get_document` work fine. The KB has **no ranked player list**
   — only per-player cards with a one-line count each.
9. `tools/SIDdecompiler.exe` leaves "unreferenced data" holes on untaken branches; fine for a
   first look, insufficient for complete coverage. Wrote a linear disassembler instead.
10. A heredoc containing a Python triple-quoted string collided with the outer `<<'PYEOF'` and
    produced a SyntaxError — used the `Edit` tool for that patch instead.
11. Naming a scratchpad file `dis.py` **shadowed the stdlib `dis` module** and broke
    `import dataclasses` → renamed to `dis6502.py`.

### Considered but not pursued
- Extending `galway_driver11_emitter` to emit `$A0+transpose` in orderlists (would remove the
  duplicate transposed sequences) — rejected: it is a shared path used by 8 other players.
- Clearing `$16CC` in the emitted file to remove the startup frame — rejected: the driver would
  never initialise its state. The frame is harmless (uniform 20 ms shift).
- Chasing the Stage A losses before landing the parser fix — deliberately inverted; the stride bug
  would have silently corrupted Stage A's instrument records.

</attempted_approaches>

<critical_context>

### The two-column rule (do not violate)
HardTrack fidelity is reported as **two columns that must never be averaged**: sequencer-pitch
notes (88.39%) and program-driven notes (2.61%, instrument field 5 bit 7). The second is the
unimplemented synth engine, not a decode error — those instruments set `$D400/$D401` from their
own wave program, so the sequencer note CANNOT appear there. A pooled figure would also drift with
a tune's drum/melody mix for reasons unrelated to the decode.

### Always quote the window
The match window has **no plateau** (parser 81.06→93.17%, Stage A 37.05→95.79% for windows 4→24).
No window is "correct". All reported figures use **8 frames**. `--lag 1` on the Stage A validator
removes the separately-established Driver 11 startup phase and is legitimate BECAUSE the mechanism
was identified independently — it is not window-widening.

### The Driver 11 startup frame (repo-wide, not HardTrack-specific)
The shipped template `G5/examples/Driver 11 Test - Arpeggio.sf2` carries `$16CC = $40`. Bit 6 →
`BVS $1047` at `$100D` → the driver's FIRST play call goes to a state-init path (clears
`$16CD..$1740`) instead of playing a row. **Every Driver 11 Stage A build in this repo starts one
frame late.** Constant phase, not drift; inaudible; only breaks measurement.

### Driver 11 conventions learned the hard way
- **Note byte = the C-0 semitone index ITSELF**, not `index+1`, despite the comment in
  `sidm2/galway_to_driver11.py`. `index+1` = every note one semitone sharp.
- Wave table col 1: `$00-$7F` relative semitone, **`$80+` absolute note** — same rule as
  HardTrack's arp column, so it transliterates verbatim. Masking with `$7F` destroys it.
- `$7E` (`+++`) gates a voice; on a voice with no pitch yet it plays frequency `$0000` = silence.
- A wrapped SF2's PSID play address is `load+$1006`, NOT `$1003`. `$1003` is silent.
- `emit_driver11_sf2(..., sequences=, orderlists=)` writes them verbatim; orderlists are plain
  sequence indices and the emitter prefixes a hardcoded `$A0` (transpose 0).

### Environment / tooling
- Corpus `SID/Shogoon/` and `bin/hardtrack composer/` are now TRACKED, so tests run from a clone.
- `tools/player-id.exe "GLOB"` — pass the glob as ONE quoted argument to get the summary table.
- Grep on code files is blocked by a tokensave hook when the pattern looks like a symbol; override
  with `TOKENSAVE_DISABLE_GREP_HOOK=1` or use tokensave MCP tools.
- Scratchpad helpers (NOT in the repo, will vanish):
  `<scratchpad>/dis6502.py` (linear 6502 disassembler),
  `<scratchpad>/htmap.py`, `htsim.py`, `htval.py`, `htinstr.py` (superseded by the repo modules),
  `<scratchpad>/gatetest.py` (**the instrumented walk that records pattern entries + onsets with
  pattern/transpose/entered-sounding — genuinely useful, worth re-creating or promoting**).
- `pytest` full run ≈ 159 s.

### Refusals are deliberate
`HardTrackModule` raises `HardTrackError` for 5 of 38 corpus files (4 multi-instance rips:
Eternal, Fruitmania, Miecze_Valdgira_2, Zone_of_Darkness; 1 PSID-init mismatch: Commercial_Fake).
Before the guard existed the simulator ran away and emitted a note on EVERY frame of EVERY voice —
2,997 phantom onsets scored against the wrong song.

### Sources
- `sid-reference-project` KB card `knowledge/players/hardtrack-composer.md` (authorship, CSDb
  74928, 1,126 files / 45 composers). Its `data_format` was all TODO before this session.
- `docs/players/PLAYBOOK.md` §1 (RE → Stage A → Stage B ladder), §3 (SF2II caps), §4 (fidelity
  ladder). `docs/players/PATTERNS.md` for named failure classes.
- CLAUDE.md's `fidelity_common.py` paragraph — `score_pct` returns None on n=0, `exercised()`
  guards constant series. Both used.

</critical_context>

<current_state>

### Deliverables
| item | status |
|---|---|
| `sidm2/hardtrack_parser.py` | **complete**, 28 tests |
| `pyscript/hardtrack_validate.py` | **complete** |
| `bin/hardtrack_to_sf2.py` (Stage A) | **complete**, 13 tests |
| `pyscript/hardtrack_stagea_validate.py` | **complete**, has `--lag` |
| `docs/players/HARDTRACK.md` | **complete + current** (includes the falsification and the root cause) |
| ACCURACY_MATRIX / players README / CLAUDE.md rows | **complete + current** |
| CHANGELOG / STORY v3.24.0 | **complete** |
| Stage B (native driver) | **not started** |
| `DriverSelector` wiring | **not done, deliberately** — Stage A is a `bin/` tool |

### Repo state
- HEAD = `c31279a`. **6 commits ahead of `origin/master`, NOT PUSHED.**
- Working tree clean except `whats-next.md` (this file).
- Version **3.24.0**, build date 2026-08-09.
- Tests **2,110 passing / 8 skipped / 2 xfailed / 0 failures** (full run after the last commit).
- `out/hardtrack/` contains build artifacts (`Love_tune_2.sf2`, `L2.sid`, `L2_play1003.sid`,
  `_cmp.sid`, `_t.sid`, `Zakplus.sf2`, `Hopscotch.sf2`, …) — **untracked scratch, safe to delete**.
  `output/Love_tune_2_export/` likewise (from the misbehaving text exporter).

### Headline numbers (all at an 8-frame window)
- Parser: **88.39%** sequencer-pitch (5167/5846) · **2.61%** program-driven (28/1074) ·
  8 of 33 files at exactly 100.0% · 5 of 38 refused.
- Stage A: **90.64%** (`--lag 0`) / **91.26%** (`--lag 1`, removing the Driver 11 startup phase) ·
  6 of the 8 parser-100% files also 100.0%.

### Open questions for the user
1. **Push the 6 commits?** Not done; never requested.
2. **Commit this `whats-next.md`?** It was already dirty when the session started.
3. Which thread next — the two genuine Stage A losses (`Love_tune_3`, `Walk_to_Soul`), the
   parser's 11.6% residual, modelling the synth programs, RetroDebugger on the editor, or Stage B?

### Standing caveats a fresh context must not lose
- Never average the two fidelity columns.
- Never quote a percentage without its window.
- Stage A > parser is an ARTIFACT.
- The `+1` frame is a Driver 11 template property affecting EVERY Stage A builder here.
- `SID/Shogoon/` is mixed-player: only 38 of 150 files are HardTrack.

</current_state>
