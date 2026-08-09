#!/usr/bin/env python3
"""Cross-reference what the HardTrack player's own code does with each field.

The instrument record is 13 parallel tables. Which field means what is settled
by reading the CONSUMER, not by asking whether the stored bytes look plausible
-- a plausibility check passed BOTH readings of the swapped fields 3/4 and so
discriminated nothing (docs/players/HARDTRACK.md, falsified hypothesis 4).

This tool re-derives three structural facts about the player from the binaries,
so the figures quoted in the docs can be regenerated from a fresh clone:

  reads     every one of the 13 fields is read by the player -- none is
            editor-only storage -- and field 5 is read exactly three times
  masks     field 5 is only ever masked with $03, $10 and $80, so bits
            2, 5 and 6 are dead and bit 4 has exactly one consumer
  slide     the $63/$64 slide-active byte has exactly three stores: the two
            command handlers, plus one `LDA #$00` clear in the note-on reset

Usage:  py -3 pyscript/hardtrack_player_xref.py [SID_DIR] [--verbose]
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.hardtrack_parser import HardTrackModule, INSTRUMENT_FIELDS  # noqa: E402
from pyscript.disasm6502 import Disassembler6502                       # noqa: E402

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'SID', 'Shogoon')

LDA_ABS_Y = 0xB9
STA_ABS_X = 0x9D
LDA_IMM = 0xA9
AND_IMM = 0x29
CMD_SLIDE_UP = 0x63

FIELD5_MASKS = frozenset({0x03, 0x10, 0x80})


def modules(sid_dir: str):
    for p in sorted(glob.glob(os.path.join(sid_dir, '*.sid'))):
        try:
            yield p, HardTrackModule.from_sid(p)
        except Exception:          # refused rips are deliberate; skip quietly
            continue


def field_reads(m: HardTrackModule) -> dict[int, list[int]]:
    """field index -> offsets of every `lda FIELD,y` in the player."""
    tabs = {m.instrument_base + f * m.num_instruments: f
            for f in range(INSTRUMENT_FIELDS)}
    out: dict[int, list[int]] = {f: [] for f in range(INSTRUMENT_FIELDS)}
    d = m.data
    for i in range(len(d) - 2):
        if d[i] != LDA_ABS_Y:
            continue
        f = tabs.get(d[i + 1] | d[i + 2] << 8)
        if f is not None:
            out[f].append(i)
    return out


def field5_masks(m: HardTrackModule, reads: list[int]) -> list[int | None]:
    d = m.data
    return [d[i + 4] if d[i + 3] == AND_IMM else None for i in reads]


def slide_state(m: HardTrackModule) -> tuple[int | None, list[int], list[int]]:
    """(slide-active address, every store to it, those that store zero)."""
    d, load = m.data, m.load
    i = d.find(bytes([0xC9, CMD_SLIDE_UP]))
    if i < 0:
        return None, [], []
    dis = Disassembler6502(d, load, len(d))
    a, act = load + i, None
    for _ in range(8):
        ln = dis.disassemble_instruction(a)
        if ln is None:
            break
        if ln.bytes[0] == STA_ABS_X:
            act = ln.bytes[1] | ln.bytes[2] << 8
            break
        a += max(1, len(ln.bytes))
    if act is None:
        return None, [], []
    stores = [j for j in range(3, len(d) - 3)
              if d[j] == STA_ABS_X and (d[j + 1] | d[j + 2] << 8) == act]
    clears = []
    for j in stores:
        k = j
        while k >= 3 and d[k - 3] == STA_ABS_X:   # a run of sta abs,x shares one lda
            k -= 3
        if k >= 2 and d[k - 2] == LDA_IMM and d[k - 1] == 0x00:
            clears.append(j)
    return act, stores, clears


def main(argv: list[str]) -> int:
    sid_dir = next((a for a in argv[1:] if not a.startswith('-')), DEFAULT_DIR)
    verbose = '--verbose' in argv or '-v' in argv

    total = 0
    bad_reads, bad_masks, bad_slide = [], [], []
    for path, m in modules(sid_dir):
        total += 1
        name = os.path.basename(path)[:-4]
        reads = field_reads(m)

        want = {f: 1 for f in range(INSTRUMENT_FIELDS)}
        want[5] = 3
        if {f: len(v) for f, v in reads.items()} != want:
            bad_reads.append((name, {f: len(v) for f, v in reads.items()}))

        masks = field5_masks(m, reads[5])
        if set(masks) != FIELD5_MASKS:
            bad_masks.append((name, masks))

        act, stores, clears = slide_state(m)
        if act is None or len(stores) != 3 or len(clears) != 1:
            bad_slide.append((name, act, len(stores), len(clears)))

        if verbose:
            print('%-30s n=%2d base=$%04x  slide=$%04x stores=%d clear=%s  f5 masks=%s'
                  % (name, m.num_instruments, m.instrument_base, act or 0, len(stores),
                     '$%04x' % (m.load + clears[0]) if clears else '-',
                     ' '.join('$%02X' % x if x is not None else '??' for x in masks)))

    print('\n%d decodable modules in %s' % (total, sid_dir))
    for label, rows in (('every field read exactly once (field 5: 3x)', bad_reads),
                        ('field 5 masked only with $03/$10/$80', bad_masks),
                        ('slide byte: 2 handlers + 1 note-on clear', bad_slide)):
        print('  %-44s %s' % (label, 'OK %d/%d' % (total - len(rows), total)))
        for r in rows:
            print('      *** %s' % (r,))
    return 1 if (bad_reads or bad_masks or bad_slide) else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
