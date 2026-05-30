# Galway → Driver 11 — Table Mapping Design (Stage A0)

**Created:** 2026-05-29 | **Stage:** A0 of `GALWAY_SF2_DRIVER_PLAN.md`
**Status:** design (no code yet). Defines how a flattened Galway 1st-gen tune
maps onto SID Factory II **Driver 11** tables, so the converter can emit a
*real, editable, playable* Driver 11 SF2 (sound approximated/lossy — Stage B
replaces the sound with a native Galway driver).

This is the mapping spec the Stage A1 module `sidm2/galway_to_driver11.py`
implements. Every **⚠ LOSSY** marker is an intentional, documented
approximation, not a bug.

---

## 1. Inputs and output target

### Input — what the extractor already produces (`sidm2/galway_1stgen_extractor.py`)
- `recover_channels(...) -> GalwayChannelState` — `.pc[3]`, `.ram` (64K post-init
  image), `.subtune`, `.layout` (has `lofrq_addr`/`hifrq_addr`/`vt0`).
- `flatten_all_channels(state) -> (voices, table_used)` — `voices` is 3 lists of
  `GalwayEvent`:
  - `note`  — `pitch` = index into `LoFrq/HiFrq` *after* transpose; `dur` = raw
    duration byte; `tie` = no-retrigger articulation.
  - `rest`  — `dur` = raw duration byte.
  - `instr` — `value` = ptr to a 5-byte `Vlm` instrument def.
  - `fload` — `value` = ptr to a `Dn` block; `dur` = byte count (≥26 ⇒ instrument).
  - `code` / `end` / `desync` — control/termination/lost-sync (no musical row).
- `extract_instruments(ram, voices) -> [GalwayInstrument]` — `.ctrl` (VWF
  waveform+gate), `.ad`, `.sr`, `.vadsd`, `.vrd`, `.waveforms`, `.ptr`.

### Output — Driver 11 song model → existing emission path
Driver 11 SF2 emission already exists: `SF2Writer(driver_type='driver11')`
(`sidm2/sf2_writer.py`) loads the `Driver 11 Test - Arpeggio.sf2` template and
calls the `inject_*` functions in `sidm2/driver11_section_injectors.py`
(`inject_instruments`, `inject_sequences`, `inject_commands`,
`inject_orderlists`, `inject_wave_table`, `inject_pulse_table`,
`inject_filter_table`, `inject_tempo_table`, `inject_init_table`,
`inject_hr_table`, `inject_arp_table`). Those injectors currently read a
Laxity-shaped `data` object.

**A1 decision:** introduce a clean `Driver11Song` dataclass (orderlists,
sequences, instruments, wave/pulse/filter/arp/tempo/init/hr) and a thin adapter
so the existing injectors (or a small purpose-built emitter mirroring their
documented byte layouts) consume it. Do **not** overload the Laxity `data`
object. Driver 11 formats are specified in `docs/reference/SF2_FORMAT_SPEC.md`.

---

## 2. Pitch mapping (Galway note index → SF2 note byte)

Galway `note.pitch` indexes the player's `LoFrq/HiFrq` chromatic frequency
tables (`N00..N89`, ~90 semitones + silence, engine map §8). Driver 11 sequence
note bytes are chromatic: `$00`=C-0 … `$5D`=B-7 (`SF2_FORMAT_SPEC.md` §Sequence).

So the map is a constant offset: **`sf2_note = pitch_index + BASE`**, clamped to
`$00..$5D`.

- **Calibration task (A1):** determine `BASE` by matching `LoFrq[i]|HiFrq[i]<<8`
  to the standard PAL frequency table (the same table SIDM2 already uses for the
  Vibrants freq-LUT decode). Read the actual 16-bit value at
  `state.layout.lofrq_addr + i` / `hifrq_addr + i` from `state.ram`, find the
  nearest standard PAL note, and derive `BASE` once per file (it should be
  constant for all notes; assert that).
- ⚠ **LOSSY:** notes outside `$00..$5D` (extreme octaves) clamp. Galway's
  per-frame frequency *modulation* (FM/portamento slides) is **not** in the note
  index — it's synth state — so the discrete SF2 note is the slide *target*,
  not the slide itself (see §6).

Replaces the crude `pitch+1` clamp in `galway_to_voice_streams` (which was only
for the embed display view).

---

## 3. Timing / duration mapping (the main rhythmic decision)

Galway `note.dur`/`rest.dur` is a raw byte; for note bytes `<$60` it indexes the
per-tune `IDRT` table (32 entries, seeded from the tune's `durbase`, engine map
§7); otherwise it is used raw → `CLOCKn` (frames the note holds). Driver 11
instead plays **one sequence row per tempo-table tick count**; duration is
expressed as *number of rows* a note occupies (note row + `+++` sustain rows +
`---`/new-note).

Mapping:
1. **Resolve `IDRT`** from `state.ram` (the extractor recovers the post-init
   image, where `CalcDurations` has already filled `IDRT`). For a note byte `b`:
   `frames = ram[IDRT_addr + dur - 1]` when `b < $60` else `frames = dur`
   (mirrors `flatten_channel`'s note path; engine map §5a). Locate `IDRT_addr`
   from the `TUNE`/`CalcDurations` routine (A1 RE task; or expose it from the
   detector).
2. **Pick a row granularity `TICK`** (frames-per-row) for the song, then
   `rows = round(frames / TICK)` (min 1). Emit the note on row 0, `+++` (`$7E`)
   for `rows-1` sustain rows. Rests → `---` (`$80`) for `rows` rows.
3. **Tempo table** = constant `TICK` (`TICK 7F 00`). Choose `TICK` = GCD of the
   observed `frames` values (falling back to a small constant like 4–6) so most
   notes land on integer row counts.

- ⚠ **LOSSY:** non-integer `frames/TICK` rounds → small rhythmic drift.
- ⚠ **LOSSY:** Galway multi-speed (`RF`/`ClkAdd`, multiple play calls/frame) is
  collapsed into the single 50 Hz row clock; absolute tempo is approximate.
  (Stage B's native driver preserves multi-speed.)

---

## 4. Instrument mapping (`GalwayInstrument` → Driver 11 instrument + wave row)

Driver 11 instrument = 6 bytes, column-major (`SF2_FORMAT_SPEC.md` §Instruments):
`[AD, SR, Flags, FilterIdx, PulseIdx, WaveIdx]`.

| Driver 11 field | From Galway | Notes |
|---|---|---|
| AD (col 0) | `GalwayInstrument.ad` | direct |
| SR (col 1) | `GalwayInstrument.sr` | direct |
| Flags (col 2) | `$80` (HR enable) + `$10` (osc reset) baseline | ⚠ Galway has no Driver 11 flag concept; use sane defaults. Set `$40` only if the instrument used a filter (had a `Filter` cmd nearby). |
| FilterIdx (col 3) | filter-program row (see §5) or `$00` | |
| PulseIdx (col 4) | pulse-program row (see §5) or `$00` | |
| WaveIdx (col 5) | wave-program row (see §4a) | required |

### 4a. Wave table
Each distinct instrument gets a minimal wave-table program: one row
`[waveform_byte, $00]` then `[$7F, jump]` to loop. `waveform_byte` =
`GalwayInstrument.ctrl` with the low control bits normalised to gate-on
(e.g. pulse→`$41`, saw→`$21`, tri→`$11`, noise→`$81`; the extractor already
decodes `.waveforms`). Multi-waveform instruments (rare) → pick the dominant bit.

- ⚠ **LOSSY:** Galway's per-frame waveform switching / FM is not captured; the
  instrument plays a static waveform.

### Instrument index assignment
Build the ordered distinct-instrument list from `extract_instruments`; map each
`GalwayInstrument.ptr` → Driver 11 instrument row index (0-based, ≤31). This is
the same ordering `galway_to_voice_streams` uses for its `$A0|idx` markers, so
the sequence instrument column stays consistent. Files with **0** extracted
instruments (Commando/Parallax-class, mechanism still un-RE'd — see engine map)
→ emit one default instrument and flag the file as low-fidelity (or fall back to
embed; see §9).

---

## 5. Pulse / Filter / FM modulation (Stage A: minimal, mostly deferred)

Galway's FM/PM generators (`Dn` offsets 0–22) and the `Filter`/`Master` commands
drive continuous modulation that has no clean Driver 11 table equivalent.

**Stage A policy — approximate-or-omit, keep it editable and stable:**
- **Pulse:** if instrument waveform is pulse (`$41`), emit a static pulse
  program from `PINIT` (`Dn`+22): one `set pulse` row + jump. No sweep. ⚠ LOSSY.
- **Filter:** omit by default (FilterIdx `$00`, Flags filter bits off). Optional:
  if a `Filter` command was present, emit a single static cutoff row. ⚠ LOSSY.
- **FM / vibrato / portamento → commands (§6), best-effort.**

This is the **primary audible gap** vs the original and the explicit reason
Stage B exists. A0 records it; A1 does not try to fully model it.

---

## 6. Command mapping (Galway opcodes → Driver 11 command rows)

Driver 11 commands = 3 bytes `[cmd, p1, p2]`, referenced from the sequence
command column (`SF2_FORMAT_SPEC.md` §Commands).

| Galway | Driver 11 | Stage A treatment |
|---|---|---|
| `Transp`/`CT`/`JT` (transpose) | order-list transposition | Applied at flatten time already (pitch includes transpose). For per-pattern transpose, set the order-list entry transpose nibble. |
| `Vlm` / `FLoad`(instr) | instrument column (`$A0+idx`) | §4 — sets the row's instrument. |
| `Freq` (FM/slide setup) | `T0` slide / `T2` portamento | ⚠ best-effort: if the next note differs, emit `T2` portamento toward it. Often omitted in A1 v1. |
| `Filter` | `Ta XX` (filter program) | optional static (see §5). |
| `Master` | `Te -X` (main volume) | map master-volume nibble → `Te`. |
| `MBendOn`/`MBendOff` | `T1` vibrato on / none | ⚠ approximate vibrato with a fixed `T1` freq/amp, else omit. |
| `Moke`/`Soke`/`DMoke`/`DSoke` | — | ⚠ DROP (arbitrary self-mod; no SF2 equivalent). |
| `Code` | — | file → embed fallback (§9). |
| `Call`/`Ret`/`For`/`Next`/`Jmp` | — | resolved at flatten time (already expanded). |

**Stage A1 v1 minimum:** notes + instruments + tempo + master volume. Slides/
vibrato/filter are an "approximation backlog" inside Stage A, added incrementally
and each measured against the §8 trace baseline.

---

## 7. Sequence / order-list structure

- **3 voices → 3 Driver 11 tracks.** Each voice's event list → one or more
  sequences, segmented at instrument-change (`$A0|idx`) markers — reuse the
  existing segmentation in `placeholder_edit_area._build_populated_orderlists`
  (already proven on Galway streams), but emitting **Driver 11** sequence rows
  (instr/cmd/note triplets with `$80` persistence packing per
  `SF2_FORMAT_SPEC.md` §Sequence Packing) instead of the placeholder view bytes.
- **Order list** per track: one entry per emitted sequence, `[transpose, seqidx]`,
  with the loop marker at the end at the recovered song loop point (the
  flattener already stops at the loop point — record where).
- **Gate model:** note row = note byte; held frames → `+++` (`$7E`) rows;
  note end / rest → `---` (`$80`). `tie` notes (no-retrigger) → `**` tie marker
  (instrument column), per `SF2_FORMAT_SPEC.md`.

---

## 8. Validation (Stage A baseline)

1. **Structural:** converted file opens in SF2II (built editor at
   `~/Downloads/SIDFactoryII_Win32_20231002`); sequences + instruments visible;
   editing a note audibly changes playback (inherent to Driver 11).
2. **Audio divergence (the honest number):** trace the converted SF2 with
   `tools/sidm2-sid-trace.exe` and the original SID; compare per-frame SID
   register writes. **Expect divergence** (lossy) — record it per file as the
   Stage A baseline that Stage B must beat. Reuse `bin/_validate_galway_trace.py`
   structure.
3. **Corpus:** run all flattenable `SID/Galway_Martin/` files; table of
   notes/instruments/divergence; note embed-fallback files.

---

## 9. Fallback policy

A file routes to **embed** (today's v3.6.3 path) instead of Driver-11-transpile
when: channel recovery fails, the flattener desyncs on all voices, a `Code`
event is present, or 0 instruments extracted *and* waveform can't be inferred.
`convert_galway_to_sf2` chooses: `driver11-transpile → embed`, with
`--galway-mode {driver11,embed}` override.

---

## 10. Lossy-points summary (what Stage B fixes)

| Aspect | Stage A (Driver 11) | Stage B (native) |
|---|---|---|
| Waveform/FM per-frame modulation | static waveform | Galway `SOUNDn` verbatim |
| Continuous portamento | discrete note + optional `T2` | real freq slide |
| Pulse/filter sweeps | static or omitted | real programs |
| Multi-speed tempo | collapsed to 50 Hz rows | `RF`/`ClkAdd` preserved |
| Self-mod (`Moke`/`Code`) | dropped / embed | (still embed) |
| Editable + playback | ✅ yes | ✅ yes |

---

## 11. Stage A1 work items

**Status (2026-05-29): items 1-7 DONE, item 8 in progress.** Mapping +
IR in `sidm2/galway_to_driver11.py`; emission in `sidm2/galway_driver11_emitter.py`
(authoritative packed format ported from SF2II `datasource_sequence.cpp`;
column-major tables; template overwrite of `Driver 11 Test - Arpeggio.sf2`;
long-track segmentation; aux rebuild + `$0FFB` repoint). `convert_galway_to_sf2`
defaults to the transpile with embed fallback. Tests: `test_galway_to_driver11.py`
(32) + full suite 1389 pass. Remaining (item 8): SF2II GUI load-test + zig64
divergence baseline. Note: pitch is `index + 1` (note `$00` = off); raw stream
duration is used as frames directly (no IDRT resolution — empirically the bytes
are already musical), tempo = GCD of common durations.

1. `sidm2/galway_to_driver11.py`: `GalwayDriver11Song` dataclass +
   `galway_to_driver11(state) -> GalwayDriver11Song`.
2. Pitch `BASE` calibration (read `LoFrq/HiFrq` vs PAL table) + assertion test.
3. `IDRT` resolution + `TICK`/tempo derivation.
4. Instrument + wave-table builder (§4).
5. Sequence/order-list builder emitting Driver 11 rows (§7) — adapt the existing
   segmenter.
6. Emit via `SF2Writer(driver_type='driver11')` (clean adapter, not the Laxity
   `data` object).
7. Wire `convert_galway_to_sf2` mode + fallback (§9).
8. Validation harness (§8) + unit tests (pitch calibration, duration→rows,
   instrument decode, end-to-end Wizball/Terra).

## Related
`docs/analysis/GALWAY_SF2_DRIVER_PLAN.md` (parent plan),
`docs/analysis/GALWAY_1STGEN_ENGINE.md` (engine), `docs/reference/SF2_FORMAT_SPEC.md`
(Driver 11 formats), `sidm2/galway_1stgen_extractor.py` (inputs),
`sidm2/driver11_section_injectors.py` (emission).
