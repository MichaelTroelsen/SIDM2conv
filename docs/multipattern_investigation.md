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

## Class B upgrade — partial success (2026-05-09 second pass)

After the initial "DOES NOT WORK" finding (kept below for context), a
second pass took a different angle: scan the binary statically for
`LDA abs,X` instruction pairs whose operands differ by 3, then validate
each candidate by walking the post-INIT memory and scoring the resulting
voice byte streams. Real NP21 voice streams have a characteristic
statistical signature (start with $A0-$BF instrument prefix, ≥70% of
bytes < $A0, plausible length 8-200) that distinguishes them from
arbitrary code byte runs.

Implemented in:
- `sidm2/ch_seq_ptr_scanner.py` — autodetector
- `sidm2/sid_init_runner.py::trace_play_reads` — runtime memory-read
  trace during PLAY (used as a filter when available)
- `sidm2/sf2_writer.py:_build_np21_sf2_edit_area` — falls back to
  the autodetector when conventional `$0A1C/$0A1F` ch_seq_ptr extraction
  yields no in-range pointers

**Real-world impact** on the SID/Laxity/ corpus (286 files):

| Class | Count | % | Meaning |
|---|---|---|---|
| A_native | 42 | 15% | conventional `$1A1C/$1A1F` ch_seq_ptr extraction works (Stinsen, Unboxed, etc.) |
| **B_lifted** | **33** | **12%** | autodetect found a non-Stinsen ch_seq_ptr table, real voice sequences extracted |
| C_unchanged | 151 | 53% | autodetect found no candidate or yielded non-NP21 byte runs; empty-patterns fallback |
| (driver11) | 57 | 20% | player-id detection routed to driver11 fallback path; my upgrade doesn't apply |
| CONVERT_FAIL | 3 | 1% | pre-existing parse errors |

**Net lift: 18% → 27% (+9 pp)** of the Laxity corpus now has a real
editor view.

Verified F10-load on `1983_Sauna_Tango.sid` and `C20H25N30.sid`: both
load 5/5 in SF2II, with real notes visible in the editor. Stinsen +
Unboxed canonical regression tests still pass (zig64 trace 1910/1910 +
2734/2734).

**Why most Class B/C files don't lift**: the `LDA abs,X`-pair fingerprint
catches Stinsen/Sauna_Tango/C20H25N30-style players that load voice
pointers via `LDA voice_seq_lo_table,X / LDA voice_seq_hi_table,X`. Other
NP21 variants use different addressing modes (`LDA abs,Y`,
`LDA (zp),Y`, self-modifying code, etc.) that the static scanner doesn't
match. A future refinement could add detection for `LDA abs,Y` ($B9)
pairs and zero-page indirect-Y patterns.

The original "Class B doesn't work" investigation below is preserved for
historical context — the FIRST attempt (read post-INIT `$1A1C/$1A1F`)
genuinely doesn't work; the SECOND attempt (LDA-pair fingerprinting +
walk validation) does for ~12% of files.

---

## Class B upgrade — first attempt (2026-05-09) — DID NOT WORK

I tried to lift Class B to Class A by capturing `ch_seq_ptr` after running
INIT in a py65 6502 emulator (`sidm2/sid_init_runner.py`). Findings:

- For Class A files (Stinsen): post-INIT memory at `$1A1C/$1A1F` matches
  pre-INIT — the bytes are **pre-populated in the binary at SF2-export
  time**, not written by the player's INIT routine.
- For Class B files (Sauna_Tango, Bossa_Nova, 7-BITS, C20H25N30,
  Adventure, Coop_6581 — 6 sampled): post-INIT bytes at `$1A1C/$1A1F`
  are **identical to pre-INIT garbage**. Running PLAY 10× also doesn't
  change them.

This means `$1A1C/$1A1F` is **not the ch_seq_ptr location** for these
Class B files. They're using a different NP21 player variant where the
voice pointer table sits somewhere else.

Implications for the "Class B = analyzer recovers" metric (24%):

The `LaxityPlayerAnalyzer` claims to recover ≥1 sequence for those
files, but its recovery is via heuristic fallback strategies in
`laxity_parser.py:_extract_sequence_at_address`:
- Strategy 2: treat the (garbage) ch_seq_ptr address as a direct file
  offset
- Strategy 3: treat it as a low-memory offset

Both walk `c64_data` from the heuristic offset until a `0x7F` byte
turns up and call that "a sequence." The byte run found may be
arbitrary table data (instrument bytes, pulse table, etc.) that just
happens to contain a `0x7F`. **The "Class B" count is largely a
false-positive metric** — the recovered "sequences" are not
necessarily what the player actually plays.

So the corpus picture is closer to:
- Class A: ~18% (real recovery, ch_seq_ptr at $1A1C/$1A1F works)
- Class B + C combined: ~82% (no reliable recovery — the existing
  analyzer's "B-class" successes are mostly heuristic noise)

## Where this could go (multi-day work)

To genuinely lift Class B/C to A would require **per-NP21-variant
analysis**: identify the player variant from the binary, look up its
ch_seq_ptr address, extract from there. Variants seen across the
corpus include at least:

- **Stinsen-class** — ch_seq_ptr at $1A1C/$1A1F (covered today)
- **Native Laxity NewPlayer V21 (multiple sub-variants)** — locations
  unknown; would need RE per variant

A reasonable approach would be:
1. Disassemble each unique NP21 binary in the corpus.
2. Find the `LDA <addr>,Y` or `LDX <addr>,X` instructions that load
   from a 3-byte-by-3-byte structure (lo + hi tables).
3. Extract the addr of the lo + hi tables for that variant.
4. Build a player-fingerprint → ch_seq_ptr-addresses map.
5. Plug into `_build_np21_sf2_edit_area`.

That's a multi-day reverse-engineering project. Not started; not
recommended unless editor-view fidelity for native Laxity files
becomes a strong user requirement.

## Recommendation

1. **Do nothing right now**. The user-facing audio path is 100% on the
   canonical corpus and the F10-load reliability is sound.
2. The corpus classifier in `pyscript/probe_multipattern.py` overcounts
   Class B because the analyzer's heuristic fallbacks produce false
   positives. True recovery rate is closer to 18% (Class A only).
3. The py65 INIT runner at `sidm2/sid_init_runner.py` is kept for
   future investigation — it correctly runs INIT and snapshots memory,
   it just doesn't help with the ch_seq_ptr-recovery problem because
   the assumed location is wrong for non-Stinsen-class files.
4. Drop the "multi-pattern songs" phrasing from project docs — it's
   misleading. The right phrasing is "Class A: Stinsen-class layout
   works today. All other Laxity files would need per-variant RE for
   real editor-view recovery; not done."

## Files used in this investigation

- `pyscript/probe_orderlist.py` — per-file probe of `ch_seq_ptr` validity
- `pyscript/probe_multipattern.py` — full corpus classifier (overcounts
  Class B — see disclaimer above)
- `sidm2/sid_init_runner.py` — py65-based INIT runner. Kept for future
  per-variant RE; the simple "run INIT, read $1A1C" approach was
  proven empirically not to work for non-Stinsen-class files.

Run either against any `.sid` file to reproduce.
