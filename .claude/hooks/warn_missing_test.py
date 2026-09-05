"""PostToolUse(Write|Edit): warn when a source file has no test exercising it.

The repo convention is `pyscript/test_<name>.py` for every source `<name>.py`.
The /whattask plan's own notes record this rule being broken five times, and a
cross-check on 2026-08-26 found THIRTEEN more builders and tools with no test
file at all -- build_mon_native_song.py, build_sdi_native_song.py,
hardtrack_native_rebuild.py, sf2_editor_automation.py among them.

WARNS, never blocks. A missing test is a debt to record, not a reason to refuse
an edit -- and a PostToolUse hook cannot block the write anyway.


WHY THIS CHECKS IMPORTS AND NOT JUST THE FILENAME (decided 2026-09-05, do not
re-litigate). The first version warned whenever `pyscript/test_<name>.py` did
not exist. That is a NAMING check wearing a coverage check's clothes, and it was
wrong a third of the time. Measured by running THIS hook over every watched
file (the numbers below are its own behaviour, not a separate estimate): the
name-only rule warned on 91 of 169 watched files; the name+import rule warns on
62. Twenty-nine of the warnings -- 32% -- were files that a test does exercise,
just under another name. sidm2/models.py is the clearest case: 12 test files
import it and there is no test_models.py. By directory the survivors are
sidm2 41 (of 68), bin 13 (of 15), scripts 8 (of 8).

A warning wrong a third of the time is one people learn to ignore, which wastes
the hook entirely. So it now fires only when BOTH are true: no same-named test
file, AND no test file imports the module at all. Scanning all 182 test files
costs ~12-32 ms, which is nothing for a PostToolUse hook.


THE SCOPE DECISION (same date). WATCHED stays sidm2/ + bin/build_* + scripts/
rather than narrowing to sidm2/ only. Narrowing was the other option on the
table and is rejected because the import-aware check above already removes the
noise that made narrowing attractive, and because bin/build_* holds the SEVEN
genuinely-untested native song builders -- the highest-value gap in the whole
census. Dropping bin/ would hide exactly the files most worth a test.


THE TRIAGE, measured 2026-09-05 at HEAD 57f6ca3 (161 non-test files under
sidm2/ + bin/build_*, 83 with no same-named test -- 68 + 15. NOTE this is not
the 94/74/20 the task record quotes; five builders and several sidm2 modules
gained tests since that count, so the debt is smaller and shrinking).

  (a) LOAD-BEARING AND GENUINELY UNTESTED -- worth a test, in this order:
      bin/build_dmc_native_song.py          bin/build_fc_native_song.py
      bin/build_hardtrack_native_song.py    bin/build_hubbard_native_song.py
      bin/build_mattgray_native_song.py     bin/build_romuzak_native_song.py
      bin/build_soundmonitor_native_song.py
        -- each is a per-player Stage B builder that produces shipped corpus
           artifacts, and none has any test importing it.
      sidm2/sf2_caps.py       13 shipped importers, 0 test importers, 43 LOC
      sidm2/kimmel_parser.py   6 shipped importers, 0 test importers, 387 LOC
        -- the only two sidm2 modules that are both widely imported and touched
           by no test at all. sf2_caps is 43 lines of constants that five
           builders compare their table sizes against; a wrong cap silently
           truncates a build.

  (b) CEREMONY -- a test here would be ritual, not safety:
      the 9 sidm2 modules with ZERO shipped importers and zero test importers
      (laxity_raw_np21_builder 1101 LOC, np21_edit_area_builder 846,
       sid_structure_extractor 625, laxity_music_data_injector 500,
       sf2_packed_reader 468, sf2_compatibility 453, extraction_validator 371,
       memory_overlap_detector 327, galway_trace 100) -- 4,791 lines that
      nothing in the shipped tree imports. These want a provenance decision
      (keep? archive?), not a test.
      the 8 bin/ driver-and-corpus assembly one-offs (build_*_driver_full x3,
      build_galway_corpus, build_galway_digi{,_full,_songs},
      build_galway_trace_song) -- run by hand, output checked by eye.

  The 27 sidm2 modules covered under another name are neither: they need a
  RENAME or a cross-reference, not a new test, and the hook no longer nags
  about them.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WATCHED = ("sidm2", "bin", "scripts")


def _a_test_imports(stem: str) -> bool:
    """True if any pyscript/test_*.py imports `stem`, under any spelling.

    Cheap enough to do on every edit: 182 files / 2.0 MB / ~12 ms. Deliberately
    over-matches rather than under-matches -- a false NEGATIVE here just means
    the hook stays quiet about a module that is in fact tested, which is the
    harmless direction. Warning wrongly is the failure mode that matters.
    """
    pat = re.compile(
        r"(from\s+sidm2\.%s\s+import|import\s+sidm2\.%s\b"
        r"|from\s+%s\s+import|^\s*import\s+%s\b)" % (stem, stem, stem, stem),
        re.M)
    try:
        for f in (REPO_ROOT / "pyscript").glob("test_*.py"):
            try:
                if pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                    return True
            except OSError:
                continue
    except OSError:
        return False
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    ti = data.get("tool_input") or {}
    tr = data.get("tool_response") or {}
    fp = tr.get("filePath") or ti.get("file_path")
    if not fp:
        return 0

    try:
        target = Path(fp).resolve()
        rel = target.relative_to(REPO_ROOT)
    except Exception:
        return 0                                   # outside the repo: not ours

    if target.suffix.lower() != ".py":
        return 0
    if target.name.startswith("test_"):
        return 0                                   # a test needs no test
    parts = rel.parts
    if not parts or parts[0] not in WATCHED:
        return 0
    if parts[0] == "bin" and not target.name.startswith("build_"):
        return 0                                   # bin/ is full of one-off probes

    expected = REPO_ROOT / "pyscript" / ("test_%s.py" % target.stem)
    if expected.exists():
        return 0
    if _a_test_imports(target.stem):
        return 0                                   # tested under another name

    msg = ("No test exercises %s -- there is no pyscript/test_%s.py AND no test "
           "file imports it. (The hook checks imports too, so this is a real gap "
           "rather than a naming mismatch: 29 of the 91 files the old rule "
           "warned about ARE covered elsewhere and no longer warn.) If this edit "
           "changes behaviour, create the test rather than leaving the gap; the "
           "triage in this hook's docstring says which files are worth one."
           % (rel.as_posix(), target.stem))
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
