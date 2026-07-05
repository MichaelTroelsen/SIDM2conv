# The Player-Porting Playbook — consolidated cross-player knowledge

**Mission:** tools that combine static code with AI-driven reverse engineering to convert **any SID into an SF2 that plays at ≥99% fidelity and is 100% editable** in stock SID Factory II.

This document consolidates everything learned porting **seven player families** (Laxity NP21, SF2/Driver 11, NP20, Martin Galway, Future Composer, ROMUZAK, Maniacs of Noise) plus the NP21-adjacent clusters. It is the method to follow — and the traps to avoid — before taking on the next player.

*Updated 2026-07-05 (v3.13.0 era). Per-player detail: the docs in this directory. Accuracy numbers: [../reference/ACCURACY_MATRIX.md](../reference/ACCURACY_MATRIX.md).*

---

## 1. The staged method (proven 4×: Galway → ROMUZAK → MoN → FC-in-progress)

Every player port follows the same ladder. Each stage is independently shippable and validates the one below it.

| Stage | Deliverable | Fidelity | Effort |
|-------|-------------|----------|--------|
| **RE** | Parser (`sidm2/<player>_parser.py`): orderlist/pattern/instrument decode, relocation-safe table signatures | notes/order byte-exact vs siddump | days |
| **A — transpile** | Editable **Driver 11** SF2 via the shared IR (`GalwayDriver11Song` + `galway_driver11_emitter`) | notes/timing/envelope exact; timbre modulation flat | ~1 day once the parser exists |
| **B — native driver** | From-scratch SF2 driver (fork of the shared engine) + trace-driven table build | per-frame **byte-exact** freq/wf/pulse/filter | days-weeks |
| **C — structural** *(frontier)* | Replace trace-unrolled programs with the player's own compact looping synth tables | byte-exact **and** compact (few files) | per-player RE |

Key insight from four ports: **Stage A is cheap once the parser exists** because emission is fully shared (`sidm2/galway_driver11_emitter.py` is consumed by all four players — the one part of the codebase already factored right). **Stage B is expensive but reusable** — the MoN native pipeline handled Cybernoid, Myth, and Supremacy with only per-tune parser variants.

### When can the parser be skipped? (trace-only path)
Galway's bytecode interpreter has no static score, so its native build is **pure trace-driven** (reconstruct notes from the real player's SID output — legato segmentation, gate detection). MoN/ROMUZAK/FC have real orderlists, so parse statically and use the trace only for the *synth* side (slides/PWM/filter). Myth showed a third mode: **emulation extraction** — when the player relocates/self-installs (compilation wrappers), drive it in py65 and intercept the freq-lookup instead of static parsing.

---

## 2. Anatomy of the shared Stage-B pipeline

```
SID file
  │  ground truth (pick per player)
  ├─ siddump (pyscript/siddump_complete.py)      ── per-frame register table
  ├─ zig64  (tools/sidm2-sid-trace.exe)          ── cycle-accurate CSV
  └─ py65 emulation probe                        ── intercept table lookups
  │
  ├─ parser (sidm2/<player>_parser.py) → notes, durations, instruments
  │
  ├─ program builders (bin/build_<player>_native_song.py)
  │     fm_program_for       per-note pitch program (slides/vibrato/arps)
  │     pulse_program_for    per-note PWM program
  │     extract_wave_programs  gate/waveform envelope → wave rows
  │     filter_program_for   cutoff envelope → SET+ADD rows
  │     cluster/dedup        fit the SF2II caps (see §3)
  │
  ├─ gen_includes_song → tables (.inc) + layout  ── currently duplicated per player (§6)
  ├─ 64tass assemble (state-region + edit-area guards) → driver .prg
  ├─ wrap → .sf2 (+ PSID export for WAV A/B)
  │
  └─ validate (§4): onset match → per-frame fidelity → real-SF2II capture → ear
```

### The native driver engine (one engine, currently three copies)
`drivers_src/{galway,romuzak,mon}/*.asm` are the **same ~1,300-line engine**: 3-voice SF2 sequencer (orderlist chaining, packed sequences, durations, transpose), `wave_step`, `pulse_step`, `filt_prog_step`, per-frame FM pitch program, and the `$c0-$ff` per-note command channel selecting (FM, pulse) bundles. Per-player deltas are small and feature-shaped:

- **ROMUZAK** (+40 lines): drum wave-row mode (col1 = freq hi byte), SEEK pulse-hold, per-instrument pulse.
- **MoN** (+~100 vs ROMUZAK): RLE wave rows (col1 = frame **count**, cut Cybernoid 18→11 parts, byte-identical), per-note filter-envelope restart (flag `$40`), gate-envelope wave programs.
- **Galway** (base): 16-bit pulse pointer (573-row PWM), digi engines (NCO sawtooth + PCM hybrid + $D418 gap-sweep), editable chord-arp wave programs.

### Technique catalog (what solved what — reuse before reinventing)

| Problem | Technique | First proven on |
|---------|-----------|-----------------|
| Slides/vibrato/arps per note | (FM, pulse) **bundles** on the `$c0-$ff` command channel; drop delta[0] (driver holds base on trigger frame) | Galway v3.10 → MoN |
| Too many bundles (>63) | **greedy nearest-merge clustering** — count-weighted FM-contour L1, hard distance cap, pulse-audibility-aware | Rambo (Galway v3.12) |
| Legato voices (held gate) | segment by **settled-pitch change**, tie flag = pitch change without re-gate | Wizball (v3.11) |
| Long PWM | 16-bit pulse pointer, row-major table | Wizball (v3.11) |
| Gate/waveform envelope | per-note **wave programs**, RLE'd; steady-state loop `$7F` | MoN B3 |
| Resonant filter | **cutoff envelope** programs (SET + ADD rows), restart per note via flag-`$40` instrument, drives restricted to the `$D417`-routed voice, canonical per **(instrument, shape)** | Hawkeye → Myth filter fix |
| Chord arps, editable | discrete-semitone arps → SF2II **wave-table semitone column** (on-grid test: exact semitones after detrend) | Terra Cresta (v3.12) |
| `play=$0000` self-installed IRQ | trace INIT until a vector installs ($FFFE or CINV $0314), then simulate a 6502 IRQ per frame with a step cap | Arkanoid (v3.12) |
| Relocating compilation wrappers | py65 **emulation extraction** — run the real wrapper init, find the freq-lookup PC by signature, intercept per frame | Myth |
| $D418 volume-digi samples | VICE `-sounddev dump` capture → NCO phase-accumulator lead + PCM drum bank hybrid, gap-sweep records | Arkanoid digi |
| Table location across relocated rips | **code-signature scanning** (never absolute addresses); resolve self-modified pointers by *which* operand the setup writes | Cybernoid |

---

## 3. Hard limits (design against these from day one)

**SF2II per-file caps** (all enforced in the native builders — a dense tune must be windowed into parts when these bind):

| Cap | Value | Enforced at |
|-----|-------|-------------|
| Command bundles (`$c0-$ff`) | **63** | `greedy_cluster(..., 63)`, `NFM=64` |
| Instruments (`$a0-$bf`) | **32** | `instrs[:32]`, `CAP_I=32` |
| WAVE / FILTER table rows | **256** each | cursor guards raise |
| Sequences | **120** (128 slots − margin) | `CAP_SEG=120` |
| Packed sequence events | **960** (SF2II `Unpack` buffer is 1024 with **no bounds check** — overflow = heap corruption) | `_SEQ_EVENT_LIMIT` |
| Memory wall | tables < **$D000** (~27,650 play-calls ≈ 9.2 min); state region `$16CC-$1702` must stay clear | `assemble()` guards |

**Part-count economics** (MoN finding, proven quantitatively): dense tunes blow bundles+instruments+wave-rows **simultaneously**, so relieving one cap alone yields zero part reduction. The trace-driven build unrolls the player's compact looping tables — *no trace-based method compresses this losslessly*. The lossless fix is **Stage C structural RE** of the synth engine (extract its looping arp/wave tables + selectors). Supremacy's engines are already cracked; see `whats-next.md` for the bounded remaining work.

---

## 4. Fidelity measurement ladder (climb it in order)

1. **Onset match** — parser/Stage-A notes+frames vs siddump (`mon_validate.py`, `romuzak_validate.py`, `fc_validate.py`).
2. **Per-frame register fidelity** — freq (semitone), wf, pulse, AD/SR, filter cutoff, headless (`mon_part_fidelity.py`, `romuzak_native_validate.py`). *Compare only over the real song length — `$FE`-halting subtunes score garbage against post-end silence.*
3. **Real SF2II capture** — the instrumented `SIDFactoryII_dbg.exe` diffed against a zig64 trace (`sf2ii_vs_real.py`); this catches what headless metrics miss (it exposed the Galway pulse gap).
4. **Audio A/B** — VICE render + spectral distance (`listen_compare.py`) and the **user's ears** (GUI confirm). Load SF2s via `pyscript/sf2_open_in_editor.py FILE 40` (SF2II's argv-load Heisenbug).

**Trust rules learned the hard way:**
- Byte-exact registers but wrong sound → **suspect the capture CPU** (the siddump SBC carry bug made a 16-bit vibrato too wide project-wide; cross-check py65 + VICE).
- Trace-replay has a **cycle-level floor** (~0.17 VICE spectral distance on high-resonance filtered voices); write-order/schedule reproduction does *not* close it — don't chase it.
- Aligned-waveform diff is the wrong audio metric for tonal voices (phase decorrelates identical-sounding audio); use RMS envelope + band spectra.
- Headless metrics overstate: Galway's "37 faithful" became 30/40 under the objective real-SF2II metric. **The objective per-voice metric is the truth.**

---

## 5. Gotchas (each of these cost real sessions)

**SF2II's bundled 6510 emulator:**
- `CMP` carry computed from bit7 of (A−op) — only correct for |A−op| ≤ $7F. **Never `cmp` values >$7F apart in a native driver**; split on the high bit (`bmi`/`and`) first.
- 1024-event `Unpack` with no bounds check → cap sequences by unpacked-event count; one packed sequence per fixed slot (the editor reads fixed slots, not the pointer table).
- Parser anti-runaway: an embedded player that never RTSes trips the "6510 emulation exceeded cycle window".

**6502 assembly:** `STY abs,x` does not exist (use `TYA`/`STA`); long routines overflow `bpl`/`bne` range (near-branch + `jmp`); ZP allocations collide silently (Galway's `pptr` at `$ea/$eb` vs `vhold` cost a two-voices-silent bug — keep a ZP map per driver).

**Freq tables:** the generic PAL table is 1 semitone off and detuned vs real players — **always emit the player's own freq table** (`write_freqtable` from the binary). MoN's is SPLIT (separate lo/hi tables, not interleaved).

**PSID quirks:** `load=0` means the real load address is the first 2 data bytes; the PSID default subtune is often a jingle (Hawkeye main theme = subtune 3, Combat School music = subtune 1) — pick the real tune explicitly.

**Python/RE discipline:** never bare `except Exception:` around extract+rewrite blocks (a swallowed `NameError` silently disabled F3 wave-copy for 9 releases); confirm a table's record stride before claiming its format (DRAX $1B8A was mislabeled twice); never generalize a layout from one file — confirm each independently via backward dataflow from the fixed `STA $D40x,Y` writes.

**Build hygiene:** `drivers_src/*/{layout,freqtable}.inc` are regenerated every build — `git checkout` before committing; `bin/SIDFactoryII_dbg.exe` is a modified binary, never commit it; SF2II must launch with cwd=`bin` (SDL2.dll + config).

---

## 6. New-player checklist

1. **Scope the corpus** — how many SIDs share this player? (MoN unlocks 179 Tel tunes; a V20 singleton is poor ROI.)
2. **Identify entry points** — init/play JMPs, subtune dispatch, load-address quirks (`load=0`, relocation, self-IRQ).
3. **Map the sequencer** — tempo gate, per-voice loop, orderlist model, pattern byte dispatch, duration model (sticky? additive? ticks vs frames). Disassemble (`bin/_mon_disasm.py`-style + py65 write-PC probes — raw disasm misaligns on illegal opcodes).
4. **Locate tables by signature** — freq (verify 12-semitone rollover), instruments (verify AD/SR sanity), pattern/orderlist pointers. Relocation-safe, per-file confirmed.
5. **Write the parser + validate onsets** vs siddump (aim byte-exact before anything else).
6. **Stage A**: transpile through `galway_driver11_emitter`; GUI-confirm notes/order/timing.
7. **Stage B**: fork/parameterize the shared native engine; trace-driven program builders; climb the measurement ladder (§4); mind the caps (§3).
8. **Tests at every step** (`pyscript/test_<player>_*.py`) — parser decode, tempo model, onset timing, program round-trips through a driver-step model.
9. **Document**: `docs/players/<PLAYER>.md` + memory file + update the [README index](README.md) and [ACCURACY_MATRIX](../reference/ACCURACY_MATRIX.md).

**Standing user preference:** accuracy/byte-exactness over speed, cost, and file count. Never ship lossy output silently.

---

## 7. Where knowledge lives

| Layer | Location |
|-------|----------|
| Per-player docs | `docs/players/*.md` (this directory) |
| Accuracy source of truth | `docs/reference/ACCURACY_MATRIX.md` |
| Driver-11 table formats | `docs/analysis/DRIVER11_TABLE_FORMATS.txt`, `docs/analysis/SF2_DRIVER_BINARY_FORMAT.md` |
| Native-driver plans | `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md`, `ROMUZAK_SF2_DRIVER_PLAN.md` |
| Active frontier handoff | `whats-next.md` (repo root) |
| Deep RE session memories | `memory/*.md` (agent memory; per-player `*-re.md` files) |
| Consolidation/optimization roadmap | `docs/ROADMAP.md` |
