"""The version number lives in five places. Two of them have gone stale.

`sidm2/__init__.py` is the manifest that actually ships, so it is canonical;
the other four are documentation banners that a human has to remember to
update. Twice they have not been:

  * `docs/reference/ACCURACY_MATRIX.md` sat at v3.22.0 through the v3.23.0
    release -- recorded in CLAUDE.md's own bump checklist, which was then
    amended to name the file.
  * `README.md`'s banner sat at v3.22.0 for **four** releases (3.23.0, 3.24.0,
    3.25.0, 3.26.0) for exactly the same reason: the amended checklist still
    did not name README.

That is the "duplicated truth" failure -- one fact in five places, where only
some copies get updated -- and a checklist is the wrong remedy, because the
checklist is what failed twice. This test is the remedy: the stamps cannot
disagree without something going red.

To add a new stamped location, add a row to STAMPS.
"""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sidm2  # noqa: E402

# (path, regex capturing the version, human hint for the failure message)
STAMPS = [
    ("README.md", r"\*\*Version (\d+\.\d+\.\d+)\*\*", "the banner on line 6"),
    ("CLAUDE.md", r"\*\*SIDM2 v(\d+\.\d+\.\d+)\*\*", "the header on line 3"),
    ("docs/reference/ACCURACY_MATRIX.md", r"\*\*Version\*\*: (\d+\.\d+\.\d+)",
     "the stamp under the title"),
    ("STORY.md", r"\*\*Current version:\*\* v(\d+\.\d+\.\d+)",
     "the 'Current version:' narrative"),
]

DATE_STAMPS = [
    ("README.md", r"Build Date: (\d{4}-\d{2}-\d{2})"),
    ("CLAUDE.md", r"\| Updated (\d{4}-\d{2}-\d{2})"),
]


def _read(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        pytest.skip(f"{rel} not present")
    return open(p, encoding="utf-8", errors="replace").read()


@pytest.mark.parametrize("rel,pattern,hint", STAMPS)
def test_documented_version_matches_the_package(rel, pattern, hint):
    m = re.search(pattern, _read(rel))
    assert m, (
        f"{rel}: no version stamp matched {pattern!r}. If the wording changed, "
        f"update STAMPS in this test -- do not delete the check."
    )
    assert m.group(1) == sidm2.__version__, (
        f"{rel} says {m.group(1)} but sidm2/__init__.py says "
        f"{sidm2.__version__}. Update {hint}. This exact drift has shipped "
        f"twice before."
    )


@pytest.mark.parametrize("rel,pattern", DATE_STAMPS)
def test_documented_build_date_matches_the_package(rel, pattern):
    m = re.search(pattern, _read(rel))
    assert m, f"{rel}: no build date matched {pattern!r}"
    assert m.group(1) == sidm2.__build_date__, (
        f"{rel} says {m.group(1)} but sidm2/__init__.py says "
        f"{sidm2.__build_date__}."
    )


def test_the_changelog_has_a_heading_for_the_current_version():
    """A bump that leaves everything under [Unreleased] is a half-done release.

    That happened at v3.25.0: the version was bumped but CHANGELOG kept the
    entries under `## [Unreleased]` with no `## [3.25.0]` heading, and it took
    a follow-up commit to notice.
    """
    text = _read("CHANGELOG.md")
    assert f"## [{sidm2.__version__}]" in text, (
        f"CHANGELOG.md has no '## [{sidm2.__version__}]' heading -- the "
        f"release entries are probably still under [Unreleased]."
    )
