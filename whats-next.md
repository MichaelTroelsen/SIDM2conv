# Handoff — SIDM2 session, 2026-08-14

<original_task>
**"read what next"**, then **"do the task on the list"** twice, then **"turn it
on by default and rebuild the corpus"**. The list held one item — **#16 HardTrack
brightness gap** — whose named decisive experiment was *build the HRC per-note
lookahead and A/B the audio*. That ran, re-pointed the question, and the second
pass answered the re-pointed one.
</original_task>

<work_completed>

**Two commits' worth of work: the experiment, then the RE that made it correct
enough to ship.** `SR_PREKILL` in `drivers_src/mon/romuzak_driver.asm` is now ON
for HardTrack by default and the corpus is rebuilt behind it.

## The RE finding: instrument mode 2 is the hard restart

Field 5's `$03` mask was named `mode` and never explained. Both of the player's
`LDA #$00 / STA $D406,y` sites are guarded by the **previous** frame's mode:

```
$11ca  lda F5,y / and #$03 / pha      ; this instrument's mode
$11d0  lda mode,x / sta prevmode,x    ; shift: prev <- cur, once per frame
$11d7  pla / sta mode,x
$11da  lda prevmode,x / cmp #$02
$11df  beq $11e9                      ; -> lda #$00 / sta $D406,y + gate off
$11e1  lda #$fe / sta gmask,x         ; else a PLAIN gate-off

$12da  lda legato,x / bne skip        ; the note-FETCH path: the same kill,
$12e2  lda prevmode,x / bne $12ea     ;   on a non-legato fetch
```

Three consequences, each of which had to be right:

- **It belongs to the note that is ENDING.** Keyed on the starting note the rule
  scores 4 of 6 ADSR keys on `Teekkno`; keyed on the ending note, **242 of 242**.
- **The corpus carries only modes 0 and 2** (134 and 792 instruments over 38
  files), so the fetch site's `bne` is the note-end site's `cmp #$02`.
- **It is not `skip_filter_rearm`.** Bit 4 suppresses a filter re-arm and nothing
  else — that reading stands. The real hard restart was in the two bits beside it.

Prediction vs the players' own output: `Teekkno` 242/242, `Love_tune_2` 158/158,
`Muminki_Rooooolz` 375/375, `Walk_to_Soul` 331/340, `Muza_Do_Dema` 139/145 —
**zero false positives in 1,260 note-ons**, residual one-directional.

## What shipped

`Instrument.ends_with_hard_restart` → the shim's `sr_restart` → instrument col2
bit `$04` → `sr_pre` tests `VIFLAGS,x`, which still holds the ENDING note's
instrument because the next fetch has not run `set_instr` yet. The emitter masks
`$04` out unless `SR_PREKILL` is set, so a build without the feature is
byte-identical whatever a shim asks for.

| | off → on |
|---|---|
| SR mismatching frames, **33 files** | **12,397 → 1,794**, worse on **0** |
| `Teekkno` (the discriminator), gated vs not | 42 → **26**, against 42 → **468** ungated |
| mean \|centroid error\|, 9 tunes | 67.4 → **51.4 Hz** |
| mean \|rolloff error\| | 184.7 → **132.6 Hz** |
| `Love_tune_2` centroid | −56.6 → **−102.7 Hz** ⚠️ |

**It is a correctness fix, not a brightness one.** `Love_tune_2` reads darker;
what it buys there is the release-tail level error, +1.26 → −0.42 dB on the
frames where the original sits at −35..−28 dBFS.

Corpus rebuilt: **33/33, 313 parts**, `passband_check --player hardtrack` still
**25/33** with the same 8 UNCONFIRMED multi-part files. The Stage B sweep is
byte-identical off vs on (raw 91.04%, audible 88.25%) — the fix does not touch
frequency, so that is a safety check and not a win.

## New tracked tools + tests

- `pyscript/hardtrack_sr_prekill_ab.py` — the A/B. `--all` sweeps the corpus over
  each file's own reported part-1 span; `--no-audio` drops the renders.
- `pyscript/hardtrack_native_rebuild.py` — clears `out/hardtrack_native/` and
  rebuilds every file at the shipping window. *A fix in the builder is not a fix
  in the corpus* (`PATTERNS.md` F7) is why this is a script, not a sentence.
- `pyscript/test_hardtrack_sr_prekill.py` — 8 tests. Suite **2,444**.

</work_completed>

<attempted_approaches>

## Three traps, all invisible to the register comparison

1. **The kill must be gated on the voice being SILENT.** `SR=$00` zeroes
   *sustain* too: the envelope falls to zero and only a gate RISE re-attacks it,
   so one mistimed kill silences the rest of a held note **while every later
   register still reads correct**. Four such frames cost **−24 dB** across
   27.1–28.0 s on `Love_tune_2`.
2. **The gate cannot be recomputed from `WAVE[VWI]`.** `wave_step` INCs `VWI` on
   the frame a row's count expires — exactly the pre-fetch frame — so the first
   guard blocked **100%** of the kills instead of 4 of 244 and looked like "the
   fix does nothing". Hence `VGCUR ($1889)`, the `$D404` byte actually written.
3. **Firing on every note is a regression the corpus mean looks good through.**
   Ungated, `Teekkno` went 42 → 468 and flipped its centroid sign while the
   9-file means still improved. Always look for the file that goes backwards.

## Smaller ones

- A first cut zeroed `VAD`/`VSR` inside the init loop and pushed `bpl iv` **3
  bytes out of branch range**. Moved to its own loop after the branch.
- **The heredoc backslash trap bit twice more**, exactly as the last two handoffs
  warned: `<<'PY'` ate `\r\n` into literal newlines, and `"bin\\build_x.py"`
  became `bin\x08uild_x.py`. **Write patch scripts with the Write tool, and use
  forward slashes in paths.**
- `drivers_src/mon/romuzak_driver.asm` is **CRLF**; a patcher reading it with
  `newline=''` and matching `\n` anchors silently matches nothing.
- A scratch file named `dis.py` shadowed the stdlib `dis` and broke every import.

</attempted_approaches>

<critical_context>

- **Every window is that file's own part-1 span.** The A/B tool now reads it from
  the same subprocess call that produced the build, clamps an asserted window
  *down* to it and never up. Past a part's end our build LOOPS against the
  original's continuing music.
- **Inertness verified by hash, not argument**: `Monty_on_the_Run` (Hubbard,
  `HARD_RESTART=1`), `Final_Luv` (Sound Monitor, `HARD_RESTART=0`), MoN's
  `Cybernoid_II` and `Love_tune_2`-with-flag-off all rebuild byte-identical.
- `.cerror SR_PREKILL && RELEASE_WF` — `sr_pre` reads the gate off the written
  `$D404`, which that path substitutes with `VRELWF`.
- Full write-up: `docs/players/HARDTRACK.md`, the two sections ending with "The
  selector is instrument mode 2, and the fix is ON by default".

</critical_context>

<current_state>

Suite 2,444 passing. Version unchanged at 3.27.0 (this session's cadence).

| task | state |
|---|---|
| #16 HardTrack brightness gap | **CLOSED as posed.** No corpus-wide deficit; the SR restart is modelled, selected correctly, shipped and rebuilt. `Love_tune_2`'s darkness survives and is now *understood* rather than open: it is what modelling the player's own release kill costs on that one file. Anyone reopening it should start from the loud frames (−1.87 → −2.26 dB vs the original), not the tails. |

**Open, untouched:**

- **`Filthy_Hit_VE-4x`** — 0.0%, 1,387 audible frames. The SDI V path's py65
  `v_traces` records no `$D418`; extending it closes the last real SDI passband
  gap (the other 3 V files differ by only 12 frames each). *Delegable.*
- **33 SDI files UNCONFIRMED** — each needs a per-file asserted `--seconds`.
  *Delegable, mechanical, chunk at ~20 files.*
- **8 HardTrack files UNCONFIRMED** in `passband_check` for the same reason —
  multi-part builds measured over a window their part 1 may not span.
- **DMC corpus tail: 87 of 216 frequency voices below 90**, incl.
  `French_Frites` (24.1/34.4/26.3) — a decode question, not a filter one.
- `Altered_States_Tune_2`'s 47-frame first-filter-row latency — inaudible,
  unexplained. Low value.
- A **startup-latency generalisation** was discarded as under-controlled. Redo
  it with per-file spans and fitted offsets or not at all.

</current_state>
