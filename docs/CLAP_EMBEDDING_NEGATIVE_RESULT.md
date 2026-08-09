# CLAP audio embeddings on SID material: a measured negative result

**Date**: 2026-08-09 | **Verdict**: do NOT wire CLAP similarity into any fidelity report.
**Tooling**: `sidm2/audio_embed.py`, `pyscript/clap_worker.py`, `pyscript/clap_validate.py`

## Why this was tried

`docs/AUDIO_LISTENING_CAPABILITY_ASSESSMENT.md` gap #6: Claude has no audio-perception
modality, so every "listening" capability in this project is a hand-designed numeric
proxy (`sidm2/audio_listen.py`) that only measures what someone thought to measure. A
pretrained audio-embedding model promised a *learned* similarity that could move on
differences nobody hand-coded a metric for.

laion-clap pins `numpy<2.0` against this project's numpy 2.5.1, so it was installed into
an isolated venv (`tools/clap_venv/`, gitignored) driven as a subprocess. **The isolation
turned out to be load-bearing for a reason beyond package versions**: numpy 1.x publishes
no wheels above cp312, so the venv needs a different *Python version* (3.12) than the
project (3.14) -- something no in-process dependency juggling could deliver.

## The test

`pyscript/clap_validate.py`, built on the same principle as
`measure_repeatability_floor()` in `pyscript/audio_tightness_tool.py`: **a metric is
evidence only when it beats what the same input scores against itself.**

- **Same-tune floor** -- one tune rendered at several sidplayfp `--delay` values. Same
  music, different free-running SID phase. CLAP should call these near-identical.
- **Cross-tune** -- different tunes. CLAP should call these clearly less similar.
- **Separation** = `min(same) - max(cross)`. Positive means every same-tune pair
  outscored every different-tune pair.

## Results

| Tunes | Render length | min(same) | max(cross) | median same / cross | Separation | Verdict |
|---|---|---:|---:|---:|---:|---|
| 4 | 20 s | 0.7952 | 0.8483 | 0.964 / 0.616 | **-0.053** | FAIL |
| 4 | 60 s | 0.9099 | 0.9038 | 0.959 / 0.767 | **+0.006** | PASS (fragile) |
| 9 | 60 s | 0.5336 | 0.9469 | -- / 0.708 | **-0.413** | **FAIL** |

Representative cross-tune pairs at 60 s over 9 tunes -- entirely different compositions,
different composers:

```
+0.9391  Angular vs Beast
+0.9344  Commando vs Angular
+0.9296  Stinsens_Last_Night_of_89 vs Angular
+0.9292  Cybernoid_II vs Beast
```

## Two findings worth keeping

**1. The 60 s / 4-tune PASS was a small-sample artifact.** At +0.0061 it was a
technical pass and a practical nothing; widening to 9 tunes flipped it to -0.4133. Any
future re-test must vary the CORPUS, not just the render length -- a margin that thin is
one unlucky pair from inverting, and it was.

**2. Longer renders made discrimination WORSE, not better.** Going 20 s -> 60 s raised
the cross-tune median from 0.616 to 0.767 while same-tune barely moved. Both populations
compressed into a narrow 0.86-0.99 band. That is the signature of a general-audio model
collapsing toward a genre centroid: to a model trained on AudioSet-scale material, all
C64 SID music is "C64 SID music" first and a specific composition second. More audio
gives it more evidence for the genre, not for the piece.

## Why this kills the use case specifically

Even granting the fragile 4-tune PASS on its own terms, its own floor disqualifies it.
The intended use is comparing an original `.sid` against a converted driver build --
**the same music, differing only in synthesis**. That pair necessarily scores *higher*
than the cross-tune population, i.e. comfortably inside a same-tune floor of 0.91. A
metric whose noise floor swallows the entire question it was brought in to answer cannot
answer it.

## Falsification performed before concluding

The test assumes delay-shifted renders are perceptually identical. That assumption was
checked rather than trusted -- if the renders genuinely differed, CLAP would have been
right and the test wrong. Hawkeye at three delays:

| pair | rms(diff)/rms | correlation | onset match | centroid delta |
|---|---:|---:|---:|---:|
| d0 / d6568 | 0.6694 | 0.7761 | 99.5% | -0.6 Hz |
| d0 / d13136 | 1.2318 | 0.2414 | 88.2% | -1.1 Hz |
| d6568 / d13136 | 1.2452 | 0.2242 | 87.1% | -0.5 Hz |

The renders differ substantially at sample level (correlation as low as 0.22) while
containing the same music (87-99% onset match, centroid within 1.2 Hz). So the same-tune
spread is real, not CLAP hallucinating -- and the verdict still stands, because two
DIFFERENT compositions scoring 0.947 above a same-tune 0.534 is a discrimination failure
no premise correction rescues.

## Status of the tooling

Kept, not deleted. It costs nothing when unused, degrades to a clear actionable error
when the venv is absent (`unavailable_reason()`), and is covered by 19 tests that run
without torch installed (`pyscript/test_audio_embed.py`). A future re-test -- a
music-specific checkpoint, a fine-tuned model, a different embedding family -- needs only
to re-run `clap_validate.py`. **Nothing in the conversion pipeline imports it, and
nothing should until that script passes on a wide corpus with a margin that is not
noise.**

Uninstall with `py -3 pyscript/install_clap.py --uninstall`.

## The general lesson

This is the `sidm2/fidelity_common.py` docstring's lesson arriving from a new direction:
five weighted-accuracy scorers in this repo were each independently broken, one scoring
two identical captures at 50%. The defense that worked here was refusing to report the
number until it had been checked against the case it claimed to judge. The validation
gate cost about an hour and ~1 GB; without it, "CLAP similarity 0.94" would have looked
like a strong fidelity result while being indistinguishable from two unrelated tunes.
