"""Shared SF2II per-file capacity constants -- single source of truth for the
native-driver build caps and the driver state-region overlap guard.

Promoted from copy-paste (R2, docs/CODE_REVIEW_2026-07.md, 2026-07-30):
``CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100`` was
re-declared byte-for-byte identically in six native song builders
(``bin/build_{dmc,hubbard,mon,myth,sdi,soundmonitor}_native_song.py``), and
``ST_FIRST, ST_LAST = 0x16cc, 0x1702`` was re-declared identically in three
driver-full assemblers (``bin/build_{galway,romuzak,blackbird}_driver_full.py``).
A fix to either needed re-applying by hand in every copy.

Blackbird's own song builder deliberately uses a WIDER ``CAP_B = 96``
(``bin/build_blackbird_native_song.py``, see its own comment there) -- that
stays a local override, not folded in here, since it is a real per-player
choice (Blackbird's combo-fx-index scheme uses more of the command space),
not an accident of copy-paste.

Not yet consolidated here -- documented as a known gap, not migrated (see
docs/CODE_REVIEW_2026-07.md's R2 item): the 960-event sequence-unpack limit
(``sidm2/galway_driver11_emitter.py``'s own ``_SEQ_EVENT_LIMIT``) and the
general "$D000 memory wall" PLAYBOOK.md describes. Both live in the Stage-A/
Driver-11 emitter path, a different subsystem from the native Stage-B
builders below, and migrating them needs their own verification pass.
"""

# --- Native Stage-B builder caps (bundles/instruments/table rows/sequences) ---
# Enforced via each builder's own `fits()` adaptive-windowing probe.
CAP_B = 63      # command bundles ($c0-$ff space): 64 slots, one reserved as a
                # sentinel by players that need it (e.g. Blackbird's
                # RESTART_ARM_FX) -- 63 is the common, non-Blackbird default.
CAP_I = 32      # instruments ($a0-$bf, 32 slots)
CAP_TBL = 256   # WAVE / FILTER table rows (each)
CAP_SEG = 120   # sequences (the native seq-pointer table holds 128 entries;
                # 120 leaves margin so a part laid out last never overflows)
STEP = 100      # adaptive-window probe step, in rows/ticks (~2s at typical
                # tempos -- the size of each doubling attempt while searching
                # for the widest window that still fits under the caps above)

# --- Driver state-region overlap guard (build_*_driver_full.py's assemble()) ---
# SF2II reads/writes this fixed range every frame; driver code or tables
# spilling into it corrupts playback state and crashes the editor on play.
ST_FIRST = 0x16CC
ST_LAST = 0x1702
