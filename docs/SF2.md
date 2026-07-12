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
| DMC (Demo Music Creator) | Johannes Bjerregaard | **native** (MoN engine) | `SID/JohannesBjerregaard/` (88) | see below; **56 eligible** (within-frame onsets, 2026-07-11) | `bin/` |
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
**native** driver. **56 of 88** files are onset-eligible (within-frame onset detection unlocked 15 more, 2026-07-11 — see `docs/players/DMC.md`); the strongest measured:

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

**DMC generations decoded** (why a file is eligible — **41 of 88** now): the parser is
relocation-safe and handles three freq layouts (interleaved / split / ADC-vibrato / staged),
five sound-record idioms (state / absolute-store / indexed-store / state-copy / staged-emit),
and the interleaved-track generation. **2026-07-11: within-frame onset detection** (the
note-set retriggers gate OFF+ON inside one play call — invisible to end-of-frame state)
unlocked 15 more files (Balloon wf 0->100 / pulse 0->100, Domino_Dancing, Cant_Stop, the
Jazz set…): survey now **56 ELIGIBLE / 18 FALLBACK / 14 NO-TABLES**, all 56 build clean.

---

## Maniacs of Noise (Jeroen Tel) — native

| Tune | Fidelity (freq/wf/pulse/filter) | Notes |
|---|---|---|
| **Hawkeye** sub 2 & 3 | **100/100/100/100** | byte-exact, full length, single editable SF2 |
| Hawkeye sub 0 | ~100 pitch/wf/pulse (13×30 s parts) | filter ~75% at window seams |
| **Cybernoid II** sub 0 | **100/100/100** (part01) | rest-tail fix 2026-07-10; 13 parts |
| Cybernoid I | 97–100 freq / **100 wf** / **100 pulse** | rest-tail fix; 13 parts |
| Myth (sub 0, sub 2) | freq/wf/pulse ~100, filter ~90–96 | emulation-extracted |
| **Supremacy** sub 1 | **99.9 × every register** | rest-tail fix (was 94.3 wf); 2 parts |
| Supremacy sub 0 / sub 2 | sub0 ~78–90 (structural); sub2 94–100 (osc2 = pure ±1-frame write-jitter — **100 skew-tolerant**, audibly exact) | 13 / 10 parts (was 16/70 incl. stale) |

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

<!-- BEGIN GENERATED: build inventory -->

## Complete build inventory

**199 songs built** across 6 native players (each song may span several SF2 parts).

*Auto-generated from the built SF2 files under `out/` by `pyscript/gen_sf2_index.py` — re-run after building more tunes. "Parts" = the number of SF2 files a song is split into (a long song exceeds the SF2II table/`$D000` caps and ships as windowed parts; 1 = a single file).*

### DMC (Demo Music Creator) — Johannes Bjerregaard  ·  `native`  ·  57 songs / 944 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Again Its JB | Johannes Bjerregaard | 1989 Upfront | 12 |
| Alf TV Theme | Johannes Bjerregaard | 1988 Maniacs of Noise | 40 |
| Balloon | Johannes Bjerregaard | 1990 Johannes Bjerregaard | 1 |
| Billie Jean | Johannes Bjerregaard | 1990 Johannes Bjerregaard | 15 |
| Blobby | Johannes Bjerregaard | 19?? Johannes Bjerregaard | 2 |
| Blue Monday 88 | Johannes Bjerregaard | 1989 The Dominators | 7 |
| Camel Riders Inc | Johannes Bjerregaard (The Jerk) | 1987 The Jerk | 12 |
| Cant Stop | Johannes Bjerregaard | 1988 Upfront | 114 |
| Chase v2 | Johannes Bjerregaard | 1988 Johannes Bjerregaard | 11 |
| Cute Tune | Johannes Bjerregaard | 1988-90 Johannes Bjerregaard | 38 |
| Deel 2 | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 8 |
| Depeche Mode Songs | Johannes Bjerregaard | 1986 Danish Music Company | 6 |
| DMC Demo IV tune 1 | Johannes Bjerregaard | 1988 Danish Music Company | 7 |
| DMC Demo IV tune 2 | Johannes Bjerregaard | 1988 Danish Music Company | 15 |
| DMC Demo IV tune 3 | Johannes Bjerregaard | 1988 Danish Music Company | 16 |
| Domino Dancing | Johannes Bjerregaard | 1988 Maniacs of Noise | 7 |
| Dragon Sword | Johannes Bjerregaard | 2018 Johannes Bjerregaard | 7 |
| Dreaming | Johannes Bjerregaard | 1988 Danish Music Company | 15 |
| Dreaming 2 | Johannes Bjerregaard | 1987 Danish Music Company | 28 |
| Dummy II | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 11 |
| Dummynaytos | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 1 |
| Eagles | Johannes Bjerregaard | 1987 Hewson | 7 |
| Fat 6 | Johannes Bjerregaard | 1988 Johannes Bjerregaard | 23 |
| First Try PSX | Johannes Bjerregaard | 1988 Johannes Bjerregaard | 47 |
| Fourth Dimension | Johannes Bjerregaard | 1988 Danish Music Company | 6 |
| French Frites | Johannes Bjerregaard | 1990 Johannes Bjerregaard | 64 |
| Fruitbank | Johannes Bjerregaard | 1989 Mastertronic/Dig. Design | 11 |
| Hit the Baze | Johannes Bjerregaard | 1988 Danish Music Company | 10 |
| In the Mood | Johannes Bjerregaard | 1988 Triton Technology | 3 |
| Jazz 1 | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 31 |
| M A C H | Johannes Bjerregaard | 1987 Starvision | 2 |
| Mixerplot | Johannes Bjerregaard | 1989 Upfront | 9 |
| MSI Demo | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 36 |
| Music Demo | Johannes Bjerregaard | 1988 Maniacs of Noise | 32 |
| Myth Demo | Johannes Bjerregaard | 1989 Maniacs of Noise | 11 |
| Namnam Special | Johannes Bjerregaard | 1988 Danish Music Company | 20 |
| Omega Force One | Johannes Bjerregaard | 1988 64'er/Markt & Technik | 25 |
| Predictable main | Johannes Bjerregaard | 1989 Bones/Maniacs of Noise | 4 |
| Ragtime Anno 87 | Johannes Bjerregaard | 1987 Johannes Bjerregaard | 3 |
| Roadblaster | Johannes Bjerregaard | 19?? Johannes Bjerregaard | 1 |
| Rockbuster | Johannes Bjerregaard | 1988 Danish Music Company | 17 |
| Scandalous | Johannes Bjerregaard | 1989 The Dominators | 19 |
| Shape | Johannes Bjerregaard | 1988 Upfront | 38 |
| Slimbo4 | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 11 |
| Some Soul | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 29 |
| Spacegame Music | Johannes Bjerregaard | 1987 The Main Force 2772 | 2 |
| Special Agent | Johannes Bjerregaard | 1987 Firebird | 27 |
| Spy vs Spy III | Johannes Bjerregaard | 1987 Johannes Bjerregaard | 23 |
| STII8 | Johannes Bjerregaard | 2014 Johannes Bjerregaard | 8 |
| Stormlord V2 | Johannes Bjerregaard | 1989 Maniacs of Noise | 2 |
| Test | Johannes Bjerregaard | 1989 Johannes Bjerregaard | 10 |
| Thunder Force | Johannes Bjerregaard | 1987 Rack-It | 8 |
| Tiny Symphony | Johannes Bjerregaard | 1988 Danish Music Company | 5 |
| Twilight Beyond | Johannes Bjerregaard | 1988 Danish Music Company | 4 |
| Wanna Get Sick | Johannes Bjerregaard | 1989 Upfront | 7 |
| Who Is Robb Vol 1 | Johannes Bjerregaard (The Jerk) | 198? The Jerk | 15 |
| Zoom | Johannes Bjerregaard | 1988 Discovery Software Int'l | 1 |

### Maniacs of Noise — Jeroen Tel  ·  `native`  ·  26 songs / 201 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Children Songs sub0 | Jeroen Tel | 1988 Maniacs of Noise | 11 |
| Cybernoid II sub0 | Jeroen Tel | 1988 Hewson | 13 |
| Cybernoid sub0 | Jeroen Tel | 1988 Hewson | 14 |
| Daring Dots sub0 | Jeroen Tel | 1988 Maniacs of Noise | 1 |
| G I Hero sub0 | Jeroen Tel | 1988 Maniacs of Noise | 13 |
| Gaplus preview sub0 | Jeroen Tel | 1988 Maniacs of Noise | 18 |
| Gaplus sub0 | Jeroen Tel | 1988 Mastertronic | 27 |
| Hawkeye Proto 1 sub0 | Jeroen Tel | 198? Maniacs of Noise | 4 |
| Hawkeye sub0 | Jeroen Tel | 1988 Thalamus | 7 |
| Hawkeye sub2 | Jeroen Tel | 1988 Thalamus | 2 |
| Hawkeye sub2 native |  |  | 1 |
| Hawkeye sub3 | Jeroen Tel | 1988 Thalamus | 1 |
| Hawkeye sub3 native |  |  | 1 |
| Ice Age sub0 | Jeroen Tel | 1988 Maniacs of Noise | 23 |
| Iets van JT sub0 | Jeroen Tel | 1988 Maniacs of Noise | 10 |
| M A C C sub0 | Jeroen Tel | 1988 Maniacs of Noise | 7 |
| Myth sub0 | Jeroen Tel | 1989 System 3 | 8 |
| Pal sine hoener tune 1 sub0 | Jeroen Tel | 2020 Offence | 3 |
| Sample sub0 | Jeroen Tel | 1988 Maniacs of Noise | 4 |
| Supremacy sub0 | Jeroen Tel | 1991 Virgin | 13 |
| Supremacy sub1 | Jeroen Tel | 1991 Virgin | 2 |
| Supremacy sub2 | Jeroen Tel | 1991 Virgin | 10 |
| Thats preview sub0 | Jeroen Tel | 1988 Maniacs of Noise | 1 |
| Tomcat sub0 | Jeroen Tel | 1989 Digital L&M/Players | 3 |
| Viool Tello sub0 | Jeroen Tel | 1988 Maniacs of Noise | 1 |
| Wizzy sub0 | Jeroen Tel | 1988 Maniacs of Noise | 3 |

### Rob Hubbard — Rob Hubbard  ·  `native`  ·  61 songs / 589 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| 5 Title Tunes song0 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| 5 Title Tunes song1 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| 5 Title Tunes song2 | Rob Hubbard | 1985 Rob Hubbard | 2 |
| 5 Title Tunes song3 | Rob Hubbard | 1985 Rob Hubbard | 2 |
| 5 Title Tunes song4 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Action Biker song0 | Rob Hubbard | 1985 Mastertronic | 1 |
| Action Biker song1 | Rob Hubbard | 1985 Mastertronic | 1 |
| Action Biker song2 | Rob Hubbard | 1985 Mastertronic | 1 |
| Auf Wiedersehen Monty song0 | Rob Hubbard & Ben Daglish | 1987 Gremlin Graphics | 43 |
| Chimera song0 | Rob Hubbard | 1985 Firebird | 12 |
| Chimera song1 | Rob Hubbard | 1985 Firebird | 1 |
| Commando song0 | Rob Hubbard | 1985 Elite | 4 |
| Commando song16 | Rob Hubbard | 1985 Elite | 4 |
| Commando song2 | Rob Hubbard | 1985 Elite | 1 |
| Confuzion song0 | Rob Hubbard | 1985 Incentive | 5 |
| Crazy Comets song0 | Rob Hubbard | 1985 Martech | 5 |
| Crazy Comets song1 | Rob Hubbard | 1985 Martech | 1 |
| Deep Strike song0 | Rob Hubbard | 1987 Durell | 25 |
| Delta song0 | Rob Hubbard | 1987 Thalamus | 221 |
| Delta song11 | Rob Hubbard | 1987 Thalamus | 3 |
| Delta song12 | Rob Hubbard | 1987 Thalamus | 3 |
| Geoff Capes Strongman Challenge song0 | Rob Hubbard | 1986 Martech | 1 |
| Geoff Capes Strongman Challenge song3 | Rob Hubbard | 1986 Martech | 1 |
| Geoff Capes Strongman Challenge song4 | Rob Hubbard | 1986 Martech | 1 |
| Geoff Capes Strongman Challenge song5 | Rob Hubbard | 1986 Martech | 1 |
| Gerry the Germ song0 | Rob Hubbard | 1986 Firebird | 2 |
| Gerry the Germ song1 | Rob Hubbard | 1986 Firebird | 1 |
| Gerry the Germ song4 | Rob Hubbard | 1986 Firebird | 1 |
| Gerry the Germ song6 | Rob Hubbard | 1986 Firebird | 1 |
| Gremlins song0 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Gremlins song1 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Gremlins song2 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Gremlins song3 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Gremlins song4 | Rob Hubbard | 1985 Rob Hubbard | 2 |
| Gremlins song5 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Gremlins song6 | Rob Hubbard | 1985 Rob Hubbard | 1 |
| Hunter Patrol song0 | Rob Hubbard | 1985 Mastertronic | 8 |
| Last V8 C128 version song0 | Rob Hubbard | 1985 MAD/Mastertronic | 2 |
| Last V8 C128 version song1 | Rob Hubbard | 1985 MAD/Mastertronic | 1 |
| Last V8 C128 version song2 | Rob Hubbard | 1985 MAD/Mastertronic | 1 |
| Last V8 song0 | Rob Hubbard | 1985 MAD/Mastertronic | 2 |
| Last V8 song1 | Rob Hubbard | 1985 MAD/Mastertronic | 1 |
| Last V8 song11 | Rob Hubbard | 1985 MAD/Mastertronic | 4 |
| Last V8 song2 | Rob Hubbard | 1985 MAD/Mastertronic | 1 |
| Lightforce song0 | Rob Hubbard | 1986 Faster Than Light (FTL) | 9 |
| Master of Magic song0 | Rob Hubbard | 1985 MAD/Mastertronic | 6 |
| Master of Magic song1 | Rob Hubbard | 1985 MAD/Mastertronic | 1 |
| Master of Magic song2 | Rob Hubbard | 1985 MAD/Mastertronic | 1 |
| Monty on the Run song0 | Rob Hubbard | 1985 Gremlin Graphics | 4 |
| Monty on the Run song1 | Rob Hubbard | 1985 Gremlin Graphics | 1 |
| Monty on the Run song2 | Rob Hubbard | 1985 Gremlin Graphics | 1 |
| Ninja song0 | Rob Hubbard | 1986 Entertainment USA | 21 |
| One Man and his Droid song0 | Rob Hubbard | 1985 Mastertronic | 11 |
| Saboteur II song0 | Rob Hubbard | 1987 Rob Hubbard | 86 |
| Sanxion song0 | Rob Hubbard | 1986 Thalamus | 31 |
| Shockway Rider song0 | Rob Hubbard | 1987 Faster Than Light (FTL) | 22 |
| Star Paws song0 | Rob Hubbard | 1987 Software Projects | 10 |
| Thing on a Spring song0 | Rob Hubbard | 1985 Gremlin Graphics | 4 |
| Zoids song0 | Rob Hubbard | 1986 Martech | 4 |
| Zoids song1 | Rob Hubbard | 1986 Martech | 1 |
| Zoids song2 | Rob Hubbard | 1986 Martech | 1 |

### Martin Galway — Martin Galway  ·  `native`  ·  40 songs / 40 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Arkanoid | Martin Galway | 1987 Imagine | 1 |
| Arkanoid alternative drums | Martin Galway | 1987 Imagine | 1 |
| Athena | Martin Galway | 1987 Imagine | 1 |
| Combat School | Martin Galway | 1987 Ocean | 1 |
| Comic Bakery | Martin Galway | 1986 Imagine | 1 |
| Commando High-Score | Martin Galway | 1986 Martin Galway | 1 |
| Daley Thompsons Decathlon loader | Martin Galway | 1984 Ocean | 1 |
| Game Over | Martin Galway | 1987 Imagine | 1 |
| Green Beret | Martin Galway | 1986 Imagine/Konami | 1 |
| Helikopter Jagd | Martin Galway | 1986 Ocean | 1 |
| Highlander | Martin Galway | 1986 Ocean | 1 |
| Hunchback II | Martin Galway | 1984 Ocean | 1 |
| Hyper Sports | Martin Galway | 1985 Imagine/Konami | 1 |
| Insects in Space | Martin Galway | 1989 Hewson | 1 |
| Kong Strikes Back | Martin Galway | 1984 Ocean | 1 |
| Match Day | Martin Galway | 1986 Ocean | 1 |
| Miami Vice | Martin Galway | 1986 Ocean | 1 |
| MicroProse Soccer indoor | Martin Galway | 1988 MicroProse | 1 |
| MicroProse Soccer intro | Martin Galway | 1988 MicroProse | 1 |
| MicroProse Soccer outdoor | Martin Galway | 1988 MicroProse | 1 |
| MicroProse Soccer V1 | Martin Galway | 1988 MicroProse | 1 |
| Mikie | Martin Galway | 1986 Imagine | 1 |
| Neverending Story | Martin Galway | 1985 Ocean | 1 |
| Ocean Loader 1 | Martin Galway | 1985 Ocean | 1 |
| Ocean Loader 2 | Martin Galway | 1985 Ocean | 1 |
| Parallax | Martin Galway | 1986 Ocean | 1 |
| Ping Pong | Martin Galway | 1986 Imagine | 1 |
| Rambo First Blood Part II | Martin Galway | 1985 Ocean | 1 |
| Rastan | Martin Galway | 1988 Imagine | 1 |
| Rolands Ratrace | Martin Galway | 1985 Ocean | 1 |
| Short Circuit | Martin Galway | 1986 Ocean | 1 |
| Slap Fight | Martin Galway | 1987 Imagine | 1 |
| Street Hawk | Martin Galway | 1986 Ocean | 1 |
| Street Hawk Prototype | Martin Galway | 1985 Ocean | 1 |
| Swag | Martin Galway | 1984 Micromania | 1 |
| Terra Cresta | Martin Galway | 1986 Imagine | 1 |
| Times of Lore | Martin Galway | 1988 Origin Systems | 1 |
| Wizball | Martin Galway | 1987 Ocean | 1 |
| Yie Ar Kung Fu | Martin Galway | 1985 Imagine | 1 |
| Yie Ar Kung Fu II | Martin Galway | 1986 Imagine | 1 |

### ROMUZAK V6.3 — Oliver Blasnik  ·  `native`  ·  4 songs / 4 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Delirious 9 tune 1 | Michael Troelsen (Fun Fun) | 1990 Genesis Project | 1 |
| Delirious 9 tune 1 native | Michael Troelsen (Fun Fun) | 1990 Genesis Project | 1 |
| Road of Excess end | Michael Troelsen (Fun Fun) | 1990 Triangle | 1 |
| Road of Excess end native | Michael Troelsen (Fun Fun) | 1990 Triangle | 1 |

### Sound Monitor (Musicmaster) — Fun Fun  ·  `native`  ·  11 songs / 27 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Dance at Night remix | Michael Troelsen (Coto) | 1987 Danish Cracking Crew | 8 |
| Dreamix | Michael Troelsen (Fun Fun) | 1987 Triangle | 5 |
| Dreamix Two | Michael Troelsen (Fun Fun) | 1987 Triangle | 2 |
| Final Luv | Michael Troelsen (Fun Fun) | 1987 Triangle | 1 |
| Fuck Off | Michael Troelsen (Fun Fun) | 1987 Triangle | 2 |
| Fun Mix | Michael Troelsen (Coto) | 1987 Danish Cracking Crew | 2 |
| Just Cant Get Enough | Michael Troelsen (Fun Fun) | 1988 Triangle | 1 |
| No Title | Michael Troelsen (Fun Fun) | 1987 Triangle | 1 |
| Poppy Road | Michael Troelsen (Fun Fun) | 1987 Triangle | 1 |
| Thats All | Michael Troelsen (Fun Fun) | 1987 Triangle | 3 |
| Times Up | Michael Troelsen (Fun Fun) | 1987 Triangle | 1 |

<!-- END GENERATED -->

---

*Generated 2026-07-09. Fidelity figures are the latest measured/documented values; native
builds live in `bin/` and are not yet registry-wired into the auto pipeline. For the method
behind the numbers see [`docs/players/PLAYBOOK.md`](players/PLAYBOOK.md).*
