# The native SF2 drivers we authored (target reference)

Most of this project *converts* from a C64 player. But for the trace-driven ports
(Galway, MoN, ROMUZAK, Hubbard) the **target** is not stock SF2 Driver 11 — it's a
**from-scratch native SF2 driver we wrote in 6502**, loaded by unmodified SID Factory
II. This doc is the reference for those drivers: what they are, their memory map, and
the feature flags that specialize one shared driver per source player.

For the *method* that produces the data these drivers play, see [PLAYBOOK.md](PLAYBOOK.md).
For each source player, see its own doc ([GALWAY](GALWAY.md), [MON](MON.md),
[ROMUZAK](ROMUZAK.md), [HUBBARD](HUBBARD.md)).

---

## Two driver codebases

| Driver | Source | Serves | Lines |
|--------|--------|--------|-------|
| **Galway native** | `drivers_src/galway/galway_driver.asm` | Martin Galway | ~1,320 |
| **Shared trace driver** | `drivers_src/mon/romuzak_driver.asm` | Maniacs of Noise, ROMUZAK, **Rob Hubbard** | ~1,920 |

The shared driver started as the ROMUZAK/MoN driver and grew feature flags as each
new player needed them; Hubbard reuses it wholesale. (`drivers_src/romuzak/` holds
the ROMUZAK-specific `layout.inc`/build glue; the `.asm` is the `mon/` one.) The
long-term plan ([../ROADMAP.md](../ROADMAP.md)) is to unify Galway into this shared
driver too — they are ~80% the same interpreter.

---

## What a native driver *is*, in SF2 terms

SID Factory II loads a driver as a binary blob plus a descriptor. The driver owns
three responsibilities SF2II calls each frame:

1. **INIT** (`$1000`) — one-time setup; SF2II calls with A = subtune.
2. **PLAY** (`$1003`) — called once per video frame; advances the sequencer and
   writes `$D400-$D418`.
3. **The editable tables** — sequences, orderlists, instruments, and the wave /
   pulse / filter programs the editor shows and lets the user change. Editing a
   table changes playback because the driver *interprets* these tables live.

Our drivers implement the full SF2 sequence/orderlist/instrument model plus per-voice
**program interpreters** (FM/pitch, pulse, wave, filter) walked by a 16-bit pointer —
this is what lets a 9-minute Ocean Loader or a dense Hubbard tune stay editable
instead of being an opaque embedded player.

---

## Memory map (shared trace driver)

The single hardest constraint: SF2II **reads and writes a pinned playback-state
region every frame**, so driver code and tables must not occupy it.

| Range | Owner | Notes |
|-------|-------|-------|
| `$1000-$1005` | INIT / PLAY / STOP entry vectors | fixed |
| `$1006-~$1623` | driver code | the main interpreter bank |
| `$16CC-$1702` | **SF2II PINNED playback-state** | **must stay clear** — code/tables here crash on play (the `.cerror` guard enforces it) |
| `$1710-$17xx` | freqtable | pinned above the state region |
| `$1800-$187F` | per-voice scratch (VWI, FM_*, PPTR, filter state, …) | driver RAM |
| `$1890-$193C` | out-of-line handlers | `pn_hr`, `fm_hrarm`, `fm_scaled`, `pl_loop`, `hp_init0` — moved here when the main bank hit the `$16CC` cap |
| `$1940-$19BF` | HP pulse-engine tables | `HPVAL/HPFX/HPW_LO/HPW_HI` (poked per instrument) |
| `$19C0-$19FF` | HP + swallow runtime state | `VINST/PDLY/PDIR/HPSKIP`, `SWC/SWP`, `HPMAP` |
| `$1A00+` | **edit area** | sequences, orderlists, instruments, and the wave/pulse/filter/FM/pulse-program tables — the hard upper wall for everything below |
| … up to `$D000` | tables + song data | the memory wall (`$D000` = ~9 min of play-calls) |

**This map is exactly where V2 currently breaks:** swallow-class tunes with filter
programs push tables down into `$16CC-$1702` and fail the `.cerror` guard. See
[HUBBARD_V2_PLAN.md](HUBBARD_V2_PLAN.md).

---

## Feature flags (`layout.inc`, set per tune by the build)

The build (`bin/build_mon_native_song.py` / `build_romuzak_native_song.py`) emits a
`layout.inc` that switches driver features on per source player. All default off →
the driver is byte-identical to the MoN baseline (regression-checked every change:
Hawkeye sub3 = 100/100/100/100).

| Flag | Player | Effect |
|------|--------|--------|
| `TEMPO` / `TEMPO2` / `MULTISPEED` | all | tick period; swing short-period; multispeed calls/frame |
| `NOTE_PREAMBLE` | MoN (Supremacy) | every retrigger plays freq `$0000` + wf `$41` for one frame (the engine's hard-restart) |
| `HARD_RESTART` | Hubbard | release "kill ADSR" (`$7D` rows) + per-retrigger ADSR re-arm **on** the fetch frame |
| `FMSCALE_ON` | MoN/ROMUZAK (on); Hubbard (off) | enables the scaled-vibrato FM entry (`$40-$43` hi marker) — off where real Hz deltas reach that range (Hubbard drum dives) |
| `HP_ENGINE` | Hubbard V1 | the per-instrument pulse engine (the ROM's pulsework in 6502; pulse exact by construction) |
| `TEMPO_SWALLOW` | Hubbard V2 | poked countdown `SWC/SWP` skips the row-tick dec every Nth frame (fractional tempo). `SWP==0` = off |
| `DIGI_SPIKE/NCO/HYBRID/SWEEP/RLE` | Galway | `$D418` digi-sample playback (sawtooth NCO + PCM hybrid) |

---

## Per-voice program interpreters (the editable engine)

Each voice runs four interpreters per frame, in order (a note's RESET takes effect
the *same* frame — pulse/filter run after `do_row`):

- **`fm_step`** → `$D400/1`: walks FMTAB via a 16-bit pointer, accumulating a signed
  Hz offset onto the note's base freq. Entry types: freeze, Hz-delta run, `$7F` loop,
  `$80-$FF` semitone-hold (structural arps, pitch-independent).
- **`pulse_step`** → `$D402/3`: either the **HP engine** (`.if HP_ENGINE`, Hubbard V1)
  or the standard set/add/`$7F`-loop PULSETAB walk (MoN, Hubbard V2).
- **`wave_step`** → `$D404`: 2-column wave program (waveform, semitone), one row/frame,
  gate bit preserved via a per-voice AND-mask.
- **`filt_prog_step`** → `$D415/6/7` + mode: one global filter program, set/add/loop,
  started by a flagged (`$40`) instrument and restarted per note on the routed voice.

The `$C0-$FF` sequence command channel selects a per-note **(FM, pulse) bundle** — how
one 32-instrument table serves thousands of distinct per-note synth shapes.

---

## Fidelity ceiling reached

| Player | freq | waveform | pulse | filter |
|--------|------|----------|-------|--------|
| MoN (Hawkeye sub2/3) | 100 | 100 | 100 | 100 |
| ROMUZAK | ~100 | byte-exact | byte-exact | — |
| Galway (Wizball/Ocean Loader full) | ~100 | 100 | ~100 | 100 |
| Hubbard V1 (Monty/Commando/Zoids/Last_V8) | ~100 | 100 | **100** | 100 |
| Hubbard V2 (Delta theme) | 100 | 85-96 | 100 | 100 |

All measured by `bin/mon_part_fidelity.py` (semitone-freq / waveform / pulse / filter)
and cross-checked by the VICE register-stream dump for the ADSR/`$D418`/gate blind
spots the % metric can't see.
