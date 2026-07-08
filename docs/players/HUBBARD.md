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
- **The vacuous-100.0 trap:** `mon_part_fidelity` with `secs=0` computed a negative window → empty comparison loops → a *fake* 100.0. A silent SF2 measured perfect. Always pass a real window that fits the part (song length for jingles; `off0` = part start).
- **Play-routine spin class:** several rips (Last_V8, Tarzan, …) spin forever on a bare py65 — 2M steps × thousands of frames = a 3-hour replay that killed the corpus batch. Use `sidm2.cpu6502_emulator` with the `$D012` raster fake (`measure_tick_schedule`, `HPReplay`, `initial_instruments`, `swallow_state`).

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
