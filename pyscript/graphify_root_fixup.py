"""Repair graphify-out/.graphify_root so the code graph is queryable in this clone.

WHY THIS EXISTS AT ALL
----------------------
`graphify` records the directory it extracted, as a bare path, in
`graphify-out/.graphify_root`. Run `graphify extract` from Git Bash and the
recorded value is a POSIX-style path such as

    /c/Users/mit/claude/c64server/sidm2

Windows `pathlib.Path()` parses that as a DRIVE-RELATIVE path beginning with a
root directory named `c`, which does not exist. Nothing crashes -- graphify
carries on and answers queries against a root it cannot resolve, so the failure
is SILENT. That is what makes it worth a script rather than a note: a stale
root does not look like an error, it looks like an empty result.

AND WHY IT CANNOT LIVE IN graphify-out/ ITSELF
----------------------------------------------
`.gitignore` ignores `graphify-out/` wholesale (the directory is ~37 MB of
rebuildable cache). So the repaired file is untracked by construction: it does
not survive a fresh clone, and anyone who re-extracts from Git Bash re-breaks
it. A repair that lives inside the thing it repairs is not durable. This script
is tracked, computes the correct root from ITS OWN location, and is therefore
correct in any clone on any machine without being edited.

WHAT IT DELIBERATELY DOES NOT CLAIM
-----------------------------------
Repairing the root does NOT make `graphify path` and `graphify query`
trustworthy. Measured separately in this repo: the
`bin_build_sdi_native_song -> bin_build_mon_native_song` import edge IS present
in `graph.json`'s links, yet `graphify path` reported "no directed path" in
both directions with the correct node ids. A NEGATIVE FROM THE CLI MEANS
NOTHING. Read `graph.json`'s `links` directly, map node ids via their
`source_file` field, treat a cross-file edge as a prompt to LOOK, and confirm
with grep. See docs/guides/GRAPHIFY_GUIDE.md.

Usage:
    py -3 pyscript/graphify_root_fixup.py           # repair if needed
    py -3 pyscript/graphify_root_fixup.py --check   # report only, never write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# This file is pyscript/graphify_root_fixup.py, so the repo root is two up.
# Deriving it rather than hard-coding it is the whole point: the last recorded
# value was an absolute path to one developer's machine.
REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_FILE = REPO_ROOT / "graphify-out" / ".graphify_root"


def resolves_to_repo_root(recorded: str, repo_root: Path | None = None) -> bool:
    """True when `recorded` already names this repo, however it is spelled.

    Case and trailing separators are not defects -- Windows is case-insensitive
    and graphify itself wrote `SIDM2` for a directory named `sidm2`. Rewriting
    over a value that already works is churn, and churn in a file nobody reads
    is how a fixup becomes noise. Only a value that does not RESOLVE is broken.
    """
    root = REPO_ROOT if repo_root is None else repo_root
    text = recorded.strip()
    if not text:
        return False
    try:
        candidate = Path(text).resolve()
    except (OSError, ValueError):
        # A Git Bash path can raise on some Windows configurations rather than
        # merely resolving to something absent. Both mean "broken".
        return False
    if not candidate.exists():
        return False
    try:
        return candidate.samefile(root)
    except OSError:
        return False


def inspect(root_file: Path | None = None, repo_root: Path | None = None):
    """Return (status, recorded_value). Never writes.

    status is one of:
      'absent'  -- no graphify-out/.graphify_root (a fresh clone; nothing to do)
      'ok'      -- the recorded value resolves to this repo
      'broken'  -- it does not, and a query run against it will silently misfire
    """
    path = ROOT_FILE if root_file is None else root_file
    if not path.exists():
        return "absent", None
    recorded = path.read_text(encoding="utf-8", errors="replace")
    if resolves_to_repo_root(recorded, repo_root):
        return "ok", recorded
    return "broken", recorded


def repair(root_file: Path | None = None, repo_root: Path | None = None) -> bool:
    """Rewrite the root file when it is broken. Returns True if it wrote.

    The value is written with NO trailing newline, matching what graphify
    itself produces -- the file on disk here was 35 bytes for a 35-character
    path. Adding a newline is the kind of "harmless" difference that turns a
    string comparison somewhere upstream into a second silent failure.
    """
    path = ROOT_FILE if root_file is None else root_file
    root = REPO_ROOT if repo_root is None else repo_root
    status, _ = inspect(path, root)
    if status != "broken":
        return False
    path.write_text(str(root), encoding="utf-8", newline="")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="report only; exit 1 if a repair is needed")
    a = ap.parse_args(argv)

    status, recorded = inspect()
    if status == "absent":
        print("no %s -- nothing to repair (run /graphify to build the graph)"
              % ROOT_FILE)
        return 0
    if status == "ok":
        print("ok: .graphify_root resolves to this repo (%r)" % recorded)
        return 0

    print("BROKEN: .graphify_root is %r, which does not resolve to %s"
          % (recorded, REPO_ROOT))
    if a.check:
        print("--check given, not writing. Re-run without it to repair.")
        return 1
    repair()
    print("repaired -> %s" % REPO_ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
