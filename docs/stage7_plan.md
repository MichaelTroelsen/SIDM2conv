# Stage 7 — Edit-affects-playback for tables (instruments / wave / pulse / filter)

**Status:** Phase A shipped 2026-05-09. **Phase B.0/B.1/C for WAVE shipped
2026-05-09 — F3 (wave) edits now propagate to playback end-to-end** via
the wave split-copy 6502 routine and a fixed `extract_all_laxity_tables`
wave detector. Phase B.2 (instruments / pulse 6502 emission) deferred.

## Background

v3.3.0 closed criterion 3 for **sequence** edits (F1 in SF2II) via the
runtime translator at `$0F0E`. The PLAY handler at `$0F04` is patched
to `JMP $0F0E`; the translator regenerates the shadow buffer from
SF2-format edit-area bytes through `sidm2.sf2_to_np21` on every PLAY
tick. v3.4.0 extended this with the multi-pattern translator at
`$0F8E`.

What **doesn't** propagate today: edits to instruments (F2), wave
(F3), pulse (F4), filter (F5). The NP21 binary at `$1000` keeps reading
its own table data at hardcoded offsets (`$1A6B` instruments,
`$1942` wave, `$1A3B` pulse, `$1989` filter for Stinsen). Edits in the
SF2 editor go to the SF2 edit area — a separate region that the
player ignores.

Stage 7 closes this gap.

## Architecture

Same model as the sequence translator: every PLAY tick, copy the
SF2-edit-area table bytes back into the NP21 binary's table addresses.
Each table has a different layout, so each needs its own conversion.

```
┌─────────────────┐                   ┌──────────────────┐
│ SF2 edit area   │   PLAY-tick       │ NP21 binary tables│
│ (user edits)    │ ─────────────►    │ at fixed addrs    │
│                 │   convert+copy    │ ($1A6B, $1942...) │
└─────────────────┘                   └──────────────────┘
                                              │
                                              ▼
                                       (player reads)
                                              │
                                              ▼
                                          SID audio
```

## Three phases

### Phase A — Python reference + tests (✅ shipped)

`sidm2/sf2_to_np21_tables.py` — pure-Python conversion functions:

- `convert_wave_table(sf2_bytes, n_rows=32)` — Wave is byte-for-byte
  identical between SF2 and NP21 (rows of `(note_offset, waveform)`
  pairs). Direct copy.
- `convert_instruments_table(sf2_bytes, np21_existing, n_rows=32)` —
  NP21 has 8-byte rows; SF2 has 6-col rows. Maps:
  ```
  NP21 byte 0 (AD)        ← SF2 col 0 (AD)
  NP21 byte 1 (SR)        ← SF2 col 1 (SR)
  NP21 byte 2 (HR)        ← SF2 col 2 (HR)
  NP21 byte 3 (flags2)    ← preserved from existing NP21
  NP21 byte 4 (flags3)    ← preserved
  NP21 byte 5 (pulse_pm)  ← preserved
  NP21 byte 6 (pulse_ptr) ← SF2 col 4 (Pulse)
  NP21 byte 7 (wave_ptr)  ← SF2 col 5 (Wave)
  ```
  SF2 col 3 (Filter) is synthesised at write time and not
  back-propagated — NP21 has global filter selection, not per-instrument.
- `convert_pulse_table(sf2_bytes, np21_existing, n_rows=16)` — NP21 has
  4-byte rows; SF2 has 3 cols. SF2 cols 0..2 → NP21 bytes 0..2; NP21
  byte 3 (next-program ptr) preserved.
- Filter conversion is **deferred** — NP21 stores three parallel arrays
  (resonance/sweep/mode) at variant-dependent offsets. Needs the same
  per-variant detection work as the Class B `ch_seq_ptr` autodetector.

Tests: 19 cases in `pyscript/test_sf2_to_np21_tables.py`. Round-trip
identity (NP21 → SF2 → NP21 = no-op when no edit) is the key correctness
property. Edge cases for short inputs, multi-row tables, and the
"Filter column not propagated" rule are covered.

### Phase B.1 — 6502 plumbing (✅ shipped 2026-05-09)

What's in:

- `_emit_wave_copy_routine(sf2_addr, np21_addr, n_bytes)` —
  emits a 12-byte 6502 byte-copy routine. Tested mechanically (py65
  step-through confirms it executes during PLAY and overwrites the
  destination bytes).
- `_emit_multipat_translator` accepts a new optional
  `table_copy_addr` parameter; when set, the translator emits
  `JSR table_copy_addr` before its existing `JSR play_addr`. With
  default `None`, behaviour is unchanged from v3.4.0.

What's NOT in (and why): the wave_copy_addr is currently hardcoded
to `None` in `_inject_laxity_raw_np21`, so no routine is actually
emitted. See Phase B.0 below.

### Phase B.0 — Per-variant wave-table address RE (✅ SHIPPED 2026-05-09)

**Empirical findings 2026-05-09:**

1. `extract_all_laxity_tables` returns wave_addr=`$17EC` for Stinsen.
   py65 step-through shows `$17EC..$17EE` is per-voice mutating
   player state — the player WRITES waveform values to those
   addresses each tick, then reads them when issuing the
   `STA $D404` instruction. So $17EC IS read by the player but
   only as a transient stash; wave-copying to it is clobbered.

2. Canonical CLAUDE.md address `$1942` has note-offset data
   (`00 0f 7f 88 7f 88 0f 0f 00 7f`) — small numbers + `$7F` end
   markers. Note-offsets, not waveforms.

3. **Stinsen's actual wave-program is at `$18DA`** (waveform bytes
   `21 21 41 7f 81 41 41 41 7f 81 41 80 80 7f 81 ...`). Confirmed by
   direct-edit experiment:
   - File generated, byte at `$18DA` patched from `$21` (saw) to
     `$11` (triangle), zig64 trace re-run.
   - Result: `osc<v>_control` register writes flipped from `$20`
     (saw bit) to `$10` (tri bit) on ALL THREE VOICES.
   - Edit propagated end-to-end. So `$18DA` is the actual wave
     read source for Stinsen.

The trace path (via `pyscript/probe_wave_read_addr.py`):
```
osc<v>_control writes ← read from $15B1, $17EC, $17EE
   ↓ (chase)
$17EC, $17EE writes   ← read from $18DA-$18DC (wave program),
                              $190A (extension), $11D4
   ↓
$18DA-$190A           ← STATIC bytes in NP21 binary; THIS IS the
                          wave-program source
```

So the wave path is: STATIC wave program at $18DA (and probably
$190A) → player walks it byte-by-byte → stores current value at
$15B1/$17EC-EE → reads that and writes to SID osc-control. Edits
to $18DA propagate; edits to $17EC are clobbered by the player's
own write-back.

**What this means for Phase B:**

The SF2 edit area's wave bytes ARE WRONG. They were extracted
from `$17EC` (mutating player state captured at one specific
moment), not from `$18DA` (the actual wave program). So even if
the wave-copy routine writes back to $18DA, it'd be writing
garbage.

To make Phase B work end-to-end, we need:

1. **Fix `extract_all_laxity_tables` wave detection** to find
   `$18DA` (or equivalent for other NP21 variants). The detector
   in `sidm2/instrument_extraction.py::find_and_extract_wave_table`
   uses heuristics that misidentify mutating player state as a
   wave table.

2. **Re-emit the SF2 edit area Stage 4 wave** with bytes from
   `$18DA` (the actual wave program). This propagates wherever the
   user sees in the editor view.

3. **Then** the wave-copy 6502 routine in Phase B.1 plumbing can
   actually do its job: copy bytes from the SF2 edit area back to
   `$18DA` on every PLAY tick.

4. Then Phase C verifies edits propagate.

Per-variant: $18DA is Stinsen-specific. Other NP21 variants will
have the wave program at different addresses. The same dynamic-
trace approach (probe_wave_read_addr.py) finds it in seconds for
any file given init_addr/play_addr — so this is automatable
post-detection.

**Status (2026-05-09 evening): Wave detector is FIXED.**
`extract_all_laxity_tables` now prefers `find_and_extract_wave_table`
(which uses `find_wave_table_from_player_code`) over the
LDA-near-STA$D404 heuristic in `find_table_addresses_from_player`.
The new chain validates the static wave program at $18DA (Stinsen)
and returns `wave_data_addr` alongside `wave_addr` so callers know
the parallel arrays' two endpoints.

### Phase B.2 — 6502 emission for instruments / pulse (✅ PLUMBING SHIPPED 2026-05-09)

**Status:** Routines implemented + tested. **Wire-up disabled** —
per-variant NP21 instrument/pulse address RE has more variance than
wave did:
- **Stinsen**: AD/SR scratch fed from $18D8/$18D9 — adjacent to
  wave-data start at $18DA (so writing back into a "row-major
  8 bytes/instrument" layout would clobber wave data). Layout
  appears to be ≤2 bytes/instrument or column-major-with-overlap;
  needs targeted RE.
- **Angular**: per-voice scratches at $197B-$1986 (12 bytes total:
  3 voices × 4 fields PWlo/PWhi/AD/SR). The SID register writes
  source DIRECTLY from those scratches; chase to the static
  instrument table not yet done.
- **Beast**: per-voice scratches at $1911-$191C — same parallel-
  array layout as Angular but at different addresses.

The `_emit_instr_copy_routine` and `_emit_pulse_copy_routine`
functions are wired into `SF2Writer` but **NOT** called from
`_inject_laxity_raw_np21` — there are no validated per-variant
addresses to pass them. Once per-variant RE provides clean
{instr_addr, n_instruments} and {pulse_addr, n_rows} pairs, the
wire-up is ~10 lines per table.

**6502 size (measured)**:
- Wave (already shipped): 31 bytes (split-copy, n_rows=32)
- Instruments: 110 bytes (5-field × 5-pass, n_instruments=16)
- Pulse: 66 bytes (3-field × 3-pass, n_rows=16)
- Total Stage 7: ~207 bytes in SF2 edit area

These all live in the SF2 edit area trailing buffer, called via
JSR from the multipat translator.

**Tests**: `pyscript/test_sf2_writer_phase_b2.py` — 11 cases:
opcode emission, py65 step-through, multi-row copy, round-trip
identity, edge cases (n=32 with stride wrap).

### Phase C — End-to-end zig64 verification (✅ SHIPPED 2026-05-09 for Wave)

**Verified 2026-05-09 for Stinsen wave:**

1. Generate Stinsen.sf2; capture baseline zig64 trace (300 frames):
   1909 SID register writes.
2. Patch byte at file-offset $2CA5 (SF2 edit-area row 0 waveform byte)
   from $21 (saw bit) to $11 (tri bit).
3. Re-run zig64 trace.
4. **Result: 155 `osc<v>_control` writes flipped from $20 (saw) to
   $10 (tri) on all three voices.** Edit propagated end-to-end.

Trampoline fix that made the trace-path verification possible:
when `play_addr != init_addr+3` AND `num_patterns > 0`, the
`init+3` trampoline now `JMP`s to `TRANSLATE_BASE` (multipat
translator at $0F9E) instead of `play_addr` directly. Without
this, zig64-traced playback would bypass the translator and
the wave-copy routine; only SF2II's PLAY-handler path would
fire it. SID register writes are byte-for-byte identical to the
pre-Phase-B.1 behaviour (only the cycle column shifts because
the translator now runs on every PLAY tick) — golden traces
were re-baselined.

**Phase C status for instruments / pulse: DEFERRED** — depends on
Phase B.2 6502 emission work.

For each of {wave (✅ done), instruments, pulse}:
1. Generate an SF2 from a known-good source (Stinsen).
2. Capture baseline zig64 trace (300 frames of SID writes).
3. Edit one byte in the SF2 edit area at a known offset (e.g., change
   wave row 0 waveform from $41/Pulse to $21/Saw).
4. Re-run zig64 trace.
5. Verify the trace shows the EDIT propagated — for the wave change,
   `osc<v>_control` writes should now have the saw bit set instead of
   pulse, on every voice that uses instrument 0.

Acceptance criterion mirrors v3.3.0's edit-proof tests in
`TestCriterion3EditProof`.

## What's NOT in scope for Stage 7

- **Filter table** — variant-dependent layout, deferred.
- **Commands table** — already exposed in F1 (commands appear inline
  in sequences), so per-table propagation isn't needed.
- **Multi-variant table addresses** — Phase B will hardcode Stinsen-
  class addresses. Future work could extend the Class B autodetector
  to find Wave/Pulse/Instruments addresses for other variants too.

## Compatibility

Phase A is pure Python with no behavior change — just adds the
spec module + tests. Phase B will modify the translator but should
preserve all existing v3.3.0 / v3.4.0 contracts (sequence
edit-propagation, multi-pattern segmentation, etc.). Round-trip
identity is the safety net: if no edits are applied, the bytes
written back must equal the bytes read in.
