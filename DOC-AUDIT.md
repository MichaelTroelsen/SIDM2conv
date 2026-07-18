# Documentation Audit — SIDM2

**Audited:** 2026-07-18
**Tree state:** commit `751aca7` on `master` — **working tree dirty (9 entries)**
**Repo:** https://github.com/MichaelTroelsen/SIDM2conv (PUBLIC)
**Findings:** 17 (3 P0, 5 P1, 6 P2, 3 P3) — all HIGH confidence
**Filed as:** issues [#6](https://github.com/MichaelTroelsen/SIDM2conv/issues/6)–[#15](https://github.com/MichaelTroelsen/SIDM2conv/issues/15) (10 issues, grouped by root cause)

| Finding | Issue |
|---|---|
| P0-1 `generate_stinsen_html.py` | [#6](https://github.com/MichaelTroelsen/SIDM2conv/issues/6) |
| P0-2 CONTRIBUTING test command | [#7](https://github.com/MichaelTroelsen/SIDM2conv/issues/7) |
| P0-3 + P1-5 archived-but-documented | [#8](https://github.com/MichaelTroelsen/SIDM2conv/issues/8) |
| P1-4 `memory/` absent | [#9](https://github.com/MichaelTroelsen/SIDM2conv/issues/9) |
| P1-1 filter "not implemented" | [#10](https://github.com/MichaelTroelsen/SIDM2conv/issues/10) |
| P1-2 + P3-1 version divergence / duplication | [#11](https://github.com/MichaelTroelsen/SIDM2conv/issues/11) |
| P1-3 `tools/README.md` | [#12](https://github.com/MichaelTroelsen/SIDM2conv/issues/12) |
| P2-5 missing LICENSE | [#13](https://github.com/MichaelTroelsen/SIDM2conv/issues/13) |
| P2-1 CONTRIBUTING worked example | [#14](https://github.com/MichaelTroelsen/SIDM2conv/issues/14) |
| P2-0, P2-2, P2-3, P2-4, P2-6, P3-2, P3-3 | [#15](https://github.com/MichaelTroelsen/SIDM2conv/issues/15) (umbrella) |

Nothing was withheld: the secrets scan was clean, so no security finding needed suppressing on this
public repo, and all 17 findings are HIGH confidence.

> Findings describe the **working tree**, which does not match `HEAD`. Uncommitted at audit
> time: `M sidm2/mon_parser.py`; untracked `SID/Gallefoss_Glenn/`, `SID/Jeff/`,
> `SID/Red_kommel_jeroen/`, `SID_INVENTORY.md`, `archive/cleanup_2026-07-09/`, `bin/LFT/`,
> `bin/SIDDuzz/`, `bin/_kimmel_work/`.

---

## Scope — what was and was not read

The repo holds **192 markdown files / 4.0 MB** (excluding `archive/`, `.venv/`,
`node_modules/`, `.pytest_cache/`). That is far beyond a single-pass read, so reading was
**tiered**. This report is not comprehensive and must not be read as such.

| Tier | Treatment | Files |
|---|---|---|
| **Tier 1** | Read in full, in the main thread | `README.md` (1096 lines), `CLAUDE.md` (215), `CONTRIBUTING.md` (586) |
| **Tier 2** | Read in full, delegated; claims adjudicated centrally | all 19 of `docs/players/*.md` (incl. `PLAYBOOK.md`, `PATTERNS.md`, `NATIVE_DRIVER.md`), `docs/ARCHITECTURE.md` (1079), `docs/guides/HTML_ANNOTATION_TOOL.md` (626), `docs/reference/ACCURACY_MATRIX.md` (91), `tools/README.md`, `tools/sf2pack/README.md`, `tools/sf2export/README.md`, `mcp-siddump/README.md`, `galway_sf2/README.md`, `scripts/autoit/README.md` |
| **Tier 3** | **Not read.** Existence verified only where linked from Tier 1/2 | the remaining ~160 files |

Delegated readers extracted claims only; they were forbidden from verifying anything, and every
returned claim was treated as LOW confidence until re-checked in the main thread against the
filesystem or code.

**Partially adjudicated:** the player docs carry several hundred 6502 addresses, register
offsets and per-tune fidelity figures. Their *paths and counts* were checked; the **addresses
and percentages were not** — verifying those means running the converter and tracer. See
Unverifiable.

**Blind spots — text search cannot see inside these.** A clean secrets scan over this repo is
not proof of absence. Not searched: `G5/siddump108.zip`, `bin/DMC/*.zip`, `bin/LFT/*.zip`,
`bin/SIDDuzz/*.zip`, `bin/drivers/*.zip`, `bin/FC10/*.zip`, `bin/RoMusak/*.zip`,
`bin/sound monitor/*.zip`, `learnings/codebase64_latest/**` (dozens of `.zip`/`.pdf`), and
PDFs including `bin/documentation/user_manual.pdf`, `bin/SIDDuzz/sdi_217_manual (1).pdf`,
`learnings/C64_Reference_Pages_202-231.pdf`.

---

## Ground truth established

Collected by execution before any prose was read.

| Fact | Value | Source |
|---|---|---|
| Code version | **3.21.0** | `sidm2/__init__.py:7` |
| Build date | 2026-07-16 | `sidm2/__init__.py:8` |
| Packaging manifest | **none** | no `pyproject.toml`, `setup.py`, `package.json`, `go.mod` |
| Tests collected | **1916** (+8 collection errors) | `python -m pytest --collect-only -q` |
| `test_*.py` on disk | 125 (110 `pyscript/`, 14 `scripts/`) | `find` |
| Suites run by `test-all.bat` | **7** | `rg -o 'python (scripts\|pyscript)/\S+\.py' test-all.bat` |
| CI workflows | **5** | `ls .github/workflows/` |
| `.py` files | **527** (201 `pyscript/`, 176 `bin/`, 128 `sidm2/`, 22 `scripts/`) | `find -maxdepth 1` per dir |
| Live `.md` files | **192** | `find` |
| SID files | **1361** | `find SID -iname '*.sid'` |
| LICENSE file | **absent** | `ls` |

---

## Findings

### P0-1 — `generate_stinsen_html.py` was archived; six live references still point at it, including Quick Start

The file does not exist at the documented path. It is at
`archive/cleanup_2026-01-02/obsolete_utils/generate_stinsen_html.py`.

| Location | Text |
|---|---|
| `README.md:41` | `python pyscript/generate_stinsen_html.py input.sid` — **inside Quick Start** |
| `README.md:129` | `python pyscript/generate_stinsen_html.py input.sid` |
| `README.md:575` | `from pyscript.generate_stinsen_html import main` — Python API example |
| `README.md:728` | `│   ├── generate_stinsen_html.py` — project-structure tree |
| `CLAUDE.md:40` | `python pyscript/generate_stinsen_html.py file.sid       # HTML docs (3,700+ annotations)` |
| `CLAUDE.md:86` | ``**HTML Annotation Tool** (`pyscript/generate_stinsen_html.py`)`` |

Additionally `docs/guides/HTML_ANNOTATION_TOOL.md` — **626 lines** — documents this tool as a
current feature across ~12 invocation examples.

**Verification:** `find . -name 'generate_stinsen_html.py'` returns exactly one path, under
`archive/`. `[ -e pyscript/generate_stinsen_html.py ]` is false.

**Consequence:** the fifth command in Quick Start fails for every new user, and an agent
following `CLAUDE.md:86` will try to fix or reimplement a tool that was deliberately retired.

**Confidence:** HIGH.

---

### P0-2 — CONTRIBUTING.md's setup-verification command fails

`CONTRIBUTING.md:24`, in "Development Workflow → 1. Setup", under the comment
`# Run tests to verify setup`:

```
python -m unittest test_converter -v
```

**Verification — run in this session:**
```
ModuleNotFoundError: No module named 'test_converter'
FAILED (errors=1)
```

The file is `scripts/test_converter.py`; it is not importable as a top-level module. The same
command also appears at `CONTRIBUTING.md:155`, `:158`, `:161`, and at `:557` as the **first
item of the pull-request checklist** ("All tests pass (`python -m unittest test_converter -v`)").

`README.md:516` and `CLAUDE.md:12` instead teach `test-all.bat` / `python -m pytest`, both of
which work. Two documents teach incompatible conventions and CONTRIBUTING's is the broken one.

**Consequence:** the first thing a contributor runs fails, and the PR checklist can never be
truthfully ticked.

**Confidence:** HIGH.

---

### P0-3 — README documents an archived script as live, with a usage command

`README.md:439-442`:

```
**Regenerator 2000 Labeler** (`pyscript/regen2000_label_laxity_np21.py`):
- Auto-labels NP21 Laxity driver symbols in Regenerator 2000 via MCP HTTP
- Marks filter tables, INIT/PLAY entry points, SMC regions
- Usage: `python pyscript/regen2000_label_laxity_np21.py --port 3000`
```

**Adjudicated by the filesystem.** `CLAUDE.md:94` says this tool was archived 2026-04-29 to
`archive/cleanup_2026-04-29/orphaned_utils/`. `find` confirms exactly one copy, at that archive
path. README is wrong; CLAUDE.md is right.

**Confidence:** HIGH.

---

### P1-1 — README states filter conversion is unimplemented, and contradicts itself three times

`README.md:1037`, in Troubleshooting → Common Issues:

```
**Q: Filter data not preserved**
A: Filter conversion not yet implemented. Edit filters manually in SF2 editor.
```

Contradicted within the same file at `README.md:17` ("custom driver, **filter 100%**") and
`README.md:948` ("### v3.1.4 (2026-03-21) - Filter Accuracy 0% → 100%"), and by
`CLAUDE.md:159` ("filter accuracy 100% (Stinsen verified v3.1.4)").

**The code casts the deciding vote.** Filter conversion is implemented across at least eight
call sites:
`sidm2/table_extraction.py:958 find_and_extract_filter_table`,
`:885 detect_np21_filter_offsets`, `:1440 find_filter_table_np21_v2`,
`sidm2/driver11_section_injectors.py:707 inject_filter_table`,
`sidm2/sf2_writer.py:312 _inject_filter_table`, `:610 _emit_filter_cutoff_only_routine`,
`sidm2/laxity_converter.py:26 convert_filter_table`,
`sidm2/galway_format_converter.py:312 convert_filter_table`.
A dedicated validator exists at `pyscript/validate_filter_accuracy.py`.

The FAQ entry is dead text. A user trusting it does redundant manual work on data the
converter already carries.

**Confidence:** HIGH.

---

### P1-2 — Version divergence: code is 3.21.0, four live locations say 3.13.0

| Location | States | Correct? |
|---|---|---|
| `sidm2/__init__.py:7` | `__version__ = "3.21.0"` | **canonical** |
| `CLAUDE.md:3` | `**SIDM2 v3.21.0**` | ✅ |
| `docs/reference/ACCURACY_MATRIX.md:4` | `**Version**: 3.21.0` | ✅ |
| `README.md:6` | `**Version 3.13.0** \| Build Date: 2026-06-29` | ❌ |
| `README.md:1096` | `**Last Updated**: 2026-07-05 \| **Version**: 3.13.0` | ❌ |
| `docs/INDEX.md:6` | `**Version**: v3.13.0` | ❌ |
| `docs/INDEX.md:17` | `**Accuracy source of truth** (v3.13.0)` | ❌ |
| `CLAUDE.md:171` | ``docs/reference/ACCURACY_MATRIX.md` (accuracy source of truth, v3.13.0)` | ❌ — the file itself says 3.21.0 |

**Ranked P1, not P0:** the drift-catalog escalates version divergence to P0 when a *packaging
manifest* disagrees with the code, because installed artifacts then ship mislabelled. This
project has no manifest — nothing is published to a package index — so no mislabelled artifact
exists. The README badge is still the first thing every reader sees.

**Confidence:** HIGH.

---

### P1-3 — `tools/README.md` is a third-party product's README, and promises two absent binaries

The entire file (13 lines) is SIDwinder's own documentation, not SIDM2's:

```
# SIDwinder

Version: v0.2.6
...
## Dependencies

This package includes the necessary dependencies:
- tools/exomizer.exe - Used for compressing PRG files
- tools/KickAss.jar - The KickAss assembler used for compiling ASM files
- SIDwinder.cfg - Configuration file
```

**Verification:**
- `tools/exomizer.exe` — MISSING
- `tools/KickAss.jar` — MISSING
- `tools/SIDwinder.cfg` — present

"This package includes the necessary dependencies" is false for two of the three. The version
`v0.2.6` describes SIDwinder, not SIDM2 (3.21.0) — a reader browsing `tools/` sees a README
describing a different product at a wildly different version.

`tools/` does contain the five executables `README.md:783-787` promises — all present. The
defect is this file, not the directory.

**Confidence:** HIGH.

---

### P1-4 — The `memory/` knowledge store does not exist, and 11 live documents route agents to it

Eleven live documents reference **15 distinct `memory/*.md` files**. There is no `memory/`
directory.

**Absence protocol — all four steps, with positive control:**
```
ls -d memory                     → no memory/ in root
find . -maxdepth 3 -type d -name 'memory'  → (no output)
git check-ignore -v memory       → not gitignored
git ls-files 'memory/*' | wc -l  → 0 tracked
ls -d docs/players               → docs/players   ← positive control: the method sees directories
```
So it is not hidden, not ignored, and never tracked.

| Location | Reference |
|---|---|
| `CLAUDE.md:200` | ``Full details + card schema: `memory/tdz-c64-knowledge-base.md`.`` |
| `docs/players/PLAYBOOK.md:185` | ``Deep RE session memories \| `memory/*.md` (agent memory; per-player `*-re.md` files)`` |
| `docs/players/HUBBARD.md:131` | ``**Memory:** `memory/hubbard-player-re.md` (the complete arc log with every gotcha).`` |
| `docs/players/MON.md:171` | 4 files: `hawkeye-mon-player-re.md`, `myth-supremacy-mon-re.md`, `cybernoid-mon-orderlist-re.md`, `hawkeye-mon-filter-engine-re.md` |
| `docs/players/CLUSTERS.md:22` | 4 files plus `stinsen-*`, `beast-angular-*` globs |
| `docs/players/LAXITY.md:31`, `:47` | `corpus-state-2026-05-22`, `laxity-corpus-c2-failures`, `sid-root-4-criterion-status`, `laxity-np21.md` |
| `docs/players/SDI.md:36` | ``Trail: `memory/gallefoss-sdi-player.md`.`` |
| `docs/players/NP20.md:21` | `memory/drax-np21-cluster-re.md` |
| `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md:161-162` | `galway-1stgen-engine-map.md`, `next-galway-hubbard-work.md` |
| `docs/stage7_plan.md:193`, `:215` | `stinsen-instr-layout.md`, `wave-copy-non-idempotency.md` |
| `whats-next.md:165`, `:320` | `memory/mainstream-mon-tel.md` — named as where the **next session should start** |

**Why this outranks an ordinary dead link:** these are not "further reading". `PLAYBOOK.md:185`
lists `memory/*.md` as a standing project resource; `CLAUDE.md:197` instructs agents to write
knowledge cards and `:200` points here for the schema; `whats-next.md:320` opens the next session
with a file that cannot be opened. Each per-player doc describes its memory file as the complete
RE arc log — the deepest reasoning, deliberately kept out of the docs to keep them compact.

**This audit cannot tell you whether the content is lost or merely elsewhere** — that is a
question about this machine, not this repository. If the notes exist untracked outside the repo,
the fix is to say so in the docs. If they are gone, the references should be removed so agents
stop chasing them.

**Confidence:** HIGH that no `memory/` exists in this repo. **Deliberately no claim** about
whether the underlying notes exist anywhere.

---

### P1-5 — Three dead references in `CLAUDE.md`, the agent-facing entry point

| Line | Reference | Reality |
|---|---|---|
| `CLAUDE.md:84` | `docs/analysis/SIDWINDER_PYTHON_DESIGN.md` | at `docs/archive/analysis_2026-01-02/` |
| `CLAUDE.md:90` | `PYAUTOGUI_INTEGRATION_COMPLETE.md` | at `archive/cleanup_2026-04-28/old_docs/completion_reports/` |

(`CLAUDE.md:200`'s `memory/tdz-c64-knowledge-base.md` is covered by P1-4.)

`README.md:426` gets the first one right — it links
`docs/archive/analysis_2026-01-02/SIDWINDER_PYTHON_DESIGN.md` and labels it `(archived)`.
CLAUDE.md was not updated when the file moved.

**Confidence:** HIGH (existence checks with `find` fallback).

---

### P2-0 — `CLAUDE.md`'s player index lists 8 of 19 docs, and contradicts its own table

`CLAUDE.md:171` enumerates the per-player docs as:

```
per-player docs (`LAXITY`, `GALWAY`, `MON`, `ROMUZAK`, `FUTURECOMPOSER`, `DRIVER11`, `NP20`, `CLUSTERS`)
```

`docs/players/` holds **19** `.md` files. Omitted: `HUBBARD.md`, `HUBBARD_V2_PLAN.md`, `DMC.md`,
`SOUNDMONITOR.md`, `SDI.md`, `KIMMEL.md`, `DEENEN.md`, `PATTERNS.md`, `NATIVE_DRIVER.md`
(`PLAYBOOK.md` and `README.md` are listed separately on the same line).

**It contradicts the same file.** `CLAUDE.md`'s Known Limitations table at lines 148-155
documents Rob Hubbard, Kimmel, Deenen, Future Composer, DMC, Sound Monitor and SDI in
detail — every one of which has a dedicated player doc the index omits. The seven newest and
most active player arcs are exactly the ones an agent cannot find from the index.

`PATTERNS.md` is the most costly omission: `CLAUDE.md:198` cites "PATTERNS.md D2/D4" as binding
methodology without ever saying where the file is.

**Also stale on the same line:** `docs/reference/ACCURACY_MATRIX.md` is labelled `v3.13.0`; the
file itself reads `**Version**: 3.21.0` (`ACCURACY_MATRIX.md:4`). Same defect as P1-2.

**Confidence:** HIGH.

---

### P2-1 — CONTRIBUTING's worked example points at two paths that do not exist

`CONTRIBUTING.md` offers the Laxity driver as *the* reference implementation to copy:

| Line | Claims | Reality |
|---|---|---|
| `CONTRIBUTING.md:509` | `Driver: G5/drivers/laxity/` | `drivers/laxity/` — `G5/drivers/` holds only `sf2driver*.prg` |
| `CONTRIBUTING.md:512` | `Tests: pyscript/test_laxity_*.py` | pattern matches `pyscript/test_laxity_analyzer.py` only |
| `CONTRIBUTING.md:552` | `pyscript/test_laxity_parser.py` (38 tests) | does not exist |

`CLAUDE.md:119` repeats the first error — `G5/drivers/  # SF2 drivers (laxity, driver11, np20)`.
`README.md:737` has it right: `drivers/laxity/     # Custom Laxity driver`.

**Absence protocol applied** to both claims: loose search (`find -name 'test_laxity*'`) returns
real matches elsewhere, and `G5/drivers` exists and was listed in full — so the patterns work and
the specific targets are genuinely absent, not merely unmatched.

**Confidence:** HIGH.

---

### P2-2 — Four different live test counts; `CLAUDE.md` disagrees with itself

| Location | Claims | Literally false? |
|---|---|---|
| `README.md:25` | `**1,400+ unit tests**` | no |
| `README.md:828` | `233+ tests across 17+ test files` | no |
| `README.md:842` | `233+ tests, 100% pass rate` | no |
| `README.md:729` | `test_*.py       # 200+ unit tests` | no |
| `CLAUDE.md:5` | `200+ tests` | no |
| `CLAUDE.md:12` | ``test-all.bat` (164+ tests)` | no |
| `CLAUDE.md:44` | `test-all.bat                  # 200+ tests` | no |
| `CLAUDE.md:181` | `Run `test-all.bat` (200+ tests)` | no |

Ground truth: **1916 tests collected**. Every figure carries a `+`, so each is a floor and none
is strictly false — this is a maintenance finding, not a correctness one, and is ranked
accordingly.

What *is* a defect: `CLAUDE.md` states two different floors for the same command, 164+ at
line 12 and 200+ at line 44. Per the drift catalog, the same metric carrying different values
inside one file is a finding on its own — it demonstrates the number is unmaintained. The
useful figure (1916) appears nowhere.

Note also that `test-all.bat` runs **7 suites**, not the full collection — so no documented
command actually executes 1916 tests.

**Confidence:** HIGH.

---

### P2-3 — `scripts/test_complete_pipeline.py` fails at collection

Not a documentation defect, but it undercuts every "100% pass rate" claim above. Surfaced by the
ground-truth run:

```
scripts\test_complete_pipeline.py:20: in <module>
    from pyscript.complete_pipeline_with_validation import (
pyscript\complete_pipeline_with_validation.py:41: in <module>
    from scripts.extract_sf2_properly import extract_sf2_properly
E   ModuleNotFoundError: No module named 'scripts.extract_sf2_properly'
```

This is a live file outside `archive/`. The other 7 collection errors are all under `archive/`
and are expected.

**Confidence:** HIGH.

---

### P2-4 — Stale magnitude metrics in the Statistics section

| Location | Claims | Actual |
|---|---|---|
| `README.md:827` | `**Python Files**: ~37 active scripts` | **527** `.py` |
| `README.md:829` | `**Documentation**: 52+ markdown files` | **192** live `.md` |
| `README.md:739` | `docs/               # Documentation (50+ files)` | **245** under `docs/` |

`~37` carries no `+` — it is an approximation, and it is off by more than an order of magnitude.
The two `+` figures are floors and remain technically true.

**Confidence:** HIGH.

---

### P2-5 — Missing LICENSE on a public repo that promises MIT

`README.md:1088`: `MIT License - See [LICENSE](LICENSE) for details.`
`scripts/autoit/README.md:248`: `Part of SIDM2 project. See project LICENSE file.`

`ls LICENSE LICENSE.md LICENSE.txt` → absent. The repo is PUBLIC (`gh repo view` →
`"visibility":"PUBLIC"`), so the link renders as a 404 on GitHub and anyone wanting to reuse
the code has a stated licence with no text behind it.

**Confidence:** HIGH.

---

### P2-6 — Dead or misdirected links across Tier 1/2 docs

Each verified individually with `find` fallback (bare filenames in docs are often relative, so a
root-relative miss alone is not evidence).

| Location | Reference | Reality |
|---|---|---|
| `README.md:369` | `CONVERSION_POLICY_APPROVED.md` | `docs/integration/CONVERSION_POLICY_APPROVED.md` |
| `README.md:492` | `PYAUTOGUI_INTEGRATION_COMPLETE.md` | archived |
| `docs/ARCHITECTURE.md:1078` | `PIPELINE_EXECUTION_REPORT.md` | **MISSING everywhere** |
| `docs/guides/HTML_ANNOTATION_TOOL.md:602` | `../analysis/SIDWINDER_PYTHON_DESIGN.md` | `docs/archive/analysis_2026-01-02/` |
| `docs/guides/HTML_ANNOTATION_TOOL.md:603` | `../implementation/PLAYER_DETECTION.md` | **MISSING everywhere** |
| `docs/guides/HTML_ANNOTATION_TOOL.md:604` | `../reference/LAXITY_FORMAT.md` | **MISSING everywhere** |
| `tools/sf2pack/README.md:220` | `docs/VALIDATION_WORKFLOW.md` | **MISSING everywhere** |
| `tools/sf2pack/README.md:221` | `docs/SF2_TO_SID_LIMITATIONS.md` | `docs/reference/` |
| `tools/sf2export/README.md:208` | `docs/SF2_FORMAT_SPEC.md` | `docs/reference/` |
| `scripts/autoit/README.md:235` | `docs/analysis/GUI_AUTOMATION_COMPREHENSIVE_ANALYSIS.md` | **MISSING everywhere** |

Five resolve to a moved location (reader finds them); five do not exist anywhere.

**Confidence:** HIGH.

---

### P3-1 — Duplicated truth: the root cause behind P1-2 and P2-2

The version number is maintained by hand in **six live documentation locations** plus
`sidm2/__init__.py`. Four have drifted. The accuracy figure `99.93` appears in **15+ live
markdown files** (`CLAUDE.md`, `README.md`, `CONTEXT.md`, `CONTRIBUTING.md`,
`docs/ARCHITECTURE.md`, `docs/CHEATSHEET.md`, `docs/COMPONENTS_REFERENCE.md`,
`docs/guides/{FAQ,GETTING_STARTED,BEST_PRACTICES,DRIVER_SELECTION_GUIDE,BATCH_REPORTS_GUIDE}.md`,
`docs/analysis/{DRIVER_LIMITATIONS,CONVERSION_MASTERY_ANALYSIS}.md`,
`docs/implementation/SID_TO_SF2_REFACTORING_SUMMARY.md`). These currently agree.

**Canonical sources to keep:** `sidm2/__init__.py:7` for the version;
`docs/reference/ACCURACY_MATRIX.md` for accuracy — a role it already claims and, uniquely among
the docs checked, keeps current (it self-reports 3.21.0). Everything else should link rather
than restate.

The project already has the machinery: `CLAUDE.md:183` documents
`py -3 pyscript/gen_sf2_index.py` regenerating `docs/SF2.md` between GENERATED markers. The same
pattern would fit the version stamp.

**Confidence:** HIGH on the duplication; the current agreement of the `99.93` copies means this
is fragility, not error.

---

### P3-2 — README carries 17 version-history entries duplicating an 8,968-line CHANGELOG

`README.md` is **1096 lines**; `README.md:851-1019` is a Version History section with 17
`### vX.Y.Z` headings, ending at `README.md:1019` with
`**Complete changelog**: [CHANGELOG.md](CHANGELOG.md)` — which is 8968 lines and canonical.

**A correction to the record:** this was previously assumed to violate the project's own rule at
`CLAUDE.md:206-208`. Reading it precisely, it does not — "This file stays compact — do not add
per-version entries **here**" scopes to `CLAUDE.md`. No existing rule forbids the README
duplication. It is reported on its own merits only.

**Confidence:** HIGH on the measurement.

---

### P3-3 — Two small counting errors in `docs/ARCHITECTURE.md`

| Location | Claims | Actual |
|---|---|---|
| `docs/ARCHITECTURE.md:1021` | `**Availability Flags** (12 total):` then lists 12 | **13** — omits `ASM_ANNOTATION_AVAILABLE` |
| `docs/ARCHITECTURE.md:1035` | `All 7 functions + all 12 availability flags` | 7 functions ✅, 13 flags |
| `docs/ARCHITECTURE.md:1058` | `scripts/sid_to_sf2.py ... (802 lines)` | **874** |
| `CONTRIBUTING.md:467` | `docs/ARCHITECTURE.md (834 lines)` | **1079** |

The flag count was verified by extracting unique names, not by counting matching lines — a naive
`rg -c '_AVAILABLE\s*='` returns 26 because each flag is assigned twice (try/except ImportError),
which would have produced a bogus "26 vs 12" finding. The `__all__` breakdown was parsed with
`ast`: 7 functions + 13 flags = 20 entries.

**Confidence:** HIGH.

---

## Unverifiable — reported, not adjudicated

**Every accuracy and fidelity percentage in this project.** Verifying figures like 99.93%,
88–96%, "100% byte-exact", the SDI medians, or Sound Monitor's 99.23% would require running the
converter and the trace toolchain — long-running commands with side effects, which this audit
must not execute.

This is the correct outcome rather than a gap, because **the project ships its own verification
agent**: `.claude/agents/sidm2-fidelity-falsify.md`. `docs/reference/ACCURACY_MATRIX.md:11-14`
records that Sound Monitor and SDI were already put through an adversarial audit by it, and that
*no percentage was wrong* — what was wrong was surrounding framing. Re-adjudicating those numbers
with weaker tools would duplicate that work and risk contradicting it from a position of less
knowledge. Route all such claims there.

**The player docs are dense with unverifiable claims by nature** — several hundred 6502
addresses (`$16CC-$1702`, `$E943`, `$1900/$1980`), register-level fidelity medians, and n-counts
like `n≈841k`. Confirming any of them requires disassembly or a trace run. Their file paths and
counts were checked and are in good shape; their numbers were not adjudicated.

Two of them pre-emptively disclose their own weakness, which is the behaviour to encourage:
`SOUNDMONITOR.md:49-50` states its sweep scripts are "untracked + gitignored" and that
"**no tracked test asserts any Sound Monitor fidelity number** — it is not regression-locked";
`SOUNDMONITOR.md:44` records that a claim which propagated CHANGELOG → CLAUDE.md → accuracy
matrix "was wrong; corrected 2026-07-16". A project that catches and documents its own doc
drift is doing this audit's job for it.

Also unverified: throughput figures (`111,862 events/second`, `8.1 files/second`,
`3.1x speedup`), all timing figures in `scripts/autoit/README.md`, and the coverage figures at
`docs/ARCHITECTURE.md:1037-1042` (65.89%, 299/445, 90/112) — reproducing them needs a coverage
run this audit did not perform. They are stale-looking, but "looks stale" is not evidence.

---

## Checked and found clean

Reported so coverage can be judged, not only failures.

| Check | Result |
|---|---|
| Secrets scan (tracked + untracked text files) | **clean** — no matches. See blind spots above. |
| `.env` present / committed | none exists |
| Critical Rule "No .py in root" (`CLAUDE.md:11`) | **holding** — `ls *.py` empty |
| CI workflow count (`CLAUDE.md:5` "5 workflows") | **correct** — 5 files in `.github/workflows/` |
| All 7 suites invoked by `test-all.bat` | **all exist** |
| 15 `.bat` launchers named in `CLAUDE.md` Quick Commands | **all exist** |
| `tools/` executables named at `README.md:783-787` | **all 5 present** |
| ~29 doc paths named in `CLAUDE.md` | 26 OK, 3 dead (P1-4) |
| ~27 script/asset paths in `CLAUDE.md` | 26 OK, 1 dead (P0-1) |
| 26 paths in README Documentation/References tables | **all resolve** |
| "6 specialized error classes" (`CONTRIBUTING.md:222`) | **correct** — the 6 named subclasses exist in `sidm2/errors.py` (plus `Colors` helper and `SIDMError` base) |
| `__all__` function count (`docs/ARCHITECTURE.md:1035`) | **correct** — exactly 7 |
| `requirements.txt` (`README.md:513`) | exists |
| `mcp-siddump/` server + requirements | both exist |
| `sf2pack.exe`, `sf2export.exe`, `sf2_loader.exe`, `sf2_loader.au3` | **all present** |
| `SID/stinsen_sid_trace_300frames.csv` ground truth | exists |
| `docs/reference/ACCURACY_MATRIX.md` version stamp | **current** (3.21.0) |
| `tools/sidm2_sid_trace.zig` in-repo source-of-truth claim | **correct** — file present |
| "658+ SID files" (`CLAUDE.md:5`, `README.md:26`) | floor holds — 1361 actual |
| `docs/players/` file count | **19**, exactly as `CLAUDE.md:171` implies |
| `whats-next.md` at repo root (`PLAYBOOK.md:184`) | exists |
| Cross-links between the 19 player docs | **all resolve** — no dead `[X.md](X.md)` among them |

---

## Explicitly not findings

Per the skill's not-findings rules, these were examined and deliberately **not** reported:

- **`CLAUDE.md`'s Known Limitations table (lines 138-159) is exemplary.** Entries like
  "**pulse 100% is CAPTURED, not modelled**", "a **mode count, NOT accuracy** (an eligible file
  can still score 39%)", "**Every % is window-dependent** — quote the window", "headline comes
  from **untracked** scratch, no tracked test — not reproducible from a fresh clone", and
  "the old 'filter 100%' was `0==0`" are the standard other projects should be held to. Three
  of them pre-emptively disclose exactly the class of defect this audit hunts. This table is why
  the findings list above is short.
- **`README.md:807-819` Known Limitations** — accurate and current.
- **Files under `archive/`** are not missing. Only live documents *pointing at them as current*
  are findings (P0-1, P0-3, P1-4).
- **`docs/ROADMAP.md` and open TODOs** — plans, not drift.
- **Machine-specific paths** (`C:\Users\mit\Downloads\zig64\...` at `CLAUDE.md:98`,
  `README.md:448`) — normally P3 and escalated only for projects inviting outside contribution.
  Noted rather than filed: `CLAUDE.md:98` is explicit that `tools/sidm2_sid_trace.zig` in-repo is
  the source of truth and that the zig64 copy goes stale, so the absolute path is a documented
  rebuild recipe, not a dependency. `README.md:448` is weaker — it names only the external path,
  omitting the in-repo one — but is a single line and not load-bearing.

---

## Recommended order of work

1. **P0-1** — one decision resolves six references plus a 626-line guide: restore
   `generate_stinsen_html.py` from archive, or delete the references and the guide.
2. **P0-2** — replace `python -m unittest test_converter -v` with `python -m pytest` in five
   places in `CONTRIBUTING.md`.
3. **P1-4** — decide what happened to `memory/`. This is a judgment call only you can make, and
   it blocks the next session (`whats-next.md:320`). Everything else here is mechanical.
4. **P0-3, P1-5** — four dead references; mechanical.
5. **P1-1** — delete the four-line filter FAQ entry at `README.md:1036-1037`.
6. **P1-2 + P3-1** — fix the four stale version stamps, then make `sidm2/__init__.py` the single
   source and have the docs link rather than restate.
7. **P1-3** — replace `tools/README.md` with SIDM2's own description of the directory.
8. **P2-0** — regenerate the player index at `CLAUDE.md:171` from `ls docs/players/`.

The remaining findings are maintenance and can be batched.
