"""Build EVERY validating Hubbard v1 subsong -> native SF2 parts.

For each corpus file: sweep all PSID songs, keep those whose parser decode
matches the siddump trace (>=95% onsets, >=15 real onsets — filters out the
1-2s game SFX subsongs), and run the native build for each. Compilation rips
(multiple embedded players, e.g. 5_Title_Tunes) resolve PSID song -> module
automatically inside build_hubbard_native_song.

  py -3 bin/hubbard_build_all.py [--dry]   (builds are SEQUENTIAL — the
                                            drivers_src scratch is shared)
"""
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.hubbard_parser import (HubbardModule, decode_song, load_sid,
                                  detect_module_map)
from sidm2.fidelity_common import siddump_note_onsets

FILES = ['Monty_on_the_Run', 'Commando', 'Crazy_Comets', 'Zoids', 'Gremlins',
         'Master_of_Magic', 'One_Man_and_his_Droid', 'Last_V8',
         'Geoff_Capes_Strongman_Challenge', '5_Title_Tunes', 'Chimera',
         'Last_V8_C128_version',
         # v2 split-songs class + widened freq sig (parser upgrade 2026-07-07)
         'Action_Biker', 'Confuzion', 'Devils_Galop', 'Gerry_the_Germ',
         'Hunter_Patrol', 'I_Ball', 'Ninja', 'Thing_on_a_Spring']
MIN_ONSETS = 8            # below this = game SFX, not music
MIN_PCT = 95.0
ALWAYS_S0 = True          # song 0 of every corpus file is already metric-proven
                          # at 100.0 — short -t15 windows under-score slow intros
DRY = '--dry' in sys.argv


def validate(path, d, la, h, song, n_mod, mm):
    if n_mod > 1:
        m = HubbardModule(d, la, module=mm.get(song, 0))
        dsong = 0
    else:
        m = HubbardModule(d, la)
        dsong = song
    voices, _ = decode_song(m, dsong)
    fpt = m.frames_per_tick
    real = siddump_note_onsets(path, [f'-a{song}', '-t15'])
    rf = [set(fr for fr, _ in (real[v] if isinstance(real, (list, tuple))
                               else real.get(v, [])) if fr < 700)
          for v in range(3)]
    nall = sum(len(x) for x in rf)
    if nall < MIN_ONSETS:
        return None, nall, 0.0
    pf = [set(tk * fpt for tk, n in voices[v]
              if not n.append and n.pitch >= 0) for v in range(3)]
    best = max(sum(len(rf[v] & set(fr + ph for fr in pf[v] if fr + ph < 700))
                   for v in range(3)) for ph in range(6))
    return best, nall, 100.0 * best / nall


def main():
    built, skipped, failed = [], [], []
    for name in FILES:
        path = f'SID/Hubbard_Rob/{name}.sid'
        raw = open(path, 'rb').read()
        nsongs = struct.unpack('>H', raw[0x0E:0x10])[0]
        d, la, h = load_sid(path)
        n_mod = HubbardModule.module_count(d)
        mm = detect_module_map(d, la, h.init_address, nsongs) if n_mod > 1 else {}
        print(f'##### {name}: {nsongs} psid songs, {n_mod} module(s)')
        for s in range(nsongs):
            try:
                hit, nall, pct = validate(path, d, la, h, s, n_mod, mm)
            except Exception as e:
                skipped.append((name, s, f'decode: {str(e)[:40]}'))
                continue
            force = ALWAYS_S0 and s == 0
            if hit is None and not force:
                skipped.append((name, s, f'sfx ({nall} onsets)'))
                continue
            if not force and pct < MIN_PCT:
                skipped.append((name, s, f'{pct:.0f}% ({hit}/{nall})'))
                print(f'  s{s}: SKIP {pct:.0f}% ({hit}/{nall})')
                continue
            print(f'  s{s}: {pct:.0f}% ({hit}/{nall}) -> build')
            if DRY:
                built.append((name, s))
                continue
            r = subprocess.run(
                [sys.executable, 'bin/build_hubbard_native_song.py',
                 path, str(s), 'auto'],
                capture_output=True, text=True, timeout=5400)
            tail = (r.stdout or '').strip().splitlines()
            print('   ', tail[-1] if tail else '(no output)')
            if r.returncode != 0:
                failed.append((name, s, (r.stderr or '')[-200:]))
            else:
                built.append((name, s))
    print(f'\nBUILT {len(built)} subsongs; skipped {len(skipped)}; '
          f'failed {len(failed)}')
    for name, s, why in failed:
        print(f'  FAIL {name} s{s}: {why}')


if __name__ == '__main__':
    main()
