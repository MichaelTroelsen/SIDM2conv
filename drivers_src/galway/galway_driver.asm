; =====================================================================
; Galway native SF2 driver -- feature selection only.
;
; The engine itself is drivers_src/common/sf2_native_driver.asm, shared with
; the other player(s) in this pair (R1, docs/CODE_REVIEW_2026-07.md). This
; file exists to (a) pick the feature set and (b) keep the per-player path
; and filename that bin/build_*_driver_full.py's assemble() expects -- MoN
; repoints that module's GAL global at its own directory, so the
; <dir>/<name>_driver.asm convention is load-bearing, not cosmetic.
;
; Galway: no drum rows, no SEEK hold, and pulse programs are
; PER-COMMAND (the $c0-$ff command selects the pulse program), so all
; three flags are 0 -- this is the base engine.
;
; layout.inc / freqtable.inc are read from THIS directory: 64tass resolves a
; nested .include relative to the including file, so the builder passes
; `-I <this dir>` for the shared body to find them.
; =====================================================================
FEAT_DRUM_ROWS   = 0
FEAT_SEEK_PULSE  = 0
FEAT_INSTR_PULSE = 0

        .include "../common/sf2_native_driver.asm"
