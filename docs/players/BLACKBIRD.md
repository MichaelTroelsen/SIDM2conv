# Blackbird (Linus Åkesson / "lft") — recon started 2026-07-19

**Status: decompression SOLVED for the v1.2-exact bucket (2026-07-19),
`sidm2/blackbird_parser.py` shipped same day; not yet wired into the
conversion pipeline (no SF2 emission).** `bin/LFT/blackbird-1.2/` bundles the
author's own editor + `birdcruncher` exporter, **including full assembly
source** (`Export/source/player.s`, `rplayer.h`) and the **C compressor source**
(`Export/source/cruncher.c`). This is the opposite situation from every other
player in this project: instead of reverse-engineering a black-box binary, we
have the literal ground truth. That makes locate/detection, table layout, AND
now the note-stream decompression **100% solved, independently verified, and
committed as a real tested module** for all 11 v1.2-exact-bucket files (see
"Compression — SOLVED" and "Parser module shipped" below). What's left before
this is a real, wired-in SF2 converter: no Stage A/Driver 11 transpile or
native Stage B build yet, not in `DriverSelector.PLAYER_REGISTRY` (intentionally,
until SF2 emission exists) — see "What's genuinely proven vs. still open".

## Corpus scope

`SID/LFT/` has 59 files by Linus Åkesson. Splitting by how closely each file's
compiled play-routine bytes match the bundled v1.2 template (`docs` grouping
below) — this is NOT the same split as the SID inventory's player-id tag, which
only knows "Blackbird/LFT" vs generic "LFT" vs "UNIDENTIFIED" and doesn't
distinguish tool *versions*:

| bucket | count | example files | meaning |
|---|---|---|---|
| **v1.2 exact match** | 11 | Fargo, Glyptodont, Dishwasher_Groove, Dithered_Island, Elvendance, Euclid_Was_Here, Into_the_Unknown, Maple_Leaf_Rag, Revolutions_Delivered, Thus_Spoke_the_PC_Speaker, Toy_Rocket | byte-identical to `player.h`'s `seg_play_data` except at the documented relocation offsets — **locate is fully solved for these** |
| near-v1.2 variant A | 5 | Crank_Crank_Airwolf, Fugue_on_a_Theme_by_D_M_Hanlon, Quintessence, To_Die_For_II, Trinket | first diff at code offset 446 (225 total diffs) — likely birdcruncher 1.1 |
| near-v1.2 variant A' | 1 | Crank_Crank_Revolution | first diff at 393 (234 diffs) — close to variant A, not identical |
| older variant B | 10 | Arrow_of_Time, Fjaellevator_Music, Hachi_Bitto_Whirlwind, In_Darkness_Hope, Nine, Scene_Spirit_v2, ... | first diff at 204 (374 diffs) — a substantially rewritten wave/pulse engine section (`everyframe`'s waveform-read code), likely birdcruncher 1.0 |
| much-older / uncertain | 7 | Reminiscence, Lunatico_Note, A_Computer_in_My_Backpack, To_Die_For, Lunatico_Side_1, Lunatico_Side_2, Perfectly_Well-Adjusted, Your_Heptacular_Eyes | diverges almost from byte 3/5 — tagged "Blackbird/LFT" by player-id but either a pre-1.0 engine or a much more different code shape; not investigated |
| **not Blackbird at all** | ~25 | Foerklaedd_Gud (7 variants), Platform_Hopping, Sideways, Air_on_a_Rasterline, King_Fisher_0x28, Machine_Yearning_2SID, Fratres_Arvo_Paert_2SID (2SID), Hardsync (3 subtunes), Allt_under_himmelens_faeste, Nymphaea, Summer_Cloud, Slaepwerigne, Specular_Highlight, Scene_Spirit, Shards_of_Fancy, A_Chipful_of_Love_for_You | diverges almost completely (~1000+/1030 bytes) — these are Åkesson's OTHER, per-song custom-coded engines, correctly showing as generic `LFT` or `UNIDENTIFIED` in `SID_INVENTORY.md`, not Blackbird |

**Scope verdict**: ~27 files (11 exact + 16 near-variants) are genuinely the
Blackbird engine across 2-3 tool versions. That's a real but modest corpus —
smaller than MoN's 179 or Deenen's 40, more like Kimmel's 4-file scale but with
the advantage of having full source for at least one version.

## Detection / locate — SOLVED for the v1.2-exact bucket

The compiled player is a **relocatable template**: `birdcruncher` builds a fixed
1280-byte code+table blob (`seg_play_data` in `player.h`) and patches ~250 known
byte offsets with the tune's actual symbol addresses (`seg_play_reloc()` in the
same file is literally the patch list — a byte-for-byte relocation manifest,
not a guess). Comparing a real SID's play-routine bytes against this template,
**skipping only the documented offsets**, gives a deterministic yes/no — no
disassembly or signature-hunting needed, unlike every other player in this repo.

Verified end-to-end against `SID/LFT/Fargo.sid`: 100% byte match outside the
relocation slots. `playorg` (the segment's origin = `jmp initroutine`) sits
exactly at the SID's **init address** (not load — some Blackbird tunes relocate,
e.g. `Reminiscence.sid` loads at `$A000`), and **play = init + 3** (`playroutine`
label, matching the PSID header's declared play address in every case checked).

**Reading the relocated bytes back out gives every table address directly** —
no independent computation needed, since the relocation manifest tells you
exactly which offset holds which symbol:

| symbol | recovered from (offset in `seg_play_data`) | Fargo.sid value |
|---|---|---|
| `zp_base` | byte 4 = `zp_base+6` (single byte, zp<0x100) | `$E0` |
| `seg_init` | bytes 1-2 = `seg_init+0` (16-bit LE) | `$16A6` |
| `ins_ad` | bytes 553-554 = `ins_ad + -1` | `$1500` |
| `ins_sr` | bytes 559-560 = `ins_sr + -1` | `$1523` |
| `ins_wave` | bytes 533-534 = `ins_wave + -1` | `$1546` |
| `ins_filt` | bytes 526-527 = `ins_filt + -1` | `$1569` |
| `fx_start` | bytes 489-490 = `fx_start + -1` | `$158C` |
| `filttable` | bytes 372-373 = `filttable + 0` | `$15AF` |
| `fxtable` | bytes 194-195 = `fxtable + 0` | `$15CD` |
| `wavetable` | bytes 290-291 = `wavetable + 0` | `$1675` |
| `streamstart` | `seg_init_data` bytes 1 (lo) / 5 (hi) | `$1CA6` |

`ins_sr - ins_ad == ins_wave - ins_sr == ins_filt - ins_wave == fx_start - ins_filt`
gives `nins` directly (35 for Fargo) — a free consistency check, same trick as
the MoN/Tel arc's evenly-spaced-fields signature.

Scratch locate script (not yet committed to the repo — lives in this session's
scratchpad, re-derive from the table above if picking this up later):
`bb_locate.py` in the session scratchpad, built by parsing `player.h`'s
`seg_play_reloc`/`seg_init_reloc` C source directly with regex into an
offset→(symbol,delta) map, so the relocation manifest never needs to be
hand-copied or drift from the shipped tool.

## Memory layout (from `cruncher.c`'s own `org` bookkeeping, lines ~1216-1268)

```
resident (= SID init addr)      seg_play (1280 bytes: code + freq/pulse tables)
+ 1280                          ins_ad[nins]
+ nins                          ins_sr[nins]
+ nins                          ins_wave[nins]
+ nins                          ins_filt[nins]         (4 COLUMN-MAJOR parallel
+ nins                          fx_start[nfx]            arrays, 1-based index —
+ nfx                           filttable[...]            same shape as the
                                fxtable[...]               MoN/Tel column-major
                                wavetable[...]             instrument bug this
                                seg_init (86 bytes)        session just fixed)
                                <compressed note stream, ends at streamstart,
                                 read BACKWARD (decreasing addresses) at runtime>
```

## Event-byte encoding (from `player.s`'s own header comment, ~line 28-37)

Per-voice decoded byte stream (after decompression — see below), one "step" =
zero or more PREFIX tokens then usually a terminal token, consumed by a 3-phase
per-frame automaton (`prepare1`/`prepare2`/`prepare3` in `player.s`):

| range | meaning | consumed by |
|---|---|---|
| `$F9-$FF` | out-of-band (tempo change / sync / end / loop) — composer convention puts these only in voice 3's stream | `prepare1` |
| `$C9-$F8` | arpeggio/fx select (index into `fxtable` via `fx_start`) | `prepare1` |
| `$80` | gate off | `prepare2` |
| `$81` | legato (no retrigger, matches the MoN/Tel "tie" concept this session found) | `prepare2` |
| `$83-$B2` | instrument select (`(byte - $82)`, 1-based, 48 max) | `prepare2` |
| `$00-$7F` | note; **LSB is a delay-bit**, real note = `byte >> 1` | `prepare3` |
| `$B8-$C7` | delay (low 4 bits select one of 16 preset wait-frame counts) | `prepare3` |

Gate-off/legato/instrument are mutually exclusive per step ("at most one"), same
for note (note bytes ALSO imply an inline 1-frame delay via their own LSB, so a
note doesn't strictly need a following delay byte). `INS_RESTART`/`INS_RESTART2`
(two threshold instrument numbers, recovered the same relocation way) select
progressively more aggressive hard-restart behavior (matches the "avoid the
6581 ADSR delay-bug" trick documented all over `PATTERNS.md`/other player docs).

**Per-frame automaton** (`player.s` `prepare1`→`prepare2`→`prepare3`→`execute`→
`everyframe`, one voice loop each): a voice's `v_trtimer` counts UP each real
frame from a preloaded negative value; while still negative the voice is
skipped entirely. Once it wraps non-negative, prepare1-3 collectively fetch
ONE new event over up to 3 consecutive real frames (`prepare1`→`prepare2`→
`prepare3` is a genuine 3-stage pipeline, NOT three peeks at the same instant),
and `execute()` (gated by a SEPARATE `zp_master`/`zp_tempo`/`groove` cycle,
threshold `3*7`) applies whatever's been staged to the SID registers. `everyframe`
(arpeggio/pulse-width/filter-program stepping) runs every single real frame
regardless, which is why smooth vibrato/filter sweeps keep moving between note
ticks. **This tempo/pipeline interaction has NOT been fully validated against a
live trace** — the analysis above is a straight read of the disassembly, but
"tempo defines a tick grid" vs "tempo is pure pipeline latency, delay bytes are
literal frame counts" wasn't settled with a siddump/zig64 cross-check before
this recon session ended. Confirm this before building `frame_to_tick`-style
math for a `blackbird_parser.py`.

## Compression — algorithm identified, decoder NOT yet correctly replaying

The note stream is a **custom LZ77 variant with per-copy semitone transposition**,
stored **physically reversed** so the 6502 can read backward with a decrementing
pointer and reconstruct forward playback order. Reference: `unpackvoice` in
`player.s` (runtime decoder) and `crunch_some`/`run_prep1-3`/`crunch_streams` in
`cruncher.c` (the compressor — and, crucially, **the compressor's own internal
simulation of the SAME timer/pipeline automaton**, used purely to decide *when*
each voice's ring buffer needs more compressed data).

**Control-byte grammar** (verified against `cruncher.c`'s `crunch_some`, not
just the asm comment):
- top 5 bits all zero → literal: bottom 3 bits = N literal bytes follow
  (`ctrl==0` means genuine stream end, i.e. the "Stop" byte cruncher.c emits
  for a non-looping song).
- top 5 bits nonzero → back-reference copy: bottom 3 bits `n`, copy `n+3` bytes;
  top 5 bits `t` (1-31) encode transpose `t-16` (applied ONLY to bytes with
  bit7 clear, i.e. genuine NOTE bytes — every other token type, having bit7
  set by construction, copies verbatim); one offset byte follows the control
  byte. **Confirmed from the encoder** (`cruncher.c` line 494/498):
  `putbyte(bb, ((transp+16)<<3) + length - 3)` then, non-loop builds,
  `putbyte(bb, (wpos - offset) & 0xff)` — so a decoder recovers the real
  back-distance as `dist = (L - offset_byte) & 0xff` (`256` if that's `0`),
  `src = L - dist`, where `L` is **that voice's own** running decoded length
  (NOT a shared byte count across voices — see below).

**Why this needed more than the encoder's loop body read literally**: the
physical compressed stream is a SINGLE byte sequence interleaving all 3
voices' pieces via `crunch_streams`'s loop (`crunch_some(v2); prep1×[2,1,0];
crunch_some(v1); prep2×[2,1,0]; crunch_some(v0); prep3×[2,1,0]`, repeat). On
the ENCODER side `ds->rledata` (the note array) is COMPLETE from the start, so
call order between `crunch_some` and `run_prepN` is irrelevant to correctness —
both just walk a pre-existing array at different rates. On the DECODER side
it's the opposite: a voice's bytes only exist once ITS OWN reveal-step has
run, so a literal transcription of the encoder's loop crashes immediately
(voice1/voice0's own prep1 tries to peek data that hasn't been revealed yet on
frame 0, since their own `crunch_some`-equivalent runs LATER in the same
iteration).

**Fix found this session**: `player.s`'s `initroutine` explicitly primes voice1
(`X=7`) and then voice0 (`X=0`) with ONE unpack call EACH, with `preparejmp`
patched to a literal `RTS` opcode (disabling prepare1/2/3 entirely) — this
happens BEFORE the main dispatcher loop / `zp_master` cycle ever starts.
`cruncher.c` mirrors this exactly (found independently, then cross-checked):
right before calling `crunch_streams()`, the non-loop build path calls
`crunch_some(&vdecode[1], ...)` then `crunch_some(&vdecode[0], ...)` (see
`cruncher.c` ~line 1173-1176) — TWO priming pieces, voice1 then voice0, NOT
voice2, with no prep-stage attached. Voice2 gets its first real piece revealed
naturally inside the main loop's first iteration (matching the real
dispatcher: `playroutine`'s FIRST call after init has `zp_master=3*7=21`,
decrements to 14, and 14 is exactly voice2's slot — `X/7` where `$D400+X` is
the SID register offset, so `X=14→voice2, X=7→voice1, X=0→voice0`).

Adding this 2-piece priming step before the main loop fixed the frame-0 crash
completely. **Result: decoding now gets through ~3500-5200 frames (roughly
70-100 seconds of real playback) across every v1.2-exact file tried** (Fargo,
Glyptodont, Toy_Rocket, Elvendance, Euclid_Was_Here, Dishwasher_Groove all
tested) before hitting a SECOND, subtler bug — always an "internal stream
error" in `prepare3` (an out-of-grammar byte where a note/delay was expected),
consistently in the 3500-5200 frame range but on DIFFERENT voices depending on
the file (voice0, voice1, or voice2). The consistent timing across files (not
tied to any specific file's content) and the individually-plausible-looking
byte sequences right up to the crash point (proper mixes of note/delay/
instrument/gate-off bytes, correct transpose arithmetic verified by hand)
point toward a **remaining refill-scheduling drift** (a piece physically meant
for one voice's slot getting attributed to another, which wouldn't look
obviously wrong until — purely by chance, much later — a misattributed byte
lands in a position expecting a different grammar range) rather than a math
error in the LZ/transpose logic itself, which was re-verified by hand and
checks out.

**Recommended next step**: get a real 6502 emulator (py65, or
`mcp__mcp-c64__run_program`) to actually run a Blackbird-compiled SID and dump
the per-voice ring buffers live, byte by byte, as ground truth to diff the
Python port against past the ~3500-frame mark — this sidesteps further
static-analysis guessing entirely, since the real hardware defines the one
true order. The Python port (not committed to the repo — lives in this
session's scratchpad at `bb_decode.py`/`bb_locate.py`, re-derive or ask to
recover from the scratchpad if continuing) already has per-piece logging
(`PIECE_LOG`) that dumps voice/position/type/bytes for every emitted piece,
useful for diffing against a live trace once one exists.

**2026-07-19 live-trace session (RetroDebugger MCP, `Fargo.sid`)** — did the
above, manually, far enough to prove the method and get real data, not far
enough to catch the misattribution itself (that needs an automated capture,
see below):

- `unpackvoice` = playorg + 601 bytes → live-disassembly-confirmed at `$1259`
  for Fargo (`$100F: JMP $1259` matches the byte-offset math exactly — same
  relocation-manifest trick as the symbol table above, now cross-checked
  against a running CPU rather than just the static template).
- The actual control-byte fetch (`lax (zp_inptr),y`) is 3 instructions later,
  at unpackvoice+11 (`$126C` for Fargo) — break there, not at unpackvoice's
  entry, since entry fires on EVERY per-voice service call (most of which
  immediately bail via `bmi postunpack`, buffer still has >=128 bytes) while
  the fetch point only fires on genuine decode events.
- **Free ground truth per hit**: at the `$126C` breakpoint, the `A` register
  still holds `v_trwpos,x` (loaded 3 instructions earlier at unpackvoice+2 and
  never overwritten before the branch not taken) — i.e. **`L`, that voice's
  running decoded length, reads directly off the CPU registers with zero extra
  memory probing.** `X` gives the voice (0/7/14). One more memory read of
  `zp_inptr` (confirmed at `$E2/$E3` = zp_base+2 for Fargo) plus the control
  byte at that address (read backwards, decrementing) gives ctrl/offset/L for
  a complete, math-checkable record with no guessing.
- **Confirmed live**: records are packed back-to-back in the shared stream
  with no padding — a copy record is exactly 2 physical bytes (ctrl + offset),
  a literal record is `1+n` bytes, and the NEXT voice's record starts
  immediately at the next lower address, no gaps. Cross-checked the dist/src
  math from a real sample (voice0, ctrl=`$87`→copy n=7/count=10/t=16→
  transpose 0, offset=84, L=120 → dist=36, src=84, no wrap) and a wrapping one
  (voice2, ctrl=`$A9`→copy count=4/transpose+10, offset=226, L=12 → dist=42,
  src=226 — src>L, i.e. a genuine ring-wrap read of "older lap" data, which is
  valid by design, not a bug signature by itself).
- **Order is NOT simple round-robin**: sampled sequence in this session was
  voice0, voice1, voice2, voice2 (again), i.e. a voice can receive two
  consecutive records before the others get serviced again. This rules out any
  static schedule assumption for reconstructing attribution offline — it's
  genuinely load-dependent on each voice's real consumption rate, confirming
  (not just theorizing) that only a full replay recovers the true order.
- **zig64 gap found**: `mcp__sidm2-siddump__trace_sid` (the project's usual
  fast ground-truth tracer) reports **0 SID writes over 300 frames** for
  Fargo, despite RetroDebugger's live run producing audible sound over the
  same address range. Unclear why yet — Fargo is a normal PSID (init/play, no
  self-installed IRQ), so this isn't the documented RSID/`play=$0000` escape
  hatch case. Worth a bounded follow-up before trusting zig64 on any Blackbird
  file.
- **Why manual stepping didn't finish the job**: reaching the actual
  misattribution (reported around frame 3500-5200 by the Python port) this way
  means single-stepping/continuing through a LOT of individual decode events
  by hand — impractical to do exhaustively through one-by-one tool calls.
  What's needed next is a proper automated capture (a small resident script or
  a `retro_breakpoint`-driven batch loop that logs every `$126C` hit's
  X/A/`zp_inptr` without a human in the loop for each one) run long enough to
  cross the crash boundary, then diff against the Python port's own
  `PIECE_LOG`. The technique above (breakpoint address, the free-`A`-register
  trick, the record-packing model) is exactly what that script needs — it's
  now proven, just not yet run to completion.

**2026-07-19, second file — `Glyptodont.sid`, background-agent capture**: same
technique (identical addresses: `unpackvoice`=`$1259`, breakpoint at `$126C`,
`zp_inptr`=`$E2`, since Glyptodont is also a byte-identical v1.2-template
match). Delegated the mechanical continue/read/log loop to a background agent
instead of doing it by hand — captured **80 clean records spanning frames
4248-5026**, fully inside the documented 3500-5200 crash window. **Zero
anomalies again**: no early `n==0`, every dist/src computation checks out
including several genuine ring-wraps (e.g. a record at L=0 with offset=184
correctly wraps to src=184), and the same non-round-robin voice servicing
pattern (repeated back-to-back same-voice runs) as Fargo. This is now the
SECOND file confirming real hardware plays through the reported crash range
with no issue — reinforcing that the "internal stream error" is a bug in the
offline Python port's own scheduling reconstruction, not evidence of anything
wrong on real hardware. Raw data for both files (Fargo frames 4199-5371,
Glyptodont frames 4248-5026) is saved in `memory/blackbird-lft-player.md` /
this session's scratchpad for whoever fixes the offline decoder next.

## Compression — SOLVED for the v1.2-exact bucket (2026-07-19)

The root cause of the "internal stream error" was never a scheduling-order bug
at all (the scheduling simulation, mirroring `cruncher.c`'s
`crunch_some`/`run_prep1-3`/`crunch_streams`, was already correct in the prior
session's `bb_decode.py`) — it was **how the stream terminator is handled**.

Per `player.s`'s `unpackvoice`, the genuine end-of-stream control byte
(`ctrl == 0x00`, i.e. "top 5 bits zero AND n==0") is read via `txa; beq
stopstream` — **that branch happens BEFORE the instruction that decrements
`zp_inptr`**. So reading the terminator does NOT advance the shared physical
read pointer. Real hardware freezes there **permanently**: every subsequent
refill request, from ANY of the 3 voices (not just whichever one happened to
hit the terminator first), re-reads the SAME frozen byte and falls into
`stopstream`, which appends exactly one `$C0` filler byte per hit — chosen
deliberately by the original author, since `$C0` is rejected by `prepare1`/
`prepare2` as "not consumed" and accepted by `prepare3` as a valid delay code
(index 0), so the pipeline free-wheels forever without ever producing an
invalid/out-of-grammar byte.

The previous (buggy) decoder instead let its read pointer keep decrementing
past the terminator and marked only the ONE voice that hit it "done" — so the
shared pointer kept sliding into whatever real program/table bytes happen to
sit physically below the compressed-stream region, eventually producing an
out-of-grammar byte **on unrelated garbage, far past the actual end of the
real data**. That's why the crash always looked "subtle" and file-dependent:
it was never a property of the music data at all, just how far past the true
end of stream each file's particular memory layout happened to have before
hitting something `prepare3` couldn't parse.

**Verification (independently re-run, not just taken on faith)**:
- Both live-CPU ground-truth captures match **exactly**: not just "somewhere
  in the output" but a **unique contiguous subsequence** — the full 68-record
  Fargo trace and 80-record Glyptodont trace each appear at exactly one
  offset in the fixed decoder's piece stream, with every (voice, position mod
  256, control byte) triple matching in order.
- All 11 v1.2-exact-bucket files (Fargo, Glyptodont, Dishwasher_Groove,
  Dithered_Island, Elvendance, Euclid_Was_Here, Into_the_Unknown,
  Maple_Leaf_Rag, Revolutions_Delivered, Thus_Spoke_the_PC_Speaker, Toy_Rocket)
  decode to a genuine, clean freeze (real end-of-stream) with **zero**
  out-of-grammar bytes across all 3 voices.
- The decoded event-type distributions (note/delay/gate-off/instrument/arp/
  legato/oob counts per voice) look like real music data, not noise.

**Parser module shipped (2026-07-19, same day)**: `sidm2/blackbird_parser.py`
— locate + the fixed decompressor, ported from the validated scratch work
with the terminator-freeze fix intact. `pyscript/test_blackbird_parser.py`
(9 tests / 27 subtests) locks in: the strict unique-exact-contiguous-match
validation against both live-CPU ground-truth captures (now committed as
`SID/blackbird_fargo_trace_4199_5371.json` /
`SID/blackbird_glyptodont_trace_4248_5026.json`), the 11-file v1.2-exact
clean-decode sweep, and `locate_blackbird` correctly rejecting both
non-Blackbird files and the near-v1.2 variant bucket (confirmed: the older
birdcruncher 1.0/1.1 files have different compiled bytes and don't match the
v1.2 template — genuinely out of scope for now, not a bug). All of this was
independently re-verified (not just taken on the building agent's word,
matching this investigation's now-standing practice): tests re-run directly,
the strict-match code read line-by-line to confirm it really requires
uniqueness, and the sweep/false-positive/variant checks re-run by hand with
the same results.

**Still not done**: NOT wired into `sidm2/driver_selector.py`'s
`PLAYER_REGISTRY` or `sidm2/conversion_pipeline.py` yet (intentionally — no
SF2 emission exists, wiring it in now would misroute files into a broken
conversion). No Stage A (Driver 11 transpile) or native Stage B driver. The
near-v1.2 variant buckets (~16 files, older birdcruncher versions) have
different compiled bytes and need their own locate/relocation-manifest work
before they're supported — not attempted yet.

## What's genuinely proven vs. still open

- **Proven, working**: template-based detection (11/59 files), full symbol/table
  address recovery via the relocation manifest, `nins` cross-check, complete
  memory layout, the event-byte grammar (note/instrument/gate-off/legato/
  arpeggio/delay/oob ranges), the column-major 4-array instrument table shape,
  and now **the full multi-voice interleaved decompression** (scheduling +
  stream-terminator handling), verified against real CPU ground truth on 2
  files and clean-decoded on all 11 v1.2-exact files.
- **Understood but unverified**: the tempo/pipeline timing model (does it define
  a tick grid, or is it pure pipeline latency with delay-bytes as literal frame
  counts?) — the decoder replicates the automaton mechanically without this
  question needing to be answered, but it matters for eventually mapping
  decoded events to SF2 rows/frame timing.
- **Not started**: turning the validated decoder into `sidm2/blackbird_parser.py`,
  testing it against the near-v1.2 variant buckets (older birdcruncher
  versions, different compiled bytes, unlocated), and everything past
  Stage-A decode (Driver 11 transpile, native Stage B).

## Files (for a future continuation)

- `bin/LFT/blackbird-1.2/Export/source/player.s` — full player asm, `.(...)` `.ext`
  syntax (a custom assembler, not ACME/64tass) — read the header comment block
  first, then `prepare1`→`prepare2`→`prepare3`→`execute`→`everyframe` in that
  order (they cross-reference each other).
- `bin/LFT/blackbird-1.2/Export/source/cruncher.c` — the compressor; `crunch_some`
  (~line 435), `run_prep1/2/3` (~line 522), `crunch_streams` (~line 564) are the
  ones that matter for decoding; the `org`-assignment block (~line 1216) is the
  memory-layout source of truth.
- `bin/LFT/blackbird-1.2/Export/source/player.h` / `rplayer.h` — the compiled
  1280-byte template + the exact relocation manifest as executable C (parse
  with regex, don't hand-transcribe).
- `bin/LFT/blackbird-1.2/BlackbirdUsersGuide.pdf` — composer-facing docs, NOT
  read this session (no `pdftoppm` available in this environment); may have
  useful terminology but the asm source is authoritative for the byte format
  regardless.
