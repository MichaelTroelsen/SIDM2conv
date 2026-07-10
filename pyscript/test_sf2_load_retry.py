"""Smoke tests for sf2_load_retry — pure-logic tests, no GUI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sf2_load_retry


def test_missing_file_returns_missing_verdict():
    """load_with_retry on a non-existent path returns verdict='MISSING'."""
    import os
    import tempfile
    missing = os.path.join(tempfile.gettempdir(), '__sidm2_does_not_exist__.sf2')
    res = sf2_load_retry.load_with_retry(missing, max_attempts=3)
    assert res['verdict'] == 'MISSING'
    assert res['attempts'] == 0
    assert res['first_pass'] is None
    assert res['attempt_log'] == []


def test_first_pass_short_circuits(monkeypatch, tmp_path):
    """If attempt 1 PASSes, no further attempts are made."""
    f = tmp_path / 'fake.sf2'
    f.write_bytes(b'\x00' * 64)
    calls = []

    def fake_test_one(path, total_timeout=12.0):
        calls.append(path)
        return {'verdict': 'PASS', 'elapsed_s': 5.0, 'exit_code': None}

    monkeypatch.setattr(sf2_load_retry.harness, 'test_one', fake_test_one)
    res = sf2_load_retry.load_with_retry(str(f), max_attempts=10, verbose=False)
    assert res['verdict'] == 'PASS'
    assert res['attempts'] == 1
    assert res['first_pass'] == 1
    assert len(calls) == 1


def test_eventual_pass_after_crashes(monkeypatch, tmp_path):
    """Returns PASS on the first successful attempt and stops there."""
    f = tmp_path / 'fake.sf2'
    f.write_bytes(b'\x00' * 64)
    sequence = ['CRASH', 'CRASH', 'PASS', 'CRASH']
    idx = [0]

    def fake_test_one(path, total_timeout=12.0):
        v = sequence[idx[0]]
        idx[0] += 1
        return {'verdict': v, 'elapsed_s': 5.5,
                'exit_code': None if v == 'PASS' else 0xC0000005}

    monkeypatch.setattr(sf2_load_retry.harness, 'test_one', fake_test_one)
    # Disable the inter-attempt sleep for fast test
    monkeypatch.setattr(sf2_load_retry.time, 'sleep', lambda *_: None)
    res = sf2_load_retry.load_with_retry(str(f), max_attempts=10, verbose=False)
    assert res['verdict'] == 'PASS'
    assert res['attempts'] == 3
    assert res['first_pass'] == 3
    # PASS short-circuits — index advanced exactly 3 times, not 4
    assert idx[0] == 3


def test_all_crashes_returns_crash(monkeypatch, tmp_path):
    """When every attempt crashes, returns CRASH and full attempt log."""
    f = tmp_path / 'fake.sf2'
    f.write_bytes(b'\x00' * 64)

    def fake_test_one(path, total_timeout=12.0):
        return {'verdict': 'CRASH', 'elapsed_s': 5.5, 'exit_code': 0xC0000005}

    monkeypatch.setattr(sf2_load_retry.harness, 'test_one', fake_test_one)
    monkeypatch.setattr(sf2_load_retry.time, 'sleep', lambda *_: None)
    res = sf2_load_retry.load_with_retry(str(f), max_attempts=4, verbose=False)
    assert res['verdict'] == 'CRASH'
    assert res['attempts'] == 4
    assert res['first_pass'] is None
    assert len(res['attempt_log']) == 4
