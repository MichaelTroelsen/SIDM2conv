"""CLAP audio-embedding bridge: a learned perceptual similarity, out of process.

WHY A SUBPROCESS AND NOT AN IMPORT
----------------------------------
laion-clap hard-pins ``numpy<2.0``. This project runs numpy 2.5.1 across
``sidm2/`` and ~1900 tests. Installing laion-clap into the main environment
would force-downgrade numpy project-wide. So CLAP lives in its OWN virtualenv
(``tools/clap_venv/``, created by ``pyscript/install_clap.py``) and is driven
as a subprocess over a newline-delimited JSON protocol. **Nothing in this
module imports torch, laion_clap, or librosa** -- it is numpy-only, like the
rest of ``sidm2/``, and it degrades to a clear error when the venv is absent.

WHAT THIS BUYS, AND WHAT IT DOES NOT
------------------------------------
``sidm2/audio_listen.py``'s features (centroid, rolloff, flatness) are
hand-designed proxies: they measure what someone thought to measure. CLAP is a
model trained to place audio and text in a shared space, so cosine distance
between two audio embeddings is a *learned* similarity that can move on
differences nobody hand-coded a metric for.

It is still NOT hearing, and it carries a specific hazard this project has been
burned by repeatedly (see ``sidm2/fidelity_common.py``'s docstring): a
confident-looking number that was never checked against the case it claims to
judge. CLAP is trained on general audio (AudioSet-scale), not SID chiptune. Its
discriminative power ON THIS MATERIAL is an empirical question, not an
assumption -- ``pyscript/clap_validate.py`` answers it by testing whether
cross-tune similarity actually separates from the same-tune re-render floor.
**Do not report a CLAP similarity without that floor beside it**, for exactly
the reason ``audio_tightness_tool.py`` never reports an onset match rate
without ``--repeat-floor``: a similarity inside the noise floor is not evidence.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
CLAP_VENV = PROJECT_ROOT / 'tools' / 'clap_venv'
WORKER_SCRIPT = PROJECT_ROOT / 'pyscript' / 'clap_worker.py'

# Loading the checkpoint takes tens of seconds; every later call is fast. The
# bridge therefore keeps ONE worker alive rather than paying that per call.
STARTUP_TIMEOUT_S = 600.0
CALL_TIMEOUT_S = 300.0


class ClapUnavailable(RuntimeError):
    """The CLAP venv is not installed (an actionable state, not a bug)."""


class ClapWorkerError(RuntimeError):
    """The worker started but a command failed."""


def venv_python() -> Path:
    """Interpreter inside the CLAP venv (Windows layout vs POSIX layout)."""
    if os.name == 'nt':
        return CLAP_VENV / 'Scripts' / 'python.exe'
    return CLAP_VENV / 'bin' / 'python'


def is_available() -> bool:
    """True when both halves of the bridge exist on disk.

    Deliberately does NOT start the worker or import anything -- callers use
    this to decide whether to offer a CLAP-backed feature at all, and that
    decision must be cheap.
    """
    return venv_python().exists() and WORKER_SCRIPT.exists()


def unavailable_reason() -> Optional[str]:
    """Human-actionable explanation, or None when available."""
    if not WORKER_SCRIPT.exists():
        return f"CLAP worker script missing: {WORKER_SCRIPT}"
    if not venv_python().exists():
        return (
            f"CLAP venv not installed (expected {venv_python()}).\n"
            f"  Install with: py -3 pyscript/install_clap.py\n"
            f"  This is a large download (torch + checkpoint, ~2-3 GB) and is "
            f"OPTIONAL -- every other tool in this project works without it."
        )
    return None


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two embedding vectors.

    Computed here, main-side, rather than in the worker: the worker returns
    raw embeddings so a caller can cache them and make many comparisons
    without re-running the model.
    """
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return float('nan')  # undefined, not zero -- an empty embedding is no evidence
    return float(np.dot(a, b) / (na * nb))


class ClapBridge:
    """Persistent CLAP worker, driven over newline-delimited JSON.

    Use as a context manager::

        with ClapBridge() as clap:
            emb = clap.embed(['a.wav', 'b.wav'])
            print(cosine(emb[0], emb[1]))

    The worker redirects fd 1 so that library chatter (torch/librosa warnings,
    checkpoint download progress) cannot corrupt the protocol stream -- see
    pyscript/clap_worker.py. Responses arrive on a duplicated real stdout;
    everything else lands on stderr.
    """

    def __init__(self, verbose: int = 0) -> None:
        reason = unavailable_reason()
        if reason:
            raise ClapUnavailable(reason)
        self.verbose = verbose
        self._proc: Optional[subprocess.Popen] = None
        # Populated by start(): {'model': ..., 'device': ...}. Callers report it
        # so a result can be traced to the checkpoint and device that produced it.
        self.info: Dict[str, Any] = {}

    def __enter__(self) -> "ClapBridge":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def start(self) -> Dict[str, Any]:
        """Spawn the worker and block until the model reports ready."""
        if self._proc is not None:
            raise RuntimeError("ClapBridge already started")
        self._proc = subprocess.Popen(
            [str(venv_python()), str(WORKER_SCRIPT)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=None if self.verbose > 1 else subprocess.DEVNULL,
            text=True, bufsize=1,
        )
        self.info = self._call({'cmd': 'ping'}, timeout=STARTUP_TIMEOUT_S)
        return self.info

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.poll() is None:
                self._proc.stdin.write(json.dumps({'cmd': 'quit'}) + "\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=15)
        except Exception:
            pass
        finally:
            if self._proc.poll() is None:
                self._proc.kill()
            self._proc = None

    def _call(self, payload: Dict[str, Any], timeout: float = CALL_TIMEOUT_S) -> Dict[str, Any]:
        if self._proc is None or self._proc.poll() is not None:
            raise ClapWorkerError("CLAP worker is not running")
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

        line = self._proc.stdout.readline()
        if not line:
            raise ClapWorkerError(
                "CLAP worker exited without responding (re-run with -vv to see its stderr)")
        try:
            resp = json.loads(line)
        except json.JSONDecodeError as e:
            raise ClapWorkerError(f"Malformed worker response: {line[:200]!r}") from e
        if not resp.get('ok'):
            raise ClapWorkerError(resp.get('error', 'unknown worker error'))
        return resp

    def embed(self, wav_paths: Sequence[Union[str, Path]]) -> np.ndarray:
        """Audio embeddings, shape (len(wav_paths), D).

        Paths are handed to CLAP, which loads and resamples them itself (it
        wants 48 kHz; this project renders 44.1 kHz -- letting CLAP do the
        loading avoids a hand-rolled resample in the measurement path).
        """
        paths = [str(Path(p).resolve()) for p in wav_paths]
        missing = [p for p in paths if not Path(p).exists()]
        if missing:
            raise FileNotFoundError(f"WAV(s) not found: {missing}")
        resp = self._call({'cmd': 'embed', 'paths': paths})
        return np.asarray(resp['embeddings'], dtype=np.float64)

    def text_embed(self, texts: Sequence[str]) -> np.ndarray:
        """Text embeddings in the SAME space as embed(), shape (len(texts), D).

        Enables zero-shot audio<->text scoring ("does this sound like a harsh
        buzzy lead"). Treat results as a weak signal: CLAP's training captions
        are general-audio, so its vocabulary for SID synthesis specifics is
        unproven -- validate before quoting, same rule as everything else here.
        """
        resp = self._call({'cmd': 'text_embed', 'texts': list(texts)})
        return np.asarray(resp['embeddings'], dtype=np.float64)

    def similarity(self, wav_a: Union[str, Path], wav_b: Union[str, Path]) -> float:
        """Cosine similarity between two rendered WAVs, in one call."""
        emb = self.embed([wav_a, wav_b])
        return cosine(emb[0], emb[1])
