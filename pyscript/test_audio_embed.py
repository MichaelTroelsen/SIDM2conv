#!/usr/bin/env python3
"""Tests for sidm2.audio_embed (the CLAP subprocess bridge).

Every test here runs WITHOUT tools/clap_venv installed -- the worker process is
faked. That is the point: the bridge is optional tooling, so its client code
must be verifiable in the normal ~1900-test suite on a machine that has never
downloaded torch.

Usage:
    python -m pytest pyscript/test_audio_embed.py -v
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import audio_embed
from sidm2.audio_embed import (ClapBridge, ClapUnavailable, ClapWorkerError,
                                cosine, is_available, unavailable_reason, venv_python)


class FakeProc:
    """Stands in for the worker subprocess: canned responses, recorded requests."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.killed = False
        self._returncode = None

        outer = self

        class _Stdin:
            def write(self, data):
                outer.requests.append(data)

            def flush(self):
                pass

        class _Stdout:
            def readline(self):
                if not outer._responses:
                    return ''          # worker died / no more output
                r = outer._responses.pop(0)
                return r if isinstance(r, str) else json.dumps(r) + "\n"

        self.stdin = _Stdin()
        self.stdout = _Stdout()

    def poll(self):
        return self._returncode

    def wait(self, timeout=None):
        self._returncode = 0
        return 0

    def kill(self):
        self.killed = True
        self._returncode = -9

    def sent(self):
        return [json.loads(r) for r in self.requests]


PING_OK = {'ok': True, 'model': 'fake-clap', 'device': 'cpu'}


def _bridge(responses):
    """A started ClapBridge wired to a FakeProc, with availability forced on."""
    proc = FakeProc(responses)
    with mock.patch.object(audio_embed, 'unavailable_reason', return_value=None), \
         mock.patch.object(audio_embed.subprocess, 'Popen', return_value=proc):
        bridge = ClapBridge()
        bridge.start()
    return bridge, proc


class TestCosine(unittest.TestCase):
    def test_identical_vectors_are_one(self):
        v = np.array([1.0, 2.0, 3.0])
        self.assertAlmostEqual(cosine(v, v), 1.0, places=9)

    def test_orthogonal_vectors_are_zero(self):
        self.assertAlmostEqual(cosine(np.array([1.0, 0.0]), np.array([0.0, 1.0])), 0.0, places=9)

    def test_opposite_vectors_are_minus_one(self):
        self.assertAlmostEqual(cosine(np.array([1.0, 1.0]), np.array([-1.0, -1.0])), -1.0, places=9)

    def test_scale_invariant(self):
        a = np.array([1.0, 2.0, 3.0])
        self.assertAlmostEqual(cosine(a, a * 7.5), 1.0, places=9)

    def test_zero_vector_is_nan_not_zero(self):
        # An empty embedding is NO EVIDENCE, not "maximally dissimilar" -- same
        # rule as fidelity_common.score_pct returning None rather than 0.0.
        self.assertTrue(np.isnan(cosine(np.zeros(4), np.array([1.0, 0, 0, 0]))))


class TestAvailability(unittest.TestCase):
    def test_unavailable_when_venv_missing(self):
        missing = Path('C:/definitely/not/here/python.exe')
        with mock.patch.object(audio_embed, 'venv_python', return_value=missing):
            self.assertFalse(is_available())
            reason = unavailable_reason()
            self.assertIsNotNone(reason)
            self.assertIn('install_clap.py', reason)

    def test_constructor_raises_when_unavailable(self):
        with mock.patch.object(audio_embed, 'unavailable_reason',
                                return_value='no venv'):
            with self.assertRaises(ClapUnavailable):
                ClapBridge()

    def test_venv_python_path_is_platform_shaped(self):
        p = venv_python()
        self.assertIn(p.name, ('python.exe', 'python'))


class TestProtocol(unittest.TestCase):
    def test_start_sends_ping_and_records_info(self):
        bridge, proc = _bridge([PING_OK])
        self.assertEqual(proc.sent()[0], {'cmd': 'ping'})
        self.assertEqual(bridge.info['model'], 'fake-clap')

    def test_embed_sends_resolved_paths_and_parses_matrix(self):
        emb = {'ok': True, 'embeddings': [[1.0, 0.0], [0.0, 1.0]]}
        bridge, proc = _bridge([PING_OK, emb])
        with mock.patch.object(Path, 'exists', return_value=True):
            out = bridge.embed(['a.wav', 'b.wav'])
        self.assertEqual(out.shape, (2, 2))
        req = proc.sent()[1]
        self.assertEqual(req['cmd'], 'embed')
        self.assertEqual(len(req['paths']), 2)
        # paths must be absolute -- the worker runs with a different cwd
        self.assertTrue(all(Path(p).is_absolute() for p in req['paths']))

    def test_embed_refuses_missing_file_before_calling_worker(self):
        bridge, proc = _bridge([PING_OK])
        with self.assertRaises(FileNotFoundError):
            bridge.embed(['no_such_file_12345.wav'])
        self.assertEqual(len(proc.sent()), 1)  # only the ping

    def test_text_embed_sends_texts(self):
        emb = {'ok': True, 'embeddings': [[0.5, 0.5]]}
        bridge, proc = _bridge([PING_OK, emb])
        out = bridge.text_embed(['a buzzy chiptune lead'])
        self.assertEqual(out.shape, (1, 2))
        self.assertEqual(proc.sent()[1]['cmd'], 'text_embed')
        self.assertEqual(proc.sent()[1]['texts'], ['a buzzy chiptune lead'])

    def test_similarity_round_trip(self):
        emb = {'ok': True, 'embeddings': [[1.0, 0.0], [1.0, 0.0]]}
        bridge, _ = _bridge([PING_OK, emb])
        with mock.patch.object(Path, 'exists', return_value=True):
            self.assertAlmostEqual(bridge.similarity('a.wav', 'b.wav'), 1.0, places=9)

    def test_close_sends_quit(self):
        bridge, proc = _bridge([PING_OK, {'ok': True}])
        bridge.close()
        self.assertEqual(proc.sent()[-1], {'cmd': 'quit'})


class TestErrorHandling(unittest.TestCase):
    def test_worker_error_response_raises(self):
        bridge, _ = _bridge([PING_OK, {'ok': False, 'error': 'checkpoint missing'}])
        with mock.patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(ClapWorkerError) as cm:
                bridge.embed(['a.wav'])
        self.assertIn('checkpoint missing', str(cm.exception))

    def test_malformed_response_raises(self):
        bridge, _ = _bridge([PING_OK, "not json at all\n"])
        with mock.patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(ClapWorkerError) as cm:
                bridge.embed(['a.wav'])
        self.assertIn('Malformed', str(cm.exception))

    def test_dead_worker_raises_rather_than_hanging(self):
        # readline() returning '' is EOF: the worker exited. A bridge that
        # treated that as an empty result would silently produce a zero score.
        bridge, _ = _bridge([PING_OK])
        with mock.patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(ClapWorkerError) as cm:
                bridge.embed(['a.wav'])
        self.assertIn('without responding', str(cm.exception))

    def test_start_twice_is_rejected(self):
        bridge, proc = _bridge([PING_OK])
        with mock.patch.object(audio_embed.subprocess, 'Popen', return_value=proc):
            with self.assertRaises(RuntimeError):
                bridge.start()


class TestWorkerScriptIsNotImportable(unittest.TestCase):
    """pyscript/clap_worker.py must never be imported by the main environment.

    It imports laion_clap (numpy<2.0) which is not installed here on purpose.
    Its heavy imports live inside main(), so importing the module is harmless --
    this pins that, so a refactor that hoists `import laion_clap` to module
    scope fails loudly here instead of at pytest-collection time.
    """

    def test_module_scope_has_no_heavy_imports(self):
        src = (Path(__file__).parent / 'clap_worker.py').read_text(encoding='utf-8')
        module_level = [ln for ln in src.splitlines()
                        if ln.startswith('import ') or ln.startswith('from ')]
        for banned in ('laion_clap', 'torch', 'librosa'):
            self.assertFalse([ln for ln in module_level if banned in ln],
                             f"{banned} must be imported inside main(), not at module scope")


if __name__ == '__main__':
    unittest.main()
