<original_task>
Two-part request, in sequence:

1. "lets work on matt_gray ... Last_Ninja2 is his most rated. can you list his
   top 5 most rated songs" -- rank Matt Gray's HVSC tunes by rating/popularity.
   Corpus: `C:\Users\mit\Downloads\HVSC_85-all-of-them\C64Music\MUSICIANS\G\Gray_Matt`

2. "yes, start Stage A on Driller" -- then, in follow-ups: commit, run the real
   SF2II play-test, "go with last ninja", "fix the onset drift", "do next"
   (Tusker), "do deliverance and quedex".

Scope = RE + Stage A (Driver 11 transpile) for the Matt Gray player family.
Stage B (native driver) was never in scope.

NOTE: this file previously held the Blackbird->pivot handoff. Blackbird is
CLOSED at v3.22.0; Matt Gray was the pick and is the subject below.
</original_task>

<work_completed>

## Part 1 -- the popularity ranking (delivered, no code)

**Method note that matters:** DeepSID's per-file `rating` field is the
LOGGED-IN USER'S OWN rating (`php/music.php` joins `ratings` on `user_id`), so
an anonymous API pull returns 0 for every file. It is NOT a public average.
Also `music.php` requires header `X-Requested-With: XMLHttpRequest` AND the
folder path prefixed `/_High Voltage SID Collection/...`; anything else 500s.
Drove it via `javascript_tool` inside the page's own origin.

Ranking built from **Remix.Kwed.Org remix counts**, scraped across all 4
composer-search result pages and aggregated by the DeepSID original-tune link
on each remix row (178 remixes over 13 tunes):

| # | Tune | Remixes |
|---|------|--------:|
| 1 | Last_Ninja_2 | 121 |
| 2 | Tusker | 15 |
| 3 | Deliverance | 9 |
| 4 | Driller | 8 |
| 5 | Quedex | 5 |

Runners-up: Vendetta 4, Bangkok_Knights_Loader 4, Mean_Streak 3, Dominator 3.
Last Ninja 2 alone = 68% of his RKO output, matching Remix64's own
retrospective ("almost three quarters").

Cross-checks: HVSC Top 100 lists only Last Ninja 2 (#12) and Driller (#54); the
1997 sidmusic.org chart lists Last Ninja 2 (7 votes), Driller (4), Quedex (2).
**Tusker and Deliverance rest on the remix count ALONE.**

Within Last_Ninja_2.sid, remix demand concentrates on subtune 2 (35) and
subtune 12 (30).

## Part 2 -- TDZ knowledge base

`mcp__tdz-c64-knowledge` was initially unreachable (never finished connecting);
the user reconnected it via `/mcp`. It already held a **`matt-gray`
player-routine card** (`status: verified`), plus **SIDin #2** ("Matt Gray's
Driller music routine") and **SIDin #3** (fingerprinting his engine by its
portamento-flag check) -- both worth reading before further RE.

I **updated the card in place** (`update_document`, card id `matt-gray`
preserved, old version superseded) with:
- Corrected attribution: Hunter's Moon is a **co-credit** -- the HVSC PSID
  author field reads `Matt Gray & Martin Walker`. The card had it as a plain
  Matt Gray credit; the 1997 chart credited Martin Walker alone. Both
  half-right. It is the ONLY co-credit among the 55 files.
- A corroboration the card lacked: Driller's PSID header (`init=$15E0 /
  play=$0E46`) matches the Codebase64 disassembly EXACTLY.
- Porting gotcha: Tusker's `play=$E002` sits under KERNAL ROM.
- The popularity ranking + the DeepSID rating trap, scoped as third-party data.

## Part 3 -- the code (the bulk of the work)

**Branch `mattgray-driller-stage-a`, pushed to origin. HEAD = `9e00576`.**

| commit | what |
|--------|------|
| `eae7325` | parser + validator + Stage A converter + 14 tests + docs |
| `19d3436` | SF2II play-test results |
| `13769e8` | LN2 wrapper cracked; located but explicitly NOT trusted |
| `5264e13` | LN2 format solved (`$70` duration split) -- 12/13 at 100%/100% |
| `da7afb1` | all 13 LN2 subtunes parse; truncated-pattern tolerance |
| `cf73031` | onset drift fixed (`$f9` control code) -- 13/13 at 100%/100% |
| `3fdcb81` | Tusker (2nd wrapper shape) -- 4/4 at 100%/100% |
| `9e00576` | play-trampoline following; Deliverance/Quedex are further generations |

### Files created

| Path | What |
|------|------|
| `sidm2/mattgray_parser.py` | parser, code-map walker, signature locator, sequencer simulation, both relocating wrappers |
| `bin/mattgray_validate.py` | onset/pitch validation vs siddump, plain/modulated split |
| `bin/mattgray_to_sf2.py` | Stage A -> Driver 11 SF2, part windowing |
| `pyscript/test_mattgray_parser.py` | 14 tests, skip cleanly without HVSC |
| `docs/players/MATTGRAY.md` | full player doc incl. the generations table |

Also edited: `docs/players/README.md` (index row), `CLAUDE.md` (Known
Limitations row).

### The engine, as reverse-engineered

`music_play` is a shim calling ONE shared `play_voice` three times with
X = `$00/$07/$0e` -> every per-voice state array has **stride 7**.

Pattern dispatch, **Driller (1987)**:
- `>= $fd` -> duration (2-byte code `$fd nn`), **sticky**
- `$fc nn` / `$fb nn` -> slide type 2 / type 1
- `$fa nn` -> set instrument (driver multiplies by 8)
- `$00` -> **REST / note-off**
- `$01-$f9` -> note index into the 96-entry freq table
- `$ff` -> end of pattern (consumed AFTER a note)

Pattern dispatch, **Last Ninja 2 / Tusker (1988-89)** -- full order:
`>= $fb` slide - `>= $fa` instrument - `>= $f9` **parameter (2-byte, plays NO
note)** - `>= $70` **duration = byte - $70, sticky** - else note

Track bytes (all builds): `$ff` restart at 0 - `$fe` stop - else pattern number.

Instruments are **TWO parallel 8-byte tables** (`instr_A0` + `instr_A1`), NOT
one 16-byte record. Full field map in `docs/players/MATTGRAY.md`.

Tempo: a row tick every `(tempo + 1)` frames; a duration byte D holds D+1
ticks. Verified empirically (Driller `$3f` -> onsets on frames 1, 257, 513...).

### Relocating wrappers (two distinct shapes)

**LN2 (1988)** -- `relocating_subtunes()`. `init $3f40` copies the selected
subtune's self-contained blob to `$4000`. 13 blobs (13 separate
`(C)1988 MATT GRAY` strings). Tables: src lo/hi `$3f80`/`$3f8d`, tail `$3f9a`,
pages `$3fa7`; length = `pages*256 + tail` (tail 0 => full extra page).

**Tusker (1989)** -- `relocating_subtunes_v2()`. Self-modifying copy loop,
sources **page-aligned** so only a hi-byte table exists (`$4138`), length in
**whole pages** (`$413c`), destination **`$e000`** -- under KERNAL ROM, which is
exactly why its PSID play address is `$e002`. 4 blobs.

### Results (vs `siddump_complete.py`, plain instruments, headline)

| File | Subtunes | onset | pitch |
|------|---------:|-------|-------|
| Driller | 1 | **1513/1513 = 100%** | **1513/1513 = 100%** |
| Last Ninja 2 | 13/13 | **100%** every one | **100%** every one |
| Tusker | 4/4 | **100%** every one | **100%** every one |

**18 tunes total, all 100%/100% on the sequencer.** LN2 n ranges 1-1070 per
subtune at 6000 frames; Tusker n = 86, 439, 708, 685.

### Stage A + SF2II play-test

`bin/mattgray_to_sf2.py` emits stock Driver 11 via the shared
`galway_driver11_emitter`. Driller loops at 8320 rows = 33,280 frames = 665.6 s,
past the SF2II memory wall, so it **splits into 2 parts** (never truncates
silently). Sequences round-trip byte-exactly (6000/6000 rows/voice, 0
mismatches), 41 sequences vs the 120 cap, none over the 960-event `Unpack` limit.

Play-tested in REAL SF2II via `probe_once()` from
`pyscript/blackbird_crash_probe.py` (player-agnostic despite the name):
- part01 x3 @45 s -> 3/3 SURVIVED; part02 x3 @45 s -> 3/3 SURVIVED
- part02 x1 @195 s = **100% coverage** -> SURVIVED
- part01 x1 @492 s -> probe reported CRASHED, **VOID**: the user closed the
  window, and `probe_once()` cannot distinguish that from a crash (it only
  checks "process still alive"). No proof-of-play screenshot was written, the
  identical signature either way. **User then confirmed part01 directly,
  watching it play through TWICE.**

Screenshots confirmed Driver 11.00, tempo `03`, 22 instruments, and real
decoded music on all three tracks in part 2 with the primed instrument selects
(`a000`/`a006`/`a00b`) on row 0.

### Memory files written

- `memory/matt-gray-player.md` -- corpus ranking, DeepSID trap, engine summary
- `memory/matt-gray-driller-re.md` -- the RE arc + the measurement traps
- Both indexed in `memory/MEMORY.md`

</work_completed>

<work_remaining>

## 1. Deliverance (1990) -- a THIRD generation. Best next target.

`...\MUSICIANS\G\Gray_Matt\Deliverance.sid`, `load=$4000 init=$4D96
play=$4DA1 songs=7`. Flat file, **no relocating wrapper**.

Already solved: its PSID play address is a **trampoline** (`$4da1: jsr $4daa
...`), so `_find_play_voice()` now falls back to `_scan_for_shim()`, which finds
the 15-byte `ldx #$00 / jsr pv / ldx #$07 / jsr pv / ldx #$0e / jsr pv` body
anywhere in the image. **That works -- the shim IS found.**

Still failing: `could not locate the track-pointer tables`. The 1990 build
reorganised them, so `locate()`'s "6 consecutive `LDA abs,y` sites whose
operands step by 2" no longer holds.

Steps:
1. Get `play_voice` via `_scan_for_shim()`, dump `p._b9_sites()` and compare
   the shape against Driller's and LN2's.
2. Disassemble the track-pointer setup -- find what replaced the 6-site pattern.
3. Re-derive the pattern-byte dispatch -- do NOT assume it matches LN2. Use the
   technique that worked: list `lda (zp),y` sites and the `cmp #imm` values
   following each (this is exactly how the LN2 `$70` and `$f9` codes were found).
4. Check `_duration_base()` -- may find `$70`, a different constant, or nothing.
5. Validate: `py -3 bin/mattgray_validate.py <sid> --subtune N --frames 6000`.
   Do NOT trust a parse that merely succeeds (see attempted_approaches).

## 2. Quedex (1987) -- a FOURTH generation, harder.

`load=$4000 init=$4B79 play=$4BB3 songs=9`. `_scan_for_shim()` finds **nothing
at all** -- no `ldx #$00/$07/$0e` + `jsr` triple exists anywhere in the image.
Its play routine is `$4bb3: lda $4b7f / bne ...`.

So Quedex does NOT use one shared `play_voice` called three times; its voice
dispatch is structurally different, and it is the earliest of the four --
plausibly pre-dating that refactor. Needs a from-scratch disassembly of `$4bb3`
onward. `MattGrayParser` currently *assumes* the shim exists
(`_find_play_voice` raises without it), so supporting Quedex means a second
entry-point strategy, not just a new `locate()` branch.

## 3. Remaining smaller items

- **LN2 subtunes 5 and 6 have unusable sample sizes** -- n=19 and n=**1** even
  at 6000 frames, because nearly all their notes are pitch-modulated. Their
  "100%" is not evidence. Widen the window or keep them out of any headline.
- **`probe_once()` limitation** is real and affects the Blackbird play-tests too
  (same oracle): "process absent" => "crashed" unconditionally, so any
  long-window trial is corrupted if someone touches the window. Fix by
  recording the process exit code (clean close vs crash differ) and/or
  screenshotting periodically during the window rather than only at the end.
- **Stage A not play-tested for LN2/Tusker.** `out/LN2_s1.sf2` was emitted as a
  smoke test only.
- **Not wired into `DriverSelector`** -- deliberate, same as every other native
  player here.
- The other ~50 HVSC Gray_Matt files are untouched and unclassified.
- Re-run the FULL suite (`py -3 -m pytest pyscript/ -q`); it was last run green
  at `eae7325`, not after the LN2/Tusker commits.

</work_remaining>

<attempted_approaches>

## Things that failed, with the reason -- do not repeat

**DeepSID as a rating source.** Its `rating` column is per-logged-in-user, not
a public average. Anonymous pull returns 0 for all 55 files. Verified against
`php/music.php` (~lines 1271-1277). Dead end for ranking.

**DeepSID `music.php` via curl.** HTTP 500 regardless of params, even with
cookies and `X-Requested-With`. The working form needs the folder path prefixed
`/_High Voltage SID Collection/...` AND `searchType=%23all%23` AND `page=0` --
found only by reading the page's own network requests. Driving it from
`javascript_tool` in the page origin is the reliable route.

**Trusting the WebFetch'd Codebase64 disassembly for exact table order.** Its
pattern-pointer listing appeared as `pattern_00, pattern_01, pattern_03,
pattern_02, ...` (da65 names labels by ADDRESS, not index), which would have
swapped patterns 2 and 3. Reading the real bytes by backward dataflow from the
code operands gave the right answer and matched siddump. **Always re-derive
table addresses from `LDA abs,y` operands, never from a listing.**

**My own first extraction script dropped the PSID `load=0` branch.** Driller's
header declares `load=$0000`, so the real load address is the first two data
bytes. Without that every table operand decoded to plausible-looking garbage
while the file still "parsed". Assert the opcode is `$b9` before trusting an
operand.

**A flat byte scan for `LDA abs,y` sites.** The player interleaves code and data
(Driller's per-voice state arrays sit at `$0cce`, mid-routine), so a linear
sweep invents instructions out of table bytes and yields nonsense operands like
`$0111`. Replaced with a recursive-descent code walk (`_code_map()`) following
branches/JSR/JMP and stopping at RTS/illegal opcodes.

**Locating the pattern tables early in `locate()`.** Reliably mis-fired on two
adjacent *instrument-field* reads (LN2's `$461a`/`$4620`, six apart) that look
exactly like a lo/hi pointer pair for a six-pattern song. Fixed by locating
patterns LAST, from operands no other table has claimed.

**Assuming "it parses" means "it decodes".** THE key lesson of this arc. The
first LN2 decode produced entirely sensible pattern counts (45), instrument
counts (18) and note counts -- and scored **11-22% pitch**. Nothing about it
announced itself as broken. Only `bin/mattgray_validate.py` caught it. Cause:
the `$70` duration split. Run the validator before believing any new build.

**Reading a single flattering measurement window.** Subtune 1 was 303/303
(100%) at 3000 frames but 683/692 (98.7%) at 6000. Always widen the window.

**Alternatives considered, not pursued:** py65 emulation extraction to
materialise the LN2 blobs (unnecessary -- the copy loop decodes statically);
CSDb as a rating source (rates releases, not individual game SIDs).

</attempted_approaches>

<critical_context>

## Measurement discipline -- the two traps that faked parser bugs

1. **siddump's default display hides genuine writes.** It prints `....` when a
   register's VALUE did not change, so Driller's `42 3b 3b 42 3b 3b` (a note
   re-triggered at the same pitch) looked like 30 parser misses that were not
   misses. `bin/mattgray_validate.py` passes **`-w`/`--written`** (write-hook
   precision) for exactly this. **Do not remove it.**

2. **The first "pitch miss" was the parser being right.** Driller pattern 5 is
   `fa 0e fd 3f 2f 2b 2e fc 20 2a ff`; note `$2a` was off by exactly `+$20` --
   the `$fc` slide rate. Slides come from the PATTERN STREAM as well as the
   instrument, so the plain/modulated classification must be **per-note**.

## The plain/modulated split is not decoration

On a pitch-modulated instrument the player rewrites `$d400` **every frame**, so
an onset there matches whatever the parser predicts -- that bucket **cannot
falsify the timing model** and is reported separately, never claimed. A note is
"modulated" if its instrument has arp (`A0[5]`), drum path (`A0[7]` bit0),
auto-slide (`A1[0]`/`A1[4]`) **or** a `$fb`/`$fc` slide attached to that note.
This is the vacuous-100 failure class `sidm2-fidelity-falsify` exists to catch
-- do not collapse the buckets into one number.

## Gotchas

- **PSID `load=0`** -> real load address is the first 2 data bytes (Driller).
- **`music_init` ignores the accumulator** in Driller: literally
  `lda #$01 / sta $0d0f / rts`, so both its PSID subtunes play tune 1. HVSC
  nonetheless lists 8:41 / 10:21 against a measured 11:05 loop.
- **A `$fb`/`$fc` slide binds ONLY to the note immediately after it** -- the
  driver zeroes the effect slot at the top of every fetch (`L09b6`).
- **LN2 subtune 7's last pattern is genuinely truncated** by the relocating copy
  (ends `af 30 00`, no `$ff`). `_read_pattern()` returns it short and reports
  `song.truncated_patterns`; `_fetch()` bounds-checks control-code params.
  Reading every pattern eagerly made one unreachable pattern fatal.
- **Driller's three tracks have different lengths (117/82/109) but wrap on the
  SAME tick (8320)** -- a good internal-consistency check.

## Environment

- Corpus: `C:\Users\mit\Downloads\HVSC_85-all-of-them\C64Music\MUSICIANS\G\Gray_Matt`
  (55 `.sid` + a `Worktunes/` subfolder). Tests read `HVSC_ROOT`, defaulting to
  that path, and skip cleanly if absent.
- `/tmp` does NOT exist on this box -- use the session scratchpad.
- Bash tool caps at 10 min; the 492 s play-test overran it and needed
  `run_in_background`.
- SF2II must launch with `cwd=bin/`. Its F10-load is heap-flaky (~73%/attempt),
  hence `load_attempts`.

## Key references

- Codebase64 Driller disassembly:
  https://codebase64.net/doku.php?id=base:matt_gray_-_driller
- TDZ KB card `matt-gray` (updated this session); **SIDin #2** and **SIDin #3**
  in the same KB -- read before more RE.
- `docs/players/PLAYBOOK.md` sections 1 (staged method), 3 (SF2II caps),
  4 (measurement ladder), 5 (gotchas).
- `docs/players/MATTGRAY.md` -- full write-up incl. the generations table.

</critical_context>

<current_state>

## Committed and pushed -- nothing is uncommitted

Branch **`mattgray-driller-stage-a`**, HEAD **`9e00576`**, tracking
`origin/mattgray-driller-stage-a`. 8 commits. Working tree clean except
`.claude/settings.local.json`, which was **already modified before this session
started** and was deliberately never staged.

No PR opened. Link if wanted:
https://github.com/MichaelTroelsen/SIDM2conv/pull/new/mattgray-driller-stage-a

## Status of deliverables

| Item | Status |
|------|--------|
| Popularity ranking | **Complete** (chat + doc + KB card) |
| Driller RE + Stage A | **Complete**, 100%/100%, SF2II play-tested |
| Last Ninja 2 (13 subtunes) | **Complete**, 100%/100%, Stage A emits; NOT play-tested |
| Tusker (4 subtunes) | **Complete**, 100%/100%; Stage A NOT run/play-tested |
| Deliverance | **Blocked** -- shim found, track tables not located |
| Quedex | **Not started** -- no shim exists; different architecture |
| Stage B (native driver) | **Not started**, out of scope |
| TDZ KB card | **Updated** in place, verified by re-search |

## Verification state

- `pyscript/test_mattgray_parser.py`: **14/14 pass**
- Full suite: **1693 passed, 7 skipped, 2 xfailed, 0 failures** -- run after
  `eae7325`, **NOT re-run** after the later LN2/Tusker commits. Re-run it.
- Driller regression re-checked after every change: **1513/1513 onset,
  1513/1513 pitch**

## Open questions

- Does Deliverance share the `$70`/`$f9` dispatch, or is it a third encoding?
  `_duration_base()` will answer once the tables locate.
- Is Quedex worth the effort? #5 by remix count (5 remixes) and needs a
  from-scratch entry-point strategy. Deliverance (9 remixes, shim already
  found) is the better ROI.
- Should Stage A SF2s for LN2/Tusker be play-tested before anyone relies on
  them? (Recommend yes -- the only thing that catches SF2II-only hazards.)

## Honest framing to preserve

Every "100%" here is **the sequencer on plain instruments only**. Stage A
knowingly omits the slide/arp/PWM/drum engine, so the output will NOT sound
like the originals -- timbre is a Stage B claim. Do not let the 18-tune
100%/100% headline drift into meaning "sounds right".

</current_state>
