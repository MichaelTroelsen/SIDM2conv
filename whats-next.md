<original_task>
Standing mission: any SID -> SF2 at 99% fidelity + 100% editable.

Session 2026-07-17. Entry: **"read what next and continue"** — no pre-set
task; I read the prior handoff and picked up its own recommended next step:
**Zamzara's unexplained pitch 25%** (a "third, separate issue" left open by
the prior session's commits 86a0efb/924322d). Driven forward by repeated
bare "continue"/"cont" prompts.

Mid-session, at a genuine fork, the user was asked (AskUserQuestion) and
chose: **"Implement the arp/slide engine"** — over (a) relaxing a stale
plausible() guard to score a quick win, (b) moving to mon_parser LOCATE, or
(c) chasing Mantalos/Mr_Heli. I.e. **accuracy over speed: make
Constant_Runner a GENUINE win rather than a metric-passing one.** That is the
live task and it is PARTIALLY DONE (see work_remaining #1).

STANDING RULES (all still live): accuracy over speed; never ship lossy
silently; **verify by EMULATION before rewriting a parser**; a fidelity claim
must never outrun its evidence; NEVER run pyscript/sf2_open_in_editor.py
unless asked; corpus-gate every decoder change; **read your own tool's output
before trusting it**; verify a falsifier as rigorously as the claim it
attacks.
</original_task>

<work_completed>
Repo: master. **7 new commits** on top of 924322d. Version UNCHANGED at
**3.21.0** (bug-fix/RE work, not a release milestone — correct not to bump).
Tests **1561 passed / 7 skipped / 2 xfailed**, run and confirmed after EVERY
code commit (5 full runs, ~3 min each). Zero regressions throughout.

  0e1c823  Zamzara's decode is now byte-exact (engine-check 100/100/100)
  32a5afd  Zamzara's freq tables were byte-swapped -> 100/100, 6th clean win
  623f4e3  verify EVERY located file's freq table order, not just Zamzara's
  7e6a594  the "voice1 arpeggio" is PERCUSSION - RE'd, located, decoded
  a441055  emit the percussion/wave streams as real Driver 11 wave rows
  c901ec4  whats-next: session handoff (superseded by THIS file)
  35fefac  audio-validate the emitted percussion (CR passes; AtW does NOT)

**Deenen corpus: 10/19 located, 5 -> 6 CLEAN WINS.** Zamzara is the new one.
The 6: Ding, B_A_T, LotR, After_the_War, **Zamzara** (all exactly 100/100) +
Astro (77.4/91.5). Constant_Runner still refused by plausible() (100/97.7).

=== PART A: ZAMZARA — SIX BUGS, 18.8% -> BYTE-EXACT -> 6th CLEAN WIN ===
All in `sidm2/deenen_parser.py`. Each verified via
`bin/deenen_engine_check.py` (ground truth = the player's OWN computed note,
watched live under py65) before moving to the next layer.

1. **Orderlist high-byte grammar was the WRONG DIALECT** (commit 0e1c823).
   Zamzara shares Constant_Runner's shallow `gram.pat_thr==$40 /
   gram.ff_mode=='restart'` signature, so `decode_voice` routed it through
   the Jeroen-Tel 3-tier grammar. Disassembly ($BE3C-$BE56) shows Zamzara has
   only **TWO tiers, no $60 branch at all**:
     - `$80+` (the FALL-THROUGH, no branch taken) = `AND #$1F` -> `$e2,x`
       note-transpose (unsigned)
     - `$40-$7F` (the `BCC lbe50` target) = `AND #$3F` -> `$fb,x` repeat count
   A FIRST ATTEMPT GOT THE BRANCH DIRECTION BACKWARDS (assumed BCC took the
   $40 tier to transpose). Caught by a live register trace ($e2,x=12 from
   orderlist byte $8C; $fb,x=3 from byte $43) BEFORE shipping.
   Routed via a new `zclass` local -> `if zclass / elif tel / else` chain in
   `decode_voice`; `_is_zamzara_row_class()` now gates BOTH the row parser
   AND the orderlist grammar. `$FF` handling extended to `if tel or zclass`
   (Zamzara's $BE32 restart-to-0 has the same shape as tel's $13FA).

2/3. **`_parse_row_zamzara`'s duration path had two errors** (0e1c823), found
   by disassembling the FULL flow ($BDE0-$C080) after the orderlist fix alone
   made things WORSE — a signal the row port had a latent bug its original
   single hand-verified row (`FE F4 C3 A0 A0 76 1A`) never exercised (it
   never hit a duration+$FD combination):
   (a) A `$FD` interrupting duration accumulation needs the **SAME full
       3-byte consumption** as a top-level `$FD` (the port had a 1-byte
       shortcut).
   (b) Duration accumulation is **NOT an unbounded loop**: hardware allows at
       most ONE inline accumulate step ($BEFC-$BF1C); a THIRD consecutive
       $80+ byte re-enters the full $BE91 dispatch (JMP, not a tight loop) —
       NOT modelled past that depth (unverified/unexercised in the corpus).

4. **An unmodelled post-note "peek tail"** ($BF9B-$BFA9) (0e1c823). EVERY
   note-forming path falls through it: an **unconditional `INC $e9,X`** (at
   $BFA2) landing at `e9x_pos+1`, THEN a peek of that byte for `$FF`.
     - peek != $FF -> byte discarded, `$e9,x` STAYS at `e9x_pos+1` (`BNE
       lbfba` skips $BFAC); re-examined fresh next row.
     - peek == $FF -> hardware falls into $BFAC and **resets `$e9,x` to 0
       THAT SAME FRAME**. Modelled by returning a `None` next-pi sentinel;
       `decode_voice`'s row loop treats `npi is None` as "append the event,
       stop re-entering row_parser for this playthrough".
   **RESTS bypass this tail entirely** (`STA $f2,x` / `JMP $bfba`, never
   reaching $BF3B) -> they still return a plain `y+1`.
   **The SLIDE path is the one asymmetry**: its own `DEY`-then-refetch dance
   (read pos+3 into scratch/target, DEY, re-read pos+2 as the note) leaves
   real `$e9,x` at pos+3 — ONE BYTE AHEAD of the note's read position —
   before the tail's INC even runs. So slide-terminated notes call
   `note_return(y+1, b)`; every other path (bare note, arp, instrument->
   duration->note) is in lockstep and calls `note_return(y, b)`.
   Modelled as a `note_return(e9x_pos, b)` closure inside
   `_parse_row_zamzara`.

5. **`groove_rate()` tie-broke toward a harmonic ALIAS** (0e1c823). R=2.0 and
   R=3.0 BOTH scored 10 hits, but 2.0 emitted **21 candidate onsets** to
   3.0's **10** (10/10 = the honest fit). The loop's `if tot > best[0]` kept
   the FIRST candidate on a tie (2.0 sorts before 3.0). Fixed: tie-break
   toward FEWER candidates via a `(tot, -ncand)` comparison, `best` widened
   to `(tot, ncand, R)`. **GENERIC subsystem** — every Deenen file's tempo
   model shares it — so corpus-verified: **zero change to all clean wins**
   (After_the_War/B_A_T/Ding/LotR still exactly 100/100; Astro still exactly
   77.4/91.5); only Zamzara (25.0->71.8) and non-win Mr_Heli moved.

6. **THE REAL PITCH KILLER: THE FREQ TABLES WERE BYTE-SWAPPED** (32a5afd).
   `DeenenLocate` pairs the two split freq tables **by ADDRESS ORDER** (lower
   of the pair = FREQ_LO, since `hi-lo == $5F` holds on the Ding class).
   **Zamzara lays them out reversed**: `$C3EE` is its **HI** table, `$C44D`
   its **LO**. So every frequency the decoder computed was byte-swapped —
   note 60 -> `$8623`=34339 instead of the real `$2386`=9094.
   Proven THREE independent, agreeing ways:
     (i) the SID write itself: `$C3CE: LDA $c6,x / STA $d400,y` (freq LO) and
         `$C3D3: LDA $ef,x / STA $d401,y` (freq HI), while note-formation
         `$BF47` loads `$c44d,y`->`$c6,x` and `$BF4E` loads `$c3ee,y`->`$ef,x`;
    (ii) the slide engine's 16-bit arithmetic at `$C1F0` (`LDA $cf,x / SEC /
         SBC` FIRST, then `LDA $c9,x / SBC` with the borrow -> `$cf,x` is
         unambiguously the low byte, and `$cf,x` comes from `$c44d`);
   (iii) real siddump output: the frequency at a known onset (frame 578) is
         exactly 9094 = the SWAPPED lookup.
   **Fix**: `DeenenModule._fix_freq_table_order()` — decides from the SID
   write, not the address order. Acts ONLY on positive evidence of a swap,
   ABSTAINS otherwise.
   **Result**: Zamzara onset 100.0 / pitch 100.0 = the **6th clean win**.
   Non-vacuous, independently checked: **all 103 real onsets frame-aligned,
   0 pitch mismatches (was 44)**. Every other file byte-identical.

   Then **623f4e3 generalized the detector to a SECOND shadow shape**. The
   first version only knew `LDA zp,X / STA $D40x,Y` (Zamzara), so it
   ABSTAINED on 5 of the 6 wins — their table order was still only ASSUMED
   correct by the convention just proven wrong. The Ding class uses ABSOLUTE
   X-indexed shadows: `$193A: LDA $1086,x / CLC / STA $d400,y` and `$1941:
   LDA $1089,x / ADC #$00 / STA $d401,y`, fed by `$1429: LDA $10f3,y / STA
   $1086,x` and `$142F: LDA $1152,y / STA $1089,x` (lo->lo, hi->hi = Ding is
   correct, now CHECKED not believed). Detector now scans back from the store
   for the nearest indexed LDA allowing ONLY a carry/immediate-add gap
   (`CLC|SEC|ADC #|SBC #`), and tags shadows `('zp'|'abs', addr)` so a zp $86
   can't collide with an abs $1086.
   **Result: ALL 10 located files come back positively VERIFIED, zero
   abstentions**, Zamzara the only one rewritten. Freq order is now confirmed
   from code everywhere in this corpus, not assumed.

7. **`plausible()`'s $40-class blanket refusal was stale for Zamzara**
   (0e1c823). Added `and not self._is_zamzara_row_class()` — Zamzara's rows
   ARE ported and proven exact; Constant_Runner (no row-class signature)
   stays correctly refused.

=== PART B: THE "ARPEGGIO" IS PERCUSSION (the user's chosen task) ===
**RETRACTS this project's 2-session-old "Constant_Runner voice1 has an
unmodelled ARPEGGIO effect" diagnosis** (7e6a594).

The `$1723` wave engine has TWO stream modes selected by the stream HEADER's
bit7. The old note read the **bit7-CLEAR** branch (a relative semitone added
to the base note, `CLC / ADC $f2,x / AND #$7F`) and **assumed that was the
path being taken**. It is not: instr 1/2/6 all carry a **header with bit7
SET**, taking `$1765: BIT $d0 / BMI -> STA $75,x / STA $fb,x` — the stream
byte is written to **BOTH freq hi and freq lo**, i.e. **raw freq = `b<<8|b`,
COMPLETELY INDEPENDENT of the played note**. A fixed descending click.
**It's a DRUM.**

**Proof (exact)**: instr 1's stream `3C 09 05 04 03 02 38` decodes to
semitones **[69, 37, 26, 23, 18, 11, 68]** — *byte-for-byte the very sweep
the old notes recorded as the unexplained mystery* ("69->37->26->23->18->11
->68"). The old note quotes the right numbers while drawing the wrong
conclusion. **Confirmed LIVE** (watching `$fb,x`/`$75,x` on voice1 across
real frames): 15420(69) 2313(37) 1285(26) 1028(23) 771(18) 514(11)
14392(68), then hold. instr 2 likewise ([71,44,...] matches frames 38-39).
**Also observed live: the base note plays for exactly ONE frame before the
drum overrides** (frame 1 = 568/semi 12) — which is why the ONSET pitch
metric mostly agrees already (CR pitch 97.7).

SHIPPED (7e6a594) in `sidm2/deenen_parser.py`:
- `_locate_wave_engine()` — relocation-safe; called from `__init__` ->
  `self.wave_eng`. Everything from operands: both zp shadows (mapped back to
  instrument-record offsets via their `LDA instr+k,Y / STA zp` load sites —
  CR: **instr[4] bit3 = enable**, **instr[7] high nibble - 1 = arp-table
  index**), the arp table, the two wave-pointer tables, and `bias`, which
  **VARIES per file**: $0a CR / $19 After_the_War / $11 Astro / $1e Mantalos
  / $14 Mr_Heli.
  **Signature gotcha**: the bare `4A 4A 4A 4A A8 88 B9` idiom gives **3 hits
  per file** (high-nibble-extract + table-index is common here). Anchor the
  WHOLE dispatcher including the `18 69 imm A8` tail -> **exactly 1 hit** on
  rips that have it (After_the_War, Astro, Constant_Runner, Eye_to_Eye,
  Mantalos, Mr_Heli), **0** on those that don't (B_A_T, Ding, LotR).
  **Zamzara has a wave/arp engine too but a DIFFERENT one** — driven from its
  row grammar's `$C4F0`/`$C502` tables ($BF23). Per-file, as ever.
- `wave_program(i)` — full byte grammar: header (bit7 = raw mode, `(>>4)&7` =
  frames-per-step-1, `&$0F` = loop target), `$FF` -> loop to
  `(header&$0F)+1`, `$FE` -> **hold forever** (the sustain/terminator: `DEC
  $b4,x` then exit, so it re-reads $FE every frame and never advances),
  raw vs absolute(`>=$7F`) vs relative steps.
  CR: **1/2/6 = percussion**; **instr 0 is the ONLY note-mode one** (absolute
  `$81` then relative +5,+4,+3,+2,+1,+0 = a descending slide into pitch) — so
  the relative path IS real, just not what 1/2/6 use.

SHIPPED (a441055) in `bin/deenen_to_sf2.py`:
- `_wave_program(m, di, wf, base_row)` emits the streams as real Driver 11
  wave rows, replacing the old 2-row held-waveform stub in
  `build_instruments`. Follows **`bin/fc_to_sf2.py`'s drum path** (the
  closest precedent — same problem, already solved for Future Composer) plus
  `bin/kimmel_to_sf2.py`'s `_wave_program`.
  **Encoding confirmed from TWO shipping builders, not just the spec doc**:
  col1 `$80-$DF` = absolute semitone (`fc_to_sf2._drum_note`,
  `kimmel_to_sf2:61`), col1 `$01-$7D` = relative semitone, col0 `$7F` = jump.
  (`docs/reference/SF2_FORMAT_SPEC.md` documents `$80+` as "Absolute note
  (great for drums)".)
  **Independent corroboration**: fc_to_sf2's drum comment says FC "plays the
  note's OWN pitch on the trigger frame, then the drum table from frame 1",
  so it leads with one root row — EXACTLY what the live CR trace shows. Two
  unrelated engines, same shape; the root row is grounded, not guessed.
  Verified emission (CR): instr 1 -> root, ABS 69/37/26/23/18/11/68,
  self-jump (hold). instr 2 -> ABS 71/44/42/70/69/38/71. instr 6 -> 23 steps,
  jump back to row 39 = its step 5 (header loop=5). instr 0 -> the relative
  slide. `speed` honoured by repeating rows; jump targets prog-relative then
  offset by the instrument's `wave_row` at extend time.
  **KNOWN LOSSY STEP (deliberate, documented in the docstring, not silent)**:
  raw `b<<8|b` is not exactly a semitone, so an absolute-note row plays the
  NEAREST one — the sweep is QUANTIZED. Inaudible on a click, but it IS an
  approximation and the only lossy step here.

=== PART C: AUDIO VALIDATION (35fefac) — NEW TOOL, MIXED RESULT ===
`bin/deenen_sf2_validate.py` (NEW, ~130 lines). Why it exists:
`bin/deenen_validate.py` scores the **DECODER** (onset+pitch) and is
**structurally BLIND** to what `deenen_to_sf2` emits — so a441055's wave rows
shipped decoded+emitted but never audio-checked.
Method (copies `bin/mon_sf2_validate.py`'s probe path): build the SF2 exactly
as the builder's `main()` does -> `parse_sf2_blocks` -> `psid_wrap(sf2[2:],
sla, 0x1000, 0x1006)` -> siddump the probe -> check real SID output.
**Compares PER-FRAME FREQUENCY, not onsets** — the percussion is a
within-note sweep, so an onset-only compare (what mon_sf2_validate does)
cannot see it at all and would report success while testing nothing.

RESULTS:
- **Constant_Runner PASS** — instr 1 [69,37,26,23,18,11,68], instr 2
  [71,44,42,70,69,38,71], instr 6 (23 steps): every pitch present in real
  output. The wave rows genuinely fire.
- **After_the_War FAIL** — instr 15 never emits **[57, 73]**; instr 24 never
  emits **[38]**. This is the **exact file flagged as the regression risk**
  (an existing 100/100 clean win that HAS this engine, whose SF2 changed
  under a metric that cannot see it). The risk was real; the tool caught it.

Diagnostics run on the failure (all read-only, no fix applied):
- The rows **ARE** correctly emitted: 73, 57, 38 all present in
  After_the_War's wave table. **The emission is not dropping them.**
- **NOT a window artifact**: still missing at a 90s window (tested).
- instr 15: header `$86` -> speed 1, loop 6; raw bytes
  [80,14,72,80,72,80,32,36,40,44,40,36,32,30] -> semis
  [74,44,73,74,73,74,59,61,62,64,62,61,59,57].
- **Pattern noticed (suggestive, NOT confirmed)**: instr 15's `73` and instr
  24's `38` BOTH sit at **step index 2**, while steps 0-1 (74,44 / 66,44) ARE
  heard. instr 15's `57` is its FINAL step.

=== PART D: DOCS ===
`docs/players/DEENEN.md` fidelity table refreshed (was **stale at 4 wins** —
never updated when Astro became the 5th) -> now 6 wins with per-file notes;
added the freq-table-order ⚠️ warning **at the engine-map source** (the exact
line that encoded the wrong "hi - lo = $5F" assumption) and the
engine-check-certifies-only-what-it-watches box; corrected the stale
"Zamzara all-$00" claim in the plausible() blurb.
`docs/reference/ACCURACY_MATRIX.md` + `CLAUDE.md` Known-Limitations rows
updated 4 -> 6 clean wins.
Memory `memory/deenen-player.md` heavily updated: two ⚠️ RETRACTION boxes
(portamento; arpeggio->percussion), the corrected **PERCUSSION ENGINE** map
(exact addresses/flags/tables), the freq-swap section, and the emission's
validation gap. `memory/MEMORY.md` index line rewritten.
</work_completed>

<work_remaining>
## THE LIVE THREAD — in priority order

1. ⚠️ **FIX `bin/deenen_sf2_validate.py`'s POOLING FLAW FIRST.** Discovered at
   the very end and **it weakens every PASS the tool has reported**:
   `heard` is a SINGLE GLOBAL SET of every semitone across ALL 3 voices over
   the whole window. So a pitch produced by a completely unrelated note or
   instrument counts as "heard".
     - **FAIL is a strong signal** (the pitch appears NOWHERE).
     - **PASS is only NECESSARY, NOT SUFFICIENT.** Constant_Runner's PASS is
       real evidence the wave rows fire, but it does NOT prove *those
       instruments* produced *those pitches at those times*. **I over-stated
       it by calling the gap "closed" — it is not.**
   FIX: attribute per-voice and per-time-window against the decoder's own
   note schedule (`m.voice_onsets(v)` + the instrument of each event from
   `decode_voice`), i.e. "during the frames when voice V is playing a note
   with instrument I, do I's drum pitches appear ON VOICE V?". Real work, not
   a tweak. Until then, quote the tool's FAILs, not its PASSes.

2. **Resolve the After_the_War FAIL** (instr 15 missing [57,73]; instr 24
   missing [38]). **UNRESOLVED — DO NOT GUESS A FIX.** Ruled out already:
   the rows are emitted (present in the wave table); it is not a window
   artifact (90s tested).
   Live hypotheses, in order of plausibility:
   (a) **Note-length truncation = CORRECT behaviour.** Both missing pitches
       sit at step index 2; steps 0-1 are heard. If those notes are only
       ~2 frames long, the stream never reaches step 2 — nothing is wrong,
       and the later steps I DID see (59,61,62,64) may have come from other
       notes entirely (exactly the pooling flaw in #1). **Fixing #1 likely
       resolves #2 by itself — do #1 first.**
   (b) **An absolute-note numbering OFFSET.** `fc_to_sf2._drum_note` returns
       `max(0, min(idx + base + 1, 95))` — there is a **`+1` and a `base`**
       that `_wave_program` does NOT apply. BUT a uniform shift does not fit
       the evidence (74 is heard while the adjacent 73 is not), so do not
       apply it speculatively. Check it against the driver first.
   (c) Quantization collision (two raw bytes rounding to one semitone).

3. **Zamzara's `$FD` portamento** — the OTHER half of the user's chosen task,
   **NOT STARTED**. Engine at `$C166-$C220`: `$c3`=speed, `$c4c3`=target
   (`ADC $e2,x`-transposed), `$d5,x`=enable flag, a self-modified SEC/SBC vs
   CLC/ADC direction patch at `$C1B2-$C1BB`, a 16-bit divide at `$C1C8-$C1EF`,
   and a snap-to-target path at `$C206`. Real freq observed gliding
   9094->7624 over 24 frames. NOT metric-visible (onset-only). Driver 11 has
   a **T0 slide command (XXYY = 16-bit speed)** and **Kimmel already ports
   freq-slide via T0** (`bin/kimmel_to_sf2.py`, see [[kimmel-player]]) — that
   is the template.

4. **Constant_Runner's `plausible()` guard** — still refusing, deliberately.
   Its stated premise is **already provably stale on BOTH counts**: rows
   proven identical to Ding's in **d83e7f0** ("the Tel pattern ROWS need no
   porting - they are already identical"), and the **35.6%** it cites was the
   attack-transient metric bug fixed in **2dccee7** (now **97.7**). Once #1/#2
   are settled, relax it **BECAUSE the effect is genuinely modelled and
   verified** — never because relaxing it scores a win. Would make CR the
   **7th clean win** (onset 100.0 / pitch 97.7).

## OPEN, NOT TOUCHED THIS SESSION
5. **Mantalos** — 0%/0%/0% vs the player's own notes. Confirmed to take the
   Ding path (`_is_zamzara_row_class()` False, `gram.ff_mode=='seg'`), so
   none of this session's fixes touch it. Its 924322d orderlist fix stands;
   the remaining brokenness is separate and undiagnosed.
6. **mon_parser LOCATE extension** — the prior handoff calls this a **BIGGER
   prize** than the Deenen decoder work: 12 `$40`-class Tel rips already
   decode but fail file detection (`mon_validate` 0/0 = vacuous no-evidence,
   not a decode failure). Also unlocks MoN **native Stage B** (100%
   byte-exact on Hawkeye) instead of a Stage A transpile.
7. Astro/Mr_Heli's ZP `$88,X` nested-loop orderlist variant. The 9
   not-located files. `Zamzara_v1` (`no dispatch` — more basic).
   **Smooth_Criminal** (matches `_is_zamzara_row_class`, `loc='sig'` = not
   fully located; will auto-route to the Zamzara row parser once located —
   check it for the self-modifying-code orderlist pattern too).
8. Long-standing: the DEGENERATE-value bug (`score_pct` can't catch
   tot=1000/ONE distinct value, e.g. Hubbard's "filter 100%");
   `pyscript/trace_comparator.py:291,341` reachable vacuous-100;
   `bin/hubbard_validate.py` V1-only silently wrong on V2; SM's 99.23% not
   reproducible from a fresh clone (untracked sweep script);
   Galway/MoN/ROMUZAK/FC matrix rows never audited by the falsifier.
</work_remaining>

<attempted_approaches>
**A frame-pitch fidelity probe — INVALID, discarded, DO NOT REDO.** To settle
whether Zamzara-vs-CR were judged consistently, I wrote a per-frame
(sustain-inclusive) pitch metric. It read **Ding voice0 at 5.3%** — while
Ding is a verified 100/100 clean win. That is not Ding being broken: these
engines have per-frame vibrato/porta that Stage A never models, so the probe
measured "does the engine modulate pitch" (yes) rather than "is the decode
right". **The project's onset-only metric is chosen deliberately for exactly
this reason.** I discarded the numbers rather than report them.

**Misdiagnosing the freq byte-swap as "an unmodelled portamento" — WRONG,
retracted in 32a5afd's message.** I observed a real glide (9094->9024->...->
7624) and reasoned to the wrong cause. The glide is real but happens AFTER
the onset; the metric samples at onset+0..2 where the frequency is exactly
the note's table value. **Reasoning from a real observation to a plausible
wrong cause cost roughly a session.**

**Misreading the wave engine as an arpeggio for TWO sessions.** The
relative-semitone branch IS real code and I found it — but instr 1/2/6 never
take it; the header's bit7 selects the raw/percussion path instead. **Read
the SELECTOR, not the first branch you find.**

**Hand-tracing 6502 control flow instead of probing it — 3 wrong attempts.**
On Zamzara's peek-tail I guessed a universal `+1`, then a universal `+2`;
each BROKE voices that were already at 100%. Only a live per-voice register
trace ($e9,x at every $BE7D dispatch, across ALL THREE voices — not just
voice0) revealed the real asymmetry. Also got the BCC branch direction
backwards once on the orderlist grammar (caught by a register trace before
shipping). **The "verify by emulation before rewriting a parser" rule earned
its keep three times.**

**The audio validator's first run FAILED for a wrong reason.** It scanned all
32 instrument records, but only USED instruments get wave rows emitted — so
it "failed" on records not in the SF2 at all (CR's record 21 decodes to 64
unterminated steps incl. a semitone of **-1** = silence: garbage, not a
defect). Fixed to iterate `B.used_instruments(m)`. **Verify the falsifier
before believing it.**

**The validator's pooling flaw (found last, unfixed)** — see work_remaining
#1. It makes PASS necessary-but-not-sufficient. I stated the gap was "closed"
before noticing this; it is not.

**NOT pursued deliberately**: relaxing CR's plausible() guard to score a
quick 7th win (the user was asked and chose the harder, honest path);
applying fc_to_sf2's `+1`/`base` offset speculatively (doesn't fit the
evidence).

**Environment**: `/tmp` on this Windows/Git-Bash setup still resolves
unpredictably (and a stray `dis.py` there shadows the stdlib `dis`). Use the
session scratchpad. Also: `sleep N && cmd` chaining is blocked by the
harness — use `run_in_background` + the completion notification.
</attempted_approaches>

<critical_context>
## THE LESSON OF THIS SESSION
**A ground-truth tool certifies ONLY the quantity it actually watches.**
`bin/deenen_engine_check.py` reported "the decoder reproduces the player
EXACTLY" (100/100/100) on Zamzara **while every frequency it emitted was
byte-swapped** — because it watches note INDICES and the corruption was
downstream in index->frequency. Its own docstring even says "validates NOTES,
not timing/timbre/effects", and a byte swap is precisely a not-notes defect.
I over-read its verdict as "the decode is right".
**COROLLARY: note-exact decode + a pitch metric that still disagrees =>
suspect index->frequency BEFORE inventing an unmodelled effect.** I invented
one (portamento) and was wrong.
The SAME shape recurred at the end: my own new audio validator's PASS is
weaker than it looks (pooling flaw, work_remaining #1). **Ask what a green
result actually proves.**

## THE SAME BUG CLASS, A NEW SHAPE EVERY TIME
A locate/metric silently substitutes a PLAUSIBLE-LOOKING WRONG VALUE. Shapes
added this session: freq tables paired by ADDRESS ORDER (right for Ding,
backwards for Zamzara); `groove_rate` tie-breaking to a harmonic ALIAS that
scores equal on hits but emits 2x the candidates; a `plausible()` guard whose
justification went stale UNDER it (both cited facts became false without the
guard changing); and a validator that pools evidence across voices so an
unrelated source satisfies a check.

## PER-FILE, ALWAYS — NOW SIX INDEPENDENT LAYERS
Deenen varies per file at: (1) orderlist grammar, (2) row grammar, (3)
orderlist-pointer resolution (direct vs self-modifying code), (4) **freq-table
byte order**, (5) **wave/percussion engine — present/absent AND which shape**
(Zamzara's is a different engine entirely), (6) groove rate.
**Assume NOTHING carries across files without re-verifying.**

## KEY FILES
- `sidm2/deenen_parser.py` — `_fix_selfmod_ord_ptr`, **`_fix_freq_table_order`
  (NEW)**, **`_locate_wave_engine` + `wave_program` (NEW)**,
  `_parse_row_zamzara` (+ its `note_return` closure), `_is_zamzara_row_class`,
  `decode_voice` (zclass/tel/Ding routing + the `npi is None` sentinel),
  `groove_rate` (tie-break), `plausible` (the $40-class guard).
- `bin/deenen_to_sf2.py` — **`_wave_program()` (NEW)** emits the wave rows;
  `build_instruments`, `voice_rows`, `main()` (the SF2 assembly path).
- `bin/deenen_sf2_validate.py` — **NEW**; the audio check. Has the pooling
  flaw (work_remaining #1).
- `bin/deenen_engine_check.py` — ground truth for **NOTES ONLY** (see lesson).
- `bin/deenen_validate.py` — scores the **DECODER**, not the SF2.
  `PITCH_SETTLE_WINDOW=2`. **Cannot see a441055 at all.**
- `bin/mon_sf2_validate.py` — the SF2->PSID probe path template.
- `bin/fc_to_sf2.py` — the drum -> absolute-note-wave-row TEMPLATE
  (`_drum_note`, the `+ base + 1` offset lead).
- `bin/kimmel_to_sf2.py` — `_wave_program` (arp) + **T0 freq-slide** template.
- `docs/reference/SF2_FORMAT_SPEC.md` — wave table: col0 waveform/`$7F`=jump;
  col1 `$00` none / `$01-$7D` relative semitone / **`$80+` absolute note
  ("great for drums")** / (with `$7F`) jump target row.
- Memory: **`memory/deenen-player.md` — READ FIRST.** Carries the two
  retraction boxes, the corrected PERCUSSION ENGINE map (exact
  addresses/flags/tables), the freq-swap section, and the validation gap.

## ENVIRONMENT
- Tests: `py -3 -m pytest pyscript/ -q` -> **1561 passed / 7 skipped /
  2 xfailed** (~3 min). Confirmed after every commit this session.
- Corpus: `py -3 bin/deenen_validate.py` (~2-3 min) -> 10/19, **6 clean wins**.
- Ground truth: `py -3 bin/deenen_engine_check.py [names]` (NOTES only).
- Audio: `py -3 bin/deenen_sf2_validate.py [path] [secs]` (CR passes; AtW
  fails; PASS is weak — see #1).
- py65 `MPU` + a minimal `Mem` wrapper (overriding `__getitem__`/
  `__setitem__`, tracking `mem.pc`) is the standard probe pattern.
- Disassembly: `pyscript/disasm6502.Disassembler6502(memory, start_addr,
  size)` then `.disassemble_range(lo, hi)` + `.format_output()`.
- `core.autocrlf=true` — the CRLF warnings on md files are cosmetic; diffs
  are clean. (Gotcha: reading with universal-newlines then writing with
  `newline=''` converts CRLF->LF on disk; git normalizes it away.)
- **Nothing pushed to origin** (local only, as prior sessions).
</critical_context>

<current_state>
- **v3.21.0 unchanged** in `sidm2/__init__.py` (correct — bug-fix/RE work, no
  release milestone).
- **7 commits on master this session, NONE pushed.** Working tree clean
  except: the same pre-existing untracked corpora/scratch
  (`SID/Gallefoss_Glenn/`, `SID/Jeff/`, `SID/Red_kommel_jeroen/`,
  `SID_INVENTORY.md`, `archive/cleanup_2026-07-09/`, `bin/LFT/`,
  `bin/SIDDuzz/`, `bin/_kimmel_work/`) plus a local-only
  **`.claude/settings.local.json`** diff (permission allowlist, NOT part of
  this work — deliberately left uncommitted, as in prior sessions).
- **Tests: 1561 / 7 skipped / 2 xfailed.** No known failures.
- **Deenen: 10/19 located, 6 clean wins** (was 5 at session start; docs were
  stale at 4). Zamzara is new at exactly 100.0/100.0 — verified non-vacuous
  (103/103 onsets aligned, 0 pitch mismatches).
- **Freq table order: VERIFIED FROM CODE on all 10 located files** (zero
  abstentions). No longer an assumption anywhere in this corpus.
- **Percussion**: decoded ✅, emitted ✅, **partially validated ⚠️** —
  Constant_Runner passes the audio check but via a validator whose PASS is
  necessary-not-sufficient; After_the_War FAILS with a real, unexplained
  discrepancy. **Do not claim the percussion is "reproduced".**
- **Constant_Runner**: still `plaus=-` (refused). Decode engine-exact
  (100/100/100 notes), onset 100.0 / pitch 97.7. The guard's premise is stale
  but lifting it is gated on #1/#2.
- **Docs**: DEENEN.md / ACCURACY_MATRIX.md / CLAUDE.md all say 6 clean wins
  and carry the freq-table-order trap + the certifies-only-what-it-watches
  lesson. Memory updated with retractions + the corrected engine map.
- **OPEN QUESTIONS**: (a) does fixing the validator's pooling flaw make
  After_the_War pass (i.e. was it note-truncation all along)? (b) does
  Driver 11's absolute-note numbering carry fc_to_sf2's `+ base + 1` offset?
  (c) Zamzara's portamento — untouched.
- **NEXT SESSION SHOULD START WITH**: `memory/deenen-player.md` (retraction
  boxes + PERCUSSION ENGINE map), then **work_remaining #1** (fix the
  validator's pooling flaw) — it is both the weakest link in the current
  evidence AND the most likely resolution of #2.
</current_state>
