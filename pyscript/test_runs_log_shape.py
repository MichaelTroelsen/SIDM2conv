"""Shape guards for .claude/tasks/runs.jsonl -- specifically its `opened` arrays.

WHY THIS EXISTS. `/whattask` reads every `opened` entry as a TASK ID and folds it
into the next plan. Four entries in the log are absolute Windows paths, so the
plan grew four "tasks" named `C:/Users/mit/claude/c64server/sidm2/docs/ROADMAP.md`
and similar. Nothing downstream can run those, and nothing upstream noticed.

THE RULE IS "NOT A PATH", NOT "LOWERCASE". The obvious rule -- `^[a-z0-9-]+$` --
is WRONG here and the log proves it: it flags eight entries, and four of them are
perfectly good ids that merely carry uppercase for emphasis
(`dmc-part01-and-parts19-22-are-ONE-defect-not-two`,
`patterns-a-jN-verify-on-one-file-is-structurally-serial`,
`laxity-freq-clamp-to-5D-hides-a-failure-instead-of-refusing`,
`laxity-freq-table-search-must-establish-the-SIZE-not-just-the-address`).
`/whattask` handles those without complaint. What it cannot handle is a path.
So the guard tests for path-shaped entries -- separators, a drive colon,
whitespace -- and leaves casing alone.

THE LOG IS APPEND-ONLY, so the four bad records CANNOT be removed; they are
evidence of what a run actually opened. They are frozen below as named
exceptions, which is what lets this file assert the rule for everything written
from here on without rewriting history to do it.
"""

import json
import os
import re
from pathlib import Path

import pytest

LOG = Path(__file__).resolve().parent.parent / ".claude" / "tasks" / "runs.jsonl"

# The four historical violations, frozen verbatim. All four were opened by ONE
# record (`roadmap-e1-vice-voice-mute`), which is itself the tell: a single run
# emitted paths where it meant ids, so this is one mistake rather than a habit.
KNOWN_PATH_ENTRIES = frozenset({
    "C:/Users/mit/claude/c64server/sidm2/docs/ROADMAP.md",
    "C:/Users/mit/claude/c64server/sidm2/scripts/sid_to_sf2.py",
    "C:/Users/mit/claude/c64server/sidm2/sidm2/audio_export_wrapper.py",
    "C:/Users/mit/claude/c64server/sidm2/sidm2/sidplayfp_wrapper.py",
})

_PATH_SHAPED = re.compile(r"[/\\]|^[A-Za-z]:|\s")


def looks_like_a_path(entry: str) -> bool:
    """True when an `opened` entry is a filesystem path rather than a task id.

    Deliberately NOT a casing check: see the module docstring. A slug with
    uppercase in it is still a slug.
    """
    return bool(_PATH_SHAPED.search(entry)) or not entry


def _last_record_per_id(log_path=LOG):
    """(line number, record) for the LAST line carrying each record id.

    A record can be superseded by a later one with the same id, and that is
    exactly what /whattask (step 2b) and hooks/digest.js both read -- only the
    last record's `opened` array is ever folded into a plan. A superseded
    record's `opened` entries cannot cause the harm this file guards against,
    so the path check must not see them either.
    """
    if not log_path.exists():
        return {}
    latest = {}
    with log_path.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            latest[rec.get("id")] = (n, rec)
    return latest


def _opened_entries(log_path=LOG):
    """(line number, record id, opened entry) for every entry in the log,
    across ALL records -- used only where every historical entry matters
    (the frozen-exceptions test), never for the path check."""
    if not log_path.exists():
        return
    with log_path.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            rec = json.loads(line)
            for entry in (rec.get("opened") or []):
                yield n, rec.get("id"), entry


def _opened_entries_last_per_id(log_path=LOG):
    """(line number, record id, opened entry), scoped to each id's LAST
    record -- what /whattask and hooks/digest.js actually read."""
    for n, rec in _last_record_per_id(log_path).values():
        for entry in (rec.get("opened") or []):
            yield n, rec.get("id"), entry


pytestmark = pytest.mark.skipif(
    not LOG.exists(), reason=".claude/tasks/runs.jsonl not present in this checkout")


def test_the_predicate_actually_discriminates():
    """POSITIVE CONTROL, first: a guard that called everything an id would pass
    the next test vacuously, and this session has shipped two such tests."""
    assert looks_like_a_path("C:/Users/mit/claude/c64server/sidm2/docs/ROADMAP.md")
    assert looks_like_a_path("docs/ROADMAP.md")
    assert looks_like_a_path("sidm2\\laxity_parser.py")
    assert looks_like_a_path("two words")
    assert looks_like_a_path("")
    # ...and the four real ids it must NOT condemn, which is the half a
    # lowercase rule got wrong:
    assert not looks_like_a_path("dmc-part01-and-parts19-22-are-ONE-defect-not-two")
    assert not looks_like_a_path("laxity-freq-table-search-must-establish-the-SIZE-not-just-the-address")
    assert not looks_like_a_path("patterns-a-jN-verify-on-one-file-is-structurally-serial")
    assert not looks_like_a_path("graphify-guide-into-docs-index")


def test_no_NEW_opened_entry_is_a_filesystem_path(log_path=LOG):
    """The rule, for everything except the four frozen historical records.

    Scoped to each id's LAST record: a record superseded by a later one with
    the same id has its `opened` array read by nothing downstream (/whattask
    step 2b and hooks/digest.js both read last-record-per-id), so a
    superseded record's path-shaped entries cannot cause the harm this test
    guards against and must not be flagged.
    """
    offenders = [(n, i, e) for n, i, e in _opened_entries_last_per_id(log_path)
                 if looks_like_a_path(e) and e not in KNOWN_PATH_ENTRIES]
    assert not offenders, (
        "an `opened` entry is a path, not a task id -- /whattask will fold it into "
        "the next plan as a task nothing can run:\n"
        + "\n".join("  line %d  %s  ->  %r" % o for o in offenders))


def test_the_frozen_exceptions_are_still_exactly_those_four():
    """If this fires, the append-only log was REWRITTEN, which is a bigger
    problem than the paths. It also stops the exception list quietly growing
    into a place where new violations get parked instead of fixed."""
    found = {e for _, _, e in _opened_entries() if e in KNOWN_PATH_ENTRIES}
    assert found == set(KNOWN_PATH_ENTRIES), (
        "the frozen historical path entries changed: missing %s, unexpected %s"
        % (sorted(set(KNOWN_PATH_ENTRIES) - found), sorted(found - set(KNOWN_PATH_ENTRIES))))


def test_every_opened_entry_is_a_string():
    """Cheap, and it is the failure mode that would make the checks above
    raise a TypeError instead of reporting a violation."""
    bad = [(n, i, e) for n, i, e in _opened_entries() if not isinstance(e, str)]
    assert not bad, "non-string `opened` entries: %r" % (bad,)
