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
