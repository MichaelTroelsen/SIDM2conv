"""Convert each SID in the test set, then drive SIDFactoryII F10-load
N times per file. Print per-file PASS/CRASH summary and totals.

Usage:  py -3 pyscript/sf2_corpus_pass_rate.py [N=5]

The list is hard-coded — picked to span every driver class previously
exercised (Laxity NewPlayer v21 root, Galway, Hubbard, Tel_Jeroen,
Laxity SF2-exported, Fun_Fun) so we can confirm the Block 3
TextFieldSize fix generalises beyond Stinsen + Unboxed.
"""
import os, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'pyscript'))
import sf2_load_test as h

CONVERTER = ROOT / 'scripts' / 'sid_to_sf2.py'

CORPUS = [
    # Laxity NP21 root (the original reference corpus)
    'SID/Stinsens_Last_Night_of_89.sid',
    'SID/Unboxed_Ending_8580.sid',
    'SID/Angular.sid',
    'SID/Beast.sid',
    'SID/Cycles.sid',
    'SID/Colorama.sid',
    'SID/Phoenix_Code_End_Tune.sid',
    # Other driver classes
    'SID/Galway_Martin/Arkanoid.sid',
    'SID/Hubbard_Rob/Action_Biker.sid',
    'SID/Tel_Jeroen/11_Heaven.sid',
    'SID/Fun_Fun/Byte_Bite.sid',
]


def convert(sid: Path, sf2: Path) -> bool:
    # Clear stale output to avoid the converter's overwrite-refusal.
    sf2_txt = sf2.with_suffix('.txt')
    for p in (sf2, sf2_txt):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    rc = subprocess.run(
        [sys.executable, str(CONVERTER), str(sid), str(sf2), '-q'],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return rc.returncode == 0


def main(argv):
    N = int(argv[0]) if argv else 5
    results = []
    bin_dir = ROOT / 'bin'
    for rel in CORPUS:
        sid = ROOT / rel
        if not sid.exists():
            print(f'MISSING: {rel}'); continue
        sf2 = bin_dir / f'_corpus_{sid.stem[:30]}.sf2'
        print(f'\n=== {rel} ===')
        if not convert(sid, sf2):
            print(f'  CONVERT FAILED'); continue
        size_kb = sf2.stat().st_size // 1024
        print(f'  converted -> {sf2.name} ({size_kb} KB)')

        ok = crash = other = 0
        for i in range(1, N + 1):
            r = h.test_one(str(sf2))
            v = r['verdict']
            print(f'  trial {i}: {v}', flush=True)
            if v == 'PASS': ok += 1
            elif v == 'CRASH': crash += 1
            else: other += 1
        results.append((rel, ok, crash, other, N))

    print('\n\n========== summary ==========')
    print(f'{"file":<50s} {"PASS":>6s} {"CRASH":>6s} {"OTHER":>6s} {"rate":>6s}')
    total_p = total_c = total_o = total_n = 0
    for rel, ok, crash, other, n in results:
        rate = f'{100*ok/n:.0f}%'
        print(f'{rel:<50s} {ok:>6d} {crash:>6d} {other:>6d} {rate:>6s}')
        total_p += ok; total_c += crash; total_o += other; total_n += n
    overall = f'{100*total_p/total_n:.0f}%' if total_n else 'n/a'
    print(f'{"TOTAL":<50s} {total_p:>6d} {total_c:>6d} {total_o:>6d} {overall:>6s}')


if __name__ == '__main__':
    main(sys.argv[1:])
