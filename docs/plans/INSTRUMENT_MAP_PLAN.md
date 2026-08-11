# Instrument map: joining SF2 instruments to the siddump trace

**Status**: **BUILT, all five stages.** Unreleased — the entry is under
`CHANGELOG.md`'s `[Unreleased]`, which already carried other work; cutting a
release is a separate decision. Plan written and executed
2026-08-10. §9 records what the stages actually found — read it before §6, since
three of the five acceptance criteria were met only after the code was wrong
once. The design below is left as written; §9 says where reality amended it.
**Prior art**: [h2g](https://github.com/MichaelTroelsen/h2g) `python/instrmap.py`
(550 lines) and its `FIDELITY-TOOL-IMPROVEMENTS.md` §1–2; `sid-reference-project`
`scripts/dev/instrument-map.js` (949 lines), which generalised it.

Everything in §3 was measured on this repo's own files today. Nothing here is
inherited on trust — h2g's central claim is measured on **one** player family and
does not survive the trip unmodified, which §4 is about.

---

## 1. What the prior art actually did — two separate things

They get conflated because they live in the same repo. They are independent, and
SIDM2 has already done one of them.

**(a) Stop throwing away four fifths of siddump.** h2g's `parse_dump` read only
the note and waveform fields out of each voice cell and never read the filter
cell at all, so ADSR, pulse width, cutoff, resonance, filter type and volume were
discarded at parse time. Three separate pieces of work landed in registers no
column of the report could see. Fixed in h2g v0.5.76 (parse) and v0.5.78 (score),
adding `adsr`, `pul`, `filt` and `cut` columns.

**SIDM2 already has this.** `fidelity_common.siddump_frames_full()` carries
`adsr` (the `$D405`/`$D406` pair as one 16-bit value), `filtctl` (`$D417`) and
`volmode` (`$D418`) per frame; `_reg("adsr", ("$D405/$D406",), ...)` is in the
dimension registry; and `registers_unread()` exists precisely so a run can print
which registers it did *not* look at. Item (a) is closed here — do not rebuild it.

**(b) Key the trace by ADSR to recover an instrument map.** The interesting one.
It rests on one property: in many players `$D405`/`$D406` is a **verbatim
per-instrument copy** of the instrument record, so it identifies an instrument
where waveform cannot (several instruments share a waveform) and pulse cannot (a
swept width has no single value). h2g measured that at *"0 of 1635 corpus records
differ"* — on the Hubbard family only.

From that key, h2g builds:

- a **mapping table** — one row per instrument of ours: declared ADSR, the
  waveform its wavetable opens on, the modal waveform the *original* sounds under
  that ADSR, note counts on both sides, and a verdict (`ok`,
  `**the original plays it, we do not**`, `**we play it, the original does
  not**`, `**waveform: pulse -> saw**`);
- a section listing **ADSRs the original sounds that no instrument of ours
  carries**;
- a per-instrument **profile read off the original** — waveform per frame over
  the first 8 frames, pulse band, pitch fall, frames until gate-off — described
  in the source as *"the spec the `.sng` should meet"*;
- `annotate_dump()` — **siddump's own table with three instrument columns
  appended** (`Ins1 Ins2 Ins3`), `*` marking the onset frame, a lowercase letter
  for an ADSR no instrument of ours carries. This is the thing this repo does not
  have, and the thing the request is really about.

`sid-reference-project` then took the same technique to 61 HVSC player families
and found that h2g's version does not survive contact with them — §4.

---

## 2. What SIDM2 has and does not have

| capability | state |
|---|---|
| `$D405/$D406` parsed per frame, fill-forwarded | ✅ `siddump_frames_full()` |
| `adsr` registered as a scoreable dimension | ✅ `fidelity_common._reg("adsr", …)` |
| empty/vacuous-comparison guards | ✅ `score_pct()` returns `None`, `exercised()` |
| note onsets from the trace | ✅ `siddump_note_onsets()` — note *names*, no registers |
| **onset → instrument index attribution** | ❌ nothing does this |
| **SF2 instrument table located by search, not by constant** | ❌ constants only |
| **siddump annotated with instrument columns** | ❌ |
| **per-instrument fidelity** (which instrument loses the frames) | ❌ every score is per voice / per register |

Every fidelity number in this repo is per voice and per register. A HardTrack
Stage B run says "ADSR 88–94%, systematically HardTrack's pre-note-on SR-zeroing";
an SDI run says "274/324 ship some default instrument data". Neither can say
*which instrument*. That is the gap.

---

## 3. Evidence this works on SIDM2 material (measured today)

Probe: `siddump_frames_full(path, ['-t20'])` → gate 0→1 edges per voice → sample
the first settled frame within 4 of the onset → group by ADSR.

| file | frames | onsets | distinct ADSR | ratio | unsettled | settle delay |
|---|---|---|---|---|---|---|
| `SID/Angular.sid` | 1000 | 347 | 10 | 0.03 | 4 | +1 on all 347 |
| `SID/Beast.sid` | 1000 | 301 | 8 | 0.03 | 2 | +1 on 299, +0 on 2 |

Ratio 0.03 is the far side of the `reliable` threshold (0.4). **The key holds on
Laxity NP21.**

Then the join — `SID/Angular.sid` (original) against `SF2/Angular.sf2` (our
conversion), with the instrument table located by **search**, not by constant:

```
ROW hits=9/10 stride=8 file_off=3311 addr=$1A6B
```

`$1A6B` is `INSTRUMENTS` in CLAUDE.md's Laxity constants; stride 8, `[0]=AD,
[1]=SR`. The search recovered the documented address without being told it. The
join:

| observed ADSR | notes | → instrument |
|---|---|---|
| `$0198` | 79 | 8 |
| `$0028` | **50** | **absent from the table** |
| `$00A8` | 41 | 11 **or** 12 |
| `$03F8` | 38 | 0 |
| `$0694` | 38 | 3 **or** 4 **or** 5 **or** 6 |
| `$0188` | 33 | 7 |
| `$02A8` | 33 | 2 |
| `$03E8` | 17 | 10 |
| `$04F8` | 17 | 1 |
| `$02A9` | 1 | 9 |

Three findings, all of which the plan below has to survive:

1. **It works.** 9 of 10 sounded envelopes name a declared instrument.
2. **`$0028`, 50 notes, in no record.** Either a hard-restart envelope the sample
   frame is catching, or a real conversion gap. Unresolved — and it is exactly
   the kind of thing no current SIDM2 metric can report.
3. **The key is not injective.** `$0694` covers instruments 3–6, `$00A8` covers
   11–12. A map that prints one number there is lying; h2g prints `3/4/5/6` or
   `3+`.

And the control that decides the architecture: reading the table at the
**constant** `$1A03` (Driver 11's documented instrument offset) instead of
searching gave **0 of 10** matches on `SF2/Angular.sf2` — because that file uses
the Laxity driver — and an all-zero AD column on `out/Bad_Blood.sf2`. Commit
`80b5a72` in this repo is *"Driver 11 orderlists came from a hardcoded Laxity file
offset"*. **The locator must be a search that returns a verdict.**

---

## 4. The three hazards, and why h2g's version cannot be ported verbatim

**H1 — the hard restart.** h2g samples onset+1, reasoning that the onset frame can
still hold the player's transition. Taken literally elsewhere this produces
confident garbage: Laxity/JCH NewPlayer runs a multi-frame hard restart (frequency
driven to `$FFFF`, waveform cleared, a restart envelope written), and on Stinsen's
`Last_Night.sid` a fixed onset+1 sampled the **restart on 96 of 96 notes** —
yielding four tidy, perfectly stable "instruments", graded `reliable`, whose ADSR
values appear **nowhere in the payload**. The fix is the *first settled frame
within 4*: gate still on, a real waveform selected, frequency off the
`$0000`/`$FFFF` sentinels. When more than half the notes never settle, the file is
`unusable` and **no table is emitted** — and that test must run **before** the
distinct-value tests, since a hard restart is exactly the small, tidy value set
those tests reward. The `$0028`/50-note result in §3 may be a live instance; the
tool has to be able to say so rather than silently absorbing it.

**H2 — siddump force-displays every register on frame 0.** Already a
fixed-then-recurring bug class here (`fidelity_common`'s own docstring;
`PATTERNS.md` D4/D9). Frame 0 hands back pre-init bus state, not a write. Onset
detection keyed on a gate 0→1 edge must not treat frame 0 as an edge, and
`exercised()` must gate any percentage the map produces.

**H3 — the key does not always exist.** h2g's "0 of 1635" is one player family.
Across a 27-file spread in `sid-reference-project`: 12 `reliable`, 5 `degenerate`
(one ADSR covers every note — stable but separates nothing; Galway's Wizball, 1
value over 32 onsets), 3 `suspect`, 7 `insufficient-data` (includes digi players,
which never gate), 0 `unusable` in that sample though `unusable` is real. **The
first thing the tool does is decide whether the key holds at all**, and emit
evidence-plus-verdict rather than a table when it does not.

---

## 5. Proposal

### 5.1 `sidm2/instrument_map.py` — the library

Pure functions over data already available. No new tracer, no new siddump mode.

```
onsets_with_registers(frames, settle_max=4) -> [Onset]
    Onset = (voice, frame, sample_frame, settled, adsr, wave_class,
             pulse_bucket, freq)
    Gate 0->1 edges from siddump_frames_full(), sampled at the first settled
    frame within `settle_max`. wave_class = $D404 & 0xF0 (gate/test/sync/ring
    masked off, so one instrument is not split into several rows).
    pulse_bucket = pulse // 0x100 (a swept width has no single value).

key_reliability(onsets, frames, min_onsets=30) -> Verdict
    reliable | degenerate | suspect | insufficient-data | unusable, each with
    the numbers that produced it. Unsettled-ratio test FIRST (H1).

locate_instrument_table(sf2_bytes, observed_adsr) -> [Candidate]
    Both shapes this repo's drivers actually use:
      row-major     AD/SR adjacent at a constant stride (Laxity, 8; HardTrack)
      column-major  AD and SR in parallel arrays a constant delta apart
                    (Driver 11: 32 AD at $0A03, 32 SR at $0A23)
    Ranked by hits/observed, reporting `width` -- how far apart the matched
    bytes sit. A real column is tight, and $00/$0F line up by luck.

check_declared(candidate, observed) -> confirmed | confirmed-weakly
                                     | layout-wrong | out-of-range
    `confirmed-weakly` when the match is close to free: too few observed
    values, or a declared table large enough that landing in it says nothing.

build_map(observed, declared) -> [MapRow]
    Ties preserved ("3/4/5/6"), never collapsed to a single index.
```

Register an `instr` dimension via `register_dimension()` if any percentage is
printed, so `registers_unread()` keeps accounting for what was compared.

### 5.2 `instrument-map.bat` / `pyscript/instrument_map_report.py` — the report

```
instrument-map.bat orig.sid converted.sf2 [-t 20] [--annotate] [--json]
```

Four sections, each already justified by prior art:

1. **Key reliability** — verdict plus the numbers that produced it. Printed even
   when the answer is "this file has no ADSR key", because that is a result.
2. **Mapping** — per declared instrument: ADSR, the waveform its wavetable opens
   on, the original's modal waveform and note count, ours, verdict. Plus the
   *sounded-by-the-original-with-no-instrument-of-ours* list. `$0028`×50 from §3
   is the first entry this repo will get.
3. **Profile from the original** — waveform per frame over the first 8 frames,
   pulse band at onset *and* over the whole note (a sweep that restarts with the
   note sits on one onset value however far it travels, so an onset-only reading
   calls a working sweep static), pitch fall, gate-off frame. This is the spec
   the SF2 wave/pulse programs should meet.
4. **`--annotate`** — siddump's own table with `Ins1 Ins2 Ins3` appended, `*` on
   onset frames, lowercase letters for unmatched ADSRs plus a legend. The
   instrument is decided **once per note** at the sample frame and held to the
   next onset, so the column can never disagree with §2's table.

`iter_siddump_rows()` already splits on `|`, so appending columns is a
line-rewrite of `run_siddump()` output — no change to `siddump_complete.py`.

### 5.3 Per-instrument fidelity — the reason to do this at all

Once a frame carries an instrument label, every existing per-frame comparison can
be **grouped by it**. `freq`/`wf`/`pul`/`adsr` agreement stops being one number
per voice and becomes one number per instrument, with `n`. "HardTrack Stage B
ADSR 88–94%" becomes "instrument 5 is 61%, everything else is 100%", which names
the record to go and look at. Same for SDI's 274/324 default-instrument files: the
map says which slots are actually sounded and which are never reached.

This is the payoff. §§5.1–5.2 are the plumbing.

---

## 6. Stages

**Stage 1 — the key, and the honest refusal.** `onsets_with_registers` +
`key_reliability`. CLI prints the verdict and nothing else.
*Accept when*: a spread of ≥20 files across ≥6 player families runs without
crashing and the verdict distribution is reported; at least one file grades
`unusable` or `degenerate` and the report says why. A tool that grades everything
`reliable` has not been tested, it has been believed.

**Stage 2 — locate and check.** `locate_instrument_table` + `check_declared`,
across both table shapes.
*Accept when*: the search independently recovers `$1A6B`/stride 8 on
`SF2/Angular.sf2` **and** the Driver 11 column layout at `$0A03`/`$0A23` on a
Driver 11 build, with no constant supplied; and a deliberately wrong declared
offset produces `layout-wrong`, not silence.

**Stage 3 — the report.** §5.2 sections 1–3.
*Accept when*: `$0028`×50 on Angular is either explained (hard restart — in which
case H1's settle logic is wrong for Laxity and must be fixed) or stands as a real
conversion gap with a named cause. **Do not ship with that row unexplained**; the
first finding is the calibration.

**Stage 4 — `--annotate`.**
*Accept when*: the annotated dump round-trips — stripping the appended columns
returns `run_siddump()`'s output byte for byte.

**Stage 5 — per-instrument fidelity.** §5.3, wired into one validator first
(HardTrack Stage B, which has a live unexplained ADSR residual).
*Accept when*: the per-instrument split sums back to the existing whole-file
number, and a deliberately corrupted instrument record moves exactly one row.

---

## 7. What this does not do

- It is a **register comparison, not a sound comparison**. It sees a wrong
  sustain or an invented hard restart; it cannot see an envelope that is right but
  arrives three frames late. Pair it with `audio-tightness.bat`; do not substitute
  it.
- **ADSR is not injective** (§3): where several instruments share an envelope the
  map narrows to a set, not a record. A genuine limit of the key, not a bug to
  engineer around.
- **A register trace localises; it does not adjudicate.**
  `sid-reference-project` found a real falsification this way (`john-player`:
  every observed ADSR absent from the declared table and present at `+1/+2` of the
  same grid) and only the *disassembly* could say which half of the claim was
  wrong. Expect the same here — the map produces the question, not the answer.
- Resonance shares the `$D417` byte with the routing bits and siddump never
  separates them, so nothing here scores resonance on its own.

---

## 8. Tests (`pyscript/test_instrument_map.py`)

- Synthetic frame list with a known hard restart → `unusable`, no table emitted,
  and the restart's ADSR values do **not** appear in the output.
- Single-ADSR file → `degenerate`, not `reliable` (a one-row map must never read
  as "this player has one instrument").
- Fewer than 30 onsets → `insufficient-data`.
- Frame 0's force-display does not register as a gate edge (H2).
- `locate_instrument_table` on a hand-built row-major and a hand-built
  column-major buffer, including the `$00`-padding false-positive case.
- Ties: an ADSR shared by two records renders as both, never as one.
- `--annotate` round-trip (Stage 4 acceptance) as a unit test.

---

## 9. What was built, and what it found

Shipped:

| file | what |
|---|---|
| `sidm2/instrument_map.py` | the library: onsets, key verdict, table search, map, profiles, annotation, `InstrumentScores` |
| `pyscript/instrument_map_report.py` + `instrument-map.bat` | the report |
| `pyscript/instrument_map_sweep.py` | the key-verdict calibration sweep |
| `pyscript/test_instrument_map.py` | 31 tests |
| `bin/build_hardtrack_native_song.py` | Stage 5: a PER INSTRUMENT block under the existing per-voice table |

31 tests pass; the full `pyscript/` suite is unchanged.

### Stage 1 — the key holds, and it fails in more ways than two

27 files, 13 player directories, 20 s each
(`py -3 pyscript/instrument_map_sweep.py -n 2`):

**16 reliable, 6 insufficient-data, 2 no-trace, 2 degenerate, 1 unusable.**

`unusable` is `Tel_Jeroen/05-09-87.sid`: **372 of 372 onsets never settle** —
the sample never leaves the player's hard restart. That is H1, in this corpus,
on a file that would otherwise have graded `reliable` off two tidy stable
values. `degenerate` is `deenen/Aids_See_Ass.sid` (1 value over 154 onsets) and
`JohannesBjerregaard/2nd.sid` (1 over 93).

**A fifth verdict was added that the plan did not anticipate: `no-trace`.** Two
files reported 0 onsets, and 0 onsets is ambiguous in a way that matters — a
digi player that never gates and a file the tracer could not drive are
indistinguishable from the count alone. `Gray_Matt/Always_on_My_Mind.sid` and
`LFT/A_Computer_in_My_Backpack.sid` are the second kind, and calling them
`insufficient-data` would have filed a tooling failure as a property of the
music. This is the same empty-vs-zero confusion `score_pct` exists for.

### Stage 2 — the search works, and it is ambiguous by exactly one thing

- `SF2/Angular.sf2`: recovers **`$1A6B`, row-major, stride 8** — the documented
  Laxity `INSTRUMENTS` constant — with no address supplied. The *original*
  `SID/Angular.sid` independently resolves to the same address.
- Packed SF2 **Driver 11** test tunes: recovers **column-major, step 32**, the
  `$0A03`/`$0A23` layout, on 3 of 4 (the 4th sounds only 3 envelopes in one
  tight run and is genuinely under-determined — `confirmed-weakly` is for that).

Two corrections the code needed:

1. **Aliasing.** A stride-N grid explains the same bytes from every base N·k
   earlier, with every record index shifted by k. Ranking by base picked the
   earliest shadow and Angular first resolved to `$19CB` — **every instrument
   renumbered by +20**. Aliases are now collapsed to one candidate.
2. The survivor is the base whose first *sounded* record is record 0, which is
   an **assumption, not a deduction**: the trace cannot see a leading run of
   slots the tune never plays. Driver 11's own test tunes never sound slot 0, so
   the search reports `$1D3B` where the truth is `$1D3A`. **One record high, and
   the tool says which direction the error runs.**

### Stage 3 — `$0028` is explained, and it is neither of the two options

The plan allowed two outcomes: a hard-restart artifact (fix H1) or a real
conversion gap. It is a third thing.

`$0028` is sounded 50 times on `SID/Angular.sid` and appears in **neither** the
conversion's instrument table **nor the original's own** — both resolve to
`$1A6B` with the same 13 records. Frame-by-frame, the two traces are identical:
gate on with no waveform, `$0028` written, held for the whole note, back to
`$0F01` (record 14) at gate-off. It is a real sustained note envelope the player
writes from outside its instrument records, and **our conversion reproduces it
byte for byte**.

So it is not a defect, and the tool had to gain the vocabulary to say that:

- a new verdict **`incomplete`** — a minority miss does not falsify an address
  that the majority independently confirms. `layout-wrong` is now reserved for
  the case where most or all observed values are absent, which is the real
  falsification (`sid-reference-project`'s `john-player`).
- the orphan table gained an **`our notes`** column. An envelope both sides
  sound the same number of times is a blind spot in the key, not a conversion
  gap, and those two findings need different investigations.

### Stage 4 — round-trip is byte-exact on real siddump output

Verified on the full 1000-frame `SID/Angular.sid` dump, in memory and through a
file. One bug on the way, and it is the kind a passing test hides: siddump emits
**CRLF**, `splitlines()` eats the `\r`, and a `str` comparison against a
`\n`-only expectation still succeeds. Both functions now split on `\n` alone and
carry any trailing `\r` across the insertion.

### Stage 5 — the residual now names a record

`bin/build_hardtrack_native_song.py SID/Shogoon/Love_tune_2.sid 30`, with the
split fed from the identical match result the voice totals use:

```
  FIDELITY (per-frame freq semitone vs original, all parts):
      0   |  95.9% ( 1492) |  91.7% (  733)
  PER INSTRUMENT (... ADSR key: reliable)
    voice instr    freq%      n     (split sums back to the per-voice n: True)
      0        1    97.2%    745
      0        0    96.4%    640
      0      4/5    86.7%     45
      0        7    77.8%     36        <-- 
      0        8    88.5%     26
      1       11    78.5%    107        <-- 
      1        -     0.0%     10   (frames before the first note-on)
```

"Voice 0 is 95.9%" becomes "records 7, 4/5 and 8 are the residual, records 0 and
1 are not". The unattributed bucket is explicit so the split **sums back** —
verified in the run and in a unit test, because a split that does not sum back is
measuring a different population than the headline above it.

### Where the plan was wrong

- §5.2's *"the waveform its wavetable opens on"* column is **not built**. It
  needs per-driver wave-table knowledge (Laxity `$1ACB` vs Driver 11 `$0B03`),
  which is exactly the hardcoded-offset dependency §3's control argues against.
  The original-vs-ours modal waveform columns carry the same signal without it.
- §5.1's `check_declared(candidate, observed)` signature became
  `check_declared(data, layout, observed, count)` — the verdict needs the bytes,
  not just the shape.
