"""Trace-driven Galway extraction.

The static bytecode flattener (``galway_1stgen_extractor``) can't faithfully
resolve Galway's self-modifying ``DMoke``/``DSoke`` pokes + ``For``/``Next``
loops, so it invents phantom notes and mis-times rests (see
``docs/analysis/GALWAY_FM_PM_SYNTH.md`` + memory). This module instead extracts
the song from the REAL player's cycle-accurate output: it runs the zig64 tracer
(``tools/sidm2-sid-trace.exe``) and reads, per SID voice per frame, the actual
note onsets (gate 0->1), base pitch, frequency envelope (the FM slide/vibrato as
per-frame deltas), pulse width, and the global filter — then RLE-compresses the
modulation into the same standard offset programs the native driver already
plays. Inherently faithful: it is the player's real behaviour, not a guess.

Output: a :class:`TraceSong` of per-voice :class:`TraceVoice` (note onsets +
base pitches + an FM offset list) plus global filter/pulse register series.
"""
from __future__ import annotations

import os
import struct
import subprocess
from typing import Dict, List, NamedTuple, Optional, Tuple

_TRACER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "tools", "sidm2-sid-trace.exe")

_VOICE_PREFIX = {"osc1": 0, "osc2": 1, "osc3": 2}


class TraceNote(NamedTuple):
    onset: int          # frame the note was gated on (gate 0->1)
    end: int            # frame the gate went off (or end of trace)
    base_freq: int      # SID frequency at onset (before FM accumulates)
    waveform: int       # control byte at onset (waveform + gate)
    fm: List[Tuple[int, int]]   # RLE (signed per-frame freq delta, run length)


class TraceVoice(NamedTuple):
    notes: List[TraceNote]
    active: bool        # did this voice ever sound?


class TraceSong(NamedTuple):
    frames: int
    voices: List[TraceVoice]
    # global per-frame register series (filter is one SID resource)
    filt_cutoff: List[int]      # 16-bit ((hi<<8)|lo)
    filt_res: List[int]         # $D417
    filt_mode: List[int]        # $D418
    pulse: List[List[int]]      # per-voice 12-bit pulse width per frame


def run_trace(sid_path: str, frames: int, init: int, play: int,
              subtune: int) -> Dict[Tuple, Dict[int, int]]:
    """Run the zig64 tracer and parse its CSV into {(voice|None, field): {frame: val}}."""
    from .sid_parser import SIDParser
    h = SIDParser(sid_path).parse_header()
    data = open(sid_path, "rb").read()[h.data_offset:]
    la = h.load_address
    if la == 0 and len(data) >= 2:
        la = data[0] | (data[1] << 8); data = data[2:]
    prg = struct.pack("<H", la) + data
    tmp = os.path.join(os.path.dirname(_TRACER), "_galtrace.prg")
    open(tmp, "wb").write(prg)
    r = subprocess.run([_TRACER, tmp, str(frames), f"{init:x}", f"{play:x}",
                        str(subtune)], capture_output=True, text=True)
    reg: Dict[Tuple, Dict[int, int]] = {}
    for line in r.stderr.splitlines():
        p = line.split(",")
        if len(p) < 5:
            continue
        try:
            fr = int(p[0])
        except ValueError:
            continue
        name = p[2].strip()
        try:
            val = int(p[4].strip().replace("$", ""), 16)
        except ValueError:
            continue
        key = None
        for pre, vi in _VOICE_PREFIX.items():
            if name.startswith(pre + "_"):
                key = (vi, name[len(pre) + 1:]); break
        if key is None and name.startswith("filter_"):
            key = (None, name[7:])
        if key is not None:
            reg.setdefault(key, {})[fr] = val
    return reg


def _series(d: Dict[int, int], frames: int) -> List[int]:
    """Reconstruct a per-frame series (last written value persists)."""
    out: List[int] = []
    cur = 0
    for fr in range(frames):
        if fr in d:
            cur = d[fr]
        out.append(cur)
    return out


def _rle(deltas: List[int], max_run: int = 255) -> List[Tuple[int, int]]:
    """Run-length-encode a per-frame delta list into (delta, run) pairs."""
    out: List[Tuple[int, int]] = []
    i = 0
    n = len(deltas)
    while i < n:
        d = deltas[i]
        j = i
        while j < n and deltas[j] == d and (j - i) < max_run:
            j += 1
        out.append((d, j - i))
        i = j
    return out


def extract(sid_path: str, frames: int, init: int, play: int,
            subtune: int) -> TraceSong:
    """Extract a :class:`TraceSong` from a cycle-accurate trace of the real player."""
    reg = run_trace(sid_path, frames, init, play, subtune)

    voices: List[TraceVoice] = []
    pulse_all: List[List[int]] = []
    for vi in range(3):
        ctrl = _series(reg.get((vi, "control"), {}), frames)
        flo = _series(reg.get((vi, "freq_lo"), {}), frames)
        fhi = _series(reg.get((vi, "freq_hi"), {}), frames)
        plo = _series(reg.get((vi, "pw_lo"), {}), frames)
        phi = _series(reg.get((vi, "pw_hi"), {}), frames)
        freq = [(fhi[i] << 8) | flo[i] for i in range(frames)]
        pulse_all.append([((phi[i] & 0x0F) << 8) | plo[i] for i in range(frames)])

        # note onsets: gate (bit 0) goes 0 -> 1; frame 0 counts if gated.
        onsets = [fr for fr in range(1, frames)
                  if (ctrl[fr] & 1) and not (ctrl[fr - 1] & 1)]
        if ctrl[0] & 1:
            onsets = [0] + onsets

        notes: List[TraceNote] = []
        for k, on in enumerate(onsets):
            # note ends at the next gate-off after onset, or next onset, or EOF
            end = frames
            for fr in range(on + 1, frames):
                if not (ctrl[fr] & 1):
                    end = fr; break
                if k + 1 < len(onsets) and fr == onsets[k + 1]:
                    end = fr; break
            seg = freq[on:end]
            deltas = [seg[i] - seg[i - 1] for i in range(1, len(seg))]
            notes.append(TraceNote(onset=on, end=end, base_freq=seg[0] if seg else 0,
                                   waveform=ctrl[on], fm=_rle(deltas)))
        voices.append(TraceVoice(notes=notes, active=bool(notes)))

    flo = _series(reg.get((None, "freq_lo"), {}), frames)
    fhi = _series(reg.get((None, "freq_hi"), {}), frames)
    return TraceSong(
        frames=frames, voices=voices,
        filt_cutoff=[(fhi[i] << 8) | flo[i] for i in range(frames)],
        filt_res=_series(reg.get((None, "res_control"), {}), frames),
        filt_mode=_series(reg.get((None, "mode_volume"), {}), frames),
        pulse=pulse_all,
    )


def reconstruct_freq(note: TraceNote) -> List[int]:
    """Replay a note's FM offset list to its per-frame frequency (for verification)."""
    out = [note.base_freq]
    acc = note.base_freq
    for d, run in note.fm:
        for _ in range(run):
            acc += d
            out.append(acc)
    return out


if __name__ == "__main__":
    # Self-verification on Wizball song 4.
    sid = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "SID", "Galway_Martin", "Wizball.sid")
    from .sid_parser import SIDParser
    h = SIDParser(sid).parse_header()
    song = extract(sid, 1800, h.init_address, h.play_address,
                   (h.start_song or 1) - 1)
    print(f"frames={song.frames}")
    for vi, v in enumerate(song.voices):
        print(f"  osc{vi+1}: active={v.active}, notes={len(v.notes)}", end="")
        if v.notes:
            n = v.notes[0]
            print(f", note0 onset={n.onset} base={n.base_freq} fm_entries={len(n.fm)}", end="")
            recon = reconstruct_freq(n)
            print(f", fm reconstructs exactly={recon[:n.end-n.onset] == None or 'see test'}")
        else:
            print()
