# Players — SID → SF2 support index

One document per **player** (the C64 music routine a SID file was made with). SIDM2 auto-selects a driver by player type via `DriverSelector.PLAYER_REGISTRY` (`sidm2/driver_selector.py` — the single source of truth for the *wired* pipeline). Several newer players live in `bin/` and are not yet registry-wired — see the table.

> **Cross-player methodology** (how a new player gets ported, the shared native-driver pipeline, size caps, gotchas): [PLAYBOOK.md](PLAYBOOK.md).
> **Technique catalog** (named recurring mechanisms, diagnostics, failure classes - the pattern library): [PATTERNS.md](PATTERNS.md).
> **The target native drivers we authored** (memory map + feature flags of the from-scratch SF2 drivers): [NATIVE_DRIVER.md](NATIVE_DRIVER.md).
> **Accuracy numbers**: [../reference/ACCURACY_MATRIX.md](../reference/ACCURACY_MATRIX.md).

**Source vs target:** most docs below describe a **source** player (the C64 routine we convert *from*). The trace-driven ports (Galway, MoN, ROMUZAK, Hubbard) also required us to author a **target** — a from-scratch native SF2 driver; those are documented together in [NATIVE_DRIVER.md](NATIVE_DRIVER.md). Open per-player work has its own plan doc (e.g. [HUBBARD_V2_PLAN.md](HUBBARD_V2_PLAN.md)).

| Player | Doc | Path | Fidelity | Corpus |
|--------|-----|------|----------|--------|
| **Laxity NewPlayer v21** | [LAXITY.md](LAXITY.md) | wired (`laxity`) | 99.93–100% | `SID/Laxity/` (286) + `SID/` root |
| **SF2-exported / Driver 11** | [DRIVER11.md](DRIVER11.md) | wired (`driver11`, default) | 100% (SF2-exported) | round-trip / safe default |
| **NewPlayer 20** | [NP20.md](NP20.md) | wired (`np20`, registry-only) | 70–90% | `SID/` (NP20.G4 variants) |
| **Martin Galway** | [GALWAY.md](GALWAY.md) | Stage A wired (`galway`); native in `bin/` | native ~100% (30/40 objectively clean in real SF2II) | `SID/Galway_Martin/` (40) |
| **Maniacs of Noise (Jeroen Tel)** — Hawkeye, Cybernoid I/II, Myth, Supremacy | [MON.md](MON.md) | `bin/` only | **100% byte-exact** (Hawkeye sub 2/3, full length); others ~95-100% per register | `SID/Tel_Jeroen/` (179) |
| **ROMUZAK V6.3** | [ROMUZAK.md](ROMUZAK.md) | `bin/` only | native: byte-exact wf/pulse/AD-SR (~98–100%) | `SID/Fun_Fun/` (Delirious, Road_of_Excess) |
| **Rob Hubbard** (V1 + V2/Delta) — Monty, Commando, Zoids, Last V8, Delta, Lightforce, … | [HUBBARD.md](HUBBARD.md) | `bin/` only | V1 native: pulse/freq/filter **100%**; V2 Delta theme 100% (wf 85–96%) | `SID/Hubbard_Rob/` (95); ~19 built, ~28 decode ≥95% |
| **DMC (Demo Music Creator)** — Johannes Bjerregaard | [DMC.md](DMC.md) | `bin/` only | native: **Rockbuster ≈97%** (freq/wf/pulse); 21/43 onset-eligible, most 2/3 voices 90–100% | `SID/JohannesBjerregaard/` (88) |
| **Sound Monitor (Musicmaster)** — Chris Hülsbeck '86 | [SOUNDMONITOR.md](SOUNDMONITOR.md) | `bin/` only | Stage A 32/33 voices note-accurate; native: Final_Luv 98–99.9 skew-tolerant every register (1 part / 161s) | `SID/Fun_Fun/` (11 × `$C000/$C475`) |
| **SID Duzz' It (SDI)** — Gallefoss/Tjelta | [SDI.md](SDI.md) | `bin/` only (Stage A) | 6 variants decoded; strict medians A 98/D 100/C 67/B 75/E 58/V 22; 254 Stage A SF2s, 0 failures | `SID/Gallefoss_Glenn/` (~350) |
| **Jeroen Kimmel** (Hubbard-derived) — Radax, The Judges | [KIMMEL.md](KIMMEL.md) | `bin/` only | **11/12 voice-medians exact 100%** (frame-pitch); arp/PWM/freq-slide/drum ported | `SID/Red_kommel_jeroen/` (4; Radax × 6 subtunes) |
| **Charles Deenen** (MoN/Deenen replay + dialects) | [DEENEN.md](DEENEN.md) | `bin/` only | 4 clean wins ~100% (10/19 located) + 8 freebies at 100% | `SID/deenen/` (40) |
| **Future Composer** | [FUTURECOMPOSER.md](FUTURECOMPOSER.md) | `bin/` only | Stage A: notes/order trace-validated | `SID/Fun_Fun/` ($1800 variant, 5/20) |
| **NP21-adjacent clusters** (Stinsen/Beast/Angular, DRAX, 2000 A.D., Wizax, Zetrex/V20) | [CLUSTERS.md](CLUSTERS.md) | inside the Laxity path | audio 100%; editor-view varies | `SID/` root + Laxity corpus |

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
| Rob Hubbard — remaining V2 laggards | `SID/Hubbard_Rob/` (~13 of 95) | IK+/Thundercats/Tarzan/Mega_Apocalypse/Knucklebusters/Game_Killer note-format & speed variants; 6 no-signature files (Casio_Extended cluster); the swallow-class state-region relocation. See [HUBBARD.md](HUBBARD.md). |
| Future Composer (non-$1800 variants) | `SID/Fun_Fun/` (15/20) | Needs player-base detection; format already RE'd. |
| Jeroen Tel non-MoN / remaining MoN tunes | `SID/Tel_Jeroen/` | The MoN parser + native pipeline generalize; each new tune may need an orderlist-model variant (5 exist so far). Includes the **72-file MoN/Deenen group** — see [DEENEN.md](DEENEN.md). |
| Charles Deenen — Variant B + ZP-loop variants | `SID/deenen/` (9 of 19 replay files, + 15 MoN/FutureComposer) | Variant-B "Smooth-class" groove+reloc (~4 files), the Astro/Mr_Heli `$88,X` ZP-loop orderlist engine, and 9 not-located. See [DEENEN.md](DEENEN.md). |
| DMC — legato / multispeed variants | `SID/JohannesBjerregaard/` (~22 of 88) | Self-IRQ/multispeed timing (Chase), the 0%-variant track signature, and a latent mid-note `+$40xx` FM-encoding collision. Per-voice base-note **resolved** (adaptive `_sem`). Format RE'd; see [DMC.md](DMC.md). |

**Adding a player** (3 steps): (1) add to `PLAYER_REGISTRY` in `sidm2/driver_selector.py`; (2) add to `PLAYER_EXTRACTORS`/`PLAYER_CONVERTERS` in `sidm2/conversion_pipeline.py`; (3) implement an analyzer extending `player_base.BasePlayerAnalyzer`. For the full staged porting method (Stage A transpile → Stage B native driver) see [PLAYBOOK.md](PLAYBOOK.md).
