"""Tests for `sf2_viewer_core`'s driver detection.

The corpus (SF2/, out/hardtrack/) is on disk here, so these run against real
files rather than synthetic headers -- which matters, because the bug they pin
was invisible to any synthetic test: it turned on a constant that is identical
in every SF2 ever written.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)


# --------------------------------------------------------------------------
# Driver detection. $0D7E is the SF2 CONTAINER load address, shared by every
# driver, so it cannot identify one.
# --------------------------------------------------------------------------

def _sf2(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *parts)


def test_normalize_driver_name_folds_screen_codes():
    """Driver names ship in two encodings and only one is ASCII.

    `Angular.sf2` stores L,$01,$18,$09,$14,$19 -- screen codes for A-Z --
    while `Balance.sf2` stores plain "Laxity". A substring test against the
    display string alone silently misses every screen-code file, which is how
    the first attempt at this fix un-detected genuine Laxity SF2s.
    """
    from sf2_viewer_core import SF2Parser
    assert SF2Parser._normalize_driver_name('L\x01\x18\x09\x14\x19') == 'LAXITY'
    assert SF2Parser._normalize_driver_name('Laxity') == 'LAXITY'
    assert 'DRIVER' in SF2Parser._normalize_driver_name('D\x12\x09\x16\x05\x12 11.00')


@pytest.mark.skipif(not os.path.isdir(_sf2('SF2')), reason='SF2 corpus absent')
def test_laxity_detection_is_not_the_container_load_address():
    """Regression: the detector used to return True for EVERY SF2.

    It tested `load_address == 0x0D7E`, which is the container's address and is
    identical for Laxity and Driver 11 alike, plus "some non-zero byte at
    $0E00", which any non-empty file satisfies. Genuine Laxity files parsed
    fine so nobody noticed, while Driver 11 files failed into a fallback and
    printed three "invalid sequence address $0000" warnings.
    """
    import glob
    from sf2_viewer_core import SF2Parser

    lax = sorted(glob.glob(_sf2('SF2', '*.sf2')))[:6]
    d11 = sorted(glob.glob(_sf2('out', 'hardtrack', '*.sf2')))[:3]
    if not lax or not d11:
        pytest.skip('need both a Laxity and a Driver 11 SF2')

    for p in lax:
        pr = SF2Parser(p); pr.parse()
        assert pr.load_address == 0x0D7E                    # same for both
        assert pr.is_laxity_driver, os.path.basename(p)
    for p in d11:
        pr = SF2Parser(p); pr.parse()
        assert pr.load_address == 0x0D7E                    # ...which is the point
        assert not pr.is_laxity_driver, os.path.basename(p)


@pytest.mark.skipif(not os.path.isdir(_sf2('out', 'hardtrack')), reason='no Driver 11 SF2s')
def test_driver11_orderlist_is_not_read_from_the_laxity_offset():
    """Regression: every Driver 11 orderlist position exported as `A000`.

    `_parse_music_data` derived column 1 from the hardcoded LAXITY file offset
    $1766, which on a Driver 11 file lands in a run of zeros -- so the unpacker
    dutifully produced 'transpose $A0, sequence 0' for every position of all
    three tracks. The real address is in the Music Data block's word at offset
    12 ($242A on all five files here).

    Checked structurally rather than against a golden dump. The strong
    invariant is CONTIGUITY: the emitter numbers sequences 0..N with no gaps, so
    a correct orderlist references exactly max+1 distinct sequences. All five
    files satisfy that (Zakplus 62 refs / max $3D, Love_tune_2 30 / $1D, ...),
    and the broken read could not -- it referenced sequence 0 and nothing else.

    Track lengths are deliberately NOT asserted equal: voices loop at different
    points, and Hopscotch really is 44/48/48.
    """
    import glob
    from sf2_viewer_core import SF2Parser

    paths = sorted(glob.glob(_sf2('out', 'hardtrack', '*.sf2')))
    if not paths:
        pytest.skip('no Driver 11 SF2s built')
    for p in paths:
        name = os.path.basename(p)
        pr = SF2Parser(p); pr.parse()
        assert not pr.is_laxity_driver, name
        tracks = pr.orderlist_unpacked
        assert len(tracks) == 3, name
        assert all(tracks), f'{name}: an empty track'
        seqs = [tuple(e['sequence'] for e in t) for t in tracks]
        assert len(set(seqs)) == 3, f'{name}: tracks are identical'
        used = {s for t in seqs for s in t}
        assert used == set(range(max(used) + 1)), f'{name}: gaps in {sorted(used)}'
        assert max(used) > 0, f'{name}: only sequence 0 referenced (the old bug)'


@pytest.mark.skipif(not os.path.isdir(_sf2('SF2')), reason='SF2 corpus absent')
def test_laxity_orderlist_comes_from_the_block_word_too():
    """The Laxity exception is gone: the block word is right for that driver too.

    This test previously pinned the OPPOSITE -- the hardcoded `$1766` offset --
    on the grounds that choosing needed Laxity ground truth. That ground truth
    exists, and all three forms agree the constant is wrong:

      * the block's word layout is identical across both drivers (word16 -
        word12 == $300, three tracks of $100), and the constant is a fixed
        $24e0 for every Laxity file here while word12 moves per file;
      * a correct orderlist terminates on all three tracks and references
        exactly max+1 distinct sequences -- word12 passes 47/47, the constant
        0/47;
      * `laxity_parser` decodes Angular's source SID independently, and word12
        matches its shape while the constant yields 253 entries of sequence
        $7F.

    Both assertions below are load-bearing: the address must come from the
    block, and the resulting orderlist must satisfy the invariant.
    """
    import glob
    from sf2_viewer_core import SF2Parser, BlockType

    paths = sorted(glob.glob(_sf2('SF2', '*.sf2')))[:6]
    if not paths:
        pytest.skip('no Laxity SF2s')
    checked = 0
    for p in paths:
        pr = SF2Parser(p); pr.parse()
        if not pr.is_laxity_driver:
            continue
        d = pr.blocks[BlockType.MUSIC_DATA][1]
        assert pr.music_data_info.orderlist_address == d[12] | (d[13] << 8)
        assert pr.music_data_info.orderlist_address != pr.load_address + (0x1766 - 4)
        seqs = [e['sequence'] for tr in pr.orderlist_unpacked for e in tr]
        assert seqs, f'{os.path.basename(p)}: no orderlist entries'
        assert set(seqs) == set(range(max(seqs) + 1)), (
            f'{os.path.basename(p)}: sequences {sorted(set(seqs))[:12]} not contiguous')
        checked += 1
    assert checked, 'no Laxity files were checked'



# --- the Laxity payload base -------------------------------------------------
# These pin the fix for "the two-stage decode produces wave_ptr errors on an SF2
# payload". The suspect was the PSIDHeader's init_address; it is not, and that is
# measured rather than argued -- SF2Parser already carries the real one in
# driver_common.init_address and feeding it changes nothing. The cause is that
# sidm2.laxity_parser's table constants are offsets from the PLAYER BASE while
# the code added them to the FILE's load address. The two coincide at $1000 for a
# raw SID, which is why it only showed on an SF2 wrapper.

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parsed_sf2(name):
    """Parse an SF2 by basename. Named _parsed_sf2, not _sf2: this module
    already has a _sf2() that returns a PATH, and shadowing it broke four
    passing tests when these were first appended."""
    from sf2_viewer_core import SF2Parser
    p = SF2Parser(os.path.join(_ROOT, "SF2", name))
    p.parse()
    return p


def test_laxity_payload_rebases_on_the_player_not_the_file_load_address():
    p = _parsed_sf2("Angular.sf2")
    assert p.is_laxity_driver
    assert p.load_address == 0x0D7E, hex(p.load_address)
    data, base = p.laxity_payload()
    assert base == 0x1000, hex(base)
    # the payload really starts at the base, not merely claims to
    assert len(data) == len(p.data[2:]) - (0x1000 - 0x0D7E)


def test_the_instrument_table_constant_lands_in_code_off_the_file_load_address():
    """The concrete reason the anchor matters, kept as bytes rather than prose.

    load+$0A6B = $17E9 on this file and the bytes there are 8D 18 D4 -- STA
    $D418, i.e. player code. At the player base the same constant reaches the
    real table, whose first bytes match the raw SID's byte for byte.
    """
    from sidm2.laxity_parser import LAXITY_INSTR_TABLE_OFFSET as INS
    p = _parsed_sf2("Angular.sf2")
    raw = p.data[2:]
    wrong = raw[(p.load_address + INS) - p.load_address:][:3]
    data, base = p.laxity_payload()
    right = data[INS:INS + 3]
    assert bytes(wrong) != bytes(right)
    assert bytes(right) == bytes([0x03, 0xF8, 0x80]), bytes(right).hex()


def test_every_laxity_sf2_on_disk_can_be_rebased():
    """The base is a CHECKED constant, not an assumed one.

    All 47 Laxity SF2s load at $0D7E; if one ever does not, laxity_payload()
    must refuse rather than slice at a negative offset. This is the test that
    turns "$1000 looked right on the file I tried" into an invariant.
    """
    import glob
    seen = 0
    for f in sorted(glob.glob(os.path.join(_ROOT, "SF2", "*.sf2"))):
        try:
            from sf2_viewer_core import SF2Parser
            p = SF2Parser(f)
            p.parse()
        except Exception:
            continue
        if not p.is_laxity_driver:
            continue
        seen += 1
        assert p.load_address <= 0x1000, (os.path.basename(f), hex(p.load_address))
        assert p.laxity_payload() is not None, os.path.basename(f)
    assert seen >= 40, seen


def test_laxity_payload_refuses_when_the_load_is_above_the_player_base():
    """Refusing beats slicing at a negative offset."""
    p = _parsed_sf2("Angular.sf2")
    p.load_address = 0x2000
    assert p.laxity_payload() is None


def test_laxity_sf2_decodes_through_both_stages_not_the_packed_heuristic():
    """Angular's SF2 must decode through the REAL sequence table, not a heuristic.

    THREE DECODES HAVE OCCUPIED THIS DISPATCH and the history is the point, because
    each looked plausible:
      1. the packed-sequence heuristic -- {0:64, 1:667, 2:24, 3:7, 4:30}, with
         sequence 1 over-reading to 667 entries against a declared length of 75,
         which the A/B listening page had to refuse outright;
      2. the two-stage decode -- 197/174/139, pinned here as CURRENT BEHAVIOUR
         rather than as correct, because ch_seq_ptr points at ORDERLISTS
         (docs/players/LAXITY.md) and those three bodies are 14-byte orderlists
         run through the sequence grammar, over-shooting their $FF because the
         extractor stops on $7F;
      3. the real sequence table -- 14 sequences, which is what the file has.

    The previous version of this test said "Update this when the dispatch flips."
    It has flipped, and these are the file's own sequence lengths.
    """
    p = _parsed_sf2("Angular.sf2")
    assert p.is_laxity_driver
    counts = [len(v) for _, v in sorted(p.sequences.items())]
    assert counts == [2, 48, 63, 45, 40, 64, 64, 38, 48, 63, 36, 29, 32, 35], counts

    # NOT the two earlier decodes -- named so a silent revert is loud
    assert counts != [197, 174, 139], "reverted to the two-stage orderlist decode"
    assert 667 not in counts, "reverted to the packed heuristic's over-read"

    # the orderlists are exposed AS orderlists, which is what makes the per-voice
    # streams recoverable now that self.sequences is per-FILE
    assert [ol[0] for ol in p.laxity_orderlists] == [0x87, 0x93, 0x87]
    assert [ol[1] for ol in p.laxity_orderlists] == [0x01, 0x02, 0x05]

    # every sequence is within the file's declared length, so nothing over-reads
    dsl = p.music_data_info.default_sequence_length
    assert dsl == 75
    assert max(counts) <= dsl, counts


def _angular_real_sequences():
    """Angular through the real sequence table, bypassing the default dispatch."""
    p = _parsed_sf2("Angular.sf2")
    p.sequences = {}
    assert p._parse_laxity_real_sequences() is True
    return p


def test_angular_ground_truth_matches_the_sf2ii_editor_capture():
    """The SF2II capture, checkable at last -- five cycles could not reach it.

    Ground truth (SID Factory II, Ctrl+P + F1): T3 reads
    'A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4'. That is sequence 07 rows 7..14, exact and
    with NO transpose, which pins the note naming at the same time:
    octave = value // 12, class = value % 12, 0 = C-0.

    A PREVIOUS CYCLE REJECTED THIS TABLE AND WAS WRONG. It compared entries
    0/1/2 against T1/T2/T3, but the orderlists name 01/02/05 and the rows shown
    live in 07 -- so it was reading the right table at the wrong indices.
    """
    names = "C C# D D# E F F# G G# A A# B".split()

    def nm(v):
        return "+++" if not v else "%s-%d" % (names[v % 12], v // 12)

    p = _angular_real_sequences()
    rows = [nm(e.note) for e in p.sequences[7]]
    assert rows[7:15] == ["A-4", "G-4", "B-4", "G-4", "D-4", "C-5", "B-4", "G-4"], rows[:16]
    # the T1/T2 line's 'C-4 --- A-3' is rows 1..3 of the same sequence
    assert rows[1:4] == ["C-4", "+++", "A-3"], rows[:6]


def test_angular_orderlists_are_read_as_orderlists():
    """Three per-voice orderlists: a transpose byte, then sequence NUMBERS.

    The editor names T1/T2/T3 as sequences 01/02/05 and these are where that
    comes from -- the first entry of each voice's orderlist.
    """
    p = _angular_real_sequences()
    assert [ol[0] for ol in p.laxity_orderlists] == [0x87, 0x93, 0x87]
    assert [ol[1] for ol in p.laxity_orderlists] == [0x01, 0x02, 0x05]
    assert p.laxity_orderlists[2][1:] == [5, 6, 3, 4, 3, 7, 10, 10, 11, 12, 11, 13]


def test_sequence_table_locate_is_unique_or_refuses():
    """The locate is an exhaustive scan, so a TIE must refuse rather than pick.

    The shape is self-verifying -- bodies start at table + 2N, so entry 0 must
    equal that -- and across all 47 Laxity SF2s on disk it yields exactly one
    candidate 22 times, none 25 times, and two candidates NEVER. This pins both
    halves: Angular resolves uniquely, and a buffer with no such structure
    returns None instead of guessing.
    """
    p = _parsed_sf2("Angular.sf2")
    data, base = p.laxity_payload()
    tbl, count, ptrs = p.laxity_locate_seq_table(data, base)
    assert (tbl, count) == (0x1B1C, 14)
    assert ptrs[0] == tbl + 2 * count          # the constraint that makes it unique
    assert ptrs == sorted(ptrs)
    assert p.laxity_locate_seq_table(bytes(4096), 0x1000) is None


def test_the_two_stage_reader_declines_rather_than_returning_empty():
    """laxity_payload() returning None must mean 'decline', so the dispatch falls
    through to the older readers instead of publishing an empty result."""
    p = _parsed_sf2("Angular.sf2")
    p.load_address = 0x2000          # above the player base -> cannot re-base
    p.sequences = {}
    assert p._parse_laxity_two_stage() is False
    assert p.sequences == {}


def test_real_sequences_carry_the_decoded_duration_not_a_constant():
    """The precondition abpage's row_schedule was blocked on.

    _entry() used to pass duration=0 for every event, so every column summed to
    zero frames and row_schedule refused all three voices as DEGENERATE. Measured
    before the fix: Counter({0: 607}) across all 14 of Angular's sequences.

    This asserts the value is DECODED, not defaulted: a spread of distinct
    durations, and specifically some greater than 1, because a uniform 1 is what
    a fitted "one row per event" constant would also produce. The decode itself
    lives in sidm2/sequence_translator.py:233 -- outside this module, which is
    what makes it ground truth rather than a number chosen here.
    """
    p = _angular_real_sequences()
    durs = [e.duration for s in p.sequences.values() for e in s]
    assert durs, "no events decoded at all -- the test is vacuous"
    assert len(set(durs)) > 1, (
        "every duration is %r -- _entry() is passing a constant again, and every "
        "consumer summing duration*tempo will read the song as zero-length"
        % sorted(set(durs)))
    assert max(durs) > 1, "no event lasts more than one frame; that is a flat constant"
    assert min(durs) >= 0 and all(isinstance(d, int) for d in durs)


def test_the_duration_fix_did_not_move_the_editor_ground_truth():
    """Durations and pitches are independent, and this pins that they stayed so.

    The risk in touching _entry() is shifting the note stream by a row while
    making the durations look right. Sequence 07 rows 7..14 are the SF2II
    capture (Ctrl+P, F1) and must be byte-identical to what
    test_angular_ground_truth_matches_the_sf2ii_editor_capture already asserts.
    """
    names = "C C# D D# E F F# G G# A A# B".split()

    def nm(v):
        return "+++" if not v else "%s-%d" % (names[v % 12], v // 12)

    p = _angular_real_sequences()
    rows = [nm(e.note) for e in p.sequences[7]]
    assert rows[7:15] == ["A-4", "G-4", "B-4", "G-4", "D-4", "C-5", "B-4", "G-4"], rows[:16]


def test_default_sequence_length_is_a_DEFAULT_not_a_maximum():
    """The prescribed fix for the over-read is REFUTED, and this pins why.

    sf2-viewer-core-sequence-overread asked to "fix it at the parser using the
    file's own default_sequence_length as the bound". That would truncate real
    music. docs/reference/SF2_FORMAT_SPEC.md, "Contiguous Sequence Stacking":
    "Sequences in each track can have different lengths - they stack like Tetris
    blocks." So the field is the length a NEW sequence gets, not a cap.

    Measured across SF2/: on files whose sequence table LOCATES, the bodies are
    already bounded structurally by the next pointer, and their lengths straddle
    dsl in both directions --

        Cycles.sf2               dsl 13, lengths 2..65   (located)
        Unboxed_Ending_8580.sf2  dsl 38, lengths 2..65   (located)
        Angular.sf2              dsl 75, lengths 2..64   (located)

    ANGULAR IS THE LUCKY CASE and that is the trap: its dsl happens to exceed its
    longest sequence, which is the only reason `len > dsl` ever looked like a
    valid guard. On Cycles the same test flags 4 correctly-decoded sequences.
    """
    p = _parsed_sf2("Angular.sf2")
    dsl = p.music_data_info.default_sequence_length
    assert dsl == 75
    assert max(len(v) for v in p.sequences.values()) <= dsl, (
        "Angular is expected to sit UNDER its dsl -- that coincidence is what the "
        "rest of this test exists to stop anyone generalising from")

    # the sequences are bounded by the TABLE, not by a length: consecutive
    # pointers are what stops each body, which is why a length cap is the wrong
    # instrument even where it would happen to work
    addr, count, ptrs = p.laxity_seq_table
    assert count == len(ptrs) == 14
    assert all(ptrs[i + 1] > ptrs[i] for i in range(len(ptrs) - 1)), ptrs


def test_a_located_file_may_legitimately_exceed_its_default_sequence_length():
    """The counter-example to the length guard, on a real file.

    If this file ever stops exceeding dsl, the evidence for the test above is
    gone and the refutation needs re-checking rather than assuming.
    """
    import os
    path = os.path.join(_ROOT, "SF2", "Cycles.sf2") if "_ROOT" in globals() else None
    p = _parsed_sf2("Cycles.sf2")
    dsl = p.music_data_info.default_sequence_length
    assert dsl == 13, dsl
    over = [k for k, v in p.sequences.items() if len(v) > dsl]
    assert p.laxity_seq_table, "Cycles must LOCATE, or it is not evidence about located files"
    assert len(over) >= 4, (
        "Cycles no longer exceeds its dsl (%d over) -- re-check the claim that "
        "default_sequence_length is not a maximum" % len(over))


def test_the_seqtable_imports_survive_a_bare_script_invocation():
    """THE ONLY TEST THAT CAN CATCH THIS, and it has to shell out.

    sf2_viewer_core's seq-table imports are PACKAGE imports
    (`from sidm2.laxity_parser import ...`), so they need the repo ROOT on
    sys.path -- not the sidm2 directory, which is what the two older
    sys.path.insert lines add. Under pytest, rootdir is already on sys.path, so
    an in-process assertion CANNOT distinguish the working case from the broken
    one. That is exactly how the defect shipped: 3044 tests green while every
    page the CLI built used the refuted packed-heuristic decode.

    Measured before the fix, same file and same function, only sys.path differing:
        with the root  -> row_schedule(SF2/Angular.sf2) = [512,512,481], 14 seqs
        without it     -> [64, 0, 31], 5 seqs   (the decode 34ed351 refuted)

    So this test builds a script whose sys.path has cwd and '' REMOVED, runs it
    in a subprocess, and asserts the flag is True there.
    """
    import subprocess
    import tempfile
    import textwrap

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = textwrap.dedent("""
        import sys, os
        sys.path.insert(0, os.path.join(%r, 'pyscript'))
        for p in list(sys.path):
            if p in ('', os.getcwd()):
                sys.path.remove(p)
        import sf2_viewer_core as V
        print('SEQTABLE=%%s' %% V.LAXITY_SEQTABLE_AVAILABLE)
    """ % str(root))
    with tempfile.TemporaryDirectory() as td:
        script = os.path.join(td, "probe_seqtable.py")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(src)
        # cwd is the tempdir, NOT the repo root, so nothing puts the root on
        # sys.path except the module's own insert.
        r = subprocess.run([sys.executable, script], capture_output=True,
                           text=True, cwd=td)
    assert "SEQTABLE=True" in r.stdout, (
        "the seq-table imports failed in a bare script context, so the real "
        "Laxity reader is inert wherever the tool actually runs.\n"
        "stdout=%r stderr=%r" % (r.stdout[-400:], r.stderr[-400:]))


def test_the_repo_root_is_on_sys_path_from_this_module():
    """Pins the mechanism, so the insert cannot be 'tidied' away as redundant.

    It looks redundant -- two sibling inserts already mention sidm2 -- and that
    is precisely why it needs a test: removing it breaks only the script path,
    which no other test exercises.
    """
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "sf2_viewer_core.py"), encoding="utf-8").read()
    assert "sys.path.append(str(Path(__file__).parent.parent))" in src, (
        "the repo-root sys.path entry is gone; the package imports below it "
        "will fail in any bare-script context")
    # APPEND, NOT insert(0) -- a defensive pin. This directory is itself named
    # `sidm2`, so prepending the repo root would let a bare `import X` resolve to
    # a repo-root sibling ahead of the intended module. NOTE: an earlier version
    # of this comment blamed prepending for 6 red tests in
    # test_stage7_emissions.py. That was wrong -- those are a pre-existing
    # order-dependent flake (the failing subset changed between runs; the suite
    # is 3046/0 under -p no:randomly either way).
    assert "sys.path.insert(0, str(Path(__file__).parent.parent))" not in src, (
        "the repo-root entry was changed back to insert(0), which shadows "
        "sibling modules -- see test_stage7_emissions.py")


# --- a decode that cannot fit in its own file is refused ----------------------
#
# The three Laxity fallback readers scan to the grammar's own $7F with nothing
# bounding them (22 of 47 SF2s locate a pointer table and are structurally
# bounded; the other 25 fall through to these). The bound applied is an
# IMPOSSIBILITY, not a threshold: every packed entry costs at least one byte, so
# the entries decoded from a file cannot outnumber the file's bytes.
#
# default_sequence_length is deliberately NOT used -- refusing on it dropped
# whole legitimate voices, which is settled and pinned elsewhere.

def _all_sf2s():
    import glob
    return sorted(glob.glob(os.path.join(_ROOT, "SF2", "*.sf2")))


def _parsed(path):
    import io
    import contextlib
    from sf2_viewer_core import SF2Parser
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        p = SF2Parser(path)
        if not p.parse():
            return None
    return p


def test_no_file_decodes_more_entries_than_it_has_bytes():
    """THE INVARIANT, over the whole SF2/ corpus rather than one file.

    Before the guard, _test_commando.sf2 decoded 24,696 entries from 22,705
    bytes. Nothing else came close -- the next largest is 1,762 entries in
    13,276 bytes, 13% of its own bound -- so this is not a tight fit that
    legitimate files brush against.
    """
    files = _all_sf2s()
    if len(files) < 10:
        pytest.skip("no SF2 corpus on this machine")
    seen = 0
    for f in files:
        p = _parsed(f)
        if p is None:
            continue
        seen += 1
        total = sum(len(v) for v in (p.sequences or {}).values())
        assert total <= len(p.data), (
            "%s decoded %d entries from %d bytes"
            % (os.path.basename(f), total, len(p.data)))
    assert seen > 20, "parsed too few files for this to mean anything: %d" % seen


def test_the_guard_costs_the_corpus_NOTHING():
    """A refusal must not take legitimate decodes with it.

    Measured 2026-09-03: 47 of 47 files in SF2/ still decode sequences after
    the guard, exactly as before it. The one refusal falls THROUGH to a later
    reader rather than emptying the file.
    """
    files = _all_sf2s()
    if len(files) < 10:
        pytest.skip("no SF2 corpus on this machine")
    parsed = [p for p in (_parsed(f) for f in files) if p is not None]
    assert parsed, "nothing parsed"
    with_seqs = [p for p in parsed if p.sequences]
    assert len(with_seqs) == len(parsed), (
        "%d of %d files lost their sequences to the guard"
        % (len(parsed) - len(with_seqs), len(parsed)))


def test_commando_records_WHY_it_was_refused():
    """The refusal is reported, not silent -- five of the six consumers of this
    module have no over-read guard of their own and cannot tell an impossible
    decode from a long one."""
    path = os.path.join(_ROOT, "SF2", "_test_commando.sf2")
    if not os.path.exists(path):
        pytest.skip("SF2/_test_commando.sf2 not present")
    p = _parsed(path)
    assert p is not None
    refusals = getattr(p, "sequence_refusals", [])
    assert refusals, "the impossible decode was accepted silently"
    r = refusals[0]
    assert r["entries"] > r["bytes"], r
    assert "at least one byte" in r["reason"]
    assert r["reader"], "the refusal does not say which reader produced it"
    # and it fell through rather than emptying the file
    assert p.sequences, "the refusal emptied the file instead of falling through"


def test_a_pointer_bounded_file_is_not_touched_by_the_guard():
    """The guard is wired to the FALLBACK readers only. A file whose sequence
    table locates is cut at the next pointer, so its lengths are structural and
    it must never acquire a refusal."""
    files = _all_sf2s()
    if len(files) < 10:
        pytest.skip("no SF2 corpus on this machine")
    bounded = [p for p in (_parsed(f) for f in files)
               if p is not None and getattr(p, "laxity_seq_table", None)]
    assert bounded, "no pointer-bounded file in the corpus to check against"
    for p in bounded:
        assert not getattr(p, "sequence_refusals", []), (
            "a pointer-bounded decode was put through the fallback guard")
