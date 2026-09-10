# Laxity NewPlayer v21 (NP21) — SID → SF2 support

**Player:** Laxity NewPlayer v21 and forks
**Registry key:** `laxity`
**Driver:** `sf2driver_laxity_00.prg`
**Accuracy:** **99.93–100%** (production — the flagship supported player); canonical

> **What the 99.93% is, established 2026-08-28.** It is a **TARGET**, not a measurement.
> The only measurement on record is **99.98% frame accuracy over n=2 files**
> (`Stinsens_Last_Night_of_89.sid`, `Broware.sid`), taken 2025-12-28 by round-trip
> SID→SF2→SID comparison, with register writes 100% (507/507) — `CHANGELOG.md:10450`,
> which says in as many words that it *exceeds the 99.93% target*. The script that
> produced it, `test_laxity_accuracy.py`, is **no longer in the tree**, so as it stands
> the figure is not reproducible. The earliest form (`CHANGELOG.md:10586`) asserts
> "99.93% frame accuracy" with no method attached, and that is where it began reading
> as measured. The corpus rounds (**268–283 of 286 PASS**) are real and independent,
> but they are a **pass/fail count per file**, not frame accuracy — do not merge the two.
> Re-deriving a reproducible frame-accuracy figure over a named corpus is open work.
> **DONE 2026-09-02 — and the script is tracked this time.**
>
> `pyscript/laxity_accuracy_sweep.py` re-measures the whole selector-defined
> corpus by the same round trip the retired n=2 figure used
> (SID → SF2 `--driver laxity` → SID′, then `scripts/validate_sid_accuracy.py`),
> so the new number is comparable to the old claim rather than a different
> quantity wearing its name. Run: `python pyscript/laxity_accuracy_sweep.py
> --duration 30 --json out/laxity_sweep/sweep.json`.
>
> **RESULT (2026-09-02, 17 of 17 files, 0 errors, 0 unmeasurable):**
>
> | | frame accuracy | exact frame matches |
> |---|---|---|
> | min | **98.73%** (`Unboxed_Ending_8580`) | 90.7% |
> | median | **100.00%** | 100.0% |
> | max | **100.00%** | 100.0% |
>
> **16 of 17 files are at exactly 100.00% on BOTH columns, OVER A 30-SECOND
> WINDOW** — not just the lenient per-frame mean but exact frame-for-frame
> identity, 1500/1500. The window is not a footnote to this figure, it is part
> of it: songs longer than 30s are scored on their opening only, so a defect
> that starts at 0:45 is invisible here and 16/17 is a claim about the first
> half-minute of each file rather than about the file. The sweep now prints the
> window on every line a number can be quoted from, and records `window_seconds`
> in its JSON, so the figure cannot be lifted without it (grep for
> `QUOTE THE WINDOW WITH THE NUMBER` in `pyscript/laxity_accuracy_sweep.py`).
> Whether 16/17 survives at full song length is UNMEASURED. The sole
> outlier is `Unboxed_Ending_8580` at 98.73% / 90.7%. So the 99.93% target is met
> and exceeded by the corpus, and it is now a measurement with a method in the
> tree.
>
> **THREE CONDITIONS ON QUOTING IT, none of them optional.**
> 1. **The window is 30 seconds — 1500 frames — for every file.** Songs longer
>    than 30s are measured over their opening only. The uniform `n=1500` is the
>    WINDOW, not the song length, so it does NOT distinguish a short tune from a
>    long one and must never be read as full-song coverage.
> 2. **The population is the 17 `SID/*.sid` files the driver selector routes to
>    the Laxity driver**, derived from the selector rather than hand-listed —
>    a hand list is how the last measurement's population became unrecoverable.
>    It is NOT the 286-file `SID/Laxity/` batch, which remains a pass/fail count.
> 3. **Three of these files do not locate their sequence table** (`Blue`,
>    `Clarencio_extended`, `Ocean_Reloaded` — the refusals recorded in
>    `laxity-parser-reads-runtime-pointers-as-the-sequence-table`) and all three
>    still score 100.00%. That is worth understanding rather than celebrating:
>    frame accuracy survives a failed locate because the converter falls back to
>    constants, so this metric does not exercise the locate at all.
figures in `docs/reference/ACCURACY_MATRIX.md`
**Corpus:** `SID/Laxity/` (286 files) + `SID/` root (17 mixed files)

This is SIDM2's most mature path: native Laxity NP21 SID files convert to a **custom Laxity SF2 driver** with byte-identical audio.

---

## player-id strings → Laxity driver
`Laxity_NewPlayer_V21` · `Vibrants/Laxity` · `256bytes/Laxity`

> `SidFactory_II/Laxity` / `SidFactory/Laxity` are **SF2-exported by author Laxity** → routed to **Driver 11**, not this driver. Check the player-id, not the author.

---

## What's reproduced
- Sequences (notes + durations), orderlists, instruments (AD/SR/HR/flags).
- Wave (F2), pulse (F4), filter (F5) tables — extracted from the binary and emitted in Driver-11 SF2 format.
- Filter accuracy **100%** (Stinsen-verified, v3.1.4), cross-validated against zig64 ground truth (`pyscript/validate_filter_accuracy.py`).
- C3 (edits affect playback): build-time shadow-buffer pre-fill + a runtime `$0F0E` translator regenerating per PLAY tick (`sidm2/sf2_to_np21.py`).

## Corpus status (286-file batch)
- **C1 (loads in SF2II):** ~268/286 via the SF2II GUI; ~283/286 via argv-load — the gap is an SF2II GUI Heisenbug, not a converter bug.
- **C2 (audio matches, cycle-accurate):** every file the converter emits an SF2 for has byte-identical audio (zig64 audio gate).
- Remaining residuals are architectural (shared-stream designs, CIA-IRQ Zetrex/YP variants), not correctness bugs.

See `memory/` notes (`corpus-state-2026-05-22`, `laxity-corpus-c2-failures`, `sid-root-4-criterion-status`) and `docs/FILE_INVENTORY.md` for the complete per-file inventory.

---

## Convert

```bash
sid-to-sf2.bat SID/Laxity/<file>.sid out.sf2                 # auto-selects Laxity driver
sid-to-sf2.bat SID/Laxity/<file>.sid out.sf2 --driver laxity # force
batch-convert-laxity.bat                                     # whole corpus
```

## Known limits
- Only **native** Laxity NP21 is supported by the Laxity driver (single subtune).
- Native Laxity NP21 → Driver 11 is **1–8%** — always use the Laxity driver for native files.

**Constants:** `INIT=$1000`, `PLAY=$10A1`, `INSTRUMENTS=$1A6B`, `WAVE=$1ACB`. Full reference: `docs/ARCHITECTURE.md`, `memory/laxity-np21.md`.

---

## EVERY Laxity constant was derived from two or three files — the standing rule (2026-09-06)

Three separate table constants in this codebase were each read off a couple of
songs and then applied to the corpus. All three fail on almost everything else,
and they fail the same way, because **the NP21 player is assembled per song**:
the layout is uniform, only the offset moves.

| constant | what it claimed | measured |
|---|---|---|
| `ch_seq_ptr` (`$099F` / `$0A1C`) | the sequence-pointer table | `$099F` serves **Angular and Omniphunk**, `$0A1C` serves **Stinsen and Unboxed** — and neither serves the other 13 of the 17 root files. Replaced by a code-signature search in `73780fa`. |
| instrument table (`$0A6B`) | `load + $0A6B` | **not among the ranked candidates on ANY of 14** `SID/Laxity/*.sid`, while the validated search located one on **14 of 14**. Offsets run `$0475`…`$0F07` — see the section below. |
| frequency table (`$0835`) | 96 interleaved lo/hi entries | over **303** Laxity SIDs: 61 too short, 242 return 96 entries, and only **2 of those 242** have real octave structure — Angular and Omniphunk again. 16 read all zeros. **0 of 242 are strictly ascending**, which a 96-note table must be. |

Two things follow, and they are the reason this page states the pattern once
instead of three times.

**The same two or three filenames keep appearing.** Angular and Omniphunk are
the pair behind both `ch_seq_ptr`'s `$099F` and the frequency table's only two
survivors; Stinsen and Unboxed are the pair behind `$0A1C`. A constant that
works on the file it was derived from is not evidence about the format — it is
evidence about that file, and this repo has now spent cycles on all three
mistaking one for the other.

**And "the address is right" is not "the read is right."** The frequency
constant is the sharp case: on Angular it scores 97.6% octave-doubling, which
looks like a hit, and is still not strictly ascending — because the real table
is at `$1833` and the constant reads `$1835`, two bytes high, so it starts half
an entry off and runs one entry past the end. A search that finds only the
ADDRESS would still be wrong here; the SIZE has to be established too.

> **The rule: locate a Laxity table by SEARCH, and make the search
> self-verifying.** A shape a wrong answer cannot fake — strictly ascending plus
> octave doubling for the frequency table, the `(zp),Y` fetch bases for
> `ch_seq_ptr` — is what separates a located table from a plausible one. Refuse
> on a tie rather than picking: a wrong table silently transposes or renumbers
> the whole song, and no downstream check in this repo would catch it.

## `out/Beginning.sf2` is silent because it is a STALE DRIVER 11 BUILD (2026-09-05)

**Attribution, not a defect in this driver.** `out/Beginning.sf2` renders
completely dead, and the cause is the limit stated directly above: it is a
**Driver 11** build of a **native Laxity** file, which is the 1–8% pairing.
The converter at HEAD does not make this mistake — a fresh conversion of the
same source is byte-for-byte correct on onsets.

| | measured |
|---|---|
| `player-id.exe SID/Laxity/Beginning.sid` | **`Vibrants/Laxity`** → routes to the Laxity driver |
| driver string inside `out/Beginning.sf2` | `" 11.00 - T"` → **Driver 11** |
| driver string inside `out/Beginning_v2.sf2` | `" 11.00 - T"` → **also Driver 11** |
| gate-on frames, original, first 400 | **389** |
| gate-on frames, `out/Beginning.sf2` | **0** |
| gate-on frames, fresh conversion | **389** |

A fresh conversion reproduces the original's note onsets **exactly** — voice 1
25/25, voice 2 2/2, voice 3 2/2, offset `0` on every one, zero frames of drift.
And the converter says so itself while doing it:

```
Player Type:     Vibrants/Laxity
Selected Driver: LAXITY (sf2driver_laxity_00.prg)
Reason:          Laxity-specific driver for maximum accuracy
Alternative:     Driver 11 (1-8% accuracy - not recommended)
```

So the two `out/Beginning*.sf2` artifacts predate correct auto-selection (or were
built with an explicit `--driver driver11`). **Rebuilding them fixes it**; nothing
in `laxity_parser.py` or `laxity_converter.py` needs changing, and the 99.93%
row is not implicated.

### Two measurement traps this cost, both worth knowing

⚠️ **A Laxity-driver SF2 is entered at `$1003`, NOT at `$10A1`.** CLAUDE.md's
Essential Constants list `PLAY=0x10A1`, and that is the play address of the
**native NP21 player inside the original SID** — not of the SF2 artifact, which
is an SF2 driver entered like any other. Probing a correct Laxity build at
`$10A1` returns **0 gate-on frames** and reads exactly like a dead conversion.
This mistake was made in both directions while diagnosing this file.

⚠️ **The symptom is "silent from frame 0", not "silent after ~0.25 s".** The
opening transient in the staged WAV is the driver's init writing registers; no
note ever gates. A description built from the audio envelope alone puts the
failure a quarter-second later than it is, and points diagnosis at a decay
mechanism that does not exist.

## The sequence table's bodies need not follow the table: Stinsen's 97-byte gap is the ORDERLIST BLOCK (2026-09-10)

`SF2Parser.laxity_locate_seq_table` used to require `ptrs[0] == tbl + 2*N` —
bodies immediately after the table. Stinsen's own SF2 violates it: the table is
at `$1A22` with N=39, so it ends at `$1A70`, and the first body is at `$1AD1`,
**97 bytes later**.

**Those 97 bytes were read before any code was written**, and they are not
padding and not a coincidence. They decode as exactly three `$FF`-terminated
voice orderlists — 41, 22 and 28 entries, each ending `FF 00`, transposes
`$A0`/`$A2`/`$AC` in range, every index below 39, and **all 39 sequences
referenced with none missing**:

```
A0 0E 0F 0F 0F 0F 11 01 05 01 04 AC 02 03 A0 13 14 13 15 0E 11 01 05 01 04
AC 02 1B A0 13 14 13 15 1C 1C 1C 1C AC 02 1F 20 FF 00   <- voice 0
A0 00 12 06 06 06 07 25 25 16 17 06 06 18 25 25 06 06 06 06 1D 21 FF 00
A0 0A 0A 0B 0C A2 0A A0 10 08 09 19 AC 0D A0 0B 10 08 09 1A AC 0D 23 24 26
A0 1E 22 FF 00
```

So the gap is a **known structure**, and the bound is derived from its grammar
rather than from its size. The locator screens the *content* of the gap
(`_gap_is_orderlists`) instead of accepting a shift up to some maximum.

**Why not the fitted bound.** An earlier attempt used `0 <= shift <= 97` and
located the same files — but 97 is simply Stinsen's own shift. Sweeping it
showed a **step at 97, not a plateau**, and it let four documented false locates
back in (`Broom_Tycoon`, `Hand_Interludes_Side_1/2/3`). A frequency table does
not decode as an orderlist, so the content screen admits Stinsen and refuses all
eight.

**Both control sets hold** (measured over the 47 `.sf2` in `SF2/`):

| control | result |
|---|---|
| files that located before the change | 22 — **0 moved, 0 lost** |
| files newly located | 24, **all at `$1A22` N=39** — Stinsen plus 23 `_stin_*`/`_test_*` copies of it |
| `PS_FALSE_LOCATES` (8 `SID/Laxity` files) | still refuse, 8/8 |

**The gain is ONE SONG**, and that is worth stating plainly: the 24 new files
are one tune and 23 edited derivatives at the identical table.

**A consequence to know about, RESOLVED.** Stinsen was the *only* file in
`SF2/` reaching the guarded `Laxity SF2 offset-table parser`, so locating it
structurally left that reader with **zero subjects in `SF2/`** (still true:
measured again at this head, 0 of the 47 `.sf2` in `SF2/` reach it; the one
remaining non-structural file, `_test_commando.sf2`, reaches
`indexed sequence table` instead). `SF2/` is a build **output** directory, not
the whole corpus, and the reader is exercised by decoding a **converted** SID,
so the search moved to the wider input corpus instead of stopping at an empty
output directory.

**Denominator: 286 of 286 `SID/Laxity/*.sid` converted** with
`sidm2.conversion_pipeline.convert_laxity_to_sf2` (2026-09-10) and each
resulting in-memory SF2 parsed and checked for provenance. **52 of 286 reach
`Laxity SF2 offset-table parser`** (non-structural), and most clear 5x their
own `default_sequence_length` by a wide margin — `Aids_Trouble` (dsl 129,
longest sequence 11,250, 87x), `Alliance` (dsl 55, longest sequence 12,451,
226x), `Cool_as_Wize_Title` (dsl 105, longest sequence 16,015, 152x) among
them. So the guard is **not dead code and not untested any more**: it has a
real, reproducible subject outside `SF2/`, and none of the 52 tripped the
impossibility refusal (`sequence_refusals` empty on all of them) — the guard
lets every one of these large-but-possible decodes through, which is the
behavior it exists to have.

`test_a_dsl_exceeding_file_still_decodes_THROUGH_the_guard` no longer skips.
It converts `SID/Laxity/Alliance.sid` on the fly (via the same
`convert_laxity_to_sf2` call, into a temp dir — nothing is checked into `SF2/`
for this), asserts the resulting provenance `reader` string is exactly
`"Laxity SF2 offset-table parser"` (not merely that the file decodes),
asserts `structural is False`, asserts the longest sequence exceeds 5x the
file's `default_sequence_length`, and asserts `sequence_refusals` is empty. If
a future locate fix ever routes Alliance structurally too (the same shape as
904e91e did to Stinsen), this test fails loudly on the reader-string
assertion — the fix is to re-run the 286-file search above and swap in
whichever of the other 51 files still reaches the guard, not to loosen the
assertion.

## `$80–$9F` is a DURATION byte: `(b & $0F) + 1` frames, bit 4 a separate flag (2026-09-05)

**Settled against the player's own 6502 code**, not against another module in
this repo — three readings of this byte range coexisted here and all three were
in-repo, which is what made them unresolvable from the inside.

Ground truth: `drivers/laxity/laxity_player_disassembly.asm` (SIDwinder
disassembly of *Stinsen's Last Night of '89*, a native NP21 rip). The sequence
byte reader:

```
    bpl Label_12          ; bit 7 clear -> not a duration byte at all
Label_10:
    cmp #$90
    bcc Label_11
    inc DataBlock_6 + $100,X    ; bit 4 set -> bump a SEPARATE flag
Label_11:
    and #$0F                    ; duration = LOW NIBBLE
    sta DataBlock_6 + $FD,X
    iny
    lda (ZP_0),Y                ; then fetch the note
```

and the counter it feeds:

```
    dec DataBlock_6 + $EE,X
    bpl Label_16          ; advance the row only when it goes NEGATIVE
```

`dec` + `bpl` means a stored `n` survives `n` decrements and advances on the
`n+1`th. So:

> **duration = `(byte & $0F) + 1` frames — 1..16 for `$80`..`$8F`.
> Bit 4 is NOT part of the count; it sets a separate flag.**

### All three readings in this repo were wrong, each differently

| where | reading | verdict |
|---|---|---|
| `sidm2/sequence_translator.py:233` | ~~`(b & $1F) + 1`~~ → **`(b & $0F) + 1`** | **FIXED 2026-09-06.** The mask folded bit 4 into the count; the `+1` was already right |
| `pyscript/sf2_viewer_core.py` `unpack_sequence` | `b & $0F`, bit 4 = tie | **right mask and right bit-4 split — but no `+1`**, so every duration is one frame short |
| `CLAUDE.md` Laxity constants | `$80 = GATE_OFF` | **wrong for the sequence stream** — `$80` is a duration byte whose nibble is 0, i.e. one frame |

⚠️ **The `$100,X` flag is not purely a "tie".** The same location is incremented
at line 140 when the NOTE byte is `$00` or `$7E`. So it is a shared
gate/continue flag that bit 4 is one input to, and calling it `tie` in a decoder
is a simplification that happens to work rather than the player's own model.

### A THIRD defect in the same decoder: the duration is STICKY and the parser resets it

Found while pinning the mask (2026-09-06), from the same disassembly:

```asm
$1102   lda DataBlock_6 + $FD,X     ; the stored count...
        sta DataBlock_6 + $EE,X     ; ...reloads the counter EVERY row
...
$10B2   dec DataBlock_6 + $EE,X
        bpl Label_16
```

`$FD,X` is written **only** when a `$80–$9F` byte arrives, and the row-advance
path reloads `$EE,X` from it every row. So **the last duration persists across
following notes until a new duration byte appears.**

`sequence_translator.parse_sequence` instead does `current_duration = 1` in its
"reset per-note state" block after every note, so `84 30 31 32` decodes as
`[5, 1, 1, 1]` where the player holds 5 for all three. This is **not fixed** —
it is a second semantic change with its own blast radius and wants its own
measured arm. It is recorded as a `strict=True` xfail in
`pyscript/test_sequence_translator.py`, so whoever fixes it is forced to remove
the marker rather than leaving the divergence undocumented.

### What was changed, and what was not

**SHIPPED (2026-09-06):** `sequence_translator.py`'s mask, `$1F` → `$0F`. The
four suites the task named — `scripts/test_converter.py`,
`pyscript/test_laxity_analyzer.py`, `pyscript/test_sf2_viewer_core.py`,
`pyscript/test_abpage.py` — were baselined at **259 passed** before the edit and
are at **259 passed** after it, including both pins of Angular's editor capture
(sequence 07 rows 7..14 = `A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4`). The published
**99.93–100%** figure is carried by `test_laxity_analyzer.py` and
`test_converter.py` within that set and did not move.

**NOT SHIPPED:** `unpack_sequence`'s missing `+1`. Two independent reasons, and
the second is the substantive one:

1. It fails `pyscript/test_abpage.py::test_row_schedule_default_no_longer_truncates_hawkeye_at_2048`
   (2495 → 2919 rows) and
   `test_sf2_viewer_core.py::test_a_dsl_exceeding_file_still_decodes_THROUGH_the_guard`
   (1762 → 2231 entries). Both shift because `row_schedule` expands each event
   into `duration` rows, so the counts move by roughly one row per event. Both
   numbers were measured under the one-frame-short decoder, so they are not
   evidence against the fix — but `test_abpage.py` is read-only to the task that
   found this.
2. **The ground truth does not obviously transfer.** The `+1` is derived from the
   *native NP21 player's* counter. `unpack_sequence` decodes **every** SF2,
   including Driver 11 artifacts — the Hawkeye file in the failing test is
   MoN/Driver 11, not Laxity. `drivers/laxity/sf2driver_laxity_00.prg` is the
   same player repackaged, so the `+1` is sound *for the Laxity driver*; whether
   Driver 11 uses the same `n+1` convention is **not established**, and applying
   it corpus-wide on that assumption is the over-generalisation this page exists
   to prevent.

Fixing it wants a task that declares `pyscript/test_abpage.py` as writable and
establishes Driver 11's own counter from `G5/drivers/sf2driver11_*.prg`.

### Why the mask fix waited (historical)

The mask difference is **not inert**. Measured over the 6 `SID/Laxity/*.sid`
files whose sequence table locates: **1,708 duration bytes, of which 232 (13.6%)
have bit 4 set** — exactly the population on which `$1F` and `$0F` disagree. So
switching `sequence_translator.py` to the correct mask changes the decoded
duration of roughly one event in seven.

`sidm2/sequence_translator.py` is imported by `sidm2/laxity_analyzer.py`, which
owns the two-stage path behind the published **99.93–100%** native-Laxity
figure. A mask change there can move that number, and confirming it does not
requires a corpus-scale accuracy re-measurement — not the two single files a
decoder task normally declares. Fixing `unpack_sequence`'s missing `+1` is
equally non-inert in the other direction: `abpage.row_schedule` multiplies
duration by tempo, so every row's frame position shifts.

**That caution was right about the `+1` and over-cautious about the mask.** The
mask fix shipped on 2026-09-06 against a measured 259-pass baseline (above); the
`+1` is still open for the two reasons listed there.

## The locate is CONFIRMED on 11 of 11 — by the player's own fetches, not the editor (2026-09-06)

`locate_seq_ptr_table` (73780fa) was verified on **three** files whose sequence
addresses are independently known (Angular `$1907`, Omniphunk `$1907`, Stinsen
`$1A1C`) and merely *plausible* on eleven more. That mattered because the
conversion A/B showed the emitted SF2 is **byte-identical with and without the
locate**, so a wrong locate is invisible downstream.

### The prescribed ground truth cannot work, and that is settled

The task's method was SF2II's orderlist panel (Ctrl+P, F1). Two cycles
established it is unusable: the panel shows a converter **stub** that is
byte-identical across files (`a0 00 fe ff ff…` → `00 01 02`), while **zero of
14** files' real orderlists start `00 01 02`. It disagrees with every file by
construction, *including the confirmed ones*. No GUI was used for the result
below.

### What was used instead: the player fetches its own sequences

The locate finds `ch_seq_ptr` by **code signature** — two `LDA abs,X` whose
operands are 3 apart. Every file contains ~10–24 candidates matching that shape,
because the player keeps several parallel 3-byte per-voice tables side by side.
So *"is the table read?"* discriminates nothing — the player reads all of them.

What only the real table can do is supply the **base addresses of the
indirect-indexed `(zp),Y` fetches that walk sequence data**. So: emulate `init`
plus 200 `play` calls under `sidm2/cpu6502_emulator.py`, record every address
reached through `(zp),Y`, and ask whether the pointers *stored in* the located
table are among them. Score is out of 3, one per voice.

### It discriminates — checked before it was believed

On Angular, of **22** candidates sharing the code signature, **exactly one
scores 3/3 and it is the located one**; the other 21 score 0/3. Both historical
constants score less than 3 (`$099F` → 1/3, `$0A1C` → 0/3), and an off-by-one
degrades rather than passing (±1 → 2/3, +2 → 1/3). On Stinsen, 1 of 21, and
`$0A1C` also scores 3/3 — correct, that constant genuinely serves Stinsen.

### The result

> **11 of 11 score 3/3, alongside 3/3 on all three controls.**

| | files | score |
|---|---|---|
| controls (independently confirmed) | Angular, Omniphunk, Stinsen | **3/3 each** |
| the eleven | Balance, Beast, Cascade, Chaser, Colorama, Cycles, Delicate, Dreams, Dreamy, Phoenix_Code_End_Tune, Unboxed_Ending | **3/3 each** |

⚠️ **The caveat, and it is not a small one.** On **6 of the 14** the located
table is the *unique* 3/3 candidate; on the other **8** a neighbour six bytes
below also scores 3/3 (Angular's `$1901` vs `$1907` shape). Those neighbours
hold *different* pointers, so they are a second real table the player also
fetches through — most likely the orderlist pointers.

**This does not weaken the locate, and the reason is the control:
Omniphunk — one of the three independently confirmed files — is among the
ambiguous eight.** So the ambiguity is structural to the format, not a symptom
of a wrong pick. What the check establishes on all 14 is that the located
address *is* a table the player fetches sequence-shaped data from; on 6 it also
excludes every alternative.

Pinned in `pyscript/test_laxity_parser.py` (15 tests, ~3 s). Shifting the
locate −6 to the ambiguous neighbour fails 7 of them.

⚠️ **The locate accepts far more than 14 files.** Swept over `SID/` and
`SID/Laxity/` it locates **208**, of which 178 are unique-3/3. This page's
denominator of 14 is the population the original task named, not the reach of
the function.

## The instrument table is NOT at a fixed offset — and the validated search is not a drop-in (2026-09-05)

**`LaxityParser._extract_instruments()` reads `load_address + $0A6B`** (i.e.
`$1A6B` for a `$1000` load). Measured against `instrument_map`'s own validated
search over 14 `SID/Laxity/*.sid` files:

> **the offset `$0A6B` is not among the ranked candidates on ANY of the 14.**
> The search located a top candidate on **14 of 14**, each explaining 100% of
> that file's observed envelopes.

The located offsets are genuinely per-file, which is why no constant can work:

```
$0475  $047A  $0492  $04F9  $061B  $0708  $07A6
$0823  $08FD  $0A2B  $0A97  $0AB3  $0E31  $0F07
```

Note the load addresses vary too — `Alibi.sid` loads at `$4000`, `Aids_Trouble`
puts its table at `$AE31` — so this is not a fixed *address* problem that a
load-relative offset already solves. It is per-song table placement, the same
shape `PATTERNS.md` records for every other player in this repo.

This supersedes the earlier framing that asked which of two candidates
(`$1A6B` or `lo_base+$4F`) is right. **Neither is**; there is no two-way choice.

### Why the search was NOT wired in

`instrument_map.locate_instrument_table(data, observed, ...)` ranks layouts by
how many **observed ADSRs** they explain — `observed` comes from note onsets in
a RENDERED TRACE (`siddump_frames_full` → `onsets_with_registers`).

`LaxityParser.__init__(self, data: bytes, load_address: int)` takes bytes and
nothing else, and the module imports only `logging`, `typing` and `dataclasses`
— **it cannot render anything.** So the validated search is not a drop-in
replacement for the constant: wiring it in means giving `LaxityParser` a trace,
which changes its constructor contract and reaches every call site
(`laxity_analyzer.py:491`, `sf2_viewer_core.py:1556` and `:1797`, plus the
tests).

That is a real change with a real design question behind it — should a byte
decoder depend on a renderer? — and it is not one to make as a side effect of
correcting a constant.

### What the constant currently costs, so the priority is honest

It is NOT behind the 99.93–100% figure. `laxity_analyzer.extract_music_data()`
builds its own instruments via `extract_instruments()` /
`instrument_extraction.extract_laxity_instruments`, not from
`laxity_data.instruments`. What the parser's instruments actually feed:

- `driver11_section_injectors.py:97-100`, i.e. the **Laxity → Driver 11** path,
  which is separately documented at **1–8%** and not recommended for native
  files;
- `laxity_analyzer.py:525-531`, where the parser's first instrument record is
  used as a **search seed** to report `extraction_addresses['instruments']`. A
  wrong seed makes that report wrong or empty — a reporting defect, not a
  fidelity one.

⚠️ `table_extraction.py:1518` already says the hardcoded `$1A6B` fallback is
"wrong for many". This section is the measurement behind that sentence.

## Sequence numbering: the editor's 01/02/05 vs the analyzer's 0/1/2

Measured on `SF2/Angular.sf2` (2026-08-29, HEAD `fa19503`), against the payload
re-based on the player base by `SF2Parser.laxity_payload()` (a40a859).

### `ch_seq_ptr` points at ORDERLISTS, not sequences

This is the root fact and it invalidates several older readings. The three
values `locate_seq_ptr_table` recovers on Angular are `$1AF2 / $1B00 / $1B0E` —
**exactly 14 bytes apart**, because each is one voice's orderlist:

```
$1AF2  87 01 01 01 01 01 01 08 08 08 08 08 08 FF     voice 0
$1B00  93 02 02 02 02 02 02 09 09 09 09 09 09 FF     voice 1
$1B0E  87 05 06 03 04 03 07 0A 0A 0B 0C 0B 0D FF     voice 2
```

Leading byte = transpose, then twelve **sequence numbers**, `$FF` = end.
`sidm2/laxity_parser.py:_extract_sequences_and_orderlists` treats each of these
as a sequence body and decodes it with the *sequence* grammar. It terminates on
`$7F`, not `$FF`, so it runs straight through the orderlist end: 73 bytes from
`$1AF2` spans all three orderlists **and** the pointer table below them. Its
comment — "the orderlist for Laxity is typically just one sequence per voice" —
is describing this artifact, not the format.

**So the 197/174/139 "event" counts are not a row count of anything.** Do not
compare them to editor rows.

### The real sequence table

A split lo[14]/hi[14] pointer table at `$1B1C`, immediately below the
orderlists. Its 14 entries partition `$1B38–$1EC2` **exactly, 907 bytes, zero
left over** — which is the check that says you have found the right table:

```
seq  0 $1B38   3 bytes   80 00 7F        <- the null sequence; no orderlist uses it
seq  1 $1B3B  84         seq  8 $1D46  84
seq  2 $1B8F  86         seq  9 $1D9A  86
seq  3 $1BE5  75         seq 10 $1DF0  54
seq  4 $1C30  60         seq 11 $1E26  50
seq  5 $1C6C  81         seq 12 $1E58  51
seq  6 $1CBD  81         seq 13 $1E8B  56
seq  7 $1D0E  56
```

The orderlists use `01`–`0D` and never `00`. The offset of this table from the
player base varies per build, so **locate it, never index to a constant** — the
same rule 73780fa established for `ch_seq_ptr`.

### The mapping

| Scheme | What it is | Angular |
|---|---|---|
| Editor `01 / 02 / 05` | the **payload's** sequence numbers — the first entry of each voice's orderlist | `87 **01**`, `93 **02**`, `87 **05**` |
| Analyzer `0 / 1 / 2` | `sorted(unique ch_seq_ptr addresses)` positions, i.e. **voice order** | voice 0/1/2 |

They are not two numberings of the same objects: one indexes sequences, the
other indexes voices. Analyzer index *i* = voice *i* = orderlist entry `[0]` of
that voice.

### Ground truth, now checkable — and one line matches exactly

Decoding sequence `07` with `LaxitySequenceParser` gives, as rows:

```
row  0   1   2   3   4   5      6   7   8   9  10  11  12  13  14
    E-4 C-4 +++ A-3 E-4 F#-10  G-4 A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4
                                     ^-------- rows 7..14 --------^
SF2II capture, T3:                   A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4
```

Eight consecutive rows, **exact, no transpose**. That simultaneously validates
the sequence table above and the note naming: `octave = value // 12`,
`pitch class = value % 12`, `0 = C-0` (so `45 = A-3`, `48 = C-4`, `57 = A-4`).

The capture's T1/T2 line `+++ +++ C-4 --- A-3 +++ +++ +++` also resolves inside
sequence `07`, at rows 1–3 (`C-4 +++ A-3`).

**This REFUTES the "decoded notes sit about three octaves below the editor"
reading.** The octaves were wrong because the decoder was reading an
*orderlist* — sequence numbers `01 01 01 08` decoded as note bytes. Against the
real sequences the octaves are correct.

### What is still open

- **The capture's T1/T2/T3 labels do not map onto voices 0/1/2.** Voice 0's
  orderlist plays only `01` and `08`, voice 1 only `02` and `09`; neither ever
  plays `07`, yet all three ground-truth lines resolve inside `07` (which voice
  2 reaches at orderlist position 5). The capture is therefore a **scrolled**
  view: `01/02/05` is the orderlist's first row, and the note rows shown belong
  to a different song position. Any future ground-truth capture must record the
  orderlist position, not just the track labels.
- **`F#-10` appears in the decode** (seq 3, 4, 7, 11–13) — a note value above
  `$5F`, so a command byte being read as a note. A real stage-2 gap, unrelated
  to the numbering.

### The editor's orderlist panel cannot confirm a locate — it reads a stub

Two ground-truth captures of Angular's orderlist disagree: the table above
records the editor showing `01 / 02 / 05`, and a 2026-09-05 SF2II capture of a
freshly converted Angular showed `0000: 00 01 02` with track labels
`a000 / a001 / a002`. The second reading is the converter's own SF2-level
orderlist, and it is **the same on every file**, so a panel showing it
discriminates nothing.

Measured, no GUI involved — `SF2Parser` over three converted files:

| converted file | SF2 orderlist (what the editor loads) | `laxity_orderlists` (the embedded NP21 payload) |
|---|---|---|
| Angular | `A0 00 / A0 01 / A0 02` | `87 **01**` / `93 **02**` / `87 **05**` |
| Cascade | `A0 00 / A0 01 / A0 02` | `85 **07**` / `85 **09**` / `91 **05**` |
| Cycles  | `A0 00 / A0 01 / A0 02` | `93 **01**` / `87 **0C**` / `87 **02**` |

The left column is byte-identical across all three (`a0 00 fe ff ff …`) while
the right is file-specific and reproduces `locate_seq_ptr_table` +
`read_orderlist_numbers` exactly. The SF2 orderlist is a **stub**: the Laxity
driver plays from the payload, so the emitted SF2 needs only enough of a
Driver-11-shaped orderlist for the editor to open the file. Angular's stub is
one to two positions long against fourteen sequences.

**And the stub can never coincide with a real answer.** Across all 14 files the
locate accepts, the native first entries are `01 02 05`, `08 02 01`,
`0E 00 0A`, `01 03 05`, `01 03 06`, `07 09 05`, `01 02 17`, `01 02 03`,
`01 0C 02`, `05 02 05`, `01 02 03`, `01 05 07`, `07 08 02`, `01 11 09` —
**zero of 14 are `00 01 02`**. So a panel reading `00 01 02` disagrees with
every file by construction, including Angular, whose `01 02 05` is proven. A
disagreement read off that panel is therefore not evidence against a locate,
and an agreement is impossible.

Consequences for anyone resuming the "11 files are plausible, not verified"
question:

- **Do not re-run the SF2II panel method for this.** It is refuted with a
  mechanism, not merely unlucky. The earlier `01 / 02 / 05` capture must have
  come from a different panel or a different artifact; until someone records
  *which* panel, the table row above should be read as "the payload's numbers",
  not "what SF2II displays".
- **siddump pitch is not the fallback.** Angular's sounded onsets are `B-7`
  (semitone 95, the top of the table) on all three voices — the instruments'
  arpeggio and wave-program own the pitch, not the sequencer. Comparing a
  decoded note stream against siddump onsets scores 0 agreement on all three
  *confirmed* files, so it fails its own control.
- What is left is a ground truth that reads the **sequence rows** at a recorded
  orderlist position, which is what the `07` decode above already did once.

## `Unboxed_Ending_8580` at 98.73%: voice 1 acquires a wave program the original does not (2026-09-05)

It is the sole Laxity file under 100% in the round-trip sweep, and the residual
is **not** spread thin — it is one voice, three registers, and a periodic
pattern from a single frame onward.

### Which registers

Of the 22 the validator scores, **three** are below 100, and all three are
voice 1:

| register | accuracy | original writes | ours | delta |
|---|---|---|---|---|
| `Voice1_Control` | 85.33% | 377 | 459 | **+82** |
| `Voice1_FreqLo` | 95.73% | 751 | 767 | +16 |
| `Voice1_FreqHi` | 95.73% | 751 | 767 | +16 |

Voices 2 and 3 are **100.00 / 100.00** on both frequency and waveform, and
`filter_accuracy` is 100.0. We do not write *less* than the original — we write
**more**, which is the shape of an engine running where none should.

### Which frames

Re-measured directly with siddump over the same 30 s / 1500-frame window:
voice 1 disagrees on **236 frames (15.73%)**, voices 2 and 3 on **zero**. The
236 span frames **586 to 1499** — to the end of the window — in **27 contiguous
runs** at a regular ~12-frame period:

```
(586,591) (598,603) (610,615) (622,627) (634,639) (646,651) ...
```

Six frames on, six off, repeating. Nothing before frame 586 disagrees at all.

### What the defect is

On those frames the original holds three waveform values — `$20` (saw, gate
off), `$21` (saw, gate on), `$09` — while ours emits a spread: `$F8` ×82,
`$2A`, `$02`, `$2B`, `$2C`, `$1C`. Two tells:

- **`$F8` sets the TEST bit** (plus all four waveform bits). TEST holds the
  oscillator at zero, so where the original is releasing a sawtooth we silence
  it. Our gate is also ON for fewer of these frames than the original's (42 vs
  94).
- **The frequency ramps with lo == hi.** At frames 588–590 ours reads 2313,
  2570, 2827 — steps of exactly **+257 = `$0101`** — against the original's
  9436, 9436, 7940. The comparison JSON records the same shape as `$0909` and
  `$0A0A`. A value whose low and high bytes are equal and increment together is
  a **table index landing in `$D400/$D401`**, not a pitch.

Taken together: from frame 586 our voice 1 runs a wave/arp program the original
does not, and its table index leaks into the frequency pair.

### So it is a defect, not an inaudible residual

This is the branch the task's verify asks to be chosen between, and the
evidence picks it. The differing frames carry real waveform changes on a real
voice, including a TEST bit that silences an oscillator the original leaves
ringing. It is a release-tail and timbre difference rather than a wrong note,
which is exactly the class a gate-on-only "audible" column cannot see (see
`docs/players/MATTGRAY.md` for the same blindness stated there). **Do not quote
the 98.73% as inaudible.**

Not diagnosed here: *why* frame 586 — what the song does there, and which
table our converter attaches to voice 1 at that point. That is where the next
attempt starts; the span, the period, the three registers and the lo==hi tell
are all measured and need no re-deriving.
