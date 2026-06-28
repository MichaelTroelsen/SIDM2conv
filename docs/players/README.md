# Players — SID → SF2 support index

One document per **player** (the C64 music routine a SID file was made with). SIDM2 auto-selects a driver by player type via `DriverSelector.PLAYER_REGISTRY` (`sidm2/driver_selector.py` — the single source of truth).

| Player | Doc | Driver | Accuracy | Corpus |
|--------|-----|--------|----------|--------|
| **Laxity NewPlayer v21** | [LAXITY.md](LAXITY.md) | `sf2driver_laxity_00.prg` | 99.93–100% | `SID/Laxity/` (286) + `SID/` root |
| **SF2-exported / Driver 11** | [DRIVER11.md](DRIVER11.md) | `sf2driver11_00.prg` | 100% (SF2-exported) | round-trip / safe default |
| **NewPlayer 20** | [NP20.md](NP20.md) | `sf2driver_np20_00.prg` | 70–90% | `SID/` (NP20.G4 variants) |
| **Martin Galway** | [GALWAY.md](GALWAY.md) | native (`bin/`) / Driver 11 transpile | ~100% (validated tunes) | `SID/Galway_Martin/` (40) |
| **Future Composer V1.0** | [FUTURECOMPOSER.md](FUTURECOMPOSER.md) | Driver 11 transpile (`bin/fc_to_sf2.py`) | notes/order byte-exact; trace-driven pulse/filter | `SID/Fun_Fun/` ($1800 variant, 5) |
| **ROMUZAK V6.3** | [ROMUZAK.md](ROMUZAK.md) | Driver 11 transpile (`bin/romuzak_to_sf2.py`) | notes/order byte-exact (Delirious); sounds Stage-A | `SID/Fun_Fun/` (Delirious, Road) |

## Player-id → driver mapping

`player-id.exe` emits a player string; the registry maps it to a driver:

| player-id string | Driver |
|------------------|--------|
| `Laxity_NewPlayer_V21`, `Vibrants/Laxity`, `256bytes/Laxity` | Laxity |
| `SidFactory_II/Laxity`, `SidFactory/Laxity` | **Driver 11** (SF2-exported *by* Laxity, not native!) |
| `SidFactory_II`, `SidFactory`, `SF2_Exported`, `Driver_11` | Driver 11 |
| `NewPlayer_20`, `NewPlayer_20.G4`, `NP20` | NP20 |
| `Martin_Galway`, `Galway` | Galway |
| *unknown* | Driver 11 (safe default) |

> **Trap:** `SidFactory_II/Laxity` means a file *exported from SF2 by author Laxity* → use **Driver 11**, NOT the Laxity driver. Only `Laxity_NewPlayer_V21` etc. are native Laxity.

## Not yet supported (future work)

| Composer | Corpus | Notes |
|----------|--------|-------|
| Rob Hubbard | `SID/Hubbard_Rob/` (95) | Per-channel bytecode interpreter (Galway-shaped problem). Embed for audio; editor fidelity is the hard part. |
| Jeroen Tel | `SID/Tel_Jeroen/` (179) | Not in registry. |
| Fun Fun | `SID/Fun_Fun/` (20) | Not in registry. |

**Adding a player** (3 steps): (1) add to `PLAYER_REGISTRY` in `sidm2/driver_selector.py`; (2) add to `PLAYER_EXTRACTORS`/`PLAYER_CONVERTERS` in `sidm2/conversion_pipeline.py`; (3) implement an analyzer extending `player_base.BasePlayerAnalyzer`. See `docs/reference/ACCURACY_MATRIX.md`.
