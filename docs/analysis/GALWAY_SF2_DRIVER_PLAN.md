# Galway → SF2 Driver — Executable Plan (staged)

**Created:** 2026-05-29 | **Scope chosen by user:** *Both, staged* —
ship a Driver-11 transpile first (editable + playable immediately, lossy
sound), then build a native Galway SF2 driver for faithful timbre.

**Goal:** convert Galway SID → an SF2 that opens in SID Factory II with a
populated, **editable** song where **edits affect playback** — first via the
existing Driver 11, then via a purpose-built Galway driver that reproduces
Galway's actual sound.

This supersedes the v3.6.3 *embed-the-player* approach (audio-faithful but
editor is display-only; edits don't change playback). Embed stays as the
ultimate fallback for files that can't be expressed in tables.

---

## Why this is the shape of the problem

SF2II is a **data-driven editor**: editing power comes from a driver's
embedded **descriptor** (serialized into file header blocks 1–9; block 3 =
table definitions, 4 = instrument descriptor, 6/7/8 = color/insert-delete/
action rules) plus the driver's **6502 replay binary**. A driver "like the
others" = author both, then have the converter emit tables that driver reads.

Galway's engine is a per-voice **bytecode interpreter** (loops, calls, inline
native `Code`, self-modifying pokes — see `GALWAY_1STGEN_ENGINE.md`) and so
**cannot be losslessly flattened**. Resolution used throughout this plan:
- **Sequencer control-flow** (Call/For/Jmp/CT/JT) is resolved at *conversion*
  time by the existing flattener (`galway_1stgen_extractor.flatten_all_channels`).
- **Synth** (FM/PM modulation + ADSR + filter) is already table-shaped (the
  29-byte `Dn` block); Stage A approximates it onto Driver 11, Stage B keeps
  Galway's real synth code.
- **Inexpressible** files (inline `Code`, arbitrary self-mod) → embed fallback.

---

## Assets on disk (verified 2026-05-29)

| Asset | Path | Use |
|---|---|---|
| SF2II C++ source | `~/Downloads/sidfactory2-master/.../editor/driver/*.cpp` | RE driver descriptor binary format (Stage B) |
| Galway 1st-gen ASM | `~/Downloads/galway_src/wizball.asm` (+arkanoid/gameover/greenberet/rambload) | Lift synth core (Stage B) |
| Built SF2II editor | `~/Downloads/SIDFactoryII_Win32_20231002` | GUI load-tests |
| Descriptor emitter | `sidm2/sf2_header_generator.py` | Already emits Block 3 table descriptors |
| Flattener + instr extractor | `sidm2/galway_1stgen_extractor.py` | Conversion front-end (DONE) |
| Cycle-accurate tracer | `tools/sidm2-sid-trace.exe <prg> [frames] [init] [play] [subtune]` | Frame-exact validation |
| Driver 11 SF2 emission | `sidm2/sf2_writer.py`, `driver11_section_injectors.py`, `driver11_table_helpers.py` | Stage A target |

---

# STAGE A — Transpile to Driver 11 (working milestone)

Reuses the fully-working Driver 11 editor+playback path. The work is the
**mapping** Galway → Driver 11 tables. Sound is approximated (lossy); editing
and playback are real.

### A0 — Mapping design (`docs/analysis/GALWAY_TO_DRIVER11_MAPPING.md`)
Define and document, with the lossy points called out explicitly:
- **Notes/durations:** flattened `GalwayEvent` notes → Driver 11 note rows;
  Galway duration (`IDRT`-resolved) → row count / tempo table. Pitch already
  handled (`galway_to_voice_streams`).
- **Instrument (`Dn` 29B → Driver 11 6B + programs):** `VADV`→AD, `VSRV`→SR,
  `VWF`→wave-table waveform byte, `PINIT`→pulse program seed, flags. FM
  generator words → approximate via wave/pulse/arp programs; PM → pulse
  program; filter program → Driver 11 filter table.
- **Commands:** `Transp`→orderlist transpose; `Vlm`/`FLoad`→instrument column;
  `Freq` (FM/slide)→`T0` slide / `T2` portamento / `T1` vibrato; `Filter`→`Ta`
  filter index; `Master`→`Te` volume; `Soke`/`Moke` pokes → best-effort or drop.
- **Continuous portamento:** Galway slides continuously; approximate with
  `T2` portamento between adjacent notes. (Primary audible-loss source.)

### A1 — Implement `sidm2/galway_to_driver11.py`
`galway_to_driver11(state) -> Driver11Song` producing orderlists, sequences,
instrument table, wave/pulse/filter/arp tables, command table. Pure data; no
6502. Unit-tested against Wizball/Terra_Cresta flattened output.

### A2 — Wire the conversion path
`convert_galway_to_sf2` (in `conversion_pipeline.py`) gains a mode that emits a
**real Driver 11 SF2** via the existing writer instead of embed. Default order:
Driver-11-transpile → embed fallback (if flatten fails / `Code` present).
Keep `--galway-mode {driver11,embed}` override.

### A3 — Validate Stage A
- SF2II GUI: file opens, sequences + instruments populated, **edit a note →
  playback changes** (inherent to Driver 11).
- zig64 trace converted-SF2 vs original SID: **measure** divergence (expected,
  lossy) — this is the Stage A baseline the native driver must beat.
- Corpus: run all `SID/Galway_Martin/` flattenable files; record pass/notes.

### A4 — Integrate
`DriverSelector` note (Galway→driver11-transpile), docs, tests, `test-all.bat`.
**Milestone release.** Editable + playable Galway SF2, lossy sound, today.

---

# STAGE B — Native Galway SF2 driver (fidelity)

Author `sf2driver_galway_00.prg` + descriptor: Galway's *real* synth driven by
an editable Galway-shaped table model. Faithful timbre + full editor + edits
affect playback.

### B0 — Pin the driver-descriptor binary format
Read `driver_architecture_sidfactory2.cpp` + `driver_info.cpp`; disassemble
`sf2driver11_00.prg` / `sf2driver13_00.prg` to see a real in-binary descriptor.
Deliver `docs/analysis/SF2_DRIVER_BINARY_FORMAT.md` + a `GalwayDriverDescriptor`
emitter. *Validate:* hand-built stub driver loads in GUI, no crash.

### B1 — Toolchain + skeleton driver
Stand up ACME/64tass build (Galway src uses Ocean directives — port or
re-assemble). Minimal driver: descriptor parses, init/play present, plays
silence. *Validate:* F10 loads; `SYS` runs; zig64 clean.

### B2 — Port the Galway synth core
Lift `SOUNDn` (FM/PM + ADSR state machine), `FILTER`, `NOTE`/`LoFrq`/`HiFrq`,
`INITSOUND` from `wizball.asm`, driven by the Galway-shaped table model from B0
(instrument row + FM/PM/filter program sub-tables, mirroring how Driver 11
splits wave/pulse/filter). Hardcode Wizball tables. *Validate:* zig64 frame-0+
registers match original Wizball (osc1 `$1F1F`/AD`$06`/SR`$FA`/ctrl`$41`…).

### B3 — SF2 sequencer
Per-voice reader over SF2 orderlist+sequence (note/instr/command rows) driving
the synth; replicate Galway multi-speed (`RF`/`ClkAdd`) timing. *Validate:*
hand-authored SF2 plays; **editing a note in SF2II changes playback**.

### B4 — Converter wiring
New default in `convert_galway_to_sf2`: flatten → map `Dn`→Galway tables +
events→sequences → emit SF2 with the Galway driver + descriptor. Order becomes
galway-native → driver11-transpile → embed. *Validate:* Wizball/Terra round-trip.

### B5 — Validation harness + corpus accuracy
Frame-by-frame zig64 compare across `SID/Galway_Martin/`; GUI load-test each;
produce a **real** Galway accuracy matrix replacing the fictional "88–96%."

### B6 — Integrate
`DriverSelector` (Galway→galway-native), `DRIVER_REFERENCE.md` +
`SF2_FORMAT_SPEC.md` Galway sections, CLAUDE/CHANGELOG/STORY, tests.

---

## Risks

- **Descriptor RE (B0):** no driver source published; mitigated by C++ parser +
  real-driver disassembly + existing `sf2_header_generator.py`.
- **Continuous portamento/FM:** highest fidelity risk; Stage A approximates,
  Stage B keeps Galway's `SOUNDn` so it should carry over (verify per-note FM
  state seeding).
- **Multi-speed timing:** driver must reproduce `RF` gating.
- **2nd-gen player** (Athena/Times of Lore/Insects): different engine, no
  source → **out of scope**, stays on embed.
- **`Code`/self-mod files:** embed fallback (no fidelity loss, not editable).

## Done-when

- Stage A: a flattenable Galway SID converts to a Driver 11 SF2 that opens,
  edits, and plays in SF2II; divergence-vs-original measured.
- Stage B: same files convert to a Galway-driver SF2 whose zig64 trace matches
  the original SID materially better than Stage A; accuracy matrix published.

## Related
`docs/analysis/GALWAY_1STGEN_ENGINE.md`, `memory/galway-1stgen-engine-map.md`,
`memory/next-galway-hubbard-work.md`, `sidm2/galway_1stgen_extractor.py`.
