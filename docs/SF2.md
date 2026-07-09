# SF2 Build Index — fidelity, original player, and SF2 driver

A consolidated list of the SF2 files SIDM2 produces: the **original player** (the C64 music
routine the SID was written with), the **SF2 driver** that plays the converted file, and the
measured **fidelity**. See [`docs/reference/ACCURACY_MATRIX.md`](reference/ACCURACY_MATRIX.md)
for the source-of-truth accuracy data and [`docs/players/`](players/) for per-player detail.

**Fidelity** is per-frame register match vs the original SID, per voice, as **freq / waveform /
pulse [/ filter]** (%). **100/100/100** = byte-exact on all three oscillators (the crown
standard). "Original player" = the source C64 routine; "SF2 driver" = the target driver the
converted SF2 runs on (a stock **Driver 11**, the native **Laxity** driver, or a from-scratch
**native** driver we authored — see [`docs/players/NATIVE_DRIVER.md`](players/NATIVE_DRIVER.md)).

---

## Summary by player

| Original player | Composer | SF2 driver | Corpus | Fidelity | Wired? |
|---|---|---|---|---|---|
| Laxity NewPlayer v21 | Laxity & others | **Laxity** (native) | `SID/Laxity/` (286) + `SID/` root | **99.93–100%** (filter 100%) | ✅ auto |
| SF2-exported (incl. `SidFactory_II/Laxity`) | any | **Driver 11** | round-trip | **100%** | ✅ auto |
| Martin Galway | Martin Galway | native (Stage A → Driver 11) | `SID/Galway_Martin/` (40) | native ~100%; **30/40 objectively clean** in SF2II | Stage A auto; native `bin/` |
| Maniacs of Noise | Jeroen Tel | **native** (MoN) | `SID/Tel_Jeroen/` | **100/100/100/100** (Hawkeye sub 2·3) | `bin/` |
| ROMUZAK V6.3 | Oliver Blasnik | **native** (ROMUZAK) | `SID/Fun_Fun/` (2) | byte-exact wf/pulse/AD-SR (~98–100%) | `bin/` |
| Rob Hubbard V1 | Rob Hubbard | **native** (MoN engine) | `SID/Hubbard_Rob/` | pulse/freq/filter **100%** | `bin/` |
| Rob Hubbard V2 (Delta) | Rob Hubbard | **native** | `SID/Hubbard_Rob/` | Delta theme freq/pulse/filter 100% (wf 85–96) | `bin/` |
| DMC (Demo Music Creator) | Johannes Bjerregaard | **native** (MoN engine) | `SID/JohannesBjerregaard/` (88) | see below; **33 eligible** | `bin/` |
| Future Composer ($1800) | Michael Troelsen | Driver 11 (Stage A) | `SID/Fun_Fun/` | notes/order trace-validated | `bin/` |
| NewPlayer 20.G4 | various | NP20 | `SID/` (NP20 variants) | 70–90% | ✅ auto (registry) |

---

## Byte-exact hall of fame — 100/100/100 on all three voices

The tunes that reproduce **frequency + waveform + pulse** byte-exact on every oscillator:

| Tune | Original player | SF2 driver |
|---|---|---|
| **Hawkeye** (subtunes 2 & 3, full length, +filter) | Maniacs of Noise (Jeroen Tel) | native MoN |
| **Ocean Loader** (9 min) | Martin Galway | native Galway |
| **Wizball** (default, 135 s) | Martin Galway | native Galway |
| **Delirious 9 / Road of Excess** | ROMUZAK (Blasnik) | native ROMUZAK |
| **Monty / Commando / Zoids / Last V8 / …** (V1, pulse+freq+filter) | Rob Hubbard | native |
| **In_the_Mood** | DMC (Bjerregaard) | native |
| **M_A_C_H** | DMC (Bjerregaard) | native |
| **Fourth_Dimension** | DMC (Bjerregaard) | native |

*(Laxity NP21 and SF2-exported tunes are byte-exact by construction across their whole
corpora and are not enumerated here — see the summary table.)*

---

## DMC (Johannes Bjerregaard) — per-tune fidelity

Native build: `py -3 bin/build_dmc_native_song.py SID/JohannesBjerregaard/<tune>.sid auto`.
Per-voice **freq/wf/pulse** measured over a 15 s window (the real `auto` multi-part build
scores higher on legato voices — see [`docs/players/DMC.md`](players/DMC.md)). All use the
**native** driver. **33 of 88** files are onset-eligible; the strongest measured:

| Tune | osc1 | osc2 | osc3 | Notes |
|---|---|---|---|---|
| **In_the_Mood** | 100/100/100 | 100/100/100 | 100/100/100 | byte-exact |
| **M_A_C_H** | 100/100/100 | 100/100/100 | 100/100/100 | byte-exact |
| **Fourth_Dimension** | 100/100/100 | 100/100/100 | 100/100/100 | byte-exact |
| Deel_2 | 100/94/90 | 98/100/100 | 100/100/100 | interleaved-track gen |
| Rockbuster | 97/100/100 | 98/96/100 | 93/100/100 | the headline (freq 65→97) |
| Dreaming | 100/100/100 | 100/100/100 | 90 (freq, A/B) | osc3 39→90 via legato A/B |
| Zoom | 100/99/97 | 95/99/100 | 91/99/100 | |
| Slimbo4 | 98/100/98 | 99/100/91 | 97/100/56 | interleaved-track gen |
| Twilight_Beyond | 100/100/100 | 96/100/87 | 87/100/64 | indexed-store gen |
| Spy_vs_Spy_III | 100/100/100 | 90/94/84 | 89/89/84 | indexed-store gen |
| Special_Agent | 100/100/100 | 57/100/1 | 100/100/100 | osc2 pulse open |
| Thunder_Force | 100/100/100 | 96/100/86 | 96/100/92 | absolute-store gen |
| Fruitbank | 96/98/94 | 91/98/89 | 96/96/82 | interleaved-track gen |
| Scandalous | 87/100/29 | 100/100/100 | 99/100/76 | osc1 pulse open |
| Predictable_main | 100/100/100 | 100/50/100 | 100/50/100 | wf open on osc2/3 |
| Blobby | 87/100/100 | 100/100/100 | 100/100/100 | base-note fix (osc1 75→87) |
| Wanna_Get_Sick | 100 (freq) | 94 (freq) | 94 (freq) | base-note fix (osc1 66→100) |
| Tiny_Symphony | 100 (freq) | 75 (freq) | 98 (freq) | base-note fix |
| First_Try_PSX | 82/85/92 | 83/87/47 | 84/88/73 | split-freq gen |
| Fat_6 | 61/74/66 | 46/74/66 | 94/92/82 | split-freq gen |
| Alf_TV_Theme · Music_Demo · Test | *(newly eligible — ADC-vibrato freq gen; build, not yet measured)* | | | |

Other eligible (build, not individually measured here): Billie_Jean, Cant_Stop, Chase_v2,
DMC_Demo_IV_tune_1, Dreaming_2, MSI_Demo, Namnam_Special, Omega_Force_One, Shape, Some_Soul.

**DMC generations decoded** (why a file is eligible): the parser is relocation-safe and now
handles the interleaved/split freq table, three sound-record idioms (state / absolute-store /
indexed-store), and the interleaved-track + ADC-vibrato-freq generations. ~32 files remain
NO-TABLES (further per-generation RE — Stormlord, Flimbos_Quest, Crazy_Comets_remix, …).

---

## Maniacs of Noise (Jeroen Tel) — native

| Tune | Fidelity (freq/wf/pulse/filter) | Notes |
|---|---|---|
| **Hawkeye** sub 2 & 3 | **100/100/100/100** | byte-exact, full length, single editable SF2 |
| Hawkeye sub 0 | ~100 pitch/wf/pulse (13×30 s parts) | filter ~75% at window seams |
| Cybernoid I | ~95–100 / ~99–100 / ~100 / ~99 | 11–20 parts |
| Cybernoid II | ~99–100 per register | |
| Myth (sub 0, sub 2) | freq/wf/pulse ~100, filter ~90–96 | emulation-extracted |
| Supremacy (3 subtunes) | freq 96–99, wf/pulse ~99.8–100, filter 100 | 24–70 parts |

Build: `bin/build_mon_native_song.py` / `bin/build_myth_native_song.py`. Driver: native MoN.

---

## Martin Galway — native

40-tune corpus; **30/40 objectively clean** in real SF2II (≥95% freq, ≥90% pulse), 40/40
build. Confirmed byte-exact set includes **Ocean Loader** (9 min) and **Wizball** (135 s
default) at ~100% on every register; **Rambo** and **Terra Cresta** validated. Build:
`bin/build_galway_trace_song.py` (corpus `bin/build_galway_corpus.py`). Driver: native Galway.

---

## Rob Hubbard — native

| Set | Fidelity | Notes |
|---|---|---|
| **V1** (~12 tunes + subsongs: Monty, Commando, Zoids, Last V8, Gremlins, …) | pulse + freq + filter **100%** | per-instrument HP pulse engine (exact by construction) |
| **V2 / Delta** (6 split-songs built) | Delta theme freq/pulse/filter **100%** (wf 85–96) | swallow-tempo, split song tables |

~19 tunes build, ~28 decode ≥95%. Build: `bin/build_hubbard_native_song.py`
(corpus `bin/hubbard_build_all.py`). Driver: native (shared MoN engine).

---

## ROMUZAK V6.3 (Oliver Blasnik) — native

| Tune | Fidelity | Notes |
|---|---|---|
| **Delirious_9_tune_1** | note/orderlist-exact + byte-exact wf/pulse/AD-SR (~98–100%) | full song loop |
| **Road_of_Excess_end** | same | |

Build: `bin/build_romuzak_native_song.py`. Driver: native ROMUZAK.

---

## Wired pipeline (auto driver selection) — the production converter

| Original player | SF2 driver | Fidelity | Corpus |
|---|---|---|---|
| **Laxity NewPlayer v21** (native) | **Laxity** | **99.93–100%** (filter 100%, Stinsen-verified) | `SID/Laxity/` (286) + `SID/` root |
| **SF2-exported** (incl. `SidFactory_II/Laxity`) | **Driver 11** | **100%** | round-trip |
| **NewPlayer 20.G4** | NP20 | 70–90% | NP20 variants |
| Unknown | Driver 11 (safe default) | varies | — |

`sid-to-sf2.bat input.sid output.sf2` auto-selects the driver by player-id. **Trap:**
`SidFactory_II/Laxity` = *exported by author Laxity* → Driver 11, **not** the Laxity driver.

---

*Generated 2026-07-09. Fidelity figures are the latest measured/documented values; native
builds live in `bin/` and are not yet registry-wired into the auto pipeline. For the method
behind the numbers see [`docs/players/PLAYBOOK.md`](players/PLAYBOOK.md).*
