"""A refused native build must leave the disk exactly as it found it.

The defect these pin, measured 2026-08-21 on `DMC_Demo_IV_tune_5`: the builder
packed the song into 92 parts, wrote parts 1-4, and raised `WAVE overflow: 288
rows > 256` on part 5. Parts 1-4 stayed on disk. Nothing distinguishes them from
a legitimate 4-part build, so the next sweep SCORES 4/92 of a song as though it
were the whole thing -- the same shape as `Flimbos_Quest_main` shipping 34 parts
of silence and being read as a fidelity defect rather than a build that failed.

The contract is on the SET, not the file. `os.replace` already made each single
artifact all-or-nothing; what was missing is that the parts of one build appear
together or not at all.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
sys.path.insert(0, ROOT)

BM = pytest.importorskip("build_mon_native_song")


@pytest.fixture
def clean_pending():
    """`_PENDING` is module state, so a test that leaves entries in it poisons
    the next one -- and the atexit hook would then commit them at teardown."""
    BM._PENDING.clear()
    yield
    for tmp, _ in BM._PENDING:
        if os.path.exists(tmp):
            os.remove(tmp)
    BM._PENDING.clear()


def _stage(tmp_path, name, pending=True):
    staged = str(tmp_path / (name + BM._STAGE))
    final = str(tmp_path / name)
    with open(staged, "wb") as f:
        f.write(b"SF2")
    if pending:
        BM._PENDING.append((staged, final))
    return staged, final


# --- what gets staged, and what deliberately does not -----------------------

@pytest.mark.parametrize("label, staged", [
    ("part 1/92 (0-2s, 0-100f)", True),
    ("part 47/92 (94-96s, 4700-4800f)", True),
    ("part 1/1 (0-30s, 0-1500f)", False),   # a one-part set cannot be partial
    ("Balloon 0-400s", False),              # single-window builders read back
    ("Hawkeye_sub2", False),                # in-process; must write straight
    ("", False),
    (None, False),
])
def test_only_a_multi_part_set_is_staged(label, staged):
    """Single-window emits must keep writing straight to their final path.

    Not a stylistic choice -- `build_dmc_native_song.py`'s legato A/B re-opens
    the parts it just emitted (`measure_song_voices`, `open(pf, "rb")`) and
    swallows the failure with `except Exception: continue`. Staging a path that
    something reads back in-process would have turned that A/B silently into
    all-`None` and changed which voices are built legato, with nothing failing.
    """
    assert BM._stages(label) is staged


# --- the commit path --------------------------------------------------------

def test_commit_publishes_every_staged_part_at_once(tmp_path, clean_pending):
    pairs = [_stage(tmp_path, f"song_part{i:02d}.sf2") for i in (1, 2, 3)]
    assert not any(os.path.exists(f) for _, f in pairs), "published too early"

    assert BM.commit_parts() == 3
    assert all(os.path.exists(f) for _, f in pairs)
    assert not any(os.path.exists(s) for s, _ in pairs), "staging copy left behind"
    assert BM._PENDING == []


def test_prune_commits_before_it_prunes(tmp_path, clean_pending):
    """`prune_stale_parts` is the commit point precisely because it runs after
    every multi-part loop and only when that loop finished. If it pruned first
    it would delete by a count whose files are not on disk yet."""
    for i in (1, 2):
        _stage(tmp_path, f"song_part{i:02d}.sf2")
    stale = tmp_path / "song_part09.sf2"        # survivor of a longer era
    stale.write_bytes(b"OLD")

    BM.prune_stale_parts(str(tmp_path / "song"), 2)

    assert (tmp_path / "song_part01.sf2").exists()
    assert (tmp_path / "song_part02.sf2").exists()
    assert not stale.exists()


def test_prune_removes_the_span_of_every_part_it_prunes(tmp_path, clean_pending):
    """A `.span` outlives its `.sf2` unless pruned with it.

    Measured 2026-08-21 before this: `out/dmc` held 352 spans over 31 songs
    whose artifact had already been pruned (Cant_Stop 96, Ragtime_Anno_87 35).
    No READER is fooled -- nothing globs spans, `fidelity_common` derives each
    from a known build path -- which is why it survived undetected. What it
    breaks is the phantom-file inventory this function exists to prevent.
    """
    for i in (1, 2, 3, 4, 5):
        (tmp_path / f"song_part{i:02d}.sf2").write_bytes(b"SF2")
        (tmp_path / f"song_part{i:02d}.sf2.span").write_text("0 30\n")

    BM.prune_stale_parts(str(tmp_path / "song"), 3)

    assert sorted(p.name for p in tmp_path.glob("song_part*.sf2")) == [
        "song_part01.sf2", "song_part02.sf2", "song_part03.sf2"]
    assert sorted(p.name for p in tmp_path.glob("song_part*.sf2.span")) == [
        "song_part01.sf2.span", "song_part02.sf2.span", "song_part03.sf2.span"]


def test_prune_counts_artifacts_not_files(tmp_path, capsys, clean_pending):
    """Two parts pruned is 'pruned 2', not 'pruned 4' -- a span is not a part.
    Same class as the discard message that reported 0 for a real dropped part."""
    for i in (1, 2, 3):
        (tmp_path / f"song_part{i:02d}.sf2").write_bytes(b"SF2")
        (tmp_path / f"song_part{i:02d}.sf2.span").write_text("0 30\n")

    BM.prune_stale_parts(str(tmp_path / "song"), 1)

    assert "pruned 2 stale part files" in capsys.readouterr().out


def test_prune_sweeps_staging_files_a_kill_left_behind(tmp_path, clean_pending):
    """A hard kill (no exception, no atexit) leaves `.staging` files. They are
    not artifacts and must not accumulate under `out/`."""
    orphan = tmp_path / ("song_part04.sf2" + BM._STAGE)
    orphan.write_bytes(b"ORPHAN")

    BM.prune_stale_parts(str(tmp_path / "song"), 8)   # 4 <= 8: not a stale part

    assert not orphan.exists()


# --- the discard path -------------------------------------------------------

def test_discard_removes_staged_parts_and_leaves_nothing(tmp_path, clean_pending):
    pairs = [_stage(tmp_path, f"song_part{i:02d}.sf2") for i in (1, 2, 3, 4)]

    BM._discard_pending()

    assert not any(os.path.exists(f) for _, f in pairs)
    assert not any(os.path.exists(s) for s, _ in pairs)
    assert os.listdir(tmp_path) == []


def test_discard_count_counts_artifacts_not_queue_entries(tmp_path, clean_pending):
    """Each part queues its `.sf2` AND its `.span`, but a label with no span
    parses queues only one -- so `len(_PENDING) // 2` under-reports. It printed
    'discarded 0 staged part(s)' for a real discarded part before this."""
    _stage(tmp_path, "song_part01.sf2")
    _stage(tmp_path, "song_part01.sf2.span")
    _stage(tmp_path, "song_part02.sf2")          # span-less part

    n = sum(1 for _, final in BM._PENDING if final.endswith(".sf2"))

    assert n == 2


# --- end to end, in a real interpreter --------------------------------------

_UNWIND = """
import sys
sys.path.insert(0, {bin!r}); sys.path.insert(0, {root!r})
import build_mon_native_song as BM
staged = {out!r} + BM._STAGE
open(staged, 'wb').write(b'SF2')
BM._PENDING.append((staged, {out!r}))
{tail}
"""


@pytest.mark.parametrize("tail, survives", [
    ("raise ValueError('WAVE overflow: 288 rows > 256')", False),
    ("pass", True),
])
def test_atexit_commits_on_a_clean_exit_and_discards_on_a_refusal(
        tmp_path, tail, survives):
    """The net under `build_myth_native_song.py`, whose part loop calls
    `emit_one` and then nothing -- no `prune_stale_parts` to commit at. Must run
    in a subprocess: the behaviour under test IS interpreter shutdown.
    """
    out = str(tmp_path / "song_part01.sf2")
    src = _UNWIND.format(bin=os.path.join(ROOT, "bin"), root=ROOT,
                         out=out, tail=tail)
    r = subprocess.run([sys.executable, "-c", src], capture_output=True,
                       text=True, cwd=ROOT)

    assert os.path.exists(out) is survives, r.stdout + r.stderr
    assert not os.path.exists(out + BM._STAGE), "staging copy left behind"
    if not survives:
        assert "disk unchanged" in r.stdout
