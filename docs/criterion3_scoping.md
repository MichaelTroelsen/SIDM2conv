# Criterion 3 — scoping document (Step 2/3 revert, then partial reversal)

**Date**: 2026-04-30 (initial scoping); 2026-04-30 update (architecture vindicated)
**Outcome**: Step 2 + Step 3 were reverted on misdiagnosis. Subsequent
investigation showed the architecture was correct; the trace failure was a
test-tool artifact (zig64 bypasses the SF2 PLAY handler). Re-attempting
with the fix; this document is kept as historical record and corrected
below.

## CORRECTION (later same day): the architecture WAS correct

The "Choice A: redirect $1A22/$1A49 instead" recommendation in the
sections below is **wrong**. After the revert, I performed an experiment:
take a v3.2.2 .sf2 file, append a shadow buffer manually, COPY the
original NP21 sequence bytes verbatim into the shadow, and patch
$1A1C/$1A1F to point at the shadow. zig64 trace then matches the ground
truth at 100% (299/299 frames). This proves:

- **$1A1C/$1A1F is read at runtime** — it's not just an init-time hook.
  The state machine at `DataBlock_6+$157,X` cycles 2 → 1 → re-init
  (Label_5 reads $1A1C/$1A1F) → 2 → 1 → ... whenever a sequence ends
  (0xFF/$Y target byte hit), state F4 decrements 1→0 and Label_5 fires.
- **The data at $1A1C/$1A1F IS the per-voice sequence stream** — it
  contains pattern_index bytes, instrument prefixes, and the loop
  terminator. The player reads it, decodes it, and the pattern_index
  byte resolves into the per-pattern note pointer at $1A22/$1A49 just
  like with the original NP21 binary.

So Step 2's pointer-patching WAS correct. The reason Step 3's trace
showed 0.67% was that zig64 calls `play_addr` ($1003 patched as JMP
$1006) directly, bypassing the SF2 PLAY handler at $0F04 where the
runtime translator's JMP $0F0E lived. The translator never executed
during zig64's trace, so the shadow stayed at the defensive $FF $00
init Python applied. That bytes-of-zeros input to the player produces
the "all voices converge on pattern 0" symptom I diagnosed below as a
pointer-table bug — but it's actually a shadow-not-populated bug.

**Recovery plan:** the previously reverted Step 2 + Step 3 are correct as
a unit. Two-line fix: have Step 2 pre-fill the shadow with the SF2-edit-
area bytes already translated through `sidm2/sf2_to_np21.sf2_to_np21()`
(so zig64's flow gets a correct shadow even without running the runtime
translator), AND keep Step 3's runtime translator at $0F0E (so the
editor's PLAY path regenerates the shadow whenever the user has edited
the SF2 edit area).

The original scoping recommendation (redirect $1A22/$1A49 instead) was
based on an incomplete reading of the state machine. Section "What I
actually found at run-time" below is left intact for historical context;
the conclusion in "Recommendation" is superseded.

---

## Original scoping (as written, with wrong conclusion)

**Outcome (as written initially)**: Step 2 (shadow buffer + ch_seq_ptr patch) reverted. Step 3
(6502 translator) abandoned in current form. The runtime-translator
approach is **not yet viable** as planned because the plan's model of the
NP21 player's sequence-read path is incomplete.

**Current state**: v3.2.2 (commit `4bc0443`) + Step 1's pure-Python
reference translator (commit `702df8f`). Step 2 reverted. Stinsen +
Unboxed both back at 100% zig64 frame-set match.

## What the plan said

`docs/criterion3_plan.md` (commit `10b2c27`) assumed:

> The laxity SF2 driver runs the original NP21 player code, which reads
> sequences from inside the embedded NP21 binary at ch_seq_ptr ($0A1C/$0A1F).

Step 2 patched `c64_data[$0A1C+v]` / `c64_data[$0A1F+v]` to redirect each
voice's sequence read to a per-voice shadow slot. Step 3 emitted a 6502
translator at `$0F0E` that filled the shadow at PLAY time from the SF2
edit area at `seq00_addr`.

## What I actually found at run-time

When Step 2 + Step 3 were both in place, Stinsen's zig64 trace dropped
from 100% to **0.67%** (2/299 frames matching). Unboxed by coincidence
matched at 100%, but for the wrong reasons (see below). Investigation:

### The player has TWO sequence-pointer tables

Reading `drivers/laxity/laxity_player_disassembly.asm:62-156` carefully:

**Table 1 — `$1A1C/$1A1F` (3 lo + 3 hi bytes)** — accessed at the **INIT**
or **state-reset** path only, gated by `DataBlock_6+$157,X == 1`:

```
; Label_5 ($106F)
LDA  DataBlock_6+$157,X      ; voice state
CMP  #$01
BNE  Label_8                 ; if state != 1, skip to playback
LDA  DataBlock_6+$F4,X
BNE  Label_8                 ; if F4 != 0, skip
INC  DataBlock_6+$F4,X
LDA  DataBlock_6+$37B,X      ; $1A1C+X — read once at init
STA  ZP_0
LDA  DataBlock_6+$37E,X      ; $1A1F+X
STA  ZP_1
LDY  DataBlock_6+$F1,X
LDA  (ZP_0),Y                ; read first byte of seq init metadata
```

What this path actually does: it reads a small **header** from `$1A1C/$1A1F`
that contains an instrument prefix (e.g. `$A0`) and a **pattern_index**
byte. The pattern_index is stored to `DataBlock_6+$FA,X`. After this
runs once, state advances to `$157,X = 2` (set at `$1115`) and Label_5
is no longer entered for that voice — until the song's order-list
advances and a new state-1 reset is triggered.

**Table 2 — `$1A22/$1A49` (40+ lo + 40+ hi bytes)** — accessed on **every
PLAY** for normal note decoding:

```
; Label_8 ($10AF) — the per-frame sequence reader
LDA  DataBlock_6+$E2          ; some "playing" gate
BNE  Label_16
DEC  DataBlock_6+$EE,X        ; per-voice tick counter
BPL  Label_16
LDY  DataBlock_6+$FA,X        ; pattern_index (set by Label_5 above)
LDA  DataBlock_6+$381,Y       ; $1A22+Y — pattern pointer LO
STA  ZP_0
LDA  DataBlock_6+$3A8,Y       ; $1A49+Y — pattern pointer HI
STA  ZP_1
LDY  DataBlock_6+$F7,X        ; current Y offset within pattern
LDA  (ZP_0),Y                 ; read note byte → byte_decoder
```

The pattern_index in `$FA,X` indexes into the table at `$1A22/$1A49` to
get the **actual** per-pattern note-stream pointer. This is where the
real notes come from.

### So patching only `$1A1C/$1A1F` doesn't redirect playback

The shadow buffer is read by Label_5 (the init path). It interprets
shadow byte 0 as an instrument prefix (`SEC; SBC #$A0`), shadow byte 1
as the pattern_index, etc. That pattern_index is then used UNCHANGED
with the **original** `$1A22/$1A49` table to find the actual note stream.
The note stream is read from inside the original NP21 binary, never from
the shadow.

Stinsen's voices end up with garbage instrument values (because shadow
byte 0 was `$FF` from my defensive init, and `$FF − $A0 = $5F`) and all
three voices converge on `pattern_index = 0` (because shadow byte 1 was
`$00`). All three voices then play pattern 0's note stream — which gives
the observed "all voices play the same notes" trace divergence.

### Why Unboxed matched at 100% (coincidence)

Unboxed's voices 0/2 share the same source sequence in `$1A1C/$1A1F`
(both pointed at the same address; `addr_to_sf2_idx` collapsed them to
pattern index 0). The original pattern_index for those voices was 0.
When the shadow's byte 1 was also 0, the resulting garbage state
happened to align with the original behaviour for two of three voices,
and the third voice's divergence was small enough to fall within
matching-frame tolerance for the specific 300-frame trace. This is **not
a real success** — it's an artifact of Unboxed's pattern_index distribution.

## Implications

The plan's pseudocode for Step 3 — translate `seq00_addr` bytes into the
shadow on every PLAY — does the right thing for what the **editor**
displays, but the **player** reads notes from a different memory region
that the translator doesn't touch.

Three architectural choices follow:

### Choice A — redirect `$1A22/$1A49` instead of `$1A1C/$1A1F`

Patch the per-pattern pointer table at `$1A22/$1A49` to point at shadow
slots. The 6502 translator translates each pattern in the SF2 edit area
into its shadow slot at PLAY time.

**Open questions:**
- How many patterns does the table hold? (Counted from disassembly: at
  least 39 entries — `$1A22-$1A48` lo + `$1A49-$1A6F` hi, so 39 patterns.
  Some are referenced, others may be dead.)
- The SF2 editor's view of the song needs to match this granularity. The
  editor's Block 5 currently exposes `track_count = 3` and `seq_count = N`
  (where N = number of unique voice initial sequences, typically 3). For
  approach A the editor needs `seq_count = 39+` so each pattern is
  visible. The current `_build_np21_sf2_edit_area` would need to extract
  every entry from `$1A22/$1A49`, follow each pointer to its note stream,
  walk it to find a 0xFF terminator, and store one per Block-5 sequence
  slot.
- The editor's user model becomes "edit one of 39 short sub-patterns"
  rather than "edit one of 3 song-level sequences". That's a different
  tracker UX than what the SF2 editor was designed for. But it might map
  naturally to SID Factory II's concept of sequences-within-an-orderlist.
- Cycle budget for translating 39 patterns × ~30 bytes each = ~1200 bytes
  per frame. ~12k cycles. About 60% of a PAL frame — tight.

**Estimated effort:** 6-10h (reverify the table size, extract patterns,
extend the SF2 generator, write a wider-range translator).

### Choice B — redirect a higher-level structure (the orderlist)

The orderlist (still mostly unmapped) drives state transitions that
re-enter Label_5 with new `$157,X = 1` state. If we find where the
orderlist lives, redirecting THAT might be the cleaner level — edits
to the orderlist propagate via the existing init path through to the
pattern_index, and the pattern table can stay original.

**Open questions:**
- Where is the orderlist? Need more disassembly reading. Likely
  somewhere referenced by `DataBlock_6+$157,X` transitions or by
  whatever sets `$F4,X` back to 0.
- Edits to orderlist mean "play these patterns in this order" — that's
  a useful thing to edit but doesn't let the user edit per-note content.

**Estimated effort:** unknown until orderlist is located.

### Choice C — abandon the runtime-translator approach

Fall back to plan approach 2 (Driver-11 re-encode) or approach 4
(round-trip on save). Both require larger pieces of work. Approach 2
loses the v3.1.5+ raw-NP21 verbatim-embedding property; approach 4
doesn't satisfy real-time edit-and-replay.

## Recommendation

**Pause Step 3** as currently scoped. Keep Step 1's Python reference
translator (committed `702df8f`) — it correctly inverts the byte mapping
and stays useful for any future translator work.

Choice A is the most natural path forward: redirect `$1A22/$1A49`
instead. The 6502 translator's per-byte transform from Step 3 still
applies (it's correct for the byte format); only the addressing changes
(more, smaller patterns instead of 3 × 256-byte slots). Most of the
infrastructure already in place is reusable.

But before committing to A, the orderlist question (Choice B) deserves
a 1-2h investigation — if the orderlist is small and easily located, it
might offer a cleaner edit surface than 39 individual patterns.

## What this revert restores

- `sidm2/sf2_writer.py` back to the v3.2.2 layout: ch_seq_ptr untouched,
  no shadow buffer, PLAY at `$0F04` is the standard `JSR play_addr; RTS`
- `pyscript/test_sf2_writer.py` test helpers back to 2-tuple unpack
- `_build_np21_sf2_edit_area` returns `(music_data_params, sf2_edit_bytes)`
  — the `voice_init_idx` exposure introduced in Step 2 is removed

What stays from criterion-3 work so far:
- **v3.2.2 byte-mapping fix** (`4bc0443`): real bug fix, independent of
  the runtime-translator approach. Editor view of every existing `.sf2`
  is now correct.
- **`docs/criterion3_step0_findings.md`** (`4bc0443`): the player byte
  semantics writeup; still accurate, still useful.
- **`sidm2/sf2_to_np21.py`** + 7 round-trip tests (`702df8f`): the
  byte-level translator spec is independent of which addresses the
  shadow lives at. Reusable for choice A.

## Notes for the next attempt

- Re-verify `$1A22/$1A49` table size by counting actual references in
  the player. The disassembly comment said `+ $381,Y` and `+ $3A8,Y`
  — the gap between `$381` and `$3A8` is `$27 = 39`, suggesting 39
  entries. Confirm by walking the disassembly for any other reference
  to `$1A22+Y` or `$1A49+Y`.
- The voice **state machine** (`DataBlock_6+$157,X`) determines when
  Label_5 vs Label_8 runs. Map all the transitions. If state ever resets
  to 1 mid-song (e.g. on orderlist advance), `$1A1C/$1A1F` is read more
  than once and might still be a useful hook.
- The `voice_init_idx` map added in Step 2 was correct for what Step 2
  *thought* it was doing — pulling per-voice sequence info from
  `$1A1C/$1A1F`. For choice A we'd want a different map: per-pattern
  pointer extraction from `$1A22/$1A49`.
