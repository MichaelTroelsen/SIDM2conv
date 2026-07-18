# Blackbird (Linus Åkesson / "lft") — recon started 2026-07-19

**Status: recon only, not yet a supported player.** `bin/LFT/blackbird-1.2/` bundles
the author's own editor + `birdcruncher` exporter, **including full assembly
source** (`Export/source/player.s`, `rplayer.h`) and the **C compressor source**
(`Export/source/cruncher.c`). This is the opposite situation from every other
player in this project: instead of reverse-engineering a black-box binary, we
have the literal ground truth. That makes locate/detection and table layout
**100% solved and verified**; the note-stream **decompression** is understood in
principle (the reference algorithm is in hand) but not yet correctly replaying —
see "Open: decompression" below before spending more time guessing at it.

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

**Why this isn't decoded correctly yet**: the physical compressed stream is a
SINGLE byte sequence, but it interleaves all 3 voices' pieces — `crunch_streams`
calls `crunch_some(voice2)`, then `run_prep1` for voice 2,1,0, then
`crunch_some(voice1)`, then `run_prep2` ×3, then `crunch_some(voice0)`, then
`run_prep3` ×3, repeating until every voice's (fully pre-known, on the encoder
side) note data is exhausted. Each `crunch_some(voiceN)` call only actually
emits bytes if that voice's own `wpos-rpos < 128` (a real ring-buffer-level
gate); each `run_prepN` call reads/advances that voice's own `rpos` into its
own (fully known, for the encoder) note array.

The catch: on the encoder side `ds->rledata` is the COMPLETE note array from
the start, so call order between `crunch_some` and `run_prepN` in the same loop
iteration is irrelevant to correctness (both just walk a pre-existing array at
different rates). **On the decoder side it's the opposite** — a voice's decoded
bytes only exist once THAT voice's own `crunch_some`-equivalent has run, so the
exact interleaving order between "reveal voice N's next physical piece" and
"let voice N's prep1/2/3 peek at what's been revealed so far" matters a lot,
and isn't simply invertible by reading the encoder's loop body literally. Two
reorderings were tried this session (mirroring the exact encoder call order,
then moving all 3 voices' emits before any prepN calls) — the first crashes on
an unconsumed arpeggio byte at frame 0 (a voice's own prep1 ran before its own
first physical piece existed), the second gets further but crashes on an
out-of-range back-reference (a voice's own consumption outpaced what had
actually been revealed). **Neither is correct; don't trust either output.**

**Recommended next approach, NOT attempted this session**: rather than keep
guessing at the interleaving order from the encoder's C source alone, either
(a) get a real 6502 emulator (py65, or `mcp__mcp-c64__run_program`) to actually
run a Blackbird-compiled SID and dump the DECOMPRESSED per-voice ring buffers
live, byte by byte, as ground truth to diff a Python port against — this
sidesteps the ordering ambiguity entirely since the real hardware defines the
one true order; or (b) very carefully re-trace `player.s`'s ACTUAL frame-by-frame
`playroutine` DISPATCH (the `zp_master` cycling through `unpackvoice`/`everyframe`
slots) rather than `cruncher.c`'s simulation of it, since the compressor's loop
body is a simulation equivalence, not a literal 1:1 mirror of the real per-frame
call sequence (confirmed: `playroutine` dispatches to EITHER an unpack call OR
a prepareN/execute/everyframe call per real invocation, never both — the
cruncher's single "while" iteration abstracts over what is really several
separate real-time dispatcher calls). Path (a) is more reliable and matches
this project's own standard practice (never trust a static-analysis-only model
without a real trace) — see `mcp__sidm2-siddump__trace_sid` / `run_program`.

## What's genuinely proven vs. still open

- **Proven, working**: template-based detection (11/59 files), full symbol/table
  address recovery via the relocation manifest, `nins` cross-check, complete
  memory layout, the event-byte grammar (note/instrument/gate-off/legato/
  arpeggio/delay/oob ranges), the column-major 4-array instrument table shape.
- **Understood but unverified**: the tempo/pipeline timing model (does it define
  a tick grid, or is it pure pipeline latency with delay-bytes as literal frame
  counts?); the exact LZ back-reference/transpose math (derived from the
  encoder's own emit code, high confidence, but never round-tripped against a
  real decode).
- **Not working**: the multi-voice interleaved decompression order. Two
  attempts both crash; don't reuse either without fixing the ordering first.
- **Not started**: everything past Stage-A decode (Driver 11 transpile, native
  Stage B).

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
