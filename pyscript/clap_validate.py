#!/usr/bin/env python3
"""Does CLAP actually discriminate on SID material? Run this BEFORE trusting it.

CLAP is trained on general audio (AudioSet-scale captions), not C64 chiptune.
Whether its embedding space separates two different SID tunes at all is an
empirical question about THIS material, and a similarity number printed without
that check is exactly the failure mode sidm2/fidelity_common.py's docstring
catalogues: a confident-looking score that was never validated against the case
it claims to judge (five separate weighted-accuracy scorers in this repo were
each independently broken; one scored two identical captures at 50%).

THE TEST
    Same-tune floor  -- render one tune several times with different power-on
                        delays (sidplayfp --delay, the only renderer that
                        exposes it). Same music, different free-running SID
                        phase. CLAP should call these near-identical.
    Cross-tune        -- render different tunes. CLAP should call these
                        clearly less similar.
    Verdict           -- min(same-tune) - max(cross-tune). Positive means every
                        same-tune pair outscored every different-tune pair:
                        clean separation, CLAP carries signal here. Zero or
                        negative means the two populations OVERLAP and a CLAP
                        similarity on this material is not evidence of anything.

This mirrors measure_repeatability_floor() in pyscript/audio_tightness_tool.py:
a metric is only evidence when it beats what the same input scores against
itself.

Usage:
    py -3 pyscript/clap_validate.py
    py -3 pyscript/clap_validate.py --seconds 20 --delays 3
"""
import argparse
import itertools
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from sidm2.audio_embed import ClapBridge, ClapUnavailable, cosine, unavailable_reason
from sidm2.sidplayfp_wrapper import SidplayfpIntegration

PAL_CYCLES_PER_FRAME = 985248 // 50

# Deliberately spread across composers/engines: a separation that only holds
# within one composer's sound would not generalize to the corpus.
DEFAULT_TUNES = [
    'SID/Hubbard_Rob/Commando.sid',
    'SID/Hubbard_Rob/Sanxion.sid',
    'SID/Tel_Jeroen/Hawkeye.sid',
    'SID/Stinsens_Last_Night_of_89.sid',
]


def render(sid_path: Path, out_wav: Path, seconds: int, delay: int) -> Path:
    result = SidplayfpIntegration.export_to_wav(
        sid_file=sid_path, output_file=out_wav, duration=seconds,
        power_on_delay=delay, verbose=0)
    if not result or not result.get('success'):
        err = result.get('error') if result else 'sidplayfp unavailable'
        raise RuntimeError(f"render failed for {sid_path.name} (delay={delay}): {err}")
    return out_wav


def delays(n: int):
    """delay=0 plus evenly-spaced sub-frame offsets (deterministic, so two runs
    of this script validate against the same perturbations)."""
    return [0] + [round(PAL_CYCLES_PER_FRAME * (i + 1) / n) for i in range(n - 1)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seconds', type=int, default=20, help="Render length (default: 20)")
    ap.add_argument('--delays', type=int, default=3,
                    help="Power-on delays per tune = same-tune sample count (default: 3)")
    ap.add_argument('--tunes', nargs='*', default=None, help="Override the tune list")
    ap.add_argument('--keep-temp', action='store_true')
    args = ap.parse_args()

    reason = unavailable_reason()
    if reason:
        print(f"[ERROR] {reason}")
        return 1

    root = Path(__file__).parent.parent
    tunes = [Path(t) if Path(t).is_absolute() else root / t
             for t in (args.tunes or DEFAULT_TUNES)]
    missing = [t for t in tunes if not t.exists()]
    if missing:
        print(f"[ERROR] Missing tune(s): {[str(m) for m in missing]}")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix='clap_validate_'))
    try:
        print(f"Rendering {len(tunes)} tunes x {args.delays} delays "
              f"({args.seconds}s each, sidplayfp)...")
        renders = {}
        for tune in tunes:
            for d in delays(args.delays):
                wav = tmp / f"{tune.stem}_d{d}.wav"
                render(tune, wav, args.seconds, d)
                renders[(tune.stem, d)] = wav

        print("Starting CLAP (first run loads the checkpoint; be patient)...")
        with ClapBridge(verbose=1) as clap:
            print(f"  model={clap.info.get('model')} device={clap.info.get('device')}")
            keys = list(renders)
            emb_matrix = clap.embed([renders[k] for k in keys])
            emb = {k: emb_matrix[i] for i, k in enumerate(keys)}

        same, cross = [], []
        for (name_a, da), (name_b, db) in itertools.combinations(keys, 2):
            c = cosine(emb[(name_a, da)], emb[(name_b, db)])
            (same if name_a == name_b else cross).append(
                (c, f"{name_a}(d{da}) vs {name_b}(d{db})"))

        if not same or not cross:
            print("[ERROR] Need >=2 tunes and >=2 delays to compare populations.")
            return 1

        same_vals = [c for c, _ in same]
        cross_vals = [c for c, _ in cross]

        print("\n" + "=" * 78)
        print("SAME TUNE, different power-on delay  (should be HIGH)")
        print("=" * 78)
        for c, label in sorted(same):
            print(f"  {c:+.4f}  {label}")
        print(f"  --> min {min(same_vals):+.4f}  median {np.median(same_vals):+.4f}")

        print("\n" + "=" * 78)
        print("DIFFERENT TUNES  (should be clearly LOWER)")
        print("=" * 78)
        for c, label in sorted(cross, reverse=True)[:12]:
            print(f"  {c:+.4f}  {label}")
        if len(cross) > 12:
            print(f"  ... {len(cross) - 12} more")
        print(f"  --> max {max(cross_vals):+.4f}  median {np.median(cross_vals):+.4f}")

        margin = min(same_vals) - max(cross_vals)
        print("\n" + "=" * 78)
        print(f"SEPARATION = min(same) - max(cross) = {margin:+.4f}")
        print("=" * 78)
        if margin > 0:
            print("  [PASS] Every same-tune pair scored above every different-tune pair.")
            print("         CLAP carries signal on this material. Still report the")
            print("         same-tune floor alongside any similarity you quote -- a score")
            print(f"         at or above {min(same_vals):.4f} is indistinguishable from")
            print("         'the same tune rendered again'.")
        else:
            print("  [FAIL] The two populations OVERLAP: at least one pair of DIFFERENT")
            print("         tunes scored as similar as two renders of the SAME tune.")
            print("         A CLAP similarity on SID material is NOT evidence of anything")
            print("         under this configuration. Do not wire it into a fidelity")
            print("         report. Investigate (longer renders? different checkpoint?)")
            print("         or drop the approach -- do not quote the number regardless.")
        return 0 if margin > 0 else 2

    except ClapUnavailable as e:
        print(f"[ERROR] {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return 1
    finally:
        if args.keep_temp:
            print(f"\n[INFO] Renders kept: {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
