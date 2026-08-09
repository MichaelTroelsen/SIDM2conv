# The Player-Porting Playbook — consolidated cross-player knowledge

**Mission:** tools that combine static code with AI-driven reverse engineering to convert **any SID into an SF2 that plays at ≥99% fidelity and is 100% editable** in stock SID Factory II.

This document consolidates everything learned porting **seven player families** (Laxity NP21, SF2/Driver 11, NP20, Martin Galway, Future Composer, ROMUZAK, Maniacs of Noise) plus the NP21-adjacent clusters. It is the method to follow — and the traps to avoid — before taking on the next player.

*Updated 2026-07-05 (v3.13.0 era). Per-player detail: the docs in this directory. Accuracy numbers: [../reference/ACCURACY_MATRIX.md](../reference/ACCURACY_MATRIX.md). **Named recurring mechanisms, diagnostics, and failure classes: [PATTERNS.md](PATTERNS.md)** - check it for a matching symptom before writing new code.*

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
  ├─ vsid wrapper (sid-reference-project, VICE)  ── RSID/play=$0000 fallback
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
| `play=$0000` self-installed IRQ | trace INIT until a vector installs ($FFFE or CINV $0314), then simulate a 6502 IRQ per frame with a step cap. **When that fails, use the VICE wrapper** (below) — zig64 has no autonomous VIC/CIA delivery, so a player whose INIT waits on its own IRQ as a handshake can never complete here | Arkanoid (v3.12); RSID gap (v3.21.0) |
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
| Memory wall | tables < **$D000**; state region `$16CC-$1702` must stay clear | `assemble()` guards |
| ~~"~27,650 play-calls ≈ 9.2 min"~~ | **RETRACTED 2026-07-30 (R20)** — not derivable from the format and not in the history. Nothing in a Driver 11 file grows with *time* (fixed-size tables + a fixed 128×256-byte sequence region), so per-module capacity is a function of event **density**. MEASURE it (`bin/mattgray_to_sf2.convert`'s `_part_fits` probe): Driller's whole 665.6 s song is ONE module at 57/128 slots, top `$61CF` | — |

**A capacity check must compare a REQUIRED count against the cap — MEASURED 2026-07-30 (R20a).**
The Matt Gray probe's sequence check counted non-zero pointer entries across all 128 slots and
compared that to 128: a value bounded by the cap, tested against the cap, so it **could never
fail**. Reading the count back out of an emitted file cannot work *in principle* here, because
`galway_driver11_emitter` **truncates** at the cap — so the file never reports more than the cap
however much was dropped, and (until this fix) it dropped **silently**, its `break` leaving the
voice loop so later voices were emitted as a single empty sequence and went **totally silent**.
Rule: count what the window **needs**, before emitting; make the truncation path announce itself;
and read a shared cap through its module, never a `from … import` copy that is bound once and
goes stale.

**Stage A part-splitting is shared: `sidm2/d11_windowing.py`.** A Stage A builder that can exceed
128 sequences must window the song rather than hand the emitter an oversized list. Two planners,
picked by how the builder packs — and the choice is about **alignment across voices**, which is
what keeps a split song in sync:

| builder shape | planner | why it is aligned |
|---|---|---|
| per-voice **row grid**, packed with `segment_track` (SDI) | `plan_row_windows` | all three voices share the grid, so one row index cuts them together |
| one sequence per **bar**, same bar chain walked per voice (Sound Monitor) | `plan_entry_windows` | orderlist entry *k* is bar *k* in every voice |

Do **not** cut a row-grid builder on orderlist indices: `segment_track` cuts where packing limits
fall, so entry *k* is a different musical position in each voice and the voices desync. Both
planners grow by doubling then binary-search the edge, count post-**dedup** (dedup is what makes
most songs fit at all — counting before it over-splits), and emit a single full-span window when
the song fits, so files that never needed splitting stay **byte-identical**. Convention: a split
song becomes `NAME_partNN.sf2` and the superseded single file is deleted, so nobody opens the
truncated one.

⚠️ **`dedup` must match how you will call the emitter.** Passing explicit
`sequences=`/`orderlists=` uses them as given (plan with `dedup=True`); passing a bare `song`
lets the emitter's own segmenting branch pack `song.tracks`, and **that branch does not
deduplicate**. Planning post-dedup for the bare-`song` path underestimates, so the planner says
"fits" and the emitter truncates anyway — which is precisely how Galway's `Short_Circuit` kept
losing 29 sequences after the first fix attempt.

**Full audit of every builder sharing the emitter (2026-07-30).** Sweep with
`pyscript/sf2_truncation_sweep.py <player>`; it rebuilds and reads the emitter's warning, which
is the only oracle that knows what was *requested*.

| path | built | lost music | now |
|---|---|---|---|
| SDI Stage A | 343 | 13 | ✅ split (`plan_row_windows`) |
| Sound Monitor Stage A | 11 | 2 | ✅ split (`plan_entry_windows`) |
| **default pipeline** (Galway path) | 40 | 1 | ✅ split; `output_path` stays part 1 so the caller's contract holds |
| Hubbard Stage A | 89 | 1 | ⚠️ **open** — no common time base, see `HUBBARD.md` |
| MoN / ROMUZAK / FC / Deenen / Kimmel / Matt Gray | 179/20/5/7/4/6 | 0 | — |
| Blackbird Stage A | 16 | 0 | not a shipped CLI (test-only) |

Regression gate across all fixes: **378 byte-identical, 0 unexpected diffs, 16 newly split.**
Laxity → the Laxity driver never touches this table (different packer), so the 286-file Laxity
corpus is out of scope — check *which emitter a path actually reaches* before sweeping it.

**Never run `pytest` while an SF2II play-test is in flight.** `pyscript/conftest.py` used to kill
every `SIDFactoryII` process on the machine at session end (two paths, one of them silent);
`psutil.kill()` is a TerminateProcess and its exit code is what the crash oracle reads as
CRASHED. It manufactured a *100% crash rate on both arms* of a Driller A/B — the tell was a
uniform **exit code 15** across unrelated builds. Both paths are now scoped to editors the test
session itself started, but keep the ordering rule.

**A play-test must prove the module actually PLAYED, not just that the editor lived.** Gate the
trial on SF2II's own "Playing time" readout advancing (`blackbird_crash_probe.probe_once`, verdict
`NOPLAY` when it never does) — process aliveness alone reports SURVIVED for an editor sitting
idle at `0:00` because the `F1` was lost to another window taking foreground. And capture
evidence with `PrintWindow`, not a screen-region grab: a region grab captures whatever is on top
of the editor, which silently made every "proof of play" screenshot a picture of VICE.

**Which cap actually binds - MEASURED 2026-07-30 (R18).** Instrumenting the windowing probe on
FC's `Is_There_a_Difference` (5 parts) showed **command bundles bind every single cut**
(64/66/67/64 against the 63 cap) while **WAVE rows sat at 40-61 of 256** (16-24%). So
compressing wave rows (RLE) buys **zero** part reduction on a bundle-bound tune, and MoN's
Cybernoid 18-to-11 RLE win was real only because *that* tune is wave-row-bound. **Measure which
cap binds before relieving one.** Corollary: part count lives in the bundle count, which is why
the lossless path is Stage C structural RE (collapse bundles at source). A lossy dial also
exists and is quantified - the probe requires the PRE-cluster raw bundle count to fit, so
raising `CAP_B` permits clustering and cuts parts hard (Blackbird measured 16 parts at CAP_B=64
vs 5 at 128, for ~5.8pp freq); keep it opt-in per player, never a default.

**Part-count economics** (MoN finding, proven quantitatively): dense tunes blow bundles+instruments+wave-rows **simultaneously**, so relieving one cap alone yields zero part reduction. The trace-driven build unrolls the player's compact looping tables — *no trace-based method compresses this losslessly*. The lossless fix is **Stage C structural RE** of the synth engine (extract its looping arp/wave tables + selectors). Supremacy's engines are already cracked; see `whats-next.md` for the bounded remaining work.

---

## 4. Fidelity measurement ladder (climb it in order)

1. **Onset match** — parser/Stage-A notes+frames vs siddump (`mon_validate.py`, `romuzak_validate.py`, `fc_validate.py`).
2. **Per-frame register fidelity** — freq (semitone), wf, pulse, AD/SR, filter cutoff, headless (`mon_part_fidelity.py`, `romuzak_native_validate.py`). *Compare only over the real song length — `$FE`-halting subtunes score garbage against post-end silence.*
3. **Real SF2II capture** — the instrumented `SIDFactoryII_dbg.exe` diffed against a zig64 trace (`sf2ii_vs_real.py`); this catches what headless metrics miss (it exposed the Galway pulse gap).
4. **Audio A/B** — VICE render + spectral distance (`listen_compare.py`) and the **user's ears** (GUI confirm). Load SF2s via `pyscript/sf2_open_in_editor.py FILE 40` (SF2II's argv-load Heisenbug).

**Picking a tracer — and the RSID gap:**
`tools/sidm2-sid-trace.exe` (zig64) drives a tune by calling its **PSID-declared play
address** once per frame. RSID files that install their own IRQ declare `play=$0000`:
there is nothing to call, and zig64 has **no autonomous VIC/CIA interrupt delivery**, so a
player whose INIT waits on its own IRQ as a handshake can never finish. Since **v3.21.0**
the tracer *says so* (`FAILED:` + non-zero exit) instead of emitting an empty trace that
was indistinguishable from a silent tune — see the trust rules below.

**The escape hatch:** `scripts/dev/vsid-trace.js` in the *separate*
`sid-reference-project` wraps VICE's `vsid`, which runs a full emulated C64 and lets the
machine drive the player. **21 of SIDM2's 22 untraceable RSIDs trace under it**
(`Broken_Ass` 1068 writes, `Myth` 259, `A_Mind_Is_Born` 100; only `Final_Countdown_BASIC`
returns 0, plausibly genuine). Cross-validated on a PSID both tools drive: **exactly 90**
changed-value writes each over 16 frames of Stinsen.
```
node scripts/dev/vsid-trace.js <file.sid> --frames 200 --json --changed-only
```
Gotchas: `--changed-only` is required to match zig64's semantics (vsid records redundant
writes too); **vsid exits 1 on normal termination** — check for the dump file, not the
exit code; **cycle timings are NOT comparable** between the tools (~1 frame apart), only
the write *sequence* agrees. Not wired into SIDM2.

**Trust rules learned the hard way:**
- **An equality check over evidence must first assert the evidence exists.** The zig64
  audio gate compared two traces for equality, so when the tracer couldn't drive a file
  both sides came back empty, `len(0)==len(0)`, and it returned True — certifying 64 zero
  bytes as byte-identical to `Broken_Ass.sid` (v3.21.0 fix: fail closed). `compare(a, b)`
  where both are empty is not a match; it's "no test ran". Audit any gate of that shape.
- **A too-short window looks exactly like a broken trace** — Arkanoid gives 0 writes at 5
  frames and 460 at 200. Re-check at ≥200 frames before calling a file broken.
- **Subtract the target driver's own startup frame before scoring it.** Driver 11's first
  play call after init is spent initialising its state block and writes no SID register, so
  **every Stage A transpile in this repo renders one frame late** against a native-player
  original. It shows up as a *constant* `+1` offset (no drift) and is worth ~0.7 pp corpus-wide,
  but it wrecks individual arpeggiated instruments whose target pitch arrives at the end of a
  ramp. Fix it in the validator (`--lag 1`), never by patching the driver or widening the
  window. Mechanism + affected builder list: [DRIVER11.md](DRIVER11.md); PATTERNS.md **F6**.
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

**Wrapping an SF2 as a PSID probe — the play address differs by driver:** a **Driver 11** SF2 is driven at **`$1006`** (the per-frame tick; `$1003` is *stop* and gives total silence), while the repo's **native** drivers declare `init $1000` / **`play $1003`** / `stop $1006`. Both conventions are live in `bin/` — copy the one that matches the driver you built, not the nearest validator.

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
| Deep RE session memories | `memory/*.md` — **not a repo path**: the Claude Code auto-memory store outside this git repo (per-player `*-re.md` files); ask your assistant to recall a named file |
| Consolidation/optimization roadmap | `docs/ROADMAP.md` |
