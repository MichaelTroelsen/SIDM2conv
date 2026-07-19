# SID to SF2 Conversion Index

A script-generated master list of every SID song that has actually been converted to an SF2 file on disk. Re-run after building/converting more tunes:

    py -3 pyscript/gen_conversion_index.py

See also [`docs/SF2.md`](SF2.md) for the native-build fidelity index (a narrower, hand-curated companion doc covering the same `out/` pipeline).

---

<!-- BEGIN GENERATED: conversion index -->

## Summary

**603 songs / 2207 SF2 files** converted on disk, across two independently-scanned locations (counts are NOT deduplicated between them — the same song may legitimately appear in both):

- `out/<player>/` native-build pipeline: **571 songs / 2175 files** across 9 player dirs
- `SF2/` (root + subdirs): **32 songs / 32 files** — **3 unresolved source match(es)**: SF2/ (root)/Blue (multiple), SF2/ (root)/Stinsens_Last_Night_of_89 (multiple), SF2/Hubbard_Rob/Commando (multiple)

*`output/` (repo root) was scanned and excluded: it holds only 3 stray `.sf2` files under test-report scratch dirs (`output/cockpit_test/`), duplicating names already covered by `SF2/` and not a real conversion location.*

---

## Songs converted per composer

*Every (composer, original player) pair appearing in either scanned location, aggregated by the PSID header's author field ("Composer" column above) — sorted by song count, descending. A composer who worked across more than one player/engine gets one row per player. `(unknown)` = a resolved source `.sid` with a blank author field; `(unresolved)` = the `SF2/`-side songs with no unambiguous source match (see the unresolved note above).*

| Composer | Original Player | Songs |
|----------|------------------|------:|
| Glenn Rune Gallefoss | SID Duzz' It (SDI) | 209 |
| Glenn Rune Gallefoss (Shark) | SID Duzz' It (SDI) | 134 |
| Rob Hubbard | Rob Hubbard | 60 |
| Johannes Bjerregaard | DMC (Demo Music Creator) | 55 |
| Martin Galway | Martin Galway | 40 |
| Jeroen Tel | Maniacs of Noise | 24 |
| Thomas Mogensen (DRAX) | Laxity_NewPlayer_V21 | 12 |
| Charles Deenen | Maniacs of Noise / Deenen | 9 |
| Michael Troelsen (Fun Fun) | Sound Monitor (Musicmaster) | 9 |
| Jeroen Kimmel | Jeroen Kimmel (Hubbard-derived) | 6 |
| Martin Galway | Martin_Galway | 5 |
| Michael Troelsen (Fun Fun) | ROMUZAK V6.3 | 4 |
| (unresolved) | unresolved | 3 |
| Charles Deenen (TMC) | Maniacs of Noise / Deenen | 3 |
| Jeroen Kimmel (Red) | Jeroen Kimmel (Hubbard-derived) | 3 |
| Rob Hubbard | Rob_Hubbard | 3 |
| (unknown) | Maniacs of Noise | 2 |
| Charles Deenen (TSS) | Maniacs of Noise / Deenen | 2 |
| Jeroen Tel & Markus Klein (LMan) | CheeseCutter_2.x | 2 |
| Johannes Bjerregaard (The Jerk) | DMC (Demo Music Creator) | 2 |
| Michael Troelsen (Coto) | Sound Monitor (Musicmaster) | 2 |
| Charles Deenen & Jeroen Tel | Maniacs of Noise / Deenen | 1 |
| G. R. Gallefoss & B. Vosseteig | SID Duzz' It (SDI) | 1 |
| Glenn Gallefoss & D. Bakewell | SID Duzz' It (SDI) | 1 |
| Glenn R. Gallefoss & R. Bayliss | SID Duzz' It (SDI) | 1 |
| Glenn Rune Gallefoss & Bjarte V | SID Duzz' It (SDI) | 1 |
| Glenn Rune Gallefoss & Mitch | SID Duzz' It (SDI) | 1 |
| Jeroen Tel | Rob_Hubbard | 1 |
| Laxity & Shogoon | SidFactory_II/Laxity | 1 |
| M. Troelsen (Fun Fun) & Chix | Soundmonitor | 1 |
| Michael Troelsen (Coto) | Soundmonitor | 1 |
| Michael Troelsen (Fun Fun) | MoN/FutureComposer | 1 |
| Rob Hubbard & Ben Daglish | Rob Hubbard | 1 |
| Thomas E. Petersen (Laxity) | Laxity_NewPlayer_V21 | 1 |
| Thomas E. Petersen (Laxity) | Rob_Hubbard | 1 |

---

## Native-build pipeline — `out/<player>/`

*The 9 known native/Driver-11-Stage-A player subdirectories under `out/` (same mapping as `pyscript/gen_sf2_index.py`). "Original Player" is the already-known label for these dirs (not re-detected); "SF2 Driver" is read live from each SF2's descriptor block.*

### DMC (Demo Music Creator) — Johannes Bjerregaard  ·  57 songs / 943 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| Again Its JB | DMC (Demo Music Creator) | 1 | Romuzak | 12 | Johannes Bjerregaard | 1989 Upfront |
| Alf TV Theme | DMC (Demo Music Creator) | 1 | Romuzak | 40 | Johannes Bjerregaard | 1988 Maniacs of Noise |
| Balloon | DMC (Demo Music Creator) | 1 | Romuzak | 1 | Johannes Bjerregaard | 1990 Johannes Bjerregaard |
| Billie Jean | DMC (Demo Music Creator) | 1 | Romuzak | 15 | Johannes Bjerregaard | 1990 Johannes Bjerregaard |
| Blobby | DMC (Demo Music Creator) | 1 | Romuzak | 2 | Johannes Bjerregaard | 19?? Johannes Bjerregaard |
| Blue Monday 88 | DMC (Demo Music Creator) | 1 | Romuzak | 7 | Johannes Bjerregaard | 1989 The Dominators |
| Camel Riders Inc | DMC (Demo Music Creator) | 1 | Romuzak | 12 | Johannes Bjerregaard (The Jerk) | 1987 The Jerk |
| Cant Stop | DMC (Demo Music Creator) | 1 | Romuzak | 114 | Johannes Bjerregaard | 1988 Upfront |
| Chase v2 | DMC (Demo Music Creator) | 1 | Romuzak | 11 | Johannes Bjerregaard | 1988 Johannes Bjerregaard |
| Cute Tune | DMC (Demo Music Creator) | 1 | Romuzak | 38 | Johannes Bjerregaard | 1988-90 Johannes Bjerregaard |
| Deel 2 | DMC (Demo Music Creator) | 1 | Romuzak | 8 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Depeche Mode Songs | DMC (Demo Music Creator) | 5 | Romuzak | 6 | Johannes Bjerregaard | 1986 Danish Music Company |
| DMC Demo IV tune 1 | DMC (Demo Music Creator) | 1 | Romuzak | 7 | Johannes Bjerregaard | 1988 Danish Music Company |
| DMC Demo IV tune 2 | DMC (Demo Music Creator) | 1 | Romuzak | 15 | Johannes Bjerregaard | 1988 Danish Music Company |
| DMC Demo IV tune 3 | DMC (Demo Music Creator) | 1 | Romuzak | 16 | Johannes Bjerregaard | 1988 Danish Music Company |
| Domino Dancing | DMC (Demo Music Creator) | 2 | Romuzak | 7 | Johannes Bjerregaard | 1988 Maniacs of Noise |
| Dragon Sword | DMC (Demo Music Creator) | 1 | Romuzak | 7 | Johannes Bjerregaard | 2018 Johannes Bjerregaard |
| Dreaming | DMC (Demo Music Creator) | 1 | Romuzak | 15 | Johannes Bjerregaard | 1988 Danish Music Company |
| Dreaming 2 | DMC (Demo Music Creator) | 1 | Romuzak | 28 | Johannes Bjerregaard | 1987 Danish Music Company |
| Dummy II | DMC (Demo Music Creator) | 1 | Romuzak | 11 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Dummynaytos | DMC (Demo Music Creator) | 1 | Romuzak | 1 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Eagles | DMC (Demo Music Creator) | 25 | Romuzak | 7 | Johannes Bjerregaard | 1987 Hewson |
| Fat 6 | DMC (Demo Music Creator) | 1 | Romuzak | 23 | Johannes Bjerregaard | 1988 Johannes Bjerregaard |
| First Try PSX | DMC (Demo Music Creator) | 1 | Romuzak | 47 | Johannes Bjerregaard | 1988 Johannes Bjerregaard |
| Fourth Dimension | DMC (Demo Music Creator) | 1 | Romuzak | 6 | Johannes Bjerregaard | 1988 Danish Music Company |
| French Frites | DMC (Demo Music Creator) | 1 | Romuzak | 64 | Johannes Bjerregaard | 1990 Johannes Bjerregaard |
| Fruitbank | DMC (Demo Music Creator) | 28 | Romuzak | 11 | Johannes Bjerregaard | 1989 Mastertronic/Dig. Design |
| Hit the Baze | DMC (Demo Music Creator) | 1 | Romuzak | 10 | Johannes Bjerregaard | 1988 Danish Music Company |
| In the Mood | DMC (Demo Music Creator) | 1 | Romuzak | 3 | Johannes Bjerregaard | 1988 Triton Technology |
| Jazz 1 | DMC (Demo Music Creator) | 1 | Romuzak | 31 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| M A C H | DMC (Demo Music Creator) | 9 | Romuzak | 2 | Johannes Bjerregaard | 1987 Starvision |
| Mixerplot | DMC (Demo Music Creator) | 1 | Romuzak | 9 | Johannes Bjerregaard | 1989 Upfront |
| MSI Demo | DMC (Demo Music Creator) | 1 | Romuzak | 36 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Music Demo | DMC (Demo Music Creator) | 2 | Romuzak | 32 | Johannes Bjerregaard | 1988 Maniacs of Noise |
| Myth Demo | DMC (Demo Music Creator) | 2 | Romuzak | 11 | Johannes Bjerregaard | 1989 Maniacs of Noise |
| Namnam Special | DMC (Demo Music Creator) | 1 | Romuzak | 20 | Johannes Bjerregaard | 1988 Danish Music Company |
| Omega Force One | DMC (Demo Music Creator) | 1 | Romuzak | 25 | Johannes Bjerregaard | 1988 64'er/Markt & Technik |
| Predictable main | DMC (Demo Music Creator) | 1 | Romuzak | 4 | Johannes Bjerregaard | 1989 Bones/Maniacs of Noise |
| Ragtime Anno 87 | DMC (Demo Music Creator) | 1 | Romuzak | 3 | Johannes Bjerregaard | 1987 Johannes Bjerregaard |
| Roadblaster | DMC (Demo Music Creator) | 1 | Romuzak | 1 | Johannes Bjerregaard | 19?? Johannes Bjerregaard |
| Rockbuster | DMC (Demo Music Creator) | 1 | Romuzak (1 stale legacy build excluded) | 16 | Johannes Bjerregaard | 1988 Danish Music Company |
| Scandalous | DMC (Demo Music Creator) | 1 | Romuzak | 19 | Johannes Bjerregaard | 1989 The Dominators |
| Shape | DMC (Demo Music Creator) | 1 | Romuzak | 38 | Johannes Bjerregaard | 1988 Upfront |
| Slimbo4 | DMC (Demo Music Creator) | 2 | Romuzak | 11 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Some Soul | DMC (Demo Music Creator) | 1 | Romuzak | 29 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Spacegame Music | DMC (Demo Music Creator) | 1 | Romuzak | 2 | Johannes Bjerregaard | 1987 The Main Force 2772 |
| Special Agent | DMC (Demo Music Creator) | 9 | Romuzak | 27 | Johannes Bjerregaard | 1987 Firebird |
| Spy vs Spy III | DMC (Demo Music Creator) | 1 | Romuzak | 23 | Johannes Bjerregaard | 1987 Johannes Bjerregaard |
| STII8 | DMC (Demo Music Creator) | 2 | Romuzak | 8 | Johannes Bjerregaard | 2014 Johannes Bjerregaard |
| Stormlord V2 | DMC (Demo Music Creator) | 1 | Romuzak | 2 | Johannes Bjerregaard | 1989 Maniacs of Noise |
| Test | DMC (Demo Music Creator) | 2 | Romuzak | 10 | Johannes Bjerregaard | 1989 Johannes Bjerregaard |
| Thunder Force | DMC (Demo Music Creator) | 4 | Romuzak | 8 | Johannes Bjerregaard | 1987 Rack-It |
| Tiny Symphony | DMC (Demo Music Creator) | 1 | Romuzak | 5 | Johannes Bjerregaard | 1988 Danish Music Company |
| Twilight Beyond | DMC (Demo Music Creator) | 1 | Romuzak | 4 | Johannes Bjerregaard | 1988 Danish Music Company |
| Wanna Get Sick | DMC (Demo Music Creator) | 1 | Romuzak | 7 | Johannes Bjerregaard | 1989 Upfront |
| Who Is Robb Vol 1 | DMC (Demo Music Creator) | 1 | Romuzak | 15 | Johannes Bjerregaard (The Jerk) | 198? The Jerk |
| Zoom | DMC (Demo Music Creator) | 19 | Romuzak | 1 | Johannes Bjerregaard | 1988 Discovery Software Int'l |

### Maniacs of Noise — Jeroen Tel  ·  26 songs / 200 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| Children Songs sub0 | Maniacs of Noise | 3 | Romuzak | 11 | Jeroen Tel | 1988 Maniacs of Noise |
| Cybernoid II sub0 | Maniacs of Noise | 2 | Romuzak | 13 | Jeroen Tel | 1988 Hewson |
| Cybernoid sub0 | Maniacs of Noise | 2 | Romuzak (1 stale legacy build excluded) | 13 | Jeroen Tel | 1988 Hewson |
| Daring Dots sub0 | Maniacs of Noise | 1 | Romuzak | 1 | Jeroen Tel | 1988 Maniacs of Noise |
| G I Hero sub0 | Maniacs of Noise | 2 | Romuzak | 13 | Jeroen Tel | 1988 Maniacs of Noise |
| Gaplus preview sub0 | Maniacs of Noise | 1 | Romuzak | 18 | Jeroen Tel | 1988 Maniacs of Noise |
| Gaplus sub0 | Maniacs of Noise | 23 | Romuzak | 27 | Jeroen Tel | 1988 Mastertronic |
| Hawkeye Proto 1 sub0 | Maniacs of Noise | 7 | Romuzak | 4 | Jeroen Tel | 198? Maniacs of Noise |
| Hawkeye sub0 | Maniacs of Noise | 12 | Romuzak | 7 | Jeroen Tel | 1988 Thalamus |
| Hawkeye sub2 | Maniacs of Noise | 12 | Romuzak | 2 | Jeroen Tel | 1988 Thalamus |
| Hawkeye sub2 native | Maniacs of Noise | ? | Romuzak | 1 |  |  |
| Hawkeye sub3 | Maniacs of Noise | 12 | Romuzak | 1 | Jeroen Tel | 1988 Thalamus |
| Hawkeye sub3 native | Maniacs of Noise | ? | Romuzak | 1 |  |  |
| Ice Age sub0 | Maniacs of Noise | 3 | Romuzak | 23 | Jeroen Tel | 1988 Maniacs of Noise |
| Iets van JT sub0 | Maniacs of Noise | 1 | Romuzak | 10 | Jeroen Tel | 1988 Maniacs of Noise |
| M A C C sub0 | Maniacs of Noise | 2 | Romuzak | 7 | Jeroen Tel | 1988 Maniacs of Noise |
| Myth sub0 | Maniacs of Noise | 3 | Romuzak | 8 | Jeroen Tel | 1989 System 3 |
| Pal sine hoener tune 1 sub0 | Maniacs of Noise | 1 | Romuzak | 3 | Jeroen Tel | 2020 Offence |
| Sample sub0 | Maniacs of Noise | 2 | Romuzak | 4 | Jeroen Tel | 1988 Maniacs of Noise |
| Supremacy sub0 | Maniacs of Noise | 3 | Romuzak | 13 | Jeroen Tel | 1991 Virgin |
| Supremacy sub1 | Maniacs of Noise | 3 | Romuzak | 2 | Jeroen Tel | 1991 Virgin |
| Supremacy sub2 | Maniacs of Noise | 3 | Romuzak | 10 | Jeroen Tel | 1991 Virgin |
| Thats preview sub0 | Maniacs of Noise | 1 | Romuzak | 1 | Jeroen Tel | 1988 Maniacs of Noise |
| Tomcat sub0 | Maniacs of Noise | 3 | Romuzak | 3 | Jeroen Tel | 1989 Digital L&M/Players |
| Viool Tello sub0 | Maniacs of Noise | 1 | Romuzak | 1 | Jeroen Tel | 1988 Maniacs of Noise |
| Wizzy sub0 | Maniacs of Noise | 1 | Romuzak | 3 | Jeroen Tel | 1988 Maniacs of Noise |

### Rob Hubbard — Rob Hubbard  ·  61 songs / 589 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| 5 Title Tunes song0 | Rob Hubbard | 5 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| 5 Title Tunes song1 | Rob Hubbard | 5 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| 5 Title Tunes song2 | Rob Hubbard | 5 | Romuzak | 2 | Rob Hubbard | 1985 Rob Hubbard |
| 5 Title Tunes song3 | Rob Hubbard | 5 | Romuzak | 2 | Rob Hubbard | 1985 Rob Hubbard |
| 5 Title Tunes song4 | Rob Hubbard | 5 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Action Biker song0 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1985 Mastertronic |
| Action Biker song1 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1985 Mastertronic |
| Action Biker song2 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1985 Mastertronic |
| Auf Wiedersehen Monty song0 | Rob Hubbard | 13 | Romuzak | 43 | Rob Hubbard & Ben Daglish | 1987 Gremlin Graphics |
| Chimera song0 | Rob Hubbard | 4 | Romuzak | 12 | Rob Hubbard | 1985 Firebird |
| Chimera song1 | Rob Hubbard | 4 | Romuzak | 1 | Rob Hubbard | 1985 Firebird |
| Commando song0 | Rob Hubbard | 19 | Romuzak | 4 | Rob Hubbard | 1985 Elite |
| Commando song16 | Rob Hubbard | 19 | Romuzak | 4 | Rob Hubbard | 1985 Elite |
| Commando song2 | Rob Hubbard | 19 | Romuzak | 1 | Rob Hubbard | 1985 Elite |
| Confuzion song0 | Rob Hubbard | 1 | Romuzak | 5 | Rob Hubbard | 1985 Incentive |
| Crazy Comets song0 | Rob Hubbard | 17 | Romuzak | 5 | Rob Hubbard | 1985 Martech |
| Crazy Comets song1 | Rob Hubbard | 17 | Romuzak | 1 | Rob Hubbard | 1985 Martech |
| Deep Strike song0 | Rob Hubbard | 1 | Romuzak | 25 | Rob Hubbard | 1987 Durell |
| Delta song0 | Rob Hubbard | 13 | Romuzak | 221 | Rob Hubbard | 1987 Thalamus |
| Delta song11 | Rob Hubbard | 13 | Romuzak | 3 | Rob Hubbard | 1987 Thalamus |
| Delta song12 | Rob Hubbard | 13 | Romuzak | 3 | Rob Hubbard | 1987 Thalamus |
| Geoff Capes Strongman Challenge song0 | Rob Hubbard | 24 | Romuzak | 1 | Rob Hubbard | 1986 Martech |
| Geoff Capes Strongman Challenge song3 | Rob Hubbard | 24 | Romuzak | 1 | Rob Hubbard | 1986 Martech |
| Geoff Capes Strongman Challenge song4 | Rob Hubbard | 24 | Romuzak | 1 | Rob Hubbard | 1986 Martech |
| Geoff Capes Strongman Challenge song5 | Rob Hubbard | 24 | Romuzak | 1 | Rob Hubbard | 1986 Martech |
| Gerry the Germ song0 | Rob Hubbard | 23 | Romuzak | 2 | Rob Hubbard | 1986 Firebird |
| Gerry the Germ song1 | Rob Hubbard | 23 | Romuzak | 1 | Rob Hubbard | 1986 Firebird |
| Gerry the Germ song4 | Rob Hubbard | 23 | Romuzak | 1 | Rob Hubbard | 1986 Firebird |
| Gerry the Germ song6 | Rob Hubbard | 23 | Romuzak | 1 | Rob Hubbard | 1986 Firebird |
| Gremlins song0 | Rob Hubbard | 26 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Gremlins song1 | Rob Hubbard | 26 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Gremlins song2 | Rob Hubbard | 26 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Gremlins song3 | Rob Hubbard | 26 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Gremlins song4 | Rob Hubbard | 26 | Romuzak | 2 | Rob Hubbard | 1985 Rob Hubbard |
| Gremlins song5 | Rob Hubbard | 26 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Gremlins song6 | Rob Hubbard | 26 | Romuzak | 1 | Rob Hubbard | 1985 Rob Hubbard |
| Hunter Patrol song0 | Rob Hubbard | 1 | Romuzak | 8 | Rob Hubbard | 1985 Mastertronic |
| Last V8 C128 version song0 | Rob Hubbard | 18 | Romuzak | 2 | Rob Hubbard | 1985 MAD/Mastertronic |
| Last V8 C128 version song1 | Rob Hubbard | 18 | Romuzak | 1 | Rob Hubbard | 1985 MAD/Mastertronic |
| Last V8 C128 version song2 | Rob Hubbard | 18 | Romuzak | 1 | Rob Hubbard | 1985 MAD/Mastertronic |
| Last V8 song0 | Rob Hubbard | 17 | Romuzak | 2 | Rob Hubbard | 1985 MAD/Mastertronic |
| Last V8 song1 | Rob Hubbard | 17 | Romuzak | 1 | Rob Hubbard | 1985 MAD/Mastertronic |
| Last V8 song11 | Rob Hubbard | 17 | Romuzak | 4 | Rob Hubbard | 1985 MAD/Mastertronic |
| Last V8 song2 | Rob Hubbard | 17 | Romuzak | 1 | Rob Hubbard | 1985 MAD/Mastertronic |
| Lightforce song0 | Rob Hubbard | 1 | Romuzak | 9 | Rob Hubbard | 1986 Faster Than Light (FTL) |
| Master of Magic song0 | Rob Hubbard | 3 | Romuzak | 6 | Rob Hubbard | 1985 MAD/Mastertronic |
| Master of Magic song1 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1985 MAD/Mastertronic |
| Master of Magic song2 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1985 MAD/Mastertronic |
| Monty on the Run song0 | Rob Hubbard | 19 | Romuzak | 4 | Rob Hubbard | 1985 Gremlin Graphics |
| Monty on the Run song1 | Rob Hubbard | 19 | Romuzak | 1 | Rob Hubbard | 1985 Gremlin Graphics |
| Monty on the Run song2 | Rob Hubbard | 19 | Romuzak | 1 | Rob Hubbard | 1985 Gremlin Graphics |
| Ninja song0 | Rob Hubbard | 1 | Romuzak | 21 | Rob Hubbard | 1986 Entertainment USA |
| One Man and his Droid song0 | Rob Hubbard | 14 | Romuzak | 11 | Rob Hubbard | 1985 Mastertronic |
| Saboteur II song0 | Rob Hubbard | 1 | Romuzak | 86 | Rob Hubbard | 1987 Rob Hubbard |
| Sanxion song0 | Rob Hubbard | 2 | Romuzak | 31 | Rob Hubbard | 1986 Thalamus |
| Shockway Rider song0 | Rob Hubbard | 1 | Romuzak | 22 | Rob Hubbard | 1987 Faster Than Light (FTL) |
| Star Paws song0 | Rob Hubbard | 3 | Romuzak | 10 | Rob Hubbard | 1987 Software Projects |
| Thing on a Spring song0 | Rob Hubbard | 17 | Romuzak | 4 | Rob Hubbard | 1985 Gremlin Graphics |
| Zoids song0 | Rob Hubbard | 3 | Romuzak | 4 | Rob Hubbard | 1986 Martech |
| Zoids song1 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1986 Martech |
| Zoids song2 | Rob Hubbard | 3 | Romuzak | 1 | Rob Hubbard | 1986 Martech |

### Martin Galway — Martin Galway  ·  40 songs / 40 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| Arkanoid | Martin Galway | 20 | Galway | 1 | Martin Galway | 1987 Imagine |
| Arkanoid alternative drums | Martin Galway | 2 | Galway | 1 | Martin Galway | 1987 Imagine |
| Athena | Martin Galway | 9 | Galway | 1 | Martin Galway | 1987 Imagine |
| Combat School | Martin Galway | 16 | Galway | 1 | Martin Galway | 1987 Ocean |
| Comic Bakery | Martin Galway | 14 | Galway | 1 | Martin Galway | 1986 Imagine |
| Commando High-Score | Martin Galway | 1 | Galway | 1 | Martin Galway | 1986 Martin Galway |
| Daley Thompsons Decathlon loader | Martin Galway | 1 | Galway | 1 | Martin Galway | 1984 Ocean |
| Game Over | Martin Galway | 2 | Galway | 1 | Martin Galway | 1987 Imagine |
| Green Beret | Martin Galway | 21 | Galway | 1 | Martin Galway | 1986 Imagine/Konami |
| Helikopter Jagd | Martin Galway | 16 | Galway | 1 | Martin Galway | 1986 Ocean |
| Highlander | Martin Galway | 1 | Galway | 1 | Martin Galway | 1986 Ocean |
| Hunchback II | Martin Galway | 23 | Galway | 1 | Martin Galway | 1984 Ocean |
| Hyper Sports | Martin Galway | 35 | Galway | 1 | Martin Galway | 1985 Imagine/Konami |
| Insects in Space | Martin Galway | 24 | Galway | 1 | Martin Galway | 1989 Hewson |
| Kong Strikes Back | Martin Galway | 1 | Galway | 1 | Martin Galway | 1984 Ocean |
| Match Day | Martin Galway | 7 | Galway | 1 | Martin Galway | 1986 Ocean |
| Miami Vice | Martin Galway | 2 | Galway | 1 | Martin Galway | 1986 Ocean |
| MicroProse Soccer indoor | Martin Galway | 17 | Galway | 1 | Martin Galway | 1988 MicroProse |
| MicroProse Soccer intro | Martin Galway | 1 | Galway | 1 | Martin Galway | 1988 MicroProse |
| MicroProse Soccer outdoor | Martin Galway | 8 | Galway | 1 | Martin Galway | 1988 MicroProse |
| MicroProse Soccer V1 | Martin Galway | 14 | Galway | 1 | Martin Galway | 1988 MicroProse |
| Mikie | Martin Galway | 12 | Galway | 1 | Martin Galway | 1986 Imagine |
| Neverending Story | Martin Galway | 1 | Galway | 1 | Martin Galway | 1985 Ocean |
| Ocean Loader 1 | Martin Galway | 1 | Galway | 1 | Martin Galway | 1985 Ocean |
| Ocean Loader 2 | Martin Galway | 1 | Galway | 1 | Martin Galway | 1985 Ocean |
| Parallax | Martin Galway | 5 | Galway | 1 | Martin Galway | 1986 Ocean |
| Ping Pong | Martin Galway | 19 | Galway | 1 | Martin Galway | 1986 Imagine |
| Rambo First Blood Part II | Martin Galway | 23 | Galway | 1 | Martin Galway | 1985 Ocean |
| Rastan | Martin Galway | 6 | Galway | 1 | Martin Galway | 1988 Imagine |
| Rolands Ratrace | Martin Galway | 20 | Galway | 1 | Martin Galway | 1985 Ocean |
| Short Circuit | Martin Galway | 5 | Galway | 1 | Martin Galway | 1986 Ocean |
| Slap Fight | Martin Galway | 9 | Galway | 1 | Martin Galway | 1987 Imagine |
| Street Hawk | Martin Galway | 26 | Galway | 1 | Martin Galway | 1986 Ocean |
| Street Hawk Prototype | Martin Galway | 1 | Galway | 1 | Martin Galway | 1985 Ocean |
| Swag | Martin Galway | 2 | Galway | 1 | Martin Galway | 1984 Micromania |
| Terra Cresta | Martin Galway | 11 | Galway | 1 | Martin Galway | 1986 Imagine |
| Times of Lore | Martin Galway | 11 | Galway | 1 | Martin Galway | 1988 Origin Systems |
| Wizball | Martin Galway | 9 | Galway | 1 | Martin Galway | 1987 Ocean |
| Yie Ar Kung Fu | Martin Galway | 19 | Galway | 1 | Martin Galway | 1985 Imagine |
| Yie Ar Kung Fu II | Martin Galway | 7 | Galway | 1 | Martin Galway | 1986 Imagine |

### ROMUZAK V6.3 — Oliver Blasnik  ·  4 songs / 4 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| Delirious 9 tune 1 | ROMUZAK V6.3 | 1 | Driver 11.00 - The Standard | 1 | Michael Troelsen (Fun Fun) | 1990 Genesis Project |
| Delirious 9 tune 1 native | ROMUZAK V6.3 | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1990 Genesis Project |
| Road of Excess end | ROMUZAK V6.3 | 1 | Driver 11.00 - The Standard | 1 | Michael Troelsen (Fun Fun) | 1990 Triangle |
| Road of Excess end native | ROMUZAK V6.3 | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1990 Triangle |

### Sound Monitor (Musicmaster) — Fun Fun  ·  11 songs / 27 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| Dance at Night remix | Sound Monitor (Musicmaster) | 1 | Romuzak | 8 | Michael Troelsen (Coto) | 1987 Danish Cracking Crew |
| Dreamix | Sound Monitor (Musicmaster) | 1 | Romuzak | 5 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Dreamix Two | Sound Monitor (Musicmaster) | 1 | Romuzak | 2 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Final Luv | Sound Monitor (Musicmaster) | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Fuck Off | Sound Monitor (Musicmaster) | 1 | Romuzak | 2 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Fun Mix | Sound Monitor (Musicmaster) | 1 | Romuzak | 2 | Michael Troelsen (Coto) | 1987 Danish Cracking Crew |
| Just Cant Get Enough | Sound Monitor (Musicmaster) | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1988 Triangle |
| No Title | Sound Monitor (Musicmaster) | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Poppy Road | Sound Monitor (Musicmaster) | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Thats All | Sound Monitor (Musicmaster) | 1 | Romuzak | 3 | Michael Troelsen (Fun Fun) | 1987 Triangle |
| Times Up | Sound Monitor (Musicmaster) | 1 | Romuzak | 1 | Michael Troelsen (Fun Fun) | 1987 Triangle |

### SID Duzz' It (SDI) — Gallefoss/Tjelta  ·  348 songs / 348 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| 2 Young 2 Die | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| 30seconds | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1992 Digital Designs |
| 64 Antheme | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Ablegoeyer | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Abrakadabra preview | SID Duzz' It (SDI) | 20 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Acid Jazz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Aerodynamic | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Afterburner | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Agrajag | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Airwalk | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| Airwalk 98 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Airwalk II | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Aldebaran | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Aldebaran sub1 | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Aldebaran sub2 | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Aldebaran sub3 | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Alf Theme | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Alone in Space | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Ambient | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Another Beginning | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE |
| Another Day in Paradize | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Arabia | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Arcane | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Arnhild | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Ayla Partyshaker | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Babar | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Bahbar | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Banana | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk |
| Banana Man | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Barbers Adagio 64 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Basselusk | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Batman in Jp | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Beginning | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE |
| Beverly Kraven | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Black Hole Sun Digi | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Blowfish | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Blue | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Boiled Beans | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' |
| Bossa Butt | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Bouncing | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Braveheart | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Burpmania | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' |
| Buttlern | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Calmdown II another one | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| Calmdown Whats this | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 SHAPE/Blues Muz' |
| Careless Whisper | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' |
| Cheese Pop | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| Close preview | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Club 69 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2004 SHAPE/Blues Muz' |
| Coming Soon | SID Duzz' It (SDI) | 2 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Commando | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 Nostalgia |
| Commercial Countdown | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Commies | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Computare Maximus Dominanus | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Countdown to NIL | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE |
| Country-Dip | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1995 Plush |
| Crizz Crozz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Culture Mix 1 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision |
| Culture Mix 2 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision |
| Curse | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Dancing in the Moonlight | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Danske-baaten | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Darkmoon | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Das Boot | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Regina |
| Day of the Tentacle DOTT | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Death of the Pulse v1 0 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| Deelight | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Delphines | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Delta | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Delta Slow | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 Nostalgia |
| Denver | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Derilicts | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Destruction | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Devotion | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Dialects | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Different Reality VE-4x | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' |
| Digital Designs Intro 2 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| DMC Demo remake | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2004 SHAPE/Blues Muz' |
| Domino Dancing | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Dorull | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Dreadful | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Dream | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Dreamland | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Eastbottom | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Effect Freak | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Electronic Transfer | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| End | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| End 94 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| End Music | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Enigma Elg moose | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Eurovision | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Everytime | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Evil Within | SID Duzz' It (SDI) | 2 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Evil Within sub1 | SID Duzz' It (SDI) | 2 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Extreme | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Fading Away | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Faeries | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Fast Pussy | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Filthy Hit VE-4x | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Fin Sang | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Finish Line | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Fjellgeit ode to Fearlight | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 Blues Muz' |
| Flames | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Flavour | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Flimbos | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1992 Digital Designs |
| Flunk | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Forbannet | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Funhouse | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Funk Facet | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Funkman | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Funkriff | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Funkriff v2 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Fusion | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Galvanized | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Genesis P | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| Get hyped | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Got Da Bluez | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Gracious | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Granturismo | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Graut | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| GRG in Cyberspace | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| GT Groove | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Guaranteed | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Happy Birthday Tg-Acme | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Hardcore | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Hava Nagila | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Heartbeat | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Heartbit | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Hickup | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| High Pressure | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Regina |
| Hithouse | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Holy Daze | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Holy Josh | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Homebrew | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| House Fantasy | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Hyperfool | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| I Aint Mad | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Imperial March | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Implocation VE-4x | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 SHAPE/Blues Muz' |
| Impossible Mission Theme | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Infra Red | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Interlude | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Intro | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Intro Aktig | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Intro Lime | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Intro Zax | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Intro Zax II | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Invention 1 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE |
| Iridion | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Jazz My Azz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Jazzmjux | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Jazzstones | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Jazzy-d | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| JB Groove I | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| JB Groove II | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Jessie Jazz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Joikaboller | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| JS Beta Song | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| JS Fanfare | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Juba-Jazz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Jule Fun | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1992 Digital Designs |
| Kald Kaffe | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Kalkun Yak | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Karamell | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Kirby | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Kleptoekko | SID Duzz' It (SDI) | 8 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Koke Stek | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Kururin | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| L-Forza long edit | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2010 Recollection |
| L-Forza Remix | SID Duzz' It (SDI) | 2 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2009 Byterapers |
| Lame | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk |
| Lederhosen | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Leon Latex | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2007 SHAPE |
| Lesbians | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Lethal Weapon | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Lightforce | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Little Bee | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Long Ting | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Looping | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Magic Moment | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Max Mix 1 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Mekkasang | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Menthol | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Micro Mix | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Microwave | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Milkshake | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 SHAPE/Blues Muz' |
| Mini Poelse | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk |
| Moi Funk | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Moonraker | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Morphosis | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Mozell | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Mummy | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Napalm | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Nasty Hombre | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Nephritis | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Neurotica | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Neurotica short | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 Onslaught |
| Neverending Story | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Nightjazz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1992 Blues Muz' |
| NineOneOne | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Ninja IV | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1991 Digital Designs |
| Nitro Dot | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Noice | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Norvegia thats a cheese | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Norway rulls | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss & Bjarte V | 1993 Digital Designs |
| Ode to Bugg | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' |
| Oh Boy VE-2x | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 SHAPE/Blues Muz' |
| Ohne Titel | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 SHAPE/Blues Muz' |
| Oldie | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Onkie Donkie | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Opening | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Orbital | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Organ Blues | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Oswaldo | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Other Day | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Outrun | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Overlord | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Painful | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Paranoid | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Pervers | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Phneumatic | SID Duzz' It (SDI) | 2 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Phneumatic sub1 | SID Duzz' It (SDI) | 2 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Pilz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Ping Reply from Outter Space | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE |
| Pjatt | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Pling Plong | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Polkapop | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Pop | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Potatoes | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Praiser | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Prelude | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Premature | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Preview Zax | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Product | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Promises | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Psychic | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Psycho | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Psycho II | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Psycho IV | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Pulstro | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Regina |
| Pultost VE-4x | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Punkfunk | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Pust | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Quaternion | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Quest | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Radbrekk I | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Rapture | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Rar Takt | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Raw and Mean | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Reaxion extended | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 Commodore Zone |
| Reaxion Extended Remix | SID Duzz' It (SDI) | 4 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 Commodore Zone |
| Rectum | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Regina/Blues Muz' |
| Reggie | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Remote | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1996 SHAPE/Blues Muz' |
| Reyn Only | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Regina/Blues Muz' |
| Rhyme | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Rintintin | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| RNA Reset Now Asshole | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Rocker | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Rough Boy | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Rumbah | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Sacrebleu | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Sad Song | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Sad Toob | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Scene plus III | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 FairLight |
| Scimitars | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Screaming | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| SCS TRC Intro Music | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1994 Regina/Blues Muz' |
| ShapeDigi | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Sharkie | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Shocking | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Short Deel | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2000 Nostalgia |
| Short One | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Short Zax | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Sidastic | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Slamtime | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Slapfart | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Slowjazz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Slowmotion | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Smiley | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Snip Snap | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Snufs | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Solar Plexus | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Sorrows | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Sound Test | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1992 Digital Designs |
| Space Suit | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1990 Collision/Kraftverk |
| Spellbound | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Stairway 1 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Stairway 2 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Stort Plaster | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz'/HVSC |
| Strangers | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Strangle | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz'/Onslaught |
| Suburbia | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Sugarhill | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Super Galaxy preview | SID Duzz' It (SDI) | 54 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Survival | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Sveitser Ost | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Sweeper | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Sweet JB | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Syk Sang | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Synchro | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| Syncomatic | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Synthfunk | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |
| T-Shirt | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Tango | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Tanks 3000 | SID Duzz' It (SDI) | 13 | Driver 11.00 - The Standard | 1 | Glenn R. Gallefoss & R. Bayliss | 2006 Protovision |
| Tarmslyng | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Techno | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Techno-Kaare | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Techno Chaos | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Techno Rave | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss & Mitch | 1994 SHAPE/Crest |
| Teddy Bear | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Tekkno Tuna Sandwich | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Ten Seconds | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Terpentin | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1993 Digital Designs |
| Test-trip | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Tight Jeans | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Timbuktu | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Tissemann | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1993 Digital Designs |
| Toto | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Trakten | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Tranedans | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Trapped | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| Trist | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Gallefoss & D. Bakewell | 1999 Blues Muz' |
| Trooper | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Tunfiskpizza | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Twin Peaks | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 The Freaks |
| Tycoon | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Tycoon 2 | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| U May C | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Underwear VE-4x | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Velomatrix | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 SHAPE/Blues Muz' |
| Vicious Circles | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2001 SHAPE/Blues Muz' |
| Vikings | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Virtual | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Vozza Jazz | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1994 The Radbrekkjers |
| Warbeat | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Wash and Go | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1991 Digital Designs |
| Wavetrip | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1997 SHAPE/Blues Muz' |
| Weirdo | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2002 SHAPE/Blues Muz' |
| What Is Love | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Xard | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2006 SHAPE/Blues Muz' |
| Yeah | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1999 SHAPE/Blues Muz' |
| Yesterday | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | G. R. Gallefoss & B. Vosseteig | 1994 SHAPE/Blues Muz' |
| Zakazazam | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1998 SHAPE/Blues Muz' |
| Zap | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 2007 SHAPE/Blues Muz' |
| Zexest | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss (Shark) | 1992 Digital Designs |
| Zoophyte | SID Duzz' It (SDI) | 1 | Driver 11.00 - The Standard | 1 | Glenn Rune Gallefoss | 1995 SHAPE/Blues Muz' |

### Jeroen Kimmel (Hubbard-derived) — Jeroen Kimmel  ·  9 songs / 9 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| Radax | Jeroen Kimmel (Hubbard-derived) | 6 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag |
| Radax sub1 | Jeroen Kimmel (Hubbard-derived) | 6 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag |
| Radax sub2 | Jeroen Kimmel (Hubbard-derived) | 6 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag |
| Radax sub3 | Jeroen Kimmel (Hubbard-derived) | 6 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag |
| Radax sub4 | Jeroen Kimmel (Hubbard-derived) | 6 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag |
| Radax sub5 | Jeroen Kimmel (Hubbard-derived) | 6 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel | 1989 Magic Disk 64/CP Verlag |
| Rhaa Lovely II tune 2 | Jeroen Kimmel (Hubbard-derived) | 1 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel (Red) | 1987 The Judges |
| Think Twice III | Jeroen Kimmel (Hubbard-derived) | 1 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel (Red) | 1987 The Judges |
| Think Twice V | Jeroen Kimmel (Hubbard-derived) | 1 | Driver 11.00 - The Standard | 1 | Jeroen Kimmel (Red) | 1987 The Judges |

### Maniacs of Noise / Deenen — Charles Deenen  ·  15 songs / 15 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |
|------|------------------|---------:|------------|------:|----------|----------|
| After the War | Maniacs of Noise / Deenen | 3 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1989 Dinamic |
| Aids See Ass | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen (TSS) | 198? HC-Ass 5005 |
| Astro Marine Corps | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1989 Dinamic |
| B A T | Maniacs of Noise / Deenen | 6 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1990 Ubisoft |
| Constant Runner | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1989 Masters' Design Group |
| Crazy Music | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen (TMC) | 1987 Hotline |
| Ding van Charles | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen | 19?? Maniacs of Noise |
| Give It a Try | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen (TMC) | 1987 Scoop Designs |
| I Saw 2 HC-Ass 5005s Fucking | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen (TMC) | 1987 HC-Ass 5005 |
| Lord of the Rings | Maniacs of Noise / Deenen | 9 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1990 Interplay |
| Melig | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1989 Maniacs of Noise |
| Say Hello to the Boring Times | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1988 Maniacs of Noise |
| Soldier of Light | Maniacs of Noise / Deenen | 20 | Driver 11.00 - The Standard | 1 | Charles Deenen & Jeroen Tel | 1988 Reptilia Design/Softek Int |
| Super Heavy | Maniacs of Noise / Deenen | 1 | Driver 11.00 - The Standard | 1 | Charles Deenen (TSS) | 198? HC-Ass 5005 |
| Zamzara | Maniacs of Noise / Deenen | 3 | Driver 11.00 - The Standard | 1 | Charles Deenen | 1989 Rack-It |

---

## Separate conversion set — `SF2/`

*Loose conversions under `SF2/` (root + subdirs), predating/parallel to the `out/` native pipeline — NOT necessarily the same build as an `out/` song with the same name. "Original Player" is detected fresh per song via `tools/player-id.exe` against the matched source `.sid` (searched across the whole `SID/` tree); "unresolved" = zero or multiple candidate source files were found and the match was not guessed.*

### SF2/ (root)  ·  14 songs / 14 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |
|------|------------------|---------:|------------|------:|----------|----------|------------|
| Angular | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2017 Camelot/Vibrants | `SID/Angular.sid` |
| Balance | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2013 Vibrants | `SID/Balance.sid` |
| Beast | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2011 Maniacs of Noise | `SID/Beast.sid` |
| Blue | unresolved | ? | Laxity | 1 |  |  | `unresolved (multiple matches)` |
| Cascade | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2006 Maniacs of Noise | `SID/Cascade.sid` |
| Chaser | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2006 Maniacs of Noise | `SID/Chaser.sid` |
| Colorama | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2013 Alpha Flight | `SID/Colorama.sid` |
| Cycles | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2005 Maniacs of Noise | `SID/Cycles.sid` |
| Delicate | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2015 Chorus | `SID/Delicate.sid` |
| Dreams | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2008 Chorus | `SID/Dreams.sid` |
| Dreamy | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2011 Maniacs of Noise | `SID/Dreamy.sid` |
| Phoenix Code End Tune | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2016 Bonzai | `SID/Phoenix_Code_End_Tune.sid` |
| Stinsens Last Night of 89 | unresolved | ? | Laxity | 1 |  |  | `unresolved (multiple matches)` |
| Unboxed Ending 8580 | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas Mogensen (DRAX) | 2018 Bonzai | `SID/Unboxed_Ending_8580.sid` |

### SF2/Fun_Fun  ·  3 songs / 3 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |
|------|------------------|---------:|------------|------:|----------|----------|------------|
| Byte Bite | Soundmonitor | 1 | Driver 11.00 - The Standard | 1 | M. Troelsen (Fun Fun) & Chix | 1987 Triangle | `SID/Fun_Fun/Byte_Bite.sid` |
| Carillo part 2 | MoN/FutureComposer | 1 | Driver 11.00 - The Standard | 1 | Michael Troelsen (Fun Fun) | 1988 Byterapers Inc. | `SID/Fun_Fun/Carillo_part_2.sid` |
| Dance at Night remix | Soundmonitor | 1 | Driver 11.00 - The Standard | 1 | Michael Troelsen (Coto) | 1987 Danish Cracking Crew | `SID/Fun_Fun/Dance_at_Night_remix.sid` |

### SF2/Galway_Martin  ·  5 songs / 5 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |
|------|------------------|---------:|------------|------:|----------|----------|------------|
| Arkanoid | Martin_Galway | 20 | Driver 11.00 - The Standard | 1 | Martin Galway | 1987 Imagine | `SID/Galway_Martin/Arkanoid.sid` |
| Arkanoid alternative drums | Martin_Galway | 2 | Driver 11.00 - The Standard | 1 | Martin Galway | 1987 Imagine | `SID/Galway_Martin/Arkanoid_alternative_drums.sid` |
| Athena | Martin_Galway | 9 | Driver 11.00 - The Standard | 1 | Martin Galway | 1987 Imagine | `SID/Galway_Martin/Athena.sid` |
| Comic Bakery | Martin_Galway | 14 | Driver 11.00 - The Standard | 1 | Martin Galway | 1986 Imagine | `SID/Galway_Martin/Comic_Bakery.sid` |
| Game Over | Martin_Galway | 2 | Driver 11.00 - The Standard | 1 | Martin Galway | 1987 Imagine | `SID/Galway_Martin/Game_Over.sid` |

### SF2/Hubbard_Rob  ·  4 songs / 4 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |
|------|------------------|---------:|------------|------:|----------|----------|------------|
| 5 Title Tunes | Rob_Hubbard | 5 | Driver 11.00 - The Standard | 1 | Rob Hubbard | 1985 Rob Hubbard | `SID/Hubbard_Rob/5_Title_Tunes.sid` |
| ACE II | Rob_Hubbard | 1 | Driver 11.00 - The Standard | 1 | Rob Hubbard | 1987 Cascade Games | `SID/Hubbard_Rob/ACE_II.sid` |
| Action Biker | Rob_Hubbard | 3 | Driver 11.00 - The Standard | 1 | Rob Hubbard | 1985 Mastertronic | `SID/Hubbard_Rob/Action_Biker.sid` |
| Commando | unresolved | ? | Driver 11.00 - The Standard | 1 |  |  | `unresolved (multiple matches)` |

### SF2/Tel_Jeroen  ·  3 songs / 3 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |
|------|------------------|---------:|------------|------:|----------|----------|------------|
| 05-09-87 | Rob_Hubbard | 1 | Driver 11.00 - The Standard | 1 | Jeroen Tel | 1987 Maniacs of Noise | `SID/Tel_Jeroen/05-09-87.sid` |
| 11 Heaven | CheeseCutter_2.x | 1 | Driver 11.00 - The Standard | 1 | Jeroen Tel & Markus Klein (LMan) | 2018 Maniacs of Noise | `SID/Tel_Jeroen/11_Heaven.sid` |
| 11 Heaven 6581 Version | CheeseCutter_2.x | 1 | Driver 11.00 - The Standard | 1 | Jeroen Tel & Markus Klein (LMan) | 2023 Maniacs of Noise | `SID/Tel_Jeroen/11_Heaven_6581_Version.sid` |

### SF2/Laxity  ·  3 songs / 3 SF2 files

| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |
|------|------------------|---------:|------------|------:|----------|----------|------------|
| 1983 Sauna Tango | SidFactory_II/Laxity | 1 | Laxity | 1 | Laxity & Shogoon | 2021 Laxity & Shogoon | `SID/Laxity/1983_Sauna_Tango.sid` |
| 2000 A D | Rob_Hubbard | 1 | Driver 11.00 - The Standard | 1 | Thomas E. Petersen (Laxity) | 1987 Wizax 2004 | `SID/Laxity/2000_A_D.sid` |
| 21 G4 demo tune 1 | Laxity_NewPlayer_V21 | 1 | Laxity | 1 | Thomas E. Petersen (Laxity) | 2005 Vibrants/Maniacs of Noise | `SID/Laxity/21_G4_demo_tune_1.sid` |

<!-- END GENERATED -->
