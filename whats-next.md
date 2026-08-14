# Handoff — SIDM2 session, 2026-08-14

<original_task>
Opened with **"read what next"**, then **"do the task on the list"** — which was
the single filed item, **#16 HardTrack brightness gap**, whose one unattempted
step the previous handoff named exactly: *build the HRC per-note lookahead, then
A/B the audio.* No other scope was given.
</original_task>

<work_completed>

**The experiment is run and the answer is no.** The lookahead is built, it fixes
the registers, it improves the corpus, and it makes `Love_tune_2` — the one file
the brightness gap was ever about — **worse**.

## What shipped

`SR_PREKILL` in `drivers_src/mon/romuzak_driver.asm`, **off by default**,
`HT_SR_PREKILL=2` to enable per build. It zeroes `$D406` on the frame
`zp_tcnt == SR_PREKILL` for a voice whose `vhold` is 0 (it FETCHES at the next
row tick — the same predicate the SEEK pulse hold uses) and whose gate is
currently off; `sr_rearm` restores the instrument AD/SR on the fetch itself. No
row is spent, which was the point: the write lands between two row boundaries.

The width is **measured, not guessed** — every `SR=$00` run in the originals is
exactly two frames (159 runs on `Love_tune_2`, 378 `Muminki_Rooooolz`, 328
`Something_to_Eat`, 142 `Muza_Do_Dema`, 23 `Teekkno`).

- `pyscript/hardtrack_sr_prekill_ab.py` — **tracked** 9-tune A/B, builds both
  sides itself, each tune inside its own asserted part-1 span.
- `pyscript/test_hardtrack_sr_prekill.py` — 6 tests. Suite **2,442 passing**.

## The result

| | off → on |
|---|---|
| SR mismatching frames, 9 tunes | **2,966 → 1,170** (6 of 9 essentially zero) |
| mean \|centroid error\| | 67.2 → **52.7 Hz** |
| mean \|rolloff error\| | 182.9 → **136.2 Hz** |
| centroid closer to the original | **5 of 9**; further on 4 |
| **`Love_tune_2` centroid** | **−57.9 → −101.4 Hz** ⚠️ |

`Love_tune_2` per-voice SR goes 92/98/148 → 2/8/58 and every survivor is the
*reverse* direction, so the named defect is gone rather than reduced — and the
file still gets darker. The SR-tail hypothesis is confirmed in **direction** and
shown to **overshoot**: binned by the original's own level, we were **+1.26 dB**
too loud on its −35..−28 dBFS frames and land at **−0.48**, buying that with
0.32 dB on the loud frames.

## The finding that reframes the open work

**The restart is per-INSTRUMENT, not per-note.** Keyed by the AD/SR pair written
at each note-on: `Love_tune_2` 159/159 restarted, `Muminki_Rooooolz` 378/378,
**`Teekkno` 23 of 245**. Its ADSR `$0ffc` restarts on 1 of 222 note-ons while
`$099d`/`$099e`/`$cccc` restart 9/10, 7/7, 4/4. Firing unconditionally is what
costs `Teekkno` 42 → 468 and flips its centroid sign.

Two candidate selectors **ruled out**: instrument **field-5 bit 4** (the player
reads field 5 exactly three times with masks `$03`/`$10`/`$80` in 33 of 33, and
`$10`'s only consumer is the filter re-arm guard — disassembly-confirmed), and
**gate state** (the two pre-note frames are gate-off on the restarting and the
non-restarting file alike).

</work_completed>

<attempted_approaches>

## Two traps, both invisible to the register comparison

1. **The kill must be gated on the voice being SILENT.** `SR=$00` zeroes
   *sustain* as well as release: the envelope falls to zero and only a gate RISE
   re-attacks it, so one mistimed kill silences the rest of a held note **while
   every later register still reads correct**. Four such frames cost **−24 dB**
   across 27.1–28.0 s on `Love_tune_2`. The SR diff showed "4 frames"; the audio
   showed a hole. Never sign this off in the register domain alone.
2. **The gate cannot be recomputed from `WAVE[VWI]`.** `wave_step` INCs `VWI` on
   the frame a row's count expires — exactly the pre-fetch frame `sr_pre` runs
   on — so the recomputed byte is the *next* row's. The first guard therefore
   blocked **100%** of the kills instead of 4 of 244, and looked like "the fix
   does nothing". The driver now stashes the `$D404` byte it actually wrote in
   `VGCUR ($1889)`.

## Smaller ones

- A first cut zeroed `VAD`/`VSR` inside the init loop and pushed `bpl iv` **3
  bytes out of branch range**. Moved to its own loop after the branch.
- **The heredoc backslash trap bit again**, exactly as the last handoff warned:
  `py -3 - <<'PY'` ate one level of `\r\n` and wrote literal newlines into a
  patch script. Write patch scripts with the Write tool.
- `drivers_src/mon/romuzak_driver.asm` is **CRLF**; a patcher that reads it with
  `newline=''` and matches `\n` anchors silently finds nothing.

</attempted_approaches>

<critical_context>

- **Every window is that file's own part-1 span** (`Love_tune_2` 28 s,
  `Ritual_II_tune_2`/`Walk_to_Soul`/`Something_to_Eat` 10 s, `Takisobie` 12 s,
  `Rune-T_Noter` 14 s). Past a part's end our build LOOPS against the original's
  continuing music. This is the error the previous session made five times.
- **Inertness verified by hash, not by argument**: `Monty_on_the_Run` (Hubbard,
  `HARD_RESTART=1`), `Final_Luv` (Sound Monitor, `HARD_RESTART=0`) and
  `Love_tune_2` itself all rebuild **byte-identical** with the flag off. Both
  branches of the `.if HARD_RESTART + SR_PREKILL` change are covered.
- `.cerror SR_PREKILL && RELEASE_WF` — `sr_pre` reads the gate straight off the
  written `$D404`, which that path substitutes.
- Full write-up: `docs/players/HARDTRACK.md`, "The per-note lookahead was BUILT,
  and it is NOT the brightness fix".

</critical_context>

<current_state>

Suite 2,442 passing. Version unchanged at 3.27.0 (this session's cadence — the
last 25 commits carry no bump).

| task | state |
|---|---|
| #16 HardTrack brightness gap | **Decisive experiment DONE, question re-pointed.** No corpus-wide deficit; the lookahead is not `Love_tune_2`'s fix. What is now open is narrower and better posed: **which instruments get the SR restart.** It needs the player's own code (`docs/guides/RETRODEBUGGER_GUIDE.md`), not another measurement — `Teekkno` is the discriminating file. With that selector the pre-kill becomes correct everywhere and can ship on. *Opus, main.* |

**Still open from the previous handoff, untouched:**

- **`Filthy_Hit_VE-4x`** — 0.0%, 1,387 audible frames. The SDI V path's py65
  `v_traces` records no `$D418`; extending it closes the last real SDI passband
  gap (the other 3 V files differ by only 12 frames each). *Delegable.*
- **33 SDI files UNCONFIRMED** — each needs a per-file asserted `--seconds`.
  *Delegable, mechanical, chunk at ~20 files.*
- **DMC corpus tail: 87 of 216 frequency voices below 90**, incl.
  `French_Frites` (24.1/34.4/26.3) — a decode question, not a filter one.
- `Altered_States_Tune_2`'s 47-frame first-filter-row latency — inaudible,
  unexplained. Low value.
- A **startup-latency generalisation** was discarded as under-controlled. Redo
  it with per-file spans and fitted offsets or not at all.

</current_state>
