# Driver 11 — SF2-exported files & safe default

**Player:** SID Factory II's own Driver 11 (any SF2-exported file)
**Registry key:** `driver11`
**Driver:** `sf2driver11_00.prg`
**Accuracy:** **100%** for SF2-exported files; **safe default** for unknown players
**Corpus:** round-trip test files; the fallback for anything unrecognised

When a SID was **exported from SID Factory II**, it already uses Driver 11's structure — so converting it back to SF2 with Driver 11 preserves the exact tables and gives **100%** fidelity. Driver 11 is also the **safe default** when the player can't be identified.

---

## player-id strings → Driver 11
`SidFactory_II` · `SidFactory` · `SF2_Exported` · `Driver_11`
…plus the **author-Laxity SF2 exports** `SidFactory_II/Laxity` and `SidFactory/Laxity` (exported *by* Laxity, but Driver 11 internally).

> Critical: `SidFactory_II/Laxity` ≠ native Laxity. "SidFactory" in the player-id → Driver 11; `Laxity_NewPlayer_V21` → the Laxity driver.

---

## Driver 11 versions
| Version | Changes |
|---------|---------|
| 11.00 | Original default driver (the template used here) |
| 11.01 | + fret-slide command |
| 11.02 | + pulse/tempo/volume commands |
| 11.03 | + additional filter-enable flag |
| 11.04 | + note-event delay |
| 11.05 | fret-slide removed, HR table 16→8 rows, skip-pulse-reset flag |

Driver `.prg` files live in `bin/drivers/sf2driver11_0X.prg`; F12 command overlays in `bin/overlay/<os>_driver11_0X.png`.

---

## Convert
```bash
sid-to-sf2.bat input.sid out.sf2 --driver driver11
```

It is also the foundation the **Galway** Stage-A transpile targets (see [GALWAY.md](GALWAY.md)) and the table format the native Galway driver reuses.

**Tables (SF2 Driver 11):** `SEQ=$0903`, `INST=$0A03`, `WAVE=$0B03`, `PULSE=$0D03`, `FILTER=$0F03`. Format spec: `docs/reference/SF2_FORMAT_SPEC.md`.
