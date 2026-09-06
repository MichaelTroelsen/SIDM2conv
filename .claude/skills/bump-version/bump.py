"""Bump the package version and re-stamp every documented copy of it.

    py -3 .claude/skills/bump-version/bump.py 3.29.0 --dry-run
    py -3 .claude/skills/bump-version/bump.py 3.29.0
    py -3 .claude/skills/bump-version/bump.py 3.29.0 --release-unreleased

THE STAMP LOCATIONS ARE NOT LISTED HERE. They are imported from
`pyscript/test_version_stamps_agree.py`, which already owns them and whose
docstring names the exact failure this avoids: "one fact in five places, where
only some copies get updated". A hard-coded list in this script would be a SIXTH
copy of that fact and would go stale the same way ACCURACY_MATRIX.md and
README.md each did. Add a stamped file to STAMPS in the test; this script picks
it up with no edit.

LINE ENDINGS ARE PRESERVED PER FILE. CLAUDE.md is CRLF and other docs are not;
the repo has no .gitattributes and core.autocrlf is true, so rewriting a CRLF
file with LF produces a whole-file diff. Files are read and written with
newline="" so the substitution touches only the version characters.
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pyscript"))

import test_version_stamps_agree as pins  # noqa: E402  (the source of truth)

INIT = ROOT / "sidm2" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", newline="")


def write(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8", newline="")


def sub_group1(text, pattern, new):
    """Replace only capture group 1 of the first match. Returns (text, old)."""
    m = re.search(pattern, text)
    if not m:
        return None, None
    a, b = m.span(1)
    return text[:a] + new + text[b:], m.group(1)


def bump_init(version, date, dry):
    text = read(INIT)
    out, oldv = sub_group1(text, r'__version__\s*=\s*"(\d+\.\d+\.\d+)"', version)
    if out is None:
        sys.exit("sidm2/__init__.py: no __version__ = \"x.y.z\" found")
    out2, oldd = sub_group1(
        out, r'__build_date__\s*=\s*"(\d{4}-\d{2}-\d{2})"', date)
    if out2 is None:
        sys.exit("sidm2/__init__.py: no __build_date__ found")
    print("  sidm2/__init__.py        %s -> %s, %s -> %s" % (oldv, version, oldd, date))
    if not dry:
        write(INIT, out2)
    return oldv


def bump_stamps(version, date, dry):
    missing = []
    for rel, pattern, hint in pins.STAMPS:
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        out, old = sub_group1(read(p), pattern, version)
        if out is None:
            missing.append("%s (pattern %s did not match -- %s)" % (rel, pattern, hint))
            continue
        print("  %-24s %s -> %s" % (rel, old, version))
        if not dry:
            write(p, out)
    for rel, pattern in pins.DATE_STAMPS:
        p = ROOT / rel
        if not p.exists():
            continue
        out, old = sub_group1(read(p), pattern, date)
        if out is None:
            missing.append("%s (date pattern %s did not match)" % (rel, pattern))
            continue
        print("  %-24s date %s -> %s" % (rel, old, date))
        if not dry:
            write(p, out)
    return missing


def handle_changelog(version, date, dry, release_unreleased):
    text = read(CHANGELOG)
    heading = "## [%s]" % version
    if heading in text:
        print("  CHANGELOG.md             already has '%s'" % heading)
        return True
    if not release_unreleased:
        print("  CHANGELOG.md             NO '%s' heading -- write the release "
              "entry yourself, or re-run with --release-unreleased to promote "
              "[Unreleased]" % heading)
        return False
    m = re.search(r"^##\s*\[Unreleased\].*$", text, re.M)
    if not m:
        print("  CHANGELOG.md             no [Unreleased] heading to promote")
        return False
    nl = "\r\n" if "\r\n" in text[:4000] else "\n"
    new = "## [Unreleased]" + nl + nl + "## [%s] - %s" % (version, date)
    print("  CHANGELOG.md             promoting [Unreleased] -> %s" % heading)
    if not dry:
        write(CHANGELOG, text[:m.start()] + new + text[m.end():])
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("version")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--release-unreleased", action="store_true",
                    help="promote the [Unreleased] CHANGELOG heading to this version")
    a = ap.parse_args()

    if not VERSION_RE.match(a.version):
        sys.exit("version must be x.y.z, got %r" % a.version)

    print("Bumping to %s (%s)%s" % (a.version, a.date,
                                    "  [DRY RUN]" if a.dry_run else ""))
    old = bump_init(a.version, a.date, a.dry_run)
    if old == a.version:
        print("  NOTE: the package was already at %s" % a.version)
    missing = bump_stamps(a.version, a.date, a.dry_run)
    ok_changelog = handle_changelog(a.version, a.date, a.dry_run,
                                    a.release_unreleased)

    if missing:
        print("\nNOT RE-STAMPED -- fix by hand, these will fail the test:")
        for m in missing:
            print("  - %s" % m)

    if a.dry_run:
        print("\nDry run: nothing written.")
        return 0

    print("\nRunning the pinning test...")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "pyscript/test_version_stamps_agree.py",
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(ROOT), capture_output=True, text=True)
    print(r.stdout[-2500:] or r.stderr[-2500:])
    if r.returncode != 0:
        print("PINNING TEST FAILED -- the bump is half-done. Fix before committing.")
        return 1
    if not ok_changelog:
        print("Stamps agree, but CHANGELOG.md still has no heading for this "
              "version. The test will fail until it does.")
        return 1
    print("All stamps agree. NOTHING WAS COMMITTED -- that is yours to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
