<original_task>
Convert ROMUZAK V6.3 (Oliver Blasnik) SID tunes to editable Driver-11 SF2, the next
player after Future Composer. Two corpus tunes: Delirious_9_tune_1 ($2BFE) and
Road_of_Excess_end ($2C00), both Michael Troelsen / Fun Fun. "Start with delirious_9";
do both. Standing goal (same as FC): notes correct, song-order correct, sound fidelity.
(Earlier in the same session: FC timbre — trace-driven pulse + filter — and the FC
structured-orderlist breakthrough with an SF2II rebuild. Those are DONE + committed.)
</original_task>

<work_completed>
ROMUZAK fully reverse-engineered + a working converter, all committed/pushed to master:
- 79b6cfd: first converter, Delirious notes validated.
- 75684a4: structured per-sector orderlist (song patterns) — fixes "song order".
- d2e841c: B7 sound effects — arpeggios + SEEK pulse sweep.
- a29ffe6: drums (B7 bit0) from the $2D60 drum table.
- 3ccdfb9: docs/players/ROMUZAK.md + tests + README.

RE (3 agreeing sources): (1) player disasm (py65 Disassembler) of the $2BFE rip;
(2) DECRUNCHED EDITOR — `bin/RoMusak/romuzak    -nato.prg` decompressed WITHOUT VICE by
emulating the depacker in py65 (load $0801, run from $080B, step until PC leaves the
decruncher -> editor entry $1000, dump $0800-$FFFF -> out/romuzak_editor_decrunched.prg;
no copy-protection issue since we never RUN it); (3) the official manual
`bin/RoMusak/romuzak.txt`. The editor's CONVERTER has FUTURE-COMPOSER + SOUNDMONITOR
import routines (reference mappings).

CONVERTER `bin/romuzak_to_sf2.py` (reuses the FC/Galway IR + emitter + silent anchors):
- `_find_tables(d)`: locate TRACK ptrs / SECTOR ptrs / DRUM-ARP ptrs by the player-code
  signature `B9 lo hi 85 F8` (1st/2nd/3rd occurrence) = $3640/$3676/$2D60; SOUND table =
  sector_ptrs+0x80 = $36F6. Relocation-safe (Road shares the same absolute addresses).
- `RMZ`: decode TRACK orderlists + SECTOR patterns + 8-byte SOUNDS + drum sequences.
- `build_structured`: one Driver-11 sequence per SECTOR + per-voice orderlist (real
  patterns), cur_instr=None per sector (dedup-safe), silent anchors for PSE-00 intro.
- `build_instruments`: B7 effects -> arp (4 semitones in next sound row), drum (per-frame
  waveform/pitch from $2D60[B4]), SEEK pulse ramp, ->pulse. Tempo = SF2II 5.

VALIDATED (Delirious, vs original siddump, play=$2C03): osc2 92/93, osc3 113/113 notes;
structured orderlist 31/22/22 sectors -> 30 sequences; plays in real SF2II (372 frames).
out/romuzak/Delirious_9_tune_1.sf2. 4 ROMUZAK tests + all FC tests green. Full format
spec in docs/players/ROMUZAK.md and the `romuzak-player-re` memory.
</work_completed>

<work_remaining>
1. ROAD_OF_EXCESS doesn't validate yet (osc prefix 0). Two per-tune fixes:
   - BASE: calibrate_base centers the median PER TUNE (wrong). Delirious worked at
     base 0 (ROMUZAK note == SID semitone). Use a FIXED base (likely 0) for all tunes,
     or derive from the freq table; verify Road then matches.
   - TEMPO: hardcoded to Delirious's (SF2II 5). Find the SET-SPEED byte (player reads it;
     the $2C6F reload was a hardcoded #$03 4-frame divider, so SPEED is applied elsewhere
     — find it) and set tempo per tune. (Road's real play is $2C03, not init+5 — its
     wrapper omits the LDA #subtune prefix.)
2. SOUND FIDELITY (Stage-A polish, user wants it; all FC-style):
   - Drum PITCH: the $2D60 (waveform,value) value -> abs semitone mapping is a guess
     ($80|value); verify vs the original drum freq. osc3 waveform still ~30%.
   - Arp PHASE/order: currently +12/+7/+3/+0 from the next sound row; try the reverse /
     root-first; per-frame phase won't match frame-exact (Stage-A limit).
   - TRACE-DRIVEN pulse + filter: reuse fc_to_sf2._trace_pulse_programs /
     _trace_filter_program (they siddump the original and replay sweeps — player-agnostic).
   - Pulse/freq-vibrato (B5/B6), CONT/GLD/APM, FILTER (B7 bit5; none in Delirious).
3. Validate Road note-for-note; then both tunes by-ear in SF2II.
</work_remaining>

<attempted_approaches>
- Hardcoding Delirious table addresses -> broke Road (relocated). FIXED via the
  `B9 ..,Y;STA $F8` signature scan (both rips share $3640/$3676/$36F6/$2D60 absolute).
- The "BD ..,X;STA $F8" sound-table signature found the wrong instruction ($2C92);
  use sound = sector_ptrs + 0x80 instead.
- Validating Road with play=la+5 ($2C05) -> 0 notes. Road's real play is $2C03.
- Tempo sweep: tempo 5 gives Delirious osc3 113/113; tempo 2-4 too fast.
- Arp + drum decode barely moved the sf2ii_vs_real metric — per-frame effects are
  Stage-A-approximate (same as FC); judge by ear, not the frame-exact metric.
</attempted_approaches>

<critical_context>
- COMMANDS: rebuild `py -3 bin/romuzak_to_sf2.py SID/Fun_Fun/Delirious_9_tune_1.sid
  out/romuzak/Delirious_9_tune_1.sf2`; tests `py -3 -m pytest
  pyscript/test_romuzak_to_sf2.py -q`; note-validate by wrapping the SF2 as a PSID probe
  (load=parse_sf2_blocks, init=$1000/play=$1006) and the original as PSID (init=load,
  play=$2C03) and diffing siddump_complete note onsets; timbre `py -3 bin/sf2ii_vs_real.py
  <orig.sid> <ours.sf2> 14`; play in SF2II via bin/SIDFactoryII.exe --skip-intro cwd=bin.
- ROMUZAK = an EXPANDED Future Composer (manual: "Umsteigern vom Future Composer"); the
  whole FC pipeline maps over (orderlist->sectors->8-byte sounds, B7 ~= mctrl).
- FC TIMBRE + STRUCTURED ORDERLIST (earlier this session) are DONE: trace-driven pulse
  (Carillo lead 28->92%) + filter (res/route ->100%), and the structured per-block
  orderlist is the FC D11 default after the SF2II fixed-slot fix (root cause: SF2II reads
  sequences from fixed editor slots, not the pointer table — found by rebuilding SF2II
  with PC/load probes). See the future-composer-player memory.
- SF2II DEBUG PROBES still in the Downloads source tree (PCSPIN/PLAYPROBE/seqpull in
  cpuframecapture/executionhandler/screen_edit/datasource_*); bin/SIDFactoryII_dbg.exe is
  the instrumented build. Revert + rebuild (build_release via 2022 vcvarsall+msbuild) for
  a clean dbg if desired — they only affect the capture tool, not the shipping exe.
- The OTHER Fun_Fun players: 12 = SoundMonitor ($C000 player; user also dropped
  `bin/sound monitor/`), 1 unknown (Byte_Bite). ROMUZAK's SOUNDMONITOR_CNV is a reference.
</critical_context>

<current_state>
- Delirious: notes + song-order VALIDATED, plays in SF2II; sounds structurally decoded
  (arp/drum/SEEK/->pulse) but Stage-A-approximate. out/romuzak/Delirious_9_tune_1.sf2.
- Road: decodes (627/776/565 events) but notes don't line up — needs fixed base +
  per-tune tempo. out/romuzak/Road_of_Excess_end.sf2 exists (wrong base/tempo).
- All committed/pushed (latest 3ccdfb9). 4 ROMUZAK + all FC tests green.
- Untracked: bin/RoMusak/ (editor PRG, D64, manual), bin/sound monitor/, the dbg exe,
  out/* artifacts (gitignored). bin/RoMusak reference NOT committed (large binaries) —
  romuzak.txt + the decrunched editor are regenerable/referenced in docs.
- Loaded in SF2II for the user to judge by ear: Delirious with arps + drums + SEEK.
</current_state>
