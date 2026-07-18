<original_task>
Session entry point: "read what next" -> I read the prior handoff (whats-next.md,
2026-07-17, Zamzara = 6th clean win) and picked up its recommended next step
(fix the Deenen audio-validator's pooling flaw). The session then evolved through
explicit user redirections:
  1. Fix the validator pooling flaw (whats-next #1) -> resolved.
  2. "yes"/"cont" -> continue Deenen: melodic emission validation, then the
     "bigger prize" (mon_parser LOCATE).
  3. "lets get done with this and get back to sid duzz" (x2) -> bank Deenen/mon,
     pivot to SID Duzz' (SDI).
  4. "I want to be as close as 100% for the remaining player" + "grind the list"
     -> push SDI Stage B fidelity toward 100%.
  5. "lets tie the last issue with SDI" -> the variant-V wrapper.
  6. "go on" -> start the next new player. User chose (AskUserQuestion):
     **Mainstream MoN / Jeroen Tel (SID/Tel_Jeroen, 179 files)**.

STANDING RULES (all still live): accuracy over speed; never ship lossy silently
("builds != sounds right" bit HARD this session — see the V garbage-SF2 gate);
verify by EMULATION before rewriting a parser; a fidelity claim must never
outrun its evidence; corpus-gate every shared-code change; read your own tool's
output before trusting it; verify a metric before believing a low/high score;
NEVER run pyscript/sf2_open_in_editor.py unless asked; NEVER run two MoN builds
concurrently (shared drivers_src scratch).
</original_task>

<work_completed>
Repo: master. **17 commits** on top of 40d9728. Version UNCHANGED at 3.21.0
(bug-fix/RE work). Working tree CLEAN except the pre-existing untracked corpora
(SID/Gallefoss_Glenn, SID/deenen, SID/Tel_Jeroen, etc.) + the local-only
.claude/settings.local.json. Nothing pushed to origin. Full suite green after
every sidm2/ change: **1561 passed / 7 skipped / 2 xfailed** (~3.5 min).

=== ARC 1: DEENEN + MoN (4 commits) ===
The prior session left the Deenen audio validator with a POOLING FLAW (it pooled
every semitone across all 3 voices into one set, so PASS proved almost nothing).

  6990c54  "the emitted SF2 was broken 3 ways; fix + per-voice validator"
    Fixing the validator immediately exposed the BUILDER was shipping wrong SF2s
    (the 6 clean wins are DECODER-side; the emitted files were another matter).
    THREE builder bugs in bin/deenen_to_sf2.py:
    (a) WRONG TEMPO: hardcoded Driver 11 tempo=1 (=2 frames/row), but a decoded
        row is groove_rate() REAL frames, per-file (2.0/2.5/3.0). R=3 files
        played 1.5x too fast. MEASURED: the driver plays value+1 frames/row
        (off-by-one from SF2_FORMAT_SPEC). Fix: tempo_chain(m)=R-1, a two-entry
        CHAIN [1,2] for fractional R=2.5. Emitter (sidm2/galway_driver11_emitter.py
        + galway_to_driver11.py) now takes tempo as int OR list; int path
        BYTE-IDENTICAL (the 7 other Driver 11 builders untouched).
    (b) WHOLE VOICES DROPPED: voice_rows decoded the 8000-event LOOPED stream as
        literal rows (30k-150k rows/voice) -> 200-330 sequences vs the emitter's
        128-seq pointer table, which drops overflow SILENTLY. Voice 2 packs last
        -> lost EVERY entry on CR/Zamzara/After_the_War/Astro; LotR lost v1+v2.
        (This was the real cause of the prior handoff's "After_the_War instr
        15/24 missing" — those drums are on voice 2.) Fix: stop_on_loop=True (ONE
        playthrough; orderlist already ends FF 00 = loop). Builder now REFUSES
        (dropped_orderlist()) to emit a song with dropped voices.
    (c) RAW $00 percussion step (freq 0 = silence) was mapped to abs note 0;
        now emits a waveform-off row. Only Astro instr 8 hits it.
    bin/deenen_sf2_validate.py REWRITTEN: per-voice/per-time (build_sdi.. no —
    it shares deenen_to_sf2.build_song, walks each percussion note's own frames
    on its own voice; prefix-agreement; abstains on unmeasurable notes;
    silence-transparent; respects plausible(); honest window reporting).

  6e6cd54  "Constant_Runner is the 7th clean win - stale $40 guard removed"
    plausible()'s $40-class blanket refusal in sidm2/deenen_parser.py was stale:
    the tel-class ROWS were never unported (shared _parse_row; engine-check
    100/100/100), and the 35.6% was the fixed attack-transient metric bug (now
    97.7). Removed the blanket; the general degenerate/dead-voice checks remain.
    VERIFIED (probe): removing it flips ONLY Constant_Runner True; Mr_Heli/
    Mantalos/Eye_to_Eye stay refused. Corpus: 10/19 located, 7 clean wins.

  ef020be  "audio-validate the emitted SF2's MELODIC content too, per voice"
    Extended deenen_sf2_validate.py to also check melodic pitch (for each plain
    note the decoder schedules on voice V, does that pitch sound in the note's
    frame span on V?). 6/7 clean wins 100% faithful; After_the_War 127/128 (the
    one miss is voice 0's opening PORTAMENTO SLIDE, confirmed by siddumping the
    original — the same unmodelled $FD-slide class as Zamzara, whats-next #3).

  4967d7d  "instrument 0 is the REST slot - Double_Dragon + Zynon decode exact"
    (This was the payoff of the mon_parser LOCATE "bigger prize" investigation —
    see mon-locate-investigation.md.) MoN's instrument 0 is the rest/silent slot
    (all-zero 8-byte record across Hawkeye/Cyb/Cyb_II/Double_Dragon); mon_parser's
    _emit counted its events as onsets, and under the validator's monotonic
    alignment those false onsets BLOCKED real matches. Fix (sidm2/mon_parser.py):
    _silent_instr(i) + _emit sets retrig=False for a zero-instrument event.
    Numerator RISES: Double_Dragon sub0 99/123->109/109 EXACT, Zynon sub0/1/2 all
    EXACT (was pseudo-parse rejected), Cybernoid sub0 41/54->53/53. Zero
    regression (git-stash A/B verified Hawkeye sub2/3, Cyb_II sub3/5 identical).
    NOTE: the mon_parser LOCATE investigation reframed the "12 $40-class files"
    prize — they are HETEROGENEOUS (5 Deenen-dialect = deenen's job; 4 already
    won; Airwolf/Day_After = MoN/FC own sub-dialect needing locate+grammar). The
    Airwolf 4-part arc (self-mod operand $17D4/$17D7 + 2-tier grammar + speed +
    freq locate) is scoped but DEFERRED. See mon-locate-investigation.md.
    Also measured Zamzara's $FD slide: LINEAR at -70/frame -> Driver 11 T0 maps
    1:1 (de-risks whats-next #3).

=== ARC 2: SID DUZZ' (SDI) STAGE B NATIVE (13 commits) — the main event ===
Stage A was DRAINED (v3.20.0: 344 SF2s, all 6 variants A/B/C/D/E/V decoded); the
strict-pitch ceiling (~50 on E/DELTA/V) is a per-frame WFPRG-ARPEGGIO problem a
static decoder can't model. Stage B captures it. NEW FILE: bin/build_sdi_native_song.py
(a trace-driven shim into bin/build_mon_native_song, modeled on the DMC/SM
builders: measure_onsets places notes at $D404 gate-rises, base pitch from the
trace, the engine CAPTURES per-frame freq/wf/pulse/filter -> arps byte-exact).

  0d461c5 beachhead (single-window; 2_Young 98/85/100, Tranedans 88/92/99 vs
          Stage A strict 13.4; inline phase-aligned fidelity, never emit blind)
  6c697f4 docs
  1c92d46 ADAPTIVE PART-SPLITTING (build_song + measure_parts, copied from DMC/SM;
          `auto` splits whole song, no cap force-merge; Tranedans 260s->30 parts)
  c6e62bc TRACE-DRIVEN LEGATO (DELTA/E tie engine glides under one gate;
          measure_onsets sees ~1 onset; drive from the TRACE's pitch-change
          frames as TIES; Delta_Slow v2 22.7->79.9)
  93ce35d refuse files measure_onsets can't drive (V/self-IRQ) — was emitting a
          garbage SF2 with a meaningless both-silent score
  9a89a67 docs
  da5d492 TIGHTEN LEGATO CRITERION (fast arps that re-gate regularly were being
          fragmented into 1-frame ties; legato now only for voices that never
          re-gate, <=max(2,notes//20) gates; Moi_Funk v1 37->83)
  745ce07 LEADING REST for late-entering voices (THE BIG GENERAL WIN: events
          placed sequentially by dur -> a voice whose first onset != ~0 was
          shifted EARLY by its start offset; Bahbar v2 first gate frame 769 ->
          played 769f early. Insert rest of ons[0]. Broad lift: Bahbar
          99.6/76/78->100/91.8/89.5, Neverending 65/67/64->100/98/97)
  04c80a2 LAST-NOTE SUSTAIN (last note was cut to +8 frames; Neurotica_short
          sustains a held tail to ~3499 -> ~1600 frames emit-silent, final part
          ~30%. Scan the trace forward while the voice's wf stays active and hold.
          Neurotica_short 54/59/62->99.9/99.6/99.9. The "deep-song drift" was a
          truncated tail, not drift.)
  40795c5 NOISE-AWARE METRIC (a noise frame has no meaningful pitch -> score it
          on the waveform, not freq-semitone; 2_Young v1 85->100; honest, a
          broken noise voice still fails)
  b366775 docs
  3e3543e VARIANT-V WRAPPER DRIVE (the "last issue"): V is play=$0000 self-IRQ
          around a 3-JMP module (init/play/fast at base/+3/+6). _v_module_addrs()
          finds the module via the wrapper init's `JSR base; CLI` (20 lo hi 58);
          v_traces() drives it via py65 (module init, then play x v_mult per
          video frame, snapshotting $D400-$D418) -> the ground-truth per-frame +
          filter + onset traces; emitted SF2 (real play addr) siddumped and
          compared to it. ALL 6 V FILES BUILD (were 0): Different_Reality
          99.1/99.4/99.1, Oh_Boy_VE-2x 99.7/99.7/80.3, Implocation 97.1/99.8/96.4,
          Pultost 94.2/94.8/96.1, Underwear 91.8/91.3/99.8, Filthy_Hit
          76.2/99.9/96.0. ALSO fixed a PRE-EXISTING parser bug: _decode_voice_v
          used self._v_tempo (only events() presets it) -> standalone
          decode_voice() AttributeError'd on V files with a $Cx tempo cmd
          (Oh_Boy). Lazy-init'd via __dict__.setdefault.
  55414f1 docs

  SDI STAGE B FINAL STATE: ALL SIX VARIANTS (A/B/C/D/E/V) have Stage B. Most
  E/DELTA/C/V voices are 98-100% (2_Young 100/100/100, Delta_Slow 100/100/100,
  Neurotica 99.9/99.6/99.9, Moi_Funk 99.9/99.9/98.6, Kirby ~99.7, Different_Reality
  99/99/99). LONE RESIDUAL: fast per-frame ARP voices (Bahbar v1/v2 92.7/90.4,
  Filthy_Hit v0 76) — genuinely tonal (not noise), the FM-capture ceiling.

=== ARC 3: MAINSTREAM MoN / TEL — OPENED, RECON ONLY (0 commits, memory only) ===
User chose it as the next player. Reconnaissance (scratch scans, no siddump):
  - SID/Tel_Jeroen = 179 files. mon_parser: locate-in-range 54/179, DECODE-SANE
    only 19/179; 125 locate-OUT-OF-RANGE (olptr->$83FC default, freq->$8337).
  - Variant map by orderlist-ptr setup: 85 "no A0/A2-05 copy loop" (newest/
    hardest), 27 "A0-05-B1 indirect" (LDY#5;LDA($zp),Y), 8 A0-05-other, 2 LDX#5,
    1 B9, 1 BD.
  - B1 bucket FULLY RE'd on Alloyrun ($E000): source-ptr tables $e7bd(lo)/$e7c0
    (hi) indexed by subtune, copied via ($2c),Y to live pointers $e7d5. FITS
    mon_parser's existing _orderlist_ptr model (tbl_olptr=$e7bd, tbl_olptr_hi=
    $e7c0) -> a locate-SIGNATURE addition, not a model change. But freq is ALSO
    OOR for these -> need the variant's freq locate too.
Recorded in memory/mainstream-mon-tel.md (staged plan) + MEMORY.md index.
</work_completed>

<work_remaining>
## THE LIVE THREAD — mainstream MoN / Tel (SID/Tel_Jeroen), in priority order

1. **B1-indirect bucket (27 files) — the tractable first win.** Add a MISS-ONLY
   fallback to sidm2/mon_parser.py `_locate` for `A0 05 B1 <zp> 99 <dlo> <dhi>`:
   the two `BD <lo> <hi> 85 <zp>` / `BD <lo> <hi> 85 <zp+1>` feeders give
   tbl_olptr / tbl_olptr_hi (Alloyrun: $e7bd/$e7c0). ALSO locate this variant's
   FREQ table (Alloyrun freq=$8337 OOR — RE its note-formation freq read; the
   `A8 B9 .. 9D` sig likely differs) + verify pat/instr. Validate: olptr resolves
   to 3 in-image pointers/file; decode-sane; onset-validate a sample vs siddump.
   **GATE: re-validate the byte-exact wins** (bin/mon_validate on Hawkeye sub2/3
   = 152/152 & 28/28, Cybernoid sub0 = 53/53 & sub1 = 15/15, Cybernoid_II sub0 =
   37/37) — every _locate change MUST be miss-only so Hawkeye/Cyb are untouched.
   Then Stage B for the newly-covered files via bin/build_mon_native_song.

2. **The 85 "no-copy-loop" bucket** — disassemble Battle_Valley ($0810), 2400_AD;
   likely a NEWER MoN generation with a different pointer setup (the biggest RE
   unit; may need its own engine-generation handling). This is the bulk.

3. **The ~36 located-but-degenerate** — diagnose (wrong olptr resolution / grammar
   / selfmod-0-notes like Atmosphere/Bantam/Chart_Attack).

## SDI Stage B leftovers (NOT fidelity — the player is ~as-close-to-100%-as-the-
   approach-reaches)
4. Wire bin/build_sdi_native_song.py into a SHIPPING PATH (it's a standalone
   one-file-at-a-time builder). A corpus batch build + an index.
5. Bahbar-class fast-arp ~90 voices: the FM-capture ceiling; lifting needs FM-
   engine work in the SHARED bin/build_mon_native_song (risky, all players).
   Probably not worth it.

## Deenen leftovers (7 clean wins, banked)
6. whats-next #3: the $FD PORTAMENTO SLIDE (Zamzara + After_the_War's opening).
   MEASURED linear at -70/frame -> Driver 11 T0 maps 1:1 (Kimmel bin/kimmel_to_sf2
   T0 template). Extract the rate from the decoder's $FD handler, emit as T0,
   validate per-frame. Audio-only (not metric-visible). See deenen-player.md.
7. Mantalos (0/0/0, separately broken); the 9 not-located; Airwolf/Day_After
   MoN/FC locate arc (mon-locate-investigation.md).

## Long-standing tech debt
8. Vacuous-100 in pyscript/trace_comparator.py:291,341; hubbard_validate V1-only
   silently wrong on V2; SM 99.23% not reproducible from a fresh clone; Galway/
   MoN/ROMUZAK/FC matrix rows never falsifier-audited; nothing pushed to origin.
</work_remaining>

<attempted_approaches>
**SDI Stage B — the fidelity-fix sequence, each verified before the next:**
- Fast-arp voices FRAGMENTED as ties (first legato criterion `gate<0.5*notes`
  caught them) -> WRONG, 37%. The FM capture can't restart every frame. Fixed by
  the tighter criterion. LESSON: legato = "never re-gates", not "fewer gates
  than decode notes".
- A single per-part offset can't track a DRIFTING voice; but the "deep-song
  drift" on Neurotica_short was NOT drift — MAX_PART capping (tried, 700 frames)
  did NOT fix it (still 54%). The real cause was the TRUNCATED SUSTAINED TAIL
  (last note cut to +8). MAX_PART was REVERTED (unproven, forced 2_Young 1->3
  parts). DEAD END: don't cap part length for "drift".
- The scratchpad diag_weak.py DRIFTED from the build path and gave a FALSE 0% on
  Bahbar v1 (real = 92.7% via clean per-voice-offset re-measure). Don't trust it;
  the auto build's measure_parts is authoritative.
- 30s-cap sweep DISTORTS dense files (Bahbar full 99.6/76/78 vs 30s-cap 80/45/53
  — the opening is denser). Use full-song `auto`, not the cap, for real numbers.
- V garbage-SF2: with 0 onsets the shim built empty voices but STILL emitted an
  SF2 with a meaningless both-silent 85/70/91. Added the onset-agreement gate to
  REFUSE (then, for V specifically, the py65 wrapper drive replaced the refusal).

**Deenen:** the After_the_War first-note "loss" was chased as a builder bug but
is the unmodelled $FD opening slide (confirmed by siddumping the original).

**mon LOCATE "bigger prize":** it was NOT a uniform "just needs locate" set (the
framing was optimistic) — the 12 $40-class files are heterogeneous dialects; the
real win came from the instr-0 REST fix (a decode-semantics fix), not locate.

**Environment:** the SDI Stage B build regenerates shared drivers_src/*.inc
scratch (git checkout -- drivers_src/ after each build to keep the tree clean).
NEVER run two MoN/SDI-native builds concurrently (shared .inc scratch). Scratch
scans go in the session scratchpad; bin/_*.py is gitignored.
</attempted_approaches>

<critical_context>
## THE STAGE B TRACE-CAPTURE PATTERN (how SDI Stage B works — reuse for MoN Tel)
build_mon_native_song.build_native_song(shim, sid, sub, {}, [], win=(t0,t1),
traces=traces) is PLAYER-AGNOSTIC. The shim provides: voices[v] (MONEvent lists),
note_freq (PAL for onset mode via _pal), instrument(idx), frames_per_tick,
tick_to_frame, plus flags (hard_restart, snap_gate, hp_engine, tempo_toggle). It
places notes at gate-rise onsets and CAPTURES every per-frame register from the
trace. The SDI shim (bin/build_sdi_native_song.py SDIShim) is the template:
onset-aligned (fpt=1), _sem for base pitch, leading rest, last-note sustain,
legato ties, noise-aware measure_parts. build_song = adaptive part loop (caps
63/32/256/120 seqs, STEP=100); emit_one writes the SF2; measure_parts scores.

## THE V-DRIVE TRICK (for any play=$0000 self-IRQ file, incl. future MoN)
siddump AND measure_onsets choke on play=$0000. Drive the module directly via
py65 (sidm2.cpu6502_emulator.CPU6502Emulator): find the module init/play behind
the wrapper (the wrapper init's `JSR base; CLI`), then call init once + play x
mult per frame, snapshotting $D400-$D418. That py65 trace IS the ground truth;
the emitted SF2 (real play addr) is siddumped and compared. See v_traces() /
_v_module_addrs() in bin/build_sdi_native_song.py.

## HONEST METRIC LESSONS (this session, repeatedly)
- A validator that POOLS evidence proves only a value exists in the universe
  (the Deenen pooling flaw: green while the SF2 was missing voice 2 + 1.5x fast).
- A noise frame has NO pitch — score it on the waveform, not freq-semitone.
- Exact per-frame semitone over-penalizes fast modulation with phase jitter
  (Deenen percussion prefix-agreement; SDI ±1-frame only partly recovers arps).
- A ground-truth tool certifies only what it WATCHES (the freq byte-swap: engine-
  check read 100/100/100 while every emitted frequency was wrong).
- "builds != sounds right": ALWAYS get a fidelity number before claiming a build
  works; refuse to emit when you can't measure (the V garbage-SF2 gate).

## KEY FILES
- bin/build_sdi_native_song.py — NEW, SDI Stage B (the whole ARC 2). SDIShim,
  v_traces, _v_module_addrs, build_song, measure_parts, _sem, _pal, _fidelity.
- sidm2/mon_parser.py — _locate (EXTEND for MoN Tel B1 bucket, MISS-ONLY),
  _emit (the instr-0 _silent_instr fix), _orderlist_ptr (the model B1 fits),
  _decode_voice_v (the _v_tempo lazy-init fix).
- sidm2/sdi_parser.py — SDIModule, decode_voice (A/B/C/D/E/V), lay.v_mult,
  lay.freq_lo/hi, instrument tables; the _v_tempo lazy-init.
- bin/build_mon_native_song.py — the shared native engine (build_native_song,
  emit_one, filter_trace, prune_stale_parts). SHARED — mind Hawkeye/Cyb.
- bin/deenen_to_sf2.py — build_song, tempo_chain, dropped_orderlist, voice_rows
  (stop_on_loop=True), _wave_program. bin/deenen_sf2_validate.py — the rewritten
  per-voice validator.
- sidm2/dmc_parser.py measure_onsets(d,la,init,play,frames,within_frame) — the
  player-agnostic gate-rise onset detector.
- docs/players/SDI.md, MON.md, DEENEN.md — all updated this session.
- MEMORY: mainstream-mon-tel.md (THE NEXT ARC), gallefoss-sdi-player.md (SDI
  Stage B full record), deenen-player.md, mon-locate-investigation.md.

## ENVIRONMENT
- Tests: `py -3 -m pytest pyscript/ -q` -> 1561/7/2 (~3.5 min).
- SDI Stage B build: `py -3 bin/build_sdi_native_song.py <file> auto` -> out/sdi/.
- MoN validate: `py -3 bin/mon_validate.py <file> <sub>`.
- Deenen: `py -3 bin/deenen_validate.py` (corpus), `bin/deenen_sf2_validate.py`.
- Tel coverage scans: scratchpad/tel_coverage.py, tel_buckets.py.
- core.autocrlf=true — CRLF warnings on commit are cosmetic.
- After any native build: `git checkout -- drivers_src/` (regenerated scratch).
</critical_context>

<current_state>
- **v3.21.0 unchanged** (correct — bug-fix/RE, no release milestone).
- **17 commits on master this session, NONE pushed.** Working tree CLEAN except
  the pre-existing untracked corpora + local .claude/settings.local.json.
- **Tests 1561/7/2.** No known failures.
- **DEENEN: 10/19 located, 7 CLEAN WINS** (was 6). Emitted SF2s now correct
  (tempo + all voices); melodic+percussion audio-validated per-voice.
- **MoN: Double_Dragon + Zynon now decode EXACT** (instr-0 rest fix); Cybernoid
  sub0 improved to 53/53. Hawkeye/Cyb byte-exact wins UNCHANGED.
- **SDI STAGE B: COMPLETE for all 6 variants**, most voices 98-100%. Standalone
  builder (bin/build_sdi_native_song.py), NOT wired into a shipping path yet.
  Lone residual: Bahbar-class fast-arp ~90 (FM-capture ceiling).
- **MAINSTREAM MoN / TEL: OPENED, RECON DONE, 0 code.** 19/179 decode; variant
  map built; B1 bucket (27) RE'd + fits the model. NEXT: implement the B1
  miss-only locate + freq, validate vs the byte-exact wins.
- **NEXT SESSION SHOULD START WITH**: memory/mainstream-mon-tel.md, then
  work_remaining #1 (the B1-indirect locate for the 27-file bucket) — the
  most tractable first win of the mainstream-MoN arc. Corpus-gate against
  Hawkeye/Cyb on EVERY _locate change.
- **OPEN QUESTION for the user**: I asked whether to implement the B1 locate now
  (shared-code risk) or treat the recon as a checkpoint. Awaiting direction; the
  arc is at the reconnaissance beachhead.
</current_state>
