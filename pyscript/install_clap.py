#!/usr/bin/env python3
"""Install the CLAP audio-embedding model into an ISOLATED virtualenv.

This is OPTIONAL tooling. Every other tool in this project works without it;
nothing in the conversion pipeline depends on it.

WHY A SEPARATE VENV
    laion-clap hard-pins numpy<2.0. This project runs numpy 2.5.1 across
    sidm2/ and ~1900 tests, so installing it into the main environment would
    force-downgrade numpy project-wide. The venv keeps the two apart; the main
    process talks to it as a subprocess (see sidm2/audio_embed.py).

COST
    laion-clap pulls in torch (~2.5 GB on Windows) plus librosa/numba, and
    load_ckpt() downloads a model checkpoint (~2 GB) on first run. Budget
    3-5 GB of disk and a long first run. This script refuses to start without
    an explicit confirmation (or --yes).

Usage:
    py -3 pyscript/install_clap.py            # prompts before downloading
    py -3 pyscript/install_clap.py --yes      # non-interactive
    py -3 pyscript/install_clap.py --verify   # only check an existing install
    py -3 pyscript/install_clap.py --uninstall
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_embed import CLAP_VENV, WORKER_SCRIPT, venv_python

# Pinned deliberately: laion-clap's numpy<2.0 requirement is the whole reason
# this venv exists, so the constraint is restated here rather than left to
# whatever the resolver picks. numba (via librosa) accepts numpy<2.5, so the
# two coexist -- verified against PyPI metadata, not assumed.
REQUIREMENTS = ['laion-clap', 'numpy<2.0']

# NONE of the torch family is in laion-clap's dependency list -- verified with
# `pip show laion_clap`, whose Requires: names torchlibrosa but not torch,
# torchvision or torchaudio, while the package imports all three at module
# scope (hook.py:9 `import torch`; clap_module/utils.py:4
# `from torchvision.ops.misc import FrozenBatchNorm2d`). A packaging bug on
# their side. Installing laion-clap alone "succeeds" and then dies at first
# import -- which is exactly what happened on runs 2 and 3 of this script,
# one missing module at a time. timm and open_clip are ALSO imported but sit
# behind guarded try-blocks, so they stay out of here until something actually
# needs them.
TORCH_REQUIREMENTS = ['torch', 'torchvision', 'torchaudio']

# CPU-only wheels by default: this workload embeds a handful of 20-second clips,
# where GPU buys nothing, and the CPU index is roughly an order of magnitude
# smaller than the CUDA-bundled default (~200 MB vs ~2.5 GB). --cuda opts back
# into PyPI's default wheel for anyone who wants GPU.
TORCH_CPU_INDEX = 'https://download.pytorch.org/whl/cpu'

# THE VENV CANNOT USE THE PROJECT'S OWN PYTHON, and this is not a preference.
# laion-clap pins numpy<2.0, i.e. numpy 1.x, whose last release (1.26.4) ships
# win_amd64 wheels for cp39/310/311/312 ONLY. On 3.13+ pip falls back to a
# source build that imports and then dies in numpy's own getlimits with
# "OverflowError: cannot convert longdouble infinity to integer" -- observed
# here on 3.14.6 before this check existed, not a theoretical concern.
# Highest-first: newest interpreter that still has real numpy 1.x wheels.
COMPATIBLE_PYTHONS = ['3.12', '3.11', '3.10']
MAX_SUPPORTED_MINOR = 12


def find_base_python(explicit=None):
    """Locate an interpreter that numpy 1.x actually publishes wheels for."""
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    for ver in COMPATIBLE_PYTHONS:
        candidates = ([['py', f'-{ver}']] if sys.platform == 'win32' else []) + \
                     [[f'python{ver}']]
        for cand in candidates:
            try:
                r = subprocess.run(cand + ['-c', 'import sys; print(sys.executable)'],
                                    capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout.strip():
                    return Path(r.stdout.strip())
            except (OSError, subprocess.SubprocessError):
                continue
    return None


def check_interpreter(py_exe: Path) -> bool:
    """Refuse an interpreter too new for numpy 1.x wheels, loudly."""
    r = subprocess.run([str(py_exe), '-c',
                        'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'],
                       capture_output=True, text=True, timeout=30)
    ver = r.stdout.strip()
    try:
        major, minor = (int(v) for v in ver.split('.')[:2])
    except ValueError:
        print(f"[ERROR] Could not determine version of {py_exe}")
        return False
    if major != 3 or minor > MAX_SUPPORTED_MINOR:
        print(f"[ERROR] Python {ver} ({py_exe}) is too new for this venv.")
        print(f"        laion-clap requires numpy<2.0, and numpy 1.x ships no wheels")
        print(f"        above cp{MAX_SUPPORTED_MINOR}; a source build imports and then")
        print(f"        crashes in numpy's own getlimits. Install Python 3.12 and")
        print(f"        re-run, or pass --python <path-to-3.12>.")
        return False
    print(f"[OK] Base interpreter: Python {ver} ({py_exe})")
    return True


def _run(args, **kw):
    print(f"  $ {' '.join(str(a) for a in args)}")
    return subprocess.run(args, **kw)


def create_venv(base_python: Path) -> bool:
    """Create the venv FROM base_python.

    Shells out to `<base_python> -m venv` rather than using venv.EnvBuilder:
    EnvBuilder would clone the *currently running* interpreter, which is the
    project's own (3.14 here) -- exactly the interpreter COMPATIBLE_PYTHONS
    exists to avoid.
    """
    if venv_python().exists():
        print(f"[OK] venv already exists: {CLAP_VENV}")
        return True
    print(f"Creating venv from {base_python}: {CLAP_VENV}")
    CLAP_VENV.parent.mkdir(parents=True, exist_ok=True)
    r = _run([str(base_python), '-m', 'venv', str(CLAP_VENV)])
    if r.returncode != 0 or not venv_python().exists():
        print(f"[ERROR] venv creation failed (interpreter missing: {venv_python()})")
        return False
    print(f"[OK] venv created: {venv_python()}")
    return True


def install_requirements(cuda: bool = False) -> bool:
    print("\nInstalling CLAP (this is the big step)...")
    r = _run([str(venv_python()), '-m', 'pip', 'install', '--upgrade', 'pip'])
    if r.returncode != 0:
        print("[WARN] pip self-upgrade failed; continuing anyway")

    # torch FIRST and on its own: laion-clap does not declare it (see
    # TORCH_REQUIREMENT above), and pulling it from the CPU index keeps the
    # download ~10x smaller. Separate invocation rather than one resolve, so
    # the custom index applies only to torch and not to librosa/transformers.
    torch_cmd = [str(venv_python()), '-m', 'pip', 'install', *TORCH_REQUIREMENTS]
    if not cuda:
        torch_cmd += ['--index-url', TORCH_CPU_INDEX]
    r = _run(torch_cmd)
    if r.returncode != 0:
        print("[ERROR] torch-family install failed -- see the resolver output above.")
        return False

    r = _run([str(venv_python()), '-m', 'pip', 'install', *REQUIREMENTS])
    if r.returncode != 0:
        print("\n[ERROR] Dependency install failed. The resolver output above is the")
        print("        real diagnosis -- most likely a wheel is unavailable for this")
        print("        Python version. Retry against another interpreter by deleting")
        print(f"        {CLAP_VENV} and recreating it with e.g. py -3.12 -m venv.")
        return False
    return True


def verify() -> bool:
    """Start the real bridge and ping it -- the only proof that matters.

    Deliberately routed through sidm2.audio_embed rather than a bespoke check:
    if this passes, the exact path production code uses is known to work,
    including the fd-redirection guard in the worker.
    """
    print("\nVerifying (loads the checkpoint -- first run downloads it, be patient)...")
    try:
        from sidm2.audio_embed import ClapBridge
        with ClapBridge(verbose=2) as clap:
            print(f"[OK] CLAP ready: model={clap.info.get('model')} "
                  f"device={clap.info.get('device')}")
        return True
    except Exception as e:
        print(f"[ERROR] Verification failed: {type(e).__name__}: {e}")
        return False


def uninstall() -> bool:
    if not CLAP_VENV.exists():
        print(f"[OK] Nothing to remove ({CLAP_VENV} does not exist)")
        return True
    print(f"Removing {CLAP_VENV} ...")
    shutil.rmtree(CLAP_VENV, ignore_errors=True)
    ok = not CLAP_VENV.exists()
    print("[OK] Removed" if ok else f"[ERROR] Could not fully remove {CLAP_VENV}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--yes', '-y', action='store_true', help="Skip the confirmation prompt")
    ap.add_argument('--verify', action='store_true', help="Only verify an existing install")
    ap.add_argument('--uninstall', action='store_true', help="Delete the CLAP venv")
    ap.add_argument('--python', default=None, metavar='EXE',
                    help="Base interpreter for the venv (must be <=3.12; auto-detected "
                         "from py -3.12/3.11/3.10 by default)")
    ap.add_argument('--cuda', action='store_true',
                    help="Install the CUDA-bundled torch from PyPI instead of the much "
                         "smaller CPU-only build (this workload does not need a GPU)")
    args = ap.parse_args()

    if args.uninstall:
        return 0 if uninstall() else 1

    if not WORKER_SCRIPT.exists():
        print(f"[ERROR] Worker script missing: {WORKER_SCRIPT}")
        return 1

    if args.verify:
        if not venv_python().exists():
            print(f"[ERROR] No venv at {CLAP_VENV}. Run without --verify to install.")
            return 1
        return 0 if verify() else 1

    print(__doc__.split('Usage:')[0].strip())
    if not args.yes:
        reply = input("\nProceed with a multi-GB download? [y/N] ").strip().lower()
        if reply not in ('y', 'yes'):
            print("Aborted -- nothing downloaded.")
            return 1

    base = find_base_python(args.python)
    if base is None:
        print("[ERROR] No compatible Python found for the CLAP venv.")
        print(f"        Need one of {COMPATIBLE_PYTHONS} (numpy<2.0 wheel availability).")
        print("        Install Python 3.12, or pass --python <path>.")
        return 1
    if not check_interpreter(base):
        return 1

    if not create_venv(base):
        return 1
    if not install_requirements(cuda=args.cuda):
        return 1
    if not verify():
        return 1

    print("\n[OK] CLAP installed.")
    print("     NEXT STEP, and do not skip it: py -3 pyscript/clap_validate.py")
    print("     CLAP is trained on general audio, not SID chiptune. Until that")
    print("     script shows cross-tune similarity separating from the same-tune")
    print("     re-render floor, a CLAP number on this material means nothing.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
