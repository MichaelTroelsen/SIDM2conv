"""The Sound Monitor legato A/B probes are PER SONG, never one shared prefix.

bin/build_soundmonitor_native_song.py builds each song twice (gate vs
candidate-legato) before the real build, to decide which voices are legato --
the same scheme bin/build_dmc_native_song.py uses. Both wrote their probes as
`_abg` / `_abl` for every song. af84612 measured what that costs in DMC under a
parallel sweep: `prune_stale_parts` deletes every `<prefix>_part*.staging`, so
one song removed another's in-flight staging file, and `measure_song_voices`
re-reads the probe parts from disk, so a song could score ANOTHER song's probe
and pick a different split. The probes also stayed in the corpus as parts of a
song that does not exist.
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _builder_ast():
    src = open(os.path.join(ROOT, "bin", "build_soundmonitor_native_song.py"),
               encoding="utf-8").read()
    return ast.parse(src)


def test_probe_names_are_distinct_per_song():
    sys.path.insert(0, os.path.join(ROOT, "bin"))
    sys.path.insert(0, ROOT)
    import build_soundmonitor_native_song as B
    names = {B.probe_name(k, b) for k in ("g", "l")
             for b in ("Dance_at_Night_remix", "Fun_Fun")}
    assert len(names) == 4
    assert all(n.startswith("_ab") for n in names)


def test_no_probe_build_uses_a_constant_prefix():
    bad = []
    for node in ast.walk(_builder_ast()):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "build_song"
                and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)):
            bad.append((node.lineno, node.args[1].value))
    assert bad == [], f"build_song called with a constant prefix: {bad}"


def test_probe_parts_are_pruned_after_the_ab():
    # Probes are measured, not shipped -- they must not stay in out/soundmonitor.
    pruned = [n for n in ast.walk(_builder_ast())
              if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "prune_stale_parts"
              and len(n.args) == 2 and isinstance(n.args[1], ast.Constant) and n.args[1].value == 0]
    assert pruned, "no prune_stale_parts(<probe prefix>, 0) after the legato A/B"
