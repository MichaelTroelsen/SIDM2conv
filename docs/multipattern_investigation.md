# Multi-pattern Songs — Investigation Findings (2026-05-09)

## TL;DR

The phrase "multi-pattern songs" in older project docs is a misnomer.
**NP21 binaries have no multi-pattern structure** at the binary level.
What the player reads at runtime is one flat byte stream per voice, full
stop. The pattern boundaries you see in the SID Factory II editor are
**editor-side metadata that the NP21 packer compiles away** when exporting.

What we DO have is a population of Laxity NP21 files where today's
converter produces an empty placeholder editor view because the
extraction looks in the wrong place.

## Concrete classification (300-file Laxity corpus)

`pyscript/probe_multipattern.py` walks `SID/Laxity/*.sid` and classifies
each file by what the converter can extract:

| Class | Count | % | What's true | What you see in SF2II |
|---|---|---|---|---|
| **A** | 55 | 18% | `ch_seq_ptr` at `$0A1C/$0A1F` is pre-populated in the binary (SF2-exported convention). `_build_np21_sf2_edit_area` walks them; Stage 2.5 segments each voice's stream by instrument-prefix bytes for display. | Real notes, multi-pattern view. Today's success case (Stinsen, Unboxed, etc.). |
| **B** | 72 | 24% | `ch_seq_ptr` is uninitialized in the binary; the player INIT routine populates it at runtime from elsewhere. `LaxityPlayerAnalyzer` recovers ≥1 sequence by walking player code statically. | Empty placeholder editor view. Audio still plays correctly. |
| **C** | 173 | 58% | Both `ch_seq_ptr` AND the static analyzer fail. | Empty placeholder editor view. Audio still plays correctly. |

## What's wrong with the old framing

The earlier project-status memory said:

> Generalization beyond Stinsen + Unboxed — both songs are simple
> (single sequence per voice, looping). Songs with pattern chains
> (multiple sequences per voice in the orderlist) are not yet handled.

This frames the gap as "multi-sequence orderlists need walking." That
turns out to be wrong:

1. NP21 has **no orderlist or pattern table** in the compiled binary. The
   player reads one flat byte stream per voice.

2. SID Factory II's "orderlist with multiple patterns" view is built
   from compile-time metadata that never makes it into the NP21 binary.
   When you export an SF2 to NP21, the packer concatenates all patterns
   for each voice into a single per-voice stream and that's all the
   binary contains.

3. So Stage 2.5's instrument-prefix segmentation is **the only** way to
   recover something pattern-shaped from an NP21 binary, and it's a
   heuristic best-effort. There's no "real" multi-pattern recovery to
   pursue at the binary level.

## What the actual gap is

For Class B files (24%, 72 of 300), today's converter:
- Tries to walk `ch_seq_ptr` → finds garbage addresses → empty fallback
- Even though `LaxityPlayerAnalyzer` would have the per-voice stream
  starting addresses if we plumbed them through

For Class C files (58%, 173 of 300):
- Both extraction paths fail — no useful editor view available without
  more invasive analysis.

## Possible improvement: capture `ch_seq_ptr` post-INIT

A pragmatic upgrade for Class B → Class A:

1. Build the SF2 with placeholder ch_seq_ptr as today.
2. Run zig64 (or any 6502 emulator) with `init_addr` for a few hundred
   cycles to let the player initialise itself.
3. Read the contents of `$0A1C..$0A1E` and `$0A1F..$0A21` from emulated
   memory. Those are the now-populated voice sequence pointers.
4. Patch the SF2 to use those addresses, run the existing
   `_build_np21_sf2_edit_area` extraction, and ship.

Estimated cost:
- 30-50 LOC: shell out to `tools/sidm2-sid-trace.exe` with INIT-only mode
  (would need a small change to the trace tool to emit a memory
  snapshot at a chosen point) OR write a 6502 emulator hook.
- 10-20 LOC: plumb the captured pointers into the writer.
- Probably an hour or two end-to-end, plus testing.

Could lift the canonical-Laxity editor-view yield from 18% → 42% of
the corpus.

## Possible improvement: static recovery for Class C

The 173 Class C files are a deeper problem. The static analyzer
(`LaxityPlayerAnalyzer.extract_music_data()`) is the existing attempt
to recover sequences without running INIT, and it's bailing out for
these files. Its failure mode would need investigation per-file.

Likely a multi-week project. Not obviously worth it given that audio
playback already works for all 300 files (the embedded NP21 binary
plays fine in zig64 / VICE / sidplayer regardless of whether the SF2
editor view is populated).

## Recommendation

1. **Do nothing right now**. The user-facing audio path is 100% on the
   canonical corpus and the F10-load reliability is sound.
2. If editor-view fidelity becomes important for Class B files, the
   "capture ch_seq_ptr post-INIT" approach is the right next step.
   Not started.
3. Drop the "multi-pattern songs" phrasing from project docs — it's
   misleading. The right phrasing is "Class B/C files have empty
   editor views because ch_seq_ptr extraction fails."

## Files used in this investigation

- `pyscript/probe_orderlist.py` — per-file probe of `ch_seq_ptr` validity
- `pyscript/probe_multipattern.py` — full corpus classifier (A/B/C)

Run either against any `.sid` file to reproduce.
