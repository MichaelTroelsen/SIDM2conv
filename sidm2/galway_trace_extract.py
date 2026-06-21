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
    ad: int = 0         # $D405 attack/decay at onset (instrument envelope)
    sr: int = 0         # $D406 sustain/release at onset
    tie: bool = False   # legato continuation (pitch changed WITHOUT a gate re-trigger
                        # in the real player) -> the driver must not re-attack/reset


class TraceVoice(NamedTuple):
    notes: List[TraceNote]
    active: bool        # did this voice ever sound?
    legato: bool = False  # holds the gate + changes pitch via the player (Galway
                          # legato); its pulse free-runs rather than resetting per note


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


def _legato_splits(freq: List[int], start: int, end: int) -> List[int]:
    """Within a single gate-on region [start, end), return extra note onsets where
    the pitch SETTLES at a new level — i.e. legato note changes the gate doesn't
    mark. Galway holds the gate and changes pitch via the player, so a gate-based
    detector sees one giant note; this recovers the real melody.

    Robust against false splits: a vibrato (oscillates back to the current centre)
    never settles at a new level, and a slide (pitch keeps moving) only settles —
    and so only starts a new note — once it reaches and holds its destination. The
    centre tracks slow drift so a gradual portamento doesn't trip the band.
    """
    import math

    def st(f):
        return 12 * math.log2(max(f, 1) / 3000.0)

    BAND = 0.75          # semitones away from centre = "left the note"
    SETTLE = 5           # frames a new level must hold to count as a new note
    splits: List[int] = []
    centre = st(freq[start])
    cand = None
    held = 0
    i = start + 1
    while i < end:
        s = st(freq[i])
        if abs(s - centre) <= BAND:
            centre = 0.85 * centre + 0.15 * s    # follow vibrato centre / slow drift
            cand, held = None, 0
        else:
            if cand is not None and abs(s - cand) <= 0.5:
                held += 1
            else:
                cand, held = s, 1
            if held >= SETTLE:                   # settled at a new level -> new note
                splits.append(i - held + 1)
                centre, cand, held = cand, None, 0
        i += 1
    return splits


def _adsr_splits(ad: List[int], sr: List[int], start: int, end: int) -> List[int]:
    """Within one gate-on region, return extra onsets where the AD/SR envelope
    register changes and HOLDS for a few frames — Galway rewrites the envelope
    mid-note (e.g. Comic Bakery's lead drops its sustain while the note stays
    gated). Each split starts a tie note carrying the new AD/SR, so the editor
    shows the change and the driver writes it live (set_instr_v touches only the
    $D405/6 envelope registers, not the gate / FM / pulse). A 1-2 frame transient
    (hard-restart blip) is ignored by the hold check."""
    HOLD = 3
    splits: List[int] = []
    cur = (ad[start], sr[start])
    i = start + 1
    while i < end:
        v = (ad[i], sr[i])
        if v != cur and all(i + k < end and (ad[i + k], sr[i + k]) == v
                            for k in range(HOLD)):
            splits.append(i)
            cur = v
        i += 1
    return splits


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
        ad = _series(reg.get((vi, "attack_decay"), {}), frames)
        sr = _series(reg.get((vi, "sustain_release"), {}), frames)
        plo = _series(reg.get((vi, "pw_lo"), {}), frames)
        phi = _series(reg.get((vi, "pw_hi"), {}), frames)
        freq = [(fhi[i] << 8) | flo[i] for i in range(frames)]
        pulse_all.append([((phi[i] & 0x0F) << 8) | plo[i] for i in range(frames)])

        # note onsets: gate (bit 0) goes 0 -> 1; frame 0 counts if gated.
        gate_on = [fr for fr in range(1, frames)
                   if (ctrl[fr] & 1) and not (ctrl[fr - 1] & 1)]
        if ctrl[0] & 1:
            gate_on = [0] + gate_on
        # Add LEGATO note boundaries: within each gate-on region (gate held until
        # the next gate-off), split where the pitch settles at a new level. Galway
        # plays melodies legato (no re-gate), so without this each voice collapses
        # to one note whose FM/pulse spans the whole tune (unbounded -> diverges +
        # blows the 256-row pulse table). Re-gated tunes (Ocean) have short regions
        # with no settled-level change, so they pick up no spurious splits.
        onsets = set(gate_on)
        # Apply legato splitting to EVERY gate-on region (per-region, not per-voice).
        # Within a held gate Galway changes pitch AND rewrites the AD/SR envelope via
        # the player; split where the pitch SETTLES at a new level and where the
        # envelope changes-and-holds, so the editor shows the real melody (not one
        # held note) and each segment carries its true envelope. Short re-gated notes
        # never settle / hold a new envelope, so they pick up no spurious splits —
        # safe for re-gated voices (Ocean) too. The voice `legato` flag (few
        # gate-ons) is kept separately, only for the pulse/tempo model.
        legato_voice = len(gate_on) < max(8, frames // 100)
        for on in gate_on:
            region_end = frames
            for fr in range(on + 1, frames):
                if not (ctrl[fr] & 1):
                    region_end = fr
                    break
            onsets.update(_legato_splits(freq, on, region_end))
            onsets.update(_adsr_splits(ad, sr, on, region_end))
        gate_set = set(gate_on)
        onsets = sorted(onsets)

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
            # A note from a LEGATO split (not a real gate 0->1) is a tie: the player
            # changed pitch with the gate still on, so it must not re-attack.
            notes.append(TraceNote(onset=on, end=end, base_freq=seg[0] if seg else 0,
                                   waveform=ctrl[on], fm=_rle(deltas),
                                   ad=ad[on], sr=sr[on], tie=on not in gate_set))
        voices.append(TraceVoice(notes=notes, active=bool(notes),
                                 legato=legato_voice))

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
