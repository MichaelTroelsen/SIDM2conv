"""Shared building blocks for the native Stage-B song builders.

Extracted (R3, docs/CODE_REVIEW_2026-07.md, 2026-07-30) from the three
`gen_includes_song` implementations in ``bin/build_{galway,romuzak,blackbird}
_native_song.py``.

WHAT IS **NOT** HERE, AND WHY. The review's A2 item described
`gen_includes_song` as "a ~180-line identical skeleton". Measured against the
actual code, that is not accurate and this module deliberately does not try to
unify the whole function: the three signatures take genuinely different data
(Galway `fm_data`/`filter_lead`/`pulse_by_cmd`; ROMUZAK `wave_programs`/
`pulse_programs`/`drum_set`/`seek_set`/`bundles`; Blackbird `ad_sr`/
`filter_flag_of`/`fx_start`/`fxtab`/`default_filter_program`/`tempo_sched_len`),
and the middle of each function writes per-player instrument columns and lays
out per-player tables. Those differences are the per-player engine deltas
PLAYBOOK.md §2 describes, not copy-paste. Forcing them through one signature
would produce a function with a dozen mutually-exclusive flags -- worse than
three honest ones.

What IS genuinely duplicated, and is therefore here:

1. **The prologue** (22 lines, byte-identical in all three, differing only in
   `gen.driver_name`): SF2HeaderGenerator setup, the Block-2 playback-state
   contract, the placeholder edit area, and the packed-sequence slot writes.
   See `make_native_gen` + `lay_out_sequences`.

2. **The relative->absolute jump-target fixup** for wave/filter/pulse program
   rows -- ONE expression, hand-copied five times across the three files, and
   the site of a real shipped bug: `build_blackbird_native_song.py`'s own
   19-line comment (search "B3 BUG FOUND") records that its default-filter
   block used `(r + b2)` -- the row's own local index -- instead of
   `(start + b2)`. It survived because a 2-row program's wrong target
   coincidentally equals the jump row's own index, which the driver's
   `fp_read` treats as an intentional self-freeze, so Fargo still froze at the
   correct value. Any program longer than 2 rows would have jumped somewhere
   entirely wrong. `program_jump_col` exists so that arithmetic has exactly
   one definition. See its docstring for the invariant.
"""

from sidm2.sf2_header_generator import SF2HeaderGenerator
from sidm2 import placeholder_edit_area

# The Block-2 playback-state contract the native drivers implement, so SF2II's
# start/stop and follow-play work. Both addresses are read/written by SF2II
# every frame; the drivers' own ST_STATE/ST_TCNT must agree with these (see
# e.g. galway_driver.asm). Part of the $16CC-$1702 state region guarded by
# sidm2.sf2_caps.ST_FIRST/ST_LAST.
NATIVE_STATE_ADDR = 0x16D0      # $80 playing / $40 stopped
NATIVE_TCNT_ADDR = 0x16D1       # 0 on each new row (follow-play)

# Every native builder lays its packed sequences one per 256-byte slot -- SF2II's
# editor reads sequences from fixed slots, not via the pointer table, so packing
# them contiguously makes a slot read run across several with no early $7F (see
# galway_driver11_emitter.emit_driver11_sf2's own comment on the same hazard).
SEQ_SLOT_STRIDE = 0x100

# The jump/terminator opcode in a wave/filter/pulse program's column 0.
PROGRAM_JUMP_OP = 0x7F


def make_native_gen(driver_name, init, play, stop,
                    code_top=0x1000, version_major=17, version_minor=0):
    """An SF2HeaderGenerator configured for a native Stage-B driver.

    `driver_name` is the ONLY thing that differed between the three copies of
    this block. `version_major=17` is the native drivers' shared F12 overlay
    slot (bin/overlay/*_driver17_00.png).

    PLAYER_ADDRESSES is copied before mutation so the class default is never
    modified -- the original Galway code called this out explicitly and it
    matters: SF2HeaderGenerator is instantiated per build, but the dict is a
    class attribute shared across every instance in the process (a single
    corpus run builds dozens of songs).
    """
    gen = SF2HeaderGenerator()
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = init, play, stop
    gen.PLAYER_ADDRESSES = dict(gen.PLAYER_ADDRESSES)
    gen.PLAYER_ADDRESSES["driver_state"] = NATIVE_STATE_ADDR
    gen.PLAYER_ADDRESSES["tempo_counter"] = NATIVE_TCNT_ADDR
    gen.driver_name = driver_name
    gen.driver_version_major = version_major
    gen.driver_version_minor = version_minor
    gen.driver_code_top = code_top
    return gen


def lay_out_sequences(segs, gen, edit_base):
    """Build the placeholder edit area for `segs` and write the packed sequences
    into their fixed slots. Returns (edit: bytearray, mdp: dict, seq0: int).

    `segs[v]` is voice v's list of packed sequences. The voice_streams passed to
    build_placeholder_edit_area are structural ONLY -- their content is
    immediately overwritten below; all that matters is that voice v segments
    into exactly len(segs[v]) patterns so the orderlist comes out the right
    shape. (`$01` note, then `$A0 $01` -- set-instrument + note -- per extra
    segment, which is what forces a new pattern boundary.)

    Sequences are laid one per SEQ_SLOT_STRIDE-byte slot, numbered globally
    across voices in voice order (voice 0's patterns first, then voice 1's,
    ...), matching every native driver's layout.inc SEQ<v> symbols.
    """
    vstreams = [bytes([0x01]) + bytes([0xA0, 0x01]) * (len(segs[v]) - 1)
                for v in range(3)]
    edit, mdp = placeholder_edit_area.build_placeholder_edit_area(
        edit_base, gen, voice_streams=vstreams)
    edit = bytearray(edit)
    seq0 = mdp['seq00_addr']
    off = 0
    for v in range(3):
        for s, pk in enumerate(segs[v]):
            o = (seq0 + (off + s) * SEQ_SLOT_STRIDE) - edit_base
            edit[o:o + len(pk)] = pk
        off += len(segs[v])
    return edit, mdp, seq0


def program_jump_col(col0, col_last, start):
    """The last column's byte for one wave/filter/pulse program row.

    A program's rows are emitted into a shared 256-row table at an arbitrary
    `start`, but a program's own jump row names its target RELATIVE to that
    start (so identical programs dedup to one copy regardless of where they
    land). The driver reads an ABSOLUTE row, so a `$7F` jump row's target -- and
    ONLY a jump row's -- must have `start` added:

      col0 == $7F  -> absolute target = start + col_last
      otherwise    -> col_last is data (semitone offset / duration), used as-is

    `start` is the PROGRAM's start row, never the current row's index. Adding a
    row-local index instead is exactly the bug documented in
    build_blackbird_native_song.py's "B3 BUG FOUND" comment -- it is silent for
    2-row programs (the wrong target equals the jump row's own index, which the
    driver treats as an intentional self-freeze) and wrong for longer ones.
    """
    return ((start + col_last) if (col0 & 0xFF) == PROGRAM_JUMP_OP
            else col_last) & 0xFF
