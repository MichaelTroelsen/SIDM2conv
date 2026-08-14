"""Tests for the HardTrack SR pre-kill (`SR_PREKILL`), the per-note lookahead.

The A/B result itself needs eighteen builds and lives in
`pyscript/hardtrack_sr_prekill_ab.py`. What is pinned here is everything that
must hold now that it is ON for HardTrack by default:

  * only HardTrack opts in -- every other shim gets 0, and the emitter masks the
    col2 bit out of any build without the feature, so the six other players that
    share this driver stay byte-identical;
  * every byte of it is inside a `.if SR_PREKILL` block;
  * the kill is gated BOTH on the voice being silent and on the ENDING note's
    instrument carrying field-5 mode 2;
  * it refuses to assemble against `RELEASE_WF`, whose gate it cannot read.

The two gates matter more than they look. `SR=$00` zeroes SUSTAIN as well as
release, the envelope falls to zero, and only a gate RISE re-attacks it -- so one
mistimed kill silences the rest of a held note while every later register still
reads correct. Four such frames cost -24 dB on `Love_tune_2`. And firing on every
note rather than every mode-2 note took `Teekkno` from 42 to 468 mismatching SR
frames -- a regression the corpus mean still looked good through.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DRIVER = os.path.join(ROOT, 'drivers_src', 'mon', 'romuzak_driver.asm')
EMITTER = os.path.join(ROOT, 'bin', 'build_romuzak_native_song.py')
SHIM = os.path.join(ROOT, 'bin', 'build_hardtrack_native_song.py')


def read(path):
    return io.open(path, encoding='utf-8').read()


def conditional_blocks(text, flag):
    """The `.if <flag> ... .endif` spans of `text`, as a list of strings."""
    out, depth, start = [], 0, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('.if'):
            if depth == 0 and re.search(r'\b%s\b' % flag, s):
                start, depth = [], 1
                continue
            if start is not None:
                depth += 1
        elif s.startswith('.endif') and start is not None:
            depth -= 1
            if depth == 0:
                out.append('\n'.join(start))
                start = None
                continue
        if start is not None:
            start.append(line)
    return out


def test_it_is_on_for_hardtrack_and_off_for_everyone_else():
    """HardTrack opts in; every other shim gets 0 and stays byte-identical."""
    assert "os.environ.get('HT_SR_PREKILL', '2')" in read(SHIM)
    assert "SR_PREKILL = {getattr(B, 'SR_PREKILL', 0)}" in read(EMITTER)
    # ...and the col2 bit cannot leak into a build that has the feature off,
    # whatever a shim sets, because the emitter masks it out.
    assert "keep = 0x4C if getattr(B, 'SR_PREKILL', 0) else 0x48" in read(EMITTER)


def test_the_kill_is_gated_on_the_ending_notes_instrument():
    """Firing on every note is a REGRESSION, not a partial fix.

    HardTrack restarts only instruments whose field-5 mode is 2, and the test is
    on the note that is ENDING. Unconditionally, `Teekkno` went 42 -> 468
    mismatching SR frames and its centroid changed sign; gated, 42 -> 26.
    """
    block = [b for b in conditional_blocks(read(DRIVER), 'SR_PREKILL')
             if 'sr_pre:' in b][0]
    body = block.split('sr_pre:', 1)[1].split('sr_rearm:', 1)[0]
    assert 'lda VIFLAGS,x' in body and 'and #$04' in body
    assert body.index('lda VIFLAGS,x') < body.index('sta SID+6,y')


def test_mode_two_is_the_documented_selector():
    from sidm2.hardtrack_parser import HardTrackModule
    m = HardTrackModule.from_sid(
        os.path.join(ROOT, 'SID', 'Shogoon', 'Teekkno.sid'))
    modes = {m.instrument(n).mode for n in range(m.num_instruments)}
    assert modes <= {0, 2}, modes          # the corpus carries only these two
    for n in range(m.num_instruments):
        ins = m.instrument(n)
        assert ins.ends_with_hard_restart == (ins.mode == 2)
    # Teekkno is the discriminating file: it must carry BOTH modes, or it does
    # not test the gate at all.
    assert modes == {0, 2}


def test_every_new_routine_is_inside_an_sr_prekill_block():
    """Six other players share this driver; nothing here may reach them."""
    text = read(DRIVER)
    guarded = '\n'.join(conditional_blocks(text, 'SR_PREKILL'))
    assert guarded, 'no .if SR_PREKILL block found'
    for sym in ('sr_pre:', 'sr_rearm:', 'jsr sr_pre', 'jsr sr_rearm',
                'sta VGCUR,x'):
        assert sym in guarded, '%s is not inside a .if SR_PREKILL block' % sym
        # ...and nowhere else: count in the file must equal count in the blocks
        assert text.count(sym) == guarded.count(sym), \
            '%s also appears outside the guarded blocks' % sym


def test_the_kill_is_gated_on_the_voice_being_silent():
    """`sr_pre` must read the gate before zeroing SR -- see the module docstring.

    It reads VGCUR (the $D404 byte `wave_step` actually wrote) and not
    WAVE[VWI], because `wave_step` INCs VWI on the frame a row's count expires,
    which is exactly the pre-fetch frame this runs on.
    """
    block = [b for b in conditional_blocks(read(DRIVER), 'SR_PREKILL')
             if 'sr_pre:' in b]
    assert len(block) == 1
    body = block[0].split('sr_pre:', 1)[1].split('sr_rearm:', 1)[0]
    assert 'lda VGCUR,x' in body
    assert 'WAVE,y' not in body
    # the gate test must come BEFORE the store, or it tests nothing
    assert body.index('lda VGCUR,x') < body.index('sta SID+6,y')


def test_it_refuses_to_assemble_against_release_wf():
    text = read(DRIVER)
    assert '.cerror SR_PREKILL && RELEASE_WF' in text


def test_only_sr_is_killed_never_ad():
    """`B.HARD_RESTART`'s `$7D` row zeroes AD too, and AD is already right
    (0/10/20 mismatching frames on Love_tune_2's three voices). Zeroing it would
    be a regression dressed as a fix."""
    block = [b for b in conditional_blocks(read(DRIVER), 'SR_PREKILL')
             if 'sr_pre:' in b][0]
    body = block.split('sr_pre:', 1)[1].split('sr_rearm:', 1)[0]
    assert 'sta SID+6,y' in body          # $D406, sustain/release
    assert 'sta SID+5,y' not in body      # $D405, attack/decay -- never


def test_the_ab_tool_windows_are_part_one_spans():
    """Every window must be a positive span the builder itself reported. The
    error this guards is measuring past a part's end, where our part LOOPS
    against the original's continuing music -- it produced five retracted
    readings in three tools in one session."""
    sys.path.insert(0, os.path.join(ROOT, 'pyscript'))
    import hardtrack_sr_prekill_ab as ab
    assert len(ab.CASES) == 9
    for stem, secs in ab.CASES:
        assert 0 < secs <= 28, stem
        assert os.path.exists(os.path.join(ROOT, 'SID', 'Shogoon',
                                           stem + '.sid')), stem
    assert ab.ALIGN == -3, 'the render leads the original by 3 frames'
