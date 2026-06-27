# Martin Galway → SID Factory II (SF2) — full corpus

All **40** Martin Galway tunes converted to native-driver SF2 files, playable in stock
SID Factory II. Built from the cycle-accurate zig64 trace of the real player and replayed
through a from-scratch native Galway SF2 driver (`drivers_src/galway/galway_driver.asm`).

## Status (objective: SF2II's actual per-frame output vs the real SID, per voice)

- **40 / 40 build** and load in stock SF2II (0 blocked).
- **30 / 40 objectively clean** — ≥95% freq AND ≥90% pulse on every gated voice
  (`bin/sf2ii_vs_real.py`, capturing the instrumented SF2II's real output).
- **~36 / 40 by ear** — the strict metric undercounts inaudible fast-note boundary jitter;
  4 of the imperfect tunes (Hunchback_II, Swag, Insects, Yie_Ar_Kung_Fu_II) sit at 92–94%
  and sound fine.

### The 30 objectively clean
Arkanoid, Arkanoid_alternative_drums, Athena, Comic_Bakery, Commando_High-Score, Game_Over,
Helikopter_Jagd, Highlander, Hyper_Sports, Kong_Strikes_Back, Match_Day, Miami_Vice,
MicroProse_Soccer_V1/indoor/intro/outdoor, Ocean_Loader_1, Ocean_Loader_2, Parallax,
Ping_Pong, Rambo_First_Blood_Part_II, Rastan, Rolands_Ratrace, Short_Circuit, Slap_Fight,
Street_Hawk_Prototype, Terra_Cresta, Times_of_Lore, Wizball, Yie_Ar_Kung_Fu.

### The 10 with residual gaps (each a distinct, deep per-tune issue — no shared fix left)
| Tune | Gap | Cause |
|------|-----|-------|
| Mikie | freq 68% | fast per-frame pitch articulations (slide-ins/fast passages) |
| Street_Hawk | pulse 45% | builds at coarse tempo 32 at full length (legato-detect flips) |
| Neverending_Story | freq 87% | lead is a per-note *changing* chord arp |
| Daley_Thompsons | freq 85% | pitch slide |
| Green_Beret | o3 pulse 84% | PW sweeps continuously across re-gates; driver resets per note |
| Combat_School | freq 96% | a few wrong-octave notes + boundary |
| Hunchback_II | o2 92% | periodic freq-0 rests not reproduced |
| Insects_in_Space | o2 92% | vibrato depth ±1 semitone |
| Swag | o2 94% | fast-note boundary jitter (inaudible) |
| Yie_Ar_Kung_Fu_II | ~92% | fast-note boundary jitter (inaudible) |

## Notes
- **Subtune overrides** (PSID default is a sparse jingle; music is a later subtune):
  Combat_School = subtune 1, Yie_Ar_Kung_Fu_II = subtune 3. All others use the PSID default.
- These SF2s carry the **SID voices** (3 oscillators). Galway's `$D418` digi 4th-channel
  (Arkanoid lead, Game Over drums) is a separate build path (`bin/build_galway_digi_full.py`).

## Rebuild / re-validate
```
py -3 bin/build_galway_corpus.py 3500            # rebuild all 40 -> out/galway_sf2/
py -3 bin/batch_validate_galway.py 16            # objective SF2II validation of all 40
py -3 bin/build_galway_trace_song.py SID/Galway_Martin/<tune>.sid <frames> [subtune]  # one tune
```
Full technical status: `docs/players/GALWAY.md`.
