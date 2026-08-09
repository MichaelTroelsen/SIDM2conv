"""Pin the structural facts hardtrack_player_xref.py asserts about the player."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.hardtrack_parser import HardTrackModule, INSTRUMENT_FIELDS  # noqa: E402
from pyscript.hardtrack_player_xref import (                          # noqa: E402
    DEFAULT_DIR, FIELD5_MASKS, field5_masks, field_reads, modules, slide_state,
)

CORPUS = list(modules(DEFAULT_DIR))
IDS = [os.path.basename(p)[:-4] for p, _ in CORPUS]


def test_corpus_is_present():
    # SID/Shogoon/ is tracked, so this runs from a fresh clone.
    assert len(CORPUS) == 33


@pytest.mark.parametrize('path,mod', CORPUS, ids=IDS)
def test_every_instrument_field_is_read_by_the_player(path, mod):
    # None of the 13 fields is editor-only storage: each is loaded by the
    # player exactly once, and field 5 (the flag byte) three times.
    counts = {f: len(v) for f, v in field_reads(mod).items()}
    assert counts == {**{f: 1 for f in range(INSTRUMENT_FIELDS)}, 5: 3}


@pytest.mark.parametrize('path,mod', CORPUS, ids=IDS)
def test_field5_uses_only_three_bits(path, mod):
    # $80 program-drives-frequency, $10 filter re-arm suppression, $03 mode.
    # Bits 2, 5 and 6 are never consulted -- do not invent meanings for them.
    assert set(field5_masks(mod, field_reads(mod)[5])) == FIELD5_MASKS


@pytest.mark.parametrize('path,mod', CORPUS, ids=IDS)
def test_slide_is_cleared_by_the_next_note_on(path, mod):
    # A $63/$64 ramp has no target note; its lifetime is bounded only by the
    # note-on reset block, which stores zero to the slide-active byte.
    act, stores, clears = slide_state(mod)
    assert act is not None
    assert len(stores) == 3      # $63 handler, $64 handler, note-on clear
    assert len(clears) == 1


def test_field5_bit4_has_exactly_one_consumer():
    mod = HardTrackModule.from_sid(os.path.join(DEFAULT_DIR, 'Altered_States_Tune_1.sid'))
    reads = field_reads(mod)[5]
    masks = field5_masks(mod, reads)
    assert masks.count(0x10) == 1
    site = mod.load + reads[masks.index(0x10)]
    # lda F5,y / and #$10 / beq / lda note,x / cmp prev,x / bne / jmp past-filter
    d, off = mod.data, site - mod.load
    assert d[off + 3] == 0x29 and d[off + 4] == 0x10
    assert d[off + 5] == 0xF0                       # beq -> do the filter anyway
    assert d[off + 7] == 0xBD and d[off + 10] == 0xDD   # lda cur,x / cmp prev,x
    assert d[off + 13] == 0xD0 and d[off + 15] == 0x4C  # bne -> filter; jmp -> skip
