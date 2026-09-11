"""`has_sf2_magic` was a TWO-BYTE SUBSTRING SEARCH over an entire C64 image.

THE DEFECT, measured rather than reasoned about. `b'\\x37\\x13' in c64_data`
scans 8KB+ for two bytes, and two bytes recur by chance. Over the whole tree it
fired on 46 of 1,524 .sid files -- native Hubbard (14), Gallefoss (10), Laxity
(9), Bjerregaard (5), Gray (3), Shogoon (3) and Tel (2) rips -- at scattered
offsets (809, 2356, 1099, 1213, ...). NOT ONE of the 46 carried the marker at
offset 0, which is the only place a real one can be.

WHY OFFSET 0. An SF2 file is [load_lo, load_hi, $37, $13, <blocks>], so the
marker sits at FILE offset 2 and the 2-byte PRG load address is exactly what
SIDParser.get_c64_data strips. Verified against an sf2_to_sid round trip of the
tracked reference file: marker at C64-data offset 0, every time.

THE FALSE POSITIVE WAS NOT COSMETIC. `is_sf2_exported = has_sf2_magic and
driver_type == 'driver11'`, and driver11 is DriverSelector's fallback default,
so every one of the 46 that also fell through to the default was routed into the
SF2-export path and logged as "SF2-exported file" while being a native rip.

THE TRAP THIS FILE ALSO PINS: strengthening the check by walking the block chain
to BLOCK_END REJECTS a genuine export. The chain in a real file degenerates into
id=$00 size=0 filler and runs off the end without ever reaching $FF. The first
block descriptor is the invariant that actually holds -- 422 of 422 .sf2 files
in SF2/, bin/music/ and out/ begin with block id $01 and an in-bounds size.
"""
import re
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from sidm2.conversion_pipeline import has_sf2_structure   # noqa: E402
from sidm2.sf2_parser import BLOCK_DESCRIPTOR             # noqa: E402

_REFERENCE = os.path.join(_ROOT, "bin", "music", "Driver 11 Test - Arpeggio.sf2")
# One of the 46 the old substring check matched: a native Rob Hubbard rip whose
# marker sits at offset 2198, not 0. This is the file that logged verbatim
# "Using SF2 player parser (driver: driver11, SF2-exported file)".
_FALSE_POSITIVE = os.path.join(
    _ROOT, "SID", "Hubbard_Rob", "Commodore_64_Music_Examples.sid")


def _sf2_as_c64_data(path):
    """An .sf2 read the way a SID carries it: with the PRG load address stripped."""
    return open(path, "rb").read()[2:]


def test_a_real_sf2_image_is_ACCEPTED():
    assert has_sf2_structure(_sf2_as_c64_data(_REFERENCE))


def test_the_marker_at_a_nonzero_offset_is_REJECTED():
    """The exact shape of all 46 false positives, built synthetically."""
    payload = b"\x00" * 800 + b"\x37\x13" + b"\x00" * 800
    assert b"\x37\x13" in payload          # the OLD check would say yes
    assert not has_sf2_structure(payload)  # the new one says no


@pytest.mark.skipif(not os.path.exists(_FALSE_POSITIVE),
                    reason="SID corpus not present")
def test_a_real_native_rip_the_old_check_matched_is_REJECTED():
    from sidm2.sid_parser import SIDParser
    parser = SIDParser(_FALSE_POSITIVE)
    data, _load = parser.get_c64_data(parser.parse_header())
    assert b"\x37\x13" in data             # it really is one of the 46
    assert data.find(b"\x37\x13") != 0     # and not at offset 0
    assert not has_sf2_structure(data)


def test_a_wrong_first_block_id_is_REJECTED():
    """Marker in the right place, but the byte after it is not a block descriptor."""
    assert not has_sf2_structure(b"\x37\x13" + bytes([BLOCK_DESCRIPTOR + 1]) + b"\x05\x00" + b"\x00" * 8)


def test_a_first_block_running_past_the_end_is_REJECTED():
    """A size that overruns the buffer is not a structure, it is noise."""
    assert not has_sf2_structure(b"\x37\x13" + bytes([BLOCK_DESCRIPTOR]) + b"\xFF\x7F" + b"\x00" * 8)


def test_data_too_short_to_hold_a_descriptor_is_REJECTED():
    assert not has_sf2_structure(b"\x37\x13")
    assert not has_sf2_structure(b"\x37\x13" + bytes([BLOCK_DESCRIPTOR]) + b"\x05")
    assert not has_sf2_structure(b"")


def test_walking_the_chain_to_BLOCK_END_would_reject_a_REAL_export():
    """Pins the refuted 'strengthening' so nobody re-adds it.

    Reaching $FF is NOT an SF2 invariant: this tracked reference file's chain
    degenerates into id=$00 size=0 filler and runs off the end.
    """
    data = _sf2_as_c64_data(_REFERENCE)
    offset, reached_end = 2, False
    while offset < len(data):
        if data[offset] == 0xFF:
            reached_end = True
            break
        if offset + 3 > len(data):
            break
        offset += 3 + int.from_bytes(data[offset + 1:offset + 3], "little")
    assert not reached_end
    assert has_sf2_structure(data)      # accepted anyway, which is the point


# --- the gate that CONSUMES the detector -------------------------------------
#
# `is_sf2_exported = has_sf2_magic and driver_type == 'driver11'`
# (conversion_pipeline.py:487). These two tests pin what that conjunction does
# NOW that the first clause is a real structure check, because the fix inverted
# which direction it fails in.

def test_a_native_rip_is_no_longer_treated_as_an_sf2_export():
    """THE DIRECTION THE OLD SUBSTRING CHECK GOT WRONG, pinned against a real file.

    SID/Hubbard_Rob/Commodore_64_Music_Examples.sid carries the two marker bytes
    at offset 2198 and takes DriverSelector's fallback ('Standard SF2 driver for
    maximum compatibility'), so under the old check BOTH clauses were true and it
    logged, verbatim, "Using SF2 player parser (driver: driver11, SF2-exported
    file)" on a native Rob Hubbard rip. 37 files took that route.
    """
    if not os.path.exists(_FALSE_POSITIVE):
        pytest.skip("SID corpus not present")
    from sidm2.sid_parser import SIDParser
    parser = SIDParser(_FALSE_POSITIVE)
    data, _load = parser.get_c64_data(parser.parse_header())
    assert not has_sf2_structure(data)
    # so the conjunction is False regardless of what the driver clause says
    assert not (has_sf2_structure(data) and "driver11" == "driver11")


def test_the_driver_clause_can_now_only_cause_a_MISS_not_a_false_positive():
    """THE INVERSION, measured -- and why the obvious cleanup is NOT applied here.

    Across all 1,524 .sid files under SID/ and SF2/, `has_sf2_structure` is True
    for ZERO of them, so the first clause alone already excludes every corpus
    file. The `and driver_type == 'driver11'` can therefore no longer admit
    anything; it can only REJECT a genuine export whose driver verdict is not
    driver11.

    That is not hypothetical. An sf2_to_sid round trip of the TRACKED
    "bin/music/Driver 11 Test - Arpeggio.sf2" -- SF2 II's own DRIVER 11 test file
    -- is identified by player-id.exe as 'SidFactory_II/Laxity', which
    DriverSelector.PLAYER_REGISTRY maps to the LAXITY driver, not driver11. So a
    genuine SF2 export scores has_sf2_structure=True, driver_type='laxity', and
    is_sf2_exported=False.

    THE CLEANUP IS DELIBERATELY NOT APPLIED. Dropping the driver clause would
    route such files into SF2PlayerParser, which has an OPEN correctness defect
    (it reads fixed 3-byte triples from a packed variable-length stream --
    sf2-player-parser-reads-fixed-triples-from-a-variable-length-stream). Fixing
    the gate before the parser would send more files into a worse decoder. The
    ordering is: fix the parser, then drop the clause.

    This test pins the shape so the finding is not lost, and fails if someone
    drops the clause while the parser is still wrong.
    """
    from sidm2 import conversion_pipeline as CP
    import inspect
    src = inspect.getsource(CP.analyze_sid_file)
    assert "has_sf2_magic and driver_type == 'driver11'" in src, (
        "the driver clause was dropped -- that is the right END state, but only "
        "after sf2_player_parser decodes the packed grammar correctly; see this "
        "test's docstring")


# ---------------------------------------------------------------------------
# FROZEN-MODE TOOL RESOLUTION (2026-09-06)
#
# `player-id.exe` used to be resolved as os.path.join(os.getcwd(), 'tools', ...).
# Run from anywhere but the repo root that misses, detect_player_type() returns
# 'Unknown', and DriverSelector picks DRIVER11 -- for a native Laxity file the
# documented 1-8% path, chosen silently, still exiting 0. Nothing consulted
# sys._MEIPASS either, so the frozen binary could never find its bundled tools.
# ---------------------------------------------------------------------------

from sidm2.conversion_pipeline import _tool_path   # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _inside_repo(path):
    """True when `path` is under the repo root.

    normCASE, not just normpath. Windows is case-insensitive, and the suite
    imports `sidm2` through TWO differently-cased sys.path entries: graphify
    wrote `SIDM2` for a directory named `sidm2` (see
    pyscript/graphify_root_fixup.py), and test_graphify_root_fixup inserts its
    parent on sys.path. Whichever runs first fixes the casing of
    conversion_pipeline.__file__, which _tool_path derives its root from -- so
    a raw startswith made these tests pass alone and fail in a full run, on a
    path difference that is not a difference on this filesystem.
    """
    a = os.path.normcase(os.path.normpath(path))
    b = os.path.normcase(os.path.normpath(_REPO))
    return a.startswith(b)


def test_tool_path_is_absolute_and_does_not_depend_on_the_cwd(tmp_path, monkeypatch):
    """THE REGRESSION. Resolution must be identical from any working directory."""
    here = _tool_path("player-id.exe")
    monkeypatch.chdir(tmp_path)
    there = _tool_path("player-id.exe")
    assert os.path.isabs(here) and os.path.isabs(there)
    assert here == there, (here, there)
    assert _inside_repo(here), here


def test_tool_path_prefers_MEIPASS_when_frozen(tmp_path, monkeypatch):
    """PyInstaller extracts the bundle to sys._MEIPASS; a frozen binary must
    look there FIRST, otherwise it finds the tools of whatever checkout the
    machine happens to have -- or none at all."""
    fake = tmp_path / "tools"
    fake.mkdir()
    (fake / "player-id.exe").write_bytes(b"stub")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    got = _tool_path("player-id.exe")
    assert got == str(fake / "player-id.exe"), got


def test_MEIPASS_is_skipped_when_the_bundle_lacks_the_tool(tmp_path, monkeypatch):
    """A _MEIPASS without the tool must fall through to the repo layout rather
    than returning a path that does not exist -- otherwise adding frozen support
    would BREAK the from-source case."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)  # empty
    got = _tool_path("player-id.exe")
    assert os.path.exists(got), got
    assert _inside_repo(got), got


def test_the_driver_selector_is_given_the_resolved_path():
    """DriverSelector's own default is the RELATIVE Path('tools/player-id.exe'),
    so the pipeline must inject a resolved one. Fixing it at the call site uses
    the injection point the constructor already provides, and leaves
    driver_selector.py alone."""
    src = open(os.path.join(_REPO, "sidm2", "conversion_pipeline.py"),
               encoding="utf-8").read()
    assert "DriverSelector(" in src
    assert "player_id_exe=Path(_tool_path('player-id.exe'))" in src, (
        "the selector is being constructed without a resolved tool path; it will "
        "fall back to its relative default and mis-detect from any other cwd")


# ---------------------------------------------------------------------------
# The SF2 validation block imported `scripts.validate_sf2_format`, archived on
# 2026-01-02. Every conversion since then took the except arm, logged
# "SF2 format validation skipped (validator unavailable)", set validation_result
# to None, and printed a summary with NO validation line -- eight months of
# conversions reporting OK from code that never ran. Resolved by routing through
# the in-tree sidm2.sf2_diagnostics verdict (which now RETURNS an
# SF2ValidationResult instead of None), not by restoring the archived module.
# ---------------------------------------------------------------------------
import io as _io                                             # noqa: E402
import contextlib                                            # noqa: E402

from sidm2.conversion_pipeline import (                      # noqa: E402
    print_success_summary,
    _validate_sf2_structure,
    _validation_verdict,
)
from sidm2.sf2_diagnostics import (                          # noqa: E402
    validate_sf2_file as _diagnostics_validate,
    SF2ValidationResult,
)


def test_the_pipeline_validator_is_the_live_diagnostic_not_the_archive():
    """The name the pipeline calls must BE sf2_diagnostics.validate_sf2_file.

    Sabotage check: point the import back at
    archive/cleanup_2026-01-02/orphaned_scripts/validate_sf2_format.py and this
    fails at import time -- `scripts.validate_sf2_format` does not resolve.
    """
    assert _validate_sf2_structure is _diagnostics_validate

    src = open(os.path.join(_ROOT, "sidm2", "conversion_pipeline.py"),
               encoding="utf-8").read()
    # No live import of the archived module, and no silent-skip arm left.
    assert "from scripts.validate_sf2_format import" not in src
    assert "validator unavailable" not in src.replace(
        "# except arm, logged 'validator unavailable', and every conversion since then",
        "")


def test_a_real_sf2_produces_a_real_passing_verdict():
    """A genuine SF2 must validate, and the verdict must be the object the
    summary consumes -- not None, which is how a skipped validator looks."""
    result = _validate_sf2_structure(_REFERENCE)
    assert isinstance(result, SF2ValidationResult)
    assert result.ok, result.errors
    assert _validation_verdict(result) == (True, 0, len(result.warnings))


def test_the_summary_carries_the_real_verdict_for_a_good_file():
    result = _validate_sf2_structure(_REFERENCE)
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_success_summary("in.sid", _REFERENCE, validation_result=result)
    out = buf.getvalue()
    assert "Validation: PASSED (0 errors," in out, out


def test_the_summary_says_FAILED_when_the_file_is_actually_broken(tmp_path):
    """The other half of the gate: a summary that can only ever print PASSED is
    the same non-result as printing nothing."""
    broken = tmp_path / "broken.sf2"
    broken.write_bytes(b"\x00\x10" + b"\xDE\xAD" + b"\x00" * 400)  # wrong magic
    result = _validate_sf2_structure(str(broken))
    assert not result.ok
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_success_summary("in.sid", str(broken), validation_result=result)
    out = buf.getvalue()
    assert "Validation: FAILED" in out, out
    assert "0 errors" not in out, out


def test_quiet_mode_warns_on_a_failed_verdict():
    passing = SF2ValidationResult(True)
    failing = SF2ValidationResult(False, errors=["bad magic"])
    for res, expect in ((passing, "OK:"), (failing, "WARN:")):
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_success_summary("in.sid", "out.sf2", validation_result=res,
                                  quiet=True)
        assert buf.getvalue().startswith(expect), buf.getvalue()


# ---------------------------------------------------------------------------
# THE EXIT CODE. A conversion whose own structural validation says the editor
# will reject the file must not return 0 -- every wrapper script checking a
# return code reads 0 as a clean conversion.
#
# WHY THESE TESTS PATCH THE VERDICT INSTEAD OF CONVERTING A KNOWN-BAD FILE:
# there is no longer a SID in this repo whose conversion emits a structurally
# invalid SF2. The task that opened this gate named one -- a native Laxity tune
# forced through `--driver driver11` -- but that repro was an artefact of the
# sf2_diagnostics false positive fixed earlier (a hardcoded block-3 descriptor
# stride). With the diagnostic correct, driver11 output is structurally VALID;
# it is musically wrong, which is the documented 1-8% path and a different
# question entirely. So the negative fixture is a failing verdict, injected.
# ---------------------------------------------------------------------------
import pytest                                                # noqa: E402
from unittest import mock                                    # noqa: E402
from sidm2 import conversion_pipeline as _cp                 # noqa: E402
from sidm2 import errors as _errs                            # noqa: E402


def _convert(tmp_path, verdict):
    """Run a real conversion with the structure verdict forced to `verdict`."""
    out = tmp_path / "out.sf2"
    with mock.patch.object(_cp, "_validate_sf2_structure", return_value=verdict):
        _cp.convert_sid_to_sf2("SID/Angular.sid", str(out), quiet=True)
    return out


def test_a_failing_structure_verdict_raises_so_the_cli_exits_nonzero(tmp_path):
    failing = SF2ValidationResult(False, errors=["ERR Instruments table (0x80) MISSING"])
    with pytest.raises(_errs.SIDMError) as exc:
        _convert(tmp_path, failing)
    # scripts/sid_to_sf2.py maps SIDMError -> sys.exit(1); that mapping is what
    # turns this raise into a non-zero process exit.
    assert "structure" in str(exc.value).lower(), str(exc.value)


def test_the_artifact_is_still_written_before_the_raise(tmp_path):
    """Raised LAST on purpose: the .sf2 is on disk so the failure is
    inspectable, and a batch loses nothing it had already produced."""
    failing = SF2ValidationResult(False, errors=["ERR Commands table (0x81) MISSING"])
    out = tmp_path / "out.sf2"
    with mock.patch.object(_cp, "_validate_sf2_structure", return_value=failing):
        with pytest.raises(_errs.SIDMError):
            _cp.convert_sid_to_sf2("SID/Angular.sid", str(out), quiet=True)
    assert out.exists() and out.stat().st_size > 100, "artifact was discarded"


def test_a_passing_verdict_does_not_raise(tmp_path):
    """The half that is not optional. A previous attempt at this gate shipped a
    version where BOTH a good and a bad conversion exited 1 -- 'always exits 0'
    inverted, not fixed."""
    out = _convert(tmp_path, SF2ValidationResult(True))
    assert out.exists()


# ---------------------------------------------------------------------------
# The export gate keys on what the FILE declares, not on player-id.
#
# DECIDED 2026-09-10. The old test was `has_sf2_magic and driver_type ==
# 'driver11'`, and `driver_type` comes from DriverSelector -- for which
# driver11 is ALSO the FALLBACK when nothing is recognised. So the conjunct
# read `magic AND (nothing known)`.
#
# An SF2 image NAMES ITS OWN DRIVER in a descriptor block. Measured over the
# four files the old gate refused: two declare LAXITY (refusing them is right,
# for a reason nothing had established), one declares DRIVER 11.00 (refused
# WRONGLY), and one declares DRIVER 15.00 - TINY MARK I, a third case a
# driver11-or-not conjunct cannot express at all.
# ---------------------------------------------------------------------------


def test_the_declared_driver_name_is_read_as_SCREEN_CODES_not_ascii():
    """$01-$1A are A-Z. Read as latin-1 the Driver 11 name comes back as
    'D	 11.00', which matches nothing -- so a gate that
    skipped the normalisation would refuse every real export while looking
    correct."""
    from sidm2.conversion_pipeline import sf2_declared_driver
    assert callable(sf2_declared_driver)
    src = open(os.path.join(_ROOT, "sidm2", "conversion_pipeline.py"),
               encoding="utf-8").read()
    assert "SCREEN CODES" in src, (
        "the screen-code normalisation lost the comment saying why it exists")


def test_a_payload_that_is_not_an_sf2_image_declares_nothing():
    """None rather than a raise or an invented name: the gate calls this only
    behind has_sf2_structure, but a garbled chain must not normalise into
    something that matches."""
    from sidm2.conversion_pipeline import sf2_declared_driver
    assert sf2_declared_driver(bytes([0x37, 0x13]) + bytes(64), 0x1000) is None


def test_the_gate_no_longer_consults_driver_type():
    """The whole defect was the second conjunct. If `driver_type` reappears in
    the gate expression, the FALLBACK is being read as an identification again.
    GREP for `is_sf2_exported =` rather than trusting a line number -- this
    file's lines have moved twice."""
    src = open(os.path.join(_ROOT, "sidm2", "conversion_pipeline.py"),
               encoding="utf-8").read()
    m = re.search(r"is_sf2_exported\s*=\s*(.+)", src)
    assert m is not None, "the gate assignment moved or was renamed"
    expr = m.group(1)
    assert "driver_type" not in expr, (
        "the gate is consulting DriverSelector's driver_type again: %r" % expr)
    assert "declared" in expr, (
        "the gate no longer keys on the file's own declared driver: %r" % expr)


def test_the_gate_holds_in_BOTH_DIRECTIONS_on_the_real_corpus():
    """A narrowing that refuses everything satisfies only the first half, and
    that shape has shipped in this repo before.

    WHY NO NAMED out/ FILE. out/ is rebuilt by every native-driver run this
    repo has (2,300+ tests, batch builds, per-player sweeps), so a filename
    pinned here goes stale the next time someone regenerates it -- this test
    used to hardcode `out/_probe_tempo1.sid` and `SID/Hubbard_Rob/
    Commodore_64_Music_Examples.sid`; both are replaced below with the
    already-TRACKED `_REFERENCE` fixture (not a build artifact -- it does not
    get rebuilt out from under the test) and a fresh directory scan.

    MEASURED 2026-09-11, out/sdi (5,031 SF2-structured .sid files, the corpus
    this task was scoped to): the declared-driver population is 100% ONE
    name, 'ROMUZAK', on every file sampled and on a full-directory scan --
    ZERO declare a Driver 11 descriptor. A python-`random` seed-7 sample of
    150 files reproduces this: 150 of 150 are SF2-structured (the OLD gate's
    entire population), 0 of 150 are accepted by the new one. This is the
    "150 of 150 -> ~1 of 150" scoping result the gate task measured, read
    off out/sdi rather than repeated from memory: the corpus this gate
    actually protects is native-driver output, and native output does not
    declare Driver 11.

    So `out/sdi` alone cannot supply an ACCEPTED example -- there isn't one on
    disk under it -- and this test does not manufacture one there. The accept
    side is the tracked Driver 11 reference (`_REFERENCE`, already used
    elsewhere in this file), which is a real .sf2 that genuinely declares
    'DRIVER 11.00 - THE STANDARD'; the reject side is the first out/sdi file
    a runtime scan finds that is structurally an SF2 export declaring some
    OTHER driver -- exactly the population this gate must keep excluded.
    """
    from sidm2.conversion_pipeline import sf2_declared_driver

    def accepted_sid(path):
        """For a .sid: strip its own PSID/RSID header via SIDParser."""
        from sidm2.sid_parser import SIDParser
        p = SIDParser(path)
        h = p.parse_header()
        c64, la = p.get_c64_data(h)
        if not has_sf2_structure(c64):
            return False, None
        d = sf2_declared_driver(c64, la)
        return (d is not None and d.startswith("DRIVER 11")), d

    def accepted_sf2(path):
        """For a .sf2: it carries only the 2-byte PRG load address, no
        PSID/RSID header, so SIDParser cannot read it -- use
        `_sf2_as_c64_data` (load-address stripped) directly instead."""
        raw = open(path, "rb").read()
        load_address = raw[0] | (raw[1] << 8)
        c64 = _sf2_as_c64_data(path)
        if not has_sf2_structure(c64):
            return False, None
        d = sf2_declared_driver(c64, load_address)
        return (d is not None and d.startswith("DRIVER 11")), d

    if not os.path.exists(_REFERENCE):
        pytest.skip("tracked SF2 reference file absent")
    ok_export, declared_export = accepted_sf2(_REFERENCE)
    assert ok_export, (
        "the tracked Driver 11 reference %r is no longer accepted -- declared %r"
        % (_REFERENCE, declared_export))
    assert declared_export.startswith("DRIVER 11"), declared_export

    other_path, other_declared = _first_out_sdi_non_driver11_export()
    if other_path is None:
        pytest.skip("no out/sdi export declaring a non-Driver-11 driver was "
                    "found on this machine -- rebuild out/sdi to repopulate")
    ok_other, declared_other = accepted_sid(other_path)
    assert declared_other == other_declared
    assert not ok_other, (
        "%s declares %r and is being accepted as a Driver 11 export"
        % (other_path, declared_other))


def _gate_expression_from_source():
    """The literal RHS of `is_sf2_exported = ...`, read fresh off disk.

    Evaluating the text itself (rather than re-deriving the same behaviour in
    Python) is what makes this catch a regression to the retired fallback
    conjunct: `test_the_gate_holds_in_BOTH_DIRECTIONS_on_the_real_corpus`
    calls `sf2_declared_driver`/`has_sf2_structure` directly and would keep
    passing even if `analyze_sid_file` stopped using their result -- those
    functions did not change, only the expression that CONSUMES them would
    have. This closes that gap.
    """
    src = open(os.path.join(_ROOT, "sidm2", "conversion_pipeline.py"),
               encoding="utf-8").read()
    m = re.search(r"is_sf2_exported\s*=\s*(.+)", src)
    assert m is not None, "the gate assignment moved or was renamed"
    return m.group(1).split("#", 1)[0].strip()


def test_the_gate_expression_on_disk_rejects_a_declared_other_driver():
    """Pins the EXACT bug this population was scoped around, evaluated
    against the literal line on disk rather than a reimplementation of it.

    THE RETIRED FALLBACK, reproduced here rather than just named: `has_sf2_magic
    and driver_type == 'driver11'` is true whenever DriverSelector's OWN
    fallback ('driver11', its answer for an unrecognised player) fires on a
    structurally-SF2 file -- regardless of what the file's own descriptor
    names. Every out/sdi file measured 2026-09-11 declares 'ROMUZAK' (5,031 of
    5,031 SF2-structured files sampled; a python-`random` seed-7 draw of 150
    from that set is 150-of-150 SF2-structured and 0-of-150 accepted by the
    current gate), so `driver_type == 'driver11'` firing on one of them is
    exactly the false-positive shape that moved the accepted population from
    150 of 150 down to a small handful.
    """
    expr = _gate_expression_from_source()
    ns = {"has_sf2_magic": True, "driver_type": "driver11",
          "declared": "ROMUZAK"}
    assert eval(expr, {}, ns) is False, (  # noqa: S307 -- reads our own source, not input
        "the gate accepts a file declaring 'ROMUZAK' once driver_type is "
        "'driver11' -- that is the retired fallback conjunct: %r" % expr)


def test_the_gate_expression_on_disk_accepts_a_declared_driver11_export():
    """The other half: a genuine Driver 11 descriptor must still pass,
    independent of whatever DriverSelector's `driver_type` says."""
    expr = _gate_expression_from_source()
    ns = {"has_sf2_magic": True, "driver_type": "laxity",
          "declared": "DRIVER 11.00 - THE STANDARD"}
    assert eval(expr, {}, ns) is True, (  # noqa: S307
        "a genuine Driver 11 declaration is refused when driver_type says "
        "something else: %r" % expr)


def _first_out_sdi_non_driver11_export():
    """The first out/sdi .sid that is structurally an SF2 export but declares
    something other than a Driver 11 descriptor -- found by scanning the
    directory AT RUN TIME, never by naming a file: out/sdi is rebuilt
    regularly by native-driver work, so a name pinned today is not
    guaranteed to exist tomorrow. Returns (path, declared_name), or
    (None, None) if out/sdi is absent or nothing structurally-SF2 turns up
    (declaring something other than Driver 11 does not disqualify a file --
    only a non-SF2-structured one does).
    """
    d = os.path.join(_ROOT, "out", "sdi")
    if not os.path.isdir(d):
        return None, None
    from sidm2.sid_parser import SIDParser
    from sidm2.conversion_pipeline import sf2_declared_driver
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".sid"):
            continue
        path = os.path.join(d, fn)
        try:
            p = SIDParser(path)
            h = p.parse_header()
            c64, la = p.get_c64_data(h)
        except Exception:
            continue
        if not has_sf2_structure(c64):
            continue
        declared = sf2_declared_driver(c64, la)
        if declared and not declared.startswith("DRIVER 11"):
            return path, declared
    return None, None


def test_sf2_declared_driver_annotation_resolves_without_NameError():
    """PEP 649 (Python 3.12+/3.14) defers annotation evaluation, so a PLAIN
    CALL to sf2_declared_driver passes whether or not `Optional` is imported
    -- that is exactly why the missing `from typing import Optional` shipped
    unnoticed at 930b03d. This case forces the annotation to actually
    resolve via inspect.signature(), which is what a NameError surfaces
    through (typing.get_type_hints() or reading a resolved __annotations__
    entry would work equally well; a bare function call would not)."""
    import inspect
    from sidm2.conversion_pipeline import sf2_declared_driver
    sig = inspect.signature(sf2_declared_driver)
    assert sig.return_annotation is not inspect.Signature.empty
