

# --- --init / --play overrides ------------------------------------------------

def test_init_and_play_default_to_none_so_the_header_still_wins():
    """THE COMPATIBILITY HALF, and the one that matters most.

    Every existing invocation of this tool must be byte-identical, so both flags
    default to None and the code falls through to `header.init_address` /
    `header.play_address`. If a default of 0 (or 0x1000) ever creeps in here,
    every siddump in the repo silently changes entry point.
    """
    import siddump_complete as SD
    import sys as _sys
    argv = _sys.argv
    try:
        _sys.argv = ["siddump_complete.py", "dummy.sid"]
        args = SD.parse_arguments()
    finally:
        _sys.argv = argv
    assert args.init is None
    assert args.play is None


def test_the_overrides_accept_hex_and_decimal():
    """`int(x, 0)`, so 0x1000 and 4096 are the same address, and a bare '1000'
    is DECIMAL -- worth pinning because siddump's other address-ish flag
    (--basefreq) uses int(x, 16) and reads the same text as hex."""
    import siddump_complete as SD
    import sys as _sys
    argv = _sys.argv
    try:
        _sys.argv = ["siddump_complete.py", "dummy.sid", "--init", "0x1000",
                     "--play", "4099"]
        args = SD.parse_arguments()
    finally:
        _sys.argv = argv
    assert args.init == 0x1000
    assert args.play == 4099 == 0x1003


def test_barbers_adagio_needs_the_override_to_trace_at_all():
    """THE FILE THE FLAG EXISTS FOR, end to end.

    Barbers_Adagio_64 declares play=$0000. The interrupt-vector fallback then
    recovers $2708, which is not a per-frame play routine but one link of a 4x
    multispeed raster-split chain that busy-waits on $D012 -- constant under this
    emulator, so it never advances. zig64 traces the same file at rc=0 from
    $1000/$1003. Measured 2026-09-03: default invocation exits 1 after 10 lines;
    with the overrides it exits 0 and emits a full dump.
    """
    import os
    import subprocess
    import sys as _sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sid = os.path.join(root, "SID", "Gallefoss_Glenn", "Barbers_Adagio_64.sid")
    if not os.path.exists(sid):
        import pytest
        pytest.skip("Barbers_Adagio_64 not on this machine")
    tool = os.path.join(root, "pyscript", "siddump_complete.py")

    def run(extra):
        return subprocess.run([_sys.executable, tool, sid, "-t2"] + extra,
                              capture_output=True, text=True, timeout=300)

    plain = run([])
    over = run(["--init", "0x1000", "--play", "0x1003"])
    assert plain.returncode != 0, "the default invocation is supposed to FAIL here"
    assert over.returncode == 0, over.stdout[-2000:] + over.stderr[-2000:]
    # a real dump, not just a clean exit
    assert "| Frame |" in over.stdout
    assert len(over.stdout.splitlines()) > len(plain.stdout.splitlines())
    # and the override is announced rather than silent
    assert "Init address overridden" in over.stdout
    assert "Play address overridden" in over.stdout
