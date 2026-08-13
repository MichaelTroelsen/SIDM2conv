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
| Future Composer | Michael Troelsen (Fun Fun) | **native** (Stage B, via a MoN shim) | `SID/Fun_Fun/` (20) | **14/15 corpus voices exactly 100.0%** audible pitch, full song length | `bin/` |
| Sound Monitor (Hülsbeck) | Michael Troelsen (Fun Fun) | **native** | `SID/Fun_Fun/` (20) | corpus strict sweep **99.25%** freq+wf over **27 of 27** parts | `bin/` |
| SID Duzz' It (SDI) | Glenn Rune Gallefoss / Tjelta | Driver 11 (Stage A) + **native** (Stage B) | `SID/Gallefoss_Glenn/` (441) | Stage A strict onset+pitch medians A 98.3 · D 100 · C 86.0 · B 74.8 · E 50.8 · V 21.8 — **only A+D are unfitted**. Stage B covers **all six variants**, most E/DELTA/C/V voices **98-100%**; residual is a fast per-frame arp class (Bahbar v1/v2 ~92.7/90.4, Filthy_Hit v0 76). Stage B is **standalone, one file at a time** — not wired into a shipping path | `bin/` |
| Blackbird / lft | Linus Åkesson (lft) | **native** | `SID/LFT/` (61) | 16-file v1.2-exact corpus mean **99.96**; **11 of 16 exactly 100.0**, none below 99.8 | `bin/` |
| Jeroen Kimmel (Hubbard-derived) | Jeroen Kimmel | Driver 11 (Stage A) | `SID/Red_kommel_jeroen/` (4) | **11/12 voice-medians exact 100%** (frame-pitch) | `bin/` |
| Maniacs of Noise / Deenen | Charles Deenen | Driver 11 (Stage A) | `SID/deenen/` (40) | 7 clean wins (5 at exactly 100/100); 10/19 located | `bin/` |
| HardTrack Composer | Wojciech Radziejewski (Shogoon) | Driver 11 (Stage A) + **native** (Stage B) | `SID/Shogoon/` (150, mixed-player) | register model **100.00%** freq/wf/pulse on the 18 layout-seeded files; Stage B builds 33/33 | `bin/` |
| Matt Gray | Matt Gray | Driver 11 (Stage A) + **native** (Stage B) | `SID/Gray_Matt/` (55) | wf/AD/SR/filter/`$D418` **100.00%**, freq **92.7/92.9/100.0** (Last Ninja 2 sub 0, all frames) | `bin/` |
| NewPlayer 20.G4 | various | NP20 | `SID/` (NP20 variants) | 70–90% | ✅ auto (registry) |

⚠️ Every figure here is a **verdict with conditions attached** — the match window,
which files were included, and which registers were actually exercised all change
what it means. Read the player's own doc in [`docs/players/`](players/) before
quoting any of them; several have been retracted and re-measured.

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

**949 songs built** across 15 native players (each song may span several SF2 parts).

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

### Maniacs of Noise — Jeroen Tel  ·  `native`  ·  27 songs / 206 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Children Songs sub0 | Jeroen Tel | 1988 Maniacs of Noise | 11 |
| Cybernoid II sub0 | Jeroen Tel | 1988 Hewson | 18 |
| Cybernoid II sub0 native |  |  | 1 |
| Cybernoid sub0 | Jeroen Tel | 1988 Hewson | 13 |
| Daring Dots sub0 | Jeroen Tel | 1988 Maniacs of Noise | 1 |
| G I Hero sub0 | Jeroen Tel | 1988 Maniacs of Noise | 13 |
| Gaplus preview sub0 | Jeroen Tel | 1988 Maniacs of Noise | 18 |
| Gaplus sub0 | Jeroen Tel | 1988 Mastertronic | 27 |
| Hawkeye Proto 1 sub0 | Jeroen Tel | 198? Maniacs of Noise | 4 |
| Hawkeye sub0 | Jeroen Tel | 1988 Thalamus | 8 |
| Hawkeye sub2 | Jeroen Tel | 1988 Thalamus | 1 |
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

### Rob Hubbard — Rob Hubbard  ·  `native`  ·  61 songs / 634 SF2 files

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
| Commando song0 | Rob Hubbard | 1985 Elite | 45 |
| Commando song16 | Rob Hubbard | 1985 Elite | 4 |
| Commando song2 | Rob Hubbard | 1985 Elite | 1 |
| Confuzion song0 | Rob Hubbard | 1985 Incentive | 5 |
| Crazy Comets song0 | Rob Hubbard | 1985 Martech | 5 |
| Crazy Comets song1 | Rob Hubbard | 1985 Martech | 1 |
| Deep Strike song0 | Rob Hubbard | 1987 Durell | 28 |
| Delta song0 | Rob Hubbard | 1987 Thalamus | 222 |
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

### SID Duzz' It (SDI) — Gallefoss/Tjelta  ·  `Driver 11 (Stage A)`  ·  348 songs / 363 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| 2 Young 2 Die | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| 30seconds | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| 64 Antheme | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Ablegoeyer | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Abrakadabra preview | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Acid Jazz | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Aerodynamic | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Afterburner | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Agrajag | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Airwalk | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Airwalk 98 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Airwalk II | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Aldebaran | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Aldebaran sub1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Aldebaran sub2 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Aldebaran sub3 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Alf Theme | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Alone in Space | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Ambient | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Another Beginning | Glenn Rune Gallefoss | 1998 SHAPE | 1 |
| Another Day in Paradize | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 2 |
| Arabia | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Arcane | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Arnhild | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Ayla Partyshaker | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Babar | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Bahbar | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Banana | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk | 1 |
| Banana Man | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Barbers Adagio 64 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Basselusk | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Batman in Jp | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Beginning | Glenn Rune Gallefoss | 1999 SHAPE | 1 |
| Beverly Kraven | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Black Hole Sun Digi | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Blowfish | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Blue | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Boiled Beans | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' | 1 |
| Bossa Butt | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Bouncing | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Braveheart | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Burpmania | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' | 1 |
| Buttlern | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Calmdown II another one | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Calmdown Whats this | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' | 1 |
| Careless Whisper | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 1 |
| Cheese Pop | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Close preview | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Club 69 | Glenn Rune Gallefoss | 2004 SHAPE/Blues Muz' | 1 |
| Coming Soon | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Commando | Glenn Rune Gallefoss | 1999 Nostalgia | 1 |
| Commercial Countdown | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Commies | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Computare Maximus Dominanus | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Countdown to NIL | Glenn Rune Gallefoss | 2000 SHAPE | 1 |
| Country-Dip | Glenn Rune Gallefoss (Shark) | 1995 Plush | 1 |
| Crizz Crozz | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Culture Mix 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision | 1 |
| Culture Mix 2 | Glenn Rune Gallefoss (Shark) | 1990 Collision | 2 |
| Curse | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Dancing in the Moonlight | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Danske-baaten | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Darkmoon | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Das Boot | Glenn Rune Gallefoss (Shark) | 1993 Regina | 1 |
| Day of the Tentacle DOTT | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Death of the Pulse v1 0 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Deelight | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Delphines | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Delta | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Delta Slow | Glenn Rune Gallefoss | 2001 Nostalgia | 1 |
| Denver | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Derilicts | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Destruction | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Devotion | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Dialects | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Different Reality VE-4x | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 1 |
| Digital Designs Intro 2 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| DMC Demo remake | Glenn Rune Gallefoss | 2004 SHAPE/Blues Muz' | 1 |
| Domino Dancing | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Dorull | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Dreadful | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Dream | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 1 |
| Dreamland | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Eastbottom | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Effect Freak | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Electronic Transfer | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| End | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| End 94 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| End Music | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Enigma Elg moose | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Eurovision | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Everytime | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Evil Within | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Evil Within sub1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Extreme | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Fading Away | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Faeries | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Fast Pussy | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Filthy Hit VE-4x | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Fin Sang | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Finish Line | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Fjellgeit ode to Fearlight | Glenn Rune Gallefoss | 1994 Blues Muz' | 1 |
| Flames | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Flavour | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Flimbos | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| Flunk | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Forbannet | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Funhouse | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Funk Facet | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Funkman | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Funkriff | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Funkriff v2 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Fusion | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Galvanized | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Genesis P | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Get hyped | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Got Da Bluez | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Gracious | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Granturismo | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Graut | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| GRG in Cyberspace | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| GT Groove | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Guaranteed | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Happy Birthday Tg-Acme | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 3 |
| Hardcore | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Hava Nagila | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Heartbeat | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Heartbit | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Hickup | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| High Pressure | Glenn Rune Gallefoss (Shark) | 1993 Regina | 1 |
| Hithouse | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Holy Daze | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Holy Josh | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 2 |
| Homebrew | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| House Fantasy | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Hyperfool | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| I Aint Mad | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Imperial March | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Implocation VE-4x | Glenn Rune Gallefoss | 1993 SHAPE/Blues Muz' | 1 |
| Impossible Mission Theme | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Infra Red | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Interlude | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Intro | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Intro Aktig | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Intro Lime | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Intro Zax | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Intro Zax II | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Invention 1 | Glenn Rune Gallefoss | 1999 SHAPE | 1 |
| Iridion | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Jazz My Azz | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Jazzmjux | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Jazzstones | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Jazzy-d | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| JB Groove I | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| JB Groove II | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Jessie Jazz | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 2 |
| Joikaboller | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| JS Beta Song | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| JS Fanfare | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Juba-Jazz | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Jule Fun | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| Kald Kaffe | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Kalkun Yak | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Karamell | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Kirby | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Kleptoekko | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Koke Stek | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Kururin | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| L-Forza long edit | Glenn Rune Gallefoss | 2010 Recollection | 2 |
| L-Forza Remix | Glenn Rune Gallefoss | 2009 Byterapers | 1 |
| Lame | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk | 2 |
| Lederhosen | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Leon Latex | Glenn Rune Gallefoss | 2007 SHAPE | 1 |
| Lesbians | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Lethal Weapon | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Lightforce | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Little Bee | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Long Ting | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Looping | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Magic Moment | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Max Mix 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 1 |
| Mekkasang | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Menthol | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Micro Mix | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Microwave | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Milkshake | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Mini Poelse | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk | 2 |
| Moi Funk | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Moonraker | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Morphosis | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Mozell | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Mummy | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 1 |
| Napalm | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Nasty Hombre | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Nephritis | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Neurotica | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Neurotica short | Glenn Rune Gallefoss | 1999 Onslaught | 1 |
| Neverending Story | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Nightjazz | Glenn Rune Gallefoss | 1992 Blues Muz' | 1 |
| NineOneOne | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Ninja IV | Glenn Rune Gallefoss | 1991 Digital Designs | 1 |
| Nitro Dot | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Noice | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Norvegia thats a cheese | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Norway rulls | Glenn Rune Gallefoss & Bjarte V | 1993 Digital Designs | 1 |
| Ode to Bugg | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 1 |
| Oh Boy VE-2x | Glenn Rune Gallefoss | 1993 SHAPE/Blues Muz' | 1 |
| Ohne Titel | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 1 |
| Oldie | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Onkie Donkie | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 2 |
| Opening | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Orbital | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Organ Blues | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Oswaldo | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Other Day | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Outrun | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Overlord | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Painful | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Paranoid | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Pervers | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Phneumatic | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Phneumatic sub1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Pilz | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Ping Reply from Outter Space | Glenn Rune Gallefoss | 1998 SHAPE | 1 |
| Pjatt | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Pling Plong | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Polkapop | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Pop | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Potatoes | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Praiser | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Prelude | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Premature | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Preview Zax | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Product | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Promises | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Psychic | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Psycho | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 3 |
| Psycho II | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 2 |
| Psycho IV | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Pulstro | Glenn Rune Gallefoss (Shark) | 1993 Regina | 1 |
| Pultost VE-4x | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Punkfunk | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Pust | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Quaternion | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Quest | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Radbrekk I | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Rapture | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Rar Takt | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Raw and Mean | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Reaxion extended | Glenn Rune Gallefoss | 2001 Commodore Zone | 1 |
| Reaxion Extended Remix | Glenn Rune Gallefoss | 2001 Commodore Zone | 1 |
| Rectum | Glenn Rune Gallefoss (Shark) | 1993 Regina/Blues Muz' | 1 |
| Reggie | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Remote | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 1 |
| Reyn Only | Glenn Rune Gallefoss (Shark) | 1993 Regina/Blues Muz' | 1 |
| Rhyme | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Rintintin | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| RNA Reset Now Asshole | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Rocker | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Rough Boy | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Rumbah | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Sacrebleu | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Sad Song | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Sad Toob | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Scene plus III | Glenn Rune Gallefoss | 1998 FairLight | 1 |
| Scimitars | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Screaming | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| SCS TRC Intro Music | Glenn Rune Gallefoss (Shark) | 1994 Regina/Blues Muz' | 1 |
| ShapeDigi | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Sharkie | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Shocking | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Short Deel | Glenn Rune Gallefoss | 2000 Nostalgia | 1 |
| Short One | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Short Zax | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Sidastic | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Slamtime | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Slapfart | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Slowjazz | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Slowmotion | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Smiley | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Snip Snap | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Snufs | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Solar Plexus | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Sorrows | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Sound Test | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| Space Suit | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk | 1 |
| Spellbound | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Stairway 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Stairway 2 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Stort Plaster | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz'/HVSC | 1 |
| Strangers | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Strangle | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz'/Onslaught | 1 |
| Suburbia | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Sugarhill | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Super Galaxy preview | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Survival | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Sveitser Ost | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 2 |
| Sweeper | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Sweet JB | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Syk Sang | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Synchro | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Syncomatic | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Synthfunk | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| T-Shirt | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Tango | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Tanks 3000 | Glenn R. Gallefoss & R. Bayliss | 2006 Protovision | 2 |
| Tarmslyng | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Techno | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Techno-Kaare | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Techno Chaos | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Techno Rave | Glenn Rune Gallefoss & Mitch | 1994 SHAPE/Crest | 1 |
| Teddy Bear | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Tekkno Tuna Sandwich | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Ten Seconds | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Terpentin | Glenn Rune Gallefoss | 1993 Digital Designs | 1 |
| Test-trip | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Tight Jeans | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Timbuktu | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Tissemann | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Toto | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Trakten | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Tranedans | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Trapped | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| Trist | Glenn Gallefoss & D. Bakewell | 1999 Blues Muz' | 1 |
| Trooper | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Tunfiskpizza | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Twin Peaks | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 1 |
| Tycoon | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Tycoon 2 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| U May C | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Underwear VE-4x | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Velomatrix | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Vicious Circles | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Vikings | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Virtual | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Vozza Jazz | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Warbeat | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Wash and Go | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Wavetrip | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| Weirdo | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 1 |
| What Is Love | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Xard | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Yeah | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 1 |
| Yesterday | G. R. Gallefoss & B. Vosseteig | 1994 SHAPE/Blues Muz' | 1 |
| Zakazazam | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 1 |
| Zap | Glenn Rune Gallefoss | 2007 SHAPE/Blues Muz' | 1 |
| Zexest | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Zoophyte | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |

### SID Duzz' It (SDI) — Gallefoss/Tjelta  ·  `native (Stage B)`  ·  281 songs / 5227 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| 2 Young 2 Die native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| 30seconds native | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| 64 Antheme native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 37 |
| Ablegoeyer native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Abrakadabra preview native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 4 |
| Acid Jazz native | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 73 |
| Aerodynamic native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Afterburner native | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 7 |
| Agrajag native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Airwalk 98 native | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 23 |
| Airwalk II native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 4 |
| Aldebaran native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Alf Theme native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 8 |
| Alone in Space native | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 24 |
| Ambient native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 3 |
| Another Beginning native | Glenn Rune Gallefoss | 1998 SHAPE | 13 |
| Arabia native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 8 |
| Arcane native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 7 |
| Arnhild native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 22 |
| Bahbar native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 30 |
| Bahbar v native |  |  | 11 |
| Banana Man native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 5 |
| Basselusk native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 4 |
| Batman in Jp native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 7 |
| Beginning native | Glenn Rune Gallefoss | 1999 SHAPE | 20 |
| Beverly Kraven native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 2 |
| Blowfish native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 7 |
| Boiled Beans native | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' | 13 |
| Bossa Butt native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Bouncing native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 6 |
| Buttlern native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 5 |
| Calmdown II another one native | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 20 |
| Calmdown Whats this native | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' | 1 |
| Careless Whisper native | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 38 |
| Close preview native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 6 |
| Club 69 native | Glenn Rune Gallefoss | 2004 SHAPE/Blues Muz' | 90 |
| Coming Soon native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Commando native | Glenn Rune Gallefoss | 1999 Nostalgia | 38 |
| Commies native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 4 |
| Computare Maximus Dominanus native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 3 |
| Countdown to NIL native | Glenn Rune Gallefoss | 2000 SHAPE | 15 |
| Country-Dip native | Glenn Rune Gallefoss (Shark) | 1995 Plush | 1 |
| Crizz Crozz native | Glenn Rune Gallefoss | 1993 Digital Designs | 9 |
| Culture Mix 1 native | Glenn Rune Gallefoss (Shark) | 1990 Collision | 4 |
| Culture Mix 2 native | Glenn Rune Gallefoss (Shark) | 1990 Collision | 129 |
| Curse native | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 25 |
| Dancing in the Moonlight native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 6 |
| Danske-baaten native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Darkmoon native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 31 |
| Das Boot native | Glenn Rune Gallefoss (Shark) | 1993 Regina | 7 |
| Day of the Tentacle DOTT native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 29 |
| Death of the Pulse v1 0 native | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 1 |
| Deelight native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 14 |
| Delphines native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 8 |
| Delta native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 5 |
| Delta Slow native | Glenn Rune Gallefoss | 2001 Nostalgia | 12 |
| Denver native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 2 |
| Derilicts native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 14 |
| Destruction native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 6 |
| Devotion native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 3 |
| Dialects native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 9 |
| Different Reality VE-4x native | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 1 |
| Digital Designs Intro 2 native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 4 |
| DMC Demo remake native | Glenn Rune Gallefoss | 2004 SHAPE/Blues Muz' | 21 |
| Domino Dancing native | Glenn Rune Gallefoss | 1993 Digital Designs | 10 |
| Dorull native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Dreadful native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 15 |
| Dream native | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 4 |
| Dreamland native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 12 |
| Eastbottom native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 4 |
| Effect Freak native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| End 94 native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1190 |
| End Music native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 9 |
| End native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 11 |
| Enigma Elg moose native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 3 |
| Eurovision native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Everytime native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 7 |
| Evil Within native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 13 |
| Extreme native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 4 |
| Faeries native | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 28 |
| Filthy Hit VE-4x native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 2 |
| Fin Sang native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Finish Line native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 2 |
| Fjellgeit ode to Fearlight native | Glenn Rune Gallefoss | 1994 Blues Muz' | 1 |
| Flames native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 47 |
| Flimbos native | Glenn Rune Gallefoss | 1992 Digital Designs | 8 |
| Flunk native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 8 |
| Forbannet native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Funhouse native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 3 |
| Funk Facet native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 2 |
| Funkman native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Funkriff native | Glenn Rune Gallefoss | 1993 Digital Designs | 5 |
| Funkriff v2 native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 4 |
| Fusion native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 17 |
| Galvanized native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 6 |
| Get hyped native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 9 |
| Got Da Bluez native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 4 |
| Gracious native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 8 |
| Granturismo native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Graut native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 5 |
| GT Groove native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 402 |
| Guaranteed native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 6 |
| Hardcore native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 6 |
| Heartbeat native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 9 |
| Heartbit native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 6 |
| Hickup native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 54 |
| High Pressure native | Glenn Rune Gallefoss (Shark) | 1993 Regina | 53 |
| Hithouse native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Holy Daze native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 14 |
| Homebrew native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 9 |
| House Fantasy native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 10 |
| Hyperfool native | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 9 |
| Imperial March native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 3 |
| Implocation VE-4x native | Glenn Rune Gallefoss | 1993 SHAPE/Blues Muz' | 2 |
| Infra Red native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 9 |
| Interlude native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 5 |
| Intro Aktig native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Intro Lime native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 1 |
| Intro native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 3 |
| Intro Zax II native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 1 |
| Intro Zax native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Invention 1 native | Glenn Rune Gallefoss | 1999 SHAPE | 10 |
| Iridion native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Jazzmjux native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 7 |
| Jazzstones native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 11 |
| Jazzy-d native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 16 |
| JB Groove II native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 5 |
| Joikaboller native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 24 |
| JS Beta Song native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| JS Fanfare native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 11 |
| Juba-Jazz native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 4 |
| Jule Fun native | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| Kalkun Yak native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Karamell native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 4 |
| Kirby native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 5 |
| Kleptoekko native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Koke Stek native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 6 |
| Kururin native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 4 |
| L-Forza long edit native | Glenn Rune Gallefoss | 2010 Recollection | 174 |
| L-Forza Remix native | Glenn Rune Gallefoss | 2009 Byterapers | 126 |
| Lame native | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk | 31 |
| Lederhosen native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Leon Latex native | Glenn Rune Gallefoss | 2007 SHAPE | 35 |
| Lethal Weapon native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 24 |
| Lightforce native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 21 |
| Little Bee native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 4 |
| Long Ting native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 28 |
| Looping native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Magic Moment native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 7 |
| Menthol native | Glenn Rune Gallefoss | 1993 Digital Designs | 8 |
| Micro Mix native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 6 |
| Microwave native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 7 |
| Milkshake native | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' | 41 |
| Moi Funk native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 22 |
| Mozell native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 7 |
| Nasty Hombre native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 3 |
| Nephritis native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 22 |
| Neurotica short native | Glenn Rune Gallefoss | 1999 Onslaught | 7 |
| Neverending Story native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 13 |
| Nightjazz native | Glenn Rune Gallefoss | 1992 Blues Muz' | 1 |
| NineOneOne native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 101 |
| Nitro Dot native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 4 |
| Noice native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 22 |
| Norvegia thats a cheese native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 13 |
| Ode to Bugg native | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' | 21 |
| Oh Boy VE-2x native | Glenn Rune Gallefoss | 1993 SHAPE/Blues Muz' | 1 |
| Ohne Titel native | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' | 5 |
| Oldie native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Onkie Donkie native | Glenn Rune Gallefoss (Shark) | 1991 The Freaks | 19 |
| Opening native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 2 |
| Orbital native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 4 |
| Organ Blues native | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 15 |
| Other Day native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 32 |
| Outrun native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 5 |
| Overlord native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 13 |
| Painful native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 4 |
| Paranoid native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Pervers native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 5 |
| Phneumatic native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 5 |
| Pjatt native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 5 |
| Pling Plong native | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 20 |
| Pop native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 21 |
| Potatoes native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 7 |
| Praiser native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 7 |
| Prelude native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 11 |
| Premature native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 36 |
| Preview Zax native | Glenn Rune Gallefoss | 1993 Digital Designs | 2 |
| Product native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 22 |
| Promises native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Psycho IV native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Pulstro native | Glenn Rune Gallefoss (Shark) | 1993 Regina | 1 |
| Pultost VE-4x native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 4 |
| Punkfunk native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 2 |
| Pust native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 9 |
| Quaternion native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 14 |
| Quest native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 33 |
| Rapture native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 2 |
| Rar Takt native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 7 |
| Raw and Mean native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 10 |
| Reaxion extended native | Glenn Rune Gallefoss | 2001 Commodore Zone | 24 |
| Reaxion Extended Remix native | Glenn Rune Gallefoss | 2001 Commodore Zone | 11 |
| Reyn Only native | Glenn Rune Gallefoss (Shark) | 1993 Regina/Blues Muz' | 12 |
| Rhyme native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 6 |
| RNA Reset Now Asshole native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 3 |
| Rocker native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 10 |
| Rough Boy native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 2 |
| Sad Song native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 8 |
| Sad Toob native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 4 |
| Scene plus III native | Glenn Rune Gallefoss | 1998 FairLight | 54 |
| Scimitars native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 31 |
| Screaming native | Glenn Rune Gallefoss | 1993 Digital Designs | 14 |
| Sharkie native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 4 |
| Short Deel native | Glenn Rune Gallefoss | 2000 Nostalgia | 6 |
| Short One native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 2 |
| Short Zax native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 1 |
| Slamtime native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 12 |
| Slapfart native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 3 |
| Slowjazz native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Slowmotion native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 3 |
| Smiley native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 56 |
| Snip Snap native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 9 |
| Snufs native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 10 |
| Solar Plexus native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 6 |
| Sorrows native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 6 |
| Sound Test native | Glenn Rune Gallefoss | 1992 Digital Designs | 1 |
| Spellbound native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 9 |
| Stairway 1 native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Stairway 2 native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Stort Plaster native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz'/HVSC | 137 |
| Strangers native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 6 |
| Strangle native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz'/Onslaught | 6 |
| Suburbia native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 2 |
| Sugarhill native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Super Galaxy preview native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 1 |
| Survival native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 23 |
| Sweeper native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Sweet JB native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 12 |
| Syk Sang native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 3 |
| Synchro native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 5 |
| Syncomatic native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 57 |
| Synthfunk native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 28 |
| T-Shirt native | Glenn Rune Gallefoss | 1993 Digital Designs | 4 |
| Tango native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 2 |
| Tanks 3000 native | Glenn R. Gallefoss & R. Bayliss | 2006 Protovision | 69 |
| Tarmslyng native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 17 |
| Techno-Kaare native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 3 |
| Techno Chaos native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 8 |
| Techno native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 3 |
| Techno Rave native | Glenn Rune Gallefoss & Mitch | 1994 SHAPE/Crest | 2 |
| Tekkno Tuna Sandwich native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 1 |
| Ten Seconds native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 2 |
| Terpentin native | Glenn Rune Gallefoss | 1993 Digital Designs | 10 |
| Test-trip native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 7 |
| Tight Jeans native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 6 |
| Timbuktu native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 15 |
| Tissemann native | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs | 1 |
| Toto native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 10 |
| Trakten native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 2 |
| Tranedans native | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' | 30 |
| Trapped native | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' | 7 |
| Trist native | Glenn Gallefoss & D. Bakewell | 1999 Blues Muz' | 13 |
| Trooper native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 8 |
| Tunfiskpizza native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 6 |
| Tycoon 2 native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 21 |
| Tycoon native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 8 |
| U May C native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 1 |
| Underwear VE-4x native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 1 |
| Velomatrix native | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' | 7 |
| Vicious Circles native | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' | 46 |
| Vikings native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 8 |
| Virtual native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 5 |
| Vozza Jazz native | Glenn Rune Gallefoss | 1994 The Radbrekkjers | 5 |
| Warbeat native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 5 |
| Wash and Go native | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs | 7 |
| Wavetrip native | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' | 1 |
| What Is Love native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 79 |
| Xard native | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' | 2 |
| Yeah native | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' | 21 |
| Zap native | Glenn Rune Gallefoss | 2007 SHAPE/Blues Muz' | 1 |
| Zexest native | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs | 3 |
| Zoophyte native | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' | 8 |

### Jeroen Kimmel (Hubbard-derived) — Jeroen Kimmel  ·  `Driver 11 (Stage A)`  ·  9 songs / 9 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Radax | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag | 1 |
| Radax sub1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag | 1 |
| Radax sub2 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag | 1 |
| Radax sub3 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag | 1 |
| Radax sub4 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag | 1 |
| Radax sub5 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag | 1 |
| Rhaa Lovely II tune 2 | Jeroen Kimmel (Red) | 1987 The Judges | 1 |
| Think Twice III | Jeroen Kimmel (Red) | 1987 The Judges | 1 |
| Think Twice V | Jeroen Kimmel (Red) | 1987 The Judges | 1 |

### Maniacs of Noise / Deenen — Charles Deenen  ·  `Driver 11 (Stage A)`  ·  15 songs / 15 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| After the War | Charles Deenen | 1989 Dinamic | 1 |
| Aids See Ass | Charles Deenen (TSS) | 198? HC-Ass 5005 | 1 |
| Astro Marine Corps | Charles Deenen | 1989 Dinamic | 1 |
| B A T | Charles Deenen | 1990 Ubisoft | 1 |
| Constant Runner | Charles Deenen | 1989 Masters' Design Group | 1 |
| Crazy Music | Charles Deenen (TMC) | 1987 Hotline | 1 |
| Ding van Charles | Charles Deenen | 19?? Maniacs of Noise | 1 |
| Give It a Try | Charles Deenen (TMC) | 1987 Scoop Designs | 1 |
| I Saw 2 HC-Ass 5005s Fucking | Charles Deenen (TMC) | 1987 HC-Ass 5005 | 1 |
| Lord of the Rings | Charles Deenen | 1990 Interplay | 1 |
| Melig | Charles Deenen | 1989 Maniacs of Noise | 1 |
| Say Hello to the Boring Times | Charles Deenen | 1988 Maniacs of Noise | 1 |
| Soldier of Light | Charles Deenen & Jeroen Tel | 1988 Reptilia Design/Softek Int | 1 |
| Super Heavy | Charles Deenen (TSS) | 198? HC-Ass 5005 | 1 |
| Zamzara | Charles Deenen | 1989 Rack-It | 1 |

### Blackbird / lft — lft  ·  `native`  ·  16 songs / 20 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Crank Crank Airwolf native | Linus Åkesson (lft) | 2018 lft | 1 |
| Dishwasher Groove native | Linus Åkesson (lft) | 2017 lft | 1 |
| Dithered Island native | Linus Åkesson (lft) | 2018 lft | 2 |
| Elvendance native | Linus Åkesson (lft) | 2018 lft | 1 |
| Euclid Was Here native | Linus Åkesson (lft) | 2018 lft | 1 |
| Fargo native | Linus Åkesson (lft) | 2020 lft | 2 |
| Fugue on a Theme by D M Hanlon native | Linus Åkesson (lft) | 2017 lft | 1 |
| Glyptodont native | Linus Åkesson (lft) | 2017 lft | 1 |
| Into the Unknown native | Linus Åkesson (lft) | 2020 lft | 3 |
| Maple Leaf Rag native | Linus Åkesson (lft) | 2018 lft | 1 |
| Quintessence native | Linus Akesson (lft) | 2017 lft | 1 |
| Revolutions Delivered native | Linus Åkesson (lft) | 2021 lft | 1 |
| Thus Spoke the PC Speaker native | Linus Åkesson (lft) | 2019 lft | 1 |
| To Die For II native | Linus Åkesson (lft) | 2017 Genesis Project | 1 |
| Toy Rocket native | Linus Åkesson (lft) | 2017 lft | 1 |
| Trinket native | Linus Åkesson (lft) | 2017 lft | 1 |

### HardTrack Composer — Longhair/Brush  ·  `Driver 11 (Stage A)`  ·  5 songs / 5 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Hopscotch | Wojciech Radziejewski (Shogoon) | 1996 Agony/Taboo | 1 |
| Love tune 2 | Wojciech Radziejewski (Shogoon) | 1995 Agony | 1 |
| Love tune 3 | Wojciech Radziejewski (Shogoon) | 1995 Agony | 1 |
| Muminki Rooooolz | Wojciech Radziejewski (Shogoon) | 1995 Agony | 1 |
| Zakplus | Wojciech Radziejewski (Shogoon) | 1999 Taboo | 1 |

### HardTrack Composer — Longhair/Brush  ·  `native (Stage B)`  ·  33 songs / 313 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Altered States Tune 1 | Wojciech Radziejewski (Shogoon) | 1994 Taboo | 9 |
| Altered States Tune 2 | Wojciech Radziejewski (Shogoon) | 1994 Taboo | 17 |
| Arizona Dream | Wojciech Radziejewski (Shogoon) | 1995 Taboo | 7 |
| Astoria 7 tune 2 | Wojciech Radziejewski (Shogoon) | 1996 Agony | 9 |
| Domagareflexow | Wojciech Radziejewski (Shogoon) | 1995 Samar Productions | 11 |
| For Astoria 6 | Wojciech Radziejewski (Shogoon) | 1995 Agony | 9 |
| Fun Factory | Wojciech Radziejewski (Shogoon) | 1994 Taboo | 22 |
| Griffin Score | Wojciech Radziejewski (Shogoon) | 1993 Elysium | 21 |
| Hopscotch | Wojciech Radziejewski (Shogoon) | 1996 Agony/Taboo | 9 |
| If I Was a Rich Man | Shogoon & Longhair | 199? Elysium | 1 |
| Illmatic end | Wojciech Radziejewski (Shogoon) | 1999 Elysium | 9 |
| Intrigue | Wojciech Radziejewski (Shogoon) | 1994 Taboo | 5 |
| Jazz and Weird Tekno | Wojciech Radziejewski (Shogoon) | 1994 Taboo | 18 |
| Jazzloor | Shogoon & Longhair | 1994 Elysium | 4 |
| Love tune 2 | Wojciech Radziejewski (Shogoon) | 1995 Agony | 6 |
| Love tune 3 | Wojciech Radziejewski (Shogoon) | 1995 Agony | 11 |
| Love tune 5 | Wojciech Radziejewski (Shogoon) | 1995 Agony | 4 |
| Muminki Rooooolz | Wojciech Radziejewski (Shogoon) | 1995 Agony | 8 |
| Muza Do Dema | Wojciech Radziejewski (Shogoon) | 1999 Elysium | 8 |
| Ritual II tune 1 | Wojciech Radziejewski (Shogoon) | 1995 Taboo | 9 |
| Ritual II tune 2 | Wojciech Radziejewski (Shogoon) | 1995 Taboo | 14 |
| Rune-T Noter | Wojciech Radziejewski (Shogoon) | 1995 Taboo | 8 |
| Shogoon-Rave | Wojciech Radziejewski (Shogoon) | 1994 Agony/Taboo | 2 |
| Sling | Wojciech Radziejewski (Shogoon) | 2002 Elysium | 5 |
| Something to Eat | Wojciech Radziejewski (Shogoon) | 1999 Elysium | 16 |
| Takisobie | Wojciech Radziejewski (Shogoon) | 1996 Taboo/Agony | 6 |
| Teekkno | Wojciech Radziejewski (Shogoon) | 1995 Agony | 4 |
| Timsoft Intro | Wojciech Radziejewski (Shogoon) | 1994 Timsoft | 13 |
| Trance | Wojciech Radziejewski (Shogoon) | 1994 Agony | 10 |
| Tribute to Laxity | Wojciech Radziejewski (Shogoon) | 2007 Shogoon | 10 |
| Walk to Soul | Wojciech Radziejewski (Shogoon) | 1996 Taboo | 10 |
| What Can I Say Crap | Wojciech Radziejewski (Shogoon) | 1993 Elysium | 12 |
| Zakplus | Wojciech Radziejewski (Shogoon) | 1999 Taboo | 6 |

### Matt Gray — Matt Gray  ·  `native (Stage B)`  ·  37 songs / 78 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Driller sub01 | Matt Gray | 1987 Incentive | 1 |
| Hunters Moon Remastered sub01 | Matt Gray | 2018 Thalamus Digital Publ. | 1 |
| Hunters Moon Remastered sub02 | Matt Gray | 2018 Thalamus Digital Publ. | 1 |
| Hunters Moon Remastered sub03 | Matt Gray | 2018 Thalamus Digital Publ. | 1 |
| Hunters Moon Remastered sub04 | Matt Gray | 2018 Thalamus Digital Publ. | 6 |
| Hyperion 2 sub01 | Matt Gray | 1988 Matt Gray | 5 |
| Hyperion 2 sub02 | Matt Gray | 1988 Matt Gray | 3 |
| Hyperion 2 sub03 | Matt Gray | 1988 Matt Gray | 3 |
| KGB Superspy sub01 | Matt Gray | 1990 Codemasters | 2 |
| KGB Superspy sub02 | Matt Gray | 1990 Codemasters | 1 |
| KGB Superspy sub03 | Matt Gray | 1990 Codemasters | 1 |
| KGB Superspy sub04 | Matt Gray | 1990 Codemasters | 1 |
| Last Ninja 2 sub00 | Matt Gray | 1988 System 3 | 2 |
| Last Ninja 2 sub01 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub02 | Matt Gray | 1988 System 3 | 2 |
| Last Ninja 2 sub03 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub04 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub05 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub06 | Matt Gray | 1988 System 3 | 4 |
| Last Ninja 2 sub08 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub09 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub10 | Matt Gray | 1988 System 3 | 2 |
| Last Ninja 2 sub11 | Matt Gray | 1988 System 3 | 1 |
| Last Ninja 2 sub12 | Matt Gray | 1988 System 3 | 2 |
| Maze Mania sub01 | Matt Gray | 1989 Hewson | 2 |
| Maze Mania sub02 | Matt Gray | 1989 Hewson | 8 |
| Maze Mania sub03 | Matt Gray | 1989 Hewson | 1 |
| Maze Mania sub04 | Matt Gray | 1989 Hewson | 1 |
| Maze Mania sub05 | Matt Gray | 1989 Hewson | 1 |
| Motocross sub01 | Matt Gray | 1989 Codemasters | 12 |
| Motocross sub02 | Matt Gray | 1989 Codemasters | 1 |
| Motocross sub03 | Matt Gray | 1989 Codemasters | 1 |
| Motocross sub04 | Matt Gray | 1989 Codemasters | 1 |
| Tusker sub00 | Matt Gray | 1989 System 3 | 1 |
| Tusker sub01 | Matt Gray | 1989 System 3 | 2 |
| Tusker sub02 | Matt Gray | 1989 System 3 | 1 |
| Tusker sub03 | Matt Gray | 1989 System 3 | 1 |

### Future Composer — Michael Troelsen  ·  `native (Stage B)`  ·  5 songs / 19 SF2 files

| Song | Composer | Released | Parts |
|------|----------|----------|------:|
| Carillo part 2 | Michael Troelsen (Fun Fun) | 1988 Byterapers Inc. | 4 |
| Demo of the Year 88 Elite 1997 | Michael Troelsen (Fun Fun) | 1988 Triangle | 3 |
| Is There a Difference | Michael Troelsen (Fun Fun) | 1988 Triangle | 5 |
| Triangle 2 years | Michael Troelsen (Fun Fun) | 1989 Triangle | 4 |
| Triangle Intro | Michael Troelsen (Fun Fun) | 1988 Triangle | 3 |

<!-- END GENERATED -->

---

*Generated 2026-07-09. Fidelity figures are the latest measured/documented values; native
builds live in `bin/` and are not yet registry-wired into the auto pipeline. For the method
behind the numbers see [`docs/players/PLAYBOOK.md`](players/PLAYBOOK.md).*
