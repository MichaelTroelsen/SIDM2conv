<original_task>
Reverse-engineer the Hawkeye/Maniacs-of-Noise (Jeroen Tel / "MoN") music player, build a
SID->SF2 converter, extend to Cybernoid + Cybernoid_II (same MoN engine). Standing goal:
notes/order correct, then SOUND FIDELITY via a native SF2 driver that loads in stock SID
Factory II (SF2II). This session's focus: FIX the Cybernoid LEAD ("track 1") which the USER
reported "sounds wrong when vibrating" (track 2 is fine).
Targets: SID/Tel_Jeroen/{Hawkeye,Cybernoid,Cybernoid_II}.sid.
</original_task>

<work_completed_this_session>

=== ROOT CAUSE of the "lead wrong when vibrating" FOUND + FIXED = SBC CARRY BUG ===
It was NOT multispeed (the previously-approved fix — DISPROVEN, see below), NOT the driver,
NOT cycle-timing. It was a bug in `sidm2/cpu6502_emulator.py` (the CPU behind
`siddump_complete.py`): SBC set carry-out from `temp < 0x100` where `temp = A-value-borrow`
is in [-256,255] -> carry ALWAYS SET after SBC -> broke 16-bit subtraction chains
(SEC;SBC lo;SBC hi). MoN's vibrato IS such a chain, so siddump computed a too-wide vibrato,
and the native driver (built FROM siddump) replayed the wrong vibrato.
FIX: carry = `temp >= 0` (both binary + decimal SBC branches).
COMMITTED (branch fix-siddump-sbc-carry): the fix + `pyscript/test_cpu6502_sbc.py` (5 SBC
regression tests incl. a 16-bit borrow chain that fails on the OLD code).

=== HOW FOUND (methodology, reusable) ===
- Disproved multispeed: `bin/_mon_multispeed_probe.py` (INIT then PLAY, watch only $D400/1) =
  exactly 1 V0 pitch/frame across 3000 frames. MoN is single-speed. The old "3 pitches/frame"
  was the 3 VOICES' freq writes misattributed to V0.
- Refuted register-value + write-timing theories: native is byte-exact per-frame (siddump);
  whole-burst delay + voice-major order both = zero change in VICE.
- KEY: py65 (correct 6502) vs siddump DISAGREED on the vibrato values -> lockstep CPU diff
  `bin/_mon_cpu_diff.py` pinned it to SBC $F9 (A off by 1 = carry). Fixed, both now agree.

=== VALIDATION ===
- VICE A/B (`bin/listen_compare.py SID/Tel_Jeroen/Cybernoid.sid <native.sid> 6 1`; build the
  native .sid via `bin/_mk_probe.py <part.sf2> out/x.sid`): native-vs-original spectral-dist
  0.331 -> 0.189. (py65-valued regreplay floor = 0.168 = the small remaining schedule effect.)
- Hawkeye sub3 = 100/100/100 byte-exact (compare ONLY the song length ~2s; post-song-end
  silence tanks a longer window). All 1443 pyscript tests pass.
- Rebuilt from corrected siddump: Cybernoid sub0 = 11 parts, Cybernoid_II = 13 (no inflation).
  out/mon/*.sf2 (gitignored).
</work_completed_this_session>

<work_remaining>

=== REMAINING RESIDUAL (~0.168 VICE spectral-dist) — optional, smaller ===
The original writes the LEAD (V0) freq LATE in the frame (cycle ~1838 = 9.4% of the frame;
V2 at ~1.5%, V1+filter at ~5% — see `bin/_mon_write_schedule.py`). The native bunches all
writes at frame start. During fast vibrato this intra-frame SCHEDULE difference, into the
high-resonance filter, is the remaining gap. Order + absolute-position are refuted; the lever
is inter-write SPACING/late-V0. A cycle-scheduled or procedural driver could close it, but
it's much smaller than the (now-fixed) SBC effect. Decide after a GUI/ear check whether it's
worth it.

=== NEXT (per user "continue") ===
1. (in progress) Investigate/close the ~0.168 schedule residual OR confirm the fix by ear in
   SF2II first (`py -3 pyscript/sf2_open_in_editor.py out/mon/Cybernoid_sub0_part01.sf2 40`;
   argv Heisenbug -> retries; native play=$1003).
2. Pulse still not visible/editable in SF2II (driver-internal bundle; editable pulse table is
   a static $800 placeholder). Separate, larger change.
3. Roadmap after Cybernoid: Myth + Supremacy (memory/myth-supremacy-mon-re.md — Myth is a
   relocating multi-tune compilation, play=$0000 self-IRQ; both need their own setup RE).
</work_remaining>

<attempted_approaches_ruled_out>
- MULTISPEED=3 (DISPROVEN — no intra-frame multispeed; the prior "proof" was a measurement
  artifact mixing the 3 voices' freq writes). DO NOT BUILD.
- SID model 6581/8580 (user ruled out). Write-ORDER voice-major (zero WAV change). INTRA-FRAME
  whole-burst write timing (delay ~1785 cyc -> zero change). EMBED original player (SF2II
  crashes 0xC0000005). All in memory/cybernoid-mon-orderlist-re.md.
- META-LESSON: siddump (1 sample/frame) can look byte-exact while the audio is wrong; the
  wrongness can be in the CAPTURE tool's CPU (the SBC bug) OR intra-frame schedule. Cross-check
  siddump vs py65 (values) and VICE (cycle-accurate audio) — don't trust siddump alone.
</attempted_approaches_ruled_out>

<critical_context>
- FIX FILE: `sidm2/cpu6502_emulator.py` sbc() — carry now `temp >= 0` (was `temp < 0x100`).
  Guarded by `pyscript/test_cpu6502_sbc.py`.
- BUILD/TEST: `py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Cybernoid.sid 0 auto`
  (adaptive parts) or `... 0 38` (fixed 38s parts for quick tests). `py -3 -m pytest
  pyscript/test_mon_parser.py pyscript/test_mon_to_sf2.py pyscript/test_cpu6502_sbc.py -q`.
  Native fidelity (part vs original, siddump): `bin/mon_part_fidelity.py PART SUB SECS T0`.
  VICE ear-equivalent: `bin/listen_compare.py`. Cycle diff: `bin/_mon_cpu_diff.py`.
- KEY FILES: `bin/build_mon_native_song.py` (build/emit), `drivers_src/mon/romuzak_driver.asm`
  (native driver; layout.inc/freqtable.inc are BUILD-SCRATCH -> git checkout before commit),
  `sidm2/mon_parser.py` (parser, 3 orderlist variants).
- MEMORY: memory/siddump-sbc-carry-bug.md (the fix, project-wide), cybernoid-mon-orderlist-re.md
  (full diagnosis + all ruled-out approaches), hawkeye-mon-*.md, myth-supremacy-mon-re.md.
</critical_context>

<current_state>
- SBC fix + regression test COMMITTED on branch `fix-siddump-sbc-carry` (off master). out/ is
  gitignored; build-scratch .inc reverted. bin/SIDFactoryII_dbg.exe was already-modified
  (pre-existing, NOT part of this work) — left out of the commit.
- The Cybernoid lead vibrato is largely FIXED (VICE 0.331->0.189). Not yet GUI/ear-confirmed
  by the user in SF2II. The ~0.168 residual (late-V0 write schedule) is open + smaller.
- User said "commit and then continue" -> committing done; continuing on the residual /
  confirmation next.
</current_state>
