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
> **16 of 17 files are at exactly 100.00% on BOTH columns** — not just the
> lenient per-frame mean but exact frame-for-frame identity, 1500/1500. The sole
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
| `sidm2/sequence_translator.py:233` | `(b & $1F) + 1` → 1..32 | **wrong mask** — folds bit 4 into the count; the `+1` is right |
| `pyscript/sf2_viewer_core.py` `unpack_sequence` | `b & $0F`, bit 4 = tie | **right mask and right bit-4 split — but no `+1`**, so every duration is one frame short |
| `CLAUDE.md` Laxity constants | `$80 = GATE_OFF` | **wrong for the sequence stream** — `$80` is a duration byte whose nibble is 0, i.e. one frame |

⚠️ **The `$100,X` flag is not purely a "tie".** The same location is incremented
at line 140 when the NOTE byte is `$00` or `$7E`. So it is a shared
gate/continue flag that bit 4 is one input to, and calling it `tie` in a decoder
is a simplification that happens to work rather than the player's own model.

### Why the code was NOT changed when this was established

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

**Both fixes are correct and neither is safe to ship unverified.** They want a
task that declares the converter corpus and re-measures the headline figure on
both arms.

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
