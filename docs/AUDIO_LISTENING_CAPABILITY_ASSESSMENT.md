# Audio Listening Tool: Capability Assessment & Improvement Suggestions

**Scope**: `sidm2/audio_listen.py` (feature report + spectrogram) and its onset-timing
sibling `sidm2/audio_tightness.py`, as exposed through `pyscript/audio_tightness_tool.py`.

## Short answer

**No — this does not mean a human no longer needs to listen.** What exists is a
translation layer: audio -> numbers and a 2D image, in a form Claude (a text+vision
model with no audio-perception channel at all) can read. That is a fundamentally
different thing from hearing. It closes the loop for the class of defects that show up
as a measurable timing or spectral-shape delta, and for those it is a genuine
improvement — before this tool, a discrepancy invisible to register-exact comparison was
invisible to Claude, period. It does not close the loop for anything that requires
recognizing *what something sounds like*, only for things that show up as *how two
signals differ numerically*. Those are not the same set of defects.

## What the tool actually does today (grounded in the source)

- `sidm2/audio_tightness.py`: onset detection via spectral flux over **linear-Hz**
  bands (`band_energies()`, `edges = np.linspace(fmin, fmax, nb+1)` — not log/mel/Bark
  spaced), greedy nearest-neighbor onset alignment, attack-rise-time (10%-90% RMS
  envelope), a crude `logmel_distance` (misleadingly named — it's linear energy in
  log-Hz-spaced bands over a fixed 200-5000 Hz range, not a true mel scale).
- `sidm2/audio_listen.py`: whole-file averages over the same linear band-energy matrix —
  RMS in dBFS (unweighted, no A-weighting/LUFS), spectral centroid, 85%-rolloff,
  zero-crossing rate, spectral flatness (geometric/arithmetic mean ratio). All are
  **global means**, explicitly not localized to a moment in the song.
- Spectrogram: a hand-rolled 8-stop linear-interpolation colormap (`_INFERNO_STOPS`),
  fixed -80..0 dB range, `nb=96` linear frequency bins, resized to a max 1400px width —
  a coarse visualization tuned for "does something look different here", not for
  fine-grained inspection.
- Everything downmixes to mono at the input stage (`load_wav_mono`, `x.reshape(-1,
  ch).mean(axis=1)`) — stereo/panning information is discarded before any feature is
  computed.

This is an honest, working proxy for "does the audio look/measure different" — not a
model of "does it sound different to a person," and the two diverge in specific,
identifiable ways below.

## Gaps against human listening, by category

### 1. No perceptual weighting (the biggest, cheapest-to-fix gap)
Every level number is raw RMS in dBFS. Human loudness perception is frequency-dependent
(equal-loudness contours) and human frequency *resolution* is roughly logarithmic
(mel/Bark), not linear. A 2 dB difference concentrated at 8 kHz reads identically to a
2 dB difference at 200 Hz in `rms_db_mean`, but a human ear treats them very differently
— the mid-band is where hearing is most sensitive and where a small SID pulse-width or
filter-cutoff error is most audible. **`band_energies()`'s linear spacing means half the
frequency bins (by count) sit above 4 kHz, a region SID chiptune material rarely
dominates — bins are being spent where the ear cares least.**

### 2. No holistic/musical judgment
The tool cannot answer "does this sound *right*" or "is this in tune" or "does the
envelope feel natural" — only "is signal A's number bigger than signal B's number." The
project's own motivating case for `audio_tightness.py` (Blackbird's B13 entry,
"something with the perc or drums") was originally a human catching a problem no metric
flagged. This class of finding — a real defect that doesn't show up as an onset-timing
or spectral-centroid delta — is exactly what current tooling cannot surface, by
construction: it can only report what it was told to measure.

### 3. No harmonic/pitch-content analysis
There is no chroma vector, no pitch-class histogram, no fundamental-frequency tracking
in `audio_listen.py`. A driver that plays the right notes at the wrong octave, or with
a slightly detuned oscillator, would move the spectral centroid but the report gives no
way to say *why* — a human listener identifies "that note is wrong" in under a second;
this tooling would show a centroid delta and nothing else.

### 4. No temporal/structural awareness
Every `audio_listen.py` number is a whole-file mean. A driver that is perfect for 90% of
a song and badly wrong for one 2-second bridge section reports as a small, easily-missed
average delta — a human listening through the file notices the bridge immediately.
`audio_tightness.py`'s onset list is per-event, which is better, but still has no notion
of song *sections* or arrangement.

### 5. No calibration against real listening
None of the thresholds anywhere in this tooling (what counts as "loose" jitter, what
centroid delta is "brighter," what flatness delta means "more noise-like") were derived
from an actual listening test. They are reasonable-sounding defaults, not validated ones.
The project has exactly one documented case where a human's verdict is on record
(Blackbird B13) — that is one data point, not a calibration set.

### 6. Structurally: no audio perception exists at all
This is the fact under all the others. Claude has no audio input modality. Every
"listening" capability here is Claude reading numbers and looking at a false-colored PNG
of a spectrogram — an image is a channel Claude *can* process, but a spectrogram image
is already a lossy, heavily-processed derivative of the sound (magnitude only, no phase,
banded, log-compressed, palette-quantized). No feature-engineering effort changes that
this is fundamentally analysis-of-a-derivative, not perception-of-the-signal.

## Improvement suggestions, roughly in cost/benefit order

1. **Mel or Bark-scale band spacing** in `band_energies()` (or a new function reusing its
   STFT) instead of `np.linspace`. Cheapest fix here and the one most likely to make
   centroid/rolloff/flatness numbers track what a human would actually notice, since it
   reallocates resolution toward where SID chiptune material and human hearing both
   concentrate.
2. **A-weighting or a simple loudness curve** applied before computing `rms_db_mean` —
   turns "louder in dBFS" into "louder as perceived," a small filter-coefficient change
   with an outsized effect on how trustworthy the level numbers are.
3. **A calibration pass against known cases.** Blackbird B13 (register-exact, audibly
   wrong) and any future case where a human's verdict disagrees with the current metrics
   should become a small regression set: "does this tool's output at least *flag
   something* on the files we know had a real audible problem." Right now there is no
   such check anywhere in the test suite.
4. **Section-aware / windowed features** — report `extract_features()` over a sliding
   window (e.g. 5 s) alongside the whole-file mean, and flag the window with the largest
   deviation, rather than only ever reporting one number for the whole file. Directly
   addresses gap #4 above.
5. **A basic pitch/chroma summary** — even a coarse 12-bin pitch-class histogram from the
   existing band-energy matrix would let the text report say "brighter, and the pitch
   content shifted toward X" instead of only "brighter."
6. **Keep, don't remove, the human checkpoint.** The most honest improvement is
   organizational, not technical: any report this tooling generates should keep stating
   (as `format_feature_report()` already does) that global averages can hide a localized
   problem, and should recommend a human listening pass whenever `--voice all`'s
   digi-bleed guard fires, whenever the onset match rate is inside the repeatability
   floor (inconclusive by construction), or whenever a driver claims "improved" but the
   feature deltas move in an unexpected direction — cases where the numbers themselves
   say they can't be trusted.

None of the above closes gap #6. They would make the proxy better-correlated with human
judgment on the dimensions it already tries to measure (loudness, brightness, timing);
they would not give this tool the ability to recognize a defect nobody thought to encode
a metric for. That gap only closes by keeping a human listening pass in the loop for
anything this project ships as a claimed fidelity result — not by better feature
engineering.
