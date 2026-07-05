# NP21-adjacent clusters — editor-view support inside the Laxity pipeline

These are not standalone player pipelines. They are **variant clusters detected inside the default Laxity/NP21 conversion path** (`sidm2/laxity_raw_np21_builder.py`, `np21_edit_area_builder.py`): audio always works via the embedded-binary path; the cluster work is about wiring the **editor view** (F1 orderlists/sequences, F2 instruments, F3 wave, F4 pulse, F5 filter) and, where possible, edit propagation.

| Cluster | Files | Detector(s) | Editor status |
|---------|-------|-------------|---------------|
| **Stinsen** (NP21, column-major tables) | Stinsen's_Last_Night_of_89 + class | `stinsen_instr/pulse/filter_detector.py` | F1-F5 wired, edits propagate (Stage 7); zig64-verified |
| **Beast / Angular** (NP21, row-major) | Beast.sid, Angular.sid + class | `beast_*`, `angular_*` detectors | F1-F5 wired (cutoff streams, 4-byte pulse records) |
| **DRAX** (Thomas Mogensen NP21 fork) | Colorama, Delicate, Dreams, Omniphunk (SID/ root) | `drax_record_table_detector.py` | Instrument table **located + resolved** (8-byte records at detector-operand−2, byte0=AD byte1=SR, ≤32 instruments); full F1-F5 wiring is multi-day, not done |
| **Vibrants 2000 A.D.** (1988 pre-NP21) | Echo_Beat, Galax_it_y | `vibrants_2000ad_detector.py` + extractor | F1 populated (chromatic notes, per-pattern transpose); RE drained v3.5.62 |
| **Wizax-A** (1987-90 byte-stream) | 4-file cluster | `wizax_a_detector.py` | Streams RE'd (NP21-compatible bytes); F1 implementable, deferred |
| **Zetrex / YP** (shared $E000 player) | Jewels, Waste + class | `zetrex_yp_detector.py` | V20-gate recovery (audio C2); editor view empty |
| **V20 umbrella** (5+ pre-NP21 variants, 14 Class-C files) | various | `vibrants_v20_detector.py` | Deferred — audio works, full support = multi-week per variant |

## Lessons this cluster work established (apply to all binary-format RE)

- **Confirm the record stride before claiming a table's format.** DRAX's `$1B8A` was mislabeled a flat wave table (v3.5.67), corrected to 8-byte records (v3.5.68), resolved as the instrument table (v3.5.69). Dump the data and check periodicity first.
- **Never generalize a layout from one file.** DRAX scratch addresses are file-relocated; each file must be confirmed independently (v3.5.70 did this via backward dataflow from the fixed `STA $D40x,Y` output writes — the only per-file-robust anchor).
- **Trace backward from SID register writes**, not forward from guessed table addresses.
- These detectors are **FALLBACK-only** where noted (the DRAX idiom also matches pulse/filter sites in Beast/Angular).

Deep references: `memory/drax-np21-cluster-re.md`, `vibrants-2000ad-cluster-re.md`, `wizax-a-byte-stream-re.md`, `vibrants-v20-findings.md`, and per-table memories (`stinsen-*`, `beast-angular-*`).
