"""For a batch of Laxity NP21 SIDs, report whether each one:
  (A) Has valid ch_seq_ptr in binary (SF2-exported / pre-populated case);
      _build_np21_sf2_edit_area extracts real per-voice sequences directly.
  (B) Has invalid ch_seq_ptr but the LaxityPlayerAnalyzer extracts real
      orderlists + sequences from the player code.
  (C) Both ch_seq_ptr AND analyzer fail (Angular / Beast class).

Class A files get a useful editor view today. Class B files get a placeholder.
Class C files get a placeholder.

Usage: py -3 pyscript/probe_multipattern.py SID/Laxity/*.sid
"""
import logging, sys, traceback
from pathlib import Path

logging.basicConfig(level=logging.ERROR)  # quiet the analyzer
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.laxity_analyzer import LaxityPlayerAnalyzer

CH_SEQ_LO = 0x0A1C
CH_SEQ_HI = 0x0A1F


def parse_psid(path):
    buf = open(path, 'rb').read()
    data_off = (buf[6] << 8) | buf[7]
    psid_load = (buf[8] << 8) | buf[9]
    init_addr = (buf[10] << 8) | buf[11]
    play_addr = (buf[12] << 8) | buf[13]
    if psid_load == 0:
        psid_load = buf[data_off] | (buf[data_off + 1] << 8)
        c64 = buf[data_off + 2:]
    else:
        c64 = buf[data_off:]
    return psid_load, init_addr, play_addr, c64


def ch_seq_ptr_valid(c64, sid_la):
    """Returns True if at least one ch_seq_ptr points inside c64_data."""
    for v in range(3):
        if CH_SEQ_LO + v >= len(c64) or CH_SEQ_HI + v >= len(c64):
            continue
        seq = (c64[CH_SEQ_HI + v] << 8) | c64[CH_SEQ_LO + v]
        if sid_la <= seq < sid_la + len(c64):
            return True
    return False


def classify(path):
    try:
        sid_la, init, play, c64 = parse_psid(path)
    except Exception as e:
        return 'PARSE_ERR', str(e)

    has_chseq = ch_seq_ptr_valid(c64, sid_la)

    # Try the analyzer
    n_seq = 0; n_ol = 0; ol_lens = []
    try:
        # The analyzer expects a header; build a minimal one
        class H: pass
        h = H()
        h.init_address = init; h.play_address = play
        h.name = h.author = h.copyright = ''
        h.data_size = len(c64)
        a = LaxityPlayerAnalyzer(c64, sid_la, h)
        ext = a.extract_music_data()
        n_seq = len(ext.sequences) if ext.sequences else 0
        n_ol  = len(ext.orderlists) if ext.orderlists else 0
        ol_lens = [len(ol) for ol in (ext.orderlists or [])]
    except Exception as e:
        return 'ANLZ_ERR', f'{e}'

    if has_chseq:
        cls = 'A'   # ch_seq_ptr valid
    elif n_seq >= 1:
        cls = 'B'   # analyzer recovered sequences
    else:
        cls = 'C'   # empty-patterns fallback

    return cls, f'sid_la=${sid_la:04X}  ch_seq={"y" if has_chseq else "n"}  seq={n_seq}  ol_lens={ol_lens}'


def main(paths):
    counts = {'A': 0, 'B': 0, 'C': 0, 'PARSE_ERR': 0, 'ANLZ_ERR': 0}
    rows = []
    for p in paths:
        cls, info = classify(p)
        counts[cls] = counts.get(cls, 0) + 1
        rows.append((cls, Path(p).name, info))

    rows.sort()
    for cls, name, info in rows:
        print(f'  [{cls}] {name:<45s}  {info}')
    print(f'\n=== summary  ({len(rows)} files) ===')
    for cls, label in [
        ('A', 'ch_seq_ptr valid (real editor view today)'),
        ('B', 'analyzer recovered (would benefit from new path)'),
        ('C', 'empty-patterns fallback (placeholder editor view)'),
        ('PARSE_ERR', 'PSID parse failed'),
        ('ANLZ_ERR', 'analyzer crashed'),
    ]:
        if counts.get(cls, 0):
            print(f'  {cls}: {counts[cls]:>4d}  — {label}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
