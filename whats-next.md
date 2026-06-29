<original_task>
Reverse-engineer the Hawkeye music player (Jeroen Tel / "Maniacs of Noise" / MoN engine)
and build a SID->SF2 converter for it (the player after ROMUZAK). Standing goal: notes
correct, song-order correct, then SOUND FIDELITY via a native SF2 driver that loads in
stock SID Factory II. The user iteratively asked to: convert/confirm subtune 3, then
subtune 2, then push fidelity ("keep pushing" -> they chose the NATIVE DRIVER route over
Driver-11-tables or embed), then convert subtune 0. Target: SID/Tel_Jeroen/Hawkeye.sid.
</original_task>

<work_completed>
STAGE A (editable Driver-11 SF2) — DONE earlier this session, USER-GUI-CONFIRMED for
subtunes 2 & 3 ("right tune, order and notes correct, but fidelity is not"):
- `sidm2/mon_parser.py` decodes the MoN two-level orderlist->pattern format, frame-exact.
- `bin/mon_to_sf2.py SID out.sf2 SUB` -> editable Driver-11 SF2. Validators
  `bin/mon_validate.py` (parser vs siddump) + `bin/mon_sf2_validate.py` (SF2 round-trip):
  sub3 28/28 onsets, sub2 174/174, all EXACT. 9 tests (`pyscript/test_mon_parser.py` +
  `test_mon_to_sf2.py`).

STAGE B (NATIVE DRIVER, the user's chosen fidelity route) — the bulk of this session:
- `drivers_src/mon/` = copy of the ROMUZAK/Galway native SF2 engine (player-agnostic
  runners: SF2 sequencer + wave_step + pulse_step + filt_prog_step + per-frame FM pitch).
- `bin/build_mon_native_song.py` feeds the MoN decode + per-note programs (all extracted
  trace-driven from the original via siddump) into the driver tables. Reuses the shared
  pipeline via `B.GAL = drivers_src/mon` redirect (B = bin/build_romuzak_driver_full.py;
  RN = bin/build_romuzak_native_song.py).
- `bin/mon_fidelity.py` = headless per-frame register fidelity metric (freq/wf/pulse/
  filter) vs the original. THE iteration loop.

  Milestones (all committed):
  * B1 — MoN's OWN freq table (fixed `note_freq`: the table is SPLIT, lo bytes $8337[note]
    + hi bytes $8396[note], NOT interleaved; located both via signatures). Byte-EXACT
    tuning (no Driver-11 detune). Native driver has NO boot offset (Driver-11 had +5).
  * B2 — per-NOTE FM bundles via the $c0-$ff COMMAND channel. Each note carries a command
    selecting an (FM program, pulse program) bundle. `fm_program_for`: offset[k] =
    (trace_freq[k] - note_freq) & 0xFFFF, RLE'd deltas; reproduces slides AND arps
    byte-exactly. KEY 1-frame fix: the driver's pr_note holds base pitch on the trigger
    frame (FM_CNT=1), so the FM program DROPS delta[0] (starts at frame 1).
    `gen_includes_song` (in RN) gained a `bundles` param (command-indexed IFM+IPULSE).
  * B3 PULSE — `pulse_program_for` (8X set frame 0 / 0X per-frame 12-bit add / 7f freeze;
    NO 1-frame offset, pr_note resets VPC=0). Driver fix (drivers_src/mon only):
    `set_instr_v` no longer writes VIPUL (tokens pack [command][instrument], so set_instr
    ran AFTER the command and clobbered the bundle's pulse). Use RAW MoN waveform
    (record[1], e.g. $43 pulse+sync) — `_norm_waveform` stripped $43->$41.
  * B3 WAVE/gate-envelope — per-note wave programs as DISTINCT INSTRUMENTS ($a0-$bf). The
    waveform attack/gate-off ($43->$42 / $41->$40) varies per note via the $7x wprog (same
    per-note nature as arps), so it's captured per note and deduped into instruments
    (wave_step advances 1 row/FRAME, writes col0 to $D404 with VGMASK=$ff on a note).
  * B3 FILTER — the global resonant filter. `filter_trace` (per-frame cutoff
    ($D415&7|$D416<<3) + ctrl $D417). `_filt_set_row` (set-row per frame: passband Low,
    $D416=cutoff>>3, res=ctrl). `filt_is_restart` = cutoff STABLE then CHANGES at a note
    boundary (start value HIGHER OR LOWER — the earlier "upward jump" rule missed lower
    starts). Each global restart assigned to ONE voice (filter is global; voices share
    onset frames) -> no over-flag. `gen_includes_song` gained instr_flags + filter_programs
    (lays the col-major FILTER table + col2 $40 + col3 VIFILT row).

  RESULT: subtune 2 AND subtune 3 = freq + waveform + pulse + FILTER ALL 100% BYTE-EXACT
  on all 3 voices, FULL song length. Single editable SF2 each. USER-SAVED:
  out/hawkeye_subtune_2.sf2. (out/mon/Hawkeye_sub{2,3}_native.sf2 are the build outputs.)
  Earlier a "trace the FULL song length" fix landed (the per-note programs were extracted
  from a fixed -t10/500-frame window -> notes past 10s got degenerate held programs =
  "sound goes bad after 10s"; subtune 2 is 1536 frames/30.7s).

CLUSTERING + WINDOWING for dense/long tunes (subtune 0):
- `greedy_cluster` (nearest-merge: fuse the two whose merge costs least = per-item distance
  * smaller item's note count). Bundle distance = FM-contour L1 (`_fm_curve`) + pulse
  penalty; instrument distance = AD/SR + waveform + wave-program + filter diffs.
  `build_native_song` is now two-pass (collect exact bundles/instruments with counts ->
  cluster -> emit). UNDER the caps, greedy_cluster is identity (2/3 stay byte-exact).
- WINDOW SPLITTING: `build_native_song(... win=(t0,t1), traces=...)` clips notes to the
  frame window, positions the first note with a leading rest (note 0 = gate off), shares
  ONE trace across all windows. `main()`: 3rd CLI arg WINSEC -> emits one SF2 per window
  (`emit_one` factored out). `py -3 bin/build_mon_native_song.py SID 0 30`.
  Subtune 0 (the ~6.4-min main theme, ~6000 notes: V0 1713 / V1 3052 / V2 1209).
- ADAPTIVE WINDOWING (the user's chosen fix for "13 files is clunky") — `... SID 0 auto`
  grows each window to the LARGEST span whose PRE-cluster resource counts still fit ALL
  caps, so every part stays clustering-free + overflow-free = byte-exact, with the FEWEST
  files. Caps probed via a cheap `count_only=True` path on `build_native_song` (pass-1 +
  a faithful pass-2 segment count, NO clustering/assemble): <=63 bundles, <=32 instruments,
  <=256 WAVE rows, <=256 FILTER rows, and <=120 SEQUENCES. The sequence cap was the subtle
  one: the native seq-pointer table (SEQPTRLO $1a06 / SEQPTRHI $1a86) holds 128 entries and
  voices are laid in order, so >128 total sequences silently corrupts the LAST voice (osc3)
  — a 106s window gave osc3 27% until this cap was added. RESULT: subtune 0 -> **8 parts**
  (was 13). Per-part fidelity (`bin/mon_part_fidelity.py PART SUB SECS [START_SEC]`, which
  wraps a windowed part as a native PSID play=$1003 and aligns to the original at START_SEC):
  part 1 (0-88s) osc 100/100/100, osc3 99.8/97.8/99.3; part 5 (densest, bundles=63) 99.5-
  99.8%; part 8 98.9-100%. NO clustering loss. FILTER still the seam issue (60-87%/part —
  longer windows accumulate more global-filter drift; this is open issue #1, unchanged in
  nature). out/mon/Hawkeye_sub0_partNN.sf2.
</work_completed>

<work_remaining>
1. SUBTUNE 0 FILTER — RESOLVED (60%->92-98%). The filter was RE'd to a per-instrument
   cutoff ENVELOPE (FCTRL=$90F6,X frame counter reset on note-on -> threshold/delta table;
   see memory/hawkeye-mon-filter-engine-re.md). build_mon_native_song.py now generates the
   envelope as a SET + ADD-row filter program (`filter_program_for` + `_filt_add_row`),
   detects restarts as envelope ATTACKS mapped to note-ons (`detect_filter_drives`), and
   uses ONE canonical (longest-gap) program per driving instrument so they dedup.
   Part fidelity: part1 98.2%, part5 95.4%, part8 92.2% (was ~60-75%); sub2/sub3 stay 100%
   byte-exact. RESIDUAL ~2-8% = multi-voice last-wins ($D416 written by >1 voice/frame, a
   capped voice briefly winning) — would need per-voice filter programs in the driver (big
   change, mostly-inaudible single-frame blips); the single-global-program model tops out
   here and the sweep is now correct.
2. SUBTUNE 0 UX: DONE for the editable route — adaptive windowing (`... SID 0 auto`) cut
   13 -> 8 files with zero fidelity loss (see ADAPTIVE WINDOWING above). Further reduction
   would need a non-editable single embedded-player SF2 (the user chose to keep it editable),
   or fixing the filter seam so even larger windows stay clean.
3. GENERALIZE: batch all 12 Hawkeye subtunes; then the 179-tune Tel_Jeroen corpus
   (signatures relocation-safe; subtunes 6-11 use a $92xx subtune-block COPY path at init
   that the parser does NOT yet emulate — it only reads the in-place $7B(83FC) sets for
   subtunes 0-5).
4. GUI-CONFIRMED (2026-06-29): sub0 parts LOAD + PLAY in real SF2II. `bin/mon_sf2ii_confirm.py
   PART SUB SECS [START_SEC]` captures the instrumented SF2II_dbg's actual per-frame SID
   output (argv-load + auto-play) and diffs vs the original. Part1: freq/wf/pulse 100/100/100
   (osc3 99.8/97.6/99.2), FILTER 98.7%. CMP-BUG FIX needed first: filt_prog_step dispatched
   add-rows via `cmp #$90; bcs` — SF2II's 6510 miscomputes carry when |A-op|>$7f, so $0x add
   rows (vs $90) were misread as set-rows -> filter 1.6% in real SF2II. Fixed to a bit7 test
   (`lda FILTER,y; bmi fp_set`), mirroring pulse_step. See [[sf2ii-cmp-carry-bug]].
</work_remaining>

<attempted_approaches>
- OPTION 1 (arp-as-semitones) — TRIED AND REVERTED. Idea: encode arps as wave-table
  semitone offsets (col1, transposable) instead of absolute-freq FM bundles, to reduce
  bundle count for dense tunes. It REGRESSED the byte-exact subtunes: it shifted the
  bottleneck from command slots to instrument slots (sub2 instr 22->32) and dropped sub2
  freq to 91% (the waveform envelope still fragments the "shared" arps, so they didn't
  dedup as hoped). Reverted via `git checkout bin/build_mon_native_song.py`. The code is in
  the git history of the reverted change (functions `_semis`, `_wave_seq`, `_loop_pairs`,
  `pitch_and_wave`) if ever revisited — but it is NOT a clean win.
- SINGLE-FILE CLUSTERED subtune 0 — TRIED, POOR. 241 bundles + 65 instruments clustered to
  63/32 lost too much (osc3 freq 55%, pulse 1%) AND overflowed the $D000 memory wall
  ($D600). Window-splitting (option 2) is far better. (The single-file build still exists
  as out/hawkeye_subtune_0.sf2 — it is the BAD clustered one; the good ones are the parts.)
- WINDOWED build was initially SLOW (re-traced the full 384s song via siddump for EVERY
  window = 13 full siddumps). FIXED by tracing once in main() and passing `traces=` into
  build_native_song. (A stale background task from the slow version may still report
  completion — ignore it.)
- The "upward jump" filter-restart detector missed restarts where the new sweep starts
  LOWER than the held cutoff (subtune 2 frame 775: 0700->0500). Fixed to "stable then
  changes". Then it missed the song's FIRST restart (frame 1, needed R>=2); fixed with an
  R==1 special case.
</attempted_approaches>

<critical_context>
- TARGET: SID/Tel_Jeroen/Hawkeye.sid (PSID load=0 -> $7AE0, init $7AE0/play $7AE3, 12
  subtunes). MoN note byte == siddump abs-note (chromatic, $00=C-0); pitch_base 0.
- Parser facts (sidm2/mon_parser.py): tempo = speed+1 frames/tick; duration STICKY ($90CE),
  note=(b&$3F) ticks; $FE orderlist = SONG-END HALT; $FF = loop point; $40-$5F orderlist =
  pattern REPEAT counter (N+1 plays). Instrument = 8-byte record $860C+idx*8, idx = $Cx byte
  ($90DA). $7x byte = wave-PROGRAM select (the per-note arp/waveform). Freq table SPLIT:
  lo $8337[note] / hi $8396[note]. `MON._voice_blocks(v)` = per-pattern segmentation.
- NATIVE DRIVER ENGINE (drivers_src/mon/romuzak_driver.asm; B=build_romuzak_driver_full):
  EVERYTHING per-frame is trace-driven, no MoN engine port. The $c0-$ff COMMAND channel
  selects a (FM, pulse) bundle per note (pr_setprog -> IFM/IPULSE -> VIFM/VIPUL). The
  $a0-$bf INSTRUMENT selects AD/SR/waveform + the wave program (per-note via distinct
  instruments). The FILTER is one GLOBAL resource restarted per note by a flag-$40
  instrument (pr_note: VIFLAGS&$40 -> F_IDX=VIFILT, F_CNT=0, F_ACT=1).
- DRIVER TIMING GOTCHAS: FM applies row 0 at frame 1 (pr_note holds base on the trigger
  frame, FM_CNT=1) -> FM program drops delta[0]. PULSE + WAVE + FILTER apply row 0 AT the
  onset frame (no 1-frame hold) -> capture from k=0. wave_step advances 1 row/FRAME (NOT
  per tick). MoN driver `set_instr_v` was edited to NOT write VIPUL (the command owns pulse;
  set_instr runs after the command in token order [command][instrument]).
- HARD LIMITS: $c0-$ff = 64 command bundles, $a0-$bf = 32 instruments, FILTER/WAVE tables
  256 rows; the $D000 memory wall caps total SF2 data. Dense/long tunes MUST cluster
  (lossy) and/or window-split. Subtunes 2/3 fit; subtune 0 does not.
- FIDELITY MEASUREMENT: build the SF2, wrap as a PSID probe (init=$1000, play=$1003 for the
  NATIVE driver; Driver-11 SF2 uses play=$1006), siddump both, compare per-frame registers
  via `mon_fidelity.per_frame`. MEASURE OVER THE REAL SONG LENGTH (subtune 3 HALTS at $FE
  ~frame 128 and the native driver LOOPS, so a long window mis-scores). Subtune 0 song span
  = max-voice sum(dur)*fpt = 19200 frames / 384s.
- LOAD GOTCHA: argv file-load (`SIDFactoryII.exe file.sf2`) crashes ~3/4 (the known SF2II
  argv Heisenbug — reproduces identically on known-good ROMUZAK SF2; exit 0xC0000409). Load
  via `py -3 pyscript/sf2_open_in_editor.py out/X.sf2 40` (spawns SF2II empty + drives
  F10-load with retries). Loading FROM the editor is reliable.
- COMMANDS: build native whole-song `py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/
  Hawkeye.sid SUB`; windowed `... SUB WINSEC`; tests `py -3 -m pytest pyscript/
  test_mon_parser.py pyscript/test_mon_to_sf2.py -q` (9). 64tass assembles the driver
  (build_romuzak_driver_full.assemble). Use the Bash tool with a heredoc + `git commit -F
  file` (PowerShell @'...'@ here-strings fail in the Bash tool).
- MEMORY: memory/hawkeye-mon-player-re.md (full RE + B1/B2/B3 + the filter mechanism) +
  MEMORY.md index entry, both updated through the filter milestone (not yet updated for the
  clustering/windowing of subtune 0).
- REUSE: bin/build_galway_trace_song.py has `cluster_bundles` (the original nearest-merge
  with pulse-audibility weighting) if greedy_cluster needs to get smarter.
</critical_context>

<current_state>
- Subtunes 2 & 3: COMPLETE. Single editable native-driver SF2, freq+wf+pulse+filter all
  100% byte-exact, full length. out/mon/Hawkeye_sub{2,3}_native.sf2; out/hawkeye_subtune_2.sf2
  saved per user request. User confirmed sub2 "very close" / "this is good" before the
  filter; the filter then landed it at 100%.
- Subtune 0: ADAPTIVE WINDOWING -> 8 parts (was 13), `py -3 bin/build_mon_native_song.py
  SID/Tel_Jeroen/Hawkeye.sid 0 auto`, out/mon/Hawkeye_sub0_partNN.sf2. Pitch/waveform/pulse
  ~100% per part (verified parts 1/5/8 via bin/mon_part_fidelity.py); FILTER 60-87% (open
  issue #1). Each part clustering-free + under all caps + memory. (out/hawkeye_subtune_0.sf2
  = the OLD single-file clustered build = BAD, ignore/replace. The fixed-30s `... 0 30` path
  still works if needed.)
- All code committed on master (latest: the windowing commit). Working tree clean except
  out/* artifacts (gitignored) + pre-existing untracked binaries. 9 tests green; ROMUZAK
  native build re-verified unaffected by the shared gen_includes_song changes.
- An SF2II instance may be open from a prior load (PID varies). The stale background-task
  notification (b4gk9fmcp) is the superseded slow windowed build — ignore.
- Open question for the user: push the sub0 filter seam higher, use larger windows for
  fewer files, or move on (batch other subtunes / the corpus).
</current_state>
