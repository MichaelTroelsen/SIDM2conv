# Stage 7 — Edit-affects-playback for tables (instruments / wave / pulse / filter)

**Status:** Phase A shipped 2026-05-09. Phases B and C deferred.

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

### Phase B — 6502 emission (deferred)

Mirror the Phase A Python in 6502 assembly, integrated into the
existing translator at `$0F8E` (`_emit_multipat_translator` in
`sf2_writer.py`). Run once per PLAY tick, BEFORE the JSR to the
embedded NP21 player.

Estimated 6502 budget:
- Wave: ~10 bytes (loop copy of 64 bytes)
- Instruments: ~40 bytes (per-row 5-field copy with 3-byte preserve)
- Pulse: ~20 bytes (per-row 3-byte copy)
- Total: ~70 bytes additional

The translator window is currently `$0F0E..$0FFA` (≈240 bytes) and the
existing translator+multipat use ~138 bytes, so there's room. If
budget gets tight, can move HANDLER_BASE down further.

Care points:
- Each table's destination address is variant-dependent (Stinsen
  $1A6B / $1942 / $1A3B / $1989; other variants TBD via Class B
  autodetector). The 6502 routine can't hardcode these; the writer
  must patch in the addresses at SF2-build time.
- Need to handle the case where the table address is in the embedded
  NP21 binary (mostly the case) vs in the SF2 edit area itself (would
  be a self-overwrite — should skip).
- For Class B files (where ch_seq_ptr was autodetected), the table
  addresses are also autodetected — same fingerprint logic could be
  reused.

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
