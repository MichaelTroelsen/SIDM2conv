# Martin Galway player — SID → SF2 support

**Composer:** Martin Galway
**Corpus:** `SID/Galway_Martin/` (40 `.sid` files)
**Registry key:** `galway` (`sidm2/driver_selector.py` → `PLAYER_REGISTRY`)
**Status (v3.11.0):** trace-driven native driver reaches **~100% on every SID register** for validated tunes in stock SID Factory II.

---

## How Galway is converted

Galway is **not** a flat table-driven player. Each voice is driven by a **per-channel bytecode interpreter** with self-modifying pokes, `For`/`Next` loops, and a per-frame FM/PM synth — so there is no static "note table" to read. SIDM2 has two paths:

### 1. Trace-driven native build — *highest fidelity* (`bin/build_galway_trace_song.py`)
Runs the **real player** through the cycle-accurate zig64 tracer (`tools/sidm2-sid-trace.exe`) and reconstructs the song from the actual per-frame SID output: note onsets, base pitch, the FM slide/vibrato envelope, the pulse-width envelope, and the global filter — then replays them through a **from-scratch native Galway SF2 driver** (`drivers_src/galway/galway_driver.asm`). Inherently faithful: it reproduces the player's real behaviour, not a guess.

- Legato voices (held gate, pitch changed by the player) are segmented by **settled-pitch change**, not gate.
- FM slide + pulse envelope are decoupled per note (the `$c0-$ff` command channel).
- Pulse uses a **16-bit-pointer table** (v3.11.0) so a full-length song's PWM fits.
- Measured with `bin/sf2ii_vs_real.py` — diffs an instrumented SF2II's real per-frame output against the original SID, per voice.

Output: `out/galway_trace_song.sf2` (+ a PSID render for WAV A/B). **Not** the default conversion entry point — lives in `bin/`.

### 2. Driver-11 transpile — *editable* (`convert_galway_to_sf2`, the default)
Transpiles the 1st-gen bytecode-extracted score onto a real **Driver 11** SF2 (`sidm2/galway_to_driver11.py`). The editor edits the tables and Driver 11 plays them. Notes/pitch/timing/envelopes are correct; pulse/FM/filter **modulation** is approximated (it lives in Galway's per-frame synth, not static tables). Embedded-player audio is the fallback when score recovery fails.

> The C64 `$D000` memory wall caps one SF2 at ~27,650 play-calls (≈9.2 min at 50 Hz × multispeed). Longer tunes are truncated.

---

## Validated tunes

| Tune | Real-SF2II result (freq / waveform / pulse / AD-SR) | Notes |
|------|------------------------------------------------------|-------|
| **Wizball** (default subtune 4) | osc1 100/100/100/100 · osc2 99/100/99/100 · osc3 100/100/99/100 | Full 135 s, legato; `out/Wizball_full.sf2` (v3.11.0) |
| **Ocean Loader 1** | osc1 100/100/100/100 · osc2 100/100/99/100 · osc3 100/100/100/100 | Full ~9 min, re-gated (v3.10.0) |

All other tunes below are **buildable via the trace-driven path** (it is player-agnostic — it reads the real SID output) but have **not been individually validated**. `play=$0000` means the player installs its own CIA/IRQ at init (resolved by the trace).

---

## Full corpus (40 files)

| File | Init | Play | Subtunes | Default | Status |
|------|------|------|----------|---------|--------|
| Arkanoid | $4000 | $0000 | 20 | 1 | buildable |
| Arkanoid_alternative_drums | $3ef8 | $0000 | 2 | 1 | buildable |
| Athena | $6000 | $6003 | 9 | 1 | buildable (2nd-gen) |
| Combat_School | $1000 | $0000 | 16 | 1 | buildable |
| Comic_Bakery | $7f00 | $7f03 | 14 | 1 | buildable (1st-gen) |
| Commando_High-Score | $081f | $0816 | 1 | 1 | buildable |
| Daley_Thompsons_Decathlon_loader | $4c00 | $4ca8 | 1 | 1 | buildable |
| Game_Over | $0f00 | $0000 | 2 | 1 | buildable (1st-gen) |
| Green_Beret | $9fce | $cff0 | 21 | 1 | buildable (1st-gen) |
| Helikopter_Jagd | $bd80 | $a000 | 16 | 1 | buildable |
| Highlander | $a0a0 | $a0d3 | 1 | 1 | buildable |
| Hunchback_II | $9ee0 | $9000 | 23 | 16 | buildable |
| Hyper_Sports | $3f80 | $2000 | 35 | 26 | buildable |
| Insects_in_Space | $65a3 | $65cb | 24 | 1 | buildable (2nd-gen) |
| Kong_Strikes_Back | $9600 | $8ac9 | 1 | 1 | buildable |
| Match_Day | $c6a0 | $c6d0 | 7 | 1 | buildable |
| Miami_Vice | $f900 | $e0b2 | 2 | 1 | buildable |
| MicroProse_Soccer_V1 | $c000 | $0000 | 14 | 5 | buildable |
| MicroProse_Soccer_indoor | $bc00 | $bc03 | 17 | 8 | buildable |
| MicroProse_Soccer_intro | $9f80 | $0000 | 1 | 1 | buildable |
| MicroProse_Soccer_outdoor | $c035 | $c01a | 8 | 5 | buildable |
| Mikie | $7ce8 | $7cf4 | 12 | 1 | buildable |
| Neverending_Story | $95e8 | $95f4 | 1 | 1 | buildable |
| **Ocean_Loader_1** | $b428 | $a003 | 1 | 1 | ✅ **validated ~100%** |
| Ocean_Loader_2 | $a000 | $a04e | 1 | 1 | buildable |
| Parallax | $bfc0 | $bfe0 | 5 | 1 | buildable |
| Ping_Pong | $e000 | $f780 | 19 | 1 | buildable |
| Rambo_First_Blood_Part_II | $af8b | $afe8 | 23 | 1 | buildable (1st-gen) |
| Rastan | $4900 | $4910 | 6 | 3 | buildable |
| Rolands_Ratrace | $bbea | $a000 | 20 | 1 | buildable |
| Short_Circuit | $9b50 | $9b5c | 5 | 1 | buildable |
| Slap_Fight | $b800 | $b803 | 9 | 5 | buildable |
| Street_Hawk | $7f00 | $7f1e | 26 | 1 | buildable |
| Street_Hawk_Prototype | $8003 | $8000 | 1 | 1 | buildable |
| Swag | $57c0 | $57c7 | 2 | 2 | buildable |
| Terra_Cresta | $b712 | $b703 | 11 | 1 | buildable |
| Times_of_Lore | $4ffe | $4ff0 | 11 | 1 | buildable (2nd-gen) |
| **Wizball** | $6390 | $6600 | 9 | 4 | ✅ **validated ~100%** |
| Yie_Ar_Kung_Fu | $9e00 | $9e40 | 19 | 19 | buildable |
| Yie_Ar_Kung_Fu_II | $bac3 | $baeb | 7 | 1 | buildable |

*Init/play/subtune values are from each file's PSID header. "1st-gen / 2nd-gen" marks the player generation where known from Galway's own source repo (1st: Wizball/Arkanoid/Green Beret/Game Over/Rambo/Comic Bakery; 2nd: Athena/Times of Lore/Insects in Space).*

---

## Build a tune

```bash
# Trace-driven native build (highest fidelity). Args: SID, play-calls, [subtune].
py -3 bin/build_galway_trace_song.py SID/Galway_Martin/Wizball.sid 27000
py -3 bin/build_galway_trace_song.py SID/Galway_Martin/Ocean_Loader_1.sid 27000

# Measure fidelity vs the real SID in instrumented SF2II:
py -3 bin/sf2ii_vs_real.py SID/Galway_Martin/Wizball.sid out/galway_trace_song.sf2 60 4
```

Legato tunes auto-select `TEMPO = multispeed` (one editor row per video frame) for frame-accurate pulse resets.

---

## References
- Engine map: `docs/analysis/GALWAY_1STGEN_ENGINE.md`, `docs/analysis/GALWAY_FM_PM_SYNTH.md`
- Driver plan: `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md`
- Native driver: `drivers_src/galway/galway_driver.asm`
- Source ground truth: github.com/MartinGalway/C64_music (1st-gen players)
