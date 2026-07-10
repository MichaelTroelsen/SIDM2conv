<original_task>
Standing mission (project): static RE + AI tools converting any SID into an SF2 at 99%
fidelity + 100% editable. This session's explicit user tasks, in order:
1. "read whats-next" -> resume the DMC arc (adaptive base-note = the open step).
2. "update docs, cleanup, commit and push" + "fix remaining open issues; build a DMC.MD
   like the other players; update story.md".
3. Cleanup with ARCHIVE (never delete) -> "add a --archive mode to cleanup.py".
4. "keep unlocking DMC" (repeatedly) -> DMC generation coverage.
5. "do the legato full-song a/b".
6. "lav en liste med alle SF2 filer inkl. 100/100/100, original player og SF2 player"
   -> SF2.MD; then "list ALL songs + parts per song, keep it updated"; "flyt til docs og
   åben den" (artifact).
7. "reduce the number of files per song — analyse what causes the split" (BIG wish; all
   players, not only DMC; each subtune may be its own file).
8. "improve the fidelity analyser to get the last 1-2% perfection" (while continuing on
   file-count reduction).
9. "CI/CD pipeline fails with security scan — investigate and fix".
10. "when we are done we should work on SOUND MONITOR from the FunFun folder".
11. "update docs. bump version. commit and push" (v3.16.0 — done).
STANDING RULES: accuracy over speed; never ship lossy silently; archive-before-delete;
NEVER run pyscript/sf2_open_in_editor.py (PyAutoGUI hijacks the user's window — launch
SF2II via `bin/SIDFactoryII.exe --skip-intro <file>` instead, workdir bin).
</original_task>

<work_completed>
ALL COMMITTED + PUSHED (master == origin/master @ 9d8c05d). Chronological commit chain
this session (each message has full detail):
- d1da5ff SID corpora added: JohannesBjerregaard(88)/deenen/Gray_Matt/LFT.
- 5643f18 v3.15.0 docs (docs/players/DMC.md NEW, STORY/CHANGELOG/CLAUDE, .gitignore:
  *.wav + bin/_*.err/.out + external tool dirs bin/DMC|RoMusak|sid2txt|sound monitor).
- ac1b24f DMC adaptive base-note `_sem` (the FM $40-$43 high-byte collision — see
  critical_context) — Wanna osc1 66->100, Blobby 75/87->87/100, Tiny osc1 98->100.
- a05e123 bin/dmc_build_all.py corpus runner (--dry survey / build; sequential).
- 5b92f4b DMC 18/18 eligible built, 0 fail.
- 0a7af9d DMC split-freq generation ($3f00 Fat cluster; DMCLayout.freq_hi).
- 8e716c0 DMC state-generation sound fallback (In_the_Mood 100/100/100 all voices).
- a5745ef DMC absolute-store sound fallback (+M_A_C_H 100x3, Thunder_Force, Predictable).
- a21aa93 DMC indexed-store fallbacks (+Spy_vs_Spy_III/Special_Agent/Twilight_Beyond).
- be7da59 + 9d4d147 legato: single-window A/B failed (WAVE cap forces ~10s window);
  FULL-SONG multi-part A/B SHIPPED (DMC_LEGATO_AB default on, adaptive path; candidates
  by pitch-change>1.3x gate; decide on first ~90s; keep legato per voice only when it
  wins >1.0) -> Dreaming osc3 39->90; Fourth_Dimension osc2 correctly stays gate.
- c6ba313 DMC interleaved-track generation (trk_interleaved; the track read TXA/ASL/TAY
  ALSO matched the sector sig -> sector was mislabelled; re-locates the split sector).
- b47ab14 DMC ADC-vibrato freq generation (LDA acc,X/CLC/ADC vib,X/STA $D400,Y).
- f21c1ab DMC state-copy sound generation (Flimbos/Kamikaze/Myth_Demo/Stormlord_V2/STII8).
- f469951 DMC staged-emit generation (Eagles/Camel_Riders/Ragtime/Spacegame/Who_Is_Robb,
  all 99-100% onset-agree). DMC total: **41/88 ELIGIBLE** (was 18 at session start).
- 3a15a6c/a4e16eb docs/SF2.md (build index: fidelity/original player/SF2 driver/HALL OF
  FAME + complete inventory) + pyscript/gen_sf2_index.py (scans out/<player>/, groups
  _partNN, writes between GENERATED markers). Artifact published:
  https://claude.ai/code/artifact/ef593833-e303-4745-88e5-23190f4eef5b (favicon 🎛️).
- 97b794d..cc230bd PART-REDUCTION analysis (docs/analysis/PART_REDUCTION_PLAN.md):
  ~95% of splits = the 63-cap (FM,pulse) BUNDLE channel (measured via
  bin/_dmc_split_analysis.py). Phase-0 decompose (BUNDLE_DECOMPOSE=1 env in
  build_mon_native_song): DMC diverse in BOTH axes (116 pairs/88 FM/70 pulse — Phase-1
  clustering = PROVEN DUD, 0 parts saved at inaudible tolerances); Hubbard FM STRUCTURAL
  (24 shapes flat, pulse drives explosion).
- d3edfd4 Phase 2 pulse_canon: per-instrument pulse canonical un-gated from ARP_STRUCT
  via `pulse_canon` shim flag / MON_PULSE_CANON env. Commando 45->4 parts, Monty 22->4,
  Chimera 76->12, BYTE-EXACT (100/100/100+filter).
- f334fc8/3b8dd68 MoN pulse_canon = opt-in ONLY (Supremacy check failed; later
  corrected: cost = real ~6-16% osc3 pulse, and the "part02 collapse" was my own
  measurement offset error).
- ae59bab **Hubbard track bit7 TRANSPOSE generation decoded** (3 ROM-verified
  encodings; see critical_context) -> Shockway 638->21 parts, Star_Paws 188->10,
  Auf_W 274->43, Saboteur 112->86; span-sanity warning; +test (8 hubbard tests).
- 15147d6 **wave REST-TAIL fix** (shared engine): per-note wave capture extends across
  following rest events + _wave_prog_for cap 96->256. Supremacy sub1 94.3->99.9 EVERY
  register; Cybernoid_II part01 100x3; Cybernoid I wf/pulse 100. Regression sweep clean
  (Hawkeye sub2 100x4, Commando, In_the_Mood).
- 03bbb7b/d6fe158 **fidelity analyser upgrades** (bin/mon_part_fidelity.py): per-voice
  delay refinement (±2), skew-vs-content classification (mismatch matching orig ±1
  frame = inaudible write-phase, separate skew-tolerant score), mismatch-CLUSTER report
  (residual as frame-runs, top 3, for registers <99.5%), part-LOOP auto-cap (40-frame
  all-voice freq self-similarity detects the part replaying its own start).
- e2dee23 MoN corpus rebuilt w/ rest-tail fix; purged 70 STALE parts (Supremacy_sub2
  showed 70 files, real=10); MoN 268->200 files.
- 7347503 builders AUTO-PRUNE stale higher-numbered parts (prune_stale_parts in
  build_mon_native_song, called from mon/hubbard/dmc emit loops).
- 6cb48e2 Hubbard split pulse-speed table (lay.pulsespeed_tbl; transposed class keeps
  speed in a separate stride-8 array, ROM fetch $EE45).
- 0a47001 **pulse_canon GATED to hp_engine builds** — for captured-pulse classes the
  canonical is the ACTUAL pulse and lossy (Shockway osc3 pulse 0.3->100 with it off).
  main() clears it when hp_engine is gated off. Lightforce/Commando verified.
- 2212b4d **CI security scan FIXED after 199 consecutive red runs**: 8 live bandit
  findings repaired for real (dmc_build_all os.system->subprocess argv; installers
  https-enforced + nosec B310; /tmp->tempfile.gettempdir(); database.py identifier
  validation + nosec B608; siddump_extractor nosec B301 justified); workflow excludes
  ./archive. Verified with the exact CI command locally; CI now GREEN.
- 5e0cf78 **v3.16.0** (sidm2/__init__ 3.16.0/2026-07-10; CHANGELOG 3.16.0; CLAUDE.md
  header+history; STORY.md chapter+chain). Full suite **1512 passed**.
- 9d8c05d Hubbard builder HARD-REFUSES mis-decode spans (>2.5x unequal voices OR span
  >900s; HUBBARD_ALLOW_UNEQUAL=1 overrides) — Devils_Galop had begun a 20,975s (5.8h!)
  siddump trace from another unhandled track generation; killed the stuck trace.
Also: cleanup.py --archive mode (moves to archive/cleanup_<date>/ + MANIFEST.txt,
dedupes double-matched files; --clean still deletes); archive/cleanup_2026-07-09/ holds
64+51 archived scratch files; Rockbuster launched in SF2II for the user (argv method);
SOUND MONITOR arc opened (memory/soundmonitor-player.md; MEMORY.md indexed).
Transposed-class diagnosis completed: fetch $EE45 field map (+0/+1 PW, +2 wf, +3 AD,
+4 SR = V1-compatible), pulse engine $EF85-$EFE5 decoded (SELF-MODIFYING rails), osc1
residual = (a) fetch-frame pulsework step (orig starts init+speed) + (b) fx-arp steps
RE-FETCH (PW resets per arp flip; decode holds one longer note). osc2/osc3 pulse = 100.
</work_completed>

<work_remaining>
1. **FINISH THE IN-FLIGHT CORPUS REBUILD** (launched ~2026-07-10 11:30, detached
   PowerShell, log out/_hub_rebuild2.log 0-byte until exit): when `Get-CimInstance
   Win32_Process | ? CommandLine -match hubbard` count = 0 -> run
   `py -3 pyscript/gen_sf2_index.py` -> commit docs/SF2.md -> republish the artifact
   (same file path keeps the URL). Note: this batch ran with the pulse_canon gating +
   transpose fixes; Devils_Galop was killed mid-trace (logs as FAIL, fine); later files
   picked up the new hard span guard automatically.
2. **SOUND MONITOR (the next player — user directive).** memory/soundmonitor-player.md:
   11 Fun_Fun files init=$C000/play=$C475 (+Demo_87_menu $C020 variant); player
   $C000-$CBFA in-image; song data below at $7000/$9000/$A000. START by reading
   ROMUZAK's SOUNDMONITOR_CNV parsing code in out/romuzak_editor_decrunched.prg (entry
   $1000) — a literal reference parser for the SM format; plus bin/'sound monitor/'
   disks and the public 64'er format docs. Then PLAYBOOK: exemplar disasm (play $C475 ->
   JSR $CA17) -> format map -> sidm2/soundmonitor_parser.py -> onset validation ->
   Stage A/B via the shared MoN engine.
3. Transposed-track Hubbard class fidelity (osc1 pulse 27, osc3 wf 70): implement
   (a) fetch-frame pulsework step and (b) fx-arp re-fetch decode (arp steps = separate
   fetches with PW reset). Per-voice engine A/B is the likely shape (osc2=HP proven).
   Devils_Galop/I_Ball/Wiz = ANOTHER track generation to decode (the hard guard now
   refuses their builds instead of tracing hours).
4. DMC: ~21 NO-TABLES left (next shared cluster: 2nd/Skateboard/Tuba, all la=$c367
   init+$0/play+$6); Special_Agent osc2 pulse (57/100/1); Scandalous osc1 pulse 29;
   Predictable wf 50 on 2 voices.
5. Deep_Strike WAVE-overflow count-vs-emit divergence (fits() passed, emit raised
   "WAVE overflow: 258 rows" in gen_includes_song); Hawkeye sub0 filter window-seams;
   MoN safe pulse_canon default (cap window growth by RAW pre-canonical bundle count).
6. Registry-wire the native players into auto sid-to-sf2 (ROADMAP); more corpora staged:
   SID/LFT (Blackbird tracker + player SOURCE in bin/LFT/blackbird-1.2 — highest-
   leverage future player), SID/deenen, SID/Gray_Matt, SID/Gallefoss_Glenn (untracked).
</work_remaining>

<attempted_approaches>
- DMC Phase-1 bundle clustering (BUNDLE_TOL raise): DUD — 0 parts saved at inaudible
  tolerances (bundles genuinely diverse both axes). DO NOT retry for DMC.
- Single-threshold legato heuristics (SIX tried: count ratio, pitch-change ratio,
  gate<=2, gap>FM_CAP, trace-truncation measure): each trades one voice for another.
  Only the FULL-SONG per-voice A/B works (shipped).
- Single-window legato A/B: the 256-row WAVE cap forces a ~10s window; the legato
  benefit only appears past FM_CAP(=5s) over longer windows -> always picks gate.
- MoN pulse_canon default-on: REJECTED (real osc3 pulse loss on Supremacy). NOTE: my
  first "part02 collapses 7-18%" claim was a MEASUREMENT ERROR (wrong window offset —
  pulse_canon shifts part boundaries 0-32/32-38 -> 0-28/28-38). The analyser's loop
  auto-cap + correct offsets now prevent this error class.
- Hubbard transposed class: HUBBARD_FORCE_HP=1 + split speed table = necessary but NOT
  sufficient (osc1 5.6->7.2, osc3 0.3->7.5; osc2 100). The class pulse ENGINE differs
  (per-instrument rails, decoded); ALSO capture path was being ruined by pulse_canon
  (fixed by gating), after which osc3 capture = 100.
- freerun stream misfire hypothesis for osc1: WRONG (debug showed osc1 had no stream).
- Constant-transpose-offset hypothesis for Shockway freq runs: WRONG (pitches verified
  correct; mismatches sit at note boundaries = arp-flip timing).
- gh run list --workflow "CI/CD Pipeline" --jq success filter: the pipeline had NO
  successful run in 200 (chronic, predating this session).
- `git add -A` after a git mv: swept 567 unrelated untracked files into the commit —
  had to reset and force-push-with-lease (247992c replaced by a4e16eb). Stage files
  EXPLICITLY.
</attempted_approaches>

<critical_context>
- ENV: Windows, `py -3`; Bash tool + PowerShell. Long jobs: PowerShell Start-Process
  detached (+ log); Bash bg dies at 10min. PS `*>>` redirect logs are UTF-16 (grep
  fails silently — read via PowerShell Get-Content). Start-Process children inherit
  `$env:` vars set in the same command.
- ONE MoN-ENGINE BUILD AT A TIME (shared drivers_src/mon scratch). After any driver
  build: `git checkout -- drivers_src/mon/layout.inc drivers_src/mon/freqtable.inc
  drivers_src/romuzak/layout.inc`.
- MEASURING: bin/mon_part_fidelity.py <part.sf2> <sub> <secs> [t0_seconds] — pass the
  part's REAL window from the build log; per-voice delay + skew-tolerant + cluster
  report + loop auto-cap built in. TRUST skew classification: 47.7 strict / 100
  skew-tolerant = ±1-frame write jitter = audibly exact (Supremacy sub2 osc2,
  Lightforce osc1). DMC measuring: bin/_dmc_fidelity.py (UNTRACKED scratch — recreate
  from mon_part_fidelity pattern if missing; SF2 wrap = mon_sf2_validate._psid(
  bytes(sf2[2:]), sla, 0x1000, 0x1003)).
- THE FM $40-$43 COLLISION (shared driver): a raw Hz delta whose HIGH byte is $40-$43
  is dispatched as a SCALED-VIBRATO entry -> corrupts the note. Only delta1 =
  trace[onset+1]-base depends on the base note; DMC `_sem` mode `adapt` seats the base
  high when delta1 would collide.
- pulse_canon: hp_engine builds ONLY (V1: captured pulse content unused -> pure bundle
  collapse). Captured-pulse builds (swallow/transposed, hp_engine=0): LOSSY — main()
  force-clears it. MON_PULSE_CANON=1 opt-in for MoN.
- Track bit7 TRANSPOSE encodings (hubbard_parser lay.trk_transpose): 1 = `$80|semis`
  (sig B1 zz 10 ?? C9 FF F0 ?? [C9 FE F0 ??] 29 7F — Shockway $ED99, Star_Paws,
  Saboteur_II); 2 = `$80 nn` next-byte (sig ... C8 B1 zz — Auf_Wiedersehen $E49D).
  Transpose ADDS to (pitch&$7F) at fetch ($EE18: ADC transpose,X).
- Transposed-class pulse engine (Shockway $EF85-$EFE5, SELF-MODIFYING): split record
  $F2F1[i*8]+0=speed (0=static), +2=rails byte — LSR*4 patches the TOP-rail CMP operand
  ($EFB5), AND #$0F patches BOTTOM ($EFCF); dir0: PW+=speed, hi=(hi+c)&$0F, ==TOP->dir1;
  dir1: PW-=speed, ==BOT->dir0. PW AND dir RESET at every note fetch ($EE5A/$EE7B).
  ROM applies ONE pulsework step ON the fetch frame (orig first frame = init+speed).
- Hubbard tracks are SYNCED: equal per-voice one-pass lengths = healthy decode; >2.5x
  unequal or span>900s = mis-decode -> builder now REFUSES (HUBBARD_ALLOW_UNEQUAL=1).
- Wave rest-tail: gate-off rows output program&$fe, so captured $00 rows reproduce the
  engine's mid-rest wave-off; _wave_prog_for cap is 256 (settle-trim keeps hold-tails
  free). WAVE_CAP=96 still gates _gate_split (ARP_STRUCT-only).
- Bandit gate: `bandit -r . -ll -ii -x ./test_converter.py,./archive`. bin/_*.py is
  untracked/ignored (local findings there never hit CI). No os.system / shell=True /
  hardcoded /tmp in TRACKED code.
- cleanup.py: --archive MOVES to archive/cleanup_<date>/ + MANIFEST (use this);
  --clean DELETES (avoid; archive-before-delete protocol).
- SF2II load for the user: `bin/SIDFactoryII.exe --skip-intro <abs path>` (workdir
  bin) — NEVER pyscript/sf2_open_in_editor.py.
- Memories updated this session: johannes-bjerregaard-player, hubbard-player-re,
  myth-supremacy-mon-re, soundmonitor-player (NEW), MEMORY.md index.
</critical_context>

<current_state>
- Repo: master == origin/master @ 9d8c05d, v3.16.0, working tree clean (except live
  rebuild scratch drivers_src/*.inc + untracked corpora SID/Gallefoss_Glenn, bin/LFT,
  bin/SIDDuzz + gitignored out/ artifacts). CI GREEN. 1512 tests pass.
- IN FLIGHT: Hubbard corpus rebuild (detached, `bin/hubbard_build_all.py`, log
  out/_hub_rebuild2.log buffers until exit). On completion: gen_sf2_index.py ->
  commit docs/SF2.md -> republish artifact ef593833-e303-4745-88e5-23190f4eef5b.
- Fidelity state (measured, current builds): Hubbard V1 byte-exact at ~4 parts/song
  (Commando/Monty/Zoids); Supremacy sub1 99.9 every register; Cybernoid_II part01
  100x3; DMC 41/88 eligible (In_the_Mood/M_A_C_H/Fourth_Dimension 100x3); Shockway
  21 parts, osc2/osc3 pulse 100, osc1 27 (fetch-step + arp-refetch residual, decoded).
- File counts (docs/SF2.md, pre-final-rebuild): Hubbard ~529, MoN 200, DMC 236,
  Galway 40, ROMUZAK 4.
- NEXT ARC (user directive): SOUND MONITOR — recon done, ground truth staged
  (ROMUZAK SOUNDMONITOR_CNV), plan in memory/soundmonitor-player.md. Begin with the
  CNV disassembly, then the $CA17 play-body disasm on Dance_at_Night_remix.
- No temporary workarounds in place; everything is committed or documented.
</current_state>
