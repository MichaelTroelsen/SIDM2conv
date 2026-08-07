"""Validate the Matt Gray parser's note onsets against a real siddump.

Measurement ladder step 1 (see docs/players/PLAYBOOK.md §4): for every note the
parser predicts, assert the real player writes that exact 16-bit frequency on
that exact frame.

Two numbers are reported per voice, and they mean different things:

  onset match  -- the parser predicted a note on a frame where the real player
                  actually wrote $d400/$d401.  A miss means the *timing* model
                  is wrong.
  pitch match  -- of the matched onsets, the frequency written equals
                  freq_table[note].  A miss means the *note decode* is wrong.

Rests (note $00) are excluded from both: the driver restores the previous note
and only ANDs the gate bit out, so a rest writes no frequency at all.

Usage:
    py -3 bin/mattgray_validate.py <file.sid> [--subtune N] [--frames N]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.mattgray_parser import parse_sid, simulate  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SIDDUMP = os.path.join(_ROOT, "pyscript", "siddump_complete.py")


def run_siddump(sid: str, seconds: int, subtune: int) -> dict:
    """Return {voice: {frame: freq}} for every frame the player writes a freq."""
    # -w/--written is REQUIRED here.  siddump's default display prints "...."
    # for a register whose *value* did not change, which hides a genuine write
    # whenever the player re-triggers the same note twice in a row (Driller's
    # pattern 6 does exactly that: "42 3b 3b 42 3b 3b").  Without -w those
    # onsets look like parser errors when the parser is in fact correct.
    cmd = [sys.executable, _SIDDUMP, sid, f"-t{seconds}", "-w"]
    if subtune:
        cmd.append(f"-a{subtune}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"siddump failed:\n{res.stderr[:2000]}")

    out = {0: {}, 1: {}, 2: {}}
    for line in res.stdout.splitlines():
        if not line.startswith("|") or "Frame" in line:
            continue
        cells = [c.strip() for c in line.strip("|\n").split("|")]
        if len(cells) < 4:
            continue
        try:
            frame = int(cells[0])
        except ValueError:
            continue
        for vi in range(3):
            fields = cells[1 + vi].split()
            if not fields:
                continue
            freq = fields[0]
            if freq == "....":
                continue
            try:
                out[vi][frame] = int(freq, 16)
            except ValueError:
                pass
    return out


def validate(sid: str, subtune: int, frames: int) -> int:
    song = parse_sid(sid, subtune=subtune)
    events = simulate(song, frames=frames)
    seconds = max(1, frames // 50 + 1)
    dump = run_siddump(sid, seconds, subtune)

    print(f"{os.path.basename(sid)}  subtune {subtune}  "
          f"tempo {song.tempo} ({song.frames_per_tick} frames/tick)  "
          f"{len(song.patterns)} patterns  {len(song.instruments)} instruments")
    print(f"play_voice ${song.play_voice:04x}  "
          + "  ".join(f"{k}=${v:04x}" for k, v in song.table_addrs.items()
                      if k != "play_voice"))
    print()

    modulated = {i.index for i in song.instruments if _is_modulated(i)}
    print(f"instruments: {len(song.instruments) - len(modulated)} plain, "
          f"{len(modulated)} pitch-modulated "
          f"(slide / auto-effect / arpeggio / drum path)")
    print("Headline = PLAIN instruments only.  On a pitch-modulated instrument "
          "the player\nrewrites $d400 every frame, so an onset there matches "
          "whatever the parser predicts;\nthat bucket cannot falsify the "
          "timing model and is reported separately, not claimed.")
    print()

    tot = {"plain": [0, 0, 0], "mod": [0, 0, 0]}   # [notes, onset_ok, pitch_ok]
    for vi in range(3):
        notes = [e for e in events[vi] if not e.is_rest and e.frame < frames]
        rests = [e for e in events[vi] if e.is_rest and e.frame < frames]
        buckets = {"plain": [], "mod": []}
        for e in notes:
            # A note is pitch-modulated if its INSTRUMENT modulates pitch, or
            # if a $fb/$fc slide command in the pattern stream applies to it.
            is_mod = e.instrument in modulated or e.slide is not None
            buckets["mod" if is_mod else "plain"].append(e)

        line = [f"voice{vi + 1}: {len(notes):4d} notes "
                f"({len(rests)} rests excluded)"]
        detail = []
        for key in ("plain", "mod"):
            grp = buckets[key]
            on_ok = pitch_ok = 0
            bad = []
            for e in grp:
                got = dump[vi].get(e.frame)
                if got is None:
                    bad.append((e, None))
                    continue
                on_ok += 1
                if got == song.freq(e.note):
                    pitch_ok += 1
                else:
                    bad.append((e, got))
            n = len(grp)
            tot[key][0] += n
            tot[key][1] += on_ok
            tot[key][2] += pitch_ok
            line.append(
                f"  {key:5s} n={n:4d} onset {_pct(on_ok, n)} "
                f"pitch {_pct(pitch_ok, on_ok)}")
            if key == "plain":
                for e, got in bad[:4]:
                    gs = "no freq write" if got is None else f"${got:04x}"
                    detail.append(
                        f"    MISS frame {e.frame:5d} pat {e.pattern:3d} "
                        f"note ${e.note:02x} instr {e.instrument:2d}: "
                        f"want ${song.freq(e.note):04x}, got {gs}")
                if len(bad) > 4:
                    detail.append(f"    ... and {len(bad) - 4} more")
        print("\n".join(line))
        print("\n".join(detail)) if detail else None

    print()
    pn, pon, ppi = tot["plain"]
    mn, mon, mpi = tot["mod"]
    if pn == 0:
        print("NO PLAIN-INSTRUMENT NOTES -- nothing falsifiable was measured")
        return 1
    print(f"HEADLINE (plain instruments, n={pn}): "
          f"onset {_pct(pon, pn)}  pitch {_pct(ppi, pon)}")
    print(f"  informational (pitch-modulated, n={mn}): "
          f"onset {_pct(mon, mn)}  pitch-vs-base {_pct(mpi, mon)}  "
          f"-- base-pitch mismatch here is the synth side (Stage B), not a "
          f"sequencer error")
    return 0 if (pon == pn and ppi == pon) else 1


def _pct(ok: int, n: int) -> str:
    if n == 0:
        return "   n/a "
    return f"{ok}/{n} = {100.0 * ok / n:6.2f}%"


def _is_modulated(instr) -> bool:
    """True if this instrument moves the pitch away from the freq-table value.

    Any of these makes the frequency at a note's own onset frame -- or on the
    frames after it -- something other than freq_table[note]:
      A0[5] arpeggio, A0[7] bit0 drum/effect path,
      A1[0] automatic slide, A1[4] auto-started slide effect.
    """
    return bool(instr.arp_ctrl or (instr.flags & 0x01)
                or instr.slide_rate or instr.auto_effect)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sid")
    ap.add_argument("--subtune", type=int, default=1)
    ap.add_argument("--frames", type=int, default=3000)
    args = ap.parse_args()
    return validate(args.sid, args.subtune, args.frames)


if __name__ == "__main__":
    raise SystemExit(main())
