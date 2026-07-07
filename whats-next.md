<original_task>
Mission: tools that combine static code + AI to convert any SID into an SF2 at
99% fidelity playback and 100% editable. This session arc: complete Hubbard V1
(HP pulse engine to default, no-release ties, subsongs, compilation rips) and
open+largely-crack Hubbard V2 (the "64 unparseable" files).
</original_task>

<work_completed>
ALL COMMITTED AND PUSHED through b9594d2. The day's chain:
3857c1c HP pulse engine complete -> default (Monty/Commando/Zoids pulse 100)
b7bf3d4 no-release (bit5) chains = ties (killed the audible 2-frame chop)
7979e19 ADSR re-arm ON the fetch frame (dropped the 1-frame-early HRC pre-arm)
81f1fd9 compilation rips (5_Title_Tunes = 5 embedded players) + track-loop expansion
4a8d7f1 V2 wave 1: widened freq sigs + split-songs tables (8 new files 97-100%)
076fa2b V2 wave 2: the fractional-tempo SWALLOW counter decoded (10 more files)
bd8427a measure_tick_schedule on the siddump CPU (idiom-immune tick grid)
c42f8e7 native TEMPO_SWALLOW driver flag -> Delta first V2 native build
7a1a4de the silent-Delta fix + the VACUOUS-100.0 fidelity bug (secs=0 -> n=-4!)
eded980 v2 NOTE format (4-byte porta/1-byte rest/pitch-bit7 no-fetch) + v2 TRACK
        repeat counts -> ALL Delta subsongs 100% onsets; theme s11 built+delivered
9cacf36 Delta pulse 100.0 (v2 fetch RESETS pulse; PFREE now v1-only) + periodic
        pulse LOOP rows + tie-chain-spanning capture
d4bb79e corpus runner v2-aware; 29 files / 64 validating subsongs
b9594d2 Last_V8 batch-killer fixed (HPReplay on siddump CPU: 3h->27s) +
        init-seeded per-voice instruments (Last_V8 pulse 3/100/48 -> 100/100/100)

HONEST STATE (real windows; the vacuous secs=0 bug is fixed and guarded):
- Monty p1 100/99.8/100 + filter 100; VICE dump residual 1.38% (drum parity).
- Delta theme (s11, PSID default): freq/pulse/filter 100.0 all voices; wf 85-96
  (tremolo/noise-blip ordering = last texture item). User-delivered as WAV.
- Last_V8 p1 100/100/100 after init-instrument fix.
- Hawkeye sub3 (MoN regression) 100.0 — its TRUE length is 2.5s ($FE halt);
  longer windows over-run into loop-vs-halt divergence (measurement trap).
- Corpus batch (29 files/64 subsongs) running detached, PID in session.
</work_completed>

<work_remaining>
1. Corpus batch completion + spot-measure v2 part1s with REAL windows; report.
2. Delta wf texture (85-96): per-note wave capture vs the noise-blip multiplex
   (specific notes carry an $81 noise frame; canonical wave programs uniform).
3. V2 laggards: IK_plus (V0 decode runaway + percussion pitch bytes), Thundercats
   68% (note-format), Tarzan (speed addr misdetected; play needs raster fake),
   Mega_Apocalypse (runaway), Knucklebusters (per-voice speed), Game_Killer
   (tick stretch every 10 frames with NO swallow sig — wire measured schedule
   into shim grid + poke an approximated period/phase), 6 no-sig files
   (Casio_Extended cluster), Samantha_Fox/Kings_of_the_Beach etc. partials.
4. Editor '???' rows: $7D hard-restart + out-of-range notes are display-only
   artifacts in SF2II — consider a friendlier encoding.
5. Part-count compression for dense tunes (Delta s0 = 2s parts at the 63-bundle
   cap; the ARP_STRUCT structural path packs it into ONE part but its canonicals
   misfire on Hubbard — port the good prongs).
6. CLAUDE.md/CHANGELOG/STORY version bump (v3.14.0: the Hubbard v1+v2 arcs).
7. Next players (user priority): Soundmonitor (bin/sound monitor/ = user's
   reference), MoN/Deenen (Robocop3/Turrican).
</work_remaining>

<attempted_approaches>
- mon_part_fidelity secs=0 was VACUOUSLY 100.0 (n=-4, empty loops) — a silent
  SF2 measured perfect. Fixed: secs<=0 defaults 20s + hard error on empty
  window. NEVER trust a fidelity number without knowing its window; part
  windows must match (song length for jingles; off0 = part start).
- Blanket MON_ARP_STRUCT=1 on Hubbard: packs Delta whole-song into 1 part but
  canonical wave/pulse misfire (2.0% pulse) — port prongs selectively.
- Bare-py65 call harnesses: THREE Hubbard rips (Tarzan, Last_V8, +) spin
  without the raster fake -> use sidm2.cpu6502_emulator with $D012 increment
  (see measure_tick_schedule/HPReplay/initial_instruments/swallow_state).
- Background Bash tasks die at a 10-min cap; cProfile on a slow build never
  returns. Long batches: PowerShell Start-Process detached + log file. ONE
  heavy job at a time (CPU contention made 25s builds take 90+ min = the
  fake 'hangs').
</attempted_approaches>

<critical_context>
- V2 FORMAT (all RE'd from Delta $BE79-$BF9A, per-file signature-gated):
  split lo/hi songs tables (X=song*3+voice); swallow counter (skip speed dec
  every Nth frame; sig CE../10../A9 v/8D same/4C; phase=post-init counter via
  py65); v2 notes ($60-len 1-byte rest, 4-byte porta, pitch bit7 = no-fetch
  tie); v2 tracks ([pat,cnt,pat,cnt...] repeat counts); fetch RESETS pulse
  from the record (no PFREE); per-voice init instruments (instrnr sig).
- Driver: TEMPO_SWALLOW (SWC $19CC/SWP $19CD poked; SWP==0 = off — an unpoked
  driver previously swallowed EVERY tick = silence); HP state $19C0-$19CB +
  HPMAP $19E0 (NEVER below $1940 — the out-of-line code region $1890-$193C).
- Fidelity rig: mon_part_fidelity PART SONG SECS OFF0 (secs REQUIRED-ish,
  window must fit the song/part); VICE dump diff = ADSR/$D418 truth; VICE
  dump regs/values are DECIMAL.
- HP engine v1-only (v2 instrument records unknown layout — HP pokes would
  read garbage; v2 uses captured programs which measure 100 anyway).
- The corpus runner: bin/hubbard_build_all.py (29 files; sequential;
  TimeoutExpired-proof). Launch detached via PowerShell; log out/_batch_all.log.
</critical_context>

<current_state>
Working tree clean at b9594d2 (pushed). Corpus batch running detached
(check out/_batch_all.log). SF2II may still be open with Delta part1 loaded.
User's ear-driven acceptance: Monty "very good 99%" -> chop fixed; Delta
theme delivered after the wrong-subsong catch (user: "delta is song 12 of
13") — awaiting the user's verdict on the re-render with pulse 100.
</current_state>
