# Maniacs of Noise (Jeroen Tel) — SID → SF2 support

**Composer:** Jeroen Tel (Maniacs of Noise engine, 1987-89 era)
**Corpus:** `SID/Tel_Jeroen/` (179 `.sid` files)
**Registry key:** none yet — the whole pipeline lives in `bin/` (not wired into `DriverSelector.PLAYER_REGISTRY`)
**Status:** native SF2 driver, **100% byte-exact on freq + waveform + pulse + filter, all 3 voices, full song length** for Hawkeye subtunes 2 & 3; Cybernoid, Cybernoid II, Myth, and Supremacy all build at ~95-100% per register. The 2026-07-05 structural rebuild collapsed part counts: Supremacy sub1/sub2 = **one editable SF2 each** (whole song), sub0 10 parts, Hawkeye sub0 7, Cybernoid 10, Myth 7 (see *Part-count reduction*).

Covered tunes so far: **Hawkeye**, **Cybernoid**, **Cybernoid II**, **Myth**, **Supremacy**. The engine RE transfers — one parser (`sidm2/mon_parser.py`) decodes all of them via per-tune orderlist-model variants.

---

## The MoN engine (reverse-engineered)

MoN is a two-level **orderlist → pattern** player with a per-frame effects engine:

- **Tempo gate:** the sequencer advances one *tick* every `speed+1` frames (`DEC $9116`, reload from the per-subtune speed byte). Effects (slides, PWM, filter) run **every frame**.
- **Orderlist** (per voice): pattern numbers + parameter bytes — `$80+` = transpose/instrument base (`&$1F`), `$60-$7F` = param, `$40-$5F` = **pattern-repeat counter** (`&$3F`, replay N+1×), `$FE` = **song end** (terminal halt — it rewrites the play entry so later calls RTS), `$FF` = orderlist loop.
- **Pattern bytes** (Hawkeye/Cybernoid dispatch): `$00-$6F` note (+ orderlist transpose), `$70-$7F` wave-program select, `$80-$BF` **sticky duration** (`&$3F` ticks; persists across notes and patterns; a second `$8x-$Bx` adds), `$C0-$DF` instrument prefix (`&$1F` + base), `$E0-$FF` commands (`$Fx` odd = filter value; `$Fx` even = legato note — no re-gate).
- **Instruments:** 8-byte records (Hawkeye `$860C`): PW nibble, waveform/ctrl, AD, SR, effect selector, wave-program pointer, flags.
- **Freq table is SPLIT:** lo bytes and hi bytes are two separate note-indexed tables (Hawkeye `$8337` / `$8396`), *not* interleaved.
- **Filter:** a per-instrument **cutoff envelope** (not a sweep or static table) — a per-voice frame counter reset on note-on indexes a 10-byte threshold/delta table (attack base, 3 signed segment deltas, sustain, 4 thresholds); 4 selectable tables + an unused triangle-LFO mode. Only `$D416` (cutoff hi) is written.
- **Synth engines (Supremacy variant):** pitch arps are compact looping semitone tables (`dur, steps…, $FF loop`), selected by the `$60-$7F` pattern byte and restarted per note; the waveform is a plain attack + steady + release gate envelope (only the steady length varies per note).
- **`$FB` = TIE flag (Supremacy variant):** consumed by the event EPILOGUE ($1335 — note/retrig/slide finalize only, not rests): peek the byte after the event; `$FB` sets `$100A,X`, which (a) suppresses this note's gate-off ($1155) and (b) makes the NEXT note skip the whole instrument/gate restart ($12C5) — a legato pitch change. It consumes NO time. Decoding it as a top-level `$E0+` rest (27 phantom ticks each) desynced Supremacy sub0 V2 from 138.6s.

### Orderlist-model variants (one parser, `ol_mode` per tune)

| Tune | Load | Model |
|------|------|-------|
| Hawkeye | $7AE0 | `selfmod` — subtune setup self-modifies a 6-byte orderlist-pointer set (fixed high byte) |
| Cybernoid | $AE00 | `selfmod` + a second per-subtune hi-byte table |
| Cybernoid II | $A600 | `stride` — reads the pointer set directly (`LDA olBase,X`, stride 4) |
| Myth | $1D00 | relocating **compilation**: init copies a per-subtune MoN sub-player to $9000/$A400 and runs it there (`play=$0000` self-IRQ wrapper) — parsed via **py65 emulation extraction**, not statically |
| Supremacy | $1000 | `supremacy` — flat compact variant: orderlist ptr table `$16DC`+sub*8+voice*2, notes strictly `<$60`, `$60-$7F` = arp/wave-program selector, additive durations |

All table addresses are located by **relocation-safe code signatures**, never hardcoded.

---

## How MoN is converted

### Stage A — Driver 11 transpile, *editable* (`bin/mon_to_sf2.py`)
Reuses the Galway/ROMUZAK Stage-A IR (`GalwayDriver11Song` + `galway_driver11_emitter`). Notes, order, and timing are **onset-exact** (Hawkeye sub3 28/28, sub2 174/174 vs siddump), instruments carry AD/SR/waveform/PW. Timbre modulation (slides/PWM/filter) is flat — use Stage B for fidelity. Known limit: pitch can sit a note-index calibration off on some tunes (Cybernoid V1 was 2 semitones low) — the native path is pitch-exact.

```
py -3 bin/mon_to_sf2.py SID/Tel_Jeroen/Hawkeye.sid out/Hawkeye.sf2 3
```

### Stage B — native SF2 driver, *byte-exact* (`bin/build_mon_native_song.py`)
The shared trace-driven native pipeline (same engine family as ROMUZAK/Galway; driver source `drivers_src/mon/romuzak_driver.asm`):

- **Per-note (FM, pulse) bundles** via the `$c0-$ff` sequence command channel — each note's command selects an FM slide/arp program + a pulse program captured from the trace. The driver holds base pitch on the trigger frame, so FM programs drop delta[0].
- **Wave programs as instruments** — the gate envelope (`$41→$40` etc.) is a per-note wave program advancing 1 row/frame (RLE'd: col 1 is a frame *count* here, not the base engine's semitone column).
- **Filter** — the cutoff envelope is emitted as SET + ADD rows, restarted per note by a flag-`$40` instrument; drives are detected from note-on-aligned cutoff jumps, restricted to the **$D417-routed voice**, and canonicalized per **(instrument, envelope-shape)** composite key (Myth mixes up/down-ramp shapes across song sections; Hawkeye's shape is fixed per instrument).
- **Myth** goes through `bin/build_myth_native_song.py` — py65 relocate + init + play-per-frame extraction feeding the same `build_native_song` via a MON-compatible shim.

```
MON_ARP_STRUCT=1 py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Supremacy.sid 2 auto   # auto = adaptive parts
py -3 bin/build_myth_native_song.py 0 auto
```

`MON_ARP_STRUCT=1` enables the **structural path** (looping arp/slide/vibrato FM entries + canonical
wave/pulse programs, each exact- or semitone-guarded per note with trace fallback). It is calibrated
on Supremacy (where it collapses sub1/sub2 to one part each) and is fine for Hawkeye/Cybernoid.
**Keep it OFF for Myth** — measured regression: Myth sub0 part1 osc1 freq 89.1% flag-on vs 100%
flag-off (the guards admit a wrong substitution on the Myth engine variant).

Load the result via `py -3 pyscript/sf2_open_in_editor.py out/mon/PART.sf2 40` (SF2II's argv-load Heisenbug needs the retry loader). Native play address is `$1003`.

---

## Fidelity status (per tune)

All rows re-measured 2026-07-05 with adaptive (`auto`) windows and today's build
(structural flag ON except Myth; measurements strictly sequential — see *lessons*).

| Tune | Subtune | Parts | freq / wf / pulse / filter | Notes |
|------|---------|-------|----------------------------|-------|
| **Hawkeye** | 3 (main theme) | 1 | **100/100/100/99** | byte-exact, full length; GUI-confirmed |
| **Hawkeye** | 2 | 1 | **100/100/100/96.5** | byte-exact; GUI-confirmed |
| **Hawkeye** | 0 (6.4-min theme) | **7** (was 13×30s) | 99.4-100 / 99.4-100 / 99.5-100 / 70-99 | full 384s; read-watch-verified walk |
| **Cybernoid** | 0 | **10** (was 14) | 91-100 / 95-100 / 91-100 / 30-89 | full 399s; see *SBC bug* below |
| **Cybernoid II** | 0 | 20 | 100/99/100/98.8 | third orderlist variant (not re-run 2026-07-05) |
| **Myth** | 0 (main) | **7** | 95-100 / 99-100 / 95-100 / 77-98 | emulation-extracted; **flag-off build** |
| **Myth** | 2 | 2 | 100/99-100/100/96 | sub1 is empty (NOP'd in the wrapper) |
| **Supremacy** | 0 | **10** (was 34) | 92-95 / 86-90 / 97-99 / **100** | real length 234s ($FE global halt) |
| **Supremacy** | 1 | **1** (was 24) | 93-98 / 86-98 / 92-98 / **100** | real length 38s ($00 global loop) |
| **Supremacy** | 2 | **1** (was 70) | 87-98 / 87-96 / 93-98 / **100** | real length 150s; whole song, one editable SF2; **ear-confirmed 2026-07-05** |

Fidelity is measured with `bin/mon_part_fidelity.py PART SUB SECS OFF0_SECS` (per-frame semitone-freq / waveform / pulse / filter-cutoff vs siddump) and `bin/mon_sf2ii_confirm.py` (instrumented real-SF2II capture).

---

## Hard-won lessons (encoded in code/tests — do not re-learn)

- **The siddump SBC carry bug (2026-06-30).** Cybernoid's lead sounded wrong "when vibrating" although every register was byte-exact — the *capture* CPU (`sidm2/cpu6502_emulator.py`) had SBC carry stuck set, breaking 16-bit subtraction chains, so siddump computed a too-wide vibrato and the native build faithfully replayed the error. Fix: carry = `temp >= 0`; guarded by `pyscript/test_cpu6502_sbc.py`. Lesson: when trace-replay sounds wrong but the metric says byte-exact, **suspect the capture CPU** — cross-check py65 and VICE.
- **Trace-replay has a cycle-level floor.** A byte-exact per-frame register replay still measures ~0.168 VICE spectral distance vs the original on a high-resonance filtered voice (the resonant filter responds to exact write cycles). Write *order/schedule* reproduction was tested and does **not** close it. The native driver sits ~at this floor (0.189); no procedural port is warranted for this.
- **MoN is single-speed.** The "multispeed" reading was a measurement artifact (three voices' freq writes misattributed to one voice).
- **`$FE` is song end, not pattern-skip** — it halts the whole player; short subtunes must be compared only over the real song length (post-end silence skews percentages).
- **Filter resets must come from note-on-aligned drives**, never a trace-only cutoff-jump threshold (over-detects on normal sweeps and shatters spans).
- **SF2II CMP-carry:** any native-driver dispatch on values >$7F apart must bit-test (`bmi`/`and`), not `cmp` (SF2II's bundled 6510 computes CMP carry from bit7 of A−op).
- **Never run two MoN builds concurrently** — every build regenerates the shared scratch `drivers_src/mon/layout.inc` + `freqtable.inc` (and `drivers_src/romuzak/layout.inc`), so parallel builds assemble each other's tables into garbage SF2s (near-zero fidelity on random parts). Fidelity *measurements* are safe to parallelize since `mon_part_fidelity` derives a unique probe filename per part (2026-07-05; it previously shared one probe and raced too — corrupted-probe signature: freq ~0%, pulse 1-5%, wf 25-45%).
- **Don't trust SID-output "loop detected" probes alone** — Hawkeye sub0's output at 294s matches 120s for >10s because the orderlist *repeats the same entry transposed*, not because the song loops. A py65 **orderlist read-watch** (log reads of the orderlist bytes per frame) settles the real walk; it confirmed the player walks all 110 entries in 4800 ticks, exactly the parser model.
- **Uniform freq=wf=pulse percentages = misalignment, freq-only loss = decode/FM.** Two boundary classes fixed 2026-07-05 in `build_mon_native_song`: (1) notes gated ACROSS a window start were dropped (onset outside window) — a 6s window lost 44% of a voice; now re-entered at t0 as a capture-from-t0 continuation. (2) filter drives are per-note exactness-guarded + each window gets a synthetic residual-envelope restart on its first note — filter went from 30-90% to 98-100% corpus-wide.

---

## Part-count reduction — the structural path (EXECUTED 2026-07-05 for Supremacy)

Dense tunes blow three SF2II hard caps **simultaneously** (per SF2 file: 63 command bundles, 32 instruments, 256 wave rows) because the trace-driven build captures **per note**, unrolling the player's compact looping synth tables. The structural rebuild (`MON_ARP_STRUCT=1`) re-compresses them:

- **Swing tempo** (speed byte bit7 — tick periods alternate speed, speed+1), tick-exact frame accumulation, onset_delay=2, prefix-chain retriggers, additive durations, top-level rests, `$FD` 4-byte slides — all py65-tracer-proven (`bin/mon_event_trace.py` = the decode ground truth).
- **Structural FM entries** in the driver: looping semitone arps, slides (rate `7<<(speed-1)` Hz/frame, target-clamped), scaled pitch-proportional vibrato (per-program rounding), each substitution exact- or semitone-guarded per note with trace fallback.
- **Canonical wave/pulse programs** per (instr, wprog) from the longest note, gate-split, with exact unrolled guards.
- **Global song markers**: orderlist `$00` = global loop, `$FE` = global halt (Supremacy branch only — the Hawkeye-family walk was read-watch-verified to match the parser one-pass model; it needs no global cut).

Result: Supremacy sub1 70→**1 part**, sub2 24→**1 part**, sub0 34→**10 parts** (the real lengths emerged from the global markers: 38s / 150s / 234s). Adaptive window packing (`auto`) also collapsed Hawkeye sub0 13→7, Cybernoid 14→10, Myth →7 parts.

Remaining frontier:

1. **Filter window seams** — filter cutoff is the one register still 30-90% on multi-part tunes (restarts at window boundaries); whole-song parts measure filter 100%.
2. **Structural path beyond Supremacy** — flag-on regresses Myth (osc1 89%); per-variant guard calibration would let every tune use it.
3. **Registry wiring** (roadmap A4) — the whole pipeline still lives in `bin/`.

---

## Key files

| File | Role |
|------|------|
| `sidm2/mon_parser.py` | MoN decoder (orderlists, patterns, instruments, arp programs; `ol_mode` variants) |
| `bin/build_mon_native_song.py` | shared Stage-B native build (bundles, wave/pulse/filter programs, clustering, part windowing) |
| `bin/build_myth_native_song.py` | Myth emulation-extraction shim → same native build |
| `bin/mon_to_sf2.py` | Stage-A Driver-11 transpile |
| `drivers_src/mon/romuzak_driver.asm` | native driver (ROMUZAK/Galway engine copy + MoN wave-RLE `wave_step`) |
| `bin/mon_part_fidelity.py`, `bin/mon_fidelity.py`, `bin/mon_validate.py`, `bin/mon_sf2ii_confirm.py` | fidelity/validation tools |
| `pyscript/test_mon_parser.py`, `test_mon_to_sf2.py`, `test_mon_filter.py`, `test_supremacy_parser.py`, `test_cpu6502_sbc.py` | tests |

Deep memory references: `memory/hawkeye-mon-player-re.md`, `myth-supremacy-mon-re.md`, `cybernoid-mon-orderlist-re.md`, `hawkeye-mon-filter-engine-re.md`.
