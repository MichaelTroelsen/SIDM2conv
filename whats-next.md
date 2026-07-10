<original_task>
Standing mission (project): static RE + AI tools converting any SID into an SF2 at 99%
fidelity + 100% editable. This session's explicit user tasks, chronological:
1. "read whats-next" -> resume the DMC arc.
2. "update docs, cleanup, commit and push"; "fix remaining open issues; build a DMC.MD
   like the other players; update story.md".
3. Cleanup via ARCHIVE (never delete); "add a --archive mode to cleanup.py".
4. "keep unlocking DMC" (repeatedly).
5. "do the legato full-song a/b".
6. SF2.MD: "list ALL songs we converted incl. 100/100/100, original player, SF2 player,
   parts per song; keep it updated"; "flyt til docs og åben den" (artifact).
7. **"reduce the number of files per song — analyse what causes the split"** (ALL
   players; each subtune may be its own file).
8. **"improve the fidelity analyser to get the last 1-2% perfection"** (while continuing
   file-count reduction).
9. "CI/CD pipeline fails with security scan — investigate and fix".
10. **"when we are done we should work on SOUND MONITOR from the FunFun folder"** (the
    next arc — this is where the fresh session starts).
11. "update docs. bump version. commit and push" (v3.16.0) + "complete work remaining"
    (done — see current_state).
STANDING RULES: accuracy over speed; never ship lossy silently; archive-before-delete;
NEVER run pyscript/sf2_open_in_editor.py (PyAutoGUI hijacks the user's window — launch
SF2II via `bin/SIDFactoryII.exe --skip-intro <abs path>`, workdir bin).
</original_task>

<work_completed>
ALL COMMITTED + PUSHED (master == origin/master @ 85cf19b, v3.16.0, CI GREEN, 1512
tests pass). Commit chain this session (messages carry full detail):
- d1da5ff corpora: SID/JohannesBjerregaard(88)/deenen/Gray_Matt/LFT.
- 5643f18 v3.15.0 docs (NEW docs/players/DMC.md; .gitignore: *.wav, bin/_*.err/.out,
  external tool dirs bin/DMC|RoMusak|sid2txt-1.0|'sound monitor').
- ac1b24f DMC adaptive base-note `_sem` (the FM $40-$43 collision, see critical_context):
  Wanna osc1 66->100, Blobby 75/87->87/100, Tiny osc1 98->100 (osc3 protected).
- a05e123 bin/dmc_build_all.py (corpus runner: --dry survey / sequential build).
- 5b92f4b DMC 18/18 eligible built, 0 fail.
- 0a7af9d/8e716c0/a5745ef/a21aa93/c6ba313/b47ab14/f21c1ab/f469951 SEVEN new DMC
  generations decoded+tested (split-freq $3f00 Fat; state AND#$0F=In_the_Mood 100x3;
  absolute-store=M_A_C_H 100x3+Thunder_Force+Predictable; indexed-store=Spy/Special_
  Agent/Twilight; interleaved-track=Deel_2/Fruitbank/Slimbo4; ADC-vibrato-freq=Alf/
  Music_Demo/Test+Domino locates; state-copy=Myth_Demo/Stormlord_V2/STII8+Flimbos/
  Kamikaze locate; staged-emit=Eagles/Camel/Ragtime/Spacegame/Who_Is_Robb 99-100%).
  **DMC: 18 -> 41/88 ELIGIBLE.** 14 dmc tests.
- be7da59/9d4d147 legato FULL-SONG per-voice A/B shipped (DMC_LEGATO_AB default on,
  adaptive path; candidates=pitch-change>1.3x gate; decide on first ~90s; keep legato
  only where it wins >1.0): Dreaming osc3 39->90; Fourth_Dimension osc2 protected.
- 3a15a6c/a4e16eb/ca31465 docs/SF2.md build index (+HALL OF FAME) + pyscript/
  gen_sf2_index.py (auto inventory between GENERATED markers) + CLAUDE.md note.
  Artifact: https://claude.ai/code/artifact/ef593833-e303-4745-88e5-23190f4eef5b 🎛️.
- 97b794d..cc230bd PART-REDUCTION analysis (docs/analysis/PART_REDUCTION_PLAN.md —
  READ THIS for the campaign): ~95% of splits = the 63-cap (FM,pulse) bundle channel;
  decompose (BUNDLE_DECOMPOSE=1): DMC diverse both axes (Phase-1 clustering=PROVEN DUD),
  Hubbard FM structural (24 shapes; pulse drives explosion).
- d3edfd4 Phase-2 pulse_canon (per-instrument pulse canonical, `pulse_canon` shim flag /
  MON_PULSE_CANON): **Commando 45->4, Monty 22->4, Chimera 76->12 parts, BYTE-EXACT.**
- f334fc8/3b8dd68 MoN pulse_canon = OPT-IN only (real ~6-16% osc3 pulse cost on
  Supremacy; my first "collapse" claim was a measurement offset error, corrected).
- ae59bab **Hubbard track bit7 TRANSPOSE generation** (3 ROM-verified encodings):
  Shockway 638->21 parts, Star_Paws 188->10, Auf_W 274->43, Saboteur 112->86 — first
  CORRECT decode of these; span-sanity guard; 8 hubbard tests.
- 15147d6 **wave REST-TAIL fix** (shared engine; capture extends across rests; cap
  96->256): Supremacy sub1 94.3->99.9 EVERY register; Cybernoid_II part01 100x3;
  Cybernoid I wf/pulse 100. Crown jewel (Hawkeye sub2 100x4) regression-checked.
- 03bbb7b/d6fe158 **fidelity analyser** (bin/mon_part_fidelity.py): per-voice delay
  (±2), skew-vs-content classification (±1-frame transition = separate skew-tolerant
  score), mismatch-CLUSTER report (frame-runs, top 3, <99.5% registers), part-LOOP
  auto-cap (40-frame all-voice freq self-similarity).
- e2dee23/7347503 stale-part purge + builders AUTO-PRUNE (prune_stale_parts in
  build_mon_native_song, wired into mon/hubbard/dmc emit loops).
- 6cb48e2 Hubbard split pulse-speed table (lay.pulsespeed_tbl, ROM fetch $EE45).
- 0a47001 **pulse_canon GATED to hp_engine builds** (lossy for captured-pulse classes:
  Shockway osc3 pulse 0.3->100 with it off; main() force-clears when hp_engine off).
- 2212b4d **CI security scan FIXED after 199 consecutive red runs** (8 live bandit
  findings properly repaired; workflow -x ./archive; verified with the exact CI cmd).
- 5e0cf78 **v3.16.0** (constants, CHANGELOG, CLAUDE.md, STORY.md chapter+chain,
  whats-next). Full suite 1512 passed.
- 9d8c05d builder HARD-REFUSES mis-decode spans (>2.5x unequal voices or >900s;
  HUBBARD_ALLOW_UNEQUAL=1 override) — Devils_Galop had started a 20,975s (5.8h) trace.
- 521f247 comprehensive handoff.
- 85cf19b **work-remaining item 1 COMPLETED**: killed TWO RACING corpus runners found
  mid-flight; parser-identified the only stale-lossy artifacts (Delta s0/s11/s12 +
  Sanxion = captured-pulse builds from the pre-gating era); rebuilt them correctly
  (Sanxion 31 parts; Delta s11/s12=3; **Delta s0 165->221 parts = the honest count**,
  correctness over compactness); docs/SF2.md final (Hubbard 589 / MoN 200 / DMC 236 /
  Galway 40 / ROMUZAK 4 files); artifact republished (same URL).
Also: cleanup.py --archive mode (archive/cleanup_<date>/ + MANIFEST, dedup); archive/
cleanup_2026-07-09/ = 115 archived scratch files; transposed-class FULLY diagnosed
(fetch $EE45 field map V1-compatible; pulse engine $EF85-$EFE5 SELF-MODIFYING rails
decoded; osc1 residual = fetch-frame step + fx-arp re-fetch; osc2/osc3 pulse=100);
SOUND MONITOR arc opened (memory/soundmonitor-player.md + MEMORY.md indexed).
Memories updated: johannes-bjerregaard-player, hubbard-player-re, myth-supremacy-mon-re,
soundmonitor-player (NEW).
</work_completed>

<work_remaining>
1. **SOUND MONITOR — the next arc (user directive; START HERE).**
   memory/soundmonitor-player.md has the recon: **11 Fun_Fun files** init=$C000/
   play=$C475 (Dance_at_Night_remix, Dreamix, Dreamix_Two, Final_Luv, Fuck_Off, Fun_Mix,
   Just_Cant_Get_Enough, No_Title, Poppy_Road, Thats_All, Times_Up) + Demo_of_the_Year_
   87_menu ($C020 variant). Player $C000-$CBFA in-image; song data below at varying
   loads ($7000/$9000/$A000). init: A2 01 8E 0F C0 (LDX#1/STX $C00F); play $C475:
   20 17 CA AD 0F C0 F0 03 20 0D C9 (JSR $CA17...). Format = Hülsbeck Soundmonitor
   (1986, 64'er). STEPS:
   a. Read ROMUZAK's SOUNDMONITOR_CNV parsing code in out/romuzak_editor_decrunched.prg
      (entry $1000; find the CNV menu routine) — a literal reference parser of SM data.
   b. Disasm the play body ($CA17 on Dance_at_Night_remix) via a probe like
      bin/_hub_disasm.py (untracked; pattern: load_sid + the _disasm_filter_handler
      OPS-table exec trick).
   c. Format map -> sidm2/soundmonitor_parser.py (signature/relocation-light: the
      player sits at fixed $C000; find the song-data pointers init consumes — state
      seen at $02C3/$02C6).
   d. Onset-validate vs siddump -> Stage A -> Stage B via the shared MoN engine
      (docs/players/PLAYBOOK.md; shim pattern = bin/build_dmc_native_song.py DMCShim).
   e. Extra refs: bin/'sound monitor/' disks (sound_monitor_v1.0.t64.gz, cct 1.1 d64,
      Relocator, RockMonitor5.zip); public 64'er format docs (web).
2. Transposed-track Hubbard class fidelity (Shockway/Star_Paws/Saboteur/Auf_W; osc1
   pulse 27, osc3 wf 70): implement (a) fetch-frame pulsework step (ROM applies ONE
   +speed step on the fetch frame; orig first frame = init+speed), (b) fx-arp RE-FETCH
   decode (arp steps re-fetch -> PW resets per flip; the decode holds one longer note).
   Consider per-voice engine A/B (osc2=HP proven 100). Engine fully decoded in
   memory/hubbard-player-re.md.
3. Devils_Galop/I_Ball/Wiz = ANOTHER unhandled Hubbard track generation (builds now
   hard-refused instead of tracing hours) — decode like the transpose generation.
4. DMC: ~21 NO-TABLES left (next shared cluster: 2nd/Skateboard/Tuba, all la=$c367
   init+$0/play+$6); Special_Agent osc2 pulse 57/100/1; Scandalous osc1 pulse 29;
   Predictable wf 50 on osc2/3.
5. Deep_Strike WAVE-overflow count-vs-emit divergence (fits() passed, emit raised
   "WAVE overflow: 258 rows" in gen_includes_song); Hawkeye sub0 filter window-seams;
   MoN safe pulse_canon default (cap window growth by RAW pre-canonical bundle count).
6. Registry-wire native players into auto sid-to-sf2 (docs/ROADMAP.md). Staged corpora:
   SID/LFT (**Blackbird tracker + its player SOURCE in bin/LFT/blackbird-1.2** —
   highest-leverage future player), SID/deenen, SID/Gray_Matt, SID/Gallefoss_Glenn
   (all untracked in git — intentional).
</work_remaining>

<attempted_approaches>
DO NOT RE-TREAD:
- DMC Phase-1 bundle clustering (BUNDLE_TOL): 0 parts saved at inaudible tolerances —
  DMC bundles genuinely diverse in BOTH axes.
- SIX single-threshold legato heuristics: each trades one voice for another; only the
  full-song per-voice A/B works (shipped).
- Single-window legato A/B: the 256-row WAVE cap forces ~10s windows; the legato gain
  only shows past FM_CAP (5s) over longer spans -> always picks gate.
- MoN pulse_canon default-on: REJECTED (real osc3 pulse loss on Supremacy). My initial
  "part02 collapses 7-18%" was a MEASUREMENT ERROR (pulse_canon shifts part boundaries;
  wrong off0) — the analyser's loop auto-cap + correct offsets prevent this class now.
- Hubbard transposed class: FORCE_HP + split speed table alone = insufficient (osc1
  5.6->7.2); the pulse ENGINE differs (decoded); capture path was ALSO being ruined by
  pulse_canon (fixed by gating -> osc3 100).
- freerun-stream-misfire hypothesis for Shockway osc1: WRONG (debug: no stream on osc1).
- Constant-transpose-offset hypothesis for Shockway freq runs: WRONG (pitches verified
  correct; mismatches sit at arp-flip note boundaries).
- DMC wavetable-arp SEMITONE model, global tick->frame schedule, pitch-step/debounced
  onset detection, minimal-embed SF2: all dead ends (see docs/players/DMC.md).
- `git add -A` after git mv swept 567 unrelated files into a commit -> reset + force-
  push-with-lease. STAGE FILES EXPLICITLY.
- Two detached corpus runners ended up racing (a leftover from a timed-out launcher
  call whose detached child survived): CHECK for existing hubbard/mon processes before
  launching batch builds (Get-CimInstance Win32_Process | ? CommandLine -match ...).
</attempted_approaches>

<critical_context>
- ENV: Windows, `py -3`; Bash + PowerShell tools. Long jobs: PowerShell Start-Process
  detached + log (Bash bg dies at 10min). PS `*>>` logs are UTF-16 (grep fails
  silently; read via PowerShell Get-Content). $env: vars set before Start-Process are
  inherited by the child.
- ONE MoN-ENGINE BUILD AT A TIME (shared drivers_src/mon scratch). After ANY driver
  build: `git checkout -- drivers_src/mon/layout.inc drivers_src/mon/freqtable.inc
  drivers_src/romuzak/layout.inc`.
- MEASURING: `py -3 bin/mon_part_fidelity.py <part.sf2> <sub> <secs> [t0_seconds]` —
  pass the part's REAL window from the build log. Features: per-voice delay, skew-
  tolerant score, cluster report, loop auto-cap. TRUST skew classification: 47.7
  strict / 100.0 skew-tolerant = ±1-frame write jitter = AUDIBLY EXACT (Supremacy sub2
  osc2, Lightforce osc1). DMC measuring: recreate bin/_dmc_fidelity.py from the mon
  tool pattern if missing (untracked scratch); SF2 wrap = mon_sf2_validate._psid(
  bytes(sf2[2:]), sla, 0x1000, 0x1003).
- THE FM $40-$43 COLLISION (shared driver): raw Hz deltas with high byte $40-$43
  dispatch as SCALED-VIBRATO -> corrupt the note. Only delta1=trace[onset+1]-base
  depends on the base; DMC `_sem` mode `adapt` seats the base high when delta1 would
  collide.
- pulse_canon: hp_engine builds ONLY (V1: captured pulse unused -> pure bundle
  collapse). Captured-pulse builds: LOSSY, force-cleared. MON_PULSE_CANON=1 opt-in.
- Hubbard track bit7 TRANSPOSE (lay.trk_transpose): mode 1 = `$80|semis` (sig B1 zz 10
  ?? C9 FF F0 ?? [C9 FE F0 ??] 29 7F — Shockway $ED99/Star_Paws/Saboteur_II); mode 2 =
  `$80 nn` (sig ...C8 B1 zz — Auf_W $E49D). Transpose ADDS to (pitch&$7F) at fetch.
- Transposed-class pulse engine (Shockway $EF85-$EFE5, SELF-MODIFYING): split record
  $F2F1[i*8]+0=speed (0=static), +2=rails (LSR*4 patches TOP CMP operand $EFB5;
  AND#$0F patches BOTTOM $EFCF); PW±speed, hi&$0F, dir flips at rails; PW AND dir
  RESET at every fetch ($EE5A/$EE7B); ROM applies ONE step ON the fetch frame.
- Hubbard tracks are SYNCED (equal one-pass voice lengths = healthy); the builder
  hard-refuses >2.5x-unequal or >900s spans (HUBBARD_ALLOW_UNEQUAL=1 override).
- Wave rest-tail: gate-off rows output program&$fe -> captured $00 rows reproduce
  mid-rest wave-off; _wave_prog_for cap=256 (settle-trim keeps hold-tails free).
- Bandit CI gate: `bandit -r . -ll -ii -x ./test_converter.py,./archive`. bin/_*.py is
  untracked/ignored (local-only). NO os.system / shell=True / hardcoded /tmp in
  tracked code.
- cleanup.py: --archive MOVES to archive/cleanup_<date>/ + MANIFEST (use this);
  --clean DELETES (avoid). Builders auto-prune stale _partNN files > the new count.
- After native builds: `py -3 pyscript/gen_sf2_index.py` refreshes docs/SF2.md; the
  artifact republish (same file path) keeps URL ef593833-e303-4745-88e5-23190f4eef5b.
- On version bump: CLAUDE.md + CHANGELOG.md + STORY.md (chapter + chain) +
  sidm2/__init__.py (__version__/__build_date__).
</critical_context>

<current_state>
- Repo: master == origin/master @ 85cf19b, **v3.16.0**, working tree CLEAN. CI GREEN
  (the security scan fixed after 199 red runs). Full suite 1512 passed. NO background
  builds running. Untracked-but-intentional: SID/Gallefoss_Glenn, bin/LFT, bin/SIDDuzz,
  archive/cleanup_2026-07-09, out/ artifacts (gitignored).
- ALL bounded work-remaining items from the prior handoff are COMPLETE: the corpus
  correctness rebuild is done (Delta s0/s11/s12 + Sanxion rebuilt without the lossy
  canonical; Delta s0 = 221 parts, the honest count), docs/SF2.md is final (Hubbard
  589 / MoN 200 / DMC 236 / Galway 40 / ROMUZAK 4 files), artifact republished.
- Fidelity state (current builds): Hubbard V1 byte-exact at ~4 parts/song; Supremacy
  sub1 99.9 every register; Cybernoid_II part01 100x3; DMC 41/88 eligible (In_the_Mood
  / M_A_C_H / Fourth_Dimension 100x3); Shockway 21 parts (osc2/osc3 pulse 100; osc1
  fetch-step + arp-refetch residual, decoded & documented).
- THE NEXT SESSION STARTS ON **SOUND MONITOR** (work_remaining #1) — recon done, ground
  truth staged (ROMUZAK SOUNDMONITOR_CNV in out/romuzak_editor_decrunched.prg), plan in
  memory/soundmonitor-player.md. First action: disassemble the CNV parser, then the
  $CA17 play body of Dance_at_Night_remix.
- No temporary changes or workarounds in place; everything is committed or reverted.
</current_state>
