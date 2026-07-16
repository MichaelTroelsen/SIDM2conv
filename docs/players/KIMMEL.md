# Jeroen Kimmel player — SID → SF2 support

**Format:** a **Hubbard-derived** driver — a reused/hacked Rob Hubbard player, not a
clean-room engine. `player-id.exe` gives it its **own** signature (`Jeroen_Kimmel`),
distinct from `Rob_Hubbard`, and `sidm2/hubbard_parser.py` does **not** decode it
(it mislocates freq/instr). The TDZ KB card `rob-hubbard` names Kimmel among the
VGMPF-documented Hubbard reusers — this port is the first RE of the variant itself.
**Corpus:** `SID/Red_kommel_jeroen/` — 4 files:
* **Radax** (1989, CP-Verlag, load `$6000`, **6 subtunes**, relocating multi-subtune init)
* **Rhaa_Lovely_II_tune_2**, **Think_Twice_III**, **Think_Twice_V** (1987, "The Judges")

**Converter:** `bin/kimmel_to_sf2.py` → `out/kimmel_sf2/` (9 SF2s: Radax + Radax_sub1..5
+ the 3 single-subtune tunes). Parser: `sidm2/kimmel_parser.py`.
**Status:** **Stage A**, transpiled to the stock **Driver 11**. Standalone `bin/` builder —
**not** wired into `driver_selector`/`conversion_pipeline`.

> **ONE engine, not two generations.** Radax (1989) and the three 1987 "The Judges"
> tunes are the *same* driver at different tempos. Radax is merely relocated +
> multi-subtune; the emulate-init approach handles it transparently.

---

## Fidelity

Frame-pitch vs siddump (exact semitone, best global offset) — `bin/_kimmel_validate.py`:

| Tune | load | fpt | v0 | v1 | v2 |
|------|------|-----|----|----|----|
| Radax | `$6000` | 5 | **100.0** (n=128) | **100.0** (n=125) | **100.0** (n=20) |
| Rhaa_Lovely_II_tune_2 | `$1000` | 3 | **100.0** (n=156) | **100.0** (n=152) | 92.9 (n=14) |
| Think_Twice_III | `$B100` | 5 | **100.0** (n=11) | **100.0** (n=32) | **100.0** (n=8) |
| Think_Twice_V | `$1000` | 6 | **100.0** (n=86) | **100.0** (n=26) | **100.0** (n=69) |

**11 of 12 voice-medians are exact** (`med_diff = 0.0`); the lone 92.9% is Rhaa v2
(n=14, one effect note). Locate + decode succeed on 4/4.

> **VALIDATION TRAP — do not use gate onsets.** `fidelity_common.siddump_note_onsets`
> is GATE-rise based and returns near-**zero** for this engine: it plays legato and
> effects-driven, with few re-gates. Validate on **frame-pitch coverage** instead.
> A near-zero onset score here means the metric is wrong, not the decode.

---

## Engine map

Emulation-verified (py65 + zig64) on all 4 files; disassembly base = Think_Twice_V.

* **7-byte per-voice state stride** — `X = 0/7/14` (`TXA / ADC #7 / TAX / CPX #$15`).
* **Tempo** — a frame counter INCs per frame; a note-tick fires when it equals the
  per-tune tempo cell, then resets. `frames_per_tick` = that cell (TT-V 6, Rhaa 3,
  TT-III 5, Radax 5).
* **Note fetch (`$11FA`)** — a per-voice **orderlist** pointer (seeded from the song
  header at init) walks a list of **direct 2-byte pattern pointers** (lo, hi — *not*
  pattern numbers). Orderlist entry `hi=0` → loop, `hi=1` → stop.
* **Pattern note = 2 bytes** `[pitch, dur|instr]`; `pitch = 0` ends the pattern.
  byte0 = pitch index 0–95; byte1 bits0-4 = duration (lasts `dur+1` ticks),
  bits5-7 = instrument 0–7.
* **Freq tables are SPLIT** (`$11E3`) — HI table then LO table, 96 entries each,
  indexed by pitch. **Not** interleaved like stock Hubbard.
* **Instrument = 8-byte record** `[PWhi, wave_ctrl, AD, SR, pulse_speed, slide, arp, fx]`
  → `wave→$D404`, `AD→$D405`, `SR→$D406`, `PWhi→$D403`.
* **Instrument table base is PER-VOICE** (`LDA $1059,X`) — voice 1 has its own bank
  `$40` above v0/v2 on Radax/TT-III/Rhaa. Reading every voice from v0's bank gives
  wrong v1 timbre/arp (this was a real bug, fixed in `e0c2282`).

### Relocation-safe locate

All tables are found by **code signature**, never fixed offsets
(`sidm2/kimmel_parser.py`): `_FREQ_SIG`, `_ORD_SIG`, `_INSTR_SIG`, `_TEMPO_SIG`,
`_ARP_SIG`. `KimmelModule` emulates INIT via py65, then walks the orderlist/patterns
statically.

### Multi-subtune (Radax) — the relocating dispatcher

Radax's init is a **relocating multi-subtune dispatcher**, and it defeated the first
decoder (all 6 subtunes returned sub0's stale stream):

* **sub0** runs the `$6000` file image (play `$63D7`).
* **subtunes 1–5** relocate a *player copy* to `$E000` (play `$695C` → core `$E3B2`)
  and seed **that copy's** orderlist cells (`$E01E/$E025/$E02C`). The file-image
  tables (`$601E`…) never see them.

**Fix** (`cf02353`): after emulate-init, follow the per-subtune-patched play vector to
the play core, then locate tables in the **post-init RAM image** nearest that core
(`locate_mem` / `_play_core` / `_find_all_mem`). Fall back to static `locate()` when
the mem copy decodes 0 notes (sub0 + all single-subtune tunes — identical, so no
regression). `--subtune N` works end-to-end. Verified: **6/6 distinct streams** (was
1/6), 100% frame-pitch per voice, except sub3 v1 which is genuinely silent in the real
tune (a Stage-A rest-as-note artifact).

---

## The `$12CC` effects engine

The per-frame effects handler (`$12CC–$13D6` on TT-V) is what separates "notes are
right" from "sounds right" — the user's verdict on the first build was *"notes fine,
fidelity not there"*. RE'd and emitted as SF2 Driver 11 tables:

| Effect | Addr | Behaviour | SF2 emission |
|--------|------|-----------|--------------|
| **Arp** | `$12D7` | `Y = pitch + arp_table[arp_base(instr byte6) + counter++ mod 12]`; table = 12-entry blocks (repeating chords, e.g. Radax v1 = `[0,2,7]×4` at off 12) | wave-table arp rows |
| **PWM** | `$1323` | `pw += pulse_speed` (byte4) per frame; reset to `PWhi<<8` on note-on | pulse-table ramp (SET/ADD/loop) — **byte-exact** vs real trace |
| **Freq slide** | `$138E` | instrument **PWhi byte doubles as slide rate**: `freq += (PWhi & $F0)` per frame when the hi nibble ≠ 0; fx bit4 = up/down | Driver 11 **T0 slide command** (`XXYY` = signed-16) — driver-trace byte-exact |
| **Drum snap** | `$130C` | onset forces 1 frame of noise at `freq |= $8000` | `(0x81, high-abs-semitone)` wave row |

> **The PWhi double-duty finding** (`0a362a4`) is the non-obvious one: the same
> instrument byte is both the pulse-width high byte *and* the freq-slide rate. It
> affects many instruments (Radax i3/i4, the TT-III/TT-V leads).

`bin/kimmel_to_sf2.py` is the **first SIDM2 Stage-A builder to emit sequence
commands**. No `sf2_packer` change was needed — the emitter already packs
`D11Row.command`; the Commands table (`$1100`) is written post-emit by
`_patch_command_table` (read-only `sf2_parser`). Command set reference:
`docs/analysis/DRIVER11_TABLE_FORMATS.txt` (T0 slide / T1 vibrato / T2 portamento /
T3 arpeggio / T4 fret-slide).

**Verified through the real driver, not a model** — `bin/_kimmel_sf2_trace.py` takes
SF2 → `scripts/sf2_to_sid.py` → zig64 trace, so effects are checked *as Driver 11
actually plays them*. That is the gold standard for this port.

---

## Open (Stage B remainder — subtle, diminishing)

* **Secondary `$112E` freq-detune/chorus** on the arp (instr byte5 → a freq-domain
  per-frame detune synced to the arp counter, `+$100`/`+$200`). Maps to neither a
  clean wave-arp nor T1 vibrato — a subtle shimmer. **Not ported.**
* Fine drum fx-bit toggles (fx bits0-3: semitone-down / wf-EOR articulations, e.g.
  Radax i7 `fx=$26`) beyond the noise snap.
* Free-running arp phase (SF2 restarts the arp per note-on; negligible on fast arps).
* Rest/gate-off notes still play as notes (sub3 v1 rest-as-notes).
* Rhaa's one 36-semitone extreme arp block is clamped out (safe).
* Not wired into `driver_selector`/`conversion_pipeline`.
* No TDZ KB card yet (this is the first RE of the engine — worth writing one).

> **Corrected false alarm:** the "14931-byte SF2 cap" was **not** truncation. Rhaa and
> TT-III both dedup to exactly 31 unique sequences, so size = base + 31×stride — a
> coincidence. Byte-exact roundtrip reproduces every row; emitter limits
> (`_MAX_SEQUENCES 128` / `_SEQ_EVENT_LIMIT 960` / `_SEQ_BYTE_LIMIT 0xFA`) have large
> headroom. No emitter fix needed.

## Tooling

| Tool | Purpose |
|------|---------|
| `bin/kimmel_to_sf2.py` | Stage A builder (`--subtune N`) |
| `bin/_kimmel_validate.py` | frame-pitch validator (takes files as argv) |
| `bin/_kimmel_sf2_trace.py` | **gold standard**: SF2 → sf2_to_sid → zig64 trace |
| `bin/_kimmel_fx_re.py` / `_kimmel_fx_check.py` | effects-engine RE + per-frame diff |
| `bin/_kimmel_disasm.py` / `_kimmel_explore.py` / `_kimmel_locmem.py` / `_kimmel_multisubtune.py` | RE scratch |
| `pyscript/sf2_open_in_editor.py` | load an SF2 into SF2II (leaves it open) |

`bin/_kimmel_work/` holds the extracted PRGs + zig64 traces.

## Commits

`cc98a83` port → `cf02353` multi-subtune → `e0c2282` `$12CC` arp+PWM (+ per-voice
instrument-base bug fix) → `0a362a4` freq-slide (T0) + drum snap.

## See also

[PLAYBOOK.md](PLAYBOOK.md) · [PATTERNS.md](PATTERNS.md) · [HUBBARD.md](HUBBARD.md) ·
[DRIVER11.md](DRIVER11.md) · [../reference/ACCURACY_MATRIX.md](../reference/ACCURACY_MATRIX.md)
