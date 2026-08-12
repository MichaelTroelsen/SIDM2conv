"""The out/ -> player mapping is defined ONCE, and covers everything on disk.

Three shipped players (Matt Gray, Future Composer, HardTrack) were missing from
both conversion indexes at the same time, because each generator carried its own
hand-maintained copy of the mapping under a comment claiming they were "kept in
sync manually". Deduplicating alone would not have caught it -- a single stale
list is still stale -- so the second test here asserts the mapping covers every
`out/` directory that actually holds SF2 files.

That is the same move as `test_version_stamps_agree.py`: replace a checklist
item with a failing test.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

import player_index  # noqa: E402


def test_the_mapping_is_not_duplicated_in_the_generators():
    """Neither generator may re-declare the table; they must import it.

    Pins the actual defect: two copies that drift. A generator that defines its
    own PLAYERS list again would pass every other test in the suite.
    """
    for name in ("gen_sf2_index.py", "gen_conversion_index.py"):
        src = open(os.path.join(_HERE, name), encoding="utf-8").read()
        assert "from player_index import" in src, f"{name} must import the mapping"
        for literal in ("PLAYERS = [", "OUT_PLAYERS = [",
                        "SID_DIRS = {", "OUT_SID_DIRS = {"):
            assert literal not in src, (
                f"{name} re-declares `{literal.split()[0]}` instead of importing "
                f"it -- that is the duplication which hid three shipped players")


def test_every_built_directory_is_classified():
    """No out/ dir with SF2 files may be in neither PLAYERS nor IGNORED.

    Failing here means a build exists that no document will ever mention. Fix by
    classifying it in `player_index.py`: PLAYERS to index it, IGNORED (with a
    reason) to exclude it deliberately.
    """
    missing = player_index.unclassified()
    assert not missing, (
        "unclassified out/ directories holding SF2 files: "
        + ", ".join(f"{d} ({n} files)" for d, n in missing))


def test_ignored_entries_carry_a_reason():
    """An exclusion has to be a decision on the record, not a bare name."""
    for subdir, reason in player_index.IGNORED.items():
        assert reason and len(reason) > 15, (
            f"IGNORED[{subdir!r}] needs a real reason, got {reason!r}")


def test_players_and_sid_dirs_agree():
    """Every indexed player needs a corpus dir, and vice versa -- a mismatch
    silently drops the PSID metadata (title/author/released) for that player."""
    players = {p[0] for p in player_index.PLAYERS}
    assert players == set(player_index.SID_DIRS), (
        f"PLAYERS-only: {players - set(player_index.SID_DIRS)}, "
        f"SID_DIRS-only: {set(player_index.SID_DIRS) - players}")


def test_no_subdir_is_listed_twice():
    subs = [p[0] for p in player_index.PLAYERS]
    assert len(subs) == len(set(subs)), "duplicate subdir in PLAYERS"
    assert not (set(subs) & set(player_index.IGNORED)), (
        "a subdir is both indexed and ignored")


def test_the_guard_actually_detects_an_unclassified_dir(tmp_path):
    """Mutation test: the guard must FAIL on a planted directory.

    Without this, `unclassified()` returning [] proves nothing -- a function
    that always returns [] passes the coverage test above.
    """
    out = tmp_path / "out" / "brand_new_player"
    out.mkdir(parents=True)
    (out / "Song_part01.sf2").write_bytes(b"\x00")
    found = player_index.unclassified(str(tmp_path))
    assert found == [("brand_new_player", 1)], found


def test_a_dir_without_sf2_files_is_not_flagged(tmp_path):
    """Scratch dirs that hold no SF2 need no entry -- only built output counts."""
    (tmp_path / "out" / "empty_scratch").mkdir(parents=True)
    assert player_index.unclassified(str(tmp_path)) == []
