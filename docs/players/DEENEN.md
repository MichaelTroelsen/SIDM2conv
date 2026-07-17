# Charles Deenen — SID → SF2 support

**Corpus:** `SID/deenen/` — 40 `.sid`, all tagged "Charles Deenen / 1988 Maniacs of Noise".

> **The corpus is NOT one player, and it is NOT the MoN engine SIDM2 already
> supports.** [MON.md](MON.md) documents the *Jeroen Tel* Hawkeye/Cybernoid engine.
> These are different dialects that happen to share the MoN banner.

`player-id.exe` (`tools/player-id.exe -m`, `tools/sidid.cfg`) splits them:

| Group | N | Status |
|-------|---|--------|
| **MoN/Deenen game replay** | 19 | the fresh RE below — 10 located, **6 clean wins** |
| **MoN/FutureComposer** (*not* the `$1800` FC variant) | 15 | untouched |
| **Soundmonitor** | 3 | **freebie wins at 100%** (see below) |
| **Rob_Hubbard V1** | 2 | **freebie wins at ~100%**, stock pipeline unchanged |
| SFX bank | 1 | n/a |

**Status:** **Stage A**, standalone `bin/` builders — **not** wired into
`driver_selector`/`conversion_pipeline`. Parser: `sidm2/deenen_parser.py`.
Output: `out/deenen_sf2/` (12 validated SF2s).

---

## The freebies — 8 files at ~100% before any new RE

Worth reading as a method note: **a third of the useful corpus was already supported
and merely misfiled.** Classification before RE paid for itself.

* **3 Sound Monitor** — `Aids_See_Ass` 212/212, `Super_Heavy` 262/262,
  `I_Saw_2_HC-Ass..` 205/205 = **100%**. They are stock SM at fixed addresses
  (`$A000` bars / `$AE00` sound / `$C416` freq) behind a **bank-switch play wrapper**
  (play `$C020` → `JSR $C475`) carrying a 2-byte prefix. That pushed the play
  **signature +2**, so `is_soundmonitor()` rejected them. Fix: `bin/deenen_sm_build.py`
  relaxes the play-sig gate (accept +0..+3) and reuses the stock SM builder.
  See [SOUNDMONITOR.md](SOUNDMONITOR.md).
* **2 Hubbard V1** — `Crazy_Music`, `Give_It_a_Try` ≈100% through the unchanged stock
  pipeline. See [HUBBARD.md](HUBBARD.md).
* **3 MoN TTWII files decode EXACT at subtune 0** — `Say_Hello` 451/451,
  `Soldier_of_Light` 114/114, `Melig` 89/89.
  > **GOTCHA:** the MoN default **subtune 3 is a mis-located-speed-table pseudo-parse
  > trap** (speed=155 garbage). The real song is **subtune 0**. `Double_Dragon` is
  > partial (V2 exact, V0 misaligned); `Zynon` pseudo-parses and is rejected.

---

## The Deenen-replay engine (fresh RE, emulation-grounded on Ding_van_Charles)

* **Dispatch signature:** `C9 60 B0 03 4C` (`CMP #$60 / BCS +3 / JMP note-handler`) — 15/19.
* **Two-level:** per-voice **orderlist** (ptr `$195C[v*2 + subtune*8]` + reloc) →
  **pattern** (ptr `$11B1[pat*2]` + reloc).
* **Orderlist grammar:** `<$5F` pattern#, `$5F-$6E` A-transpose, `$6F-$7F` pattern-loop
  count, `$80-$FD` note-transpose (val−$82), `$FE` stop, `$FF` **segment-advance**.
* **Pattern row:** prefixes then a note — `$C0-$DF` instrument (+A-transpose),
  `$80-$BF` default-duration (val−$81, **accumulates**), `$60-$7F` arp param,
  `<$60` NOTE, `$E0-$FA` rest, `$FD/$FC/$FB/$FE` slide/enable/gate/speed.
* **Note→SID:** pitch = note+transpose → **split** freq tables FREQ_LO/FREQ_HI
  (95-entry, `|hi − lo| = $5F`). Instrument record @ `INSTR + i*8`:
  `[0]` packed PW, `[1]` waveform, `[2]` AD, `[3]` SR, `[4]` flags (bit3 = filter),
  `[7]` flags.
  > ⚠️ **WHICH of the pair is LO is NOT decided by address order.** Ding-class rips
  > put LO at the lower address (`hi = lo + $5F`); **Zamzara reverses it** (`$C3EE`
  > = HI, `$C44D` = LO). Assuming "lower = LO" byte-swaps every frequency while
  > leaving note indices perfect — invisible to any index-level check. Decide from
  > the **SID write** (`LDA zp,X / STA $D400,Y` = LO, `$D401` = HI) and trace the zp
  > back to its table. `DeenenModule._fix_freq_table_order()` does this, on positive
  > evidence only.
* **Relocation-safe locate:** every table address comes from **code operands** (freq =
  the `LDA abs,Y` pair differing by `$5F`; instr = the consecutive-operand `LDA abs,Y`
  cluster; ord/pat/reloc via `LDA..,X/Y` → `ADC reloc`). `flow_offsets()` flow-disassembles
  from init/play so scans anchor to **reachable** `AA BD` / `0A A8 B9` and pin reloc
  from the trailing ADC. Two reloc modes: **Variant A "Ding-class"** (`ADC reloc`) and
  **Variant B "Smooth-class"** (absolute pointers, reloc 0).

### The groove clock — the timing key

Note-duration counters advance only **~2 of every 5 frames**, gated by `$10CB`
(reload-4) + `$106F == $106B`.

> **The rate is NOT a constant — it VARIES per file**, and hardcoding ~2.5 was the
> single biggest onset error. Emulator-measured `DEC $0D2A-class,X` decrement periods:
> B_A_T **3**, LotR **2**, Ding **2.5** (alternating 2/3), Astro **2**, After_War **2.5**.

`groove_rate()` measures it by **emulation only**: pick the one global scalar R from
`{1.5, 2, 2.5, 3, 3.5, 4, 5, 6}` whose uniform schedule `frame = R × tick` best aligns
the decoder onset stream to the real gate-rise stream under a monotonic 1-1 match. A
single scalar cannot overfit hundreds of onsets except at the true tempo.
**Ratio-of-medians was tried first and is WRONG** — decode over-generation skews the
median to 5.25.

---

## Fidelity — `bin/deenen_validate.py`

**10/19 located · 6 clean wins** (plausible, onset ≥75, pitch ≥75) — as of 2026-07-17:

| Tune | onset% | pitch% | note |
|------|--------|--------|------|
| **Ding_van_Charles** | **100.0** | **100.0** | the RE reference |
| **B_A_T** | **100.0** | **100.0** | needed the segment-seed fix |
| **Lord_of_the_Rings** | **100.0** | **100.0** | |
| **After_the_War** | **100.0** | **100.0** | |
| **Zamzara** | **100.0** | **100.0** | own row + orderlist grammar; freq tables were byte-swapped (see below) |
| **Astro_Marine_Corps** | **77.4** | **91.5** | unlocked by the pitch-settle-window fix |
| Constant_Runner | 100.0 | 97.7 | decode **exact** [113,101,44]; refused — voice1 arpeggio unmodelled |
| Eye_to_Eye_intro | 100.0 | 62.5 | reloc |
| Mr_Heli | 19.7 | 43.3 | ZP-loop variant |
| Mantalos | 33.3 | 50.0 | `ff_mode=='seg'` → Ding path; separately broken |

**Refused, not emitted** (`plausible()` = False): Mr_Heli, Constant_Runner, Eye_to_Eye,
Mantalos. **Not located** (9): F1_Simulator, Hotline_Intro_Tune, Satan,
Shitty_Disco_Dump, Smooth_Criminal, Cool_Tune, Hotline_Intro, Koekoek, BTTF3.

> ⚠️ **`bin/deenen_engine_check.py` read 100/100/100 on Zamzara while every
> frequency it emitted was byte-swapped.** That tool watches the note-INDEX
> store; the corruption was downstream in index→frequency (`DeenenLocate`
> pairs the split freq tables by ADDRESS ORDER — `hi-lo == $5F` — but Zamzara
> lays them out reversed). A ground-truth tool certifies only the quantity it
> actually watches. **Note-exact decode + a pitch metric that still disagrees
> ⇒ suspect index→frequency BEFORE inventing an unmodelled effect** (this was
> first misdiagnosed as a portamento — wrong). Fixed by
> `DeenenModule._fix_freq_table_order()`, which decides from the SID write
> rather than the address order: it finds the per-voice shadow feeding
> `$D400`/`$D401` (both shapes occur — `LDA zp,X` on Zamzara, `LDA abs,X` on
> the Ding class), then checks which table's `LDA tbl,Y` cluster stores into
> which shadow. Acts only on positive evidence and abstains otherwise.
> **All 10 located files now come back positively VERIFIED** (no
> abstentions), and Zamzara is the only one it rewrites — so every clean
> win's freq order is confirmed from code, not assumed.

> **The builder REFUSES to emit garbage.** `plausible()` rejects degenerate/runaway
> decodes that `ok()` cannot see (Eye_to_Eye all-note-`$06`; Zamzara used to read
> all-`$00` here before its orderlist/row grammar was ported — it now decodes
> cleanly and passes), plus a **dead-voice guard**: a 0-note voice beside a
> >20-note voice means a broken decode (Mr_Heli v0). It also refuses the whole
> `$40`-class *except* Zamzara-class rips, whose rows ARE ported (Constant_Runner
> stays refused: structurally exact, but its voice1 arpeggio is unmodelled).
> `--force` overrides. This is deliberate: never ship lossy output silently.

### The B_A_T segment-seed bug (worth remembering)

`seg_seed=4` was the **subtune-table index**, not the segment base. Init
`0A0A0A 69 04` = `song*8+4` → the `$1AA2` subtune table. The real per-voice segment
base (`$0CAC`-class) inits to **0**: the emulator shows voices reading `$195C` words
@0/@2/@4, so `segidx0 = 0`, advancing by `+seg_step` to @63/@65/@67. `_segidx0()` now
tries base/0 **before** the seed candidates. The located `seg_cap=62`/`seg_step=63`
were correct all along — the "64" first observed was the **hi-byte read of index 63**.

---

## ⚠️ READ THIS FIRST: half the corpus is the JEROEN TEL engine (2026-07-16)

> **The `pattern < $40` files are running the MoN (Jeroen Tel) engine that SIDM2
> already supports. Do not write a decoder for them — `sidm2/mon_parser.py`
> already implements their exact byte grammar. The work is LOCATE, not decode.**

`mon_parser.py:397-404` (shipping, tested, used for Hawkeye/Cybernoid):
```python
if b >= 0x80:                    # $80-$FF: transpose ($90F9 = b & $1F)
if b >= 0x60:                    # $60-$7F: instrument base ($9139 = b & $0F)
if b >= 0x40:                    # $40-$5F: REPEAT counter for the next pattern
    repeat = (b & 0x3F) + 1      #   ($9118 = b&$3F -> replays N+1 times)
```
That is **byte-for-byte** what Constant_Runner's `$13F3` routine does
(`SEC / SBC #$40 -> $e0,X`, then `DEC $e0,X` at `$145B` = the repeat counter;
`SBC #$60 -> $dd,X`; `SBC #$80 -> $da,X`).

**The 12 `< $40` files:** Airwolf, Constant_Runner, Day_After_the_Beat,
Double_Dragon, F1_Simulator, Mantalos, Melig, Mr_Heli, Say_Hello_to_the_Boring_Times,
Zamzara, Zamzara_v1, Zynon.
**Two are already proven Tel-engine** — `Melig` and `Say_Hello` are two of the three
"MoN TTWII" freebies that decode EXACT at subtune 0 through `mon_parser`. The other
10 fail only because MoN's *locate* doesn't find their rips (`mon_validate` returns
`0/0` — a vacuous no-evidence result, not a decode failure).

**Next step for this corpus is therefore NOT a Deenen decoder.** It is: extend
`mon_parser`'s locate to these rips, which also puts them on the MoN **native Stage B**
path (100% byte-exact on Hawkeye) rather than Stage A transpile.

**How this was missed for three sessions:** the KB *did* have it — in the
`maniacs-of-noise` card, which lists these exact byte ranges. Searching it for
"Deenen" / "variant B" / "groove" returned nothing, because the knowledge was filed
under a different player. **Search the KB by MECHANISM (the byte ranges, the opcode
shape), not by composer or variant name.**

### The pattern ROWS did not need porting — only the orderlist did

Checked by disassembly (the row dispatch is the `C9 60 B0 03 4C` signature; the
class constants are the CMP/SBC immediates that follow):

| file | row-class CMPs | SBCs | verdict |
|------|----------------|------|---------|
| Ding_van_Charles | `$60 $FF $FE $FD $FC $FB $E0 $C0` | `$E1 $C0 $81` | the implemented grammar |
| Constant_Runner | `$60 $FF $FE $FD $FC $FB $E0 $C0` | `$E1 $C0 $81` | **identical to Ding** |
| Mantalos | `$60 $FF $FE $FD $FC $FB $E0 $C0` | `$E1 $C0 $81` | **identical to Ding** |
| **Zamzara** | `$60 $FD $FE $FC $E0 $C0 $80 …` | `$C8 $F6 $C8 $C8 $E1` | **its own row grammar** |

So `_parse_row` is already right for the Tel-class files, and the note formation
is too — Constant_Runner's `$1519` handler is `LDA $d0 / CLC / ADC $da,X` then
index `FREQ_LO $12AF` / `FREQ_HI $130E` (`$130E-$12AF = $5F`), exactly what
`_emit_note` does.

**Therefore Constant_Runner's residual 35.6% pitch is NOT a row-grammar issue.**

### PROVEN: Constant_Runner's decode is EXACT — the metric is wrong, not the decoder

`bin/deenen_engine_check.py` compares the decoder against **the player's own
computed note**, watching the note handler's `STA $f2,X` (`$152A`) under py65 —
no metric in between, no inference about SID output:

```
Constant_Runner   v0 100.0% n=92   v1 100.0% n=80   v2 100.0% n=34
```

**All three voices, every note, exact.** Meanwhile `deenen_validate` reports
pitch 35.6% for the same file. So the decoder reproduces the player perfectly and
the onset+pitch metric disagrees — a metric artifact, not a decode error.

Two suspects were tested and **refuted**, so don't retry them:
* **`$da,X` seeded by init** — no: it is `$00` on all three voices after init,
  exactly as the decoder assumes.
* **note index ≠ semitone** (the tune's own freq table being off-grid) — no:
  both Ding's `$10F3` and Constant_Runner's `$12AF` tables give
  `index == freq_to_semi(freq)` exactly.
* Slide density was a third guess and is **weak**: B_A_T has MORE `$FD` slide
  bytes (27) than Constant_Runner (23) and still scores 100/100.

**The guard stays on** (`plausible()` refuses the `$40` class) despite the proof.
The engine-check validates NOTES ONLY — not timing, timbre or effects — so
"the notes are right" is not yet "the SF2 is right", and until the metric
disagreement is *explained* rather than merely observed, emitting would be
shipping something we cannot describe. Explaining it is the next task; it is
worth real effort, because if the metric is undercounting here it may be
undercounting elsewhere in this corpus.

**Zamzara needs its own row-grammar port** (`$C8`/`$F6` bases, no `$FF` row-end)
— that is a separate, real piece of work, and it explains its 25.0/0.0.

## THE GRAMMAR IS PER-FILE (2026-07-16) — the real shape of the problem

> **There is no "Variant A grammar" and "Variant B grammar". Every rip carries
> its own class boundaries as immediates in its orderlist-fetch routine.**
> `decode_voice` hardcodes Ding_van_Charles's. Files that never exercise the
> differences score 100%; the rest are silently mangled.

Read off the real disassembly (`sidm2.deenen_parser.DeenenGrammar` reports it
per file; `bin/_deenen_vb.py` is the emulation probe):

| file | fetch | pattern | `$FF` | note-transpose |
|------|-------|---------|-------|----------------|
| Ding_van_Charles | `$12A6` | `< $5F` | **segment-advance** (cap 26, step 27) | `A-$82` |
| B_A_T / Lord_of_the_Rings | `$0EE6` / `$0F34` | `< $5F` | segment-advance | — |
| After_the_War | `$0E94` | **`< $6F`** | segment-advance | **`A-$84`** (`SBC #$80 / CLC / ADC #$FC`) |
| Constant_Runner | `$13F3` | **`< $40`** | **restart to index 0** | `A-$80` |
| Mantalos | `$0D95` | `< $40` | segment-advance | — |
| Zamzara | `$BE27` | `< $40` | restart | — |
| Soldier_of_Light | `$0CDC` | **`< $50`** | restart | uses `AND #$1F`, not `SBC` |

**Constant_Runner, decoded from the 6502 (`$13F3`):**
```
CMP #$fe / BEQ            ; stop
CMP #$ff / BNE            ; $FF -> LDA #$00 / STA $d7,X  = RESTART TO INDEX 0
CMP #$40 / BCC pattern    ; < $40  -> PATTERN index
CMP #$80 / BCC mid
SBC #$80                  ; >= $80 -> A-$80 -> $da,X   note transpose
mid: CMP #$60 / BCC low
SBC #$60                  ; $60-$7F -> A-$60 -> $dd,X  A-transpose
low: SEC / SBC #$40       ; $40-$5F -> A-$40 -> $e0,X  PATTERN LOOP COUNT
                          ;   ($145B does DEC $e0,X — that is what proves it)
```
So `8C 43 0B` is *transpose, loop-count 3, pattern $0B* — play `$0B` four times.
**`$43` was never a pattern.** Under Ding's `< $5F` threshold it became pattern
67, whose table entry (`$136D + $86 = $13F3`) is **the code itself**, giving the
out-of-file pointer `$D1B9`. Same for `$4E` → `$40C9`. That, plus `$FF` having no
model (`seg_cap`/`seg_step` are `None` for this class), is the whole 500-notes-
versus-44 runaway on v2. Emulation confirms the real player never fetches those
indices, and that v2 is genuinely silent for the first 400 frames.

**Status:** `DeenenGrammar` reads `fetch` / `pat_thr` / `ff_mode` and is
**tested** (`pyscript/test_deenen_grammar.py`) — but is **not yet consumed by
the decoder**. A first attempt to also parse the class chain by byte-scanning
for `CMP #imm / BCC` + `SBC #imm` produced garbage on Ding itself (`loop=$70-$5E`,
inverted — Ding branches with **BCS** where Constant_Runner uses **BCC**) and
would have altered all four currently-100% files. **Next step:** a real flow-walk
of the CMP/BCC/BCS chain, then wire it in and validate file-by-file. Do not wire
a byte-scan.

**After_the_War's `A-$84` is a live suspect:** it is the only clean win below 100
(pitch 98.1) and the only one whose note-transpose base differs from the
hardcoded `$82`.

## Open — each a separate sub-variant RE

* **(a) ZP-loop-counter orderlist variant** (Astro/Mr_Heli): `$88,X` nested loop
  counters, handler `c9 ff d0 .. b5 88 f0 04 d6 88` at `$0DD2` — **not** the linear
  seg-step.
* **(b) Constant_Runner v2 only** — engine otherwise decodes (v0/v1 exact); v2's
  `ord_ptr` starts at pattern `$4e`, out of range.
* **(c) Variant B "Smooth-class"** — needs its own groove clock (`$49`, advance ~1-of-3
  frames, per Smooth `$0A6D-$0A83`) **and** real reloc for the relocated/IRQ files
  (Eye_to_Eye load `$4000` play `$0000`; Zamzara `$bd70`). The "reloc 0" absolute
  assumption reads filler for several.
  > **Superseded in part:** "Variant B" is not one thing — see *The grammar is
  > per-file* above. Constant_Runner's failure was the grammar, not the reloc:
  > its ord table (`$195C`), its absolute pointers (`$1AD1/$1AEA/$1B07`) and its
  > reloc (0) were all **correct** already, verified by emulation.
* **(d) 9 files not located** — freq/instr `B9`-pair or dispatch not found (Satan reloc
  off-image; Smooth/Shitty freq pair missing). Needs flow-anchoring extended to the
  freq/instr scans, or Variant-B-specific signatures.
* **(e) minor:** the builder decode caps at 8000 rows (seq-dedup keeps SF2s 12–40 KB,
  so not urgent).
* Not wired into `driver_selector`/`conversion_pipeline`. No TDZ KB card yet.

**Next lever:** Variant-B groove+reloc (unlocks ~4), then the elaborate Variant-A
segment seed. Beyond this corpus: the **72-file MoN/Deenen group** in `SID/Tel_Jeroen/`
([MON.md](MON.md) line ~119) and the 15 MoN/FutureComposer dialect files.

## Tooling

| Tool | Purpose |
|------|---------|
| `sidm2/deenen_parser.py` | engine map + locate + decoder + groove clock |
| `bin/deenen_to_sf2.py` | Stage A builder (`--force` to override `plausible()`) |
| `bin/deenen_validate.py` | onset+pitch validator (corpus by default, or single file) |
| `bin/deenen_sm_build.py` | Sound Monitor freebie shim (relaxed play-sig gate) |
| `bin/_deenen_emu.py` | memory-bus-instrumented py65 (how groove was measured) |
| `bin/_deenen_groove.py` / `_deenen_common.py` / `_deenen_flowdis.py` / `_deenen_probe_deltas.py` | RE scratch (gitignored) |

## Commits

`7ad0b1b` engine map + relocation-safe locate + freebie/MoN wins → `36341bf` both
decoder blockers fixed (2 clean wins, 10/19 located) → `2905e9e` segment-seed +
per-file groove (B_A_T, LotR → 4 clean wins).

## See also

[MON.md](MON.md) · [SOUNDMONITOR.md](SOUNDMONITOR.md) · [HUBBARD.md](HUBBARD.md) ·
[PLAYBOOK.md](PLAYBOOK.md) · [PATTERNS.md](PATTERNS.md)
