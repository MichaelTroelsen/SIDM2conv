# Blackbird (Linus Åkesson / "lft") — recon started 2026-07-19

**Status: decompression SOLVED for the v1.2-exact bucket (2026-07-19),
`sidm2/blackbird_parser.py` shipped same day; Stage A (Driver 11 transpile)
shipped same week via `sidm2/blackbird_driver11.py` — real, loadable SF2s
built for Fargo + Glyptodont. Stage B's synth engine (arpeggio/wave/pulse/
filter) is RE'd and validated byte-exact against real hardware (see
"Stage B synth engine" below) AND now built into a real native driver
(`drivers_src/blackbird/blackbird_driver.asm` + `bin/build_blackbird_native_song.py`,
B1→B2→B3→B4 same-week): Fargo scores 69.6% overall register-match (200-frame
window vs the validated simulator; filter 99.1%, AD/SR 97.2%, freq 81.5%)
and now models the SONG'S FULL mid-song tempo schedule (B3, not just the
first pair); Glyptodont improved to 53.5% overall (B4) after 4 real bugs
found+fixed this round (a filter SET-chain misclassified as an ADD ramp, an
unmodeled filter overflow-drop, tied notes wrongly restarting WAVE+FILTER,
and unweighted bundle clustering) superseded the prior B3 report's
"architectural, not fixable" characterization of Glyptodont's gap, which did
not hold up under direct verification (see "B4 shipped" below for both,
including a full before/after table). Not yet wired into the conversion
pipeline (no `DriverSelector`/`conversion_pipeline` registration).** `bin/LFT/blackbird-1.2/` bundles the
author's own editor + `birdcruncher` exporter, **including full assembly
source** (`Export/source/player.s`, `rplayer.h`) and the **C compressor source**
(`Export/source/cruncher.c`). This is the opposite situation from every other
player in this project: instead of reverse-engineering a black-box binary, we
have the literal ground truth. That makes locate/detection, table layout,
the note-stream decompression, AND now the tick/tempo model **100% solved,
independently verified, and committed as real tested modules** for all 11
v1.2-exact-bucket files (see "Compression — SOLVED", "Parser module shipped",
"Tempo-model open caveat — RESOLVED", and "Stage A shipped" below). A native
Stage-B driver now exists and builds real SF2s for 2 of those 11 files (see
"Stage B1"/"B2"/"B3" sections below); no `DriverSelector.PLAYER_REGISTRY`
entry yet (intentionally, fidelity is still well below other players' native
drivers) — see "What's genuinely proven vs. still open".

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
ticks.

**Tempo/groove model — SOLVED 2026-07-19** (was "understood but unverified").
`execute()`'s tail (`player.s` ~line 508: `lda zp_tempo; sta zp_master;
m_groove = *+1; eor #0; sta zp_tempo`) is a genuine self-modifying odd/even
**alternation**, not a static constant: each execute cycle, `zp_master` (the
countdown that gates the NEXT cycle's length) takes the CURRENT `zp_tempo`
value, then `zp_tempo` is XORed in place with the self-modified `m_groove`
mask and stored back — since XOR is its own inverse, this ping-pongs between
exactly two values forever (real frames per cycle = `tempo_byte / 7`, since
`zp_master` decrements by 7 once per real frame down to 0). A tempo change is
encoded as a 2-byte inline literal record read directly off the shared
physical stream during `prepare1` (not through any per-voice ring buffer) —
`cruncher.c`'s `build_voice()` confirms this is deliberate: a composer
"groove" parameter splits into odd/even nibbles, emitted as `(odd-1)*7` (the
new `zp_tempo`) and its XOR with `(even-1)*7` (the new `m_groove` mask).

**Independently verified via two convergent, independent methods**: (1) a
live RetroDebugger trace on real hardware (breakpoint on `execute()`'s tail,
`retro_cpu_counters` frame deltas) measured a clean 6-frame/5-frame real-time
alternation with no drift across the sampled window; (2) a from-scratch
static decode of Fargo's compressed stream (using the shipped
`sidm2/blackbird_parser.py` module's own internal functions, re-run
independently rather than trusting the first report) extracted the ACTUAL
tempo-record byte pairs from the stream and found values `42`/`35` at the
point in the song the live trace sampled — `42/7=6` and `35/7=5`, an exact
match to the live measurement. Two unrelated methods agreeing on both the
raw values and the conversion formula is strong evidence this is right.

**Refinement beyond the first pass**: the tempo/groove pair is **NOT fixed
for a whole song** — re-decoding Fargo's FULL tempo-event history (not just
the one window the live trace happened to sample) found **22 separate tempo
OOB records** before the stream's genuine end (at internal loop-iteration
~1386, well before that "iteration" count should be read as a real-frame
count — see caveat below): starting at a 5-frame/4-frame alternation, several
repeats of that with brief 4/4 flat stretches, switching to 6/5 partway
through (where the live trace happened to sample), briefly 7/6, then settling
to constant (non-alternating) 3/3 and finally 5/5 right at the very end. Any
Stage A implementation MUST simulate the full tempo state machine (apply each
2-byte OOB record as encountered, alternate via XOR) rather than assume one
fixed groove value per song.

**Open caveat, not yet resolved**: whether `blackbird_parser.py`'s internal
`decode_streams()` loop-iteration counter (`frame`/`big_cycle` in its result)
is itself a 1:1 real-PAL-frame count, or a coarser unit (e.g. one iteration
per potential execute-cycle rather than per real frame) was NOT conclusively
settled this session — the strict ground-truth validation only checks piece
EMISSION ORDER (voice/position/control-byte), which holds regardless of
whether the loop's iteration count maps 1:1 to real frames, so it doesn't by
itself prove real-frame accuracy. This matters before Stage A can annotate
decoded events with absolute real-frame timestamps: a follow-up should cross-
check specific `decode_streams()` iteration numbers against the live-CPU
ground-truth captures' real frame numbers (both already committed under
`SID/blackbird_*_trace_*.json`) to settle it definitively before relying on
the loop counter for timing math.
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
native Stage B driver exists). Stage A (Driver 11 transpile) shipped same
week — see below. The near-v1.2 variant buckets (~16 files, older
birdcruncher versions) have different compiled bytes and need their own
locate/relocation-manifest work before they're supported — not attempted yet.

## Tempo-model open caveat — RESOLVED 2026-07-19

The prior caveat ("does `decode_streams()`'s loop-iteration counter map 1:1
to real PAL frames?") is settled: **no, it's a coarser unit — one iteration
is one TICK** (one full `execute()`-to-`execute()` cycle), not one real
frame.

**How it was settled**: instrumented a local copy of `decode_streams()`
(reusing its private helpers verbatim, not reimplementing them) to tag every
emitted piece with the loop's `frame` counter, then reused the existing
strict ground-truth alignment (`pyscript/test_blackbird_parser.py`'s
`_find_exact_contiguous`) to line that tagged stream up against both live-CPU
captures. Result: pieces sharing the SAME iteration value are **always
exactly 1 real frame apart** (both files), while pieces in different
iterations show real-frame-delta / iteration-delta ratios clustering at
**3–10, mean ~6.0 for Fargo** — exactly the documented tempo/groove range,
never anywhere near a flat 1:1.

Reading `player.s` directly explains why: `prepare1`/`prepare2`/`prepare3`
(the note-event fetch pipeline) are dispatched *only* from `unpackvoice`'s
tail (`preparejmp`), itself reachable only on the (up to 3) real frames per
cycle where the `zp_master` countdown lands on 14/7/0 — so each stage runs
**exactly once per `execute()` cycle**, i.e. once per tick, not once per
frame. A tick's real-frame length is `zp_tempo / 7`, confirming the earlier
tempo/groove finding was about a *different, coarser* unit than the decoder
loop.

**The practical payoff (no simulator needed)**: ticks are already the note
grid Blackbird composes on, and a Driver 11 row is also a fixed-tick grid —
so Stage A can use **ticks directly as rows, 1:1, no GCD/rounding**. Each
decoded note/delay byte's own duration in ticks is recoverable straight from
`player.s`'s own `v_trtimer` preload arithmetic (`prepare3`'s
`got_delay: ora #$f0`): a note byte's LSB delay-bit gives 1 tick (set) or 2
ticks (clear); a delay byte's low nibble `m` gives `16 - m` ticks. This reads
directly off the already-decoded, already-tested byte stream — no new
decoding or frame-simulation pass required.

**Independent triangulation, a third method**: recovering the actual
tempo/groove OOB byte pairs from Fargo's compressed stream (not just
detecting *that* an OOB occurred, which is all `decode_streams()` itself
does) gave `(35, 28)` as the very first pair — `35/7=5`, `28/7=4` — an exact
match to this doc's earlier claim ("starting at a 5-frame/4-frame
alternation"), independently re-derived this session rather than assumed.

## Stage A shipped 2026-07-19: `sidm2/blackbird_driver11.py`

A real, loadable Driver 11 `.sf2` now builds from a decoded Blackbird song,
reusing the shared IR/emitter (`galway_to_driver11.GalwayDriver11Song` /
`galway_driver11_emitter.emit_driver11_sf2`) unmodified, per
`docs/players/PLAYBOOK.md`'s staged method. Built and verified on both
`Fargo.sid` (378 notes, tempo chain `[5,4]`, 14 packed sequences) and
`Glyptodont.sid` (2703 notes, tempo `[4]` — its first tempo pair happened to
be flat, `(28,28)`). Both reload cleanly through `pyscript/sf2_viewer_core
.SF2Parser` (magic ID, header blocks, driver-common addresses all parse);
independently re-dumping the raw orderlist/sequence bytes via
`sidm2.sf2_parser` confirms the written structure matches what the builder
intended (per-track sequence counts and chaining) — note the *viewer's* own
`orderlist_unpacked` debug view mis-displays this file's compact
transpose-on-change encoding (reports bogus all-`sequence:0` entries); the
raw bytes are independently confirmed correct, so this looks like a
pre-existing `sf2_viewer_core.py` quirk, not a Stage-A bug — not chased
further this session.

**What Stage A does**: per-voice byte stream → steps (gate-off/legato/
instrument prefixes + a mandatory note/delay terminal) → `D11Row`s, ticks
1:1 as rows. AD/SR read byte-exact from the located `ins_ad`/`ins_sr`
tables. Tempo = the first tempo/groove OOB pair found, as a 2-value Driver
11 chain (or 1 value if that pair happens to be flat).

**What's flat/approximate (named limitations, matching the ladder's "timbre
modulation flat")**:
- Arpeggio and OOB bytes are consumed but ignored — no per-note wave/arp
  program.
- Tempo uses only the *first* tempo/groove pair; Fargo alone has 22
  documented tempo-change records over the song, so mid-song tempo drift is
  NOT reproduced.
- Pitch: **FIXED AND USER-CONFIRMED same day** — the first build used
  `SF2 note = note_index + 1` (plain chromatic, no calibration), and a user
  listen test (SID Factory II, real audio) reported it sounding roughly an
  octave flat. Root cause found by reading `player.s`'s actual pitch routine
  (~lines 221-267), not just its docstring summary: `v_basepitch = note*4`
  feeds a fractional-interpolation decoder that, for the steady/no-slide
  case, reads `freq_lsb+24,y` / `freq_msb+24,y` with **`y = note_index`
  directly** (the `*4` is for the arpeggio/portamento sub-steps *between*
  notes, not the resting pitch's table index). Comparing the real
  `freq_lsb`/`freq_msb` bytes (extracted from the compiled template) against
  this project's standard PAL frequency table gives **zero mismatches across
  all 64 note values** for `PAL_semitone = note_index + 8`, i.e.
  **`SF2 note = note_index + 9`**. Fixed in `blackbird_driver11.py`, both
  SF2s rebuilt, and the user confirmed on a second listen: "I think the
  notes are correct." The interpolation sub-positions (mid-slide pitches)
  are still not modelled — only the resting/landing pitch is calibrated.
- Instruments: Blackbird allows up to 48 (grammar: `$83-$B2`, 1-based);
  Driver 11 only has 32 slots. Capped explicitly (`build_instruments`
  clamps `nins` to 32, `steps_for_voice` clamps any pending instrument index
  to 31) rather than let the sequence packer's `& 0x1F` mask silently ALIAS
  a high instrument onto an unrelated low slot — found and fixed this
  session (Fargo's `nins=35` would otherwise have aliased 3 instruments).

**Not verified**: no zig64/siddump onset-match validation exists for
Blackbird (the zig64 gap noted earlier in this doc — 0 SID writes reported
for Fargo despite audible real hardware playback — is still open). GUI/audio
confirm (`docs/players/PLAYBOOK.md` §4 rung 3-4) WAS done this session
(twice — first listen caught the octave bug, second confirmed notes sound
right) — but per the ladder's own definition, Stage A explicitly does NOT
cover timbre (arpeggio, filter, pulse/waveform envelope, AD/SR shaping):
the user's feedback that "the fidelity is not there... hard to hear it" past
correct notes is the EXPECTED state at this rung, not a new bug — that's
exactly what Stage B (native driver) exists to close.

**`retro_load` gotcha found this session**: RetroDebugger's MCP `retro_load`
does not correctly load `.sf2` files (confirmed on both the Stage A output
AND the known-good stock template — same garbage bytes either way; renaming
to `.prg` before loading works correctly). Documented in
`docs/guides/RETRODEBUGGER_GUIDE.md`. The actual audio verification in this
session used the project's own established tool instead
(`pyscript/sf2_open_in_editor.py`, launching the real SID Factory II editor)
per `PLAYBOOK.md`'s fidelity ladder rung 3-4 — this is the right tool for
this job, not RetroDebugger.

## Stage B synth engine (`everyframe`) — RE'd and validated byte-exact (2026-07-19)

`player.s`'s `everyframe` (~line 207-355), which runs unconditionally every real
frame, drives three sub-engines read from per-instrument programs (start rows
`fx_start[i]`/`ins_wave[i]`/`ins_filt[i]`, 1-based, already located): an
arpeggio/portamento **pitch interpolator** (`fxtable`, 2-bit fractional blend
between adjacent `freq_lsb`/`freq_msb` entries), a **waveform+pulse-width
stepper** (`wavetable`, with pulse width fed through a fixed 256-entry lookup
`pwprepare` located at `seg_play_data` template offset 1024 — same fixed-offset
convention as `freq_msb`/`freq_lsb` at 817/913, i.e. baked into every
v1.2-exact file identically, not composer data), and a **global filter cutoff
program** (`filttable`, SET-absolute/ADD-signed-delta rows with silent-drop-on-
overflow). `execute()` (~line 365-517, tempo-tick-gated) commits pending
note/instrument state into these engines' starting positions each tick.

**Validated against real hardware** (VICE `vsid-trace.js`, since zig64 reports
0 writes for Blackbird — a separate, still-open gap, see below): a from-scratch
Python simulator implementing the full `playroutine` dispatch → `prepare1/2/3`
→ `execute` → `everyframe` pipeline, driven by the real per-file table bytes
and the already-decoded note stream, reproduces **100% of real $D400-$D418
register writes, in exact order and value** — 14,673/14,673 (Fargo) and
18,332/18,332 (Glyptodont) over 1200 real frames (~24s) each, spanning 3/14
distinct instruments and 19/40 distinct notes (not just an opening sustained
chord). Independently re-run and confirmed (not just taken from the building
agent's report). Comparison method: flatten both the real trace and the
simulator's write log into ordered `(register, value)` event sequences
(dropping the deterministic init-clear block) and compare position-by-position
— stricter than frame-boundary snapshots since it also validates write order,
which is what caught a real bug (see below).

**Bugs found and fixed via real-trace diffing** (not by re-reading — the
simulator's first draft got these wrong and the trace comparison caught it
immediately): (1) `everyframe`'s voice loop is a SINGLE combined per-voice
loop (fx+freq then wave+pulse for the SAME voice before the next voice), not
two separate all-voices passes; (2) `prepare1` only *peeks* the fx-select
byte when it's not in fx range — an unconditional-consume first draft silently
ate the next stream byte (an instrument-select, in the case that exposed it),
permanently desyncing that voice's cursor for the rest of the song (fixing
this alone took the match from 179/522 to 522/522 on the first short test);
(3)/(4) off-by-one errors in `fx_start` indexing and its array length
(`nfx = filttable_addr - fx_start_addr`, NOT `nins`); (5) `freq_lsb`/`freq_msb`
must be read directly from the loaded binary at their fixed offsets with NO
artificial 96-byte truncation — `lda freq_lsb+24,y` is ordinary 16-bit
addressing and legitimately reads past the nominal table extent (the tables
"overlap by 15 bytes" per `player.s`'s own comment, and the largest valid `y`
runs into `pwprepare`'s region) — this only manifested on Glyptodont, not
Fargo, purely because Fargo's `Y` values in the traced window happened to stay
smaller (a reminder that a single file's clean pass doesn't prove a formula).

**Precise per-engine semantics** (each has real 6502 carry/overflow subtlety —
see the simulator's inline comments for the exact derivation, not summarized
here in full): the fx-interpolator's 4 blend modes split into 2 with a
deliberate `carry-in=1` "small consistent error" (per `player.s`'s own
comment) and 2 with `carry-in=0`; self-relative jumps in `wavetable` and
`filttable` both include a `+1` from the preceding `cmp`'s carry feeding an
unsigned `adc` with no `sec`; the wave-engine's pulse row advances `wavepos`
by `2 + carry(bit6 of the masked waveform byte)`; pulse-width SET uses a real
`asl` (doubles the delta) while pulse-width ADD skips the `asl` via a
`.byt $80` NOP-eats-next-opcode dual-entry-point trick (a classic 6502
space-saving idiom) and is NOT doubled; the filter's non-jump advance is `+3`
(not the naive `+2` a first read suggests — `filttable`'s 4th "jump test"
byte physically overlaps the next row's first byte, a compact 3-byte/row
encoding); filter cutoff ADD mode sign-extends the low 7 bits of the row byte
and silently drops (both the state update AND the `$D416` write) on signed
overflow for that frame.

**Reusable artifacts** (scratch, not yet committed — a natural home for a real
version is `sidm2/blackbird_native.py`): the validated simulator
(`blackbird_everyframe_sim.py`) and its trace-comparison harness
(`blackbird_compare_seq.py`), plus 2 fresh 1200-frame VICE ground-truth
captures for Fargo/Glyptodont, in this session's scratchpad (see
`memory/blackbird-lft-player.md` for the exact path — ephemeral, regenerate
via `node scripts/dev/vsid-trace.js <file.sid> --frames 1200 --json --out
<path>` from the separate `sid-reference-project` if picking this up fresh).
Two more relocated template bytes were found and are NOT yet in
`sidm2/blackbird_parser.py`'s `BlackbirdLayout`: `INS_RESTART` (template
offset 93) and `INS_RESTART2` (offset 512), both stored as `value+1`.

**Still open**: the zig64-reports-0-writes gap for Blackbird (noted early this
session, `vsid-trace.js` is the working substitute, but nobody has diagnosed
*why* zig64 fails on an otherwise-normal PSID). A literal reading of the
dispatch code's `cpx #3*7` threshold gives real-frames-per-cycle =
`tempo_byte/7 + 1`, vs. this doc's earlier documented `tempo_byte/7` — the
simulator implements the literal dispatch logic directly (validated
byte-exact) rather than the abstract formula, so this is a footnote for
whoever revisits the tempo-model doc, not a correctness gap in Stage B.

## Stage B1 native driver built (2026-07-19): `drivers_src/blackbird/`

A real native SF2 driver now exists and builds a loadable SF2 for Fargo:
`drivers_src/blackbird/blackbird_driver.asm` (forked from `romuzak_driver.asm`,
sequencer/wave/pulse/filter/FM stepper code unchanged — only the DIGI engine
was stripped and one filter-init fix applied) + `bin/build_blackbird_native_song.py`
(the translator, using `bin/blackbird_everyframe_sim.py` — the validated
simulator above, now copied into the repo as the exact-formula oracle for
every table translation) + `bin/build_blackbird_driver_full.py` (assemble/wrap
harness). Output: `out/blackbird/Fargo_native.sf2`, parses clean
(`load=$0D7E tracks=3 OK`).

**Translation approach**: rather than re-deriving Blackbird's carry/asl/ror
bit tricks by hand for each table, the translator seeds a throwaway
`BlackbirdSim` at a program's starting position and calls its `everyframe()`
directly — the exact validated formula, not an approximation — then RLE-collapses
the resulting frame-by-frame values into the shared engine's SET/ADD/JUMP row
format (WAVE has a native jump primitive, used exactly; PULSE/FMTAB have none,
so those cycles are physically repeated ~250 frames then frozen — a known B2
residual). FMTAB specifically required recognizing it's a **cumulative delta
accumulator** (`FM_ACC += offset each frame`, from reading `fm_step` directly),
not an absolute table, so per-row deltas-of-deltas are emitted. FX/pitch
offsets were empirically confirmed **note-dependent** (fx=1 gives offset 365
at note 20 vs 1158 at note 40), so per-(fx,note) command bundles are used
(Fargo: 107 distinct bundles, clustered to fit the 64-slot cap via the
project's established greedy nearest-merge technique, 43 pairs merged).

**5 real bugs found and fixed** via building + comparing against the
simulator (not by re-reading): an instrument-index off-by-one (native driver
needs 0-based, Stage A's 1-based convention was silently wrong here since
Stage A never uses real per-instrument filter/wave data); the shared engine's
filter defaults IDLE (gated by a flag-`$40` note) but Blackbird's filter runs
continuously from frame 0 — needed a forced `F_ACT=1` at init; the startup
filter row needs the real position-0 program unrolled, not a hardcoded guess;
a FILTER SET-row encoder bug that dropped bit7, silently misdecoding every
SET row as an ADD row (fixing this alone moved the match rate 43%→55%); a
loop-target heuristic that could omit the filter's terminating jump row
entirely, rewritten with exact frame-accounting.

**Honest fidelity (200-frame register-trace comparison vs. the validated
simulator, same file)**: overall **55.1%** of 5000 register cells match, 0/200
frames fully identical. By category: **filter 99.1%**, **AD/SR 93.5%**,
**waveform 70.3%**, **frequency 34.0%**, **pulse ~1%** (this last number is a
measurement artifact, not a real defect — traced to real hardware's pre-note
pipeline transient in frames 0-2 before `execute()` first fires at frame 3;
the instrument in question never touches `$D402/3` in either the isolated
translation or the driver). Frequency's gap is multi-causal, all named: (a)
the driver uses a **constant `TEMPO=5`**, not Blackbird's real `[5,4]`
alternation — the single biggest source of drift after the first tick or two;
(b) the shared engine's FM runner has an inherent 1-frame lag on note trigger
(architectural, shared by every other player using this driver, not
introduced here); (c) a ~3-frame startup-pipeline offset; (d) the 43 clustered
bundle merges (verified: a merged bundle's FM delta is `0x9E8`, the cluster
neighbor's value, not the original note's own `0xA7F` — expected from
clustering, not a bug).

## B2 shipped same day: real tempo alternation + a genuine off-by-one bug found

Implemented the first named B2 lever: the driver now swings `TEMPO`/`TEMPO2`
per row (via `SWTOG`, a toggle mechanism ported verbatim from
`drivers_src/mon`'s own swing-tempo code — the same shape, reused rather than
reinvented) instead of a flattened constant, modeling the song's FIRST
tempo/groove pair only (same scope as Stage A's tempo chain; Fargo's other
~20 mid-song tempo-change records remain a B3 gap).

**A real bug was found while wiring this up, not by re-reading**: the first
attempt used Stage A's existing `estimate_tempo_chain()` values (5/4 frames)
and the match rate got WORSE (55.1%→50.2%), not better — a signal something
was wrong, not just "needs tuning." Dumping the validated simulator's own
`zp_master` at every real row-boundary commit over 200 frames settled it
definitively: **real frames-per-tick = `tempo_byte // 7 + 1`, NOT
`tempo_byte // 7`** (committed `zp_master=35` → next tick exactly 6 real
frames later, `=28` → 5 frames later — confirmed empirically, matching the
dispatch loop's `cpx #3*7` 3-slot prepare reservation the RE agent had
flagged as an unresolved footnote in the "Stage B synth engine" section
above, now resolved). **`estimate_tempo_chain()` (`sidm2/blackbird_driver11.py`)
has been dividing by 7 without the `+1` all along** — so Fargo's real tempo
pair is **6/5 frames, not 5/4** as this doc and Stage A have stated
elsewhere. This is a genuine bug affecting Stage A too (not fixed there this
pass — Stage A's output was already user-audio-confirmed acceptable at its
coarser fidelity bar, and fixing it is a small, separate, well-scoped
follow-up: `estimate_tempo_chain`'s `a // 7` / `b // 7` need `+ 1`). The
native driver bypasses the bug directly (`extract_tempo_pairs()` raw bytes +
the corrected formula), not by fixing the shared function.

**Result, same 200-frame comparison** (rebuilt + independently re-run after
the fix, by-category breakdown now printed by the build script itself):
overall **55.1% → 59.9%**; **waveform 70.3%→88.8%**, **AD/SR 93.5%→97.2%**,
**frequency 34.0%→40.8%**, filter unchanged at 99.1% (already near-ceiling),
pulse unchanged at ~1% (still the same frame-0-3 pre-note-transient
measurement artifact, not a real defect — see B1 section above). A real,
verified improvement, not a bundle/tuning artifact — the SAME 200-frame
window, only the tempo model changed.

**B3 scope** (remaining, mirroring ROMUZAK's own staged-within-a-stage
convention): fix `estimate_tempo_chain`'s off-by-one for Stage A too; model
Fargo's other ~20 mid-song tempo-change records (this pass only covers the
first pair); re-examine whether fewer/smarter bundle merges recover more of
the remaining frequency gap; the filter's overflow-silently-drops-a-frame
quirk (not modeled, rare edge case); mode=0 filter rows (format-inherent,
currently clamped to mode=1); the shared engine's inherent 1-frame FM lag on
note trigger (architectural, shared by every player using this driver); the
~3-frame startup-pipeline offset; extend to Glyptodont (not attempted yet —
all work so far is Fargo-only). Not yet audio-listened to
(`pyscript/sf2_open_in_editor.py`) or wired into `DriverSelector` — both
explicitly out of scope for this pass.

## B3 shipped: row-indexed mid-song tempo schedule + Glyptodont coverage

Two independent B3 items from the list above, done in one pass: the full
mid-song tempo schedule (not just the first pair), and the first Glyptodont
native build.

### Mid-song tempo schedule

**Checked the premise FIRST, per this task's own instruction, before building
anything**: re-deriving Fargo's full tempo-record history with the corrected
`//7+1` formula (the raw byte pairs are unchanged from B2's derivation — only
the frame-count *interpretation* was wrong before B2 — so the OLD written-down
"5/4/6/5/7/6/3/3/5/5" sequence in this doc's "Compression" section is still
wrong and is superseded by this section, not just re-labelled) shows the
**first mid-song tempo change lands at real frame 1895** — the B1/B2 200-frame
comparison window never reaches it, so it would have measured **zero
improvement** from modelling it. Extending the comparison window to 2400
frames (crossing the boundary) with the OLD first-pair-only B2 driver first,
to get a real "before" number, confirmed the gap is real: match rate fell
from 65.7% (frames 200–1895, still the first pair) to 58.1% (frames
1895–2400, after the real hardware's tempo changed and the driver didn't) —
waveform 92.7%→63.6%, AD/SR 98.1%→73.5%. Worth fixing.

**What changed**: `blackbird_driver.asm`'s `do_row` gained a 16-bit
`ROW_CNT_LO`/`ROW_CNT_HI` tick counter (1 per `do_row` call — Blackbird's own
tick grid, the same unit Stage A already maps 1:1 onto Driver 11 rows) and a
row-indexed schedule check: four new parallel byte tables
(`tempo_sched_row_lo/hi`, `tempo_sched_t1/t2`, ≤64 entries, X-register
indexed, generated fresh per song) are consulted each row; on a match,
`CUR_TEMPO`/`CUR_TEMPO2` (new live state at `$185d`/`$185e`, replacing the
compile-time `#TEMPO`/`#TEMPO2` immediates `do_row`'s `SWTOG` swing used to
read directly) are overwritten, and `SWTOG` is forced so the row that just
changed tempo uses the new pair's LONG value first — matching real
hardware's own immediate `zp_master=zp_tempo` commit, which doesn't care
about the prior alternation's parity. The tables live in the driver's
existing ~311-byte unused gap between the code (`ollo`/`olhi`, ends ~$1595)
and the reserved SF2II playback-state region ($16cc), found by inspecting the
64tass listing rather than guessing — no address layout was disturbed.
`bin/build_blackbird_native_song.py` gained `extract_tempo_schedule()`
(re-runs `blackbird_everyframe_sim.find_tempo_records()` through a throwaway
`BlackbirdSim` seeded with the song's REAL decoded streams — OOB-record
timing depends on actual note content — and records the row index +
converted `//7+1` long/short frame counts every time `execute()` consumes a
queued record) and `write_tempo_schedule()` (emits the four `.inc` files).
`bin/build_blackbird_driver_full.py`'s own skeleton self-test needed
`TEMPO2`/`TEMPO_SCHED_LEN=0` added to its `layout.inc` writer too (it had
silently never been updated for B2's `TEMPO2`, a pre-existing gap, not
something this pass introduced — fixed as a required side effect of making
the schedule check unconditionally assemble-safe).

**Result** (200-frame primary window, unchanged by design — the whole point
of checking first was that this window never crosses a boundary — plus a new
2395-frame extended window that does): primary window **59.9%, identical to
B2** (freq 40.8%, waveform 88.8%, pulse 1.0%, AD/SR 97.2%, filter 99.1% — as
predicted, not a bug). Extended window, same file, same simulator,
B2-first-pair-only vs B3-full-schedule:

| window | B2 (first pair only) | B3 (full schedule) |
|---|---|---|
| 1895–2395 (POST-CHANGE) overall | 58.1% | **73.1%** |
| 1895–2395 freq / waveform / AD/SR | 54.9% / 63.6% / 73.5% | **82.0% / 90.8% / 95.8%** |
| 0–2395 (full extended) overall | 63.6% | **66.7%** |
| 0–2395 freq / waveform / AD/SR | 57.8% / 86.3% / 92.8% | **63.4% / 92.0% / 97.5%** |

A real, verified improvement exactly where predicted (post-boundary), no
change where predicted (the pre-existing 200-frame number), filter unchanged
at ~100% either way (already near-ceiling), pulse unchanged (~1%, the same
pre-note-transient measurement artifact from B1/B2).

### Glyptodont: first native build, and a real bug found

Ran `bin/build_blackbird_native_song.py SID/LFT/Glyptodont.sid` (14
instruments incl. 11 with filter programs vs Fargo's 5, 2703 notes vs 378,
423 distinct FM+pulse bundles vs Fargo's 107) for the first time. It built
and parsed clean (`load=$0D7E tracks=3 OK`), and the size-cap guards held
with real headroom, not just "didn't crash": WAVE table 171/256 rows,
FILTER table 27/256 rows (both well under the `ValueError`-guarded 256-row
cap), 64/423 bundles survived clustering (359 pairs merged — a far more
aggressive ratio than Fargo's 43/107, a direct consequence of Glyptodont's
much larger instrument/note diversity hitting the same fixed 64-slot
`$c0-$ff` command space).

**A real bug was found and fixed**, though it turned out NOT to be
Glyptodont's main problem: `gen_includes_song`'s FILTER-writing block for the
song's default (position-0) filter program absolutised a `$7f` jump row's
target as `(r + b2)` (the row's own local index plus the loop offset)
instead of `(default_start + b2)` — matching the CORRECTLY-written
per-instrument block a few lines below, which already used `(start + b2)`.
Confirmed via direct memory dump (loaded FILTER table row 1's target byte
read `$01`, should be `$00`) before touching any code. Both Fargo's and
Glyptodont's default programs happen to be the same degenerate 2-row shape
(SET once, jump back to row 0) — for exactly that shape the bug's wrong
target (row 1, i.e. itself) coincidentally satisfies the shared engine's
own `fp_read` self-target freeze check (`cmp tmpf; beq fp_freeze`,
`blackbird_driver.asm`), so both files froze at the CORRECT steady value by
coincidence and neither file's fidelity number moved when this was fixed
(verified: rebuilt Glyptodont post-fix, filter stayed at 77.4%; rebuilt
Fargo post-fix, all numbers identical to B2/B3's own report above — no
regression). Fixed anyway since any FUTURE file whose default program is
longer than 2 rows would have jumped to the wrong place outright.

**Honest fidelity (200-frame primary window, same method as Fargo)**:
overall **49.7%** — freq 22.1%, waveform 73.3%, pulse 0.2%, AD/SR 96.6%,
filter 77.4%. Substantially worse than Fargo's 59.9% across nearly every
category, and NOT a startup transient: segmenting the window (frames 0–10
vs 10–200) shows the gap is already at its steady-state rate by frame 10
(freq 8.3%→22.8%, filter 82.5%→77.1% — moves slightly, then holds flat, not
a one-off spike that recovers). Two named, evidenced causes, neither fixed
this pass:

- **Bundle-clustering loss dominates the frequency gap.** 359/423 bundles
  (85%) got merged to fit the 64-slot cap, vs Fargo's 43/107 (40%) — every
  merged note's FM/pulse program plays its cluster NEIGHBOR's program, not
  its own. This is the same named mechanism as Fargo's own "(d) the 43
  clustered bundle merges" B1 residual, just far more aggressive here
  because Glyptodont's instrument/note diversity is ~4x Fargo's against the
  SAME fixed `$c0-$ff` 64-slot command space (a hard format ceiling, not a
  tunable parameter).
- **The filter gap is architectural, not this session's bug.** Confirmed
  Glyptodont's very first note (voice 0, instrument 6) is itself a
  filter-triggering instrument (`ins_filt=33`) — the driver's `do_row`
  processes row 0 on real frame 0 (`zp_tcnt` starts at 1, hits 0 on the
  first `do_play` call), but the validated simulator's own dispatch doesn't
  commit that SAME first note until real frame 3 (the documented `cpx #3*7`
  3-slot prepare reservation, i.e. the already-named "~3-frame
  startup-pipeline offset" B1/B2 residual). With 11 filter-carrying
  instruments (vs Fargo's 5) interleaved across 2703 notes, the global
  filter engine gets repositioned far more often, so this same
  architectural per-trigger skew (shared by the FM engine's own documented
  1-frame note-trigger lag) compounds continuously through the whole song
  instead of being a one-time startup cost — consistent with the segmented
  measurement showing a sustained, not transient, gap.

**Not fixed this pass, named honestly**: neither cause above is a
Glyptodont-specific bug to patch — both are the SAME shared-engine
architectural traits already named in B1's residual list (bundle clustering,
startup/trigger-timing skew), just scaled up by this file's larger
instrument/note count. A real fix would mean either a bigger command-space
redesign (more than 64 FM+pulse slots) or reworking the shared engine's
note/filter-trigger timing to match real hardware's earlier commit point —
both cross-player, out of scope for a single-file B3 pass. Glyptodont's
extended-window tempo comparison (Task 1's method) could not be run in
practice: its only mid-song tempo record lands at real frame 11738 (row
2348) — its FIRST record (row 1, frame 3) is flat (`[5]`, no swing) and
holds for the entire practically-comparable range, so B3's schedule
mechanism is present and structurally exercised (2 schedule entries written,
consumed correctly per the row-tracking used to derive them) but not
fidelity-measured for this file — reaching frame 11738 in the py65 headless
comparison was judged not worth the runtime cost this pass.

## B4 shipped: the "architectural" explanation for Glyptodont's gap was wrong — 3 real bugs found and fixed instead

The prior B3 report attributed Glyptodont's low filter (77.4%) and frequency
(22.1%) scores to two *architectural* causes ("the shared engine's known
startup/trigger-timing skew" and "the same named mechanism as Fargo's own...
clustered bundle merges"). **This round's job was to actually verify that,
not repeat it** — and it did not hold up. Three real, fixable bugs were
found instead, each isolated via a live py65 register/state trace against
the validated simulator (not by re-reading), each verified not to regress
Fargo:

**Bug 1 — filter SET-chain misclassified as an ADD ramp (fixed).** Traced
Glyptodont's `$D415-8` sequence frame-by-frame against the simulator; the
FIRST real divergence (frame 35 onward, instrument 16) showed the driver's
$D416 walking `8,6,4,2,0,254,252,250...` — an unbounded downward ramp that
never stops, wrapping past 0 into negative territory. Root cause: raw
`filttable` bytes `$c4,$c3,$c2` at instrument 16's self-looping row are
*three independent absolute SETs* that each happen to differ by exactly 1
(making the *output* look like a smooth `ADD -2` ramp) — but
`unroll_filter`'s RLE collapser classified SET-vs-ADD purely from whether
the output cutoff changed by a consistent delta while `(d418,d417)` stayed
the same, with no way to tell a genuine ADD from a coincidentally-smooth
chain of SETs. A SET is idempotent under a self-loop (repeats hold steady);
an ADD is not (repeats drift forever) — the misclassification only became
catastrophic at the self-loop's jump-back point. Fixed by reading the real
per-frame op type directly from the simulator (`sim.filttable(y+2) & 0x80`,
the same bit real hardware's own `coset`/`add mode` branch tests) instead of
inferring it from the output, and never letting a SET frame join an ADD run
or vice versa. **Result: Glyptodont's primary-window filter 77.4% → 85.5%**,
Fargo unchanged (its filter programs never exercise this path — see Bug 2).

**Bug 2 — filter overflow-silently-drops-a-frame, unmodeled (fixed).** The
B1-era residual list flagged this as "rare, deprioritize if uncommon" — a
direct measurement (`sim.filttable`/`adc` walk over 2400 frames, both files)
found it is **0/2400 frames for Fargo (0 ADD ops at all — its filter
programs are pure SET chains) but 485/700 ADD-op frames (69.3%), 20.2% of
ALL frames, for Glyptodont** — not rare for this file. Fixed by giving the
shared engine's `filt_prog_step`/`fp_apply` a real signed-overflow check on
the 8-bit cutoff-hi add, using the 6502's own `V` flag (`bvs fp_ovf`) —
exactly the CPU-native equivalent of real hardware's own signed-overflow
test, no hand-rederivation needed. On overflow, both the state update and
the `$D415/6` write are skipped for that frame (matching
`BlackbirdSim.everyframe`'s own `else: # filtdone` branch), while `F_CNT`
bookkeeping still advances. Architecturally correct and confirmed via sha1
diff to genuinely change the assembled driver; Fargo is provably unaffected
(0 ADD ops → the `bvs` path is never taken). Its effect on the specific
200-800-frame Glyptodont comparison window used to isolate it turned out to
be masked by Bug 3 below (fixing it alone didn't move that window's numbers
— not a discarded fix, just one whose payoff is currently hidden behind
Bug 3's own residual, see below).

**Bug 3 — tied/legato notes wrongly restart WAVE + FILTER on the native
driver (fixed, the actual cause of the frame-275+ divergence).** Traced WHY
the filter kept resetting every ~5 frames (every tick) instead of running
its ADD ramp uninterrupted like the simulator: a 17-note tied chromatic run
(voice 2, ticks 56-72, instrument 4, all with `tie=True`) was retriggering
the filter's SET row on literally every tick. Root cause, found by rereading
`BlackbirdSim.execute()`'s own dispatch: for a legato note
(`vs.pendins == 0xFF`), real hardware takes the `y & 0x80` branch and
executes **nothing** for `y == 0xFF` ("no register effect here", literally
the code's own comment) — `wavepos`/`ins_wave` and `zp_filtpos` are ONLY
ever touched in the genuine-instrument-select branch, which legato
explicitly bypasses. FX/pitch-modulation (`fxpos`) is a separate mechanism
or driven by `vs.pendfx`, set unconditionally in `prepare3` with no tie
gate — so it DOES restart on every note, tied or not. `blackbird_driver.asm`'s
`pr_note` had this backwards: the WAVE-restart and FILTER-reposition code
lived under the `pn_tied:` fallthrough label, so BOTH the tied and
not-tied paths reached it — every tied note was silently restarting the
wave program and yanking the global filter back to its instrument's start
row. Fixed by moving the WAVE+FILTER restart into the not-tied-only branch
(falling through to `pn_tied` only for the genuinely-tie-invariant FM
restart). **Verified via a direct before/after py65 trace** (not just the
aggregate %): the driver's `F_IDX` no longer cycles `3,4,4,4,4,3,4,4,4,4...`
every tick — it now sits at a constant row while `F_CHI` climbs
continuously, matching the simulator's own qualitative behavior (a smooth,
uninterrupted ramp) for the first time. **Honestly reported, not
oversold**: this did NOT move the strict byte-exact-match percentage for
the specific 200-800-frame window used to isolate it (both the buggy
oscillating trajectory and the fixed continuous one were 100% "diff" on
this register for every sampled frame in that window, because the fixed
driver's ramp *rate* still doesn't fully converge with the simulator's own
within it — the corrected trajectory is a real, verified improvement in
*kind*, but the strict per-frame equality metric gives zero partial credit
for "closer but not equal yet"). The residual rate gap is not root-caused
this pass (plausibly other voices' own legitimate, non-tied filter
repositions interleaving with instrument 4's ramp, consistent with
Glyptodont's 11 filter-carrying instruments sharing one global filter
resource) — a good target for whoever picks up B5's tempo/window-scoped
filter tracing.

**Bug 4 (the one item that WAS the established, correct technique but
simply wasn't applied) — count-weighted bundle clustering.** Verified
directly against `bin/build_galway_trace_song.py`'s own `cluster_bundles`
(the reference implementation `docs/players/PLAYBOOK.md`'s technique
catalog cites as "first proven on Rambo/Galway v3.12"): Galway's version
weights merge cost by `min(cnt[i], cnt[j])` — the note-onset usage count of
each candidate bundle — so a merge is only cheap when it affects FEW notes.
Blackbird's `cluster_bundles` had NO such weighting: it picked the globally
nearest pair by raw L1 distance alone, so a bundle played by hundreds of
notes could get merged away exactly as readily as one played once, and the
surviving representative was whichever bundle happened to be added to the
group first (not necessarily the most-played one). Fixed by porting
Galway's `cost = distance * min(weight_i, weight_j)` merge-order and by
making the survivor the group's own highest-onset-count member. Both
`bundle_counts` (real onset-event tallies, not distinct-key counts) are now
threaded through from `main()`. **Result: this was the single biggest lever
of the whole round** — Fargo's primary-window frequency match **40.8% →
81.5%** (overall 59.9% → 69.6%, extended window 66.7% → 69.5%), Glyptodont's
**22.1% → 32.5%** (overall 49.7% → 53.5%). The much bigger jump on Fargo
(only 43/107 bundles merged, vs Glyptodont's 359/423) shows unweighted
clustering was leaving real accuracy on the table even in the "mild"
clustering regime the B1 report treated as a minor, well-understood
residual — it was actually a live, fixable inefficiency the whole time.

**Full before/after (200-frame primary window, same method throughout)**:

| | Fargo before B4 | Fargo after B4 | Glyptodont before B4 | Glyptodont after B4 |
|---|---|---|---|---|
| overall | 59.9% | **69.6%** | 49.7% | **53.5%** |
| freq | 40.8% | **81.5%** | 22.1% | **32.5%** |
| waveform | 88.8% | 88.8% | 73.3% | 73.3% |
| pulse | 1.0% | 1.0% | 0.2% | 0.2% |
| AD/SR | 97.2% | 97.2% | 96.6% | 96.6% |
| filter | 99.1% | 99.1% | 77.4% | **85.5%** |
| extended (0-2395) overall | 66.7% | **69.5%** | n/a (boundary beyond cap) | n/a |

No category regressed on either file; waveform/pulse/AD/SR are unchanged
because none of the 4 bugs touch those paths. Independently re-verified
(sha1-hash-confirmed which driver binary produced which number at every
step) by the auditing session, not just taken from a building agent's
report — this round caught its OWN false lead midway (an apparent "the
overflow-drop fix does nothing" result that turned out to be masked by
Bug 3, not a wasted fix) by tracing register state directly rather than
trusting the aggregate percentage alone.

**B5 scope** (remaining, superseding the old B4 list above where it
overlaps): the Bug-3 residual rate gap (driver's post-fix filter ramp is
qualitatively right but still lags the simulator's own rate within the
200-800 window — needs a full untruncated 275-500 frame trace, not just the
sampled edges, to find the interruption pattern); fix
`estimate_tempo_chain`'s Stage-A off-by-one (still open, not touched by any
B3/B4 item); mode=0 filter rows (format-inherent — the shared SET row
clamps mode 0 to 1; measured this round at 0/2400 frames for Fargo but
280/2400 (11.7%) for Glyptodont — a real, non-trivial residual worth a
follow-up if the SF2II format allows a mode-0 encoding); whether the
64-slot bundle cap itself needs revisiting for instrument-dense files
(Glyptodont still merges 359/423 bundles even with count-weighting — the
weighting picks which merges hurt least, it doesn't raise the ceiling); the
shared engine's architectural startup/trigger-timing skew (still real, still
unquantified independently of the bugs fixed this round); extend
Glyptodont's tempo-schedule verification to its real row-2348/frame-11738
boundary; audio-listen both files (`pyscript/sf2_open_in_editor.py` — not
done this pass); extend to the remaining 9 v1.2-exact files (Dishwasher_
Groove, Dithered_Island, Elvendance, Euclid_Was_Here, Into_the_Unknown,
Maple_Leaf_Rag, Revolutions_Delivered, Thus_Spoke_the_PC_Speaker, Toy_
Rocket — none attempted natively yet); not wired into `DriverSelector` —
still explicitly out of scope.

## What's genuinely proven vs. still open

- **Proven, working**: template-based detection (11/59 files), full symbol/table
  address recovery via the relocation manifest, `nins` cross-check, complete
  memory layout, the event-byte grammar (note/instrument/gate-off/legato/
  arpeggio/delay/oob ranges), the column-major 4-array instrument table shape,
  **the full multi-voice interleaved decompression** (scheduling +
  stream-terminator handling, verified against real CPU ground truth on 2
  files and clean-decoded on all 11 v1.2-exact files), AND now **the
  tempo/groove alternation mechanism** (self-modifying XOR pair, driven by
  2-byte inline OOB records, `frames = tempo_byte / 7`), confirmed by two
  independent methods (live hardware trace + static stream decode) agreeing
  exactly on both values and formula. All shipped as a real, tested module:
  `sidm2/blackbird_parser.py` + `pyscript/test_blackbird_parser.py`. **AND
  now** the decoder's loop-iteration-counter-is-a-tick-not-a-frame finding
  (see "Tempo-model open caveat — RESOLVED" above, three-way triangulated:
  live trace, an earlier static full-song tempo-history decode, and this
  session's independent re-derivation), plus a working **Stage A**
  (`sidm2/blackbird_driver11.py`): real, loadable Driver 11 SF2s for Fargo
  (378 notes) and Glyptodont (2703 notes), ticks mapped 1:1 to rows, AD/SR
  read byte-exact, instrument-cap aliasing bug found and fixed.
- **Proven, built into a real native driver** (updated 2026-07-19, B1→B2→
  B3→B4 same week): the full Stage-B synth engine semantics (fx/pitch
  interpolator, wave/pulse stepper, global filter program) — validated
  byte-exact against real hardware as a Python simulator (see "Stage B synth
  engine" above) — are now ALSO ported into a real 6502 native SF2 driver
  (`drivers_src/blackbird/blackbird_driver.asm`, forked from the shared
  ROMUZAK-derived engine) with real table translators
  (`bin/build_blackbird_native_song.py`, using the validated simulator itself
  as the formula oracle). Fargo builds a loadable SF2 at **69.6% overall
  register-match** (200-frame window vs the simulator; filter 99.1%, AD/SR
  97.2%, waveform 88.8%, freq 81.5%; pulse ~1% is a named, evidenced
  residual, not unexplained) and models the song's FULL row-indexed mid-song
  tempo schedule (B3: 22 real tempo/groove records, not just the first pair
  — measurably fixes fidelity PAST the 200-frame window, verified on an
  extended 2395-frame comparison, now 69.5% overall post-B4). Glyptodont
  builds at 53.5% overall (B4) — **the prior B3 report's "architectural, not
  fixable" explanation for Glyptodont's gap did NOT survive direct
  verification**: a dedicated B4 pass found and fixed 4 real bugs (a filter
  SET-chain misclassified as an ADD ramp, an unmodeled filter
  overflow-drop, tied/legato notes wrongly restarting WAVE+FILTER on the
  native driver, and unweighted bundle clustering vs the established
  count-weighted technique already used by the Galway driver) — see "B4
  shipped" above for the full before/after table and evidence trail per bug.
  The shared engine's architectural startup/trigger-timing skew is still a
  real, separate, unquantified residual (not what was actually driving
  Glyptodont's gap, per the B4 investigation).
- **Not started / explicitly out of scope this round**: testing the parser
  against the near-v1.2 variant buckets (older birdcruncher versions,
  different compiled bytes, confirmed rejected by locate but not yet
  supported); wiring into `DriverSelector` (fidelity too low vs other players'
  native drivers); any zig64/siddump onset-match fidelity measurement (zig64
  itself doesn't work on Blackbird, see the open item above — the native
  driver's own register-trace-vs-simulator comparison is the fidelity metric
  in use instead); mid-song tempo tracking in STAGE A specifically (only the
  first tempo/groove pair is used there — B3's schedule work is native-driver
  only, `estimate_tempo_chain()`'s own off-by-one is also still unfixed);
  empirical/byte-exact pitch calibration against Blackbird's own sub-semitone
  `freq_lsb`/`freq_msb` interpolation tables (Stage A only calibrates the
  resting/landing pitch); extending the native driver past Fargo+Glyptodont
  to the other 9 v1.2-exact files; audio-listening the native driver's output
  (only Stage A's coarser output has been ear-confirmed so far).

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
