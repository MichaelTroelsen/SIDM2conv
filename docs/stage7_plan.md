# Stage 7 — Edit-affects-playback for tables (instruments / wave / pulse / filter)

**Status:** Phase A shipped 2026-05-09. **Phase B.1 plumbing shipped
2026-05-09**, but actual edit propagation BLOCKED on per-variant
wave-table reverse-engineering — see "Phase B.0" below. Phase C
deferred.

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

### Phase B.0 — Per-variant wave-table address RE (BLOCKER)

**Empirical finding 2026-05-09**: the Stinsen wave-table extraction
in `extract_all_laxity_tables` returns wave_addr=`$17EC`, but py65
trace shows that's a region of MUTATING player state (byte 2 changes
from `$20` to `$41` during PLAY) — not a static wave table the
player reads. Direct edits to bytes at `$17EC` mid-tick don't
propagate to playback because the player overwrites those bytes
itself.

The canonical CLAUDE.md address `$1942` has structured-looking data
(repeating `$7F` end-of-program markers) but direct edits there
ALSO don't change the SID register writes the player issues to
`osc<v>_control` ($D404/$D40B/$D412). So `$1942` isn't the read
source either, at least not for the bytes I tested.

The actual NP21 wave-read path is more complex than a flat
2-byte-per-row table. Likely candidates:
- A wave PROGRAM is a sequence of bytes terminated by `$7F`,
  played byte-by-byte each tick by the player. The "read source"
  is wherever the player's current program pointer is at that
  tick — varies per voice, per beat.
- The waveform value written to `osc<v>_control` may be derived
  by combining a STATIC waveform byte (from one table) with a
  DYNAMIC gate-bit decision (from sequence state) — not a single
  byte read.

So Phase B can't proceed via simple "flat table copy" because the
table abstraction doesn't match NP21's runtime layout. Real options:

1. Disassemble Stinsen's NP21 player, find the actual `LDA <addr>;
   STA $D404` (or `STA <osc_control_table>` etc.) instruction, and
   trace back to find the wave-read source address.
2. Run the player under py65 with read-tracing AND filter for reads
   that immediately precede SID register writes — that pinpoints
   the read addresses dynamically.

Until Phase B.0 is done, Phase B.1's plumbing is shipped but
inactive (no routine emitted). The `_emit_wave_copy_routine` is
kept as ready-to-call infrastructure for when an address is
known.

### Phase B.2 — 6502 emission for instruments / pulse (deferred)

Same model as Wave but more complex (field rearrangement). Same
Phase B.0 blocker: need to know the actual NP21 read addresses for
instrument/pulse tables, not just where the extractor THINKS they
are.

Estimated 6502 budget once Phase B.0 unblocks:
- Wave: 12 bytes (loop copy of 64 bytes; already implemented)
- Instruments: ~40 bytes (per-row 5-field copy with 3-byte preserve)
- Pulse: ~20 bytes (per-row 3-byte copy)
- Total: ~72 bytes additional

These would all live in the SF2 edit area (no translator-window
budget concern), called via JSR from the multipat translator.

### Phase C — End-to-end zig64 verification (deferred)

For each of {wave, instruments, pulse}:
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
