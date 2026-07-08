# Hubbard V2 — the plan to finish it

Status (2026-07-08): V2 is **decoded** (parser onset-validates 100% on Delta, Sanxion,
Lightforce, Saboteur_II, Star_Paws, Wiz, Auf_Wiedersehen_Monty, Deep_Strike, …) and
**one tune fully plays** (Delta theme: freq/pulse/filter 100%). The remaining work is
four bounded fronts, ordered by leverage. See [HUBBARD.md](HUBBARD.md) for the format
RE and [NATIVE_DRIVER.md](NATIVE_DRIVER.md) for the driver memory map.

---

## Front 1 — the state-region overflow ✅ FIXED (2026-07-08, commit 5c0de20)

**Resolution:** relocated the four tail data tables (`sidbase`/`frbits`/`ollo`/`olhi`,
12 bytes) from their inline position at the code-bank end (`$16C1-$16CC`) into the free
13-byte gap above the state region (`$1703-$170F`, below the freqtable). The overflow
was those tables' last byte landing on `$16CC` under the full V2 flag set — a 9-line
driver change, no interpreter logic touched. Lightforce/Sanxion/Saboteur_II confirmed
assembling; regression anchors clean (Hawkeye sub3 100/100/100/100, Monty part1
100/99.8/100, Delta theme 100/96/100). Lightforce now plays waveform 100 + filter 100
(freq 85-98; **pulse still needs the free-run polish — moved to the cross-cutting
list**, same class as Delta's wf residual).

*Original diagnosis (kept for the record):*

**Symptom:** `Lightforce, Sanxion, Saboteur_II, Shockway_Rider, Star_Paws,
Auf_Wiedersehen_Monty, Deep_Strike` decode 100% but fail assembly with
`DRIVER STATE-REGION OVERLAP $16CC-$1702`.

**Root cause (diagnosed, not guessed):** it is **not** a table spill — all tables sit
high ($4106+). The verbose guard reports exactly **1 non-zero byte at `$16CC`**, with
`drv_end=$1932`. The driver's **main code bank grows from `$1000` up to exactly
`$16CC`** when the full V2 flag set compiles together (`HARD_RESTART` + `TEMPO_SWALLOW`
+ the always-compiled filter interpreter) — its last byte lands one byte into SF2II's
pinned playback-state region (`$16CC-$1702`, reserved by `* = ST_FIRST / .fill`). The
code bank is ~1740 bytes and has run out of room below the state wall.

Delta escapes only because the parts I built manually predate the final `TEMPO_SWALLOW`
additions; a fresh full-flag Delta build hits the same wall.

**Fix (driver surgery, ~1 hr, one regression gate):** reclaim main-bank bytes so the
code ends below `$16CC`. Options, cheapest first:
1. **Move the `TEMPO_SWALLOW` `do_play` block out-of-line** — it sits in the hot
   per-frame path but is only ~9 bytes; relocate to the `$1890` out-of-line region
   (JSR round-trip) or fold it into an existing dispatch. Reclaims enough alone.
2. **Relocate a cold routine** (STOP handler, an init helper) out-of-line to `$1890+`
   (there is room up to `$1940` before the HP tables).
3. **Structural:** raise the freqtable (`$1710`) and the whole post-state layout by a
   page and let the code bank breathe — bigger change, only if 1–2 don't suffice.

**Regression gate:** after any driver change, rebuild + re-measure **Hawkeye sub3
(MoN, must stay 100/100/100/100), Monty part1 (V1), and Delta theme** — all on REAL
windows (never `secs=0`; see the vacuous-100.0 note in HUBBARD.md). Then rebuild the 7
files and confirm they assemble + spot-measure part1.

**Payoff:** 7 validated tunes become playable. This is the single highest-value fix.

---

## Front 2 — the play-routine spin class (3 files)

**Symptom:** `Devils_Galop, I_Ball, Wiz` builds time out (>90 min). The batch now
survives them (`TimeoutExpired` caught) but produces no output.

**Root cause:** the *trace* generation (`mon_fidelity.per_frame` / `filter_trace`)
drives the original SID; these rips' play routines spin without the raster fake, so
each frame runs to the step cap. We already fixed this class for `HPReplay` /
`measure_tick_schedule` by routing through `sidm2.cpu6502_emulator` with the `$D012`
increment — the **trace path** (`bin/mon_fidelity.py`, `filter_trace`) needs the same
treatment, or must confirm it already uses `siddump` (which has the raster fake) and
the hang is elsewhere (e.g. a `count_only` probe loop).

**Fix (~1–2 hr):** profile one (`HUBBARD_MAX_PARTS=2` build under `cProfile`) to
confirm the sink is the trace vs the adaptive `fits()` probe loop, then route the
offending replay through the raster-fake CPU. Likely shares a fix with Front 1's
regression once the trace path is confirmed.

---

## Front 3 — the note-format / speed laggards (~6 files)

Each is a small, isolated RE, tackled with the same method (py65 watch + disassemble
the divergent frames), roughly ascending difficulty:

| File | Onsets | Diagnosis | Approach |
|------|--------|-----------|----------|
| **Game_Killer** | 22% → **100%** (measured) | tick stretch every 10 frames, **no swallow signature** | the `measure_tick_schedule` empirical grid already validates it; wire that grid into the shim capture + poke an approximated period/phase into `TEMPO_SWALLOW` (or a schedule-table driver mode) |
| **Thundercats** | 68% | a note-format detail (content matches, timing/pitch slips) | frame-diff the divergent notes; likely a 4th note-byte or a transpose the decoder drops |
| **Tarzan** | 41% | speed address **mis-detected** (the `DEC speed` signature finds the wrong counter); play needs the raster fake | fix the speed-signature disambiguation for this variant |
| **IK_plus** | 62% | V0 pattern decode **runs away** + V2 percussion **pitch bytes differ** | the runaway is a missing terminator/format byte in V0's track; percussion is a per-voice note-encoding delta |
| **Mega_Apocalypse** | 53% | decode runaway | same class as IK+ V0 |
| **Knucklebusters** | 25% | **per-voice speed** (each voice its own tempo) | needs a per-voice tick counter in the shim + driver (V2 already has one-swallow; extend to three) |

---

## Front 4 — the no-signature files (6 files, exploratory)

`Casio_Extended, Robs_Life, Era_of_Eidolon, Task_Force, Dont_Step_on_My_Wire,
Up_up_and_Away` match neither the V1 songs-copy nor the V2 split-songs signature. They
cluster together on opcode-skeleton similarity (`Go_Go_Dash`/`Lion_Heart`/… were a
related cluster), suggesting a **third player generation** (or a non-Hubbard routine
mislabeled in the corpus). Unknown scope — treat as a fresh mini-RE: pick one
exemplar, map its play routine, decide if it's worth a signature or a one-off.

---

## Cross-cutting (affects V1 too)

- **Editor `???` rows:** the `$7D` hard-restart rows and out-of-range drum notes have
  no SF2II display name → shown as `???`. Playback is correct; a friendlier encoding
  (or a display-only remap) would clean the editor view.
- **Part-count compression:** dense tunes (Delta s0 = 385 s) fragment into 2-second
  parts at the 63-bundle cap. The `MON_ARP_STRUCT` structural path packs a whole song
  into ONE part (proven: Delta s11 = 1 part, 6 bundles) but its canonical wave/pulse
  substitutions misfire on Hubbard (pulse → 2%). Port the good structural prongs
  selectively (the freerun-pulse detection is already un-gated via `shim.freerun_pulse`).

---

## Suggested order

1. **Front 1** (state-region) — 7 files, ~1 hr, highest leverage. Do this first.
2. **Front 2** (spin class) — 3 files, shares diagnostics with Front 1's regression.
3. **Front 3** — pick off Game_Killer (already validated), Thundercats, Tarzan.
4. **Front 4** — one exemplar, scope decision.
5. Cross-cutting polish (Delta wf texture, `???` encoding, part compression) as time allows.

**Definition of done for V2:** all signature-matched files assemble + play; the
no-signature cluster either supported or explicitly documented as out-of-scope; the
accuracy matrix and HUBBARD.md updated with the final per-file fidelity.
