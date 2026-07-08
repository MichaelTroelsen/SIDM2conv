<original_task>
Standing mission (project): tools combining static RE + AI to convert any SID into an
SF2 at 99% fidelity + 100% editable. User's player priority (memory/new-player-priority):
1. Rob Hubbard (DONE, shipped v3.14.0), then Johannes Bjerregaard / DMC.

This session's explicit user tasks, in order:
1. "complete hubbard then start Johannes" — finish the Hubbard V2 arc, then begin the
   Johannes Bjerregaard corpus (SID/JohannesBjerregaard/, 88 files).
2. "can i hear rockbuster in sf2" -> "render rockbuster to wav and then continue with
   building the converter" — the DMC converter is the active work.
3. A chain of "continue"/"go on" driving: DMC format RE -> parser -> decoder -> native
   Stage B -> onset-fidelity work. Specific sub-requests: "fix the $C0 decode to tighten
   onsets", "do the emulated onset schedule", "do the wavetable-arp decode".
STANDING RULE (memory/feedback-accuracy-over-speed): max accuracy; never ship lossy
silently; the USER'S EAR is the final acceptance metric (it caught 3 Hubbard defects
the % metrics missed). NEVER use pyscript/sf2_open_in_editor.py — its PyAutoGUI types
the filename into the user's active window (garbled their input; they said "stop trying
to load it"). Load SF2s manually.
</original_task>

<work_completed>
=== HUBBARD V2 COMPLETED + SHIPPED v3.14.0 (earlier in session) ===
Commits: aaf1811, 5c0de20 (state-region), 43ad2d2 (pulse), 39dd3aa (TEMPO_SCHED),
10f59cb/776e5f5/8f93029 (docs). Highlights:
- State-region overflow (7 V2 swallow files crashed): root cause = the driver's 4 tail
  data tables (sidbase/frbits/ollo/olhi, 12B) overflowed 1 byte into $16CC (SF2II
  pinned state). Fixed by relocating them to `* = $1703` (the free $1703-$170F gap).
- V2 pulse: gated hp_engine=0/freerun_pulse=1 for any swallow file (not just v2_notes);
  Lightforce pulse 0.5->100. All 7 swallow files: pulse/wf/filter 100%, freq ~86%.
- TEMPO_SCHED driver mode added (per-frame stretch bitmap, SCHEDTAB $1940). Gated to
  no-swallow-sig files (Game_Killer 22->50). Swallow files keep the swallow path.
- Docs: docs/players/HUBBARD.md, NATIVE_DRIVER.md, HUBBARD_V2_PLAN.md; STORY.md
  v3.14.0; CLAUDE.md/CHANGELOG.md. __version__ = 3.14.0.
- Honest open items (memory hubbard-player-re.md): swallow freq ~86% = FM-during-hold
  (note-trigger timing under the tempo stretch, NOT tempo grid); spin class
  (Devils_Galop/I_Ball/Wiz); 6 no-sig files; ~7 note-format laggards.

=== JOHANNES BJERREGAARD / DMC — FULL ARC THIS SESSION ===
DMC = Demo Music Creator. Ground truth: ~/Downloads/dmc4editor11_win64.zip (its
ReadMe.txt: "the famous DMC4 Player written by Brian/Graffity in '91"). 88 files, ~all
Bjerregaard. DMC is one of the most-used C64 formats -> a parser generalizes across
much of HVSC. Full format map in memory/johannes-bjerregaard-player.md.

FORMAT (RE'd from Balloon.sid play body via disasm + py65, all addrs for load $1000,
RELOCATABLE so signature-located):
- Model: Track (orderlist) -> Sector (pattern) -> Sound (instrument).
- Tempo: DEC tempo/BPL/LDA #imm/STA -> fpt = imm+1 (per-tune, baked in code).
- Track per voice: ptr $104A/$104D,x, bytes=sector#; $FF=loop, $FE=end.
- Sector-ptr table $1900(lo)/$1980(hi) indexed by sector#.
- Sector event: cmd byte (dur=low5, bit5 flag, bit6=2 effect bytes, bit7=sound byte);
  (cmd&$E0)==$C0 = REST (dur, no note, 1 byte); then pitch byte; $FF ends sector.
- Sound: 8 bytes $1500 [AD,SR,PWinit,PWrails(lo/hi nibble=min/max),PWspeed,vib,filt6,
  flags7]. PWM engine + vibrato (per-voice 16-bit acc $1011/$1014) + filter ($D417).
- Freq table $135F INTERLEAVED lo/hi (note*2). DMC plays notes ABOVE its own table via
  octave-shift; the freq ROW comes from the WAVETABLE, not the raw note byte.
- WAVETABLE $1A00(arp)/$1B00(waveform): per-frame advance -> fast ARP. $1A00 byte =
  $80|note (ABSOLUTE note index; $DF->95, $AE->46, $A3->35, $BD->61 verified),
  $00=hold, $7E/$7F=loop. Per-sound start from the sound record.
- All SID writes at the emit block ($1314+): $1011/$1014->$D400/1, $1036->$D404(wf),
  $100B/$100E->$D402/3(pulse), $D416/$D418(filter).

CODE DELIVERED (all committed + pushed):
- sidm2/dmc_parser.py (26fd05b/47e93d6/d935241/5a59f6e): signature-located tables
  (sector/sound/freq/track, relocation-safe, works on 44/88 files); DMCNote dataclass;
  decode_track/decode_sector/decode_song (track->sector->note, $C0-rest, $FF loop/end);
  tempo detection = the GLOBAL counter (never indexed ,x/,y — excludes per-voice
  waveform counters; d935241); measure_onsets (siddump CPU6502Emulator + $D012 raster
  fake + banking; per-voice $D404 gate-rise frames).
- pyscript/test_dmc_parser.py (5fe1e0c): 6 tests, all green (Balloon addrs, relocation
  on Cant_Stop, chromatic freq table, track termination, decode, onset >=90%).
- bin/build_dmc_native_song.py (e086b03/d38a0fb/360a1f4): DMCShim -> the shared
  build_mon_native_song pipeline. TWO modes: (a) ONSET-ALIGNED (default when emulated
  onsets agree >=85% with siddump): fpt=1, one MONEvent per emulated gate-rise, dur=
  frame-gap, pitch = trace-resolved absolute semitone (_sem = freq_to_semi(trace freq
  at onset+1) -> note; note_freq = PAL table _pal, full 0-95 range); (b) tick-grid
  fallback (tick*fpt, decode pitch) for legato/multispeed/self-IRQ variants.

VALIDATION RESULTS:
- Onset decode (siddump vs decode, per-voice phase): 29/43 main-player files >=90%
  (was 25 before the tempo fix). 20 at >=95% (Dummy_II 100, Blobby/Jazz_1 ~99).
- Native fidelity (the WIN): Rockbuster freq 65->97, wf 87->100, pulse 100/100/100 via
  the emulated onset schedule. Rendered out/Rockbuster_native.wav (played for user).
- Onset-agreement survey: 21/43 files pass the >=85% check (INCLUDING several decode-
  FAIL "variant" files — MSI_Demo/Billie_Jean/Namnam/Some_Soul — because onset-align is
  decode-INDEPENDENT for pitch/timing). Most build 2/3 voices at 90-100%.

OTHER: rendered out/Rockbuster.wav (original SID, 90s) so user could hear the tune.
Built a minimal-embed SF2 (out/dmc/Rockbuster.sf2) that PLAYS byte-identical to the
original (900/900 voice-frames over 6s) BUT CRASHES SF2II on load (embed stopgap for a
$A000 player — not worth fixing; the native converter is the path).
</work_completed>

<work_remaining>
DMC next steps (REVISED — the wavetable-arp model was tried and is a DEAD END):
1. **WAVETABLE-ARP SEMITONE MODEL: DEAD END, do NOT retry.** Implemented + tested
   2026-07-08: a per-event FM override hook (build_mon_native_song._arp_fm_for ->
   m.fm_arp_program) + DMCShim semitone-hold arp programs from the trace. REGRESSED
   (Rockbuster osc3 93->75, Omega 40/41->16/6, Wanna v1 unchanged). Semitone-hold
   entries play freqtable[base+S] = quantized-to-semitone in PAL tuning, but DMC's
   freq table isn't PAL and arp steps aren't on-semitone -> strictly LESS exact than
   the Hz-delta capture, which already reproduces DMC's per-frame freq bit-for-bit.
   The Hz-delta onset-aligned capture is the RIGHT representation. Reverted; memory
   documents this.
2. **PER-VOICE ONSET/STRUCTURAL residual** is the real remaining problem (NOT the
   arp): Wanna v1 = 33% under BOTH the Hz-delta AND semitone representations, so its
   issue is invariant to the FM encoding — it's onset placement or a structural decode
   issue in that specific voice. Next: diagnose Wanna_Get_Sick osc1 concretely — dump
   its emulated onsets vs the trace's actual osc1 onsets (are notes placed at the
   right frames?), and whether the trace-resolved base note (_sem) is right. The four
   onset-detection approaches (gate-rise/pitch-step/debounce/global-schedule) are all
   exhausted (see attempted); the remaining path is per-voice diagnosis, not another
   global onset heuristic.
3. **MULTISPEED / SELF-IRQ variants** (Chase, Dummy_II): the 1x py65/siddump-CPU replay
   reads them wrong (Chase 4x too slow). PSID speed flag is 0 yet they play denser ->
   the PLAYER self-installs faster timing. Detect + emulate at the right rate (Hubbard's
   raster-fake approach partially helped; multispeed call-N-per-frame did NOT — tested).
4. Decode variants: ~14 files where signatures mislocate (the "0% variant" cluster
   Billie_Jean trk=$1440=code region) or the 70-90% desync remains — but onset-align
   already covers many of these, so lower priority.
5. Build the full corpus of onset-eligible DMC natives + spot-measure; wire a corpus
   runner like bin/hubbard_build_all.py.

HUBBARD leftovers (documented, lower priority per user having moved on): swallow freq
FM-during-hold (~86->100), spin class (Devils_Galop/I_Ball/Wiz), 6 no-sig files,
note-format laggards (IK+/Thundercats/Tarzan/Mega_Apocalypse/Knucklebusters).
</work_remaining>

<attempted_approaches>
DMC native fidelity — the emulated-onset residual, FOUR approaches tried, all
committed-then-reverted EXCEPT the shipped gate-rise version. DO NOT re-tread:
1. **note_freq bound to DMC's own freq table**: WRONG — DMC plays notes above its
   table (semi 74 from a table maxing ~semi 56) via octave shift. Fixed by _pal (PAL
   table, full range) + trace-resolved semitone. This part IS in the shipped code.
2. **Global tick->frame schedule** calibrated from the best voice's emulated onsets:
   REGRESSED the good voices (Rockbuster osc2 98->93, Billie osc2 93->74) and did NOT
   fix the bad voices. Reverted.
3. **Pitch-step onset detection** (onset = gate-rise OR freq jump > semitone):
   100% coverage BUT over-emits on the per-frame arp (Dummy_II 423 emitted vs 106
   real) -> breaks 1:1 note placement. Reverted.
4. **Debounced settle detection** (onset = gate-rise OR a new semitone that HOLDS
   >=3 frames, to reject arp jitter): improved legato COVERAGE (Wanna v1 63/64, Omega
   v1/v2 47/48) BUT REGRESSED the native build badly (Blobby 74/87/99 -> 1/1/98) —
   extra/changed onsets disrupt durations + capture windows more than coverage
   predicts. Reverted. KEY LESSON from this: Wanna's bad voice is a PITCH problem
   (arp confounds trace-resolve), NOT an onset problem — even perfect onsets leave it
   at 33% freq. So the residual is TWO intertwined problems (legato onsets + arp
   pitch), and trace-capture fights both -> the wavetable-arp MODEL is the real fix.
5. **Adaptive windowing to avoid bundle force-merge**: not the issue — a 6s/5-bundle
   window (no merge) still sat at the same freq. The fits() count_only returns the
   POST-cluster count so parts still grow to force-merge; irrelevant once onset-align
   fixed the real cause.
6. **DMC_MAX_PARTS=1 whole-song build**: force-merges 63+ arp bundles -> corrupts
   pitch. Use adaptive (no cap) or small fixed windows.
7. **Minimal-embed SF2 for Rockbuster**: plays byte-identical under siddump but CRASHES
   SF2II on load (high-load $A000 player in the embed layout SF2II rejects). Stopgap,
   abandoned in favor of the native converter.
Tempo detection FALSE MATCH: the DEC/BPL/LDA#/STA idiom matches per-voice waveform
counters too (Chase picked $1036=waveform). Fixed by excluding indexed (,x/,y)
addresses (d935241) — but Chase STILL gets a wrong tempo (its counter resists the
signature; it's multispeed).
$C0 decode: VERIFIED byte-exact against the ROM (it fixed Balloon 23->99). NOT the
onset bug — the user's hypothesis was wrong; the real bug was tempo detection.
</attempted_approaches>

<critical_context>
- ENV: Windows, PowerShell primary + Bash (git-bash). Python = `py -3`. Working dir
  C:\Users\mit\claude\c64server\SIDM2. 64tass at
  C:\Users\mit\Downloads\64tass-1.60\64tass-1.60.3243\64tass.exe. vsid at
  C:/winvice/bin/vsid.exe. siddump onsets via sidm2.fidelity_common.siddump_note_onsets.
- NEVER run pyscript/sf2_open_in_editor.py (PyAutoGUI keystroke injection hijacks the
  user's window — they explicitly said stop).
- Background Bash tasks die at a 10-min cap; long batches -> PowerShell Start-Process
  detached + log file. ONE heavy CPU job at a time (parallel jobs starve each other and
  cause fake "hangs").
- After ANY driver build, `git checkout -- drivers_src/mon/layout.inc
  drivers_src/mon/freqtable.inc drivers_src/romuzak/layout.inc` (generated scratch,
  dirties the tree).
- The trace-driven pipeline (build_mon_native_song.build_native_song + emit_one) is the
  SHARED Stage-B engine for MoN/Hubbard/ROMUZAK/DMC. Shim interface: voices (3 lists of
  MONEvent), frames_per_tick, tick_to_frame/frame_to_tick, _voice_blocks, note_freq,
  instrument(idx)->dict{ad,sr,waveform,pw,pulseval,fx,wave_prog,flags,raw}, attrs
  tempo_toggle/hard_restart/snap_gate/hp_engine/onset_delay. MONEvent fields: note,dur,
  instr,wprog,retrig,rest,slide,tie.
- Driver memory map (drivers_src/mon/romuzak_driver.asm): code $1000-~$16C0, PINNED
  state $16CC-$1702 (never occupy — .cerror guard), freqtable $1710, out-of-line
  $1890-$193C, HP/swallow/sched state $1940-$19FF, edit area $1A00+, tables to $D000.
- FIDELITY MEASUREMENT: bin/mon_part_fidelity.py infers the original from folders
  Tel_Jeroen/Hubbard_Rob ONLY — for DMC it returns orig=0 (empty window error). Measure
  DMC directly: wrap SF2 via mon_sf2_validate._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003),
  trace both with mon_fidelity.per_frame, compare freq_to_semi/wf/pul. secs=0 -> VACUOUS
  100.0 (a silent SF2 measures perfect) — always use a real window.
- freq_to_semi (fidelity_common) reference: PAL table, middle C ~$1167. sid_player
  FREQ_TABLE_LO/HI = 96-entry PAL chromatic (semi 0-95). freq_to_semi($4C20)=74.
- DMC note byte is a freq-TABLE ROW selector for the BASE; the played pitch = base +
  wavetable arp offset (per-frame). The wavetable arp value $1A00 = $80|absolute-note.
- Rockbuster: load $A000, init $A000, play $A074. Balloon: load $1000 (embedded,
  header load=0), init $1440, play $1003 -> JMP $1050. Dominant player fingerprint
  init+$440/play+$3 (~10-12 files at $1000).
</critical_context>

<current_state>
- Working tree CLEAN at 360a1f4 (pushed to origin/master). All DMC + Hubbard work
  committed. 6 DMC tests + Hubbard/MoN tests green.
- DMC deliverable status: format fully RE'd; parser+decoder DONE (29/43 >=90% onsets);
  native Stage B WORKING — **Rockbuster ~97% native fidelity** (the session's headline),
  21/43 files onset-eligible (most 2/3 voices high). out/Rockbuster_native.wav on disk.
- Hubbard: SHIPPED v3.14.0, complete for the supported set.
- The DMC per-voice residual is at the natural limit of the trace-capture approach.
  RECOMMENDED NEXT: the wavetable-arp MODEL (structural semitone arp programs, Galway
  path) as a fresh focused effort — memory johannes-bjerregaard-player.md has the arp
  format ($80|note, $7E/$7F loop) and names this as the fix. Do NOT iterate more
  onset-detection variants (4 tried, characterized above).
- Memory files updated: johannes-bjerregaard-player.md (full format map + all findings +
  4 rejected approaches), MEMORY.md index (Johannes entry), hubbard-player-re.md,
  new-player-priority.md (Hubbard DONE, Johannes active).
- OPEN QUESTION for next session: does modeling the wavetable arp as semitone FM
  programs resolve BOTH the legato-onset and arp-pitch residuals in one move? (Hypothesis
  yes — it decouples pitch from trace-capture.) Validate on Wanna_Get_Sick osc1 (the
  clearest arp-pitch failure) and Omega_Force_One.
</current_state>
