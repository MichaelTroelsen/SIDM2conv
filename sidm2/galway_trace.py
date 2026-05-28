"""Cycle-accurate trace helpers for Galway (and other) SID files, via the
rebuilt zig64 tracer `tools/sidm2-sid-trace.exe`.

The tracer plays a SID through a full PAL C64 (VIC raster works, so Galway's
raster-synced player advances) and emits per-frame SID register changes as
CSV on stderr. This module wraps it and derives the **instrument palette**
directly from what the song actually writes to the SID — universal across
all player variants, no per-game Dn-layout RE required.

(For the musical *score* — note + duration per voice — use the static
`galway_1stgen_extractor.flatten_channel`; the trace is best for the
instrument palette because Galway's portamento blurs note onsets.)
"""
from __future__ import annotations

import os
import struct
import subprocess
import tempfile
from typing import List, NamedTuple, Optional

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TRACER = os.path.join(_REPO, "tools", "sidm2-sid-trace.exe")

_WAVEFORMS = [(0x10, "triangle"), (0x20, "sawtooth"),
              (0x40, "pulse"), (0x80, "noise")]


class TraceInstrument(NamedTuple):
    """A distinct instrument the song actually played, observed on the SID."""
    voice: int            # 1..3
    ctrl: int             # waveform control nibble(s), $D404 high bits
    ad: int               # attack/decay ($D405)
    sr: int               # sustain/release ($D406)
    waveforms: tuple


def run_sid_trace(c64_data: bytes, load_addr: int, init: int, play: int,
                  subtune: int = 0, frames: int = 1500,
                  tracer: Optional[str] = None) -> Optional[str]:
    """Run the tracer and return its CSV text (stderr), or None if the tracer
    is missing / failed. Writes a temporary .prg (load word + data)."""
    tracer = tracer or _TRACER
    if not os.path.exists(tracer):
        return None
    fd, prg = tempfile.mkstemp(suffix=".prg")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(struct.pack("<H", load_addr) + c64_data)
        r = subprocess.run(
            [tracer, prg, str(frames), "%04x" % init, "%04x" % play,
             str(subtune)],
            capture_output=True, text=True, timeout=120)
        return r.stderr
    except (subprocess.SubprocessError, OSError):
        return None
    finally:
        try:
            os.remove(prg)
        except OSError:
            pass


def instrument_palette_from_trace(csv_text: str) -> List[TraceInstrument]:
    """Parse the tracer CSV into the distinct per-voice instruments played.

    An instrument is the (waveform, AD, SR) state of a voice; collected each
    time the voice has a real waveform selected. Ordered by first appearance.
    """
    cur = {1: [0, 0, 0], 2: [0, 0, 0], 3: [0, 0, 0]}   # [ctrl_wave, ad, sr]
    out: List[TraceInstrument] = []
    seen = set()
    for line in csv_text.splitlines():
        p = line.split(",")
        if len(p) != 5 or p[0] == "frame":
            continue
        reg = p[2]
        try:
            val = int(p[4].lstrip("$"), 16)
        except ValueError:
            continue
        for v in (1, 2, 3):
            if reg == "osc%d_control" % v:
                cur[v][0] = val & 0xF0
            elif reg == "osc%d_attack_decay" % v:
                cur[v][1] = val
            elif reg == "osc%d_sustain_release" % v:
                cur[v][2] = val
            else:
                continue
            wave, ad, sr = cur[v]
            if not wave:                 # no real oscillator output yet
                break
            key = (v, wave, ad, sr)
            if key not in seen:
                seen.add(key)
                waves = tuple(n for bit, n in _WAVEFORMS if wave & bit)
                out.append(TraceInstrument(v, wave, ad, sr, waves))
            break
    return out
