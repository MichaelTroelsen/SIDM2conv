"""The Laxity $80-$9F duration byte, pinned against the player's own 6502.

WHY THIS FILE EXISTS. Three modules in this repo decoded this one byte range
three different ways, and all three were wrong:

    sidm2/sequence_translator.py   (b & $1F) + 1   right +1, WRONG mask
    sf2_viewer_core.unpack_sequence b & $0F        right mask, NO +1
    CLAUDE.md's constants           $80 = GATE_OFF  not a duration at all

None of them could settle it, because each was only evidence about itself. The
ground truth is drivers/laxity/laxity_player_disassembly.asm -- a SIDwinder
disassembly of a native NP21 rip -- and it says:

    bpl <skip>              bit 7 clear -> not a duration byte
    cmp #$90 / bcc          bit 4 -> bumps a SEPARATE flag at $100,X
    and #$0F                the COUNT is the low nibble only
    sta $FD,X               ...stored, then copied to the per-voice counter $EE,X
    dec $EE,X / bpl         the row advances when the counter goes NEGATIVE

A stored n therefore survives n decrements and advances on the n+1th:

    duration = (byte & $0F) + 1 frames, i.e. $80..$8F -> 1..16.

THE MASK IS NOT A COSMETIC DIFFERENCE. 232 of 1,708 duration bytes across
SID/Laxity/ carry bit 4, so `$1F` made roughly one duration in seven up to
16 frames too long.

BIT 4 IS NOT A DURATION INPUT AND IS NOT PURELY A TIE. The same $100,X flag is
also bumped when the NOTE byte is $00 or $7E, so it is a shared gate/continue
flag. `tie` is a workable name for it in a decoder; it is not the player's model.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2.sequence_translator import LaxitySequenceParser  # noqa: E402


def durations(*seq_bytes):
    """Decode a raw sequence and return its per-event durations."""
    p = LaxitySequenceParser()
    return [e.duration for e in p.parse_sequence(bytes(seq_bytes))]


def test_the_low_nibble_plus_one_is_the_frame_count():
    """$80 is ONE frame, not zero and not 32. $8F is sixteen."""
    assert durations(0x80, 0x30, 0x7F)[0] == 1
    assert durations(0x81, 0x30, 0x7F)[0] == 2
    assert durations(0x8F, 0x30, 0x7F)[0] == 16


def test_bit_4_is_NOT_folded_into_the_count():
    """THE REGRESSION THIS FILE EXISTS FOR. Under the old `& $1F` mask, $90
    decoded as 17 frames; the player reads its low nibble and gets ONE, using
    bit 4 for a separate flag entirely. This is the assertion that fails if the
    mask is widened back."""
    assert durations(0x90, 0x30, 0x7F)[0] == 1, "bit 4 leaked into the duration"
    assert durations(0x9F, 0x30, 0x7F)[0] == 16, "bit 4 leaked into the duration"


def test_a_bit_4_byte_and_its_bare_twin_agree_exactly():
    """The pairwise form of the same rule, which a single-value assertion can
    pass by coincidence: $8n and $9n must decode to the SAME count for every n."""
    for n in range(16):
        bare = durations(0x80 | n, 0x30, 0x7F)[0]
        flagged = durations(0x90 | n, 0x30, 0x7F)[0]
        assert bare == flagged == n + 1, (n, bare, flagged)


def test_the_whole_range_is_1_to_16_and_never_32():
    """POSITIVE CONTROL on the range itself. `& $1F` produced 1..32; the correct
    reading can never exceed 16, so an out-of-range value is a mask regression
    even if the individual cases above were edited to match it."""
    got = {durations(b, 0x30, 0x7F)[0] for b in range(0x80, 0xA0)}
    assert got == set(range(1, 17)), sorted(got)


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN DIVERGENCE, not yet fixed: the parser resets current_duration to 1 "
    "after every note, but the player does NOT. Row advance reloads the counter "
    "from $FD,X every row (`lda DataBlock_6+$FD,X / sta DataBlock_6+$EE,X` at "
    "$1102), and $FD,X is written ONLY when a $80-$9F byte arrives -- so the "
    "last count persists across following notes. strict=True so that fixing it "
    "fails here and forces this marker to be removed."))
def test_a_duration_persists_until_the_next_duration_byte():
    """THE PLAYER'S RULE, recorded as an expected failure rather than pinned.

    Writing the current behaviour into an assertion would freeze a defect this
    file was created to expose. `durations(0x84, 0x30, 0x31, 0x32, 0x7F)`
    currently returns [5, 1, 1, 1]; the player would hold 5 across all three
    notes.
    """
    ds = durations(0x84, 0x30, 0x31, 0x32, 0x7F)
    assert ds and all(d == 5 for d in ds), ds


def test_the_parser_still_terminates_on_7F():
    """Cheap, and it is the failure that would make every assertion above read
    an empty list and pass vacuously.

    $7F emits an explicit END event (note=SF2_END, duration=1) and then stops --
    it is not a silent break, which is why this asserts a length of 1 rather
    than an empty list. Bytes after it are not decoded.
    """
    assert len(durations(0x7F)) == 1
    assert len(durations(0x84, 0x30, 0x7F, 0x31)) == 2   # the note, then END


@pytest.mark.parametrize("byte", [0x80, 0x88, 0x8F, 0x90, 0x98, 0x9F])
def test_no_duration_is_ever_zero(byte):
    """A zero-frame row is unplayable and is what a missing +1 produces."""
    assert durations(byte, 0x30, 0x7F)[0] >= 1


# ---------------------------------------------------------------------------
# The frequency table, located by SEARCH rather than by the $0835 constant.
#
# WHY. The constant addresses a strictly-ascending table on ZERO of 242 corpus
# files whose data is long enough to contain one, and it is two bytes past the
# base even on the two files where the ADDRESS is otherwise right: the player
# reads `LDA $1833,Y` / `LDA $1834,Y` at four sites in Angular, while $1835 is
# the SECOND read, used at $14A4 to compute table[n+1] - table[n]. Entry 0 is
# $0116 (a C), not $0127 (the C# one semitone up).
# ---------------------------------------------------------------------------

import struct  # noqa: E402

from sidm2.sequence_translator import (  # noqa: E402
    LaxityFrequencyTable,
    locate_frequency_table,
    read_frequency_table,
    LAXITY_FREQ_TABLE_ADDR,
    LAXITY_FREQ_TABLE_SIZE,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# An equal-tempered scale: 96 notes, twelve to the octave, doubling each octave.
SCALE = [min(0xFFFE, int(round(0x0116 * (2.0 ** (i / 12.0))))) for i in range(96)]


def interleaved(table, lead=b'', tail=b''):
    body = b''.join(struct.pack('<H', v) for v in table)
    return lead + body + tail


def split(table, lead=b'', tail=b''):
    return (lead + bytes(v >> 8 for v in table)
            + bytes(v & 0xFF for v in table) + tail)


def load_sid(path):
    b = open(path, 'rb').read()
    _, dataoff, la, _, _ = struct.unpack('>HHHHH', b[4:14])
    d = b[dataoff:]
    if la == 0:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return la, d


def test_an_interleaved_table_is_found_with_its_address_and_its_size():
    data = interleaved(SCALE, lead=b'\x4c\x00\x10' * 40, tail=b'\x00' * 40)
    loc = locate_frequency_table(data)
    assert loc is not None
    off, size, layout = loc
    assert layout == 'interleaved'
    assert off == 120                      # the address, not a constant
    assert size == 96                      # and the SIZE, which the constant assumed
    assert read_frequency_table(data, loc) == SCALE


def test_a_split_hi_then_lo_table_is_found_too():
    data = split(SCALE, lead=b'\xea' * 33, tail=b'\x00' * 20)
    loc = locate_frequency_table(data)
    assert loc is not None
    off, size, layout = loc
    assert layout == 'split'
    assert off == 33
    assert size == 96
    assert read_frequency_table(data, loc) == SCALE


def test_an_ascending_run_that_is_not_a_scale_is_refused():
    """The shape that defeats a pure ascending-run search.

    Stinsen and Broware each carry a 38-entry strictly ascending run of packed
    counters ($0303, $0403, $0404, $0504 ...). It ascends; it is not music, and
    the octave test is what says so.
    """
    counters = [0x0303 + (i * 0x0101) for i in range(60)]
    data = b'\x00' * 16 + interleaved(counters) + b'\x00' * 16
    assert locate_frequency_table(data) is None


def test_a_leading_zero_entry_does_not_move_the_base():
    """A zero in front of the table still ascends into it -- and is not a note."""
    data = b'\x00' * 8 + interleaved(SCALE) + b'\x00' * 8
    off, size, layout = locate_frequency_table(data)
    assert off == 8                        # the first REAL entry
    assert read_frequency_table(data, (off, size, layout))[0] == 0x0116


def test_the_two_bytes_before_the_base_are_not_taken_as_the_base():
    """The base is where the scale starts, not where an ascending run can start."""
    data = b'\x01\x00' + interleaved(SCALE) + b'\x00' * 8
    off, size, layout = locate_frequency_table(data)
    assert read_frequency_table(data, (off, size, layout))[0] == 0x0116


def test_data_with_no_table_returns_None_rather_than_a_guess():
    assert locate_frequency_table(b'\xea' * 4096) is None


def test_the_constant_is_the_fallback_and_only_the_fallback():
    """Pins the compatibility that keeps the legacy synthetic-buffer path alive.

    scripts/test_converter.py builds a buffer holding three entries at $1835 and
    nothing else. No table can be LOCATED in it, so the fallback must still read
    96 entries from the constant -- otherwise this change would silently break a
    caller in a file this task may not edit.
    """
    off = LAXITY_FREQ_TABLE_ADDR - 0x1000
    buf = bytearray(off + LAXITY_FREQ_TABLE_SIZE * 2)
    buf[off + 0], buf[off + 1] = 0x58, 0x04
    buf[off + 90], buf[off + 91] = 0x44, 0x1D
    assert locate_frequency_table(bytes(buf)) is None
    ft = LaxityFrequencyTable(bytes(buf), 0x1000)
    assert ft.table_layout == 'fallback-constant'
    assert len(ft.frequencies) == 96
    assert ft.frequencies[0] == 0x0458
    assert ft.frequencies[45] == 0x1D44


@pytest.mark.parametrize('name,addr,layout', [
    ('SID/Angular.sid', 0x1833, 'interleaved'),
    ('SID/Omniphunk.sid', 0x1833, 'interleaved'),
    ('SID/Stinsens_Last_Night_of_89.sid', 0x16A1, 'split'),
])
def test_real_rips_resolve_to_the_address_the_player_itself_reads(name, addr, layout):
    path = os.path.join(REPO, name)
    if not os.path.exists(path):
        pytest.skip(f'{name} not in this checkout')
    la, data = load_sid(path)
    ft = LaxityFrequencyTable(data, la)
    assert ft.table_layout == layout
    assert la + ft.table_offset == addr
    assert ft.table_size == 96
    assert ft.frequencies[0] == 0x0116
    assert all(ft.frequencies[i] < ft.frequencies[i + 1] for i in range(95))


def test_a_run_that_doubles_every_octave_but_is_not_a_SCALE_is_refused():
    """The octave test alone is not enough, and this is the case that shows it.

    These values double exactly every twelve entries -- perfect octave score --
    but the steps inside each octave are ratios of 1.001, nothing like the
    2**(1/12) of a semitone. Without the semitone threshold the locator accepts
    it and reports a frequency table that is not one.
    """
    fake = [(300 + 3 * (i % 12)) * (2 ** (i // 12)) for i in range(72)]
    assert all(fake[i] < fake[i + 1] for i in range(71))          # ascending
    pairs = [(fake[i], fake[i + 12]) for i in range(60)]
    assert all(abs(b - 2 * a) <= 2 for a, b in pairs)             # octave-exact
    data = b'\x00' * 16 + interleaved(fake) + b'\x00' * 16
    assert locate_frequency_table(data) is None


def test_a_located_table_reaches_fourteen_semitones_above_the_SF2_range():
    """Why the top of the note clamp can never stop firing.

    A Laxity table is 96 notes starting on $0116 = MIDI 12, so its last entry is
    MIDI 107 -- fourteen semitones above SF2's B-7 (93). Measured over the 236
    tables located in SID/Laxity, 231 have EXACTLY 14 entries above 93 and NONE
    has an entry below 0. So 'make the clamp firings go to zero' is unreachable
    by construction, and a report of clamping on a high note is not evidence
    that the table was located wrongly.
    """
    ft = LaxityFrequencyTable.__new__(LaxityFrequencyTable)
    ft.frequencies = SCALE
    notes = [ft.frequency_to_sf2_note(f) for f in SCALE]
    assert notes[0] == 12                       # entry 0 is a C, MIDI 12
    assert notes[81] == 93                      # the last one SF2 can name
    assert all(n == 93 for n in notes[82:95])   # 13 more clamp, plus the
    assert notes[95] == 93                      # clamped top entry = 14
    assert min(notes) == 12                     # nothing clamps at the bottom
