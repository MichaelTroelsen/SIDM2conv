# Laxity NewPlayer v21 (NP21) — SID → SF2 support

**Player:** Laxity NewPlayer v21 and forks
**Registry key:** `laxity`
**Driver:** `sf2driver_laxity_00.prg`
**Accuracy:** **99.93–100%** (production — the flagship supported player)
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
