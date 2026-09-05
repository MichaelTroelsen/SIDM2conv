#!/usr/bin/env python3
"""Generate `docs/api/index.html` — the API reference for the `sidm2` package.

ONE COMMAND, NO DEPENDENCIES:

    py -3 docs/api/gen_api_docs.py            # writes docs/api/index.html
    py -3 docs/api/gen_api_docs.py --check    # report only, write nothing (exit 1 if stale)

WHY AST AND NOT pydoc/Sphinx. Both of those IMPORT the module they document.
`sidm2` modules import PyQt6, numpy and Pillow, so an import-based generator
fails on a clean checkout and silently omits whatever failed to import — the
worst failure mode for a coverage document, because the gap looks like an
absence of code rather than an absence of tooling. `ast.parse` reads source and
never executes it, so this runs anywhere Python does. Sphinx is also simply not
installed here (checked 2026-09-05: no sphinx, pdoc, pdoc3 or mkdocs), and a
`conf.py` that cannot be run is a config, not a generator.

WHAT IS DOCUMENTED, and why it is not everything. CLAUDE.md: docstrings are NOT
required outside public APIs. So this emits NO stub for an undocumented symbol —
a page of empty entries reads as coverage while carrying nothing. Instead every
undocumented public symbol is counted and listed by name under "Deliberately
undocumented", so the gap is explicit and countable rather than hidden behind
placeholder prose.

Private symbols (leading underscore) are omitted entirely: they are not API.
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PKG = os.path.join(ROOT, "sidm2")
OUT = os.path.join(HERE, "index.html")


# --------------------------------------------------------------------------
# extraction — pure AST, nothing is imported
# --------------------------------------------------------------------------

def _sig(node):
    """Render a def/class signature without evaluating anything."""
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases]
        return "class %s%s" % (node.name, "(%s)" % ", ".join(bases) if bases else "")
    a = node.args
    parts = []
    pos = list(a.posonlyargs) + list(a.args)
    defaults = list(a.defaults)
    pad = len(pos) - len(defaults)
    for i, arg in enumerate(pos):
        s = arg.arg
        if arg.annotation is not None:
            s += ": " + ast.unparse(arg.annotation)
        if i >= pad:
            s += "=" + ast.unparse(defaults[i - pad])
        parts.append(s)
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    if a.kwonlyargs:
        if not a.vararg:
            parts.append("*")
        for arg, d in zip(a.kwonlyargs, a.kw_defaults):
            s = arg.arg
            if arg.annotation is not None:
                s += ": " + ast.unparse(arg.annotation)
            if d is not None:
                s += "=" + ast.unparse(d)
            parts.append(s)
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    ret = " -> " + ast.unparse(node.returns) if node.returns else ""
    kw = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
    return "%s%s(%s)%s" % (kw, node.name, ", ".join(parts), ret)


def _summary(node):
    """First paragraph of a docstring, collapsed to one line. '' if absent."""
    doc = ast.get_docstring(node)
    if not doc:
        return ""
    out = []
    for line in doc.strip().splitlines():
        if not line.strip():
            break
        out.append(line.strip())
    return " ".join(out)


def _exported_names(tree):
    """Names re-exported by `from .mod import (...)` in __init__.py."""
    names = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level:
            for a in node.names:
                if a.name != "*":
                    names.add(a.asname or a.name)
    return names


def _all_names(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if getattr(t, "id", "") == "__all__":
                    try:
                        return set(ast.literal_eval(node.value))
                    except Exception:
                        return set()
    return None


def scan():
    """-> (modules, exported, unparsed). Never imports sidm2."""
    modules, unparsed = [], []
    init = os.path.join(PKG, "__init__.py")
    exported = set()
    if os.path.exists(init):
        exported = _exported_names(ast.parse(open(init, encoding="utf-8").read()))

    # Walk SUBPACKAGES too. Scanning only sidm2/*.py silently dropped
    # sidm2/players/, and the two names it exports then showed up in the
    # "unresolved re-export" note as if they did not exist -- a generator
    # misreporting its own coverage gap. Found by running it, not by review.
    files = []
    for dirpath, dirnames, filenames in os.walk(PKG):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".py"):
                files.append(os.path.join(dirpath, fn))

    for path in sorted(files):
        rel = os.path.relpath(path, PKG).replace(os.sep, "/")
        if rel == "__init__.py":
            continue                             # the export source, scanned above
        fn = rel
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        except SyntaxError as e:
            unparsed.append((fn, str(e)))       # reported, never silently dropped
            continue
        declared = _all_names(tree)
        syms = []
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_"):
                continue                         # private: not API, not a gap
            if declared is not None and node.name not in declared:
                continue                         # __all__ is the module's own word
            methods = []
            if isinstance(node, ast.ClassDef):
                for m in node.body:
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and not m.name.startswith("_"):
                        methods.append((m.name, _sig(m), _summary(m)))
            syms.append({
                "name": node.name, "sig": _sig(node), "doc": _summary(node),
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "line": node.lineno, "methods": methods,
            })
        modules.append({
            "file": fn, "name": fn[:-3].replace("/", "."), "doc": _summary(tree),
            "declares_all": declared is not None, "symbols": syms,
        })
    return modules, exported, unparsed


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

CSS = """
:root{--bg:#fbfbfa;--fg:#1c1c1a;--mut:#6b6b64;--line:#e2e1dc;--acc:#7a4a1e;--card:#fff}
@media(prefers-color-scheme:dark){:root{--bg:#16161a;--fg:#e8e8e4;--mut:#9a9a92;
--line:#2e2e34;--acc:#e0a061;--card:#1d1d22}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:60rem;margin:0 auto;padding:2rem 1.25rem 5rem}
h1{font-size:1.7rem;margin:0 0 .25rem}h2{font-size:1.15rem;margin:2.5rem 0 .75rem;
padding-bottom:.3rem;border-bottom:1px solid var(--line)}
h3{font-size:.95rem;margin:1.5rem 0 .4rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.sub{color:var(--mut);margin:0 0 1.5rem}
.stats{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.25rem 0 0;padding:0;list-style:none}
.stats li{background:var(--card);border:1px solid var(--line);border-radius:.4rem;
padding:.5rem .8rem;font-size:.85rem}
.stats b{display:block;font-size:1.25rem;color:var(--acc)}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.84rem}
.sig{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--acc);
border-radius:.25rem;padding:.4rem .6rem;overflow-x:auto;white-space:pre;margin:.35rem 0 .3rem}
.doc{color:var(--mut);margin:0 0 .9rem;font-size:.9rem}
.meth{margin:.15rem 0 .5rem 1.25rem;font-size:.82rem;color:var(--mut)}
.meth code{color:var(--fg)}
details{background:var(--card);border:1px solid var(--line);border-radius:.4rem;
padding:.6rem .9rem;margin:.5rem 0}
summary{cursor:pointer;font-weight:600}
.note{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--acc);
border-radius:.25rem;padding:.8rem 1rem;margin:1rem 0}
.gap{columns:2;column-gap:2rem;font-size:.82rem;margin:.6rem 0 0}
@media(max-width:34rem){.gap{columns:1}}
.gap code{display:block}
table{border-collapse:collapse;width:100%;font-size:.85rem;margin:.5rem 0}
td,th{text-align:left;padding:.3rem .5rem;border-bottom:1px solid var(--line)}
a{color:var(--acc)}
"""


def render(modules, exported, unparsed):
    e = html.escape
    pub = sum(len(m["symbols"]) for m in modules)
    docd = sum(1 for m in modules for s in m["symbols"] if s["doc"])
    gaps = [(m["name"], s["name"], s["kind"])
            for m in modules for s in m["symbols"] if not s["doc"]]
    moddoc = sum(1 for m in modules if m["doc"])
    stamp = _dt.date.today().isoformat()

    o = ["<!-- GENERATED by docs/api/gen_api_docs.py - do not edit by hand -->",
         "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>sidm2 API reference</title><style>%s</style></head><body><div class='wrap'>" % CSS,
         "<h1>sidm2 API reference</h1>",
         "<p class='sub'>Generated %s from source by <code>docs/api/gen_api_docs.py</code>. "
         "Nothing here is hand-written; regenerate rather than edit.</p>" % stamp,
         "<ul class='stats'>",
         "<li><b>%d</b>modules</li>" % len(modules),
         "<li><b>%d</b>public symbols</li>" % pub,
         "<li><b>%d</b>documented</li>" % docd,
         "<li><b>%.1f%%</b>coverage</li>" % (100.0 * docd / pub if pub else 0.0),
         "<li><b>%d</b>re-exported by the package</li>" % len(exported),
         "</ul>"]

    o.append("<div class='note'><strong>What this covers, and what it does not.</strong> "
             "Only the <em>public</em> surface: module-level functions and classes whose "
             "name does not start with <code>_</code>, and, where a module defines "
             "<code>__all__</code>, only what it names there. Private symbols are omitted "
             "entirely — they are not API, so their absence is not a gap. "
             "Per <code>CLAUDE.md</code>, docstrings are not required outside public APIs, "
             "so <strong>no stub is emitted for an undocumented symbol</strong>; each is "
             "listed by name under <a href='#undocumented'>Deliberately undocumented</a> "
             "instead. Module docstrings: <strong>%d of %d</strong>.</div>"
             % (moddoc, len(modules)))

    if unparsed:
        o.append("<div class='note'><strong>%d file(s) could not be parsed</strong> and are "
                 "absent from everything below: %s</div>"
                 % (len(unparsed), ", ".join("<code>%s</code>" % e(f) for f, _ in unparsed)))

    # ---- the curated package API -----------------------------------------
    o.append("<h2 id='package'>Package API — <code>from sidm2 import ...</code></h2>")
    o.append("<p class='doc'>The %d names <code>sidm2/__init__.py</code> re-exports. This is "
             "the surface a caller outside the package is meant to use; everything in the "
             "module index below is reachable but not promoted.</p>" % len(exported))
    rows = []
    for m in modules:
        for s in m["symbols"]:
            if s["name"] in exported:
                rows.append((s["name"], m["name"], s["kind"], s["doc"]))
    o.append("<table><tr><th>name</th><th>module</th><th>kind</th><th>summary</th></tr>")
    for n, mod, kind, doc in sorted(rows):
        o.append("<tr><td><code>%s</code></td><td><code>%s</code></td><td>%s</td><td>%s</td></tr>"
                 % (e(n), e(mod), e(kind), e(doc or "—")))
    o.append("</table>")
    missing = sorted(exported - {r[0] for r in rows})
    if missing:
        o.append("<p class='doc'>%d re-exported name(s) resolve to a star-import or a "
                 "non-def symbol and have no entry above: %s</p>"
                 % (len(missing), ", ".join("<code>%s</code>" % e(x) for x in missing)))

    # ---- per-module ------------------------------------------------------
    o.append("<h2 id='modules'>Modules</h2>")
    for m in modules:
        if not m["symbols"]:
            continue
        o.append("<details><summary><code>sidm2.%s</code> — %d symbol(s)%s</summary>"
                 % (e(m["name"]), len(m["symbols"]),
                    " · declares <code>__all__</code>" if m["declares_all"] else ""))
        if m["doc"]:
            o.append("<p class='doc'>%s</p>" % e(m["doc"]))
        for s in m["symbols"]:
            o.append("<h3>%s</h3>" % e(s["name"]))
            o.append("<div class='sig'>%s</div>" % e(s["sig"]))
            if s["doc"]:
                o.append("<p class='doc'>%s</p>" % e(s["doc"]))
            for mn, msig, mdoc in s["methods"]:
                o.append("<div class='meth'><code>%s</code>%s</div>"
                         % (e(msig), (" — " + e(mdoc)) if mdoc else ""))
        o.append("</details>")

    # ---- the explicit gap ------------------------------------------------
    o.append("<h2 id='undocumented'>Deliberately undocumented</h2>")
    if not gaps:
        o.append("<p class='doc'>Every public symbol carries a docstring.</p>")
    else:
        o.append("<p class='doc'>%d of %d public symbols (%.1f%%) have no docstring. "
                 "They are listed rather than stubbed: an empty entry would read as "
                 "coverage. <code>CLAUDE.md</code> does not require docstrings outside "
                 "public APIs, so this is a list of candidates, not of defects.</p>"
                 % (len(gaps), pub, 100.0 * len(gaps) / pub if pub else 0.0))
        o.append("<div class='gap'>")
        for mod, name, kind in sorted(gaps):
            o.append("<code>sidm2.%s.%s</code>" % (e(mod), e(name)))
        o.append("</div>")

    o.append("</div></body></html>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="report and exit 1 if index.html is missing or stale; write nothing")
    a = ap.parse_args()

    modules, exported, unparsed = scan()
    doc = render(modules, exported, unparsed)
    pub = sum(len(m["symbols"]) for m in modules)
    docd = sum(1 for m in modules for s in m["symbols"] if s["doc"])

    print("scanned %d modules | %d public symbols | %d documented (%.1f%%) | %d re-exported"
          % (len(modules), pub, docd, 100.0 * docd / pub if pub else 0.0, len(exported)))
    if unparsed:
        print("  WARNING: %d file(s) failed to parse and are ABSENT from the output:" % len(unparsed))
        for f, err in unparsed:
            print("    %s: %s" % (f, err))

    if a.check:
        if not os.path.exists(OUT):
            print("  --check: %s does not exist" % os.path.relpath(OUT, ROOT))
            return 1
        cur = open(OUT, encoding="utf-8").read()
        # the date stamp changes daily; compare everything else
        strip = lambda s: "\n".join(l for l in s.splitlines() if "Generated " not in l)
        if strip(cur) != strip(doc):
            print("  --check: %s is STALE (regenerate)" % os.path.relpath(OUT, ROOT))
            return 1
        print("  --check: up to date")
        return 0

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print("wrote %s (%d bytes)" % (os.path.relpath(OUT, ROOT), len(doc.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
