<original_task>
Standing mission (project): tools combining static RE + AI to convert any SID into an
SF2 at 99% fidelity + 100% editable. User's player priority (memory/new-player-priority):
1. Rob Hubbard (DONE, shipped v3.14.0), then 2. Johannes Bjerregaard / DMC.

This session's explicit user tasks, in order:
1. "complete hubbard then start Johannes" — finish Hubbard V2, then begin
   SID/JohannesBjerregaard/ (88 files).
2. "can i hear rockbuster in sf2" -> (it crashed as an embed) -> "render rockbuster to
   wav and then continue with building the converter".
3. A chain of "continue"/"go on" driving the DMC converter: format RE -> parser ->
   decoder -> native Stage B -> onset fidelity. Named sub-requests, all attempted:
   "fix the $C0 decode to tighten onsets", "do the emulated onset schedule", "do the
   wavetable-arp model".
STANDING RULES (memory): accuracy over speed, never ship lossy silently, the USER'S EAR
is the final acceptance metric. NEVER run pyscript/sf2_open_in_editor.py — its PyAutoGUI
types the filename into the user's active window (they said "stop trying to load it");
load SF2s manually.
</original_task>

<work_completed>
=== HUBBARD V2 COMPLETED + SHIPPED v3.14.0 (first part of session) ===
- State-region overflow fix (7 V2 swallow files crashed on load): the driver's 4 tail
  data tables (sidbase/frbits/ollo/olhi, 12B) overflowed 1 byte into $16CC (SF2II pinned
  state $16CC-$1702). Fixed by `* = $1703` relocation into the free $1703-$170F gap.
- V2 pulse: gated hp_engine=0/freerun_pulse=1 for any swallow file; Lightforce pulse
  0.5->100. All 7 swallow files: pulse/wf/filter 100%, freq ~86% (FM-during-hold, open).
- TEMPO_SCHED driver mode (per-frame stretch bitmap, SCHEDTAB $1940); Game_Killer 22->50.
- Docs: docs/players/HUBBARD.md, NATIVE_DRIVER.md, HUBBARD_V2_PLAN.md; STORY.md v3.14.0;
  CLAUDE.md/CHANGELOG.md; __version__=3.14.0. memory/hubbard-player-re.md updated.

=== JOHANNES BJERREGAARD / DMC — FULL ARC (main session work) ===
DMC = Demo Music Creator. Ground truth: ~/Downloads/dmc4editor11_win64.zip (ReadMe:
"the famous DMC4 Player written by Brian/Graffity in '91"). 88 files, ~all Bjerregaard.
DMC is one of the most-used C64 formats -> a parser generalizes across much of HVSC.
FULL format map + all findings in memory/johannes-bjerregaard-player.md.

FORMAT (RE'd from Balloon.sid via disasm + py65; all addrs for load $1000, RELOCATABLE
so signature-located):
- Model: Track (orderlist) -> Sector (pattern) -> Sound (instrument).
- Tempo: DEC tempo/BPL/LDA #imm/STA -> fpt = imm+1 (per-tune, baked in code).
- Track per voice: ptr $104A/$104D,x, bytes=sector#; $FF=loop, $FE=end.
- Sector-ptr table $1900(lo)/$1980(hi) indexed by sector#.
- Sector event: cmd byte (dur=low5, bit5 flag, bit6=2 effect bytes, bit7=sound byte);
  (cmd&$E0)==$C0 = REST (dur, no note, consumes 1 byte); then pitch byte; $FF ends sector.
- Sound: 8 bytes $1500 [AD,SR,PWinit,PWrails(nibbles=min/max),PWspeed,vib,filt6,flags7].
  PWM engine + vibrato (per-voice 16-bit acc $1011/$1014) + filter routing ($D417).
- Freq table $135F INTERLEAVED lo/hi (note*2). DMC plays notes ABOVE its own table via
  the WAVETABLE (octave-shift); the freq ROW = wavetable value, NOT the raw note byte.
- WAVETABLE $1A00(arp)/$1B00(waveform): advances 1 step/frame -> fast ARP. $1A00 byte =
  $80|note (ABSOLUTE note; $DF->95,$AE->46,$A3->35,$BD->61 verified), $00=hold,
  $7E/$7F=loop. Per-sound wavetable start (e.g. Balloon note $2F starts at idx 16 after
  an attack at idx 36).
- SID emit ($1314+): $1011/$1014->$D400/1, $1036->$D404(wf), $100B/$100E->$D402/3(pulse),
  $D416/$D418(filter).

CODE DELIVERED (all committed + pushed, HEAD = 01a236b):
- sidm2/dmc_parser.py (26fd05b/47e93d6/d935241/5a59f6e): signature-located tables
  (sector/sound/freq/track, relocation-safe, on 44/88 files); DMCNote dataclass;
  decode_track/decode_sector/decode_song ($C0=rest, $FF loop/end); tempo detection = the
  GLOBAL counter (excludes per-voice counters accessed indexed ,x/,y; d935241);
  measure_onsets (siddump CPU6502Emulator + $D012 raster fake + banking; per-voice $D404
  gate-rise frames).
- pyscript/test_dmc_parser.py (5fe1e0c): 6 tests, green (Balloon addrs, relocation on
  Cant_Stop, chromatic freq table, track termination, decode, onset >=90%).
- bin/build_dmc_native_song.py (e086b03/d38a0fb/360a1f4): DMCShim -> shared
  build_mon_native_song pipeline. TWO modes: (a) ONSET-ALIGNED (default when emulated
  onsets agree >=85% with siddump): fpt=1, one MONEvent per emulated gate-rise, dur=
  frame-gap, pitch = _sem(trace at onset) -> absolute semitone; note_freq = _pal (PAL
  table, full 0-95); instrument from a decode frame-timeline. (b) tick-grid fallback for
  legato/multispeed/self-IRQ variants.

RESULTS:
- Onset decode (siddump vs decode, per-voice phase): 29/43 main-player files >=90%.
- Native fidelity WIN: **Rockbuster freq 65->97, wf 87->100, pulse 100/100/100** via the
  emulated onset schedule (commit d38a0fb). Rendered out/Rockbuster_native.wav (played
  for user). Also out/Rockbuster.wav (original SID, 90s). Native build self-checks
  emulated-vs-siddump onsets (>=85%) and falls back otherwise.
- Onset-agreement survey: 21/43 files pass the >=85% check (INCLUDING several decode-FAIL
  "variant" files — MSI_Demo/Billie_Jean/Namnam/Some_Soul — because onset-align is
  decode-independent for pitch/timing). Most build with 2/3 voices at 90-100%.

PER-VOICE DIAGNOSIS (this session's final investigation, on Wanna_Get_Sick osc1 = the
clearest failure @33% freq): emulated onsets are CORRECT (every 6 frames, match siddump).
At each onset o: frame o = $41B8 (real trigger freq), frame o+1 = $684C (a 1-FRAME ARP
ATTACK SPIKE), frame o+2 = the melody note ($1168/$1739/$1A13, changes per note). The
`_sem` helper (order 1,2,0 — "settle past the 1-frame attack") picks o+1 = the SPIKE ->
resolves every note to semi 79 -> note_freq=PAL[79]=$6853 (the wrong high note seen in
the probe). ROOT: the base note is pinned to a 1-frame arp transient.
</work_completed>

<work_remaining>
DMC — the remaining residual and its ONE viable next step:
1. **PER-VOICE ADAPTIVE BASE-NOTE RESOLUTION** (the only un-exhausted approach). The bug:
   `_sem` (bin/build_dmc_native_song.py ~line 32) picks a fixed frame (o+1) that is a
   1-frame arp spike for some voices. But NO fixed frame works for all voices — a quick
   test of order (0,1,2) HELPED Blobby/Billie v2 (->100) but CRASHED Tiny_Symphony v3
   (88->3) and did NOT fix Wanna v1 (still 33). So the fix must be ADAPTIVE per note:
   candidate approaches (untried) — (a) pick the base semitone that MINIMISES total FM
   offset over the note's frames (the true fundamental, not a transient); (b) detect +
   exclude 1-frame spikes (a semitone that appears for exactly 1 frame then leaves);
   (c) pick the semitone the note HOLDS longest but weighted toward the LOWER octave
   (arp base). VALIDATE on the two files that pull opposite directions: Wanna_Get_Sick
   osc1 (needs the settled melody, not the o+1 spike) and Tiny_Symphony v3 (regressed
   when forced to frame 0 — it genuinely settles later). Also Omega_Force_One (osc1/2
   ~40%). Rockbuster (96/98/93) and Blobby must NOT regress.
   NOTE: Wanna v1 stayed 33% under BOTH _sem frames tried, so its residual may be MORE
   than base-note — re-diagnose whether the FM capture of its fast alternating arp is
   itself the problem (dump Wanna osc1 orig-vs-probe per frame after any base fix).
2. Multispeed / self-IRQ variants (Chase, Dummy_II): 1x replay reads them wrong (Chase
   4x too slow; PSID speed flag 0 but they self-install faster timing). Falls back to
   tick-grid. Lower priority.
3. Decode variants: the "0% variant" cluster (Billie_Jean trk=$1440=code region — wrong
   signature match) + the 70-90% desync. Onset-align already covers many; low priority.
4. Build the full corpus of onset-eligible DMC natives (21 files) + a corpus runner like
   bin/hubbard_build_all.py; spot-measure.

HUBBARD leftovers (documented, user moved on): swallow freq FM-during-hold (~86->100),
spin class (Devils_Galop/I_Ball/Wiz), 6 no-sig files, note-format laggards.
</work_remaining>

<attempted_approaches>
DMC native fidelity residual — SIX approaches tried, ALL committed-then-reverted except
the shipped gate-rise onset-align. DO NOT RE-TREAD:
1. **note_freq bound to DMC's own freq table**: WRONG — DMC plays notes above its table
   (semi 74 from a table maxing ~semi 56) via octave shift. Fixed by _pal (PAL, full
   range) + trace-resolved semitone. IN the shipped code.
2. **Global tick->frame schedule** calibrated from the best voice's onsets: REGRESSED the
   good voices (Rockbuster osc2 98->93, Billie osc2 93->74), didn't fix bad voices.
3. **Pitch-step onset detection** (gate-rise OR freq jump > semitone): 100% coverage BUT
   over-emits on the per-frame arp (Dummy_II 423 vs 106 real) -> breaks 1:1 placement.
4. **Debounced settle onset detection** (a new semitone that HOLDS >=3 frames): improved
   legato COVERAGE (Wanna v1 63/64) BUT REGRESSED the build badly (Blobby 74/87/99 ->
   1/1/98). Also: coverage doesn't predict native fidelity.
5. **Wavetable-arp SEMITONE model** (the "do the wavetable-arp model" request): per-event
   FM override hook (build_mon_native_song._arp_fm_for -> m.fm_arp_program) + DMCShim
   semitone-hold arp programs from the trace. REGRESSED (Rockbuster osc3 93->75, Omega
   40/41->16/6, Wanna unchanged). WHY: semitone-hold entries play freqtable[base+S] =
   QUANTIZED to whole semitones in PAL tuning, but DMC's freq table isn't PAL (semi74 =
   $4C20 vs PAL $4E28) and arp steps aren't on-semitone -> strictly LESS exact than the
   Hz-delta capture (which reproduces DMC's per-frame freq bit-for-bit). The Hz-delta
   onset-aligned capture is the RIGHT representation. DEAD END — do NOT retry.
6. **_sem onset-frame resolution** (order 0,1,2 instead of 1,2,0): a WASH — helped Blobby
   v2/Billie v2 (->100), crashed Tiny v3 (88->3), Wanna v1 unchanged. Proves no FIXED
   frame works; must be adaptive per note.
KEY META-FINDING: Wanna v1 = 33% under Hz-delta AND semitone AND both _sem frames ->
its residual is INVARIANT to the FM encoding and the base frame -> the "arp model fixes
it" hypothesis is DISPROVEN; the fast-arp voices are a real architectural ceiling of the
single-base-note + trace-capture approach, not a patchable bug.
OTHER DEAD ENDS: minimal-embed SF2 for Rockbuster plays byte-identical under siddump but
CRASHES SF2II on load ($A000 high-load player) — abandoned. $C0 decode VERIFIED byte-exact
vs ROM (fixed Balloon 23->99) — was NOT the onset bug (user hypothesis wrong; real bug was
the tempo false-match to a per-voice waveform counter). Multispeed call-N-per-frame did
NOT fix Chase/Dummy_II.
</attempted_approaches>

<critical_context>
- ENV: Windows, PowerShell + Bash (git-bash). Python `py -3`. CWD C:\Users\mit\claude\
  c64server\SIDM2. 64tass at C:\Users\mit\Downloads\64tass-1.60\64tass-1.60.3243\64tass.exe.
  vsid at C:/winvice/bin/vsid.exe.
- NEVER run pyscript/sf2_open_in_editor.py (PyAutoGUI keystroke injection hijacks the
  user's window). Background Bash tasks die at a 10-min cap -> long batches via PowerShell
  Start-Process detached + log. ONE heavy CPU job at a time.
- After ANY driver build: `git checkout -- drivers_src/mon/layout.inc
  drivers_src/mon/freqtable.inc drivers_src/romuzak/layout.inc` (generated scratch).
- SHARED Stage-B engine = build_mon_native_song.build_native_song + emit_one (MoN/Hubbard/
  ROMUZAK/DMC). Shim interface: voices (3 lists MONEvent), frames_per_tick, tick_to_frame/
  frame_to_tick, _voice_blocks, note_freq, instrument(idx)->dict, attrs tempo_toggle/
  hard_restart/snap_gate/hp_engine/onset_delay. Optional per-event FM override hook exists
  in _arp_fm_for via m.fm_arp_program (added then reverted with the arp model — re-add if
  needed). MONEvent fields: note,dur,instr,wprog,retrig,rest,slide,tie.
- FIDELITY MEASUREMENT for DMC: bin/mon_part_fidelity.py only looks in Tel_Jeroen/
  Hubbard_Rob folders -> returns orig=0 for DMC. Measure DIRECTLY: wrap SF2 via
  mon_sf2_validate._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003), trace both with
  mon_fidelity.per_frame, compare freq_to_semi/wf/pul over N frames. secs=0 -> VACUOUS
  100.0 (silent SF2 measures perfect) — always use a real window.
- freq_to_semi (sidm2.fidelity_common) uses PAL, middle C ~$1167. sid_player.FREQ_TABLE_LO/
  HI = 96-entry PAL chromatic (semi 0-95). freq_to_semi($4C20)=74, ($41B8)=72, ($6853)~79.
- DMC note byte = a freq-table ROW selector; the played pitch = base + wavetable arp
  offset (per-frame). Fast arps have 1-FRAME attack spikes at onset+1 (the _sem trap).
- Rockbuster: load $A000, init $A000, play $A074. Balloon: header load=0 (embedded, real
  $1000), init $1440, play $1003 -> JMP $1050. Dominant fingerprint init+$440/play+$3.
- DMC build usage: `py -3 bin/build_dmc_native_song.py SID/JohannesBjerregaard/<name>.sid
  [secs|auto]`. Env DMC_MAX_PARTS caps parts. Output out/dmc/<name>_partNN.sf2.
</critical_context>

<current_state>
- Working tree CLEAN at HEAD 01a236b (pushed origin/master). All DMC + Hubbard work
  committed. 6 DMC tests + Hubbard/MoN tests green. (drivers_src/romuzak/layout.inc is
  generated scratch — `git checkout --` it if dirty.)
- DMC deliverables: format fully RE'd; parser+decoder DONE (29/43 >=90% onsets, 6 tests);
  native Stage B WORKING — **Rockbuster ~97% native** (headline), 21/43 files onset-
  eligible, most 2/3 voices at 90-100%. out/Rockbuster_native.wav on disk.
- Hubbard: SHIPPED v3.14.0, complete for the supported set.
- The DMC per-voice residual (fast-arp voices: Wanna osc1, Omega, and any voice with a
  1-frame arp attack spike at onset+1) is precisely diagnosed and at the NATURAL CEILING
  of the current architecture. SIX fix approaches exhausted + documented (see attempted).
- THE ONE VIABLE NEXT STEP: per-voice ADAPTIVE base-note resolution in _sem (bin/
  build_dmc_native_song.py) — pick the base that minimises total FM offset / excludes
  1-frame spikes, validated on the opposing-pull pair Wanna_Get_Sick osc1 vs Tiny_Symphony
  v3, without regressing Rockbuster/Blobby. Caveat: Wanna v1 stayed 33% under all base
  choices tried, so re-diagnose whether its fast-arp FM capture is itself the limiter
  before investing further.
- Memory files updated: johannes-bjerregaard-player.md (full format + all 6 rejected
  approaches + the arp-model-is-dead-end + Wanna-v1-invariant findings), MEMORY.md index,
  hubbard-player-re.md, new-player-priority.md (Hubbard DONE, Johannes active).
- No temporary changes or workarounds in place; everything is either committed or reverted.
</current_state>
