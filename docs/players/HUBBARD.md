# Rob Hubbard — SID → SF2 support

**Composer:** Rob Hubbard (his own player family, 1985–1987)
**Corpus:** `SID/Hubbard_Rob/` (95 `.sid` files)
**Registry key:** none yet — the whole pipeline lives in `bin/` (not wired into `DriverSelector.PLAYER_REGISTRY`)
**Status:** native SF2 driver, **byte-exact freq + pulse + filter on all 3 voices** for the V1 corpus (Monty/Commando/Zoids/Last_V8/… pulse 100/100/100 via the per-instrument pulse engine) and for the first V2 tune (Delta theme: freq/pulse/filter 100%, waveform 85–96%). Ground truth: Anthony McSweeney's fully-commented *Monty on the Run* disassembly (C=Hacking #5), extracted to `docs/analysis/hubbard/chacking5_monty_disassembly.txt`.

Two format generations share **one parser** (`sidm2/hubbard_parser.py`) and **one native driver** (the shared `drivers_src/mon/romuzak_driver.asm`, via `bin/build_hubbard_native_song.py` → `bin/build_mon_native_song.py`):

- **V1** (~30 tunes): Monty, Commando, Crazy Comets, Zoids, Gremlins, Master of Magic, One Man and his Droid, Last V8 (+C128), Geoff Capes, 5 Title Tunes, Chimera, Gerry the Germ, …
- **V2** (Delta class, ~30 more): Delta, Lightforce, Sanxion, Saboteur II, Thing on a Spring, Action Biker, … — an **incremental evolution** of V1, not a rewrite (40 of the 64 "unparseable" files keep the full V1 table structure).

---

## The V1 engine (reverse-engineered)

A three-level **song → track → pattern** player with a per-frame effects engine.

- **Tempo gate:** a note-*tick* fires every `resetspd+1` frames (`DEC speed / BPL / LDA resetspd / STA speed`). Effects (vibrato, pulsework, portamento, drums) run **every frame**. A note lasts `len+1` ticks; onset frame = `tick × (resetspd+1)` exactly.
- **Songs table** — 6 bytes/song = the 3 per-voice **track pointers**, stored as the two 3-byte halves the init copy loop fills (`currtrklo[0..2]` then `currtrkhi[0..2]`; half A feeds the ZP pointer LOW byte).
- **Track** — a pattern-number list terminated by `$FF` (loop) or `$FE` (halt).
- **Pattern note** — 1–3 bytes:
  - byte 0 = `len` (bits 0–4) + **bit5 no-release** + **bit6 append/tie** + **bit7 "second byte follows"**.
  - byte 1 (iff bit7): **positive** = instrument number; **negative** = portamento speed (bit0 = direction).
  - pitch byte (last): semitone index; `freq = INTERLEAVED lo,hi table` indexed `pitch×2` (96 notes).
  - **append (bit6)** consumes ONLY the length byte — a tie that keeps the previous pitch/instrument and does not re-gate.
  - **no-release (bit5)** skips the length-end ADSR kill: the following note's fetch writes ctrl over an already-on gate → **no gate edge, no re-attack** (a tie with a pitch update; see *Fidelity gotchas*).
- **Instrument** — 8-byte record `[PWlo, PWhi, ctrl, AD, SR, vibdepth, pulsespeed, fx]`. `fx` bits: 0 = drum, 1 = skydive, 2 = octave-arp, 3 = fast-PWM (later revisions only).
- **Effects engine** (per frame):
  - **Vibrato:** `counter & 7` → an oscillating `01233210` value, depth `= semitone-step >> (vibdepth+1)`, only when `len ≥ 8`.
  - **Pulsework** — per-**instrument** PW state (lives in the instrument record's bytes 0/1, shared across voices), per-voice delay/direction. Two variants:
    - **classic bounce** (Monty): step `= pv & $E0` every `(pv & $1F)+1` frames, rails at hi-nibble `$0E` (down) / `$08` (up).
    - **fast-PWM** (Commando, `fx` bit3): `PWlo += pulsespeed` every frame, hi fixed.
    - `pv == 0` → static. The counter ships a **nonzero initial value in the load image** ([0,1,29] for Monty) and is NEVER reset at note fetch.
  - **Portamento:** `±(val & $7E)` per frame.
  - **Drums:** noise on the first frame + `freqhi--` with a gate-off control byte.

All table addresses are located by **relocation-safe code signatures**, never hardcoded (songs-copy loop, pattern-pointer load, interleaved-freq read, `instr+2,X` fetch, `DEC speed/…/STA speed`).

---

## The V2 deltas (Delta class)

V2 keeps V1's pattern/note *semantics* but changes five things — each detected per-file by its own code signature so one parser handles both generations:

1. **Split songs table** (`Thing_on_a_Spring` class, no init copy loop): per-voice track pointers load from **separate lo/hi tables** indexed `song×3 + voice` (`LDA lo,X / STA zp / LDA hi,X / STA zp+1`).
2. **Fractional tempo — the "swallow counter":** a *second* countdown (`DEC abs / BPL / LDA #v / STA same / JMP`); on expiry the speed-dec is **skipped one frame**, stretching a tick. Effective tempo = `fpt + 1/(period)`. The post-init counter value is the schedule phase (recovered by py65 init-replay). Periods seen: Sanxion 109, Delta 5, Thundercats 4, Star_Paws/Wiz/AWM 128.
3. **V2 note format** (detected via `AND #$60 / CMP #$60 / BNE`):
   - `len` bits 5+6 both set → a **1-byte rest/hold**.
   - a negative 2nd byte (porta) carries an **extra parameter byte** (4-byte spec — reading it as 3 desyncs the whole stream; this was the "instr 127" garbage).
   - pitch **bit7 = no-fetch**: pitch change WITHOUT the instrument fetch (no PW/ADSR write, no gate edge) — a tie with a pitch update.
4. **V2 track format:** interleaved **repeat counts** — `[pat0 (1×), cnt1, pat1 (cnt1×), cnt2, pat2, …]`. The ROM inits its repeat counter to 1 and reads the next track byte as the count for the FOLLOWING pattern.
5. **Pulse resets per fetch:** V2's note fetch REWRITES the pulse width from the instrument record each note (no cross-note phase keep — the opposite of V1's free-running wobble).

Plus **per-voice init instruments** (both generations): notes without an instrument byte inherit the ROM's per-voice defaults after INIT, not instrument 0 (Last_V8's V2 played instrument 3's PW; `initial_instruments()` replays init to seed the shim).

### Format-generation map

| Signature present | Meaning | Example files |
|-------------------|---------|---------------|
| songs-copy loop `BD..99..E8 C8 C0 06 D0` | V1 songs table (6B/song) | Monty, Commando, Zoids |
| `BD..85..BD..85` (no copy loop) | V2 split lo/hi songs tables | Thing_on_a_Spring, Lightforce |
| `CE../10../A9 v/8D same/4C` | swallow counter (fractional tempo) | Delta, Sanxion, Star_Paws |
| `AND #$60 / CMP #$60 / BNE` | V2 note format (rest/4-byte-porta/no-fetch) | Delta, Saboteur_II |
| `BD..8E..0A 0A 0A AA` | per-voice instrnr array (init defaults) | all |

---

## How Hubbard is converted

Same staged pipeline as Galway/MoN/ROMUZAK (see [PLAYBOOK.md](PLAYBOOK.md)):

1. **Parse** (`sidm2/hubbard_parser.py`) → exact tick-timed events, onset-validated ≥95–100% against a `siddump` trace.
2. **Shim** (`bin/build_hubbard_native_song.py::HubbardShim`) — presents the decoded song as MoN-compatible `MONEvent` voices so the shared trace-driven native builder captures every per-frame effect (vibrato/portamento/drum FM, pulse wobble, filter) into FM / pulse / wave programs. Compilation rips (`5_Title_Tunes` = 5 embedded players) resolve PSID-song → module via `detect_module_map`; looping ostinato tracks are expanded to the song span; the swallow schedule rides `ticks_to_frames`.
3. **Native driver** (`drivers_src/mon/romuzak_driver.asm`) — the shared SF2 driver, feature-gated per tune via `layout.inc` flags set from shim attributes:
   - **`HARD_RESTART`** — Hubbard's release "kill ADSR" (`$7D` rows) + per-retrigger ADSR re-arm **on the fetch frame** (not one frame early — the ROM never takes the 6581 precaution).
   - **`HP_ENGINE`** (V1) — the ROM's per-instrument pulsework re-implemented in 6502 (`pulse_step`): live PW state per ROM instrument (`HPMAP` slot→instrument), per-voice delay/direction, both bounce/fast-PWM modes, poked initial counters. Pulse is 100% *by construction* (it IS the engine). Held only on a voice's own fetch frames.
   - **`TEMPO_SWALLOW`** (V2) — a poked countdown (`SWC $19CC` / `SWP $19CD`) skips the row-tick dec every Nth frame. `SWP==0` = off (an unpoked driver otherwise swallows *every* tick → silence).
   - **`FMSCALE_ON`** — off for Hubbard (real Hz drum dives reach the `$40-$43` scaled-vibrato marker range).
4. **Emit** — greedy nearest-merge bundle clustering + adaptive window-splitting keep each part inside the 63-bundle / 32-instrument / `$D000` caps; `HUBBARD_MAX_PARTS` caps builds for quick listens.

The build measures itself with `bin/mon_part_fidelity.py PART SONG SECS OFF0` (semitone-freq / waveform / pulse / filter %) and, for the register blind spots (ADSR / `$D418` / 1-frame gates), a VICE register-stream dump diff.

---

## Fidelity gotchas (learned the hard way)

- **No-release (bit5) chains are TIES**, not retriggers. Emitting them as `$7D` hard-restart rows chopped the sustained bass for 2 frames every 1.28 s — invisible to register-state %, caught by the ear and the VICE dump.
- **ADSR re-arms ON the fetch frame**, after the gate-on write — not one frame early. The 1-frame-early pre-arm cost ~5% of the register-stream match.
- **V2 pulse resets per fetch** — leaving the V1 free-run (`PFREE $08`) flag on froze the first note's ramp forever (Delta pulse 11% → 100% by dropping one flag).
- **Per-voice init instruments** — Last_V8's silent-pulse voices were reading instrument 0's PW instead of the ROM's per-voice defaults.
- **A pulse% near zero can be pure phase.** `5_Title_Tunes_song0_part01` osc3 reads
  **pulse 4.5%** with a single unbroken 596-frame residual run — which looks like a dead
  pulse engine and is a **-3-frame offset** (90.6% at that lag). `mon_part_fidelity` now
  prints a phase-invariant `pul shape` line beside it (that voice: moves 279/279, travel
  35712/35712 = identical motion). The tool's per-voice delay refinement aligns by **freq**
  only, so a voice whose pulse writes sit a few frames from its freq writes stays
  misaligned in that column. See PATTERNS.md D9 — and read the shape line only as "the
  motion is the right size", never as a pass.
- **The vacuous-100.0 trap:** `mon_part_fidelity` with `secs=0` computed a negative window → empty comparison loops → a *fake* 100.0. A silent SF2 measured perfect. Always pass a real window that fits the part (song length for jingles; `off0` = part start).
  - **Sequel (2026-07-16): fixing it here did not fix the class.** Every sibling scorer kept its own private `100.0 * ok / tot if tot else 100.0` — 11 files, including two *builders* where the fabricated score fed a real A/B decision. Now canonical: `sidm2.fidelity_common.score_pct()` returns **None** on an empty comparison and `fmt_pct` prints `n/a`; None cannot be silently compared. If you write a new scorer, use it.
- **"filter 100%" was VACUOUS — Hubbard never uses the filter.** zig64 over 1000 frames of Monty (and Delta sub11): **zero** cutoff/resonance writes; `$D417` routing never written, so no voice is even routed. `$D418` is written once for volume. The metric therefore compared `0 == 0` a thousand times — **any driver that ignores the filter entirely scores 100%.** This is the *degenerate* cousin of the empty-comparison trap and `score_pct` cannot see it (`tot`=1000, not 0); catching it needs a **distinct-value check**. The number was real and meant nothing. Corrected in `docs/reference/ACCURACY_MATRIX.md` 2026-07-16.
- **The metric never compares `$D417` resonance/routing or `$D418` mode** — "filter" means cutoff only. A real blind spot, not just a Hubbard one.
- **`bin/hubbard_validate.py` is V1-only and fails SILENTLY on V2.** It reads Delta sub11 at 23–25% because it computes onsets as `tk*fpt`, ignoring `swallow_period=5` (Monty period=0, Delta period=5). That is not a refutation of Delta — it is a validator returning a meaningless number for a whole class instead of refusing. Contradicts this project's fail-loudly rule; use `mon_part_fidelity.py` for V2 until fixed.
- **Play-routine spin class:** several rips (Last_V8, Tarzan, …) spin forever on a bare py65 — 2M steps × thousands of frames = a 3-hour replay that killed the corpus batch. Use `sidm2.cpu6502_emulator` with the `$D012` raster fake (`measure_tick_schedule`, `HPReplay`, `initial_instruments`, `swallow_state`).
- **`HP_ENGINE` fast-PWM mode ("lo += pulseval per frame") is NOT what the ROM
  does — it's a flat model of a genuinely faster, periodic clock.** Found via
  `Commando_song2` (2026-08-08), root-caused by disassembling the exact ROM
  routine the driver's own comment cites (`$5230`, `SID/Hubbard_Rob/Commando.sid`):
  `$5237-$5240` is `LDY $5518 / LDA $5591,y / ADC $5507 / STA $5591,y` — a flat
  per-frame add of the instrument's pulse-speed byte (`$5507`, set once per
  note-fetch at `$51b6` and confirmed constant through the sustained note, not
  recomputed per frame). The driver's `pulse_step` (`drivers_src/mon/
  romuzak_driver.asm`, HP_ENGINE fast-PWM branch) implements exactly that flat
  model. But the REAL register stream over a sustained fast-PWM note doesn't
  step flatly: 6 of every 8 frames advance by `pv`, 2 of 8 advance by `2*pv` —
  a genuine **1.25x rate deficit** (30 units/8 frames real vs 24/8 modelled),
  not measurement noise (pv itself was confirmed constant across the window,
  so it isn't the step VALUE changing). Likely a separate/faster pulse-clock
  in the ROM not yet traced to its source (the producer code above is the
  *consumer* of the call frequency, not what sets it — the IRQ/timer setup
  hasn't been disassembled).
  - **Does NOT falsify the documented "pulse 100%" claim.** Re-tested both
    `Monty_on_the_Run_song0` (2802-frame window, the part's full ~56s) and
    `Zoids_song0` (386-frame window, its full loop) — both hold at
    100.0/99.9-100.0/99.9-100.0. The claim was always about main themes and
    survives on a longer window than it was likely first tested with.
  - **But it's real on OTHER subtunes of the SAME files.** `Zoids_song2` —
    same file, same fast-PWM instrument bank as the clean `song0` — reads
    96.5/96.5/96.6% pulse, the identical song0-clean/song2-drifts pattern as
    Commando. Severity varies a lot: Zoids_song2 mild (96.5%), Commando_song2
    severe (14.3%) — likely depends on the specific instrument's `pv` value
    and how long a note sustains, not a single universal constant.
  - **The IRQ/timer setup was disassembled (2026-08-09) — there isn't one.**
    `init` (`$5fb2-$5fc4`) is a 4-line subtune-select dispatcher; it never
    touches `$FFFE/$FFFF`, CIA, or VIC timers. Every call traces back to ONE
    per-frame entry (`play` = `$5012` → `$5052`), gated by a single tick
    counter (`$5054: DEC $5513`) that branches between note-fetch (once every
    `fpt` frames) and the freq-slide+pulsework block (the other frames) — no
    separate/faster clock exists to find.
  - **The real mechanism, fully verified by instruction-level trace, not
    inference:** all three of Commando_song2's voices share ONE instrument
    (10) for the whole drift window (`decode_song` confirms tick 8-32, frames
    48-96) — a three-way chord on one fast-PWM instrument. Tracing actual PC
    execution (not just the register symptom) at `$523d` (`ADC $5507`) shows
    the per-instrument pulse-speed byte is `pv=1` (constant across the
    window, confirmed), and the ROM code has **no `CLC` before that ADC** —
    it inherits whatever carry the SAME voice's own preceding freq-slide
    computation (`$5205-$521e`, immediately before, no intervening flag-
    clearing instruction) happens to leave set that frame. `HPReplay.
    state_at(frame)['live_pw']` (existing py65-replay machinery in
    `bin/build_hubbard_native_song.py`, previously only sampled once per
    part to seed the modelled engine's initial phase) reproduces this
    EXACTLY when sampled every frame — confirmed byte-for-byte against the
    siddump trace.
  - **A driver fix was attempted and reverted — same day, same session.**
    Moved the fast-PWM add out of `pulse_step` into `fm_step`'s own per-voice
    loop, immediately after its own frequency ADC, with no `CLC`, matching
    the ROM's instruction adjacency exactly (per-voice interleaved, not a
    naive top-level JSR swap — a coarse subroutine reorder was checked first
    and shown NOT to work, since each per-voice loop iterates all 3 voices
    internally before the other starts, so carry would still belong to the
    wrong voice). Assembled cleanly after trimming ~56 bytes of new code
    down under a real `DRIVER STATE-REGION OVERLAP` budget the growth first
    tripped (`$16CC-$1702`, SF2II's live playback-state region — confirmed
    via a direct 64tass assemble + zero-byte-region check, not guessed).
    **Verified NOT to change a single output byte** — PC-traced the new code
    at runtime (hits `fmhp_step` 3 times/frame, every frame, exactly as
    designed) and it computes the IDENTICAL flat result as before. Root
    cause: the MODELLED driver's frequency engine (`fm_write`, `vfreq +
    FM_ACC` from parsed FM-offset tables) is a **different algorithm** from
    the ROM's raw 16-bit slide loop — both converge on the same numeric
    frequency, but the modelled engine's own arithmetic never happens to
    overflow the way the ROM's does, so its ambient carry is always 0.
    "Inherit whatever carry is lying around" only works if the SAME
    arithmetic produces it; a numerically-equivalent but structurally
    different computation doesn't share carry history. **Reverted** (`git
    checkout`) rather than leave inert, non-functional complexity in a
    driver shared by MoN/ROMUZAK/Galway — confirmed via `git diff --stat`
    showing zero changes and a full suite re-run (1888/7/2, unchanged).
  - **Why the existing `HUBBARD_PULSE_ENGINE=0` fallback isn't the fix
    either**, tried and measured before the driver-patch attempt above: it
    disables `HP_ENGINE` for the whole file and falls back to captured/
    canonical pulse bundles. On `Commando_song2` that moved 14.3% → 74% (a
    real improvement — proof the flat model IS the dominant error) but not
    to 100%: byte-exact for frames 0-191, then diverges starting EXACTLY at
    frame 192, and again at 288 — the note-repeat/loop boundaries (period 96
    frames). Root cause: the canonical-bundle emitter captures ONE pulse
    sequence per unique {instrument, pattern} and reuses it on every repeat,
    which is correct for instruments that reset per note but wrong here —
    instrument 10's PW is a continuously-accumulating global that NEVER
    resets between repeats, so replaying a bundle captured at the first
    occurrence gives stale values at the second and third. Confirmed safe
    for `song0` under the same flag (99.7-100%, unchanged), so the fallback
    itself isn't harmful — it's just architecturally the wrong tool for a
    non-resetting accumulator. This is exactly why `HP_ENGINE`'s live-
    accumulation design is the right idea for this instrument class; only
    its per-frame step FORMULA is wrong.
  - **The correct fix, not yet built:** don't try to reproduce the ROM's
    carry incidentally — derive the true per-frame "does this instrument get
    `pv` or `pv+1` this frame" schedule from `HPReplay` at BUILD time (it
    already has the ground truth, verified exact) and bake it as a per-frame
    bitmap the driver reads and adds explicitly, the same pattern this
    driver already uses for `TEMPO_SCHED`/`SCHEDTAB` (an empirically-derived
    per-frame stretch bitmap for irregular tempo, `measure_tick_schedule`).
    Live accumulation stays the underlying mechanism (per the captured-
    bundle failure above) — what's missing is only the EXTRA-STEP schedule,
    not the accumulation model itself.
  - **How much of the corpus this would actually help — surveyed
    2026-08-09.** Checked all 14 of the "real, reproducible" residual files
    (see the `out/hubbard` staleness bullet above) for the mechanism's two
    ingredients: does the tune even use a fast-PWM instrument, and does more
    than one voice share one. `decode_song`'s own voice/instrument timeline,
    not inference from the register symptom.
    - **1 of 14 (`Action_Biker_song0`) uses NO fast-PWM instrument at
      all** — its residual is a different, unrelated bug; this fix would
      not touch it.
    - **13 of 14 DO use fast-PWM instruments** — `5_Title_Tunes_song1`
      (compilation-rip, resolves to module 1 via `detect_module_map`),
      `Chimera_song0`/`song1`, `Gremlins_song0`/`2`/`3`/`4`/`6`,
      `Star_Paws_song0`, `Delta_song0`,
      `Geoff_Capes_Strongman_Challenge_song3`,
      `One_Man_and_his_Droid_song0`, `Zoids_song2`.
    - Of those 13, only **3 show explicit multi-voice sharing**
      (`Gremlins_song2` v1&v2@instr7, `Gremlins_song6` v1&v2@instr21,
      `One_Man_and_his_Droid_song0` v1&v2@instr13) — the Commando-shaped
      case, severe and uniform across voices because a chord compounds it.
    - **Voice-sharing is NOT a precondition for the bug, only for its
      SEVERITY.** The root cause (missing `CLC`, carry inherited from that
      SAME voice's own frequency slide) needs only ONE voice's own
      portamento/vibrato to overflow a byte boundary that frame — it does
      not require another voice touching the same instrument. So the other
      10 files (fast-PWM present, no detected sharing) are PLAUSIBLE single-
      voice cases, not ruled out — just not individually confirmed the way
      Commando_song2 was (`HPReplay` vs. the flat model, byte-for-byte).
    - **Net: the baked-schedule fix would plausibly help up to 12 of 14
      files** (everything except `Action_Biker_song0`, which needs separate
      diagnosis, and the still-unverified single-voice cases) — this is a
      corpus-wide fix candidate, not a one-off patch for Commando.
- **`out/hubbard/*.sf2` is a build cache, not a source of truth — it goes stale
  silently.** `out/` is `.gitignore`d entirely (not a tracked-vs-untracked
  question, it's simply not in the repo), so nothing enforces that what's on
  disk matches what the CURRENT `bin/build_hubbard_native_song.py` would
  produce. Scoping the pulse best-lag question (2026-08-08) swept 85 first-
  parts and found 44 voice-rows with pulse% below 99.5% not explained by a
  simple frame lag; checking each against a FRESH rebuild found 5 of ~18
  distinct files were STALE — `Commando_song16` (the on-disk part was a
  mis-decode; a fresh build now REFUSES outright at "span 1134s exceeds
  900s"), `Last_V8_song11`, `Deep_Strike_song0`, `Auf_Wiedersehen_Monty_song0`
  (marginal, 98.4%→99.9%), `Saboteur_II_song0` (74.7%/34.1%→99.6%/99.6%).
  A/B-verified this session's own `7bb89d7` ($D418 fix) was NOT the cause —
  rebuilding Saboteur_II against the PRE-fix driver gave the same 99.6%.
  **Always rebuild before trusting a fidelity number from this corpus.** The
  other ~13 checked files (5_Title_Tunes_song1, Chimera_song0/song1,
  Commando_song2, Gremlins_song0/2/3/4/6, Star_Paws_song0, Action_Biker_song0,
  Delta_song0, Geoff_Capes_Strongman_Challenge_song3,
  One_Man_and_his_Droid_song0, Zoids_song2) reproduced their exact original
  numbers on a fresh rebuild — those ARE real, open pulse-engine residuals,
  not staleness. `Commando_song2` stands out as the cleanest lead: all three
  voices read EXACTLY 14.3% pulse, a suspiciously round, uniform number across
  independent voices that smells more like a systematic bug (comparison
  window, alignment, or a single shared cause) than three separate per-voice
  content divergences — worth investigating first if this thread is picked
  back up.

---

## Corpus status (2026-07-08)

| Class | Files | Native build |
|-------|-------|--------------|
| **V1** (Monty, Commando, Zoids, Gremlins, Master_of_Magic, One_Man, Last_V8, Last_V8_C128, Geoff_Capes, Crazy_Comets, Chimera, 5_Title_Tunes) | 12 | ✅ built + validated subsongs; pulse/freq/filter 100% |
| **V2 split-songs** (Action_Biker, Confuzion, Gerry_the_Germ, Hunter_Patrol, Ninja, Thing_on_a_Spring) | 6 | ✅ built (97–100% onsets) |
| **V2 swallow — Delta** | 1 | ✅ theme (s11) freq/pulse/filter 100%, wf 85–96% |
| **V2 swallow — rest** (Lightforce, Sanxion, Saboteur_II, Shockway_Rider, Star_Paws, Auf_Wiedersehen_Monty, Deep_Strike) | 7 | ✅ **assemble + play** — pulse + waveform + filter **100%** (state-region fix 5c0de20 + captured-pulse fix 43ad2d2); freq ~86% (a 1-frame-per-swallow-period pitch blip — note-trigger timing under the tempo stretch, an open FM-alignment item; see HUBBARD_V2_PLAN.md Front 1b) |
| **Spin class** (Devils_Galop, I_Ball, Wiz) | 3 | ⚠️ build times out (play-routine spin during trace) |
| **Format laggards** | ~7 | 🚧 IK+ (V0 decode runaway + percussion note bytes), Thundercats 68% (note-format), Tarzan (speed-addr misdetect), Mega_Apocalypse (runaway), Knucklebusters (per-voice speed), Game_Killer (tick stretch with NO swallow sig — the `measure_tick_schedule` empirical grid validates it 100%; needs driver wiring) |
| **No-signature** | 6 | ❌ Casio_Extended / Robs_Life / Era_of_Eidolon / Task_Force / Dont_Step_on_My_Wire / Up_up_and_Away — a different/later player, unexplored |

**~19 distinct tunes build today; ~28 decode ≥95%.** The two biggest unlocks remaining: (a) the state-region relocation (turns 7 validated files playable), (b) the spin-class trace path.

### Stage A open defect: `Kings_of_the_Beach_intro` is missing music (1 of 89)

Measured 2026-07-30 (`pyscript/sf2_truncation_sweep.py hubbard`): it needs **153**
sequences, Driver 11's pointer table holds **128**, so **25 are dropped** — along
with the orderlist entries referencing them. It now says so on stderr instead of
failing silently, but it is **not fixed**.

It is the one affected builder that **cannot use the shared windower**
(`sidm2/d11_windowing.py`). Both planners there rely on a position that means the
same thing in every voice; Hubbard has none. Each voice walks its **own** pattern
list (`m.track_patterns(song, v)`), and measured on this file the voices are
wildly different lengths — orderlists **294 / 322 / 14** entries, totalling
**177212 / 153105 / 12887** rows. Voice 3 is 7% the length of voice 1 and loops
independently, so there is no common row or entry index to cut on: a row cut
would leave voice 3 empty for most of the song, and an entry cut lands at a
different musical position in each voice.

Fixing it properly means either modelling Hubbard's per-voice loop structure
across parts, or reducing the sequence count upstream. Deliberately not guessed
at — an unsound split would trade silent truncation for silent desync, which is
worse because it looks like it worked.

---

## Files

| File | Role |
|------|------|
| `sidm2/hubbard_parser.py` | V1+V2 parser (signature-located tables, module map, swallow, v2 notes/tracks, init instruments) |
| `bin/hubbard_validate.py` | onset validation vs `siddump` |
| `bin/hubbard_to_sf2.py` | Stage A (editable Driver-11 transpile) |
| `bin/build_hubbard_native_song.py` | Stage B shim + `HPReplay` + adaptive windowing |
| `bin/build_mon_native_song.py` | the shared native builder (MoN + ROMUZAK + Hubbard) |
| `drivers_src/mon/romuzak_driver.asm` | the shared native SF2 driver |
| `bin/hubbard_build_all.py` | corpus batch runner (sequential, timeout-proof) |
| `docs/analysis/hubbard/chacking5_monty_disassembly.txt` | ground-truth Monty disassembly |
| `pyscript/test_hubbard_parser.py` | parser regression tests |

**Memory:** `memory/hubbard-player-re.md` (the complete arc log with every gotcha).
