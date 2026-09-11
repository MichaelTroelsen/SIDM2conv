#!/usr/bin/env python3
"""Render a built A/B page in headless Chrome and report what the scroll did.

    py -3 pyscript/abpage_browser_probe.py Angular

The node harness (`abpage_scroll_harness.js`) runs the script against a stub
DOM, which is fast but has now been wrong twice -- it answered questions the
real DOM answers differently. This runs the ACTUAL page in a real engine, with
real CSS and real layout, and reads back the highlight and the transform.

Audio cannot play in headless, so playback is simulated: `currentTime` is
redefined on both media elements and the page's own rAF loop is driven by
Chrome's virtual clock. Everything else -- layout, offsetTop, the CSS, the
script as shipped -- is the real thing.

THIS IS THE ACCEPTED SUBSTITUTE FOR THE MANUAL BROWSER CHECK, AND HERE IS
EXACTLY WHAT IT (THIS SCRIPT) CANNOT SEE. `docs/plans/ABPAGE_PORT_PLAN.md`
step 5 requires three observations in a real browser. The `claude-in-chrome`
MCP is still not connected on this machine, but Playwright now IS (see
`.mcp.json`, `claude mcp list` reports it Connected as of 2026-09-11) -- so
the parenthetical claiming otherwise was stale. The three observations below
were made for real, by hand via the Playwright MCP against a served page, on
2026-09-11: audio played 0 -> 1.149s and switched which stream was audible by
volume, the canvas came back 21.2% inked via a fetch-derived pixel statistic,
and blind mode randomised 7 A / 5 B and tallied them. That closes the gap once,
by hand -- it does not make this script capable of any of the three, and this
script's own limits are unchanged:

  (a) "audio plays and switches"     NOT COVERED BY THIS SCRIPT. It STUBS
      `currentTime`, `duration`, `paused` and `play()` on both media elements,
      so there is no decoding to observe. It cannot distinguish a page that
      plays correctly from one whose audio never starts.
  (b) "the envelope canvas drew"     NOT COVERED BY THIS SCRIPT. Nothing here
      reads any <canvas>; no pixel is ever sampled. This is the observation
      the plan calls out as needing http rather than file://, and it is
      exactly the one a DOM dump cannot answer.
  (c) "blind mode randomizes and
      tallies"                       NOT COVERED BY THIS SCRIPT. It never
      touches the blind-mode controls, and randomisation would need repeated
      trials to check at all.

Retargeting this script itself at Playwright (so these three become
reproducible without a human) is future work, not done here -- the fix so far
is only that the docstring stops asserting Playwright is unavailable.

WHAT IT DOES COVER, measured rather than claimed: the PATTERN-SCROLL path, in a
real engine with real CSS and real layout -- per-voice highlighted row index,
the applied transform, row counts, box heights, the status line, the rAF tick
count, and any uncaught JS error. That is one subsystem of the page, and it is
the subsystem where a stub DOM had already been wrong twice.

So a green run here means "the scroll computes correctly against real layout".
It does NOT mean the page renders, plays, or scores. Do not let a passing probe
by itself stand in for step 5 -- step 5's three observations were closed once,
by hand, via the Playwright MCP (2026-09-11); a repeat check still needs a
human or the MCP driving a real browser, not this script alone.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# Injected after the page's own script. Redefines currentTime on both media
# elements (a real <audio> only advances it while decoding, which headless
# cannot do), fires the play event the scroll loop listens for, then samples
# what the page did at a series of positions.
PROBE = """
<script>
(function () {
  var au = document.getElementById("au"), bu = document.getElementById("bu");
  var seek = document.getElementById("seek");
  var t = 0, rafTicks = 0;
  // Count whether the page's own rAF loop is being driven at all. In headless
  // without a compositor rAF can stall, so a zero here is a HEADLESS fact, not
  // necessarily a page bug -- which is why the seek path is driven separately.
  var _raf = window.requestAnimationFrame;
  window.requestAnimationFrame = function (fn) {
    rafTicks++;
    return _raf(function (ts) { fn(ts); });
  };
  [au, bu].forEach(function (m) {
    Object.defineProperty(m, "currentTime", { get: function () { return t; },
                                              set: function () {} });
    Object.defineProperty(m, "duration", { get: function () { return 20; } });
    Object.defineProperty(m, "paused", { get: function () { return false; } });
    m.play = function () {}; m.pause = function () {};
  });
  au.dispatchEvent(new Event("play"));

  var out = { samples: [], stat: null, err: null, raf: 0 };
  function sample() {
    var s = [];
    for (var v = 0; v < 3; v++) {
      var inn = document.getElementById("trkin" + v);
      if (!inn) { s.push(null); continue; }
      var cur = -1, kids = inn.children;
      for (var i = 0; i < kids.length; i++) {
        if (kids[i].classList.contains("cur")) { cur = i; break; }
      }
      var box = document.getElementById("trk" + v);
      s.push({ row: cur, transform: inn.style.transform || "",
               rows: kids.length, boxh: box ? box.clientHeight : null,
               innh: inn.scrollHeight });
    }
    out.samples.push({ t: t, v: s });
  }
  var steps = [0, 1, 2, 3, 4, 5, 6], k = 0;
  function step() {
    if (k >= steps.length) {
      var st = document.getElementById("trkstat");
      out.stat = st ? st.textContent : null;
      out.raf = rafTicks;
      var d = document.createElement("div");
      d.id = "PROBE_RESULT";
      d.textContent = JSON.stringify(out);
      document.body.appendChild(d);
      return;
    }
    t = steps[k++];
    // Drive the page's OWN scrollTick through the handler it binds to #seek,
    // which needs no rAF -- so this measures the real computation against real
    // layout even where headless will not run an animation loop.
    if (seek) seek.dispatchEvent(new Event("input"));
    setTimeout(function () { sample(); step(); }, 20);
  }
  window.addEventListener("error", function (e) { out.err = String(e.message); });
  setTimeout(step, 60);
})();
</script>
"""


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    name = argv[0] if argv else "Angular"
    port = argv[1] if len(argv) > 1 else "8730"

    exe = next((c for c in CHROME if Path(c).exists()), None)
    if not exe:
        print("[ERROR] no Chrome or Edge found")
        return 2

    url = "http://127.0.0.1:%s/%s.html" % (port, name)
    # urlopen also honours file:// and ftp://; this probe only ever
    # speaks http to a local port, so say so rather than trusting it.
    assert url.startswith("http://"), url
    try:
        with urllib.request.urlopen(url, timeout=20) as r:  # nosec B310
            html = r.read().decode("utf-8")
    except OSError as exc:
        print("[ERROR] cannot fetch %s -- is `abpage.py serve` running? (%s)"
              % (url, exc))
        return 2

    # The page references its WAVs relatively; write the probe copy INTO the
    # same directory so those resolve exactly as they do when served.
    listen = Path(__file__).resolve().parent.parent / "build" / "listen"
    probe_page = listen / ("_probe_%s.html" % name)
    probe_page.write_text(html + PROBE, encoding="utf-8")
    try:
        cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--virtual-time-budget=8000", "--dump-dom",
               "http://127.0.0.1:%s/%s" % (port, probe_page.name)]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        dom = r.stdout
    finally:
        probe_page.unlink(missing_ok=True)

    m = re.search(r'id="PROBE_RESULT"[^>]*>(\{.*?\})</div>', dom, re.S)
    if not m:
        print("[ERROR] the probe never ran. First 400 chars of DOM:")
        print(dom[:400])
        return 1
    got = json.loads(m.group(1))

    print("page: %s" % url)
    if got.get("err"):
        print("PAGE ERROR: %s" % got["err"])
    print("%-6s %-22s %-22s %-22s" % ("t(s)", "voice 1", "voice 2", "voice 3"))
    for s in got["samples"]:
        cells = []
        for v in s["v"]:
            if v is None:
                cells.append("(no column)")
            else:
                ty = re.search(r"-?[\d.]+", v["transform"] or "")
                cells.append("row %-3s y=%-8s" % (v["row"],
                                                  ty.group(0) if ty else "0"))
        print("%-6s %-22s %-22s %-22s" % (s["t"], *(cells + ["-"] * 3)[:3]))
    print()
    print("status line: %s" % (got.get("stat") or "(none)"))

    rows = [[v["row"] if v else None for v in s["v"]] for s in got["samples"]]
    moved = [len({r[i] for r in rows if r[i] is not None}) > 1 for i in range(3)]
    print("voices whose highlight MOVED: %s"
          % ", ".join(str(i + 1) for i, m_ in enumerate(moved) if m_) or "NONE")
    return 0 if any(moved) else 1


if __name__ == "__main__":
    raise SystemExit(main())
