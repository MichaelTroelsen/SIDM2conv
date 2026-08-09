# Audio Listening Tool: Implementation Plans for Suggestions 1-5

Companion to `docs/AUDIO_LISTENING_CAPABILITY_ASSESSMENT.md`, which listed six improvement
suggestions for `sidm2/audio_listen.py`/`sidm2/audio_tightness.py`. Suggestion 6 ("keep the
human checkpoint") is organizational, not code -- this covers the five that are. Each plan
below is grounded in the current source (`sidm2/audio_tightness.py`, `sidm2/audio_listen.py`
as of this writing) with concrete function signatures, file targets, and a test plan, so
implementation can start directly from this doc.

## 1. Mel-scale band spacing

**Goal**: `band_energies()`'s bin edges are `np.linspace(fmin, fmax, nb+1)` -- linear Hz
spacing, so half the bins (by count) sit above 4 kHz, a region SID material rarely
dominates. Mel spacing reallocates resolution toward where both SID material and human
hearing concentrate.

**Approach**: No new dependency needed -- the mel formula is closed-form:
```python
def hz_to_mel(f): return 2595.0 * np.log10(1.0 + f / 700.0)
def mel_to_hz(m): return 700.0 * (10.0 ** (m / 2595.0) - 1.0)
```
Add a `scale: str = 'linear'` parameter to `band_energies()` (`sidm2/audio_tightness.py:87`)
and `_logmel()` (`:247`). When `scale='mel'`, compute `edges` by taking `nb+1` linearly-spaced
points in mel space via `hz_to_mel`/`mel_to_hz`, then use them exactly as the existing linear
edges are used now (the `bin_idx` binning logic is unchanged).

**Backward compatibility is the load-bearing constraint here.** `detect_onsets()` (used by
the onset-timing comparison that most of this project's fidelity numbers depend on) calls
`band_energies()` with the current linear defaults. Changing the *default* would silently
shift onset-detection statistics project-wide with no corpus re-validation. Plan: keep
`scale='linear'` as the default everywhere; wire `scale='mel'` as an explicit opt-in on
`sidm2/audio_listen.py::extract_features()` only (the brightness/rolloff/flatness features
this is actually meant to help), via a new `band_scale: str = 'linear'` parameter threaded
through to its internal `band_energies()` call. Flip the default only after a corpus
comparison shows mel-scale centroid/rolloff numbers correlate better with known cases (ties
into plan 3).

**Files**: `sidm2/audio_tightness.py` (`band_energies`, `_logmel`), `sidm2/audio_listen.py`
(`extract_features`, and the `_db_bands`/spectrogram path if mel spectrograms are wanted too
-- separate opt-in, not required for the feature-report use case).

**Test plan**: `pyscript/test_audio_tightness.py` -- mel edges are monotonic, first/last
edge equal `fmin`/`fmax`, and bin *width* increases with frequency (the actual point of mel
spacing). `pyscript/test_audio_listen.py` -- re-run `TestExtractFeaturesTone`'s low-vs-high
centroid ordering test with `band_scale='mel'` and confirm it still holds; add a case
checking two tones close in Hz but far apart perceptually (e.g. 100 Hz vs 200 Hz, one octave)
get more separated centroid bins under mel than linear scaling.

**Effort**: S (~2-3h). **Risk**: low, given the opt-in-only default policy above.

## 2. A-weighting / perceptual loudness

**Goal**: `rms_db_mean`/`rms_db_max` are raw unweighted dBFS. A-weighting (IEC 61672) is the
standard approximation of frequency-dependent loudness perception and is also closed-form --
no external curve table needed.

**Approach**: Add the standard A-weighting formula as a helper in `sidm2/audio_listen.py`:
```python
def a_weight_db(f):
    f2 = f ** 2
    ra = (12194.0**2 * f2**2) / (
        (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2))
    return 20 * np.log10(ra) + 2.0   # +2.0 dB normalizes A(1000 Hz) to 0 dB
```
Apply it as a per-band gain on the *already-computed* `band_energies()` matrix inside
`extract_features()` (`sidm2/audio_listen.py:73`) rather than re-deriving a separate
time-domain path: `weighted = bands * (10 ** (a_weight_db(centers) / 10))`, then derive a
perceptual level estimate from `weighted.sum(axis=1)` the same way `rms_db_mean` currently
derives from the raw time-domain `_frame_rms()`. Add as **new** `AudioFeatures` fields
(`rms_dba_mean`, `rms_dba_max`) alongside the existing unweighted ones -- additive, not a
replacement, since the raw dBFS numbers remain useful for exact level-matching checks (e.g.
confirming a driver's master volume nibble is set correctly).

**Files**: `sidm2/audio_listen.py` -- new `a_weight_db()`, two new `AudioFeatures` fields,
one new row in `format_feature_report()`.

**Test plan**: A 1 kHz tone should have `rms_dba_mean` within ~0.5 dB of `rms_db_mean` (A(1kHz)
is defined as 0 dB). A 60 Hz tone at the same amplitude should read meaningfully lower on
`rms_dba_mean` than `rms_db_mean` (A(60Hz) is roughly -26 dB) -- this is the actual behavior
under test, not just "the field exists".

**Effort**: S (~2h). **Risk**: low -- purely additive, no existing field changes.

## 3. Calibration pass anchored on Blackbird B13

**Goal**: none of the current thresholds (loose-jitter ms, "brighter" centroid delta, etc.)
are validated against a real human verdict. The project has exactly one documented case:
Blackbird's B13 entry (register-exact, but a human listening pass caught "something with the
perc or drums" -- see `docs/players/BLACKBIRD.md` and `CLAUDE.md`'s
`docs/guides/AUDIO_TIGHTNESS_GUIDE.md` reference, which is what motivated
`sidm2/audio_tightness.py` in the first place).

**Approach**: This is the one plan whose first step is investigation, not code -- the exact
B13 file pair (which Blackbird tune, which build) needs to be re-identified from
`docs/players/BLACKBIRD.md`'s history before a regression test can point at it. Once located:

1. Render/cache the original `.sid` and the flagged Stage-B build's `.sf2`/`.sid` as fixture
   WAVs (or keep them regenerable from source `.sid`+build script rather than committing
   audio, matching this project's existing pattern of regenerating fixtures rather than
   storing binaries).
2. Run the existing `analyze_tightness_files()` + `extract_features()` pipeline on that pair.
3. Add `pyscript/test_audio_listen_calibration.py` asserting the pipeline flags *something*
   on this known-bad pair (e.g. a specific voice's onset match rate below X%, or a jitter p95
   above the tool's own `--loose-threshold-ms`) -- a "does it flag" assertion, not a pinned
   exact number, mirroring the rank-test style `measure_repeatability_floor()`
   (`pyscript/audio_tightness_tool.py`) already uses elsewhere in this codebase.
4. Structure it as a small, appendable manifest (e.g. `calibration_cases.json`: file pair +
   known human verdict + which metric is expected to flag it) rather than one-off test
   functions, so a *second* known-bad case (there will eventually be one) doesn't require
   new test-writing, just a new manifest entry.

**Files**: new `pyscript/test_audio_listen_calibration.py`, new `calibration_cases.json` (or
similar) manifest, cross-reference in `docs/players/BLACKBIRD.md`.

**Test plan**: is itself the deliverable.

**Effort**: M (~1 day) -- dominated by locating/regenerating the exact B13 artifacts, not the
test code. **Risk**: medium and worth flagging explicitly -- it's possible current tooling
(even with plans 1/2 applied) still does NOT flag B13, since the original defect was
subjective ("something with the perc or drums") and may not correspond to any metric this
tooling computes. That outcome is itself a valid, useful result (it would mean gap #3 needs a
new feature, not just calibration of existing ones) -- don't treat "the test currently fails
to flag it" as a reason to abandon the plan; that's the information this plan exists to
surface.

## 4. Section-aware / windowed features

**Goal**: every `audio_listen.py` number today is a whole-file mean (`extract_features()`
returns one `AudioFeatures` for the entire duration). A defect confined to one 2-second bridge
section reports as a small, easily-missed average delta.

**Approach**: Add `extract_features_windowed()` to `sidm2/audio_listen.py`:
```python
def extract_features_windowed(x, sr, window_s=5.0, hop_s=None, **kwargs):
    """Returns [(window_start_s, AudioFeatures), ...] -- extract_features() applied to
    each window instead of the whole file. hop_s=None means non-overlapping windows
    (hop_s == window_s)."""
```
Internally: slice `x` into `[i*hop : i*hop+win]` sample ranges and call the existing
`extract_features()` per slice -- no change to `extract_features()` itself, this is a thin
wrapper. Add `format_windowed_diff_report(orig_windows, driver_windows, ...)` that computes
the same per-metric deltas `format_feature_report()` already computes, but per window, and
explicitly calls out the single worst window (largest `|delta|` on any tracked metric) at the
top of the report -- directly the "flag the window with the largest deviation" ask, rather
than dumping every window's full table (which would just recreate the "too much to scan"
problem windowing is meant to fix). Wire into `pyscript/audio_tightness_tool.py` as a new
opt-in `--windowed [SECONDS]` flag alongside the existing `--no-listen`/`--spectrogram`.

**Files**: `sidm2/audio_listen.py` (`extract_features_windowed`,
`format_windowed_diff_report`), `pyscript/audio_tightness_tool.py` (CLI wiring).

**Test plan**: construct a synthetic signal that's a clean 440 Hz tone for the first half and
440 Hz mixed with white noise for the second half; `extract_features_windowed` should report
the second window with materially higher `flatness_mean`, and
`format_windowed_diff_report`'s "worst window" call-out should point at it, not the first.

**Effort**: S-M (~3-4h) -- mechanically small since it reuses `extract_features()` entirely;
most of the effort is the diff-report formatting.

**Risk**: low.

## 5. Basic pitch/chroma summary

**Goal**: nothing currently says *why* brightness shifted. A 12-bin pitch-class histogram
lets the report say "brighter, and energy shifted toward C/C#" instead of only "brighter."

**Approach**: This one does NOT reuse `band_energies()`'s output directly -- `band_energies()`
groups FFT bins into `nb` wide linear/mel bands *before* any pitch computation, which
destroys the per-bin frequency precision chroma needs (two adjacent semitones can fall in the
same wide band). It needs a new lower-level function operating on raw FFT magnitude bins,
mirroring `band_energies()`'s STFT setup but mapping bins to pitch class instead:
```python
def chroma_vector(x, sr, hop_s=0.1, win_s=0.2, fmin=65.4, fmax=2093.0) -> np.ndarray:
    """12-bin pitch-class histogram (energy-weighted), normalized to sum 1.
    fmin/fmax default to C2/C7 -- SID's practical pitch range."""
```
Per frame: `np.fft.rfft`, for each FFT bin with frequency `f` in `[fmin, fmax]`, compute pitch
class `pc = int(round(12 * log2(f / f_ref))) % 12` (f_ref = a fixed reference, e.g. C0 =
16.35 Hz, so semitone-rounding lands on standard note names), accumulate `|magnitude|**2`
into `hist[pc]`. Sum across frames, normalize. Add `chroma: np.ndarray` (shape `(12,)`) to
`AudioFeatures`, wire into `extract_features()`, and add
`chroma_shift_description(orig_chroma, driver_chroma) -> str` naming the pitch class(es) with
the largest signed change (e.g. `"energy shifted toward C/C# (+0.08), away from G (-0.06)"`),
called from `format_feature_report()`.

**A real accuracy risk to flag up front**: SID bass notes sit around 50-100 Hz, needing a
window long enough to resolve that pitch cleanly (roughly 50-100ms+ for stable low-note
chroma) -- much longer than the 10-40ms windows tuned for onset *timing* elsewhere in this
codebase. `chroma_vector()` needs its own window/hop defaults (shown above, `win_s=0.2`) and
should not share `extract_features()`'s `win_ms=40` default; a short window will smear or
misassign low SID notes into the wrong pitch class.

**Files**: `sidm2/audio_listen.py` -- new `chroma_vector()`, `chroma_shift_description()`,
`AudioFeatures.chroma` field, one new line in `format_feature_report()`.

**Test plan**: a pure 440 Hz (A4) tone's `chroma_vector()` should peak at the 'A' bin; a
466.16 Hz (A#4, one semitone up) tone should peak at the adjacent bin, not the same one;
`chroma_shift_description()` comparing the two should name "A" losing energy and "A#/Bb"
gaining it. Include a low-frequency case (e.g. 55 Hz, A1) to confirm the wider default window
still resolves bass correctly -- this is the case most likely to break if the window-length
risk above isn't handled.

**Effort**: M (~4-5h) -- the pitch-class-to-Hz mapping and octave-folding are straightforward,
but getting the window length right for SID's bass range needs real verification, not just
unit tests on a mid-range tone.

**Risk**: medium -- the window-length tradeoff above is a genuine design constraint, not a
detail to gloss over during implementation.

## Suggested order

1 and 2 are independent, additive, low-risk, and unlock 4 and 5 needing less rework if done
first (4 wraps `extract_features()` as-is; 5 is fully independent of 1/2 but benefits from the
same corpus-validation step 1 already needs). Do 3 in parallel -- it's investigation-bound, not
code-bound, and its outcome (does *any* current or planned metric actually flag B13) should
inform whether 1/2/4/5 are prioritized correctly before more feature work is added blind.
