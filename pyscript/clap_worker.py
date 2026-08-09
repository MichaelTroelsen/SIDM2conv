#!/usr/bin/env python3
"""CLAP worker -- runs INSIDE tools/clap_venv, never in the main environment.

Driven by sidm2/audio_embed.py over newline-delimited JSON on stdin/stdout.
This file imports laion_clap (which pins numpy<2.0) and therefore must NEVER be
imported by the main project; it is only ever executed as a subprocess by the
venv's own interpreter. It is named clap_worker.py (not test_*.py) so pytest
does not collect it, and every heavy import happens inside main() rather than
at module scope, so even an accidental import stays harmless.

PROTOCOL (one JSON object per line, one JSON response per line)
    -> {"cmd": "ping"}                      <- {"ok": true, "model": ..., "device": ...}
    -> {"cmd": "embed", "paths": [...]}     <- {"ok": true, "embeddings": [[...], ...]}
    -> {"cmd": "text_embed", "texts": [...]}<- {"ok": true, "embeddings": [[...], ...]}
    -> {"cmd": "quit"}                      <- {"ok": true}
    errors                                  <- {"ok": false, "error": "..."}

WHY fd 1 IS REDIRECTED
    torch, librosa and laion_clap's checkpoint downloader all write progress and
    warnings to stdout, including from C extensions where redirecting
    sys.stdout would not help. Any such byte lands in the middle of the JSON
    stream and desynchronizes the protocol. So main() duplicates the real fd 1
    for protocol output, then points fd 1 itself at fd 2 -- after that, every
    print in this process (Python or native) goes to stderr, and only explicit
    protocol writes reach the parent.
"""
import json
import os
import sys


def _install_fd_guard():
    """Return a writable handle on the REAL stdout, then send fd 1 to stderr."""
    real_stdout_fd = os.dup(1)
    os.dup2(2, 1)                      # anything printing to fd 1 now hits stderr
    out = os.fdopen(real_stdout_fd, 'w', buffering=1, encoding='utf-8')
    sys.stdout = sys.stderr            # belt and braces for pure-Python prints
    return out


def _respond(out, payload):
    out.write(json.dumps(payload) + "\n")
    out.flush()


def main() -> int:
    out = _install_fd_guard()

    model = None
    model_name = None

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError as e:
            _respond(out, {'ok': False, 'error': f'malformed request: {e}'})
            continue

        cmd = req.get('cmd')
        try:
            if cmd == 'quit':
                _respond(out, {'ok': True})
                return 0

            if model is None:
                # Imported lazily and only once: loading the checkpoint is the
                # expensive step the persistent-worker design exists to amortize.
                import laion_clap  # noqa: F401  (venv-only dependency)
                import torch
                model = laion_clap.CLAP_Module(enable_fusion=False)
                model.load_ckpt()
                model_name = 'laion_clap/CLAP_Module(enable_fusion=False)'
                device = 'cuda' if torch.cuda.is_available() else 'cpu'

            if cmd == 'ping':
                _respond(out, {'ok': True, 'model': model_name, 'device': device})

            elif cmd == 'embed':
                paths = req.get('paths') or []
                if not paths:
                    _respond(out, {'ok': False, 'error': 'embed: no paths given'})
                    continue
                emb = model.get_audio_embedding_from_filelist(x=paths, use_tensor=False)
                _respond(out, {'ok': True, 'embeddings': [list(map(float, v)) for v in emb]})

            elif cmd == 'text_embed':
                texts = req.get('texts') or []
                if not texts:
                    _respond(out, {'ok': False, 'error': 'text_embed: no texts given'})
                    continue
                emb = model.get_text_embedding(texts, use_tensor=False)
                _respond(out, {'ok': True, 'embeddings': [list(map(float, v)) for v in emb]})

            else:
                _respond(out, {'ok': False, 'error': f'unknown cmd: {cmd!r}'})

        except Exception as e:  # never let one bad command kill the worker
            import traceback
            traceback.print_exc(file=sys.stderr)
            _respond(out, {'ok': False, 'error': f'{type(e).__name__}: {e}'})

    return 0


if __name__ == '__main__':
    sys.exit(main())
