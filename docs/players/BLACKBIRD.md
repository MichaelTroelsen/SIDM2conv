# Blackbird (Linus Åkesson / "lft") — recon started 2026-07-19

**Status (updated 2026-07-21, post-B22): decompression, tempo model, and
Stage A (Driver 11 transpile) all SOLVED and shipped for all 11
v1.2-exact-bucket files (`sidm2/blackbird_parser.py`,
`sidm2/blackbird_driver11.py`). Stage B's synth engine (arpeggio/wave/
pulse/filter) is RE'd and validated byte-exact against real hardware, and
built into a real native 6502 driver
(`drivers_src/blackbird/blackbird_driver.asm` +
`bin/build_blackbird_native_song.py`) that now builds a working SF2 for
**all 11 of the 11 v1.2-exact-bucket files** (B15, a coverage extension —
see "B15 shipped" below for the full per-file table), now ranging
97.4%-99.8% overall post-B22 (mean ~98%, up from B17's 93.9%-98.9%/~97% —
B21 was a Fargo-only fix, B22 fixed the filter rapid-restart freeze
(Revolutions_Delivered) plus improved two more files; see "B21 shipped"
and "B22 shipped" below). Two files needed B6's adaptive multi-part splitting automatically
(Dithered_Island: 2 parts, Into_the_Unknown: 3 parts; Fargo also now
correctly splits into 2, since B14 fixed a genuine 35-instrument overflow
that used to silently corrupt it instead of triggering the split). B11-B14
were real bug fixes found via live hardware/CPU tracing (fx-on-rest
commit timing, instrument-select restart timing, a translator bug that
misread a real "gate-off before note" Blackbird grammar pattern as a
restart, and the instrument-index overflow just mentioned) — see their
own dated sections below for the full trail, including two mid-investigation
wrong turns that were caught and corrected rather than shipped
(deliberately left visible as honest history). B16 ported a real, verified,
previously-entirely-missing engine feature (player.s's `ins_restart`/
`ins_restart2` threshold-gated hard-retrigger) with zero regression
anywhere in the corpus — but it turned out NOT to explain Fargo's own
71.1% pulse residual. B17 then found and fixed a broad corpus-wide
missing-VWI-restart bug (instrument-select-without-note rows), which
recovered most of the corpus but only partially fixed Fargo itself
(pulse 71.1%→76.1%, not 100%) — B19/B20 investigated further but reverted
both attempts (see their own section below for that honest negative
result). B21 found the REAL remaining Fargo cause: Fargo now scores
99.8%/pulse 100.0%, the best file in the corpus. B22 (right after, same
day) picked up B19/B20's other open thread and found TWO bugs behind the
filter rapid-restart freeze — a row0 SET/ADD misclassification (B19/B20's
own diagnosed fix, reapplied) AND a voice-processing-order mismatch for
filter arbitration when two voices contend for it in the same tick — both
together: Revolutions_Delivered's filter jumped 81.1%→97.1%, above its
ORIGINAL B17 baseline, not just restored to it. Only Fargo (pre-B14) and
Glyptodont (post-B13) have been individually root-caused in depth; the
other 9 files newly covered by B15 are a baseline, not yet individually
investigated. Glyptodont is the only file audio-listened so far (real SID
Factory II, user: "sounds really close, something with the perc or drums"
— tracks the waveform/filter residuals, which are the two categories still
short of 100%). Not yet wired into the conversion pipeline (no
`DriverSelector`/`conversion_pipeline` registration) for any file — all 11
native builds are deliberately out of the production pipeline until
fidelity is judged sufficient. `bin/LFT/blackbird-1.2/` bundles the
author's own editor + `birdcruncher` exporter, **including full assembly
source** (`Export/source/player.s`, `rplayer.h`) and the **C compressor source**
(`Export/source/cruncher.c`). This is the opposite situation from every other
player in this project: instead of reverse-engineering a black-box binary, we
have the literal ground truth. That makes locate/detection, table layout,
the note-stream decompression, AND now the tick/tempo model **100% solved,
independently verified, and committed as real tested modules** for all 11
v1.2-exact-bucket files (see "Compression — SOLVED", "Parser module shipped",
"Tempo-model open caveat — RESOLVED", and "Stage A shipped" below). A native
Stage-B driver now exists and builds real SF2s for **all 11** of those 11
files (see "Stage B1" through "B15" sections below); no
`DriverSelector.PLAYER_REGISTRY` entry yet (intentionally, fidelity is
still well below other players' native drivers) — see "What's genuinely
proven vs. still open".

## Corpus scope

`SID/LFT/` has 59 files by Linus Åkesson. Splitting by how closely each file's
compiled play-routine bytes match the bundled v1.2 template (`docs` grouping
below) — this is NOT the same split as the SID inventory's player-id tag, which
only knows "Blackbird/LFT" vs generic "LFT" vs "UNIDENTIFIED" and doesn't
distinguish tool *versions*:

| bucket | count | example files | meaning |
|---|---|---|---|
| **v1.2 exact match** | 11 | Fargo, Glyptodont, Dishwasher_Groove, Dithered_Island, Elvendance, Euclid_Was_Here, Into_the_Unknown, Maple_Leaf_Rag, Revolutions_Delivered, Thus_Spoke_the_PC_Speaker, Toy_Rocket | byte-identical to `player.h`'s `seg_play_data` except at the documented relocation offsets — **locate is fully solved for these** |
| **v1.2 + REPEAT=1** ("variant A", RESOLVED 2026-07-22) | 5 | Crank_Crank_Airwolf, Fugue_on_a_Theme_by_D_M_Hanlon, Quintessence, To_Die_For_II, Trinket | **NOT a different tool version** — the SAME v1.2 source, compiled with player.s's `#if REPEAT` flag (loop-on-end support) — see "REPEAT=1 locate support" below. **Locate, `decode_streams`, Stage A, AND a Stage B beachhead all shipped, same day**: all 5 files decode cleanly, build a Driver 11 IR, AND build a real playable native-driver SF2 (66-98% first-attempt fidelity, mean ~76%) — fidelity refinement (the B2-B22-style rounds) not started |
| near-v1.2 variant A' | 1 | Crank_Crank_Revolution | close to the REPEAT=1 bucket but not identical — has its own additional differences beyond REPEAT=1, not yet investigated |
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

## REPEAT=1 locate support shipped (2026-07-22): "variant A" isn't a different tool version — it's `#if REPEAT`

Picked up the near-v1.2 "variant A" bucket (5 files), previously characterized as "likely birdcruncher 1.1" purely from a raw 225-byte position-locked diff against the v1.2 template. That raw diff count was misleading: it's a cascade from ONE early size change, not 225 independent differences.

**Root cause, fully confirmed**: `player.s` guards 4 code regions behind `#if REPEAT` (loop-on-end/repeat support): a segment-name-only choice at line 49 (`seg_rplay` vs `seg_play`, no byte content difference), a real ~26-byte EOS loop-rewind block at lines 412-426 (`lda zp_pendoob; and #1; bne norepeat; ldx zp_bufs+14; stx v_trwpos+14; ...`), a tiny ~2-byte swap at lines 612-618 (`clc; adc (zp_inptr),y; tax` vs `lax (zp_inptr),y`), and another segment-name-only choice at line 721 (`seg_rinit` vs `seg_init`, again no byte difference). `player.h`'s shipped `seg_play_data` was compiled with REPEAT=0 (confirmed: it has none of these blocks). Variant A is the SAME v1.2 source, compiled with REPEAT=1.

**Method**: sequence-aligning (`difflib.SequenceMatcher`, not position-locked comparison) `player.h`'s own template against a real variant-A file's raw bytes collapses the 225 raw diffs down to exactly: one 26-byte insertion at v1.2 offset 468, one 4-byte insertion (net +2) at offset 691, one 27-byte deletion at offset 763 (the `.dsb (playorg+$400-207-*), $ee` page-alignment padding automatically shrinks to compensate — `freq_msb` lands at the identical playorg-relative offset either way, confirmed: byte-for-byte alignment resumes exactly at old-offset 817 on both sides), and two single-byte replacements (offsets 446, 615) that are relative BRANCH-DISTANCE operands whose target sits on the far side of the 25-byte insertion — a different but still build-wide FIXED constant, not a per-tune address. Every OTHER apparent diff in the raw comparison is an ordinary per-tune relocated address landing at a shifted offset.

Cross-referencing the SAME insertion region across two files with different `playorg` (Crank_Crank_Airwolf, $5000; Fugue_on_a_Theme_by_D_M_Hanlon, $1000) found only 3 bytes differing between them inside the 26-byte insert — all 3 the high byte of a `STX $xxxx` operand — and `observed - playorg` is IDENTICAL (765, 758, 751) on both files: three NEW relocatable `seg_play + N` positions for `stx v_trwpos+14` / `+7` / `+0`, the same style of entry `player.h`'s own manifest already uses elsewhere.

**Shipped**: `sidm2/blackbird_parser.py`'s `_templates_repeat1()` builds the REPEAT=1 template + relocation manifest by transforming `_templates()`'s own v1.2 data with this fixed structural diff (hardcoded insert bytes + branch-distance bytes, all derived and cross-validated as above, not guessed). `locate_blackbird` tries the v1.2 template first, falls back to REPEAT=1, and tags the result's new `.variant` field (`'v1.2'` or `'v1.2-repeat'`). `_extract_symbols` gained a `variant` parameter shifting the 5 table-address offsets (ins_ad/ins_sr/ins_wave/ins_filt/fx_start — the only 5 of the 10 tracked symbols that sit between the two REPEAT insertions) by +25 for the REPEAT=1 case.

**Result**: all 5 variant-A files locate cleanly with `variant='v1.2-repeat'`, `nins_consistent=True` (the 4-evenly-spaced-instrument-table self-check passes — a strong correctness signal, not just "didn't crash"), and `init_template_mismatch=False`. Correctly does NOT match Fargo/Glyptodont (still need the v1.2 template) or Crank_Crank_Revolution (closer to variant A than to v1.2, but has its own additional differences beyond REPEAT=1 — not yet investigated). `pyscript/test_blackbird_parser.py` gained `test_locates_v12_repeat_bucket` (positive test) and `NEAR_V12_VARIANTS`/`test_rejects_near_v12_variants` was narrowed to just Crank_Crank_Revolution + the older variant-B bucket (still unsupported).

**`decode_streams` IndexError crash: ROOT-CAUSED AND FIXED (2026-07-22, same-day follow-up round)**. The earlier py65-based "voice1 refills three times in a row" finding (previous paragraph, superseded) turned out to be a red herring: RetroDebugger came back up this round (see below) and gave clean, direct ground truth that FLATLY CONTRADICTS it — the real priming + rotation order is exactly `voice1, voice0, voice2, voice1, voice0, voice2, ...`, byte-for-byte matching `decode_streams`' own existing assumption. Verified over 6 full pieces (ctrl byte value AND physical stream pointer position matched real hardware exactly at every step, confirmed live via `retro_cpu_status`/`retro_memory_read`). The `MTEngine` crash dump from the prior round was a genuinely stuck zombie process (`RetroDebugger-notsigned.exe`, matching PID) still holding the MCP server's connection; `taskkill`-ing it (then reconnecting via `/mcp`) fixed RetroDebugger for the rest of the session — it was never actually broken, just wedged.

**Real root cause**: the crash is a COPY-op source-index formula bug, specific to REPEAT=1 builds. `player.s`'s REPEAT-guarded "tiny ~2-byte swap" (line 612-618, `clc; adc (zp_inptr),y; tax` vs `lax (zp_inptr),y`) was first characterized during the locate work as a same-length structural no-op — **that characterization was wrong**. Disassembling both variants side by side and single-stepping live (RetroDebugger, `retro_cpu_status` reading `X` directly at the post-add `LDA buf,X`) proved the two instruction sequences are NOT semantically equivalent:
- **v1.2 (REPEAT=0)**: `LAX (zp_inptr),y` loads the offset byte straight into `X`, discarding whatever was in `A`. Net effect: `src = offset` (when `offset ≤ L`).
- **v1.2-repeat (REPEAT=1)**: `CLC; ADC (zp_inptr),y; TAX` *adds* the offset byte onto the running `(count + L)` sum already in `A`. Net effect: `src = (L + count + offset) & 0xff` — a completely different formula.

`decode_streams`' old single formula (`dist = (L-offset)&0xff; src = L-dist`) only matches the v1.2 case; for REPEAT=1 it produced negative Python indices (e.g. `src=-10` for the crashing piece, confirmed live: `L=9`, `offset=0xf6=246` → real hardware computes `X=2`, model computed `src=-10`).

A second, related fix was needed: REPEAT=1 copy ops can legitimately reference **not-yet-written buffer territory** as a deliberate zero-fill trick (a `transp2=0` piece reading genuinely-zero, cold RAM at a real per-voice 256-byte output buffer — confirmed live: `L=101`, computed `src=211` on BOTH real hardware and the formula, and the real memory at that buffer offset really was `0x00 0x00 0x00...`, not garbage). `_emit_piece`'s copy loop now ring-reads (`_ring_read`, wraps at 256, returns 0 for a slot never yet written) for the REPEAT=1 variant only; v1.2 files are byte-for-byte untouched (same linear-array code path as before).

**Shipped**: `_emit_piece`/`decode_streams`/`BlackbirdModule.decode`/`decode_file` all gained a `variant` parameter (threaded from `BlackbirdLayout.variant`); the REPEAT=1 formula + ring-read only activate for `variant='v1.2-repeat'`. **Zero regression**: all 11 v1.2-exact files decode byte-identically (verified — same `real_lengths` as before the change); `pyscript/test_blackbird_parser.py` + `test_py65_illegal_opcodes.py` 18/18 pass.

**A second bug, initially misdiagnosed as REPEAT=1-specific, was found and fixed the same round**: after the copy-formula fix, all 5 files decoded MUCH further (200-3,000+ bytes vs. crashing at byte 9) but still hit a `prepare3` "out-of-grammar byte" error. Three live-verified checks (call7 `L=9`, call42 `L=101`, call82 `L=208` — reading the real per-voice output buffer directly via RetroDebugger) proved the DECODED CONTENT was byte-for-byte correct at every one of those points; the bug was never in decompression. The real fix came from comparing `_run_prep1/2/3` against `bin/blackbird_everyframe_sim.py`'s `BlackbirdSim.prepare1/2/3` — a SEPARATE, independent implementation already validated 100% against real hardware SID-register traces (14,673/14,673 + 18,332/18,332 writes, Fargo/Glyptodont). That comparison found THREE real discrepancies in `_run_prep1/2/3` (confirmed via live disassembly too — `$5043`'s real `CMP #$B8` boundary matches `BlackbirdSim`, not the old `blackbird_parser.py` code):
- `prepare1`'s fx-select threshold was `>= 0xc9`, should be `>= 0xc8`.
- `prepare2`'s instrument-select upper bound was `<= 0xb2`, should be `<= 0xb7`.
- `prepare3` had an artificial `0xb8 <= b <= 0xc7` range restriction (raising `ValueError` otherwise) that **does not exist in real hardware at all** — `BlackbirdSim.prepare3` accepts ANY byte `>= 0x80` unconditionally as a delay/timer code (`0xf0 | b`), no grammar validation whatsoever. The restriction only ever "worked" because none of the 11 v1.2-exact files' compressed data happened to trigger it — not because it reflected a real hardware constraint. **This was the actual root cause of every "out-of-grammar" crash on all 5 REPEAT=1 files.**

**Shipped**: all three boundaries corrected in `sidm2/blackbird_parser.py` (unconditionally, not variant-gated — real hardware behaves this way for v1.2 too, these were pre-existing bugs that 11 files' data simply never exposed). `_run_prep3`'s `vidx` parameter (only used by the removed error message) dropped from its signature; two other call sites duplicating this decode loop (`sidm2/blackbird_driver11.py` Stage A, `bin/blackbird_everyframe_sim.py`) updated to match.

**Result**: all 5 REPEAT=1 files now decode cleanly to a genuine `frozen=True` end-of-stream — zero crashes (`Crank_Crank_Airwolf` 558 frames/582 pieces, `Fugue_on_a_Theme_by_D_M_Hanlon` 1109/731, `Quintessence` 2575/1741, `To_Die_For_II` 3273/822, `Trinket` 1808/788). Event-type distributions for all 15 voices look like genuine music (notes dominant, sensible instrument/arp/gate-off/delay proportions), matching the profile validated for the original v1.2 bucket — not noise. **Zero regression**: all 11 v1.2-exact files decode with `real_lengths` byte-identical to before this round's changes; Stage A (`blackbird_driver11.py`) smoke-tested on Fargo, builds cleanly. Full project test suite (`pytest pyscript/`, 1,588 tests) passes: 1579 passed, 7 skipped, 2 xfailed, 0 failures.

## Stage A shipped for the REPEAT=1 bucket (same day, 2026-07-22)

`build_blackbird_driver11_song`'s main decode path already worked once `decode_streams` did (it threads `variant` through `decode_file` automatically). But `blackbird_driver11.py`'s OWN separate tempo-recovery pass (`extract_tempo_pairs`, which re-runs `_Reader`/`_Voice`/`_run_prep1-3`/`_emit_piece` independently to recover the tempo/groove OOB byte pairs `decode_streams` itself discards) had no `variant` parameter and always used the v1.2 copy-op formula — fixed by threading `variant` through `extract_tempo_pairs` → `estimate_tempo_chain` → `build_blackbird_driver11_song`, same pattern as the parser module.

**Result**: all 5 REPEAT=1 files build a Driver 11 `GalwayDriver11Song` IR cleanly (`Crank_Crank_Airwolf` 400/245/441 rows, `Fugue_on_a_Theme_by_D_M_Hanlon` 915/872/1094, `Quintessence` 2301/2644/2477, `To_Die_For_II` 2370/2318/3255, `Trinket` 1340/1513/897 — 5-20 instruments each, sane tempo chains). **Zero regression**: the 11 v1.2-exact files build identically (variant defaults to `'v1.2'`, a no-op for them). New tests: `TestBlackbirdRepeatSweep` (`pyscript/test_blackbird_parser.py`) — clean-decode + Stage-A-builds-without-raising coverage for all 5 files. Full suite: 1581 passed.

Matches this project's existing convention for the 11-file bucket: Stage A is a tested, working library capability, not wired into a batch SF2-emission pipeline or `driver_selector.py`'s `PLAYER_REGISTRY` (intentionally — no native Stage B driver exists yet for either bucket).

## Stage B beachhead shipped for the REPEAT=1 bucket (same day, 2026-07-22): all 5 files build a real, playable SF2

Picked up Stage B next. `bin/build_blackbird_native_song.py`'s `main()` called `decode_streams`/`extract_tempo_pairs` directly (not through `decode_file`) with no `variant` — fixed both call sites, plus the SAME gap in `bin/blackbird_everyframe_sim.py`'s own independent `find_tempo_records`/`run_sim` decode loops (grep for `_emit_piece`/`decode_streams` call sites before assuming a decode-level variant fix is complete — this is the third module found needing it today, after `blackbird_parser.py` itself and `blackbird_driver11.py`).

**A second, real bug found on the first build attempt**: `Crank_Crank_Airwolf` crashed in `BlackbirdSim.execute()` with `IndexError: list index out of range` on `self.ins_filt[y-1]` — the decoded note stream genuinely references instrument #7 (byte `0x89`, a valid in-grammar instrument-select) while only 5 instrument slots were located (`lay.nins=5`, confirmed correct — `nins_consistent` still holds, the 4 tables really are evenly 5-spaced in this binary). This is the EXACT SAME bug class already found and fixed for `freq_lsb`/`freq_msb` earlier in this same file (see that fix's own comment, dated from the original Glyptodont investigation): a Python list truncated to the table's "nominal" length raises where real 6502 indexed addressing (`lda ins_filt,y`) has no bounds check at all — it just reads whatever byte physically follows the table. Converted `ins_ad`/`ins_sr`/`ins_wave`/`ins_filt`/`fx_start` from fixed-length lists (built once in `__init__`) to raw-memory-read methods (`self.rb(lay.X + idx)`, matching the existing `filttable`/`fxtable`/`wavetable`/`freq_lsb`/`freq_msb` pattern exactly) — mathematically identical to the old lists for any in-range index (both just read `d[(addr-la)+idx]`), so provably zero-behavior-change for any file where the index never exceeds the table (i.e. every one of the 11 v1.2-exact files, confirmed by rebuilding all 11 — Fargo 99.7% overall, matching the documented 99.8% almost exactly; the other 10 land 94-97.3% on this build script's own quick capped-window self-check, consistent with its normal reporting).

**Result**: all 5 REPEAT=1 files now build a real, `sf2_viewer_core`-parseable SF2 on the first attempt — a genuine Stage B beachhead, comparable to "B1" in the original 11-file arc:

| File | Overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| Crank_Crank_Airwolf | 66.8% | 53.5% | 62.3% | 66.2% | 77.1% | 75.7% |
| Fugue_on_a_Theme_by_D_M_Hanlon | 86.9% | 94.6% | 65.6% | 74.4% | 93.8% | 100.0% |
| Quintessence | 97.6% | 100.0% | 96.0% | 100.0% | 91.9% | 100.0% |
| To_Die_For_II | 62.1% | 62.9% | 56.5% | 64.6% | 60.4% | 64.1% |
| Trinket | 68.0% | 45.1% | 56.3% | 74.6% | 68.7% | 100.0% |

(mean ~76% overall; figures are this build script's own capped 3000-frame self-check, same methodology as always — not yet the fuller corpus-validation pass the 11-file bucket's headline numbers come from). **Zero regression**: full pytest suite 1581 passed; `drivers_src/blackbird/*.inc` left matching Fargo's own build per established convention.

## First fidelity-refinement round (same day, 2026-07-22): one filter bug root-caused, found to be likely audibly inert

Picked `To_Die_For_II` (lowest overall, 62.1%) to investigate first. Ruled out the pervasive "2-frame-early SR/ctrl commit" pattern visible in its per-register diagnostic (`BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG` env vars) as the dominant cause: the SAME pattern is present in `Fargo` (already at 99.7% overall, considered production-quality) at the exact same magnitude — it's a known, already-tolerated residual for the whole native driver, not something new here.

**The real, precisely root-caused bug**: `$D418` (master volume/filter-mode register) goes permanently wrong at frame 992 (`sim=$0f` vs `drv=$1f`, i.e. bit4 stuck set) and stays wrong for the rest of the comparison window. Traced back through the filter-owner chain (`unroll_filter`'s translated rows for filter positions 4/11/18/22/26, all instrument-triggered): position 18's row0 is a genuine SET row with `filttable(18)=0x0f` (SID filter mode 0 — no passband type selected). `_filter_set_row`'s own long-standing code comment already flagged this exact case: `mode & 0x07 == 0` gets clamped to `mode=1` because **the native driver's row-format dispatch cannot route a byte to the SET path with mode=0 at all** — `fp_dec: cmp #$90; bcs fp_set` requires byte0≥$90, but encoding mode=0 needs byte0 in `[$80,$8f]`, which is *already* the ADD row's own encoding space (`fp_dec`'s `and #$0f` branch, used for real per-frame cutoff deltas) — a genuine space conflict in the driver's row format, not a translator oversight. Once corrupted to mode=1, the wrong value propagates through every subsequent ADD-only row/filter-owner switch (positions 4/11/26 are ALL classified ADD, i.e. mode-preserving, never correcting it) until the next differently-valued genuine SET row happens to overwrite it.

**Audibility check (before considering a driver-ASM patch)**: `$D417` (the filter voice-routing register) is `$00` — zero voices routed to the filter — for every filter program whose `$D418` shows `mode=0` in this file. This means the corrupted mode bit likely has **no audible effect**: with no voice routed to the filter, which passband type is selected doesn't matter. This matches the original code comment's own (previously untested) guess ("audibly close to leaving the passband inert"). Register-level accuracy is real and measurable, but a driver-ASM fix was judged not worth the regression risk: any change to `fp_dec`'s dispatch threshold or the ADD row's encoding space touches the SHARED driver used by all 16 files across both buckets (11 v1.2-exact + 5 REPEAT=1), for a benefit that's likely inaudible. **Deliberately NOT fixed** — documented here so it isn't re-investigated from scratch, and left as a candidate if a future file's data makes it matter more (e.g. mode=0 co-occurring with actual voice routing).

**Also found and confirmed NOT the dominant issue**: filter isn't even `To_Die_For_II`'s worst category (`freq`=62.9%, `waveform`=56.5%, `adsr`=60.4%, `pulse`=64.6% are all comparable or worse than `filter`=64.1%) — meaning multiple SEPARATE bugs remain across other categories, none investigated yet this round. `Crank_Crank_Airwolf` and `Trinket` have ZERO filter-carrying instruments at all (confirmed via their `ins_filt` tables), so their own low scores (66.8%/68.0%) come from something else entirely, not this bug.

**Not done yet**: fidelity refinement for this bucket remains largely open — comparable scope to the original B2-B22 rounds (many individual bug-hunt-and-fix cycles took the 11-file bucket from its own first build to 97-99%). The freq/waveform/adsr/pulse categories (bigger contributors than filter for `To_Die_For_II`) haven't been investigated at all; Crank_Crank_Airwolf/Trinket's own low scores are unexplained. `Crank_Crank_Revolution` ("variant A'") still unlocated. The older "variant B" bucket (10 files) still untouched. Nobody has audio-listened to any REPEAT=1 file yet (same as the 11-file bucket's own long-standing open item).

## MAJOR finding (same day, 2026-07-22): most of the bucket's "low fidelity" is a measurement-window artifact, not driver bugs — confirmed via the existing binned diagnostic, NOT an exact loop period

Went looking at `freq` next (the most universally-low category, 45-63% across 4 of the 5 files) since it's the biggest single contributor. Picked `Crank_Crank_Airwolf` (worst freq score, 53.5%, and no filter confound since it has zero filter-carrying instruments).

**First attempt — WRONG, corrected same round**: hypothesized the compiled driver loops back to the start of its own sequence (ordinary Driver11/SF2 playback once a track runs out of row data) while the validated simulator has no REPEAT loop-rewind modelling at all (`execute()` explicitly no-ops the `eos` OOB bit: `pass  # eos -- not modelled`) — so comparing driver-replaying-the-intro against simulator-sitting-silent was never meaningful past that point. Found what looked like confirmation: `Crank_Crank_Airwolf`'s own `$D400` trace matched itself at a 984-frame offset (`drv[200:210] == drv[1184:1194]`), and capping the comparison to 984f gave 96.6%/freq=100%. **This "period=984" claim was WRONG** — built a more rigorous self-comparison check (200-frame probe instead of 10, checked all 3 voice registers, rejected flat/held-note anchor windows) specifically to verify it, and the "loop" evaporated: `drv[200:400)` does NOT match `drv[1184:1384)` on any register once compared over a realistic window length. The original 10-frame match was pure coincidence (a locally-recurring value with no actual surrounding repeat) — **a textbook false positive**, caught by disciplined re-verification rather than accepted on a first "confirmed by re-measurement" result. The over-engineered self-comparison function (`find_self_loop_period`, briefly added to `bin/build_blackbird_native_song.py`) was written, tested, found unreliable even after hardening, and REMOVED again in the same round — not shipped.

**What IS robustly confirmed** (via `BB_DIAG_BIN`, the project's own EXISTING, already-tested binned-diagnostic env var — not a new, unverified technique): fidelity genuinely stays high (near "primary window" levels) for the first several hundred to ~1000-1500 real frames on 4 of the 5 files, then degrades — sometimes catastrophically — over the remainder of the 3000-frame comparison window:
- `Crank_Crank_Airwolf`: freq=100% through frame 1000, then 81%→25%→9%→5% across the remaining 2000f.
- `To_Die_For_II`: high through ~1000 (freq 100%→93%), then collapses to near-0% by frame 2500-3000 (adsr hits literally 0.0% in the final 500f bin).
- `Trinket`: high through ~500-1000, then freq specifically collapses (100%→59%→5%→3%→3%).
- `Fugue_on_a_Theme_by_D_M_Hanlon`: a DIFFERENT shape — `freq` stays high the ENTIRE 3000f (94-100% throughout, never collapses), but `waveform` specifically degrades steadily over time (97%→85%→60%→58%→33%) while other categories stay reasonable. Not the same failure mode as the other 3.
- `Quintessence`: stays HIGH THE ENTIRE 3000-frame window, no degradation pattern at all (freq=100% in every single 500f bin) — its already-reported 97.6% WEIGHTED AVERAGE is genuinely accurate, not an artifact.

**The underlying MECHANISM for the degradation (loop-back, something REPEAT-specific, or otherwise) is still NOT confirmed** — the loop-back hypothesis that motivated this investigation turned out to be unverified; only the SYMPTOM (progressive, sometimes catastrophic degradation starting several hundred to ~1500 frames in, on 4 of 5 files, in a shape that varies by file) is now solidly established. A related, still-unexplained puzzle: the full-song simulator's own `row_frame` row→real-frame mapping (`run_full_song_sim()`) only reached row 307 of `Crank_Crank_Airwolf`'s 441-row span within its entire 20,000-frame budget, with per-row real-frame gaps growing dramatically over time (last 5 tracked rows span ~150+ frames each, vs. ~8 expected) — this is a real, separate anomaly in the SIMULATOR's own bookkeeping, not yet root-caused, and may or may not be related to the degradation pattern above.

**Practical implication for anyone picking this up next**: treat every currently-reported "full-part"/"steady-state"/"WEIGHTED AVERAGE" fidelity number for this bucket as a lower bound for `Crank_Crank_Airwolf`/`To_Die_For_II`/`Trinket` specifically (their real, sustained fidelity is genuinely close to their "primary window" figures for however long the degradation takes to kick in — several hundred to ~1500 frames, file-dependent) — but treat `Quintessence`'s number as already accurate, and `Fugue`'s `waveform` score as a real, separate, still-open issue rather than a measurement artifact. **Do not trust a short (~10-50 frame) self-comparison match as proof of an exact loop period without extending the probe and checking multiple registers** — that specific mistake cost real time this round and is exactly the kind of thing that looks confirmed on a first pass.

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

## B5 shipped: 3 more real bugs (2 pulse, 1 root-causing B4's flagged residual)

User listened to `Glyptodont_native.sf2` in real SID Factory II after B4 and
gave direct feedback: "we are getting closer but still a lot missing in
fidelity" — then explicitly chose "keep bug-hunting on Glyptodont as-is" over
part-splitting (the established fix for the 64-slot bundle cap) when asked.
This round honored that choice — no part-splitting attempted.

**Bug 1 — pulse translation conflated "no write" with "write zero"**
(`bin/build_blackbird_native_song.py`'s `unroll_wave_pulse`): a throwaway
`BlackbirdSim` used to unroll a program starts with `regs=[0]*25`, so an
instrument whose wave program never sets the pulse bit (real hardware never
*writes* `$D402/3` for it — the register just holds whatever the LAST
pulse-writing instrument left there) got translated as an explicit "set
pulse width to $000, hold ~250 frames" program. Since `pn_note`
unconditionally restarts a note's pulse program on every trigger, this
stomped a real prior pulse value back to hard 0 on every note using a
flat-pulse instrument — repeated across Glyptodont's 2703 notes. Confirmed
via a live py65 trace: the simulator held a persisted nonzero value across a
whole ~249-frame note while the driver held 0. Fixed by tracking whether
`everyframe()` genuinely wrote regs 2/3 during the unroll; if never, emit a
bare `$7F` freeze-only program so the note-trigger restart is a true no-op,
matching real hardware's "leave it alone" behavior.

**Bug 2 — `$D403` write masked to a nibble** (`blackbird_driver.asm`'s
`pl_wr`): real hardware writes the SAME full byte to both `$D402` and
`$D403` (`BlackbirdSim.everyframe()`'s two `self.w()` calls use the identical
`pulse_byte`). The shared engine's `pl_wr` instead wrote only `VPHI`'s low
nibble to `$D403` — an exact-byte mismatch even on correctly-triggered
content. Fixed to write the same value to both.

**Bug 3 — filter overflow check used the wrong bias, root-causing B4's
flagged "ramp rate doesn't converge" residual**: B4's overflow-drop fix
tested signed overflow on `F_CHI` directly, but real hardware's `m_cutoff`
is `$D416 XOR $80` (a bias-128 trick centering the register's unsigned 0-255
range so a signed-overflow test correctly fires only at the genuine wrap).
Testing on the raw byte instead falsely triggered at the `$7F`/`$80`
midpoint — a live trace on Glyptodont's tied voice2/instrument4 run (the
same run B4's Bug 3 targeted) showed the simulator's cutoff climbing
smoothly `$7f→$84→$89→…→$ff` while the driver froze dead at `$7f` for ~65
frames. Fixed by reproducing the bias-128 trick (`eor #$80` before the add,
`eor #$80` back after).

**Verified numbers** (independently re-run by the calling session, matching
exactly): Fargo's PRIMARY 200-frame window is unchanged at 69.6% (correct —
none of these bugs are exercised in that short a window), but the EXTENDED
2395-frame window (which DOES exercise sustained pulse content) improved
overall=69.5%→**72.5%**, pulse=4.5%→**16.8%**, and its POST-CHANGE segment
(1895-2395) improved pulse=14.5%→**66.7%** — the first-ever run with any
byte-for-byte-identical frames (2/2395, previously always 0). Glyptodont's
PRIMARY window: pulse 0.2%→0.3% (within noise, that window is dominated by
an unfixable frame-0-2 uninitialized-memory transient); its EXTENDED
0-3000-frame window: overall 50.15%→**54.10%**, pulse 3.14%→**17.83%**
(5.7×), filter 90.33%→**92.98%** — freq/waveform/adsr byte-for-byte
unchanged, confirming no regression from these fixes. No category regressed
on either file. `pyscript/test_blackbird_parser.py` still 9/9.

**Priority-3 frequency spot-check — no hidden bug found**: only 3 of
Glyptodont's 64 surviving bundles are genuinely unclustered singletons (423
raw → 64 slots, 359 merged); for the most-played unclustered bundle, a
shift-alignment sweep found a constant ~2-frame skew (k=-2 gives 78.2% match
vs 15.2% at zero-shift) — consistent with the already-named 1-frame FM-lag +
~3-frame startup-pipeline residuals, not a new bug. Bundle clustering
remains the dominant frequency/pulse residual for Glyptodont specifically,
and is explicitly out of scope per the user's own choice this round.

**B6 scope** (remaining): the ~2-3 frame architectural startup/trigger-
timing skew (reconfirmed by this round's shift-alignment checks, still
unfixed — would need a cross-player timing-model change, high risk/reward
unclear); `estimate_tempo_chain`'s Stage-A off-by-one (still untouched);
mode=0 filter rows (still untouched); the 64-slot bundle cap itself (still
the dominant Glyptodont residual, part-splitting remains the known fix,
deferred by explicit user choice); extend Glyptodont's tempo-schedule
verification past frame 11738; **audio-listen again given 3 real bugs fixed
this round** (not done yet — worth doing before further register-trace
chasing); extend to the other 9 v1.2-exact files (none attempted natively
yet); not wired into `DriverSelector`.

## B6 shipped: adaptive part-splitting (Glyptodont: 8 parts; Fargo: 1 part, unchanged)

User listened to `Glyptodont_native.sf2` again after B5's 3 pulse/filter bug
fixes: "it is better but a lot missing in fidelity." Asked to choose between
more bug-hunting, part-splitting, or shifting focus, the user chose
part-splitting — the fix `docs/players/PLAYBOOK.md` §3 already names for
dense tunes that blow the 64-slot bundle cap ("Part-count economics"), the
same mechanism DMC/MoN use (`bin/build_dmc_native_song.py`'s `build_song`,
`bin/build_mon_native_song.py`'s `build_native_song(..., win=, count_only=)`).
This is a TIME split, not a compression fix — each part is independently
playable, together covering the whole song; Stage-C structural RE (extending
the 64-slot ceiling itself) remains the actual "no more clustering, ever"
answer and is out of scope here, unchanged from PLAYBOOK's own framing.

### What was built

`bin/build_blackbird_native_song.py` gained, all Blackbird-specific (not
edits to `sidm2/blackbird_parser.py` or its test, both untouched, still
9/9):

- **`window_steps(steps, row0, row1)`** — slices one voice's full-song
  `BBStep` list to a tick-row window. Ticks map 1:1 to D11 rows (established
  in Stage A), so this needed none of DMC's frame-alignment `align()`
  machinery — a row-index window is already tick-exact. **State continuity**
  (read DMC's `win=` docstring in full before writing this, per the task):
  a note/held-note still sounding when `row0` lands mid-step is RE-ENTERED
  at `row0` (matching DMC's own boundary-continuation fix, which exists
  because silently dropping it left a voice silent until its next onset —
  44% loss measured on one DMC file). Unlike DMC/MoN, whose per-note
  programs are captured LIVE from a siddump trace (so a mid-note capture is
  exact by construction), Blackbird's WAVE/PULSE/FM/FILTER programs are
  STRUCTURAL — real hardware (and the unchanged shared native engine) always
  replays a program from ITS OWN row 0 on a genuine note trigger; there is
  no "resume mid-cycle" primitive. So the re-entered note is forced to a
  genuine trigger (`tie=False`, explicit instrument+fx+note), not a tie —
  tying it would leave WAVE+FILTER parked at `do_init`'s default seed (B4
  Bug 3: tie skips their restart) instead of the correct instrument's
  program, wrong for the note's whole remaining span, not just briefly.
- **`run_full_song_sim`** — ONE full-song `BlackbirdSim` pass producing (a)
  the full frame-by-frame register trace, (b) `row_frame[r]`, the real-frame
  index each row's state first appears at (so a part starting at song-row
  `row0` can be validated against the RIGHT slice of the original
  performance instead of frame 0), (c) the full row-indexed tempo/groove
  schedule (same technique as B3's `extract_tempo_schedule`, folded into one
  pass instead of two).
- **`tempo_at_row` / `window_tempo_schedule`** — a part seeds `CUR_TEMPO`/
  `CUR_TEMPO2` from whichever tempo pair was ACTUALLY active at its own
  `row0` (not necessarily the song's opening pair), and gets its own
  row-shifted slice of the full schedule for its interior tempo changes.
- **`build_range(..., row0, row1, count_only=)`** — the `build_native_song`-
  shaped refactor of the old `main()` body: pass 1 computes the window's own
  used-instrument/used-bundle vocabulary (scoped to just what
  `window_steps`' output references); `count_only=True` stops after that and
  returns `(n_bundles_raw, n_instr, n_wave_rows, n_filter_rows, n_sequences)`
  for a cheap `fits()` probe (no clustering, no assemble); the real build
  goes on to cluster, pack D11 rows, and assemble+wrap a standalone `.sf2`.
  Checked the task's own premise first, against real data, before assuming
  DMC's multi-constraint shape applied unchanged: Glyptodont's WHOLE SONG
  already had deep WAVE (171/256) and FILTER (27/256) headroom, and a
  windowed part's own usage can only be a subset of that — confirmed across
  all 9 built parts (max FILTER usage seen: well under 256; instruments
  capped at 32 naturally since `nins<=32` is a located-table property, not
  window-dependent) — **the bundle cap was indeed the only constraint that
  bound in practice**, though the other 3 caps are still checked defensively
  (a future denser file could differ).
- **`build_song`** — the adaptive grid search: grow a `[row0,row1)` window by
  `STEP=150` row-ticks as long as `fits()` holds, cut, continue. Same shape
  as DMC's `while t0 < span` loop.
- **`prune_stale_parts`** — ported verbatim from `bin/build_mon_native_song.py`.
- Per-part register-trace validation reusing the SAME `report_window`
  methodology as every prior B-round (primary 200f / full-part / a new
  "steady-state" window that excludes each part's own first 200 frames, to
  separate a genuine per-part startup artifact from the rest of the part —
  same segmenting technique B1 used on the whole-song build).

Output convention changed to match DMC/MoN's own `_partNN` naming (even for
a 1-part build) instead of the old unsuffixed `_native.sf2`:
`out/blackbird/Fargo_native_part01.sf2`,
`out/blackbird/Glyptodont_native_part01.sf2` .. `_part08.sf2`. The old
unsuffixed files are deleted by `main()` on each rebuild (superseded, not
kept alongside).

### The CAP_B threshold is Blackbird-specific, NOT DMC/MoN's — verified, not assumed

DMC/MoN's own `CAP_B=63` means "a window's RAW (pre-cluster) bundle count
must already be `<=63`" — effectively **zero tolerated clustering** per
part, which is the whole point of splitting for them. Applying that
literally to Fargo (single file, whole-song raw bundle count = 107) split
it into 2 parts on the first pass here — which directly **fails this task's
own correctness check** ("Fargo must still build as exactly 1 part").
Fargo's existing, previously-shipped whole-song native build already
clusters 43/107 = 40.2% of its bundles away and was never judged a fidelity
problem worth splitting over (only Glyptodont's 359/423 = 84.9% was, per
the user's own repeated "still missing fidelity" feedback specifically on
Glyptodont). **`CAP_B = 2*NFM = 128`** — i.e. at least half a window's raw
bundles must survive unmerged — is the smallest round threshold that keeps
Fargo's known-good 40.2% loss on the "don't split" side while still
triggering a split for Glyptodont's 84.9%: PLAYBOOK.md §3's own language is
"without HEAVY clustering", which this reads as `<=50%` mild / `>50%` heavy.
**Verified, not assumed**: rerunning with `CAP_B=63` first, observing the
Fargo regression, then deriving 128 from Fargo's own already-accepted ratio
and confirming it restores exactly 1 part — this is the "verify this
assumption against the actual code/data before committing" the task asked
for, applied to the fits() threshold itself, not just the multi-constraint
question.

### Results

**Fargo: exactly 1 part, numbers UNCHANGED to the tenth of a percent** —
the correctness check the task asked for. `row0=0`/`row1=3437` (the whole
song) is what the search converges to; `window_steps` on a full-span window
is a no-op relative to the pre-refactor step list (verified: the only
place it forces anything is the very first step, which was already `tie=
False` with an explicit instrument in the original data). Rebuilt and
independently re-diffed against the pre-B6 baseline:

| | primary (0:200) | extended (0:2395) |
|---|---|---|
| pre-B6 (committed a0baaaa + uncommitted B5) | 69.6% overall (freq 81.5, wf 88.8, pulse 1.0, adsr 97.2, filter 99.1) | 72.5% overall (freq 75.2, wf 91.9, pulse 16.8, adsr 97.5, filter 99.8) |
| post-B6 (`Fargo_native_part01.sf2`, same build) | 69.6% overall, identical per-category | 72.5% overall, identical per-category (re-sliced 0:2395 from the new `run_full_song_sim` trace) |

Byte-for-byte identical register-trace comparison output — the refactor is
a genuine no-op for the file that doesn't need splitting.

**Glyptodont: 8 parts** (`row0:row1` in tick-rows; `span`=4469):
`[0:300)`, `[300:750)`, `[750:1200)`, `[1200:1350)`, `[1350:1500)`,
`[1500:1950)`, `[1950:2250)`, `[2250:4469)` (the last part absorbs the
remainder — the search's `fits()` never fails again after row 2250, which
is a real, verified finding of its own: the LAST 2219 rows / ~½ the song
need only 62 raw bundles, needing **zero clustering**, vs the earlier
denser sections).

**Bundle-cap pressure, confirmed much lower per-part than the whole-song
423-vs-64 squeeze** (this was the task's core hypothesis to verify):

| part | rows | raw bundles | after cluster | merged | merge% |
|---|---|---|---|---|---|
| 1 | 300 | 108 | 64 | 44 | 40.7% |
| 2 | 450 | 111 | 64 | 47 | 42.3% |
| 3 | 450 | 101 | 64 | 37 | 36.6% |
| 4 | 150 | 92 | 64 | 28 | 30.4% |
| 5 | 150 | 135 | 64 | 71 | 52.6% |
| 6 | 450 | 108 | 64 | 44 | 40.7% |
| 7 | 300 | 102 | 64 | 38 | 37.3% |
| 8 | 2219 | 62 | 62 | 0 | **0%** |
| **whole song (pre-B6)** | 4469 | 423 | 64 | 359 | **84.9%** |

Every part sits at 30-53% merge loss (one part at literally 0%), vs the
whole song's 84.9% — confirms the hypothesis directly: per-part local
bundle vocabulary is dramatically smaller than the whole song's, matching
Fargo's own already-accepted ~40% ballpark rather than Glyptodont's
previous ~85%.

**Fidelity: real but genuinely MIXED, not a clean win — reported honestly,
not oversold.** Per-part register-trace comparison (same methodology, same
`REGS_TO_CHECK`/`CATS` as every prior round), primary window (first 200f of
each part) and a frame-count-weighted aggregate across all 8 parts' full
windows (the fairest single number, since parts range 750-8974 real frames):

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| Glyptodont whole-song baseline (only known number — its own extended window was never reachable pre-B6, boundary at frame 11738 > the old 3000-frame cap) | 53.5% | 32.5% | 73.3% | 0.3% | 96.6% | 85.5% |
| 8-part average, primary (200f each, unweighted) | 49.9% | 34.7% | 44.8% | 15.3% | 79.7% | 84.1% |
| 8-part average, full-part (frame-count-weighted) | 53.7% | 42.0% | 49.1% | 12.3% | 83.9% | 91.8% |

**freq (+9.5pp) and filter (+6.3pp) genuinely improve** — consistent with
much lower bundle-cap pressure. **pulse also reads higher** (+12pp) but
this needs an independent re-check before trusting it at face value (see
the stale-register finding below — a resting voice's pulse register can
read 0 on BOTH sides by coincidence in a fresh part, which would inflate
the score without being a real translation improvement; B5's own pulse fix
was verified on Fargo's *actively playing* content, not this scenario).
**waveform (-24.2pp) and ADSR (-12.7pp) get WORSE**, and **overall composite
is a wash** (53.7% vs 53.5%) — not the clean win the bundle-cap-pressure
story alone predicts. Root cause, found by direct diagnosis (not assumed):

### A genuinely NEW residual, found and diagnosed this round (not fixed)

Traced part 4 (`row0=1200`) frame-by-frame: voice 1's real windowed steps
open with a REST (`kind=rest`), correctly — voice 1 isn't re-triggering
right at row 1200. But the validated whole-song simulator's register trace
at that SAME real frame shows voice 1's `$D40C`/`$D40D` (AD/SR) holding
`(17, 154)` — **nonzero, leftover from a note that finished well before row
1200** (SID registers hold their last-written value indefinitely; nothing
about "resting" clears them). The freshly-built PART's own driver
necessarily starts every register at power-on-reset (`0`), since a part is
a genuinely standalone file with no continuation from a hypothetical
"previous part" — so it reads `(0, 0)` for the same frames, a real,
structural mismatch that persists for however long that voice stays resting
within the part (here, ~15 frames before voice 1's own next real trigger;
worse in parts where a voice rests longer). This is DIFFERENT from the
already-named "forced retrigger of an actively-sounding note" residual
(`window_steps`' own docstring) — that one is about a voice that IS
sounding at the cut; this one is about a voice that ISN'T, whose real
register content is inherited from arbitrarily far back in the song's
history, which a standalone part can never reconstruct without deliberately
priming it. It explains the data cleanly: part 1 (`row0=0`, the TRUE song
start — nothing is "stale" because nothing existed before frame 0) and part
8 (all 3 voices happen to retrigger promptly near its own `row0`) both keep
ADSR/waveform near baseline (96-100%); the middle parts, where at least one
voice sits mid-rest at the cut, show the degradation.

**Not fixed this round** (named, not silently absorbed, per this task's own
instruction): a real fix exists in principle — seed each part's `do_init`
with a one-time, non-audible priming write of whatever AD/SR/waveform/pulse
byte each voice's real "last active instrument as of `row0`" would leave
behind, the same PRIMING CONCEPT `default_filter_program` already uses for
the filter engine's position-0 walk. That needs actual driver-side support
(a new init-time register-write block) — this task's own constraint says
"don't touch the driver unless splitting genuinely requires it", and this
finding suggests it plausibly does, but implementing and verifying a
driver change was judged out of scope for this pass (real risk of a new,
unverified bug in the remaining time) — flagged as the clear next step
instead.

### What's still open

- **The stale-register-at-boundary fix** (above) — the single most
  concrete, well-diagnosed next step; would likely recover most of the
  waveform/ADSR regression without touching the bundle-cap logic at all.
- **The pulse improvement needs independent re-verification** — plausible
  it's partly a coincidental zero-match artifact of the same stale-register
  effect rather than a genuine translation win; not disentangled this round.
- **Audio has NOT been listened to for any of the 9 new part files** —
  the user previously listened to the single whole-song `Glyptodont_native
  .sf2`; that file no longer exists (superseded by 8 parts). **The user
  needs to listen to each part separately** via
  `pyscript/sf2_open_in_editor.py out/blackbird/Glyptodont_native_partNN.sf2`
  to judge whether the mixed register-trace picture above (real freq/filter
  gains, real waveform/ADSR regression) nets out as an audible improvement
  — the register-trace metric alone doesn't settle that question, same
  caveat every prior round has carried.
- **A genuine part-boundary discontinuity exists and is worth naming
  explicitly**: each part is a SEPARATE, independently-loaded SF2 file, not
  a seamless single song — there is a hard stop/restart between parts (no
  crossfade, no continued envelope/filter/arpeggio state), on top of the
  stale-register and forced-retrigger residuals above, which compound at
  exactly the same instants. A listener moving from one part's SF2 to the
  next will hear a hard cut, not a splice.
- **The ~2-3 frame architectural startup/trigger-timing skew** (B5's own
  still-open item) is now paid ONCE PER PART instead of once per song (8x
  for Glyptodont) — not separately quantified from the stale-register
  effect this round, but plausibly a secondary contributor to the primary-
  window numbers specifically (steady-state windows track full-part numbers
  closely in the data above, suggesting this specific skew is NOT the
  dominant term — the stale-register effect, which persists for as long as
  a voice stays resting rather than settling after a few frames, is).
- `estimate_tempo_chain`'s Stage-A off-by-one (still untouched); mode=0
  filter rows (still untouched); extend to the other 9 v1.2-exact files
  (none attempted natively yet); not wired into `DriverSelector`.

## B7 shipped: part-boundary engine-state priming, and a real comparison-anchor bug found

B6's own "still open" list named the diagnosis precisely: a part standalone
SF2 always cold-starts (`do_init` zeroes every register/engine-state field),
but on real hardware a voice mid-sustain (or silently resting on a note that
finished long before this part's own row0) keeps its real state — B6
measured this as a real WAVE/ADSR regression (waveform -24.2pp, ADSR
-12.7pp) that made Glyptodont's 8-part split a fidelity wash (53.7% vs
53.5% pre-split) despite real freq/filter gains. This round built the named
fix (priming) and, in verifying it, found a SECOND, larger bug the priming
work exposed but didn't cause: the register-trace comparison's own frame
anchor was off by one tick for every part after the first.

### What was built

**`bin/blackbird_everyframe_sim.py`** gained two purely-additive fields
(default-off, zero behavior change for every existing caller/test):
`self.filt_owner` (tracks which `filt_start` — 0 = the song's own default
program, else a real per-instrument value — currently governs the GLOBAL
filter engine's `zp_filtpos`, alongside the existing `zp_filtpos` write in
`execute()`) and `snapshot_cb` (an optional hook `real_frame()` calls once
per frame, AFTER `execute()` has committed that tick's pending note/
instrument state but BEFORE `everyframe()` steps the wave/pulse/fx/filter
engines forward — exactly the engine state a NEW part starting at that
frame needs to prime its own `do_init` with).

**`bin/build_blackbird_native_song.py`**:
- `run_full_song_sim` now also returns `row_state[r]`: the full per-voice
  (`wavepos`, `wavemask`, `currins`, `currfx`, `pendnote`) + global
  (`zp_filtpos`, `filt_owner`, all 25 raw `$D400-$D418` registers) engine
  state captured via the new `snapshot_cb`, indexed so `row_state[r]`
  reflects the state as row `r` begins (i.e. `row_state[0]` is the sim's own
  pristine `__init__` state, byte-identical to `do_init`'s existing cold-
  start defaults by construction).
- `unroll_wave_pulse`'s and `unroll_filter`'s stats now additionally expose
  the internal position walk (`positions` / `row_frame_start` for filter,
  which also needed a real bug fix: the `$7f`-jump-row split at `cyc_start`
  mutated `rows` but not `row_frame_start`, silently desyncing the two
  lists from that point on — never mattered before B7 since nothing
  downstream re-read `row_frame_start`, but B7's own lookup needs it
  in sync). `_lookup_wave_row`/`_lookup_filter_row` map a REAL captured
  absolute table position back to the translated program's own local row
  (+ in-row frame offset, for filter) — reusing the position walk's own
  documented state-independence (same fixed table bytes → same
  deterministic sequence regardless of what triggered the walk) rather
  than re-deriving anything.
- `build_range` gained a `prime`/`row_state` path: for `row0>0`, it pulls
  in whichever instrument a resting voice is silently still holding (via
  `currins`) and whichever program is repositioning the global filter (via
  `filt_owner`, resolved back to a real instrument index by scanning
  `ins_filt`) into `used_instr`/`used_keys` *before* the normal per-
  instrument/bundle build runs, so their real WAVE/FILTER/FM/PULSE programs
  are guaranteed present for priming to reference (a resting voice never
  names an instrument in its own windowed step stream — see
  `window_steps`' docstring). `_compute_prime_consts` (new) resolves the
  concrete per-part `PRIME_*` values AFTER `gen_includes_song` has
  allocated this part's own table addresses (can't run before — the
  addresses don't exist yet), reading AD/SR/flags/filt-start straight back
  off the INSTR table (never re-derived — set once at trigger, never
  touched between triggers) and FM/PULSE pointers off the per-bundle
  address table for whichever bundle the synthetic
  `(currfx, pendnote, owner_instr)` priming key resolved to post-
  clustering. `_write_prime_consts` appends the result to the SAME
  `layout.inc` `gen_includes_song` just wrote.
- **`drivers_src/blackbird/blackbird_driver.asm`**: `do_init`'s per-voice
  `iv:` loop and the filter-init block now read `PRIME_<field><0/1/2>`
  scalar constants (via small `.byte`-table trampolines, `PRIME_<field>_TAB`,
  placed in the SAME already-`*=`-positioned "natural gap" region the
  `tempo_sched_*` tables already use — **NOT inside `layout.inc` itself**,
  which is `.include`d before any `* = ` origin directive, so raw byte data
  placed there would land at an undefined address; a real mistake caught
  before it shipped, not after) instead of hardcoded literals. Lengthening
  `iv:` pushed its own `bpl iv` past a signed 8-bit branch's range — fixed
  with the same `bmi/jmp` trampoline idiom already used elsewhere in this
  file (`pn_adv`). For `row0==0`, `_compute_prime_consts` emits values that
  are BYTE-IDENTICAL to the old hardcoded literals (verified explicitly,
  see Results below) — there is no runtime flag or branch gating this; the
  same code path degrades to the old cold-start behavior automatically.

**Fields deliberately NOT resumed mid-program** (named simplifications, not
silently absorbed): PULSE (`VPLO`/`VPHI`) is primed from the raw captured
`$D402` byte and then FROZEN (`VPC=$ff`, `VPADL`/`VPADH=0`) rather than
resumed from its real position — this engine's PULSE table has no native
jump/resume primitive at all (see `unroll_wave_pulse`'s own "PULSE"
docstring section: even a freshly-triggered note's own pulse program is a
physical repeat-then-freeze, not a true loop), so freezing at the last real
observed value is the best available approximation with the existing table
format. FM (`FM_ON`/`FM_ACC`/etc.) is forced OFF (flat, no modulation)
rather than resumed mid-flight — unlike WAVE/FILTER (purely
per-*instrument* programs), a resting voice's FM state depends on BOTH the
per-note `(fx, note)` bundle AND its own position within it, needing the
same position-mapping machinery FM's own value additionally being
note-parameterized (not just instrument-parameterized) — judged out of
scope for this round; flagged, not fixed.

### A second, bigger bug found while verifying: the comparison's own frame anchor was off by one tick

Before touching the driver at all, this round rebuilt Fargo + Glyptodont
with ONLY the `blackbird_everyframe_sim.py` changes (no priming logic yet)
to re-confirm B6's own reported numbers as a baseline — they matched
exactly (Fargo 69.6%/75.5%/75.9%; Glyptodont per-part numbers identical to
B6's own table). After wiring up priming, Fargo (row0=0, unaffected by
priming) stayed byte-identical, but Glyptodont's parts 2-8 showed almost NO
movement in waveform/ADSR despite priming clearly computing real,
non-default values (verified directly: `PRIME_AD1=17`/`PRIME_SR1=154` for
part 4's voice 1 matched B6's own named example exactly). That mismatch —
priming visibly correct, but not moving the metric — is what led to
digging further rather than reporting a hand-wavy "priming didn't help
much" result.

**Root cause**: `row_frame[r]` (used by `main()`'s existing `F0 =
row_frame[row0]` comparison anchor since B6) is the real frame at which the
sim's `row` counter *became* `r` — which happens during the `real_frame()`
call that just committed row `(r-1)`'s note/instrument event, not row `r`'s.
So `full_frames[row_frame[r]]` shows row `(r-1)`'s content, one tick STALE
— confirmed directly two independent ways: (1) `row_state[r]`'s own
per-voice content (e.g. gate mask alternating ON/OFF every tick on a
staccato passage) matched `window_steps`' step covering position `[r-1,
r)`, not `[r, r+1)`; (2) `full_frames[row_frame[1200]][11]` (voice 1's
`$D40B`) read `129` (gate ON) at the exact frame B6's own report said
should show a REST (gate OFF) — the genuine "stale content" signature, one
tick early, at a real, checkable register.

The driver's own frame 0 (`do_init` + the immediate first `do_row` call)
shows row0's OWN committed content, so it must be compared against
`full_frames[row_frame[row0 + 1]]`, not `full_frames[row_frame[row0]]`.
**Verified empirically before applying the fix** (per this task's own
"don't accept a hand-wavy explanation" instruction): switching ONLY this
anchor, on the SAME already-built (primed) part-4 driver binary, moved
waveform 40.0%→89.7%, AD/SR 63.9%→91.5%, overall 48.5%→68.3% — the anchor
alone, not the driver content, was hiding a mostly-correct translation
behind a comparison that was quietly grading it against the wrong instant.

**`row0==0` is deliberately EXEMPTED from this fix** (kept at the historical
`row_frame[0]==0` anchor), to satisfy this task's own explicit constraint
that Fargo/part-1 must not regress or change its already-verified-correct
reported numbers. This is principled, not just convenient: `row0==0` is a
genuine cold start on BOTH sides (`do_init`'s literal defaults exactly equal
the sim's own pristine `__init__` state), so the two anchors start from an
identical degenerate all-zero baseline and only ever diverge by the
ALREADY-DOCUMENTED, separately-named "~3-frame startup-pipeline offset"
residual (the `cpx #3*7` 3-slot dispatch reservation) — a real but much
smaller, already-tolerated effect, not the same one-full-TICK content
mismatch this fix addresses for `row0>0`. (Applying the corrected anchor to
Fargo too, purely as a check, moved its own numbers 69.6%→71.6%,
waveform 88.8%→97.8% — a further improvement, consistent with the same root
cause applying there too, but deliberately NOT taken since it would change
the correctness anchor's own reported baseline.)

This means the SAME bug affected every prior B6-era report that used
`row0>0` — this round's own before-priming Glyptodont baseline rebuild
(used above to confirm B6's numbers) inherited it too, since it's a
pre-existing bug in `main()`'s comparison code, not something this round's
changes introduced. It was invisible before B6 (Fargo/whole-song builds are
always `row0=0`) and invisible in B6's own report because there was no
"expected big improvement that didn't show up" signal to chase yet.

### Results (same `report_window` methodology as every prior round)

**Fargo: byte-identical to the pre-B7 baseline**, verified via sha1 (not
just the printed percentages): same `Fargo_native_part01.sf2` hash across a
from-scratch rebuild before ANY B7 code existed and after all of it,
confirming `row0==0`'s priming-reduces-to-identity property holds in
practice, not just in the Python `None`-branch code.

**Glyptodont, 8-part average** (unweighted primary-window average and
frame-count-weighted full-part average, same two numbers B6's own report
used):

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B6 baseline, primary avg | 50.0% | 34.7% | 44.8% | 15.3% | 79.7% | 84.1% |
| B7 (priming + anchor fix), primary avg | **64.5%** | **54.8%** | **84.3%** | 19.7% | **94.2%** | 86.7% |
| B6 baseline, full-part weighted | 53.7% | 42.0% | 49.1% | 12.3% | 83.9% | 91.8% |
| B7 (priming + anchor fix), full-part weighted | **65.1%** | **58.3%** | **87.2%** | 13.7% | **94.0%** | 92.5% |
| *(reference) Glyptodont whole-song, pre-split single file* | 53.5% | 32.5% | 73.3% | 0.3% | 96.6% | 85.5% |

**Waveform and AD/SR — the two categories B6 flagged as regressed — now
EXCEED the pre-split single-file baseline** (waveform 87.2% vs 73.3%;
AD/SR 94.0% vs 96.6%, essentially matching it) while freq/filter's B6-era
gains are preserved and improved further (freq 58.3% vs 32.5%; filter
92.5% vs 85.5%). Part 1 (`row0=0`, unaffected by priming or the anchor fix)
is unchanged from B6 at 59.7%/57.0%/56.6% (primary/full/steady-state) —
the correctness anchor for the part-splitting scheme itself, confirming
nothing broke the one part that must stay untouched.

Per-part breakdown, full-part window (B6 → B7): part1 57.0%→57.0%
(unaffected, `row0=0`); part2 51.5%→68.6% (waveform 36.0%→88.2%, adsr
76.6%→91.5%); part3 49.5%→65.6% (waveform 39.5%→90.0%, adsr 77.3%→92.1%);
part4 (B6's own named diagnostic example) 45.5%→71.5% (waveform
35.2%→86.0%, adsr 55.8%→91.5%); part5 46.7%→65.2% (waveform 39.8%→87.6%,
adsr 64.8%→92.9%); part6 48.2%→61.2% (waveform 32.2%→93.7%, adsr
88.3%→95.7%); part7 46.6%→61.4% (waveform 27.1%→90.1%, adsr 86.6%→94.5%);
part8 68.5%→69.3% (waveform 95.8%→97.7%, adsr 99.7%→99.8%, already
near-ceiling pre-B7 since it needed no clustering and ends the song with
no further mid-part rest crossing back into stale content).

Determinism verified: two independent from-scratch rebuilds of both files
produced byte-identical sha1 hashes on every output `.sf2`, and
`pyscript/test_blackbird_parser.py` stayed 9/9 throughout (untouched, as
required).

### Honest residuals — not fixed this round, named precisely

- **Pulse (13-44% per part, no clean trend) and freq (43-75%) are still
  the dominant gaps.** Pulse's own residual is the SAME already-documented
  "no jump/resume primitive in this table format" limitation B1-B6 already
  named, now ALSO true of the priming freeze (a resting voice's pulse
  output is approximated, not resumed, so a long-enough rest before a part
  boundary can still show drift). Freq's residual is the SAME already-named
  1-frame FM-lag + ~3-frame startup-pipeline architectural skew, now more
  visible (not less accurate) because the anchor fix stopped it from being
  masked by the larger one-tick misalignment.
- **The filter's mid-row ADD-ramp resume path (`PRIME_F_CNT`/`PRIME_F_ADHI`
  nonzero) was implemented but never actually exercised on either file** —
  every one of Glyptodont's 7 primed part boundaries happened to land
  exactly on a fresh filter-row start (`PRIME_F_CNT=0` in all 8 parts,
  checked directly). The row-start priming path (`PRIME_F_IDX`/`F_CLO`/
  `F_CHI`/`F_MODE`/raw `$D417`) IS exercised and contributed to filter's
  modest real gain (84.1%→86.7% primary), but the mid-ramp-resume code is
  unverified beyond "assembles and doesn't obviously break anything" —
  flagged for whoever next hits a part boundary that lands mid-ramp.
- **`exact frames` stayed at 0/N for every Glyptodont part**, even after
  this round's gains (Fargo itself only reaches 4/2800 in its own extended
  window) — the improvement is broad/aggregate across registers and
  frames, not byte-for-byte-perfect on any single frame; consistent with
  every prior round's own experience, not a new characteristic.
- FM's "freeze rather than resume" simplification (named above) is
  unquantified independently of the aggregate freq number — a future round
  could isolate it by checking whether Glyptodont's remaining freq gap
  concentrates on voices with long FM/arp programs specifically.
- Audio has NOT been listened to for the rebuilt parts this round (register
  trace only, per every prior round's own caveat) — worth doing given the
  size of the waveform/ADSR recovery.
- Unchanged from B6's own list: `estimate_tempo_chain`'s Stage-A off-by-one,
  mode=0 filter rows, extending to the other 9 v1.2-exact files, not wired
  into `DriverSelector`.

## B8 shipped: PULSE decoupled from the FM bundle, 4 more real bugs, Fargo 75.5% -> 94.1%

B7 left PULSE and FM as the two deliberately-unfinished pieces of part-
boundary priming, and named them as the dominant residuals. Both were built
this round — but chasing them turned up something bigger first: PULSE's real
problem was never boundary priming at all. Fargo is a **single part with no
boundary to prime** and still read pulse 26.9%, which is the signal that led
here. Four genuinely separate bugs came out of it.

### Bug 1 (the big one): PULSE was bundled with FM, but hardware ties it to the INSTRUMENT

`pr_setprog` used to set BOTH `VIFM` (the fx/arp program) and `VIPUL` (the
pulse program) from the same `$c0-$ff` command index. That is wrong about
real hardware: `BlackbirdSim.everyframe()` reads a voice's pulse rows out of
the **same wavetable walk that produces `$D404`**, seeded by `ins_wave[i]` —
pulse is per-INSTRUMENT, exactly like WAVE, and has nothing to do with the
per-note fx bundle. Bundling them meant that every time the 64-slot cap
forced a merge, the surviving bundle dragged a **foreign instrument's pulse
program** along with its FM program.

Diagnosed rather than guessed: Fargo held **waveform at 98.9%** — so the
wavepos walk, and therefore the instrument, was provably correct — while
pulse read 14.3%, and a frame-by-frame diff showed the driver *sweeping*
where the validated simulator held a flat constant. Same instrument, wrong
pulse program.

Fixed by moving the `VIPUL` load out of `pr_setprog` and into `set_instr_v`,
with the `IPULSE_LO/HI` arrays re-indexed by instrument row instead of
command index (they keep their `NFM`-sized allocation so no other table
address moves). Two independent wins:

- pulse becomes correct for merged bundles;
- the bundle vocabulary collapses to distinct **(fx, note)** pairs alone —
  **Fargo 107 raw bundles -> 80**, merges 43 -> 16 — which lifts freq too
  (80.1% -> 87.7%) purely as a side effect of less clustering.

### Bug 2: the pulse width is an ACCUMULATOR that does not cycle with `wavepos`

`unroll_wave_pulse` captured pulse output only over the wavepos cycle
(`prefix + repeat(cycle)`), assuming a repeating wavepos implies a repeating
pulse. It does not: `vs.pwidth` is a running accumulator fed through the
fixed `pwprepare` lookup, so a wave program that loops every N frames can
still produce a pulse value that sweeps continuously and never repeats.

Caught on **Glyptodont part 8** — a part with **zero** bundle clustering and
97.7% waveform, yet 1.6% pulse: the simulator swept +32/frame for the whole
window while the driver replayed a 2-3 frame loop forever.

The fix is a **per-instrument** decision, made from the data, not a global
switch — and the split matters in both directions, which is why neither
global option was taken:

| encoding applied to every instrument | Fargo pulse (full-part) | Glyptodont part 8 pulse |
|---|---|---|
| fold onto the wavepos cycle (pre-B8) | 87.8% | 1.6% |
| literal long capture (1200f) | 14.3% | — |
| adaptive: fold iff genuinely periodic | **89.6%** | (see punch list) |

The periodicity test searches **multiples** of the wavepos period, not just
the period itself (the pulse period only has to be a multiple of it).
Searching `m=1` alone misclassified all of Fargo's instruments as sweeping
and cost 73pp of pulse accuracy — a real trap, recorded here so nobody
re-derives it.

**A documented negative result**: a pure-DELTA encoding (`0X` ADD rows,
which this table format supports and nothing had ever emitted) is the
*semantically* right model — a note-on restarts the wave program but NOT the
width accumulator, so the changes should restart while the value carries
over. It scored better in a fresh part's first ~200 frames (Fargo primary
pulse 79.7% vs 27.5%) and then **drifts irrecoverably** over a long window
(full-part 7.4%), because `pwprepare` is **not affine**: it is a -16 ramp
with wrap discontinuities (index 8 -> 15, index 9 -> 254), so an output
delta is only history-independent while the accumulator stays inside one
ramp segment. Once hardware's `pw` and the capture's `pw` sit on opposite
sides of a wrap, every later delta is wrong and nothing re-anchors.
Absolute encoding wins on every long window measured, so that ships.

### Bug 3: nothing modelled hardware's `wavepos == 0` DEFAULT wave/pulse program

Real hardware's wave engine is unconditional from frame 0 with `vs.wavepos`
initialized to 0, so **before a voice's first note the default program is
already stepping** and already writing `$D404` and (via its bit6 pulse rows)
`$D402/3`. `do_init` instead pointed `VWI`/`PPTR` at whatever program
happened to land at table row 0 / bundle 0. Measured consequence: Fargo
voices 0 and 1 sat at `$D402 == 0` for the *entire song* while the simulator
held 8 — because those instruments' own pulse programs are freeze-only
(B5's `$7f` bare program), so the pre-note value is the only value they ever
have.

Fixed by pinning the genuine `wavepos==0` program at **WAVE row 0**, exactly
as `default_filter_program` / `FILT_INIT_ROW` already did for the filter
(`WAVE_INIT_ROW`), and priming `PPTR` from it. This is the structural
symmetry B1 gave the filter and never gave WAVE/PULSE.

### Bug 4: a resume landing exactly ON a row boundary skipped that row's load

The new resume path set `VPC = run - e` and advanced the cursor past row
`r`. At `e == 0` that skips the row's **load**, and a SET row's whole effect
IS its load. Caught on Fargo voice 2, whose resume sat on a `SET 187 for 247
frames` row at elapsed 0: the driver held the previous value (8) for the
entire part instead of ever writing 187. Fixed for PULSE and FM alike (at
`e == 0`, point at row `r` with the counter at 0 so the engine loads it).

### Lever 1 as originally scoped: genuine mid-program PULSE and FM resume

Both are now real, and B7's "no jump/resume primitive exists" framing turned
out to be a non-issue: **no table primitive is needed**, because both
engines' entire position lives in plain runtime state that `do_init` can
write directly. Verified against `pulse_step`/`fm_step` instruction by
instruction — a row whose byte2 is `run` is loaded on the frame its counter
reads 0, which sets the counter to `run`, applies, then decrements, so the
row is live for exactly frames `[start, start+run)`.

- **PULSE**: `PPTR` (row cursor, primed *separately* from `VIPUL` — `VIPUL`
  is the RESTART address `pn_note` reloads, `PPTR` is where the engine is
  right now; at a boundary these are genuinely different programs) +
  `VPC` + `VPLO`/`VPHI` + `VPADL`.
- **FM**: `FMP` + `FM_CNT` + `FM_OFF_LO/HI` + `FM_ON` + — the load-bearing
  one — `FM_ACC_LO/HI`, since FM is a cumulative accumulator so the voice's
  whole current pitch offset lives there rather than in the table. B7's
  cited blocker (FM is note-parameterized, so you must know which bundle was
  in flight AND how far into it) is real but the snapshot already carries
  both: `currfx` + `pendnote` select the program, `fxpos` locates the
  position inside it via the same deterministic walk `unroll_fm` records.
- Both resume programs are emitted as **aux programs** into the same
  `FMTAB`/`PULSETAB` (deduped, so they usually cost nothing) rather than
  read off the post-clustering bundle — clustering can replace a resting
  voice's real program with a merged neighbour's, and priming a mid-flight
  position into the wrong program is worse than useless.
- Both degrade safely: when the position cannot be resolved, `FM_ON=0` /
  the pulse freeze reproduce B7's behaviour exactly.

Priming does **not** fight `pn_note`: `do_init` runs before the first
`do_row`, so a voice that genuinely triggers at the part's own row 0 has its
primed state overwritten by its own trigger, as it should be.

### Bug 5 (measurement, not content): B7's `row0==0` anchor exemption is gone

B7 fixed the comparison anchor to `row_frame[row0+1]` but **exempted
`row0==0`** purely so Fargo's published baseline wouldn't move — while its
own report noted the corrected anchor scored better there too. That
exemption is removed; the anchor is now uniform. The driver's frame 0
(`do_init` + the immediate first `do_row`) shows row0's own committed
content on every part including part 1, and real hardware does not commit
row 0 until its dispatch has spent 3 frames on `prepare1/2/3`
(`row_frame[1] == 3`, measured on both files).

**The same off-by-one was still in the PRIMING snapshot**, which B7 left on
`row_state[row0]` — one full tick (~5 real frames) before the instant it
represents. Both now use `row0 + 1`.

Because this changes the measurement, the anchor's contribution is reported
separately rather than folded into the headline. Sweeping the anchor +/-1 on
the **same** final Fargo binary:

| anchor F0 | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| 0 (B7's exempted anchor) | 91.8% | 85.2 | 91.7 | 87.6 | 97.4 | 99.9 |
| 2 | 93.5% | 87.8 | 96.5 | 88.7 | 98.4 | 100.0 |
| **3 (= `row_frame[1]`, shipped)** | **94.1%** | 87.7 | 98.9 | 89.6 | 98.8 | 100.0 |
| 4 | 93.1% | 86.3 | 96.5 | 88.7 | 98.2 | 100.0 |

It is a **strict local maximum**, which a coincidental improvement would not
be. It is also worth only **+2.3pp**: Fargo's 75.5% -> 91.8% is real content
improvement measured under B7's *own* anchor, with the anchor fix adding
2.3pp on top. The headline gain is not a measurement artifact.

### Results

**Fargo (1 part, `CAP_B` unchanged in effect — still 1 part)**:

| window | B7 | B8 |
|---|---|---|
| primary (0:200) | 69.6% (freq 81.5, wf 88.8, pulse 1.0, adsr 97.2, filter 99.1) | **96.8%** (freq 88.1, wf 99.7, **pulse 100.0**, adsr 98.7, filter 100.0) |
| full-part (0:3000) | 75.5% (freq 77.8, wf 91.6, pulse 26.9, adsr 97.4, filter 99.9) | **94.1%** (freq 87.7, wf 98.9, pulse 89.6, adsr 98.8, filter 100.0) |
| exact frames | 4/3000 | **1182/3000** |

**Glyptodont (10 parts at the new `CAP_B=96`; B7 had 8 at `CAP_B=128`)**,
frame-count-weighted full-part aggregate:

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B7 (8 parts) | 65.1% | 58.3 | 87.2 | 13.7 | 94.0 | 92.5 |
| B8 (10 parts) | **67.3%** | **62.2** | **90.5** | 16.8 | 94.6 | 92.5 |

Per-part, B8 full-part window: p1 73.7, p2 69.2, p3 69.3, p4 66.4, p5 73.6,
p6 68.2, p7 62.1, p8 62.1, p9 62.7, p10 69.2. Merges per part are now
0-32 (was 28-71).

**Glyptodont's gain is real but modest, and much smaller than Fargo's** —
stated plainly rather than averaged away. Fargo's headline comes mostly from
Bugs 1/3, which bite hardest on a file whose instruments have freeze-only or
periodic pulse programs. Glyptodont's dominant residual is different (see
below) and is NOT fixed.

Determinism re-verified: two from-scratch rebuilds produced byte-identical
sha1 for Fargo's part and all 10 Glyptodont parts.
`pyscript/test_blackbird_parser.py` stayed 9/9 (untouched).

### Lever 2: the `CAP_B` sweep — a real but small effect, and 64 is disqualified

Re-derived empirically rather than argued, since B6 picked 128 under a
constraint B7/B8 have since removed (cold-start boundaries used to be very
lossy, so splitting was expensive; priming made it cheap). Glyptodont,
frame-count-weighted full-part aggregate, everything else identical:

| CAP_B | parts | overall | freq | wf | pulse | adsr | filter |
|---|---|---|---|---|---|---|---|
| 128 | 5 | 66.4 | 57.9 | 90.4 | 17.6 | 94.3 | 92.4 |
| **96** | **10** | **67.3** | **62.2** | 90.5 | 16.8 | 94.6 | 92.5 |
| 80 | 15 | 67.7 | 63.4 | 90.4 | 17.0 | 94.6 | 92.5 |
| 64 | 16 | 67.7 | 63.7 | 90.4 | 17.0 | 94.6 | 92.5 |

The effect is confined almost entirely to **freq** — the only category
bundle clustering still touches, now that B8 moved PULSE off the bundle:
**+5.8pp freq / +1.3pp overall** from 128 -> 64, **flat past 80**, at 3x the
part count.

**Fargo, prominently flagged**: it stays exactly 1 part and byte-identical
at 128 / 96 / 80 (its raw bundle count is 80 after B8's decoupling), but at
**64 it splits into 2 and regresses hard: 94.1% -> 77.5%** (pulse 89.6 ->
47.7, adsr 98.8 -> 84.2). So 64 is out on Fargo's evidence regardless of
Glyptodont's marginally better number — a case where the "Fargo stays 1
part" proxy and the actual fidelity measurement agree.

**Recommendation, shipped: `CAP_B = 96`.** It keeps Fargo at 1 part and
byte-identical, takes ~3/4 of the available freq gain (+4.3 of +5.8pp), and
needs 10 parts rather than 80's 15. Part count is a real cost the
register-trace metric does **not** price in: each part is a separate SF2
with a hard cut, no crossfade. **80 is the measured fidelity optimum if part
count is no object** — override with `BB_CAP_B` (the threshold is now
environment-sweepable so this stays a measurement, not an argument).

### Honest residuals — named precisely, not fixed

- **Glyptodont's pulse is still the dominant gap (1.2-38.7% per part;
  weighted 16.8%), and its cause is now identified as a genuine
  REPRESENTATIONAL gap rather than a bug.** This shared engine's `PULSETAB`
  stores the **output byte**; Blackbird stores an **accumulator** (`pwidth`)
  fed through a **non-affine** lookup (`pwprepare`). For a long sustained
  note crossing a part boundary — Glyptodont part 10's case, diagnosed
  directly — hardware continues its own accumulator sweep while the driver's
  forced boundary re-trigger (`window_steps`' already-named residual)
  restarts the width from the from-zero capture's phase. Absolute encoding
  re-anchors instead of drifting, which is why it ships, but it cannot
  reproduce a phase it was never given. Closing this properly means either
  a driver-side `pwidth`+lookup engine (a real Stage-C change to the shared
  stepper) or extending priming to carry a mid-sweep phase into a
  re-triggered note. Neither attempted.
- **Freq (62.2% weighted on Glyptodont, 87.7% on Fargo)** remains the second
  gap. Bundle clustering is now measured at only ~1.3pp of it (the CAP_B
  sweep above), so the majority is the already-named architectural
  1-frame FM-lag on note trigger plus the ~3-frame startup-pipeline skew —
  now more visible, not less accurate, since the anchor and content fixes
  stopped masking it.
- **The FM mid-program resume is implemented and exercised but not
  independently quantified.** Its effect is folded into the aggregate freq
  number; isolating it would need a build with FM priming forced off.
- **The filter's mid-row ADD-ramp resume path is still unexercised** —
  unchanged from B7; every Glyptodont boundary still lands on a fresh
  filter-row start.
- **`exact frames` is now genuinely nonzero on Fargo (1182/3000, up from 4)
  but remains 0-1 per part on Glyptodont.**
- **Audio has NOT been listened to for any B8 output** (register trace
  only), and the part count changed for Glyptodont (8 -> 10 files), so the
  earlier per-part listening notes no longer map. Same caveat every round
  has carried, and it matters more here because `CAP_B`'s part-count
  trade-off is explicitly a musical judgement the metric can't make.
- **A disproved hypothesis, recorded so it isn't re-tried**: a note byte
  with no preceding instrument byte looked like it should behave as legato
  (leaving WAVE/PULSE/FILTER/gate running), since `execute()` only touches
  them inside its `pendins != 0` branch. It does not — `prepare3` contains
  `if vs.pendins == 0: vs.pendins = vs.currins`, an implicit
  repeat-instrument, so a bare note performs a full instrument re-select.
  Building it the other way regressed Fargo's waveform 91.6% -> 84.1%.
  The simulator settled this in one build; the static reading of
  `execute()` alone was misleading.
- Unchanged from B6/B7: `estimate_tempo_chain`'s Stage-A off-by-one, mode=0
  filter rows, part-boundary hard cuts, extending past Fargo+Glyptodont to
  the other 9 v1.2-exact files, not wired into `DriverSelector`.

### Driver memory-map note (mechanical, but a trap for the next round)

B8's `do_init` growth plus 11 new `PRIME_*_TAB` tables overflowed the
~311-byte unpinned gap the tempo-schedule tables lived in, spilling into
SF2II's reserved `$16CC-$1702` playback-state region (caught by
`build_blackbird_driver_full.py`'s own guard, not at runtime). The driver's
private state block was relocated `$1800-$1861` -> `$1980-$19E1` (+$180,
still below `EDIT_BASE = $1A00`), and the `PRIME_*_TAB` + `tempo_sched_*`
tables moved above `freqtable`. **The first attempted placement put tables
at `$17D0-$1810`, which silently overlapped `VWI` at `$1800`** — a live
state variable, so the tables would have been overwritten at runtime rather
than failing to assemble. Worth knowing that the state block is now much
closer to `EDIT_BASE`: worst-case `tempo_sched` (64 entries x 4 tables =
256 bytes) plus freqtable and the prime tables fits with ~111 bytes spare.

## B9 shipped: the pulse ACCUMULATOR runs in the driver (Glyptodont 67.3% -> 82.7%, pulse 16.8% -> 80.9%)

B8's punch list named Glyptodont's pulse as "a genuine REPRESENTATIONAL gap
rather than a bug": this shared engine's `PULSETAB` stores the **output
byte**, Blackbird stores an **accumulator** fed through a **non-affine**
lookup, and it named the two ways out — "either a driver-side `pwidth`+lookup
engine (a real Stage-C change to the shared stepper) or extending priming to
carry a mid-sweep phase into a re-triggered note." B9 is the first of those,
and it turns out to deliver the second for free.

### The measurement that motivated it

Per-instrument, on Glyptodont: the wavepos cycle repeats every 1-10 rows, but
the accumulator **drifts by a nonzero amount per lap** (instruments 2/3/4/5/8/
10 measured at drift 6/1/2/4/20/3), so the OUTPUT never repeats. B8's
encoder therefore had to unroll until the output happened to realign — which
never happens inside any capture window. Cost: **median 1125 PULSETAB rows
per instrument** (max 1201; Fargo median 565) to express what Blackbird stores
in **one** row.

### What was built: lft's own structure, not a new table

The original scoping for this round guessed at "a parallel 1-byte-per-row
delta table." Reading `player.s` (lines 272-317) directly showed that guess
was wrong and that the real structure maps onto the shared engine far more
cleanly:

```
        ldy  v_wavepos,x
        lda  wavetable,y
        cmp  #$c0
        bcc  nojump
        adc  v_wavepos,x     ; (carry set by cmp) -> +1
        tay
        lda  wavetable,y
nojump  and  v_wavemask,x
        sta  $d404,x
        asl
        bpl  nopulse         ; bit6 of the waveform byte == "this row carries pulse"
        tya
        adc  #2              ; pulse row is TWO bytes wide
        sta  v_wavepos,x
        lda  wavetable+1,y   ; the delta lives INLINE, right after the waveform byte
        bmi  pwset
        adc  v_pwidth,x      ; bit7 CLEAR -> ACCUMULATE
        .byt $80             ; NOP #imm eats the following asl
pwset   asl                  ; bit7 SET  -> ABSOLUTE SET, doubled
        sta  v_pwidth,x
        tay
        lda  pwprepare,y
        sta  $d402,x
        sta  $d403,x
nopulse iny                  ; non-pulse row is ONE byte wide
```

`wavetable` is a single interleaved variable-width byte stream: a non-pulse
row is 1 byte, a pulse row is 2 (waveform, then delta inline), and **bit6 of
the waveform byte itself** is the "carries pulse" flag. This engine's WAVE
table is 2 columns of 256 with one row per frame, so the same information
lands in **col1 of the same row** — no new table, no second cursor, and the
pulse steps in lockstep with the wave row because it *is* the wave row.

Shipped:

- **WAVE col1 = the pulse delta**, encoded exactly as Blackbird encodes it
  (bit7 clear -> accumulate; bit7 set -> absolute, doubled by an `asl`).
- **`pwprepare` embedded** as `drivers_src/blackbird/pwprepare.inc`, read
  verbatim from each file's own template at offset 1024. The "byte-identical
  across every v1.2-exact rip" claim is now **asserted at build time**
  (`write_pwprepare` keeps a reference and fails loudly on any difference)
  rather than trusted. Measured shape, for the record — it is **not** the
  simple triangle it looks like: a descending -16 ramp with wrap
  discontinuities every ~17 entries (index 8 -> 15, 9 -> 254) plus plateaus,
  mirrored about 127/128 (`pw[i] == pw[255-i]` for all i; min 8, max 254).
  That non-affine shape is exactly why B8's output encoding could not close a
  cycle.
- **`PW_ACC`**, a per-voice 8-bit accumulator, stepped inside `wave_step`.
- **`pulse_step` DELETED** (-107 bytes), along with `VPC`/`VPLO`/`VPHI`/
  `VPADL`/`VPADH`/`PPTR_LO/HI`/`VIPUL_LO/HI` and the `PULSETAB` walk. Every
  instrument now gets a bare `$7f` program that dedups to one unread 3-byte
  entry.
- **Priming collapsed from 7 fields per voice to 2.** `PRIME_VWI` already
  positions the wave program, and the pulse program *is* the wave program —
  so the only genuinely per-voice runtime state left is the accumulator
  (`PRIME_PW_ACC`, straight from the snapshot's `v.pwidth`). This is an
  **exact** resume of the mid-sweep phase, i.e. B8's second named option
  arrives as a side effect of the first.
- A **build-time self-check**: after emitting col1, the builder replays the
  *driver's own arithmetic* over the column and requires it to reproduce the
  validated simulator's `$D402/$D403` byte on every frame of each program's
  unique span. This is what makes B9 exact-by-construction rather than
  exact-by-hope — a one-carry error fires at build time on the first
  instrument that exercises it instead of surfacing as unattributable lost
  percent.

### Two real bugs, both found by measuring rather than reasoning

**Bug 1 — WAVE col1 was NOT free, and "the translator only ever writes 0
there" is not the same claim.** col1 was described as free because the
translator has always emitted a literal `0x00` (Blackbird wave rows carry no
semitone offset; pitch is the separate fx/FM engine). But `wave_step` was
still **reading** it every frame as a signed semitone offset and adding it to
`vbasenote` — a `+0` is an invisible no-op, not an unused column. The moment
col1 carried pulse deltas, every pulse row silently transposed its voice by up
to +127 semitones. Measured on the first B9 build: **Fargo freq 87.7% ->
71.2%, overall 94.1% -> 80.9%**. The fix is not to move the delta but to
delete the read (`vbasenote + 0 == vbasenote`), which is exactly equivalent
for every Blackbird program ever emitted and is what makes col1 *actually*
free. Flagged in the driver source: this deletion is Blackbird-specific, and
the semitone column is a real shared-engine feature for any other fork.

**Bug 2 — `PW_ACC` priming alone is insufficient; the REGISTER needs priming
too.** Roughly half of both files' instruments have wave programs with no bit6
rows at all (B5's "freeze-only" case), so `wave_step` never writes `$D402/3`
for them — which on real hardware is correct and deliberate: the register
keeps whatever the last pulse-writing instrument left in it, possibly seconds
earlier. `do_init` clears the whole SID, so without priming the driver held a
hard 0 forever on those voices. Measured on Fargo before the fix: voice 2
(which does have pulse rows) was **0/400 frames mismatched — exact** — while
voices 0 and 1 were **400/400**, driver `$00` vs simulator `$08` on every
frame. Fixed with `PRIME_D402`, seeding the register once from the boundary
snapshot. B8 got the same effect indirectly via `PRIME_PULSE` -> `VPLO` ->
`pl_wr`'s every-frame rewrite; B9 writes it once, directly, which is what
hardware does.

### Results

**Fargo (1 part, unchanged)**:

| window | B8 | B9 |
|---|---|---|
| primary (0:200) | 96.8% (freq 88.1, wf 99.7, pulse 100.0, adsr 98.7, filter 100.0) | **96.8%** (freq 88.1, wf 99.7, pulse 100.0, adsr 98.7, filter 100.0) |
| full-part (0:3000) | 94.1% (freq 87.7, wf 98.9, pulse 89.6, adsr 98.8, filter 100.0) | **94.4%** (freq 87.7, wf 98.9, **pulse 90.8**, adsr 98.8, filter 100.0) |
| exact frames | 1182/3000 | **1230/3000** |

**Glyptodont (10 parts, `CAP_B=96`)**, frame-count-weighted full-part
aggregate:

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B8 | 67.3% | 62.2 | 90.5 | 16.8 | 94.6 | 92.5 |
| B9 | **82.7%** | 62.2 | 90.5 | **80.9** | 94.6 | 92.5 |

Per-part full-part overall, B8 -> B9: p1 73.7->**88.5**, p2 69.2->**83.0**,
p3 69.3->**82.2**, p4 66.4->**82.9**, p5 73.6->**85.1**, p6 68.2->**78.8**,
p7 62.1->**82.4**, p8 62.1->**78.5**, p9 62.7->**79.1**, p10 69.2->**84.7**.
Every part improved.

**freq, waveform, adsr and filter are byte-identical to B8 on both files** —
which is the expected signature of a change confined to the pulse path, and
is the check that says the gain is real rather than a re-tuning artifact.

**Table space**: Glyptodont's 10 parts total **399,552 -> 253,626 bytes
(-36.5%)**; Fargo's single part **45,142 -> 34,975 (-22.5%)**. `PULSETAB`
went from thousands of rows to one unread 3-byte entry.

### How exact is it, really — measured per voice, not asserted

Fargo, 3000 frames, per-voice `$D402` mismatches against the validated
simulator:

- **voice 0: 0/3000. voice 1: 0/3000.** Byte-exact for the entire window.
- **voice 2: exact for its first 2122 frames**, then runs exactly **one
  accumulator step** ahead for the remainder (824 mismatched frames).

The voice-2 slip was traced to a single instrument change. Instrumenting the
simulator's own `wavepos`/`pwidth` per frame shows the mechanism precisely: at
that frame `execute()` repositions `wavepos` to the new instrument's start
*before* `everyframe()` runs, so the outgoing program's `ADD +1` row never
executes. The driver triggers the same note one frame later — the
already-documented, architectural note-trigger skew, visible in the same dump
as a one-frame `$D40E` difference at exactly that frame — so it *does* run
that `ADD +1`, and is +1 ahead forever after.

This is worth stating plainly because it changes the shape of the residual
rather than the size: **the accumulator is exact, and it now INTEGRATES the
pre-existing trigger-timing skew.** Under B8's absolute encoding a trigger
slip was re-anchored by the next SET row; under B9 a single one-frame slip
permanently offsets the sweep phase. B9 trades "always approximately wrong"
for "exactly right until a trigger slips, then off by one step." On the
evidence above that is a large net win, but the pulse number is now **bounded
by the note-trigger timing model, not by the pulse representation** — so
further pulse work should target the trigger skew, not the encoding.

### The expected "fewer parts" win did NOT materialize — a negative result

The scoping for this round expected freed table space to reduce Glyptodont's
part count. It does not: **still 10 parts**, and the `CAP_B` sweep is
essentially unchanged from B8's. The reason is that B8 had already moved PULSE
off the FM bundle, so pulse rows stopped counting toward the only constraint
that actually binds (the 64-slot bundle cap). Freed WAVE/PULSETAB space is
real and shows up as 36.5% smaller files, but it was never the binding
constraint, so it buys no part-count reduction. Recorded so nobody re-derives
the expectation.

### The `CAP_B` sweep — the optimum MOVED, and now agrees on both files

Re-run because B9 changes what a part boundary costs. Glyptodont,
frame-count-weighted full-part aggregate, everything else identical:

| CAP_B | parts | overall | freq | wf | pulse | adsr | filter |
|---|---|---|---|---|---|---|---|
| 128 | 5 | 82.4 | 57.9 | 90.4 | **84.1** | 94.3 | 92.4 |
| **96** | **10** | **82.7** | 62.2 | 90.5 | 80.9 | 94.6 | 92.5 |
| 80 | 15 | 82.1 | 63.4 | 90.4 | 77.3 | 94.6 | 92.5 |
| 64 | 16 | 82.1 | **63.7** | 90.4 | 76.8 | 94.6 | 92.5 |

Under B8 this sweep was monotonic — more parts meant strictly better freq and
flat everything else, so the only cost of splitting was the part count itself
(B8 recorded "80 is the measured fidelity optimum if part count is no
object"). **B9 introduces a genuine opposing gradient**: every extra part is
another forced boundary re-trigger, and since the accumulator now integrates
trigger slips, pulse degrades monotonically as parts increase (84.1 -> 80.9 ->
77.3 -> 76.8) exactly as freq improves (57.9 -> 63.7). The two cross, and
**`CAP_B = 96` is now a strict local maximum in overall**, not a compromise
picked to limit file count.

**Fargo** stays 1 part and byte-identical at 128/96/80; at **64 it still
splits into 2 and still regresses hard: 94.4% -> 82.3%** (pulse 90.8 -> 67.4,
adsr 98.8 -> 84.2). So 64 remains disqualified on Fargo's evidence, unchanged
from B8.

**`CAP_B = 96` stays shipped** — and unlike B8, it is now the best measured
value on Glyptodont as well as the one that keeps Fargo whole, so the
"part count is a real cost the metric doesn't price in" caveat B8 needed to
justify it no longer has to do any work. Still `BB_CAP_B`-sweepable.

### What became LESS editable — stated plainly, not traded away quietly

The original scoping raised an editability concern about adding a custom
table, then withdrew it on the grounds that col1 is free so no new table is
needed. The first half is right and the second is only half right, so for the
record:

- **No new table was added.** The WAVE table remains a standard SF2II 256x2
  wave table and still renders and edits in stock SID Factory II. That is
  strictly better than a hidden driver-internal table (cf. ROMUZAK's
  FMTAB/PULSETAB, explicitly "no longer a render-in-editor table").
- **But col1's MEANING changed for Blackbird songs.** The stock editor labels
  and renders that column as the semitone/transpose column. In a B9 Blackbird
  SF2 it holds pulse deltas, so the editor will display arbitrary-looking
  transpose values, and a user editing that column will change the pulse
  width rather than the pitch. The column is visible and editable; it is
  mislabelled.
- **`wave_step` no longer applies a semitone offset at all** for this driver,
  so the transpose feature is genuinely unavailable in Blackbird songs (it was
  already unused — the translator always emitted 0 — but it is now
  structurally gone, not merely unused).

Net: nothing became invisible, one column became semantically mislabelled, and
one unused shared-engine feature became unavailable.

### Honest residuals — named precisely, not fixed

- **The note-trigger frame skew is now the binding constraint on pulse**
  (see the per-voice analysis above). It is the same architectural residual
  B1/B5/B8 all named; B9 makes its effect persistent rather than
  self-correcting. Fixing it means a cross-player timing-model change to the
  shared engine, unattempted here.
- **Freq (62.2% weighted on Glyptodont, 87.7% on Fargo) is now the largest
  remaining gap by a wide margin**, unchanged byte-for-byte from B8. Same
  causes as B8 named: the 1-frame FM lag plus the ~3-frame startup skew.
- **`exact frames` is still 0 per part on Glyptodont** despite the large pulse
  gain — every part still has at least one register off in every frame, which
  the freq residual alone is sufficient to explain.
- **The ADD carry-in fold is asserted, not proven for all inputs.** The
  driver's row space has no equivalent of hardware's `y`, so the ADD path's
  carry-in (from `tya; adc #2`) is folded into the stored delta at build time.
  This is exact because both `y` and the waveform byte's bit7 are fixed table
  properties. It has one unrepresentable code: an ADD whose folded delta lands
  on `$80` would be indistinguishable from an absolute SET of 0. Measured as
  **never occurring** (0 of 52 Fargo / 92 Glyptodont pulse-row x wavemask
  combinations; the carry itself is 1 in exactly 2 Glyptodont cases), and the
  builder raises rather than mistranslating if a future file hits it.
- **Only Fargo and Glyptodont are built.** The other 9 v1.2-exact files remain
  untouched, and `pwprepare`'s cross-file invariance is asserted only across
  those two so far.
- **Audio has NOT been listened to for any B9 output** — register trace only.
  Same caveat every round has carried.
- Unchanged from B6/B7/B8: `estimate_tempo_chain`'s Stage-A off-by-one, mode=0
  filter rows, part-boundary hard cuts, not wired into `DriverSelector`.

### Driver memory-map note

B9 reverses B8's memory pressure: deleting `pulse_step` (-107 bytes) and
collapsing 7 pulse prime fields to 1 reopened the low gap, so **all**
`PRIME_*_TAB`s and `tempo_sched_*` moved back below SF2II's reserved
`$16CC-$1702` region, and the two big fixed tables took the space above it:
`pwprepare` at `$1710-$180F`, `freqtable` moved `$1710 -> $1810`. `pwprepare`
is deliberately **not** page-aligned — alignment would force `$1800` and leave
`freqtable` no contiguous home below the state block; it costs one cycle on
indices that cross a page and nothing else.

Two guards were added rather than relying on reasoning, since B8's own trap
(a table landing on live state at `$1800`) corrupts at **runtime**, not at
assembly: a `.cerror` on the low gap overrunning `$16CC` and on `freqtable`
overrunning `$1980`, plus a new image check in
`bin/build_blackbird_driver_full.py`'s `assemble()` that the driver's private
state block `$1980-$19E1` is clear — the exact check whose absence let B8's
bug through.

Determinism re-verified: two from-scratch rebuilds produced byte-identical
sha1 for Fargo's part and all 10 Glyptodont parts.
`pyscript/test_blackbird_parser.py` stayed 9/9 (untouched).

## B10 shipped: the fx/PITCH interpolator runs in the driver (Glyptodont 10 parts -> 1, freq 66.6% -> 97.1%)

B9's move, applied to pitch. B9 replaced a stored pulse *recording* with lft's
own accumulator; B10 replaces the stored pitch *recording* with lft's own
`everyframe` fx interpolator (`player.s` 207-271), ported instruction-for-
instruction into `fx_step`.

### The problem B10 removes

The old `fm_step` stored, per program, a per-frame sequence of **absolute
frequency offsets** from a note's steady pitch. Those offsets are
**note-dependent** — Blackbird's frequency table is exponential, so the same
"+3 quarter-semitones" arp step is a different Hz offset at every pitch. So
every `(fx-program, note)` PAIR needed its own `$c0-$ff` command slot:

| | distinct fx programs (`nfx`) | slots the old encoding needed | clustered away |
|---|---|---|---|
| Fargo | 35 | 80 | 16 (20%) |
| Glyptodont | 47 | 423 | 359 (**85%**) |

What lft actually runs is note-independent: an fx program is a list of signed
**quarter-semitone** offsets, and the note enters only as `v_basepitch =
note*4`, added *before* a 4-mode interpolated table lookup. Run that
algorithm in the driver and a "program" is just an **fx index**.

### Result: clustering is not reduced, it is gone

| | slots before | slots after | merged |
|---|---|---|---|
| Fargo | 80 | **32** (of nfx=35) | **0** |
| Glyptodont | 423 (whole song) / 61-96 per part | **47** | **0** |

`cluster_bundles()` is deleted. `CAP_B` is now **completely inert**: sweeping
it 128 -> 96 -> 80 -> 64 -> 48 produces *byte-identical* output on both files
(B9's "96 is a strict optimum" finding no longer holds, because the constraint
it optimised no longer binds). It still *functions* — forcing `CAP_B=32`,
below Glyptodont's `nfx=47`, does still split into 3 parts — so this is a
non-binding cap, not dead code. The binding constraint is now `CAP_I=32`
instruments (Glyptodont uses 31).

### Part count: the round's headline goal, achieved

**Glyptodont: 10 parts -> 1.** Fargo stays at 1 part (the correctness anchor,
unchanged). Both songs are now a single SF2 with no hard cuts.

### Fidelity — measured on MATCHED frame coverage

Collapsing 10 parts into 1 **silently changes what gets measured** (10 parts x
~1425f covered the song; one part capped at 3000f covers ~14% of it). Quoting
the two default runs against each other would be meaningless, so `BB_FULL_CAP`
was added and **both builds were re-measured over the identical full-song
frame count**:

**Glyptodont, 20,223 frames (whole song), B9 10 parts vs B10 1 part:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B9 (10 parts) | 83.7 | 66.6 | 93.0 | 76.4 | 96.1 | 94.5 |
| **B10 (1 part)** | **91.4** | **97.1** | **93.5** | **77.7** | 96.1 | **94.7** |

**Fargo, 20,550 frames (whole song), 1 part both:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B9 | 77.1 | 90.3 | 76.9 | 52.0 | 74.0 | 99.9 |
| **B10** | **78.8** | **97.4** | 76.9 | 52.0 | 74.0 | 99.9 |

Nothing regressed in any category on either file. Fargo is a *pure* freq win
(every other category byte-identical). Glyptodont improves or ties everywhere
while also going 10 parts -> 1.

On the **historical default 3000-frame window** (the number prior B-rounds
quoted), for continuity: Fargo 94.4% -> **94.9%** (freq 87.7 -> 89.5);
Glyptodont 82.7% (10 parts, 14250f) -> **91.7%** (1 part, 3000f) — but that
Glyptodont pair is exactly the coverage-mismatched comparison described above,
so the 20,223-frame table is the honest one.

**Output also shrank 60%**: Fargo's SF2 34,975 -> 14,130 bytes (the ~1125-row
unrolled per-(fx,note) FMTAB programs are gone).

### The 1-frame note-trigger lag is gone by construction

`fm_step` existed to *accumulate* offsets, so `pr_note` had to write a flat
base pitch on the trigger frame and only start applying deltas the frame
after — the documented 1-frame lag. `fx_step` computes the **absolute**
frequency from `FXPOS` every frame, so there is no accumulator to prime and
nothing to lag. `pr_note` no longer writes `$D400/1` at all, exactly like
lft's `execute()`, which never touches the frequency registers.

**Measured, not assumed** — sweeping the driver trace +/-2 frames against the
simulator on Fargo, shift 0 is a strict local maximum on all three voices
(v0 86.7/87.8/**88.9**/88.0/87.0, v1 91.6/92.7/**93.9**/92.8/91.7, v2
78.0/79.9/**82.1**/80.1/78.4). No systematic pitch skew remains.

### Exact-by-construction gate

`verify_fx_engine()` replays the **driver's own arithmetic over the tables the
build actually emits** against the validated simulator's `$D400/$D401` and
`FXPOS`, for every frame of every (fx program, note) pair the file can
produce: **302,400 exact comparisons (Fargo), 705,600 (Glyptodont)**, checked
on every build. It is deliberately a model of the *asm against the emitted
blobs*, not a paraphrase of the simulator, so it is not a tautology.

Negative controls confirming it has teeth:

| injected fault | result |
|---|---|
| truncate FREQBLOB to the nominal 96-byte `freq_msb` | **fails** (IndexError) |
| flip ONE byte of a deliberate carry-bias table | **fails** (value mismatch, names fx/note/frame) |
| truncate FXTAB by one byte (drops the `+1` peek guard) | *passes* — neither file ever reaches `fxpos=$ff`, so the guard byte is defensive and **unexercised** |
| unmodified control | passes |

### The table-extent trap, handled

`fx_step`'s `freq_lsb+24,y` reads with `y` up to 127 run **151 bytes past
`freq_lsb`'s start** — past its own 111-byte extent and into `pwprepare`'s
region; `freq_msb+24,y` likewise runs into `freq_lsb`. lft documents the first
("tables overlap with 15 bytes", `player.s:692`); the second is just what a
16-bit indexed read does. So the three tables are emitted as **ONE contiguous
463-byte blob** (`FREQBLOB`, template offsets 817..1280 = `freq_msb` 96 +
`freq_lsb` 111 + `pwprepare` 256), with `freq_msb`/`freq_lsb`/`pwprepare` as
labels into it. B9's separate `pwprepare.inc` is **folded in, not
double-embedded**, and the build still asserts both that the blob is
byte-identical across files and that its `pwprepare` slice matches what
`BlackbirdSim` reads at offset 1024.

Verified placement (64tass label dump, not reasoning): `FREQBLOB=$1710`,
`freq_msb=$1710`, `freq_lsb=$1770`, `pwprepare=$17DF`, blob ends `$18DE`.
Highest reachable reads: `freq_lsb+24+127=$1807` and `pwprepare+255=$18DE` —
both inside the blob, both clear of the private state block at `$1980`. Low-gap
tables end `$1548` < `$16CC`. (B8's lesson: an overlap here corrupts at
*runtime*, not at assembly.)

### What was deleted

`fm_step` (~90 bytes), `FMTAB`, `IFM_LO`/`IFM_HI`, `FM_ON`/`FM_IDX`/`FM_CNT`/
`FM_ACC_*`/`FM_OFF_*`/`FMP_*`/`VIFM_*`, the `fmptr` zero-page pointer,
`vbasenote`, **and `freqtable`/`freqtable.inc` entirely** (it existed only to
give `fm_step` a base pitch; nothing reads it now — deleting it is also what
makes room for the blob below `$1980`). `unroll_fm()` and `cluster_bundles()`
are gone from the builder. Part-boundary priming collapsed from **eight
reconstructed FM fields per voice to two raw bytes** (`fxpos`, `basepitch`) —
the snapshot's state *is* the driver's state, so there is no lookup to get
wrong and no "couldn't resolve, fall back to flat" failure mode left (which on
Glyptodont used to fire regularly).

### Editability — what changed, honestly

- **Unchanged from B9**: WAVE col1 still carries pulse deltas, so the
  transpose column still has no stock-editor meaning. B10 did not restore it.
- **Improved**: the `$c0-$ff` command column used to hold an opaque
  per-`(fx, note, instrument)` bundle index whose number meant nothing outside
  one build. It is now **Blackbird's own fx-program number** — a stable,
  note-independent identity, so editing it selects a real arp/vibrato program
  and the same value means the same thing across parts and files.
- **Note column semantics preserved**: `pr_note` subtracts `NOTE_OFS` (=9,
  Stage A's user-verified calibration, now emitted into `layout.inc` from the
  single constant `SF2_NOTE_OFS` rather than duplicated as a literal). Note
  names still display correctly.
- **No new cost**: `FXTAB`/`FXSTART`/`FXRST` live above `gen.filter_addr`,
  outside the region declared to SF2II — exactly where `FMTAB` lived. SF2II
  renders WAVE/PULSE/FILTER/INSTR/SEQ only, and that set is unchanged.
- **Still not editable** (pre-existing, not introduced here): the pitch/arp
  program itself. Blackbird's `fxtable` uses its own jump encoding and is not
  a declared SF2II table.

### Punch list (honest)

1. **fx changes on a rest or tie are DEFERRED to the next note onset.** On
   hardware, `prepare1` sets `pendfx` from the fx byte itself, so `execute()`
   repositions `fxpos` even with no note that tick. The driver's command
   column only acts at `pr_note`. Measured: **57/208 fx changes (27%) on
   Fargo, 100/1448 (7%) on Glyptodont** land on a non-note step. This is the
   dominant remaining freq residual and it explains the *shape* of it — Fargo
   has ~4x the deferred fraction and correspondingly worse freq in the short
   window (89.5% vs Glyptodont's 97.6%). Fixing it is a sequence-format
   change (let the command act on non-note rows), not a pitch-engine change.
   Diagnostic support: at every freq-mismatched frame on Fargo, the waveform
   register **matches** (0% co-occurrence, all 3 voices) — so the voice is not
   sequence-desynced; only `FXPOS` timing differs.
2. **Fargo's pulse (52.0%) and adsr (74.0%) over the full song are weak** and
   B10 did not touch them — the 3000-frame window flatters both (90.8/98.8).
   Untouched by this round; quote the window.
3. **The FXTAB `+1` guard byte is unexercised** by either file (see the
   negative-control table). It is defensive only.
4. `CAP_B` is retained but inert; if a future file has `nfx >= 64` the build
   **raises** rather than silently clustering — a note-independent fx
   clustering pass does not exist.
5. Still only Fargo + Glyptodont; the other 9 v1.2-exact files are untried.
   Still not wired into `DriverSelector`. Still no audio listening test.

## B11 shipped: fx changes on rest/sustain rows commit same-tick, Fargo freq 97.4% -> 100.0%, Glyptodont 99.7%

B10's punch list item 1, fixed. This closes the dominant remaining freq
residual named at the end of that round.

### The bug, precisely, from `player.s` itself (not paraphrased)

Real hardware's `prepare1` (`player.s:80-110`) writes `v_pendfx,x` **directly**
from a fresh `$c9-$f8` fx-select byte on ANY row — note, rest, or sustain —
whenever one is present in that tick's stream position:

```
no_oob
        sbc     #$c8-1
        bcc     no_fx
        inc     `zp_bufs,x
        sta     v_currfx,x
        sta     v_pendfx,x        ; <-- direct write, independent of note/delay
no_fx
```

`execute()` (`player.s:441-445`), which runs unconditionally every real tick
for all 3 voices, applies whatever is in `v_pendfx` and then unconditionally
clears it back to 0:

```
        ldy     v_pendfx,x
        beq     no_fx
        lda     fx_start-1,y
        sta     v_fxpos,x
no_fx
        ...
        lda     #0
        sta     v_pendfx,x        ; <-- cleared every tick, note or not
```

Separately, `prepare3` (`player.s:167-200`) has its OWN unconditional
re-mirror of `v_pendfx = v_currfx` — but only on the branch reached by a
genuine note byte (`lda (zp_bufs,x); bmi got_delay` — delay/rest bytes take
`got_delay` and skip the mirror entirely, confirmed by tracing prepare2's
consumption of Blackbird's own `$80` gate-off byte, which lands the FOLLOWING
byte — always a delay code — in front of prepare3, never a note). That
mirror is what makes every note **restart** the current program from its own
top, restart discipline the native driver already had right since B10 (the
`pn_tied` commit block, unconditional on every note). What was missing is
the OTHER path: `prepare1`'s **direct**, same-tick write on rows that aren't
notes at all.

The native driver's `pr_setprog` handler (`blackbird_driver.asm`) already ran
on every row regardless of note/rest — it correctly staged the new program
into `VIFXS`/`VIFXR` either way — but the actual **commit** into `FXPOS` (the
`v_fxpos` analog) only ever happened inside `pn_tied`, reached exclusively
from a genuine note byte. A select that landed on a rest ($00 gate-off) or
"+++"-sustain (`$7e`) row sat staged and unapplied until whatever note came
next — exactly the "deferred to next note onset" bug B10 named and measured
(57/208 = 27% of Fargo's fx changes, 100/1448 = 7% of Glyptodont's).

**A second, independent instance of the same bug was found on the translator
side while fixing this** (not by re-reading — found by tracing where the
row-emission logic actually attaches command bytes): `bb_steps_for_voice`
(`bin/build_blackbird_native_song.py`) already carries the correct sticky
`cur_fx` value on every step kind, rest and sustain included — but
`steps_to_rows_native`, the function that turns that step list into actual
`D11Row`s, only ever checked "did the fx index change?" inside its NOTE
branch. A change that happened to land on a rest or sustain step was silently
dropped from the emitted sequence bytes entirely — so even after fixing the
driver's commit logic, the fix would have had nothing to commit on those rows,
since the `$c0-$ff` command byte was never written into the sequence in the
first place. Both halves were required together; fixing only one would have
been a no-op.

### The fix

**Driver** (`drivers_src/blackbird/blackbird_driver.asm`): a new per-row flag
`fxflag` (zero page `$ec`, reusing the byte B10 freed when it deleted
`fm_step`'s `fmptr`), reset once per row alongside the existing `pending_dur`
reset, set by `pr_setprog` whenever it fires. A new `maybe_fx_commit`
subroutine — `if fxflag && VIFXR: FXPOS = VIFXS` — is called from both
non-note terminal paths (the gate-off branch of `pr_note`, and the `pn_adv`
trampoline shared by `+++`-sustain and the reserved-skip range). `pn_tied`
(the note path) is untouched: its unconditional commit already matches
`prepare3`'s unconditional note-triggered mirror and needs no `fxflag` gate.

**Translator** (`bin/build_blackbird_native_song.py::steps_to_rows_native`):
the "did the fx index change?" check was hoisted out of the note-only branch
to run once per step regardless of kind, so a change landing on a `rest` or
`note-with-note=None` (sustain) step now emits its `D11Row` with
`command=cmdcol` set, exactly like a note step already did. No packer change
was needed — `galway_driver11_emitter.py`'s shared `_event_tokens` already
starts a new token whenever `row.command is not None`, regardless of what
the row's `note` byte is; that generic (cmd?)(instr?)(dur)(note) token shape
was already correct for every other player using Driver 11, Blackbird just
wasn't using it on non-note rows.

### Results (same whole-song methodology as B10 — `BB_FULL_CAP` set to each
file's own full length, so before/after compares the identical window)

**Fargo, 20,550 frames, 1 part:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B10 | 78.8 | 90.3→97.4 | 76.9 | 52.0 | 74.0 | 99.9 |
| **B11** | **79.4** | **100.0** | 76.9 | 52.0 | 74.0 | 99.9 |

**Glyptodont, 20,223 frames, 1 part:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B10 | 91.4 | 97.1 | 93.5 | 77.7 | 96.1 | 94.7 |
| **B11** | **92.0** | **99.7** | 93.5 | 77.7 | 96.1 | 94.7 |

A pure, isolated freq win on both files — every other category byte-identical
to B10, exactly as predicted by the residual's own diagnostic (waveform
already matched at every freq-mismatched frame, so the fix couldn't touch
anything but `FXPOS`/`$D400`/`$D401` timing). Fargo's freq is now **exact**
(100.0%) on the full 20,550-frame song, not just the 200-frame primary
window. Glyptodont's residual 0.3% is presumably the reserved-skip-range
($70-$7d) case, which per B10's own note is unexercised by either file's
current note range — most likely a genuinely separate few-frame source, not
re-investigated this round (small enough that it wasn't worth chasing given
the honest residuals named below dwarf it).

The `verify_fx_engine()` self-check (B10's exact-by-construction gate) is
**unaffected and still passes at full count** on both files (302,400 Fargo /
705,600 Glyptodont comparisons) — expected, since it tests the fx
interpolator's own arithmetic in isolation, not the row-timing of when a
program gets selected, and neither of those changed here.

### Honest residuals — not fixed this round, named precisely

1. **Fargo's pulse (52.0%) and adsr (74.0%) over the FULL song remain
   untouched** — same numbers as B10, this round never touched either engine.
2. **Glyptodont's freq is 99.7%, not 100%** — a small residual whose source
   was not chased down (see above); worth a quick look if ever revisiting fx
   timing specifically.
3. Still only Fargo + Glyptodont. Still not wired into `DriverSelector`.
   Still no audio-listening test on the native driver's output.
4. The reserved `$70-$7d` skip range in `pn_adv` is still unexercised by
   either file (same as B10's `+1` guard byte finding) — defensive coverage,
   not a known-good path.

## B12: instrument-select restarts commit same-tick (ADSR/GATE/FILTER only) — Fargo 79.4%→79.5%, Glyptodont ADSR 96.1%→96.2%

Targeted B11's own named next residual: Fargo's full-song pulse (52.0%) and
adsr (74.0%). Root-caused via a per-frame/per-register diagnostic harness
added to the build script this round (`BB_DIAG_BIN`/`BB_DIAG_LO`/
`BB_DIAG_HI`/`BB_DIAG_REG` env vars, `report_binned`/`report_registers` in
`bin/build_blackbird_native_song.py`) — kept in the shipped script as a
permanent, opt-in diagnostic, not removed after use.

### Two genuinely different bugs were found under one "adsr/pulse is weak" symptom

Binning Fargo's whole-song comparison every 2000 frames showed something a
single aggregate percentage hides completely: waveform/pulse/adsr degrade
steadily from frame ~2000, then **flatline at an exact constant (66.7% /
33.6% / 66.7%) from frame 8000 clear through to the end of the song** — a
signature of a PERMANENT desync, not a slowly-growing drift. freq stayed
**100.0%** throughout the entire binned sweep, which rules out any row/tempo
scheduling misalignment (that would skew freq identically, since B11 made
freq a direct per-frame recomputation with no memory of prior ticks).

Per-register breakdown at the flatline (frames 8000-10000) split this into
two independent, unrelated findings:

1. **Voice 2: a full, permanent instrument-state desync** (ctrl/AD/SR/pulse
   all wrong, pulse *actively drifting* while the simulator's stays
   constant) — root cause **not found this round**, see Honest Residuals.
2. **Voice 1: pulse phase-shifted by exactly one real frame**, constant rate
   otherwise (both simulator and driver step the pulse accumulator by the
   same $10 every 2 real frames — B12's own diagnostic dump at
   frames 5125-5169 shows this precisely: `sim=98,98,a8,a8,...` vs
   `drv=88,98,98,a8,...`, i.e. driver's transitions land exactly one frame
   late, not at a different rate).

### Root cause of (2), verified against `player.s` directly

`prepare2` (`player.s:117-160`) reads AT MOST one instrument/gate-off/legato
byte per real tick, and `prepare3` (SAME tick, chained via the shared
`preparejmp` dispatch) then reads WHATEVER byte comes immediately after it —
note or delay, doesn't matter. So an instrument-select is **never** "several
ticks before the next note" on hardware — it is always exactly one tick
before whatever the very next stream byte is. `execute()`'s vloop
(`player.s:447-497`) then restarts WAVE/FILTER/ADSR/GATE on **every tick
`v_pendins` holds a real instrument value — independent of note/delay**.

A raw byte-level trace of Fargo voice 1 (bytes #362-369) confirmed this
directly: a standalone instrument-select byte (`$88`, INSTR=5) sits sandwiched
between two delay/hold bytes with no note anywhere near it, followed several
ticks later by a *tied* note. On the native driver, the WAVE+FILTER+ADSR
restart lived exclusively inside `pn_note`'s untied-note branch — so this
standalone select was silently deferred, and because the note that finally
consumed it was **tied**, the restart never fired at all.

A second, independent bug compounded this: `bb_steps_for_voice`
(`bin/build_blackbird_native_song.py`) only ever cleared `pending_instr`/
`pending_tie` inside its `'note'` branch — so both could survive across
*multiple* intervening delay/rest steps and land on a note many ticks later
that they never actually belonged to (exactly the traced example: a legato
byte from one standalone tick and an instrument-select from a different one,
both incorrectly bundled onto the same much-later tied note). Both halves
had to be fixed together, same as B11's fx bug.

### The fix

**Translator**: `pending_instr`/`pending_tie` now attach to the row created
by the very next event of ANY kind (note OR delay), not just notes, mirroring
`prepare2`+`prepare3`'s same-tick pairing exactly. `steps_to_rows_native`
now tracks `cur_instr` uniformly across rest/hold/note branches (same
pattern as B11's `cur_cmd` fix), so an instrument change landing on a
rest/hold row is no longer dropped from the emitted sequence.

**Driver**: `set_instr_v` (`pr_setinst`'s handler) now writes GATE ($ff,
forcing the gate on) and, if the instrument's flag `$40` is set, restarts
the FILTER program immediately — matching `execute()`'s same-tick,
note-independent restart. ADSR was *already* written immediately in
`set_instr_v` (unchanged from B8/B9), so that half needed no code change,
only the diagnosis to confirm it wasn't the source of the desync.

**Measured, not assumed — VWI (the wave-row cursor) was deliberately left
OUT of this immediate restart**, even though `player.s`'s SAME `ins_done`
block also unconditionally writes `v_wavepos,x = ins_wave-1,y`. Restarting
VWI immediately in `set_instr_v` DID fix the same ctrl/AD/SR mismatches, but
ALSO regressed Fargo's whole-song pulse 52.0%→50.0% (net worse than doing
nothing). Removing just that one line kept every ctrl/AD/SR gain and left
pulse at its pre-B12 baseline (52.0%→51.6%). The exact mechanism wasn't
chased further this round — see Honest Residuals. `pn_note`'s own
restart-on-untied-note is unchanged and remains the only place VWI is reset.

### Results (same whole-song `BB_FULL_CAP` methodology as B10/B11)

**Fargo, 20,550 frames, 1 part:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B11 | 79.4 | 100.0 | 76.9 | 52.0 | 74.0 | 99.9 |
| **B12** | **79.5** | 100.0 | **77.0** | 51.6 | **74.7** | 99.9 |

**Glyptodont, 20,223 frames, 1 part:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B11 | 92.0 | 99.7 | 93.5 | 77.7 | 96.1 | 94.7 |
| **B12** | 92.0 | 99.7 | 93.5 | 77.7 | **96.2** | 94.7 |

A small, real, no-regression win on both files. The B10 `verify_fx_engine`
self-check still passes at full count on both (302,400 Fargo / 705,600
Glyptodont comparisons) — expected, this round never touched the fx engine.

### Honest residuals — not fixed this round, named precisely

1. **Voice 2's full instrument-state desync (starting ~frame 8000 in
   Fargo) is still completely unexplained** — this is the dominant reason
   Fargo's whole-song pulse/adsr numbers stay low. Diagnosed only as far as
   "permanently wrong, not drifting, unrelated to the (1)-class bug this
   round fixed" — a real live-trace investigation (in the style of B8/B9's
   original pulse work) is needed, not another read of `player.s`.
2. **Why removing VWI's restart from `set_instr_v` measurably helps is not
   understood, only measured.** A future round revisiting this should get
   a fresh live hardware trace around a standalone-instrument-select event
   specifically, rather than re-deriving from `player.s` alone (which reads,
   on its face, as if VWI restart SHOULD be needed there).
3. Fargo's pulse/adsr are still weak over the full song (51.6%/74.7%) —
   this round improved adsr's mechanism but the dominant residual (voice 2's
   desync, item 1) swamps the gain in the aggregate number.
4. `BB_DIAG_BIN`/`BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG` are now permanent,
   opt-in diagnostics in `bin/build_blackbird_native_song.py` — useful
   starting points for whoever picks up residual 1.

## B13 shipped: gate-off immediately before a note doesn't silence forever — Glyptodont 92.0%→97.6% (pulse 77.7%→99.7%)

Prompted by a direct observation that Glyptodont (92.0% overall) is nowhere
near 100% either, despite B11/B12's Fargo-focused work. The B12 diagnostic
tools (`BB_DIAG_BIN`/`BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG`) found a
DIFFERENT shape of residual than Fargo's: waveform/AD-SR/filter actually
reach **exact 100.0%** for the back half of Glyptodont's song (frames
12000+) — the real problem is narrow, concentrated almost entirely in
**voice 2's pulse** (`$D410`/`$D411`), which goes permanently wrong starting
around frame 10165 and never recovers.

### Why a live trace, not more `player.s` reading

Every fidelity number quoted this whole session (B1 through B12) compares
the native driver against `bin/blackbird_everyframe_sim.py` — the Python
simulator — as ground truth. That simulator was only ever validated against
**real hardware** (via the `vsid-trace.js` VICE wrapper) over the **first
1200 frames** of each song. Frame 10165 was never covered by that original
validation. Before chasing a "driver bug" further, the honest first question
is: does the simulator ITSELF still match real hardware that deep into the
song, or has *it* drifted?

### Method

`node scripts/dev/vsid-trace.js Glyptodont.sid --frames 10300 --json
--changed-only` (from the separate `sid-reference-project` repo) captured a
genuine VICE-emulated hardware trace through frame 10300 (a real ~3.4-minute
emulated playthrough, run in the background — this is not instant). The
`--changed-only` write-event list was reconstructed into full per-frame
25-register snapshots (SID reset state = `$00`, matching
`sidm2-sid-trace.exe`'s own convention) so it's directly comparable to the
simulator's/driver's own `frames` arrays. A frame-offset sweep (±10 frames)
against the first 300 frames found a clean, unambiguous peak at offset 0
(96.3% match — not 100%, expected: this is a far stricter full-snapshot
comparison than the original validation's write-*sequence* comparison,
which tolerates a 1-cycle frame-boundary misattribution that a snapshot
comparison does not). The SAME offset was re-confirmed as the local optimum
specifically around frame 10000-10300 too (92.0% at offset 0 vs 46-75% at
any other tested offset) — ruling out cumulative drift as an explanation
for anything found there.

### Finding 1: the simulator IS still correct for voice 2 here — the driver bug is real

Real hardware vs. simulator, frames 10000-10300: voice 2's freq/waveform/
pulse/AD-SR/ctrl are **100.0%** identical. This confirms the B12-era
driver-vs-simulator comparison was measuring the right thing for voice 2 —
the driver's divergence is a genuine driver bug, not an artifact of a stale
simulator.

### Finding 2: the driver's own bug, pinned to the exact frame, against real hardware directly

**Superseded below** — this "restart" framing turned out to be built on an
incomplete read of the driver's own trace (the VWI-restart write is real,
but it's a SEPARATE, correctly-legitimate event, not THE actual bug; see
"The actual root cause" further down, which corrects this). Kept here
un-edited as the genuine investigative trail, not because it's the final
answer.

Driver vs. real hardware (not simulator), voice 2 pulse, frame-by-frame:

```
frame 10165: real=$3b drv=$3b
frame 10166: real=$2b drv=$2b
frame 10167: real=$0b drv=$0b
frame 10168: real=$ea drv=$0b   <-- driver fails to step
frame 10169: real=$ca drv=$0b   <-- driver fails to step AGAIN
frame 10170: real=$aa drv=$ea   <-- driver resumes, now 2 frames behind real
frame 10171: real=$8a drv=$ca
...
```

The driver's pulse accumulator holds its value for **two consecutive real
frames** (10168, 10169) where real hardware steps normally, then resumes
stepping at the correct per-frame rate — permanently 2 frames behind for
the rest of the song (89.3% match over the following 300 frames, all of it
this same fixed 2-frame offset, not a growing drift). Crucially,
**voice 2's waveform byte ($D404-equivalent) stays 100% correct through the
same frames** — ruling out a full wave-cursor (VWI) freeze; whatever's
wrong is narrower than that (most likely: the driver's WAVE table has the
right waveform byte but a different col1 pulse-delta at the specific row(s)
visited here than real hardware's own program has — i.e. a built-table
content issue rather than a runtime cursor-tracking issue, though this is
not yet confirmed).

**Correlated event** (via `row_frame`/`steps_per_voice`, same technique
B12 used): frame 10165-10170 lands on a run of four very short (1-tick)
notes on voice 2 — the first untied (a genuine restart), the following
three all tied (no restart, per `pn_note`'s existing correct tie-gating).
Not yet confirmed as causal, only correlated — the actual WAVE-table bytes
for the active instrument around this row have not yet been inspected.

### Finding 3 (bonus, unrelated to what was being chased): the SIMULATOR has its own latent bug on voices 0/1/filter, discovered by the same trace

Real hardware vs. simulator, frames 10000-10300, voices 0 and 1 plus the
filter registers: **NOT** 100% — `v0pwlo`/`v0pwhi` (52.3%/50.0%),
`v0ctrl` (76.7%), `v1freqlo`/`v1freqhi` (95.7% each), `v1pwlo`/`v1pwhi`
(81.7%/81.3%), plus intermittent single-frame filter mismatches
(`fcuthi`/`fresfilt`/`modevol` all 99.3%, isolated one-frame swaps at
frames 10188/10258). This is a genuine simulator defect, never previously
known, since B1-B12's own validation only ever exercised the first 1200
frames. **Not investigated further this round** — it's a separate bug from
voice 2's pulse issue (which the SAME trace confirms the simulator gets
right), flagged here so a future round doesn't quietly keep trusting the
simulator as ground truth past frame ~1200 without re-checking.

### Update, same session: live 6502 tracing narrowed the mechanism (later corrected further below)

Pushed further with `py65` (the same headless CPU emulator the build script
already uses for `headless_trace`) single-stepped through the exact critical
frame, plus a 64tass `--labels` dump to resolve raw PCs to source labels.
This is real, verified progress — the root cause is now understood in much
finer detail than "somewhere near row 2034" — but still no fix.

**The row correlation was off by one.** Careful frame-exact analysis (voice
2's own `vsp_lo`/`vsp_hi`/`vhold` zero-page state, read directly from
memory) showed the restart is triggered by **row 2033** (`note=32,
command=5 [fresh fx-select], tie=False` — a genuine untied note), NOT row
2034 as B13's first pass assumed. Rows 2034-2036 (the tied run) are
downstream and correctly untouched — B13's original "correlated with a
tied-note run" theory was wrong in its specifics, though right that
something in this neighborhood is the trigger.

**The restart itself is legitimate and self-consistent.** Single-stepping
frame-by-frame caught the exact two writes: `pn_note`'s untied-restart path
(PC inside `pn_not_off`) writes `VWI,x = $44` (`INSTR_WAVE[18] = $44`,
confirmed by dumping the driver's own compiled `INSTR_WAVE` table and
matching the value), then `wave_step`'s own advance (PC inside
`ws_nopulse`) immediately steps it to `$45`. This is real hardware-mirroring
behavior, not a spurious restart: `player.s`'s `execute()` restarts
`v_wavepos` unconditionally whenever a real instrument-select is consumed —
exactly what should happen here. The driver's own captured WAVE table for
instrument 18 (`$44`=waveform `$81`/no-pulse, `$45`=`$81`/no-pulse,
`$46`=`$41`/pulse+2, `$47`=`$41`/pulse+2 self-looping) is **internally
self-consistent** with the 2-frame freeze the driver produces (two
non-pulse "settle" rows before the pulse row resumes) — this matches
`unroll_wave_pulse`'s own build-time self-check, which already validates
this exact table byte-for-byte against the simulator for one full lap in
isolation.

**The real discrepancy**: the *continuous*, whole-song simulator
(`run_full_song_sim`, independently confirmed matching real hardware
byte-for-byte in this exact window) shows only a **single half-sized
pulse step** at this same restart (`$3b`→`$2b`, half the usual ~$20 swing),
not a full 2-frame freeze. So two different code paths inside
`bin/blackbird_everyframe_sim.py` — the isolated per-instrument capture
`unroll_wave_pulse` uses (which seeds a throwaway `BlackbirdSim` with
`wavemask=0xFF`, `pwidth=0` and simulates fresh from `wave_start`) and the
continuous whole-song `everyframe()` a live restart actually goes through —
produce measurably different behavior for the first couple of frames after
a restart. `_pulse_col1`'s carry-folding math (`eff = pdelta + c_from_wp`,
designed to make a driver-side `col1 + acc` reproduce `everyframe()`'s real
`adc(pdelta, pwidth, c_from_wp)`) checked out algebraically and the
`wavetable()`/`wavemask` inputs looked identical in both paths on paper —
the exact remaining difference was not isolated before this round ran out
of runway.

### The actual root cause: pushed one more step, and it wasn't the wave engine at all

Following the "next concrete step" above (instrument `run_full_song_sim`'s
continuous simulation frame-by-frame around the restart) immediately
overturned the whole "restart" framing. `vs.wavepos` for voice 2 **never
changes** across this entire window — no restart happens on real hardware
at all. What actually happens is `vs.pendins` becomes `$FE` (the gate-off
sentinel) and `vs.wavemask` flips to `$FE` a couple of frames later: this is
a **gate-off event**, not an instrument restart.

Tracking voice 2's own raw-byte read cursor (`sim.v[2].rpos`) confirmed the
exact sequence, one byte per real frame: `$cd` (fx-select, `prepare1`),
`$80` (**gate-off**, `prepare2`), `$2f` (note=23, `prepare3`) — three
separate real frames, each one real hardware's own SEPARATE per-frame
pipeline stage (`prepare1`→`prepare2`→`prepare3`→`execute`, one stage per
real frame, confirmed directly in `blackbird_everyframe_sim.py`'s
`real_frame()` — a correction to this investigation's own earlier working
assumption that all four stages fire within a single frame).

`player.s`'s `prepare3` (167-200) is unconditional about updating
`v_pendnote` from a note byte regardless of what preceded it — but it only
overwrites `v_pendins` from `v_currins` when `v_pendins` is STILL 0
(`if vs.pendins == 0: vs.pendins = vs.currins`). Since the gate-off already
set `v_pendins = $FE` this same tick, that guard is false, so `pendins`
stays `$FE` all the way to `execute()`, which for `$FE` does `v_wavemask,x
= $FE` and **nothing else** — no wave/filter/ADSR restart, note value
completely discarded except for basepitch bookkeeping that has no audible
effect while gated off.

**The actual bug**: `bb_steps_for_voice` sets `gate_is_off = True` on a
gate-off byte, but only ever *checks* that flag in the `'delay'` branch —
the `'note'` branch ignored it entirely, always emitting a genuine active
note regardless of a directly-preceding gate-off. So `[gate_off][note]`
(exactly Glyptodont's row 2033: `$cd $80 $2f`) was silently treated as a
normal restart instead of "voice goes silent, note value discarded."

### The fix, and the regression that caught a SECOND bug in the same code

First attempt: check `gate_is_off` in the `'note'` branch too, matching the
`'delay'` branch's existing check. Rebuilding immediately regressed
Glyptodont from 92.0% to **73.2%**, freq alone dropping to 71.3% — far too
large to be the one row this was meant to fix. Counting `[gate_off]→[note]`
pairs across the whole song (with no other bytes in between) found why:
**14-45% of every voice's notes** matched that naive pattern, not the rare
handful expected.

The `'delay'` branch has *always* had a companion bug, just harmless until
now: it checks `gate_is_off` but never resets it afterward. On real
hardware, `v_pendins` resets to 0 in *every* `execute()` call, and
`prepare1/2/3` are all skipped for a voice during a multi-tick delay's own
hold (`v_trtimer` negative) — so a gate-off's silencing effect genuinely
only covers the ONE event immediately following it. Once a delay's own
countdown expires, the next event gets a fresh `prepare2` examination, and
for a note byte specifically, `prepare2`'s own "got_note: reuse currins as
pendins" implicit-repeat-instrument path **automatically restarts the
gate** — independent of any earlier, unrelated gate-off several delay-ticks
back. The old code let `gate_is_off` silently ride across an unbounded run
of delay events until whatever note finally arrived, over-applying "stays
silent" to nearly every voice's typical delay-then-note phrasing. Both
branches now reset `gate_is_off = False` unconditionally after consuming it
— the same one-event-only consumption discipline B11/B12 already
established for `pending_instr`/`pending_tie`.

### Results (same whole-song `BB_FULL_CAP` methodology as every prior round)

Re-verified the fix scope first: with the corrected same-event-only model,
`[gate_off]→[note]` pairs (no intervening delay) drop to 0.0-5.2% of notes
per voice — a plausible rare pattern, not a third of the song.

**Glyptodont, 20,223 frames, 1 part:**

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B12 | 92.0 | 99.7 | 93.5 | 77.7 | 96.2 | 94.7 |
| **B13** | **97.6** | 99.5 | **95.5** | **99.7** | 96.2 | **95.2** |

**Fargo, 20,550 frames, 1 part:** 79.5%→79.2% (freq 100.0%→99.7%, everything
else within noise) — essentially unchanged, confirming Fargo's own
still-unexplained voice-2 desync (B12's honest residual) is a **genuinely
different bug**, not the same root cause. The two are both voice-2 and both
pulse-shaped, which is why this was worth checking, but they are not the
same fix.

The B10 `verify_fx_engine` self-check still passes at full count on both
files (302,400 Fargo / 705,600 Glyptodont comparisons) — this round never
touched the fx engine. `pyscript/test_blackbird_parser.py`'s full 9/27
subtests still pass.

### Honest residuals — not fixed this round

1. **Fargo's voice-2 desync (from ~frame 8000, permanent) is still
   completely unexplained** — this fix does not touch it (verified: no
   change). Needs its OWN live-trace investigation, following the exact
   same method this round used (real-frame-exact `rpos`/internal-state
   tracing, not just register-output diffing).
2. Glyptodont's freq dipped very slightly (99.7%→99.5%) — not chased down,
   likely a minor side effect of the row-count/timing shift from
   reclassifying some rows from 'note' to 'rest'; small enough not to be
   worth pursuing given the size of the pulse win.
3. The bonus B13-recon finding (the simulator itself diverging from real
   hardware on Glyptodont voices 0/1/filter past frame ~1200) is
   **unrelated to this fix and still unresolved** — see "Finding 3" further
   up this section.
4. Only Fargo + Glyptodont built natively. Not wired into `DriverSelector`.

**Audio-listened, same session, after this fix**: the user loaded the
rebuilt Glyptodont SF2 into a real SID Factory II instance
(`pyscript/sf2_open_in_editor.py`, succeeded on attempt 3 of its usual
flaky retry loop) and reported it "sounds really close. something with the
perc or drums." — the first real listening test of the NATIVE driver's
output (Stage A's flatter output was the only thing ear-tested before
this). Tracks the numbers: waveform (95.5%) and filter (95.2%) are the two
categories still short of 100% post-B13, and percussion/noise sounds lean
hardest on exactly those; freq (99.5%) and pulse (99.7%, what B13 fixed)
aren't what drives percussive timbre.

## B14 shipped: instrument-index overflow (Fargo's true root cause) — Fargo 79.2%→92.7%

Prompted by continuing to push on Fargo's own voice-2 desync (open since
B12, confirmed by B13 as a genuinely different bug from Glyptodont's).
Applied the exact same method that cracked B13: relocate the exact onset
frame with `BB_DIAG_BIN`/`BB_DIAG_LO`/`BB_DIAG_HI`, then instrument
`BlackbirdSim`'s own internal per-voice state (`wavepos`/`wavemask`/
`pendins`/the raw byte cursor `rpos`) around it, rather than stopping at a
driver-vs-simulator register diff.

### Root cause: a real, hard format limit hit for the first time

Fargo locates `nins=35`. A live trace of a genuine instrument-select event
at real-frame ~7945 (raw byte `$a4`, decoding to raw instrument index 34)
showed `BlackbirdSim` correctly restart with `currins=$22`(34 decimal) — a
real, distinct instrument. But `bb_steps_for_voice` computed this SAME
event's driver-side instrument index as `min(max(b - 0x83, 0), 31)` — a
**direct clamp to 31**, not a remap. Instrument indices 32/33/34 (all
genuinely used later in the song, confirmed by a direct count of every
`'instrument'`-classified byte across all 3 voices: **35 distinct raw
indices actually used**, matching `nins`) all silently aliased onto
instrument 31.

This was not merely a wrong command byte: `build_range` used the SAME
clamped value to index the RAW source tables directly
(`d[(lay.ins_wave - la) + i]` etc.) — so a note using real instrument 33
played instrument 31's actual wave/ADSR/filter program instead. Once an
untied note relying on the "sticky repeat current instrument" mechanism
(no fresh instrument-select of its own) followed, the substitution
persisted for the rest of the voice's remaining notes — explaining the
"permanent from this point onward" shape B12 first measured.

**Why `fits()`'s own resource check never caught this**, despite `CAP_I=32`
already existing specifically to trigger B6's adaptive part-splitting for
exactly this class of overflow (the same mechanism that already handles
Glyptodont's bundle-count limit): `used_instr` was built from the
ALREADY-CLAMPED `s.instrument` values, which can never exceed 32 by
construction — the check was measuring a quantity that was mathematically
incapable of ever reporting an overflow, regardless of how many distinct
instruments the song actually used.

**A second under-counting bug, found while fixing this**: `used_instr`
(and `used_fx`) were only scanned from `kind == 'note'` steps — but B11/B12
already made `steps_to_rows_native` emit fx/instrument commands on
rest/hold rows too (a command doesn't need a note to apply). A standalone
instrument-select landing on a rest/hold row was invisible to the resource
count, causing a `KeyError` in the new remap once clamping no longer
silently absorbed it.

### The fix

Three coordinated changes, `bin/build_blackbird_native_song.py`:

1. **`bb_steps_for_voice`**: no longer clamps — passes through the true
   raw instrument index (`max(b - 0x83, 0)`, no upper bound).
2. **`build_range`**: builds a genuine per-part DENSE remap
   (`instr_remap = {raw: slot for slot, raw in enumerate(sorted(used_instr))}`)
   and uses it everywhere a raw index used to be used directly as a driver
   table slot — `wave_programs`/`pulse_of_instr`/`filter_programs`/
   `filter_flag_of`/`wave_stats_by_instr`/`filter_extra_by_instr` (now
   keyed by slot, not raw index), `prime_instr_of_voice`/`filt_owner_instr`
   (B7 priming's own instrument references), and `windowed_steps`' own
   `s.instrument` field (via a new `_remap_step_instrument` helper,
   producing remapped `BBStep` copies before `steps_to_rows_native` runs).
   A part genuinely needing more than 32 distinct instruments now raises
   loudly on a real build — `fits()`'s `count_only` probe sees the same
   `len(used_instr)` overflow and correctly rejects the window first, so
   B6's existing part-splitting shrinks it before this is ever reached.
3. **`used_instr`/`used_fx` counting**: now scans every step regardless of
   `kind`, matching what B11/B12 already made the row-builder emit.
4. **`main()`**: the song-wide `ad_sr` (AD/SR byte pairs, cheap, no
   unrolling) is no longer capped to 32 at extraction time — that used to
   truncate `lay.nins > 32` files before `build_range`'s own per-part
   remap ever got a chance to select which instruments fit a given part's
   own budget. `build_range` now builds a **part-scoped** `part_ad_sr`
   (indexed by driver slot, matching the other remapped tables) instead of
   passing the full song-wide list into `gen_includes_song`.

For Glyptodont (31 raw instruments, already under the cap), this remap is
a no-op — `instr_remap[i] == i` for every `i`, since `sorted(used_instr)`
is already the contiguous range it always was.

### Results (same whole-song `BB_FULL_CAP` methodology as every prior round)

Fargo now genuinely needs 2 parts (this is B6's adaptive splitting
correctly firing for the first time on Fargo, not a bug — a `used_instr`
overflow across the WHOLE song's single window, resolved once split):

| | overall | freq | waveform | pulse | adsr | filter |
|---|---|---|---|---|---|---|
| B13 (1 part) | 79.2 | 99.7 | 77.5 | 50.3 | 74.7 | 99.9 |
| **B14 (2 parts)** | **92.7** | **99.6** | **98.1** | **71.1** | **99.6** | **100.0** |

Glyptodont: **byte-identical to B13, 97.6%** (confirmed no regression;
`instr` count in the build log moved 31→32, purely from the used_instr/
used_fx under-counting fix now correctly including a rest/hold-row
reference that was always there, not a behavior change).

The B10 `verify_fx_engine` self-check still passes at full count on both
files. `pyscript/test_blackbird_parser.py`'s full 9/27 subtests still pass.

### Honest residuals — not fixed this round

1. **Fargo's pulse is still the weakest category (71.1%)**, up hugely from
   50.3% but not resolved — likely a distinct, uninvestigated bug (or
   several), not yet traced the way B13's Glyptodont pulse issue was.
2. **Fargo's part 2 shows a rough startup** (primary-200f window 93.0%,
   freq 92.3%) — likely the SAME class of part-boundary priming edge case
   B7/B8 chased for Glyptodont's own multi-part era, not re-investigated
   here since B10 already collapsed Glyptodont back to 1 part and this is
   the first NEW multi-part Fargo build.
3. Fargo now ships as **2 separate SF2 files**
   (`Fargo_native_part01.sf2`/`_part02.sf2`), not 1 — a genuine, correct
   consequence of the true instrument count, but anything downstream that
   assumed "Fargo is always 1 part" needs updating.
4. The B13-recon bonus finding (simulator diverging from real hardware on
   Glyptodont voices 0/1/filter past frame ~1200) remains unrelated and
   unresolved.

## B15 shipped: native driver extended to the full 11-file v1.2-exact corpus

Same session, prompted directly ("maybe time for more lft songs"). Nothing
new was fixed here — this is a coverage extension, running the
now-more-robust pipeline (B14's instrument-overflow fix made this safe to
try cold) against the 9 v1.2-exact-bucket files that had never been built
natively before (only located/Stage-A-covered). All 9 built successfully,
first try, no crashes, no exceptions, every B10 `verify_fx_engine`
self-check passing at full count:

| File | Overall | Freq | Waveform | Pulse | ADSR | Filter | Parts |
|---|---|---|---|---|---|---|---|
| Thus_Spoke_the_PC_Speaker | 98.9% | 100.0% | 96.6% | 100.0% | 97.2% | 100.0% | 1 |
| Maple_Leaf_Rag | 98.8% | 100.0% | 96.0% | 100.0% | 97.0% | 100.0% | 1 |
| Euclid_Was_Here | 98.3% | 99.9% | 93.7% | 100.0% | 96.2% | 100.0% | 1 |
| Dishwasher_Groove | 97.5% | 99.4% | 97.3% | 100.0% | 95.8% | 93.8% | 1 |
| Fargo (B14) | 92.7% | 99.6% | 98.1% | 71.1% | 99.6% | 100.0% | 2 |
| Glyptodont (B13) | 97.6% | 99.5% | 95.5% | 99.7% | 96.2% | 95.2% | 1 |
| Elvendance | 95.3% | 99.2% | 95.8% | 100.0% | 97.4% | 79.1% | 1 |
| Into_the_Unknown | 95.4% | 99.9% | 96.1% | 89.2% | 97.9% | 93.5% | 3 |
| Toy_Rocket | 95.1% | 99.4% | 93.9% | 87.5% | 95.7% | 99.8% | 1 |
| Dithered_Island | 92.7% | 99.9% | 95.7% | 75.3% | 96.5% | 99.8% | 2 |
| Revolutions_Delivered | 91.4% | 99.6% | 77.7% | 92.9% | 95.6% | 81.1% | 1 |

All 11 v1.2-exact-bucket files now have a working native Stage-B build,
ranging 91.4%-98.9% overall (mean ~95%). Multi-part splitting (B6's
adaptive mechanism, now correctly triggered by B14's true instrument-count
fix) fired automatically for 2 of the 9 new files (Dithered_Island: 2 parts,
Into_the_Unknown: 3 parts) — nobody had to intervene.

## B16: real ins_restart hard-restart mechanic ported (verified correct, zero regression) — did NOT explain Fargo's pulse residual

Next session, picking up the handoff's own #1 recommendation: chase Fargo's
71.1% pulse residual (the weakest category on either individually-
investigated file) using the exact live-trace method that cracked B13/B14.

### The investigation

- `BB_DIAG_BIN=2000`/`BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG` (B12's
  diagnostics) located the residual precisely: part 2's pulse match is a
  ROCK-STEADY 66.7% (=4/6 pulse registers, i.e. exactly ONE whole voice
  wrong) across nearly the ENTIRE 13,553-frame part — not degrading like
  part 1. `$D409`/`$D40A` (voice 1's pulse width) alone measured 5.2% in a
  300-frame window; voices 0/2 are pulse-perfect.
- Per-frame values showed a clean, deterministic signature from frame 50
  onward: `drv[frame] == sim[frame-1]` (driver trails the simulator by
  exactly one row-step, forever) preceded by one genuinely wrong glitch
  value at frame 49.
- **Ruled out priming (B7/B8) as the cause**: instrumented `row_state`/
  `PRIME_PW_ACC`/`PRIME_VWI` directly and rebuilt with a wrapped
  `build_range` to capture the real (non-`count_only`) part-2 build. The
  primed values were exact, and a fresh 300-frame trace showed driver and
  simulator match FRAME-FOR-FRAME for frames 0-48 — the divergence begins
  at a specific, later runtime event, not at part-start.
- Traced `BlackbirdSim`'s own internal state (`wavepos`/`wavemask`/
  `pendins`/`currins`) plus the raw byte-stream cursor around real frame
  7049 (F0+49): an instrument-change cluster (raw bytes `0x8d`/`0x39`/
  `0x98`/`0x38`, instrument 11 → instrument 22) sits right at the onset.
- Reading `player.s`'s ported `prepare2`/`execute()` in
  `blackbird_everyframe_sim.py` surfaced a mechanic **entirely absent from
  the native driver** (`grep -c ins_restart blackbird_driver.asm` was 0
  before this round): `_pr2_noteback` conditionally forces `$D406,x=0`+
  `wavemask=$FE`, and `execute()`'s own instrument-select path conditionally
  forces `$D406,x=$0f` (`>= ins_restart2+1`) and/or `$D405,x=0`+`$D404,x=1`
  (`>= ins_restart+1`) as a clean-slate pre-step before committing the
  instrument's real AD/SR — a genuine hard-retrigger technique, gated on
  comparing the instrument index against two per-song thresholds
  (`ins_restart`/`ins_restart2`, read from the SID binary at `po+93`/
  `po+512`). `set_instr_v` (the driver's instrument-select handler) just
  unconditionally applies AD/SR with zero threshold logic.

### The fix (real, shipped, verified byte-exact where it applies)

Ported the threshold-gated hard-restart into `set_instr_v`
(`drivers_src/blackbird/blackbird_driver.asm`), matching `execute()`'s
lines 359-380 (`blackbird_everyframe_sim.py`) — MINUS the `wavepos`
restart line, which B12 already proved regresses pulse when added
literally (see B12's own section above; not re-litigated here). Threading
detail: `ins_restart`/`ins_restart2` are RAW source instrument indices,
but the driver only ever sees B14's per-part REMAPPED slot number.
`build_range` now converts both thresholds into this part's own slot space
once, at build time (`instr_remap` is order-preserving, so "highest slot
whose raw index is `<=` threshold" is exact), emitting
`INS_RESTART_SLOT`/`INS_RESTART2_SLOT` via the same `PRIME_GLOBAL_FIELDS`
per-part-constant mechanism `F_IDX` etc. already use. **Gotcha caught
before shipping**: the constant must be emitted as the ALREADY-INCREMENTED
CPY operand value (`(slot+1) & 0xFF`), not the raw threshold with a `+1` in
the assembly — 64tass ERRORS ("too large for a 8 bit unsigned integer")
rather than wrapping when a part where every used instrument needs the
restart hits the `255+1=256` case; computing the `+1` in Python and masking
sidesteps this entirely. First attempt hit exactly this on
`Dithered_Island` (the only one of the 11 corpus files where it actually
occurred) — caught by the full-corpus verification pass, not by Fargo/
Glyptodont alone.

Verified DIRECTLY (not just via the aggregate metric, which is too coarse
to show a 1-2-frame register blip): compared voice 1's `$D40B`/`$D40C`/
`$D40D` (ctrl/AD/SR) frame-by-frame across the exact transition that
motivated this round — driver and simulator match EXACTLY, including the
`$0x40`→`$0x41` ctrl transition at the transition frame. This confirms the
port is correct where it fires.

### The negative result (equally important — a real, verified rule-out)

Rebuilt the full 11-file corpus with the fix: **every file's numbers are
BYTE-FOR-BYTE IDENTICAL to the B15 baseline table above** — the fix causes
zero measurable change anywhere, including Fargo's own pulse (still
71.1%). This is a genuine, informative negative result, not a failed
build: the ins_restart mechanic only ever touches `$D404`/`$D405`/`$D406`
(ctrl/AD/SR), never the WAVE-ROW CURSOR (`VWI`) or `PW_ACC` — and the
direct voice-1 ctrl/AD/SR comparison above showed those registers were
ALREADY matching before this fix, for the SPECIFIC transition under
investigation (this instrument's own ctrl/AD/SR happened to already be
right; the fix is real and will matter for OTHER instruments/files where
the pre-fix values didn't coincidentally match, but doesn't apply to
Fargo's own residual).

**This also sharpens the actual diagnosis**: since voice 1's `$D40B` (ctrl,
computed by the SAME `wave_step` routine, same `VWI`-indexed `WAVE` table,
same real frame) matches EXACTLY through the whole transition while
`$D409`/`$D40A` (pulse, `WAVE+256,y` — the SAME row's OTHER column) does
not, the WAVE-ROW CURSOR itself must be correct (or B13/B14's fixes would
have shown up as ctrl mismatches too). The bug is narrower than "pulse
cursor timing" — it must be in the PULSE-SPECIFIC computation within
`wave_step` (the `pwprepare,y`/`PW_ACC` accumulate-vs-absolute math) or,
more likely given the STATIC per-row delta encoding, in `_pulse_col1`'s
build-time carry-fold (`bin/build_blackbird_native_song.py`) — the comment
there notes the fold assumes "both y and the waveform byte's bit7 are
FIXED table properties of the row, not runtime state," which may not hold
if this WAVE program is visited from more than one distinct real-hardware
context across the song. **Not yet fixed — this is the next concrete lead
for Fargo's own residual**, narrower and better-evidenced than where B14's
own handoff left off (its recommendation to consider a "PULSE-specific
table-overflow" class of bug is now superseded by this direct-register-
comparison finding).

**Read as a corpus, not a leaderboard**: every file still carries its own
uninvestigated residuals (Revolutions_Delivered's waveform 77.7% and
filter 81.1%, Elvendance's filter 79.1%, several files' pulse in the
75-92% range) — none of these have had the live-trace treatment B13/B14
gave Glyptodont/Fargo. This table is a BASELINE for future per-file work,
not a claim that any of these 9 are individually fully understood.

### Honest residuals — not fixed this round

1. None of the 9 new files have been individually root-caused — this
   round only confirmed they BUILD, not that their remaining gaps are
   understood.
2. None have been audio-listened (only Glyptodont has, pre-B14).
3. Not wired into `DriverSelector` — still deliberately out of scope for
   all 11 files.
4. The ~16 near-v1.2-variant files (older birdcruncher tool versions) and
   the ~7 much-older/uncertain files remain completely out of scope —
   `locate_blackbird()` still correctly rejects them, no work has started
   on supporting a different template.

## B17 shipped: the real Fargo pulse root cause — a missing VWI restart for instrument-select-without-note rows — broad corpus win, not just Fargo

Same session, immediately following B16's negative result. User said "push through with py65 single-stepping" — deployed the heavier tool B13 itself used (a labeled py65 single-step trace, not just register-output diffing) rather than continuing to hand-trace the Python simulator's own internals.

### The investigation

- Set up a standalone script: capture the exact `(prg, edit)` pair `build_range` produces for Fargo's part 2 (via a wrapped `build_range` capturing the real, non-`count_only` call), assemble with `64tass --labels` to get a PC→symbol map, then single-step py65 through the driver's own `do_init` + 49 quick `do_play` frames, then single-step frame 49 (the exact frame the B16 investigation had already isolated) WITH logging: every time the PC lands on a new label, print voice 1's `VWI`/`VGMASK`/`PW_ACC`/`$D40B`/`$D409`.
- Hit and caught two of my own indexing slips before the trace was trustworthy: (1) an early script advanced the simulator's OWN Python instance to real frame 0 but mislabeled its output as frame 7043+ (never actually sought there — the loop just ran from frame 0 and the print statement's label lied); (2) the single-step driver trace needed 49 quick frames before detailed logging, not 48 — off-by-one first landed one frame early (which coincidentally still matched, masking the bug for one attempt).
- The corrected trace showed the ACTUAL row-dispatch for this tick: `pr_setinst`→`set_instr_v` fires (a genuine fresh instrument-select — `VGMASK` flips `$fe`→`$ff` immediately, matching B12's own "commit ADSR/GATE/FILTER immediately" finding), but the row's own note-slot byte is `pn_adv` (a "+++"-sustain/skip byte, NOT a genuine untied note) — so `pn_not_off`'s own VWI-restart code (`lda VIWAVE,x; sta VWI,x`, the ONLY place VWI ever gets reset, per B12's own comment) never runs. `VWI` stays wherever the OLD instrument's own wave program left it, silently continuing the WRONG program under the NEW instrument's ADSR/gate — exactly matching the observed symptom (ctrl "looks fine" for a while since consecutive WAVE rows often share the same byte; pulse desyncs immediately since it's the one column that varies every row).
- Root cause, precisely: real hardware's `execute()` resets `wavepos = ins_wave[y-1]` UNCONDITIONALLY whenever `pendins` holds a genuine instrument value — independent of whether a fresh note ALSO fires that same tick (confirmed directly against the ALREADY-TRUSTED Python simulator: it genuinely resets `wavepos` to the instrument's row 0 at this exact tick, then advances one step in the SAME frame). B12 already found (the hard way, regression-tested) that restarting VWI unconditionally inside `set_instr_v` is WRONG — but that's because it DOUBLE-restarts the far more common "instrument-select together WITH a fresh untied note" case (once via `set_instr_v` naively, again via `pn_not_off`'s own restart). B12 stopped at "leave VWI alone in set_instr_v" without finding the narrower, correct middle ground: restart it in `set_instr_v` ONLY when nothing else is going to.

### The fix — B11's exact `fxflag` pattern, applied to VWI

Added `viwiflag` (`$b9`, reusing the byte freed since B9 deleted `pulse_step`'s indirect pointer): reset to 0 once per row at `vparse` (alongside `fxflag`'s own reset), set nonzero by `set_instr_v` on every genuine instrument-select (`viwiflag` is a "restart still owed" marker, not a "this happened" marker — it may go stale/unconsumed for the common case, harmlessly, since `vparse` resets it clean next row regardless). Added `maybe_vwi_commit` (mirrors `maybe_fx_commit` exactly): if `viwiflag` is set, restart `VWI` from `VIWAVE,x` and clear the flag; called from BOTH `pn_adv` (the "+++"/sustain path) and `pr_note`'s `$00`/gate-off path — the SAME two call sites `maybe_fx_commit` already uses, for the SAME underlying reason (a non-note row can still carry a fresh select that must commit immediately, not wait for whatever note eventually follows). `pn_not_off`'s own untied-note restart is UNCHANGED — for the common case, it still does the ONE restart that's needed, and `viwiflag`'s own stale value is simply never consumed.

### Result: broad corpus win, not a Fargo-only fix

Rebuilt all 11 corpus files. **Every file improved or held steady — zero regressions anywhere**, and several jumped dramatically:

| File | Overall (B16→B17) | Pulse (B16→B17) |
|---|---|---|
| Fargo | 92.7%→93.9% | 71.1%→**76.1%** |
| Glyptodont | 97.6%→97.6% | 99.7%→99.7% (unchanged) |
| Thus_Spoke_the_PC_Speaker | 98.9%→98.9% | 100.0%→100.0% |
| Maple_Leaf_Rag | 98.8%→98.8% | 100.0%→100.0% |
| Euclid_Was_Here | 98.3%→98.3% | 100.0%→100.0% |
| Dishwasher_Groove | 97.5%→97.5% | 100.0%→100.0% |
| Elvendance | 95.3%→95.3% | 100.0%→100.0% |
| Into_the_Unknown | 95.4%→**97.4%** | 89.2%→**96.6%** |
| Toy_Rocket | 95.1%→**98.1%** | 87.5%→**100.0%** |
| Dithered_Island | 92.7%→**98.6%** | 75.3%→**100.0%** |
| Revolutions_Delivered | 91.4%→**95.2%** | 92.9%→**99.8%** |

Four of the 9 previously-uninvestigated B15 files (Into_the_Unknown, Toy_Rocket, Dithered_Island, Revolutions_Delivered — exactly the ones with meaningfully sub-100% pulse in the B15 table) jumped to 96.6-100% pulse from this ONE fix, confirming the "instrument-select landing on a non-note row" pattern is common across the corpus, not a Fargo idiosyncrasy — B16's own hypothesis-narrowing work (ruling out priming, ins_restart, and cursor-vs-value framing) is what made this precise, targeted fix possible instead of another blind guess.

**Fargo itself only partially recovered** (pulse 71.1%→76.1%, not 100%) — part 2's PRIMARY window (first 200 frames) is now a perfect 100.0% pulse match (up from 79.5%), proving the fix is correct where it applies, but the FULL-part window is still only 68.2% pulse (up from 66.9%), meaning Fargo has at least one MORE, still-unidentified pulse-affecting issue later in part 2 — not yet investigated. `pyscript/test_blackbird_parser.py`'s full 9/9 suite still passes.

Committed as (see git log for the exact hash) and pushed.

## B19/B20 investigation (same session, continued — NOTHING shipped, both reverted): Fargo's remaining pulse gap is a NEW bug class; the filter row0 fix has a real, still-unexplained rapid-restart interaction

User asked to pursue both open threads from the B16-B18 handoff to completion, then commit. Neither reached a safe, ship-ready state — both investigations produced real, verified new understanding, documented here so a future round starts further ahead rather than re-deriving it.

### Fargo's own pulse gap (68.2% full-part, post-B17) is NOT a B17-class missing-restart bug

Traced the onset (driver frame 584, voice 1) via the same live-BlackbirdSim method. Confirmed the underlying event IS a genuine "instrument-select landing on a non-note row" case (same shape as B17's original bug) — but a labeled py65 single-step trace showed the driver's OWN row-dispatch (`do_row`) does NOT fire on the frame where the simulator commits the corresponding restart; voice 1 is still mid-`vhold` on that exact frame. This means the driver's row commit is landing on a DIFFERENT real frame than the simulator's — a genuine frame-alignment/timing discrepancy, not a missing code path. Likely candidate: this part's tempo is very short (chain `[7]`, i.e. 2-real-frames-per-tick), and per the session's own established model (`critical_context`: real hardware spreads `prepare1/2/3/execute` across separate real frames, one stage per frame) a 2-frame tick cannot fit all 4 stages — meaning `execute()` fires every tick regardless of whether `prepare1/2/3` have progressed far enough to have read this tick's own event yet. The native driver's row-based dispatch (one commit per row, not spread across ticks) has no equivalent mechanism for this, and could plausibly drift by exactly one frame under sustained short-tempo play — which would explain the "off by one, forever" signature exactly. **Not confirmed, not fixed** — this needs either a targeted trace of the tempo/tick bookkeeping specifically, or accepting it as an inherent limitation of the row-based architecture for very short tempos. Different bug class than anything B11-B18 already found; do not assume B17's own fix pattern (`viwiflag`) applies here.

### The filter row0 fix (B18's own hypothesis) is very likely CORRECT in principle, but has an unexplained interaction under rapid restarts

Re-derived and re-verified the CORE finding: `unroll_filter`'s row0 must respect its TRUE source classification (`is_set_prefix[0]`) instead of always forcing SET — confirmed AGAIN independently on Elvendance (filt_start=**11**, not 14 as B18's own writeup mistakenly used — 14 is merely the self-loop tail one row downstream of the true restart target; `filt_owner` freezes at restart time while `zp_filtpos` keeps advancing, so reading `zp_filtpos` well after a restart gives the WRONG position to test — this is the actual bug in B18's own methodology, not the underlying hypothesis).

Reapplied the fix and traced Revolutions_Delivered's own regression precisely: its 8000+ region has FOUR DIFFERENT filter-owning instruments (positions 4, 21, 25, 29) restarting the SAME shared filter in rapid rotation (~every 8 frames). Verified EACH ONE's own row0 classification and delta computation independently — all correct in isolation (owner 4 = genuine SET to a fixed 0x84, confirmed by the simulator itself always landing there regardless of history; owner 21 = genuine ADD +2, confirmed exactly matching the observed 0x84→0x86 and 0x50→0x52 deltas; owner 29 = genuine SET to $D0, confirmed the simulator ITSELF briefly shows exactly $D0 at the same frame). Despite every individual piece checking out, the built driver gets PERMANENTLY STUCK at owner 29's own SET value ($D0) instead of continuing to cycle through the rotation the way the simulator does. Root mechanism not found — likely something about how repeated restarts interact with `F_CNT`/`F_IDX` bookkeeping specifically under this rapid-fire pattern, not yet isolated via single-step trace (this specific case wasn't single-stepped — the per-owner-in-isolation checks above were all done via `unroll_filter`'s own build-time walk, not a live driver trace; that's the natural next step for whoever picks this back up).

**Both reverted** (`git checkout -- bin/build_blackbird_native_song.py`, confirmed clean against `c30079e`). Fargo rebuilt afterward to restore `.inc` artifact state. Nothing new committed this round — see `whats-next.md` for the prioritized continuation.

## B21 shipped: the REAL Fargo pulse root cause — `steps_to_rows_native` was deduping "sticky repeat" instrument reselects as no-ops, dropping them from the native track entirely

Picked up the B19/B20 handoff's item 1 (Fargo's remaining pulse gap). The handoff's own leading hypothesis — a tempo/tick frame-alignment mismatch, "execute() outruns prepare1/2/3" for very-short-tempo parts — was **directly disproven** this round: a live simulator trace of Fargo part 2's actual tempo values (not the assumed constant `7`) showed the real schedule alternates `35`/`42` (7/6 real frames per tick) with clean period-2 XOR-groove alternation, resynced correctly at every explicit tempo-schedule record. A driver-side py65 trace of `ROW_CNT`/`TEMPO_SCHED_IDX`/`CUR_TEMPO`/`CUR_TEMPO2` confirmed the assembled driver's row-tick cadence tracks the simulator's **exactly**, frame-for-frame, through and past the divergence point — ROW_CNT=84 fires at real frame 584, matching the simulator's `row_frame[1284]-F0=584` precisely. The tempo/tick model was never the bug.

The real cause was one level up, in Stage A's own step→native-row translation. `bb_steps_for_voice` correctly attaches `pending_instr` to whatever event follows an instrument-select byte in the raw stream (B12's own fix), but `steps_to_rows_native` (this module) applied a SECOND, incorrect dedup on top of that: `if s.instrument is not None and s.instrument != cur_instr` — silently treating a re-select of the SAME instrument index already active as a no-op, emitting no instrument command at all for that row. Real hardware's `execute()` (player.s 447-457) does not compare values: ANY genuine instrument-select byte unconditionally resets `wavepos = ins_wave[y-1]` (back to the instrument's own row 0), sets `wavemask=0xff`, and recommits AD/SR — a same-value "sticky repeat" reselect is a real, audible restart (typically used to force a wave/pulse program back to its start mid-note), not a value-comparison no-op.

Confirmed precisely via a live `BlackbirdSim` trace: Fargo voice 1's `currins` holds at `6` continuously from real frame ~7500 through ~7650, yet the decoded stream re-issues an explicit `pendins=6` select at row 1283→1284 (real frame 7584 — exactly the frame the B19/B20 py65 trace flagged: driver still mid-`vhold`, no `do_row` dispatch label fires for voice 1, `VGMASK1` never flips). The reselect's own duration was being silently folded into the PRECEDING held note's row (a plain `D11Row(note=SF2_GATE_ON)` continuation with `instrument=None`), so the driver never saw a command byte to dispatch and just kept holding the earlier note — precisely the observed symptom, previously misdiagnosed as a timing/frame-alignment issue.

**Fix**: removed the `!= cur_instr` gate in `steps_to_rows_native` (`bin/build_blackbird_native_song.py`) — every non-`None` `s.instrument` on a step now emits its own instrument command, regardless of whether it matches the previously-active value. `bb_steps_for_voice` already guarantees `s.instrument` is only non-`None` on the ONE step immediately following a genuine select byte in the source stream (never a stale/sticky carry-forward), so this cannot introduce spurious commands on rows that didn't have one.

**Result**: rebuilt the full 11-file corpus (`BB_FULL_CAP=999999`, matching this session's established discipline). Fargo alone changed — **93.9%→99.8% overall, pulse 76.1%→100.0%**, adsr 99.6% (unchanged), freq 99.6% (unchanged), filter 100.0% (unchanged) — every OTHER file in the corpus was byte-for-byte IDENTICAL to its B17-committed numbers (Glyptodont 97.6%, Thus_Spoke 98.9%, Maple_Leaf_Rag 98.8%, Euclid_Was_Here 98.3%, Dishwasher_Groove 97.5%, Elvendance 95.3%, Into_the_Unknown 97.4%, Toy_Rocket 98.1%, Dithered_Island 98.6%, Revolutions_Delivered 95.2% — zero regressions anywhere). Fargo is now the best-scoring file in the whole corpus. 9/9 `pyscript/test_blackbird_parser.py` tests still pass.

The filter row0 rapid-restart bug from B19/B20 (item 2) remains open and unshipped — untouched this round; see B19/B20's own section above for the exact next step (a live py65 single-step of Revolutions_Delivered's rapid-restart window, not more static `unroll_filter`-only analysis).

## B22 shipped: the filter rapid-restart freeze (B19/B20 item 2) — TWO real bugs, both fixed together: row0's SET/ADD classification, and a voice-processing order mismatch for the one genuinely shared (non-per-voice) resource

Picked up B19/B20's item 2 immediately after B21. Reapplied the row0 fix B19/B20 had reverted (`unroll_filter`'s row0 must respect `is_set_prefix[0]` instead of always forcing SET; added `_filter_row_delta(sim, pos)` computing the ADD delta straight from `filttable(pos+2)`, independent of whatever cutoff a restart inherits — both exactly as B19/B20's own writeup specified). Alone, this reproduced the SAME known regression: Revolutions_Delivered's filter dropped 81.1%→71.2% (Dishwasher_Groove and Elvendance's filter both IMPROVED from the same change, 93.8%→95.6% and 79.1%→81.6% respectively — confirming the row0 hypothesis itself was correct all along, exactly as B19/B20 concluded).

Root-caused the regression via a live py65 write-trace on `F_IDX`/`F_CNT` (not just PC-based label watching, which missed `pn_not_off`'s own inline filter-restart — there's no dedicated label for it): found the driver's filter engine gets stuck reloading the SAME 2-row `(SET $D0, jump-back)` loop for ~120 real frames, then jumps to a DIFFERENT program 93 frames later than the simulator's own `filt_owner` trace says it should. Cross-referencing a live `BlackbirdSim` per-voice `pendins`/`currins` trace at the exact real frame (8475) pinned the mechanism precisely: **two voices restart the shared filter in the SAME row-tick** — voice 0 selects instrument 29 (`ins_filt[28]=4`) and voice 1 selects instrument 30 (`ins_filt[29]=29`) simultaneously. `BlackbirdSim.execute()` (player.s's own real commit order) processes voices `(2, 1, 0)` — voice 0 LAST, so its value (`filt_owner=4`) wins the tie. `do_row`'s own per-voice loop in `blackbird_driver.asm` processed `0, 1, 2` — the OPPOSITE order — so voice 1's value won instead: the driver picks the WRONG owner whenever two voices contend for the filter in one tick, not just a wrong cutoff value.

**Fix**: reversed `do_row`'s voice loop in `drivers_src/blackbird/blackbird_driver.asm` from `ldx #$00 / inx / cpx #$03 / bne vloop` to `ldx #$02 / dex / bpl vloop`, matching `execute()`'s own `(2, 1, 0)` order exactly. Everything else `parse_one` touches is per-voice-indexed (`VWI,x` / `VGMASK,x` / `SID+4,y` via `sidoff`) and genuinely order-independent — the filter engine (`F_IDX`/`F_CNT`/`F_MODE`/`F_CLO`/`F_CHI`/`F_ACT`) is the ONE truly global resource written from inside the per-voice loop (by both `set_instr_v` and `pn_not_off`'s inline restart), so this reorder only changes same-tick filter-contention outcomes, nothing else.

**Result**: rebuilt the full 11-file corpus with BOTH fixes together. **Revolutions_Delivered: filter 81.1%→97.1%, overall 95.2%→97.7%** — the regression is gone and the file is markedly better than its ORIGINAL B17 baseline, not just restored to it. Dishwasher_Groove (97.5%→97.8%, filter 93.8%→95.7%) and Elvendance (95.3%→95.7%, filter 79.1%→81.6%) both improved further. Every other file (Fargo, Glyptodont, Thus_Spoke, Maple_Leaf_Rag, Euclid_Was_Here, Into_the_Unknown, Toy_Rocket, Dithered_Island) is byte-for-byte identical to its B21 numbers — zero regressions anywhere in the corpus. 9/9 tests pass.

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
  as the formula oracle). **As of B9 (see that section for the full trail)
  Fargo builds a loadable SF2 at 94.4% overall register-match** over a
  3000-frame window vs the simulator (filter 100.0%, AD/SR 98.8%, waveform
  98.9%, pulse 90.8%, freq 87.7%, 1230/3000 frames byte-exact), and
  **Glyptodont at 82.7% weighted over 10 parts** (B8: 67.3%) -- B9 ported
  Blackbird's pulse-width ACCUMULATOR into the driver (WAVE col1 = the
  delta, `pwprepare` embedded, `PW_ACC` per voice), byte-exact on 2 of
  Fargo's 3 voices across the whole window and bounded thereafter by the
  note-trigger timing skew rather than by the pulse encoding; the figures
  quoted in the rest of this paragraph are the historical B1-era ones
  (69.6% overall, pulse ~1%) and are kept because the bug trail below
  refers to them and models the song's FULL row-indexed mid-song
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
- **B11** (fx-on-rest/sustain commits same-tick, both driver AND translator
  fixed together — see "B11 shipped" above): whole-song overall now **Fargo
  79.4% / Glyptodont 92.0%**, both a pure freq win (Fargo freq now **exact,
  100.0%**; Glyptodont 99.7%) with every other category byte-identical to
  B10.
- **B12** (instrument-select ADSR/GATE/FILTER restarts commit same-tick,
  same driver+translator pattern as B11 — see "B12" above): **Fargo 79.5%,
  Glyptodont ADSR 96.1%→96.2%**, small and real, no regressions. Found (via
  a new permanent per-frame/per-register diagnostic harness in the build
  script) that Fargo's weak full-song pulse/adsr numbers were actually TWO
  unrelated bugs — one fixed this round, one (**voice 2's still-unexplained
  full instrument-state desync from ~frame 8000 onward**) genuinely open
  and now the dominant reason Fargo's pulse (51.6%) and adsr (74.7%)
  full-song numbers stay low. That residual needs a fresh live hardware
  trace to crack, not another `player.s` read.
- **B13** (a real VICE live trace through frame 10300, plus live `py65`
  single-step CPU tracing and internal-state instrumentation of the
  simulator itself — see "B13 shipped" above): the true root cause turned
  out to be a driver-adjacent TRANSLATOR bug, not a driver/wave-engine bug
  at all — `bb_steps_for_voice` ignored `gate_is_off` in its note branch
  (a gate-off immediately followed by a note was wrongly treated as a
  genuine restart instead of "stays silent"), compounded by a companion bug
  where the delay branch never RESET `gate_is_off`, so a first attempted
  fix over-applied "stays silent" to 14-45% of every voice's notes before a
  second fix (both branches now correctly consume-and-reset the flag per
  real hardware's own per-event `v_pendins` semantics) landed cleanly.
  Fixed: **Glyptodont 92.0%→97.6%, pulse 77.7%→99.7%**. Fargo's own separate
  voice-2 desync (unfixed since B12) is confirmed a DIFFERENT bug — this fix
  left Fargo essentially unchanged (79.5%→79.2%). Also surfaced a
  previously-unknown, unrelated bug along the way: the simulator itself
  diverges from real hardware on Glyptodont voices 0/1/filter in this same
  later region — every B1-B12 fidelity number implicitly trusted the
  simulator past frame ~1200, which this trace shows isn't fully safe.
- **B14** (same live-trace method applied to Fargo's own residual — see
  "B14 shipped" above): the true root cause was a hard format limit hit for
  the first time, not a timing bug — Fargo genuinely uses 35 distinct
  instruments but the driver's command byte only has 5 bits (0-31 slots),
  and the translator silently CLAMPED overflow indices onto slot 31 instead
  of triggering B6's existing adaptive part-splitting (whose own resource
  check was measuring the already-clamped, hence always-≤32, value — a
  check that could never fire). Fixed with a proper per-part dense remap
  (raw index → compact driver slot) plus fixing the resource-count itself
  to see the true, unclamped total. **Fargo 79.2%→92.7%** (freq 99.6%,
  waveform 98.1%, adsr 99.6%, filter 100.0%; pulse 71.1%, up hugely from
  50.3% but still the weakest category and not further investigated this
  round). Fargo now correctly builds as 2 parts, not 1. Glyptodont
  byte-identical (97.6%, no regression — its own 31 instruments were
  already under the cap).
- **B15** (a coverage extension, not a fix — see "B15 shipped" above): all
  9 remaining v1.2-exact-bucket files built natively for the first time,
  cold, no crashes: 91.4%-98.9% overall (mean ~95%), 2 of the 9 needing
  B6's multi-part split automatically (Dithered_Island, Into_the_Unknown).
  **All 11 v1.2-exact-bucket files now have a working native Stage-B
  build.** None of the 9 new files have been individually root-caused or
  audio-listened — this is a baseline, not a claim of per-file understanding.
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
  `freq_lsb`/`freq_msb` interpolation tables **in STAGE A specifically** (Stage
  A still only calibrates the resting/landing pitch — B10 closed this for the
  NATIVE driver, which now runs lft's real 4-mode interpolator over the real
  tables, but Stage A is untouched); extending the native driver past Fargo+Glyptodont
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
