<original_task>
Blackbird / lft is CLOSED (shipped as v3.22.0). This handoff is a PIVOT, not a
continuation: the next session starts a NEW PLAYER.

The user's previously-stated new-player priority list (Hubbard, Sound Monitor,
Gallefoss/SDI, MoN/Deenen) is fully exhausted, so the next target is PROPOSED
below rather than inherited. **Confirm the pick with the user before starting the
RE** -- the recommendation is evidence-based, but the choice is theirs.
</original_task>

<work_completed>
## Blackbird / lft -- CLOSED at v3.22.0

Corpus **99.963%**, **11 of 16 files at exactly 100.0**, none below 99.8.
Full suite **1679 passed** / 7 skipped / 2 xfailed. All pushed; HEAD `945a642`.

Four fixes, each overturning something the repo had recorded as settled:

| commit | what |
|---|---|
| `2d65366` | **E3f re-enabled** -- the "combo values crash SF2II" verdict was FALSIFIED (120 combo commands executed across 10 screenshot-verified trials, 0 crashes) |
| `b0bff86` | **E4** -- prepare1's byte allowance is FORFEITED by prepare2; To_Die_For_II 94.2 -> 98.2 |
| `5db109c` | sweep + crash oracle promoted to `pyscript/` with 34 tests |
| `d6fff59` | **E5** -- the filter row grammar was missing a row type; To_Die_For_II -> 100.0, Revolutions_Delivered -> 100.0 |
| `2c41d97` | E5 editor play-test PASSED (4/4) |
| `486a990` | **E6** -- B7 priming and `window_steps` were fighting; Into_the_Unknown -> 100.0 |
| `c8dc848` | v3.22.0: inventories, CHANGELOG, STORY, version bump |
| `f302eca` | the corpus-mean guard had gone STALE while passing green -- repointed |
| `945a642` | E6 editor play-test PASSED (8/8) -- last verification gap closed |

Editor-verified: E5 4/4, E6 8/8. Full detail in `docs/players/BLACKBIRD.md`.
</work_completed>

<work_remaining>
## THE PIVOT: next player -- recommended target is Matt Gray

`SID/Gray_Matt/` (55 files) is the largest unported corpus left. `player-id`
breakdown, measured 2026-07-25:

| player-id | count | status |
|---|---|---|
| **Soundmonitor** | **24** | **ALREADY SUPPORTED** (native driver, v3.17-3.19) |
| **Matt_Gray** | **20** | unported -- his own engine, the real target |
| Electrosound | 6 | unported |
| Ariston | 3 | unported |
| Tonal_Kaos | 2 | unported |

### Step 0 FIRST (cheap, do before any RE)

**24 of the 55 files are Sound Monitor and may already build.** This is exactly
the Deenen pattern -- there, "a third of the useful corpus was already supported
and merely misfiled, so eight wins at ~100% came from classification alone". Run
the existing Sound Monitor pipeline over those 24 before touching a disassembler.
MEASURE, do not assume: Sound Monitor's corpus figure (99.23% strict) was
established on `SID/Fun_Fun`, and a different composer's rips may sit outside it.

### Then: Matt_Gray (20 files), the genuine new player

Follow `docs/players/PLAYBOOK.md` -- the staged method (locate/parse -> Stage A
Driver-11 transpile -> Stage B native driver) every player since Galway has used.
Check `mcp__tdz-c64-knowledge` for an existing card and for scene-history leads
(SIDin, c=hacking, codebase64 are indexed) BEFORE hunting disassemblies.

### Alternative, if the user prefers depth over breadth

**The 45 non-locating LFT rips.** The "16-file v1.2-exact corpus" was never a
curated sample -- it is every rip `locate_blackbird` supports; 45 of 61 files in
`SID/LFT/` fail location outright. Extending variant coverage is a multi-session
RE arc, but on an engine that is now VERY well understood (E4/E5/E6 documented its
prepare chain, filter grammar and priming semantics). Higher certainty, narrower
payoff than a new player.

## Carried forward from Blackbird (all documented, none blocking)

1. **The user's original SF2II crash is UNEXPLAINED.** Established: loading a
   combo build and pressing play -- with or without follow mode -- does not
   reproduce it. NOT established: that no editor state can. `BB_NO_COMBO=1`
   disables combo arming if it recurs, and a recurrence would be the most
   informative datum available.
2. **TDZ knowledge-base card written but NOT ingested** -- staged at
   `~/.tdz-c64-knowledge/temp/blackbird_lft_player.md` (schema per CLAUDE.md,
   `status: in-progress`). The MCP server never finished connecting; one
   `add_document` call when it is up.
3. **Five Blackbird files at 99.8-99.9** (Glyptodont 99.8; Fargo,
   Dithered_Island, Euclid_Was_Here, Fugue 99.9) -- small freq artifacts, not
   structural. Diminishing returns.
4. **Galway / ROMUZAK `fp_dec`** -- SF2II executes filter ADD rows as SET rows.
   `galway_driver.asm:535`, `romuzak_driver.asm:564`: `cmp #$90; bcs fp_set` with
   no high-bit guard. Widen to `cmp #$80` (B24 form) ONLY after confirming each
   player's `fp_set` mode extraction handles a top-nibble-8 byte0, then re-verify
   each corpus. Allowlisted in `test_sf2ii_emulator_hazards.py::KNOWN_UNFIXED`.
5. **`DriverSelector` is NOT a defect -- do not "fix" unasked.** Every
   native-driver player here is `bin/`-only (Galway, MoN, Hubbard, DMC, Sound
   Monitor, SDI, ROMUZAK). Blackbird matches the established pattern.
</work_remaining>

<critical_context>
## Verification discipline -- the transferable half of the Blackbird arc

These each cost real time. They are player-agnostic; apply them to whatever
comes next.

- **Check the measurement window covers the effect.** A crash batch returned
  16/16 SURVIVED from a 6-second play window over a build whose first combo
  command fires at 8.2s -- it executed NONE of the construct under test. An
  all-green result measured outside the window where the effect lives is not
  evidence of absence. `assert_window_covers()` now raises instead of reassuring.
- **Beware vacuous matches.** `$D415`/`$D416` reading "100%" while both hold
  `$0000` means nothing. Assert the evidence is non-trivial before quoting it.
- **A pinned constant not revised with its docs is worse than no guard.** The
  corpus-mean test kept passing on E4's 99.669 while the published figure moved
  to 99.963 -- still green, so it read as verification.
- **Derive the rule from the code that works, not from the discrepancy.** Three
  tick accountings disagreed, and the naive re-walk was wrong the SAME way the
  builder was. Reading `prepare1/2/3` found it.
- **Read the CONSUMER, not just the producer.** Twice the fault was in the driver
  executing correct data, not in the data. When emitted data is verifiably right
  and the output still is not, trace the consumer.
- **A register pinned at exactly 66.7% / 33.3%** is a whole-voice failure, not
  scattered error. If it is pulse, suspect accumulator phase and look for a
  timing event EARLIER than where the plateau starts.
- **Only a real editor play-test catches an SF2II-only hazard** -- but ONE manual
  play-test is a single sample from a flaky process, and it convicted the wrong
  suspect for a day. Use trials, a control arm, and a window check.
- **GUI automation steals focus and its keystrokes land in whatever is
  foreground.** It disrupted the user's own session once. Ask before running
  batches while they are at the machine.

## Reusable tooling built this session

- `pyscript/blackbird_sweep.py` -- corpus sweep + `--compare` (exit 1 on
  regression or part move). **Its byte-change column only stats `*_part01.sf2`**,
  so on multi-part files it sees the first part only.
- `pyscript/blackbird_crash_probe.py` -- SF2II crash oracle (load, press F1,
  screenshot, report survival) + combo-schedule analysis. The GUI half is lazily
  imported so the analysis half stays testable headless.
- 34 tests across both, running in 0.43s -- they never build and never launch
  SF2II.

Both are Blackbird-shaped, but the ORACLE pattern generalises: turning "the user
presses play" into a scriptable, screenshot-verified trial is what falsified E3f.

## Method docs that outlive any one player
`docs/players/PLAYBOOK.md` (the porting method), `docs/players/PATTERNS.md` (the
RE technique catalog). Read both before starting a new player.
</critical_context>

<current_state>
## Repository
- Branch `master`, HEAD `945a642`, fully pushed (`git log origin/master..master`
  empty). Only `.claude/settings.local.json` is modified; `scratchpad/` deleted.
- Version **3.22.0** (2026-07-25). `CHANGELOG.md`, `STORY.md`, `README.md`,
  `CLAUDE.md`, `docs/reference/ACCURACY_MATRIX.md`, `docs/SF2.md` and
  `docs/SID_TO_SF2_CONVERSIONS.md` are all consistent at that version.
- `out/blackbird/` holds the final E6 corpus (16 songs / 20 files).

## Baseline to protect
**1679 passed / 7 skipped / 2 xfailed** (`py -3 -m pytest pyscript/ -q`, ~5 min).
</current_state>
