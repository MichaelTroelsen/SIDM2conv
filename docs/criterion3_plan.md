# Plan: close criterion 3 — runtime SF2→NP21 sequence translator in the laxity driver

## Context

v3.2.1 keeps NP21 playback frame-accurate by embedding the song's own NP21 player
binary verbatim at $1000+ (`_inject_laxity_raw_np21` at sf2_writer.py:1449). The
SF2 editor area is appended *after* the binary and uses SF2 packed sequence
format; the player keeps reading sequences from inside the embedded NP21 binary
via the per-voice pointer table at sid_la+$0A1C / sid_la+$0A1F (verified:
`DataBlock_6` is at $16A1 in the relocated player and the per-voice pointer
load instructions at $107E / $1083 reference `DataBlock_6 + $37B,X` /
`DataBlock_6 + $37E,X`, i.e. absolute $1A1C / $1A1F).

Result: edits made in SIDFactoryII never reach the player. Criterion 3 fails.

The previous attempted fix ("store NP21 bytes at seq00_addr; point ch_seq_ptr
there") was rejected because the SF2 editor's `DataSourceSequence::Unpack`
(simulated in `pyscript/verify_editor_view.py`) asserts on byte values that are
legal in NP21 (0xFF as loop marker is read as a command prefix; 0x80 as
gate-off is read as duration; etc.).

## Recommendation: Approach 1 (runtime translator) — narrowed in scope

I'm picking option 1 from the brief, with one specific narrowing: the
translator runs in the **wrapper code area** (the gap between the SF2 handler
stub and the embedded NP21 binary, $0F0E–$0FFF — 242 bytes free) and writes
into a **shadow buffer appended after the SF2 edit area**. Pointer table
$1A1C/$1A1F is patched once at file build time to point into the shadow buffer,
not into the original NP21 sequence bytes. The embedded NP21 binary is otherwise
untouched (we already modify these 6 bytes — that does not violate "verbatim
embedding"; the existing `_inject_laxity_music_data` path patches them too).

Why not the others:
- **Approach 2** (Driver-11 re-encode) abandons the v3.1.5+ accuracy property
  that gives us 100% frame-set match today. Multi-week rewrite.
- **Approach 3** (custom SF2II) requires shipping a forked editor binary —
  user has flagged this requires explicit sign-off.
- **Approach 4** (round-trip on save) doesn't meet "edits affect playback"
  if interpreted as runtime re-replay; only meets it via reconvert.

## Architectural shape

```
file build time (Python, sf2_writer.py)            run time (6502, on every PLAY)
────────────────────────────────────────           ──────────────────────────────
                                                   ┌──────────────────────────┐
       SF2 edit area  ────────────────────────►    │ translate_sf2_to_np21    │
       (seq00_addr, SF2 packed format,             │  - read SF2 bytes        │
        editor reads/writes here)                  │  - shift notes -1        │
                                                   │  - rewrite terminator    │
                                                   │  - write NP21 bytes      │
                                                   └──────────┬───────────────┘
                                                              ▼
                                                   ┌──────────────────────────┐
       shadow buffer (NEW, appended)        ◄───── │ shadow buffer            │
       768 bytes, 3 × 256 NP21-format        ────► │ (player reads here)      │
                                                   └──────────┬───────────────┘
       $1A1C/$1A1F patched ONCE at build               player JSR play_addr
       to point at shadow voice slots                  reads from $1A1C/$1A1F
                                                       ──► hits shadow, NOT
                                                           original NP21 bytes
```

PLAY handler at $0F04 changes from
`JSR play_addr; RTS` (4 bytes)
to
`JSR translate; JSR play_addr; RTS` (7 bytes — fits, $0F04..$0F0A).

INIT handler at $0F00 stays `JSR init_addr; RTS` (the shadow doesn't need
seeding pre-init: the first PLAY runs the translator before the player's first
sequence read).

## Critical files

- `sidm2/sf2_writer.py` — the only Python that needs to change.
  - `_inject_laxity_raw_np21` (line 1449): allocate shadow buffer space, emit
    translator code at $0F0E, patch $1A1C/$1A1F bytes inside `c64_data` to
    point at shadow voice slots, extend PLAY handler.
  - `_build_np21_sf2_edit_area` (line 1570): return additional metadata —
    seq count, shadow base addr, source seq addresses — so the caller can
    emit the translator with correct constants. Update the EDITABLE-REPLAY
    GAP comment to record what shipped.
- `pyscript/verify_editor_view.py` — no code change; used as a regression check.
- `drivers/laxity/laxity_driver.asm` — no change. The translator is emitted
  procedurally from Python; it lives in the existing $0D7E–$0FFF wrapper
  region, not in the assembled wrapper itself.

## Implementation plan

Each step has a check that the implementer can run before moving on. Effort is
in calendar hours assuming the implementer is already familiar with the repo.

### Step 0 — Resolve the byte-semantics unknowns (PRE-WORK, blocking)

Before writing any 6502, hand-validate the actual NP21 byte encoding by
inspecting Stinsen's sequence data. The task brief and `sf2_writer.py:1693`
disagree on whether NP21 0x00 means C-0 or gate-off, and whether NP21 0x80–0x9F
are duration bytes or something else. The translator can't be written until
the truth table is settled.

How to settle:

1. Convert Stinsen with current converter, dump 32 bytes starting at the seq
   address pointed to by $1A1C/$1A1F in the embedded NP21 binary, and the
   first 32 bytes at `seq00_addr` (SF2 edit area). Diff them.
2. Cross-check with the disassembly at $10C9–$1108
   (`drivers/laxity/laxity_player_disassembly.asm:111-156`):
   - `bpl Label_12` at $10CB means MSB-clear bytes are notes (0x00–0x7F).
   - `cmp #$C0/bcc`, `cmp #$A0/bcc`, `cmp #$90/bcc` cascade fixes the
     command/instrument/duration ranges.
   - At $10F4–$10FB, `value == 0` and `value == 0x7E` both branch to
     `inc DataBlock_6+$100,X` (Label_13). This is "no new note" — the gate
     stays in its current state. So **NP21 0x00 == "no note this tick"** and
     **NP21 0x7E == tie**, both behaving identically here. Pitch bytes are
     0x01–0x7D.
   - That contradicts `sf2_writer.py:1693` ("NP21 0x00 = C-0"). The current
     +1-shift translation in `_build_np21_sf2_edit_area` may itself be wrong.
3. Write the truth into a comment block at the top of the new translator and
   into the EDITABLE-REPLAY GAP comment.

Verification check: `py -3 -m pytest pyscript/ -q
--ignore=pyscript/test_disassembler.py` still reports 778 passed, 7 skipped
(baseline must not move from this step alone — no code changes yet).

Effort: 1–2 h. Failure mode if wrong: every downstream step builds on a bad
truth table; the entire plan needs to restart.

### Step 1 — Add a pure-Python reference translator

In a new module `pyscript/sf2_to_np21_translator.py` (or as a function inside
`sf2_writer.py`), implement `sf2_to_np21(seq_bytes: bytes, loop_target: int |
None) -> bytes` matching the truth table from step 0. This is the spec the
6502 must match.

Verification: write a unit test in `pyscript/test_sf2_writer.py` (or a new
`test_sf2_to_np21.py`) that round-trips:
NP21-source-bytes → `_build_np21_sf2_edit_area` SF2 encoding → new translator →
NP21-bytes, and asserts equality with the source modulo a known boundary
(terminator byte). Test count goal: +3 tests, baseline becomes 781 / 7.

Effort: 1 h. Failure mode: round-trip identity fails — likely means the +1
note shift in `_build_np21_sf2_edit_area` is wrong (see step 0); fix there
first.

### Step 2 — Allocate shadow buffer and patch pointer table

In `_inject_laxity_raw_np21` (sf2_writer.py:1449), after the `sf2_edit_data`
is built, append a `shadow_buffer = bytearray(num_patterns * 256)` to the file
extent. Update `gen.driver_size` accordingly. Compute
`shadow_base = sf2_data_base + len(sf2_edit_data)`. For each voice v in 0..2:
- Read original ch_seq_ptr value from `c64_data[0x0A1C+v]`/`c64_data[0x0A1F+v]`.
- Map to a sf2 sequence index (already done by `addr_to_sf2_idx` in
  `_build_np21_sf2_edit_area` — return that map).
- Compute `voice_shadow_addr = shadow_base + sf2_idx * 256`.
- Overwrite `c64_data[0x0A1C+v]` and `c64_data[0x0A1F+v]` with lo/hi of
  `voice_shadow_addr`.

Verification: with translator NOT YET emitted, run the trace tool. Player will
read zeros from shadow → SID writes diverge → trace will not match. That's
expected. The check at this step is structural only: load the file in
`pyscript/verify_editor_view.py`, confirm Block 5 still parses cleanly and
the editor still sees the SF2 edit area unchanged. (Editor display does NOT
read $1A1C/$1A1F.)

Effort: 2 h. Failure mode: the SF2 file extent grows past the SF2 max load
area or violates the `headers_end_addr < HANDLER_BASE` invariant — handled by
existing safety check at sf2_writer.py:1500. If shadow can't fit, **EXIT**:
write the scoping doc.

### Step 3 — Emit the 6502 translator at $0F0E

Hand-assemble the translator into a Python `bytes` literal, parameterised on
`(num_patterns, seq00_addr, shadow_base, seq_count, seq_size, loop_metadata)`.
Pseudocode:

```
translate_all:
    LDX #(num_patterns - 1)
.loop_pat:
    ; src = seq00_addr + X * 0x100   (uses LDA hi-byte table, since X*256 is
    ;                                 just the high byte)
    ; dst = shadow_base + X * 0x100
    ; -- copy 256 bytes, transforming each --
    LDY #$00
.byte_loop:
    LDA (src_zp),Y          ; src_zp set up before
    ; --- per-byte transform ---
    ; if A == $7F: write loop terminator $FF, $00 then break
    ; if A < $80: subtract 1 to undo SF2 1-based note (only for pure note bytes
    ;             — but command/instrument/duration prefixes use bytes >= 0x80
    ;             so MSB-clear is unambiguous)
    ; else: pass through
    STA (dst_zp),Y
    INY
    BNE .byte_loop
    DEX
    BPL .loop_pat
    RTS
```

Concrete sizing target: ≤ 96 bytes of 6502. Hand-count opcodes; if it
overflows the $0F0E–$0FFF slot (242 bytes) the slot is fine, but the more
likely overflow is total file size. A 256-byte-per-pattern shadow with 128
max patterns is 32 KB — keep the actual `num_patterns` value, never the
SEQ_PTR_SIZE max.

Then patch PLAY handler at $0F04:

```
$0F04:  20 0E 0F        JSR translate_all   ; new
$0F07:  20 lo hi        JSR play_addr       ; was $0F04
$0F0A:  60              RTS
```

Verification A (identity): convert Stinsen fresh, run
`tools/sidm2-sid-trace.exe out.prg 300 > new_trace.csv`, diff against
`SID/stinsen_sid_trace_300frames.csv`. **Must match byte-for-byte** because
the translator with the editor's current bytes must reproduce the original
NP21 bytes (this is the "translator is identity when no edits applied"
property — criterion 1 of success).

Verification B (editor still works):
`python pyscript/verify_editor_view.py out.prg` — no assertions. (Criterion 2.)

Verification C: same procedure for Unboxed against
`SID/unboxed_sid_trace_300frames.csv`.

Effort: 4–6 h.

Failure mode 3a: traces drift on frame N → translator output at byte N
disagrees with source NP21. Fix the per-byte transform. Common bug: $7E
handled wrongly, or notes shifted in the wrong direction.

Failure mode 3b: traces drift on frame 0 → pointer-table patch is wrong or
shadow base is wrong. Fix step 2.

Failure mode 3c: `verify_editor_view.py` asserts → step 3 should not have
touched the SF2 edit area; check that you wrote to `shadow_base`, not
`seq00_addr`.

### Step 4 — Edit-proof test (the actual criterion 3)

Add an integration test (new file `pyscript/test_criterion3_edit_proof.py`)
that:
1. Convert `SID/Laxity/Stinsens_Last_Night_of_89.sid` to .sf2, copy to .prg.
2. Run trace, save baseline.
3. Read the file, locate `seq00_addr` from Block 5, find the offset of voice
   0's first note byte (parse the orderlist+sequence header by mirroring the
   logic in `verify_editor_view.py`).
4. Replace that byte with a different pitch value (e.g. add 12 = one octave
   up, clamping to 0x6F). Save back as a new .prg.
5. Run trace again. Assert that at the frame where voice 0 first sets gate=1
   (D404 bit 0), the corresponding D400/D401 (voice 0 frequency low/high)
   write differs from the baseline and matches the predicted new frequency.

Predicted-frequency math: NP21 note → SID frequency lookup table is at
`DataBlock_6 + $237` (lo) and `DataBlock_6 + $238` (hi) per the disassembly
at $1141/$1147. Compute against that table.

Verification: this test passes. (Criterion 3.)

Effort: 3 h. Failure mode: the byte we patched isn't actually a "note" byte
(could be a duration prefix or a command); the orderlist parser needs to
correctly skip non-note bytes. If repeated edits don't reach the player,
return to step 3 — the translator may be re-translating from a stale source.

### Step 5 — Update the EDITABLE-REPLAY GAP comment

Replace the comment block at sf2_writer.py:1577–1599 with a record of what
shipped: the runtime translator approach, where the translator code lives
($0F0E), where the shadow buffer lives, what byte transforms it does, and a
note that any future change to the SF2 edit-area layout has to update the
translator's per-byte transform too.

Verification: `py -3 -m pytest pyscript/ -q
--ignore=pyscript/test_disassembler.py` reports 779 (or higher) passed, 7
skipped (baseline 778 + step 1's tests + step 4's edit-proof test).
(Criterion 4.)

Effort: 0.5 h.

## Unknowns the plan needs to discover (call them out, don't wave away)

1. **NP21 byte truth table** (step 0). The brief, the existing converter,
   and the player disassembly are not all consistent. This MUST be settled
   before step 1.
2. **Whether the +1 note shift in current `_build_np21_sf2_edit_area` is
   correct.** v3.1.9 changelog says it is, but step 0's analysis of the
   player code shows NP21 0x00 == "no new note" not "C-0". If it's wrong,
   the editor view of every existing converted .sf2 has been off-by-one and
   the translator needs to compensate symmetrically (no shift) — and
   v3.1.9's bug is reopened.
3. **What `0xFF` plus a Y-target byte means in the SF2 packed reader.**
   `verify_editor_view.py` would treat 0xFF as a command prefix and consume
   the next byte as instrument/duration/note. Today's converter strips it
   (sf2_writer.py:1630–1635) and emits 0x7F at the end of the seq. The
   shadow needs a real loop terminator. Likely: emit `$FF $00` (NP21 loop)
   in the shadow, and the editor never sees the shadow.
4. **Frame budget for the translator.** Worst-case input across the test
   corpus (not just Stinsen/Unboxed). 256 × N patterns × ~10 cycles/byte =
   should fit, but verify on a song with many patterns.
5. **Shadow buffer size cap.** If a song has > ~50 patterns, the shadow
   exceeds ~12 KB. SF2 file load address is $0D7E so max addressable is
   $FFFF — plenty of headroom — but does the SF2 player's RAM bank handle
   files that large? Confirm before assuming 128 patterns.

## Exit criterion (write a scoping doc instead)

Stop and write `docs/criterion3_scoping.md` — capture findings + a
concrete go/no-go recommendation for approach 2 — if any of these hit:

- Step 0 reveals that the NP21 sequence format in the wild has variants
  beyond the documented byte ranges (e.g. Unboxed uses different
  command-byte semantics than Stinsen). A single-table translator can't
  cover it; this argues for approach 2.
- Step 3 trace identity check (verification A) drifts within the first 8
  frames *after* fixing obvious transform bugs and pointer math — implies
  the player is reading sequence data via a path other than $1A1C/$1A1F
  that we haven't found. Investigate before continuing.
- Step 3 cycle measurement on a representative song shows translator >
  ~1500 cycles, which combined with the player's existing ~5–8 K cycles
  per frame puts us within 10% of the PAL frame budget on worst case —
  switch to dirty-flag translation, which the editor doesn't support; that
  argues for approach 4.
- Step 4 edit-proof test only works when the edited byte happens to be a
  note byte; durations/commands/instruments don't propagate. That implies
  the editor's notion of "edit" doesn't map cleanly to the player's notion
  of frame-data — partial coverage of criterion 3 only, document and ship
  partial.
- Shadow buffer size cap exceeded (>16 KB for some real song) — file
  addressing problem; document and ship a max-pattern limit instead.

## End-to-end verification (after step 5)

```
./sid-to-sf2.bat SID/Laxity/Stinsens_Last_Night_of_89.sid out_stin.sf2
./sid-to-sf2.bat SID/Unboxed_Ending_8580.sid               out_unbox.sf2
cp out_stin.sf2  out_stin.prg
cp out_unbox.sf2 out_unbox.prg

# Criterion 1: identity
tools/sidm2-sid-trace.exe out_stin.prg  300 > t_stin.csv
tools/sidm2-sid-trace.exe out_unbox.prg 300 > t_unbox.csv
diff t_stin.csv  SID/stinsen_sid_trace_300frames.csv   # must be empty
diff t_unbox.csv SID/unboxed_sid_trace_300frames.csv   # must be empty

# Criterion 2: editor view clean
python pyscript/verify_editor_view.py out_stin.sf2
python pyscript/verify_editor_view.py out_unbox.sf2

# Criterion 3: edit-proof
py -3 -m pytest pyscript/test_criterion3_edit_proof.py -v

# Criterion 4: full suite
py -3 -m pytest pyscript/ -q --ignore=pyscript/test_disassembler.py
# expect: 779+ passed, 7 skipped
```

All four must pass before the EDITABLE-REPLAY GAP comment is rewritten.
