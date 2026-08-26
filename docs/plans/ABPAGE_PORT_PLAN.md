# Plan: port h2g's `abpage.py` as a SIDM2 A/B listening tool

**Status**: planned, not started. Queued in `.claude/tasks/whattask.json` as
`port-h2g-abpage-listening-rig` (model: opus).
**Origin**: `docs/H2G_FIDELITY_APP_ANALYSIS.md` §4 (read it first — it is the
survey this plan executes on). Source: `C:\Users\mit\claude\h2g\python\abpage.py`
(2,663 lines, stdlib-only Python + one inline CSS/JS page template).

## What is being built

`pyscript/abpage.py` + `ab-listen.bat`: build one self-contained HTML page per
original/converted pair that plays BOTH renders in lock-step and swaps which
one is audible — gapless, position-matched switching — with blind-test scoring,
a sync-offset control, amplitude-envelope overlays (whole-song + per-voice),
and a precomputed dual spectrogram. The gap it closes: every accuracy % in
CLAUDE.md's Known Limitations table is a claim about whether a build *sounds*
right, and SIDM2 has no rig for a human to blind-test that claim by ear.

## Architecture decisions (already made — do not re-litigate)

1. **Reuse `pyscript/audio_tightness_tool.py`'s staging, do not write new
   staging.** Its `resolve_input()` already accepts `.sid`/`.sf2`/`.wav` on
   either side (SF2 → SID via `scripts/sf2_to_sid.convert_sf2_to_sid`, then
   render via `choose_renderer`/`_render` → vsid or sidplayfp), and
   `_render_muted()` produces per-voice stems. abpage's job starts at "two WAVs
   exist"; a `stage` subcommand that calls into audio_tightness_tool's
   functions is the whole staging story. Caveat carried from CLAUDE.md: voice
   muting is NOT clean isolation on every tune — keep the per-voice strips
   optional and labelled, exactly as h2g keeps them optional.
2. **Naming convention**: `build/listen/<name>.original.wav` +
   `<name>.sidm2.wav` (+ `<name>.v{1,2,3}.{original,sidm2}.wav` when staged).
   Keep h2g's `build/listen/` layout so the page/serve machinery ports with
   minimal diff; just rename the `.h2g.` infix.
3. **Keep the stdlib FFT.** SIDM2 allows numpy, but h2g's cached-twiddle
   radix-2 implementation is already written, tested upstream, and fast enough
   (~3.4 s/tune build). Porting it verbatim is less risk than rewriting
   against numpy. (A later numpy swap is trivial if build time ever matters.)
4. **The report-quoting layer is REPLACED, not ported.** h2g's readers
   (`fidelity_rows`/`survey_rows`/`preset_rows`/`fidelity_json_rows`/
   `instrmap_rows`/`listening_notes`) read h2g's own report formats and must
   not be ported. v1 of the SIDM2 page quotes at most: (a) an optional
   `--notes FILE.md` of per-tune bullets, and (b) an optional chips row read
   from a JSON file the user points at (`--chips FILE.json`, flat
   `{name: {label: value}}`). Do NOT scrape `audio-tightness.bat` text output
   — h2g's own docstrings warn that Markdown-table scrapers degrade silently;
   if tighter integration is wanted later, that is a follow-up task after
   `audio_tightness_tool` grows a `--json` mode.
5. **Cards that do NOT transfer** (h2g-specific, drop them):
   `tracker_card`/`row_schedule` (GoatTracker .sng row grid), `facts_card`
   (SURVEY/presets), `notes_strip_card` (fidelity.json per-voice attacks),
   `instrmap_card` + `run_instrmap` (h2g's instrmap.py; SIDM2's own
   `instrument-map.bat` is a different tool — integration is out of scope,
   see H2G_FIDELITY_APP_ANALYSIS §5).
   **Cards/machinery that DO transfer near-verbatim**: the transport +
   blind-test + sync rig (SCRIPT), envelope overlay + |difference| strip,
   per-voice strips, spectrogram (`_fft` through `spectrogram_card`), CSS,
   `page()`/`index()`/`prune_stale_pages()`, `--embed`, `--serve` +
   `_RangeHandler` (Range-honouring static server — the stock one breaks
   audio seeking), `write_launcher`, `wav_rendered` provenance stamps.
6. **Placement rules**: the tool is `pyscript/abpage.py` (Critical Rule 1: no
   .py in root), launcher `ab-listen.bat` beside the other .bat launchers,
   output under `build/listen/` (gitignored — verify, add if not).

## Steps

1. **Stage subcommand** — `python pyscript/abpage.py stage ORIG CONV
   [--voices] [-t SECONDS]`: resolve both inputs through
   audio_tightness_tool's `resolve_input`, write the named WAV pair (+ stems
   with `--voices`) into `build/listen/`. Reuses `choose_renderer`; respects
   its vsid→sidplayfp fallback.
2. **Port the page builder** — copy abpage.py, delete the non-transferring
   readers/cards (decision 5), rename the `.h2g.` infix and all "H2G" strings
   in the template to SIDM2, wire decision 4's `--notes`/`--chips` inputs.
   Keep `_doc`'s ROOT-resolved-per-call pattern (its docstring records the
   test bug that motivates it).
3. **Port `--serve`, `--embed`, launcher, index, prune** — near-verbatim.
   `--embed` ceiling note (~14 MB/min mono) stays in the help text.
4. **Tests** — `pyscript/test_abpage.py`. Port the shape of h2g's abpage
   tests if present (`C:\Users\mit\claude\h2g\python\test_*abpage*`); at
   minimum: `_read_wav_mono` on good/truncated/wrong-width WAVs,
   `_spectrogram_grid` shape + shared-peak scaling on synthetic tones,
   name-globbing excludes `.v[123]` stems, page() with no chips/notes renders
   the honest-gap strings not an empty rail, prune only removes pages for
   unstaged tunes, `_RangeHandler` serves a correct 206 slice. Use tmp_path +
   monkeypatched ROOT (the exact pattern `_doc`'s docstring demands).
5. **End-to-end verification (mandatory, not optional)** — stage one real
   pair (e.g. a Laxity tune: `SID/...sid` + its `SF2/....sf2`), build, serve,
   and verify the served page actually renders: load it in a real browser
   (claude-in-chrome; Playwright MCP is not connected on this machine — see
   memory `artifact-verification`) and confirm (a) audio plays and switches,
   (b) the envelope canvas drew (it needs http, not file://), (c) blind mode
   randomizes and tallies. A page that "builds" but never rendered is not
   done — that rule is global CLAUDE.md policy.
6. **Docs** — add the tool to CLAUDE.md Quick Commands (one line),
   README.md, `docs/TOOLS_REFERENCE.md`; run `update-inventory.bat` (new
   files added). No version bump unless shipped with other changes; if
   bumped, follow the full On Version Bump checklist.

## Explicitly out of scope (follow-ups, not this task)

- `--json` mode for `audio_tightness_tool` + chips wired to it.
- Any port of h2g's `instrmap.py` (SIDM2's `instrument_map.py` already covers
  it — H2G_FIDELITY_APP_ANALYSIS §5).
- Wiring into `sid-to-sf2.bat`/`DriverSelector` or CI.

## Verify (the task's acceptance test)

`pyscript/test_abpage.py` passes under `python -m pytest`; the step-5 browser
check is performed and its three observations reported with the result;
`cleanup.bat --scan` stays clean (no root .py, no stray output).
