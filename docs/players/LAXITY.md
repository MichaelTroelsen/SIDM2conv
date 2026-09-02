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
