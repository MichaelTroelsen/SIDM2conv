# SIDM2 Conversion Accuracy Matrix
**Single Source of Truth for Accuracy Data**

**Version**: 3.13.0
**Last Updated**: 2026-07-05
**Status**: ✅ Production Reference — rewritten for the native-driver era (Galway/FC/ROMUZAK/MoN)

---

## Quick Reference — wired pipeline (auto driver selection)

| Source Player | Best Driver | Accuracy | Status |
|---------------|-------------|----------|--------|
| **Laxity NewPlayer v21** (native) | Laxity Driver | **99.93–100%** | ⭐⭐⭐⭐⭐ Production (filter 100%, Stinsen-verified) |
| **SF2-exported SID** (incl. SidFactory_II/Laxity) | Driver 11 | **100%** | ⭐⭐⭐⭐⭐ Guaranteed |
| **Martin Galway** (Stage A default) | Driver 11 transpile | notes/timing exact; timbre approximated | ⭐⭐⭐ Editable |
| **NewPlayer 20.G4** | NP20 Driver | **70–90%** | ⭐⭐⭐ Best effort |
| **Unknown Player** | Driver 11 | varies | ⭐⭐ Safe default |

**⚠️** "Laxity" can mean the AUTHOR (SF2-exported → Driver 11) or the PLAYER FORMAT (→ Laxity driver). Check player-id output.

## Quick Reference — native-driver builds (`bin/`, not yet registry-wired)

Per-frame register fidelity (freq / waveform / pulse / filter) measured vs the original SID; "byte-exact" = 100% on every register over the full song.

| Source Player | Entry point | Fidelity | Status |
|---------------|-------------|----------|--------|
| **Martin Galway** (40-tune corpus) | `bin/build_galway_trace_song.py`, corpus `bin/build_galway_corpus.py` | ~100% on every register for validated tunes; **30/40 objectively clean in real SF2II** (≥95% freq, ≥90% pulse), 40/40 build | ✅ [GALWAY.md](../players/GALWAY.md) |
| **Maniacs of Noise / Jeroen Tel** — Hawkeye | `bin/build_mon_native_song.py` | **100% byte-exact** (freq+wf+pulse+filter, 3 voices, full length) subtunes 2 & 3; sub0 windowed 13 parts (filter ~75% seams) | ✅ [MON.md](../players/MON.md) |
| — Cybernoid / Cybernoid II | same | ~95-100 / ~99-100 / ~100 / ~99 per register (11-20 parts) | ✅ |
| — Myth (sub0, sub2) | `bin/build_myth_native_song.py` | freq/wf/pulse ~100%, filter ~90-96% | ✅ (emulation-extracted) |
| — Supremacy (3 subtunes) | `bin/build_mon_native_song.py` | freq 96-99, wf/pulse ~99.8-100, filter 100 (24-70 parts — part-count frontier) | ✅ |
| **ROMUZAK V6.3** (2 tunes) | `bin/build_romuzak_native_song.py` | note/orderlist-exact + byte-exact wf/pulse/AD-SR (~98-100%) | ✅ [ROMUZAK.md](../players/ROMUZAK.md) |
| **Future Composer** ($1800 variant) | `bin/fc_to_sf2.py` | Stage A only: notes/order trace-validated | 🚧 [FUTURECOMPOSER.md](../players/FUTURECOMPOSER.md) |

## Editor-view clusters (inside the Laxity path)

Audio is 100% (embedded binary); these rows describe **editor** fidelity — see [CLUSTERS.md](../players/CLUSTERS.md).

| Cluster | Editor status |
|---------|---------------|
| Stinsen / Beast / Angular (NP21 variants) | F1-F5 wired, edits propagate, zig64-verified |
| DRAX (4 files) | instrument table resolved; full wiring pending |
| Vibrants 2000 A.D. (2 files) | F1 populated (notes + per-pattern transpose) |
| Wizax-A / Zetrex-YP / V20 umbrella | detection + audio recovery; editor view deferred |

## Anti-matrix (known-bad pairings — do not use)

| Source → Driver | Accuracy | Instead |
|-----------------|----------|---------|
| Native Laxity NP21 → Driver 11 | 1–8% | Laxity driver |
| MoN → Stage-A Driver 11 for *sound* | notes exact, timbre flat | native build (`bin/build_mon_native_song.py`) |
| Rob Hubbard → anything | no pipeline exists | future work |

---

## Understanding the metrics

- **Frame accuracy** (wired pipeline): % of frames whose SID register writes match the original byte-for-byte.
- **Per-register fidelity** (native builds): per-frame match rate per register class — freq (semitone-based), waveform, pulse, AD/SR, filter cutoff — per voice, over the real song length (post-`$FE` silence excluded).
- **Byte-exact**: 100% on every tracked register for every frame of the song. The project's crown-jewel standard (MoN Hawkeye sub2/3 achieve it).
- **Objective SF2II validation**: the instrumented editor's *actual* playback captured and diffed (`bin/sf2ii_vs_real.py`) — the truth-teller; headless metrics historically overstate (Galway "37 faithful" → 30/40 objective).

Measurement tools ladder: onset validators (`*_validate.py`) → per-frame fidelity (`mon_part_fidelity.py`, `romuzak_native_validate.py`) → real-SF2II capture (`sf2ii_vs_real.py`) → VICE audio A/B (`listen_compare.py`). See [PLAYBOOK.md §4](../players/PLAYBOOK.md).

---

## History

Pre-v3.13 versions of this file covered only Laxity/Driver11/NP20/Hubbard; the v3.1.1 edition (2026-01-02) is preserved in git history. Per-version accuracy narrative: `CHANGELOG.md` / `STORY.md`.
