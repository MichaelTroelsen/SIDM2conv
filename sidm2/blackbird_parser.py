"""Blackbird SID player parser (Linus Åkesson / "lft").

`bin/LFT/blackbird-1.2/` bundles the author's own editor + `birdcruncher`
exporter, **including full assembly source** (`Export/source/player.s`,
`rplayer.h`) and the **C compressor source** (`Export/source/cruncher.c`).
This is the opposite situation from every other player in this project:
instead of reverse-engineering a black-box binary, table location AND the
note-stream decompression algorithm come from the literal ground truth, not
disassembly guesswork. Full history/verification: `docs/players/BLACKBIRD.md`
(read it first if continuing this work).

**Scope of this module**: locate + decompress only, for the **v1.2-exact
bucket** (11 files in `SID/LFT/`, byte-identical to the compiled
`seg_play_data` template outside documented relocation offsets — see
`locate_blackbird`) **plus, as of 2026-07-22, the 5-file "v1.2-repeat"
bucket** (`_templates_repeat1`'s own docstring — the SAME v1.2 source,
compiled with player.s's `#if REPEAT` flag enabled; `locate_blackbird`
tags the result's `.variant` field so callers can tell which). Locate is
fully solved and tested for both; `decode_streams` (the note-stream
decompressor) is only verified against the v1.2-exact bucket so far — it
throws on the v1.2-repeat bucket (an `IndexError` a handful of pieces in,
a back-reference overshooting the decoded length — genuinely open, not
yet root-caused; see BLACKBIRD.md's "REPEAT=1 locate support" section).
This module does NOT resolve frame timing into notes (the tempo/pipeline
model is "understood but unverified" per BLACKBIRD.md) and does NOT emit
SF2 output — that is later work. **Not wired into**
`DriverSelector.PLAYER_REGISTRY` / `conversion_pipeline` — no SF2 target
exists yet.

## Detection / locate

The compiled player is a relocatable template: `birdcruncher` builds a fixed
1280-byte code+table blob (`seg_play_data` in `player.h`) and patches ~250
known byte offsets with the tune's actual symbol addresses
(`seg_play_reloc()`/`seg_init_reloc()` in the same file — a byte-for-byte
relocation manifest, not a guess, parsed here straight out of the shipped C
source via regex so it can never drift from the tool). Comparing a real
SID's play-routine bytes against this template, skipping only the
documented offsets, gives a deterministic yes/no.

## Compression

The note stream is a custom LZ77 variant with per-copy semitone
transposition, stored physically reversed so the 6502 reads it backward with
a decrementing pointer. Reference: `unpackvoice` in `player.s` (runtime
decoder) and `crunch_some`/`run_prep1-3`/`crunch_streams` in `cruncher.c`
(the compressor, which also simulates the same timer/pipeline automaton
purely to decide when each voice's ring buffer needs more data).

Control-byte grammar (verified against `cruncher.c`'s `crunch_some`):
  - top 5 bits zero -> literal: bottom 3 bits = N literal bytes follow
    (`n==0` is the genuine stream terminator).
  - top 5 bits nonzero -> back-reference copy: bottom 3 bits `n`, copy
    `n+3` bytes; top 5 bits `t` (1-31) encode transpose `t-16`, applied only
    to bytes with bit7 clear (genuine note bytes); one offset byte follows.
    `dist = (L - offset) & 0xff` (256 if that's 0), `src = L - dist`, where
    `L` is *that voice's own* running decoded length.

**The terminator-freeze fix** (found 2026-07-19, see BLACKBIRD.md
"Compression — SOLVED"): per `player.s`'s `unpackvoice`, the genuine
end-of-stream byte (`ctrl == 0x00`) is read via `txa; beq stopstream` —
that branch happens BEFORE the instruction that decrements `zp_inptr`. So
reading the terminator does NOT advance the shared physical read pointer.
Real hardware freezes there *permanently*: every subsequent refill request,
from ANY of the 3 voices, re-reads the SAME frozen byte and falls into
`stopstream`, which appends exactly one `$c0` filler byte per hit (`$c0` is
deliberately chosen: rejected by prepare1/prepare2 as "not consumed",
accepted by prepare3 as a valid delay code, so the pipeline free-wheels
forever without ever producing an out-of-grammar byte). An earlier decoder
let its read pointer keep decrementing past the terminator, sliding into
whatever real program/table bytes physically sit below the compressed
stream, eventually hitting an out-of-grammar byte on unrelated garbage far
past the true end of data — that is the bug this module's `decode_streams`
fixes.

Verified against two independent RetroDebugger live-CPU captures
(`fargo_trace_4199_5371.json`, `glyptodont_trace_4248_5026.json` — real
frame numbers/register values, breakpoint at `unpackvoice+11`): both match
as a unique, exact, contiguous run of (voice, position mod 256, control
byte) triples in this decoder's own piece-emission order (see
`pyscript/test_blackbird_parser.py`). All 11 v1.2-exact-bucket files decode
to a genuine clean freeze with zero out-of-grammar bytes on all 3 voices.

## Event-byte encoding (from `player.s`'s own header comment)

Per-voice decoded byte stream, one "step" = zero or more PREFIX tokens then
usually a terminal token:

  $F9-$FF  out-of-band (tempo change / sync / end / loop)
  $C9-$F8  arpeggio/fx select (index into fxtable via fx_start)
  $80      gate off
  $81      legato (no retrigger)
  $83-$B2  instrument select ((byte - $82), 1-based, 48 max)
  $00-$7F  note; LSB is a delay-bit, real note = byte >> 1
  $B8-$C7  delay (low 4 bits select one of 16 preset wait-frame counts)

`classify_byte`/`parse_grammar` below classify a decoded stream by this
table without resolving frame timing (see BLACKBIRD.md's open item on the
tempo/pipeline model).
"""
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional

from sidm2.sid_parser import SIDParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SOURCE_DIR = os.path.join(ROOT, "bin", "LFT", "blackbird-1.2", "Export", "source")


def load_sid(path):
    """PSID/RSID -> (data bytes at load address, load address, header).
    Handles PSID load=0 (real load address is the first 2 data bytes)."""
    raw = open(path, "rb").read()
    h = SIDParser(path).parse_header()
    d = raw[h.data_offset:]
    la = h.load_address
    if la == 0 and len(d) >= 2:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la, h


# ---------------------------------------------------------------------------
# player.h template + relocation manifest (parsed from the shipped tool
# source, never hand-transcribed — see module docstring "Detection / locate")
# ---------------------------------------------------------------------------
def _parse_h_array(text, dataname):
    m = re.search(dataname + r"\[\d+\] = \{(.*?)\};", text, re.S)
    if not m:
        raise ValueError(f"{dataname} not found in player.h")
    return [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", m.group(1))]


def _parse_h_reloc(text, funcname):
    m = re.search(funcname + r"\(struct ext_symbols \*sym\) \{(.*?)\n\}", text, re.S)
    if not m:
        raise ValueError(f"{funcname} not found in player.h")
    body = m.group(1)
    lines = re.findall(r"\[(\d+)\] = \(sym->(\w+) \+ (-?\d+)\)( >> 8| & 0xff)?;", body)
    out = {}
    for idx, sym, delta, shift in lines:
        out[int(idx)] = (sym, int(delta), shift.strip() if shift else '')
    return out


@lru_cache(maxsize=1)
def _templates():
    """Parse `player.h` once (lazily, cached): the compiled
    `seg_play_data`/`seg_init_data` byte templates plus their relocation
    manifests (`seg_play_reloc`/`seg_init_reloc`)."""
    path = os.path.join(_SOURCE_DIR, "player.h")
    text = open(path).read()
    return (
        _parse_h_array(text, "seg_play_data"),
        _parse_h_array(text, "seg_init_data"),
        _parse_h_reloc(text, "seg_play_reloc"),
        _parse_h_reloc(text, "seg_init_reloc"),
    )


# ---------------------------------------------------------------------------
# REPEAT=1 template (the "near-v1.2 variant A" bucket, 2026-07-22) — NOT a
# different birdcruncher tool version, as originally suspected (see
# BLACKBIRD.md's old "Corpus scope" characterization). player.s guards 4
# code regions behind `#if REPEAT` (loop-on-end support); `player.h`'s own
# `seg_play_data` was compiled with REPEAT=0 (confirmed: it lacks all 4
# blocks). The variant-A bucket is this SAME v1.2 source, compiled with
# REPEAT=1 instead.
#
# There is no REPEAT=1 C source to parse (player.h only ships the REPEAT=0
# build), so this can't be derived the same way `_templates()` is. Instead:
# sequence-aligning `_templates()`'s own play_template against a REAL
# variant-A file's raw bytes (difflib, not position-locked comparison —
# the alignment matters, since one early size change cascades into
# hundreds of apparently-"different" bytes that are actually just
# every-later-instruction shifted by a fixed amount) collapses ~225 raw
# byte diffs down to exactly:
#   - one 26-byte insertion at v1.2 offset 468 (player.s lines 412-426, the
#     `#if REPEAT` EOS loop-rewind block — `lda zp_pendoob; and #1; bne
#     norepeat; ldx zp_bufs+14; stx v_trwpos+14; ...`),
#   - one 4-byte insertion (net +2) at v1.2 offset 691 (lines 612-618, a
#     `clc; adc (zp_inptr),y; tax` vs `lax (zp_inptr),y` swap),
#   - one 27-byte deletion at v1.2 offset 763 (the `.dsb
#     (playorg+$400-207-*), $ee` page-alignment padding automatically
#     shrinks to compensate for the code growing by 25+2=27 bytes before
#     it — `freq_msb` lands at the SAME playorg-relative offset either way,
#     confirmed: byte-for-byte alignment resumes exactly at old-offset 817
#     on both sides),
#   - two single-byte replacements (old offsets 446, 615) that are relative
#     BRANCH-DISTANCE operands, not per-tune addresses — their target sits
#     on the far side of the 25-byte insertion, so the distance encoding
#     itself is a different (but still build-wide FIXED) constant, exactly
#     like the insertions above.
# Every OTHER apparent "diff" in the raw byte comparison is an ordinary
# per-tune relocated address landing at a shifted offset — confirmed by
# cross-referencing the SAME insertion region across two files with
# different `playorg` (Crank_Crank_Airwolf, $5000; Fugue_on_a_Theme,
# $1000): only 3 bytes differ between them inside the 26-byte insert, all
# 3 the high byte of a `STX $xxxx` operand, and `observed - playorg` is
# IDENTICAL (765, 758, 751) on both files — i.e. three NEW relocatable
# `seg_play + N` positions for `stx v_trwpos+14` / `+7` / `+0`, the same
# style of entry `player.h`'s own manifest already uses elsewhere.
# Verified: matches all 5 confirmed variant-A files
# (Crank_Crank_Airwolf/Fugue_on_a_Theme_by_D_M_Hanlon/Quintessence/
# To_Die_For_II/Trinket) byte-for-byte outside the (now larger) reloc set,
# and correctly does NOT match Fargo/Glyptodont (still need the REPEAT=0
# template). `Crank_Crank_Revolution` ("variant A'") does NOT fully match
# this either — it's close but has its own additional differences, not
# investigated yet (see BLACKBIRD.md).
_REPEAT1_INSERT1 = bytes([  # replaces v1.2 template offset 468 (1 byte -> 26)
    0xe3, 0xa5, 0xe5, 0x29, 0x01, 0xd0, 0x13, 0xa6, 0xee, 0x8e, 0xfd, 0x12,
    0xa7, 0xe7, 0xcb, 0xf9, 0x8e, 0xf6, 0x12, 0xa7, 0xe0, 0xcb, 0xf9,
    0x8e, 0xef, 0x12,
])
_REPEAT1_INSERT2 = bytes([0x18, 0x71, 0xe2, 0xaa])  # replaces offset 691 (2 -> 4)
_REPEAT1_STRUCTURAL_SINGLE = {446: 0x2f, 615: 0x68}  # branch-distance bytes
_REPEAT1_DELETE_RANGE = (763, 790)  # 27 bytes of padding, absent in REPEAT=1
# 3 new relocatable `seg_play + N` positions inside _REPEAT1_INSERT1, for
# `stx v_trwpos+14` / `+7` / `+0` (byte offsets are WITHIN the final,
# already-shifted template — see _templates_repeat1()).
_REPEAT1_NEW_RELOC = {478: ('seg_play', 765), 485: ('seg_play', 758), 492: ('seg_play', 751)}


@lru_cache(maxsize=1)
def _templates_repeat1():
    """Build the REPEAT=1 play_template/play_reloc by transforming
    `_templates()`'s own REPEAT=0 data with the fixed structural diff
    documented above. init_template/init_reloc are unaffected (REPEAT only
    changes segment NAMES there — `seg_rinit` vs `seg_init` — no byte
    content difference), so those two are just passed through."""
    play_template, init_template, play_reloc, init_reloc = _templates()

    def shift(off):
        if off < 468:
            return off
        if off == 468:
            return None  # the single replaced byte, no longer 1:1
        if off < 691:
            return off + 25
        if off < 693:
            return None  # replaced 2-byte field
        if off < 763:
            return off + 27
        if off < 790:
            return None  # deleted padding
        return off  # +27 (both inserts) - 27 (deleted padding) cancels out

    new_template = (
        list(play_template[0:468]) + list(_REPEAT1_INSERT1) +
        list(play_template[469:691]) + list(_REPEAT1_INSERT2) +
        list(play_template[693:763]) +
        list(play_template[790:])
    )
    for off, byte in _REPEAT1_STRUCTURAL_SINGLE.items():
        new_template[shift(off)] = byte

    new_reloc = {}
    for off, val in play_reloc.items():
        no = shift(off)
        if no is not None and off not in _REPEAT1_STRUCTURAL_SINGLE:
            new_reloc[no] = val
    for pos, (sym, delta) in _REPEAT1_NEW_RELOC.items():
        new_reloc[pos] = (sym, delta, '& 0xff')
        new_reloc[pos + 1] = (sym, delta, '>> 8')

    return new_template, init_template, new_reloc, init_reloc


def _template_match(data, base, template, reloc):
    """Compare `data[base:base+len(template)]` against `template`, skipping
    reloc'd byte offsets. True/False (False on out-of-range too)."""
    if base < 0 or base + len(template) > len(data):
        return False
    for i, tb in enumerate(template):
        if i in reloc:
            continue
        if data[base + i] != tb:
            return False
    return True


def _read_u16(data, addr, la):
    off = addr - la
    if off < 0 or off + 1 >= len(data):
        return None
    return data[off] | (data[off + 1] << 8)


def _read_u8(data, addr, la):
    off = addr - la
    if off < 0 or off >= len(data):
        return None
    return data[off]


def _assert_reloc(reloc, offset, sym, delta, shift):
    """Self-check: the hardcoded template offsets below must still name the
    symbol we think they do. Catches the template silently drifting out of
    sync with `player.h` (e.g. a birdcruncher source update) instead of
    quietly reading the wrong address."""
    got = reloc.get(offset)
    expected = (sym, delta, shift)
    if got != expected:
        raise ValueError(
            f"player.h relocation manifest drift at offset {offset}: "
            f"expected {expected}, got {got}")


def _extract_symbols(data, la, play_base, play_reloc, variant='v1.2'):
    """Read every table/symbol address directly out of the relocated bytes
    — the relocation manifest tells us exactly which offset holds which
    symbol, so nothing here is independently computed. Offsets verified
    against `player.h` (grep-confirmed 2026-07-19); `_assert_reloc` guards
    against future drift.

    `variant='v1.2-repeat'` (the REPEAT=1 build, see `_templates_repeat1`)
    shifts the 5 table-address offsets by +25 — they all sit between the
    two REPEAT-conditional code insertions (v1.2 offsets 469-691), the ONLY
    ones of these 10 symbols that move. zp_base/seg_init (<468) and
    filttable/fxtable/wavetable (<468) are unaffected."""
    tbl_shift = 25 if variant == 'v1.2-repeat' else 0
    ins_ad_off, ins_sr_off = 553 + tbl_shift, 559 + tbl_shift
    ins_wave_off, ins_filt_off = 533 + tbl_shift, 526 + tbl_shift
    fx_start_off = 489 + tbl_shift

    _assert_reloc(play_reloc, 1, 'seg_init', 0, '& 0xff')
    _assert_reloc(play_reloc, 2, 'seg_init', 0, '>> 8')
    _assert_reloc(play_reloc, 4, 'zp_base', 6, '& 0xff')
    _assert_reloc(play_reloc, ins_ad_off, 'ins_ad', -1, '& 0xff')
    _assert_reloc(play_reloc, ins_ad_off + 1, 'ins_ad', -1, '>> 8')
    _assert_reloc(play_reloc, ins_sr_off, 'ins_sr', -1, '& 0xff')
    _assert_reloc(play_reloc, ins_sr_off + 1, 'ins_sr', -1, '>> 8')
    _assert_reloc(play_reloc, ins_wave_off, 'ins_wave', -1, '& 0xff')
    _assert_reloc(play_reloc, ins_wave_off + 1, 'ins_wave', -1, '>> 8')
    _assert_reloc(play_reloc, ins_filt_off, 'ins_filt', -1, '& 0xff')
    _assert_reloc(play_reloc, ins_filt_off + 1, 'ins_filt', -1, '>> 8')
    _assert_reloc(play_reloc, fx_start_off, 'fx_start', -1, '& 0xff')
    _assert_reloc(play_reloc, fx_start_off + 1, 'fx_start', -1, '>> 8')
    _assert_reloc(play_reloc, 372, 'filttable', 0, '& 0xff')
    _assert_reloc(play_reloc, 373, 'filttable', 0, '>> 8')
    _assert_reloc(play_reloc, 194, 'fxtable', 0, '& 0xff')
    _assert_reloc(play_reloc, 195, 'fxtable', 0, '>> 8')
    _assert_reloc(play_reloc, 290, 'wavetable', 0, '& 0xff')
    _assert_reloc(play_reloc, 291, 'wavetable', 0, '>> 8')

    # zp_base: single byte, low byte only == full address since zp < 0x100.
    zp6 = data[play_base - la + 4]
    zp_base = (zp6 - 6) & 0xff
    seg_init = _read_u16(data, play_base + 1, la)

    def sym16(off, delta):
        v = _read_u16(data, play_base + off, la)
        return None if v is None else (v - delta) & 0xffff

    return dict(
        zp_base=zp_base,
        seg_init=seg_init,
        ins_ad=sym16(ins_ad_off, -1),
        ins_sr=sym16(ins_sr_off, -1),
        ins_wave=sym16(ins_wave_off, -1),
        ins_filt=sym16(ins_filt_off, -1),
        fx_start=sym16(fx_start_off, -1),
        filttable=sym16(372, 0),
        fxtable=sym16(194, 0),
        wavetable=sym16(290, 0),
    )


def _extract_streamstart(data, la, seg_init_addr):
    lo = _read_u8(data, seg_init_addr + 1, la)
    hi = _read_u8(data, seg_init_addr + 5, la)
    if lo is None or hi is None:
        return None
    return lo | (hi << 8)


@dataclass
class BlackbirdLayout:
    """Recovered symbol table for one Blackbird v1.2-template rip. Every
    value is read directly out of the relocation-patched bytes (see module
    docstring) — nothing here is independently computed, so it cannot drift
    from what the compiled binary actually contains."""
    zp_base: int = 0
    seg_init: int = 0
    ins_ad: int = 0
    ins_sr: int = 0
    ins_wave: int = 0
    ins_filt: int = 0
    fx_start: int = 0
    filttable: int = 0
    fxtable: int = 0
    wavetable: int = 0
    streamstart: int = 0
    play_base: int = 0
    load: int = 0
    init_hdr: int = 0
    play_hdr: int = 0
    init_template_mismatch: bool = False
    variant: str = 'v1.2'  # 'v1.2' (REPEAT=0) or 'v1.2-repeat' (REPEAT=1,
                            # the near-v1.2 "variant A" bucket — see
                            # _templates_repeat1()'s own docstring)

    @property
    def nins(self):
        """Instrument count: the 4 column-major instrument arrays
        (ins_ad/ins_sr/ins_wave/ins_filt) are evenly spaced by `nins` bytes
        — a free consistency check, same trick as the MoN/Tel column-major
        instrument-table signature."""
        return self.ins_sr - self.ins_ad

    @property
    def nins_consistent(self):
        d1 = self.ins_sr - self.ins_ad
        d2 = self.ins_wave - self.ins_sr
        d3 = self.ins_filt - self.ins_wave
        d4 = self.fx_start - self.ins_filt
        return d1 == d2 == d3 == d4


def locate_blackbird(path):
    """Detect + fully locate a Blackbird v1.2-exact rip.

    Returns ``None`` if the play-routine bytes don't match the compiled
    `seg_play_data` template outside the documented relocation offsets —
    i.e. this is NOT this generation of the engine (near-v1.2 variants from
    older birdcruncher tool versions, or one of Åkesson's other, unrelated
    engines, all correctly return None here; see BLACKBIRD.md's corpus-scope
    table). Returns a `BlackbirdLayout` on match.
    """
    d, la, h = load_sid(path)
    play_base = h.init_address  # playorg == init address (player.s structure)

    variant = 'v1.2'
    play_template, init_template, play_reloc, init_reloc = _templates()
    if not _template_match(d, play_base - la, play_template, play_reloc):
        variant = 'v1.2-repeat'
        play_template, init_template, play_reloc, init_reloc = _templates_repeat1()
        if not _template_match(d, play_base - la, play_template, play_reloc):
            return None

    syms = _extract_symbols(d, la, play_base, play_reloc, variant=variant)
    if syms['seg_init'] is None:
        return None
    lay = BlackbirdLayout(**syms, play_base=play_base, load=la,
                          init_hdr=h.init_address, play_hdr=h.play_address,
                          variant=variant)
    if not _template_match(d, lay.seg_init - la, init_template, init_reloc):
        lay.init_template_mismatch = True
    streamstart = _extract_streamstart(d, la, lay.seg_init)
    if streamstart is None:
        return None
    lay.streamstart = streamstart
    return lay


# ---------------------------------------------------------------------------
# Decompression: ports cruncher.c's crunch_streams()/crunch_some()/
# run_prep1-3() (the compressor's own simulation of the player's per-frame
# pipeline automaton) for DECODING — reads the physical voice-interleaved
# compressed byte stream backward and reconstructs each voice's decoded
# note-event byte array by replaying the exact scheduling the real 6502
# player uses. See module docstring "Compression" for the terminator-freeze
# fix this depends on.
# ---------------------------------------------------------------------------
class _Reader:
    """Physical compressed-stream reader: single shared pointer, BACKWARD
    (decreasing address) through C64 memory, matching `zp_inptr` in
    `player.s`. Freezes permanently once the genuine terminator byte is
    read (real hardware never decrements `zp_inptr` past it)."""
    __slots__ = ('data', 'la', 'ptr', 'frozen', 'freeze_addr')

    def __init__(self, data, la, ptr):
        self.data = data
        self.la = la
        self.ptr = ptr
        self.frozen = False
        self.freeze_addr = None

    def next(self):
        off = self.ptr - self.la
        # Defensive out-of-range guard only — should never trigger on a
        # genuinely valid v1.2-exact rip, since the freeze logic guarantees
        # the pointer never advances past the terminator. Only reachable if
        # a locate false-positive or corrupt template feeds a bad
        # streamstart.
        b = self.data[off] if 0 <= off < len(self.data) else 0xc0
        self.ptr -= 1
        return b


class _Voice:
    __slots__ = ('out', 'rpos', 'timer', 'frozen_at')

    def __init__(self):
        self.out = bytearray()
        self.rpos = 0
        self.timer = 0xff
        self.frozen_at = None  # len(out) when this voice first saw the terminator


@dataclass
class BlackbirdPiece:
    """One LZ piece emitted while decoding — a literal run, a
    back-reference copy, or post-terminator filler. `pos` is that voice's
    own decoded-stream length (`L`, the ground-truth-comparable position)
    BEFORE this piece was appended."""
    voice: int
    kind: str          # 'literal' | 'copy' | 'fill' | 'end_fill'
    ctrl: int
    pos: int
    ctrl_ptr: int = 0
    data: bytes = b''
    offset: Optional[int] = None
    dist: Optional[int] = None
    src: Optional[int] = None


def _ring_read(v, idx):
    """Read copy-source byte at 8-bit ring position `idx` (0-255),
    matching a real per-voice 256-byte output buffer: returns the most
    recently written byte at that ring slot, or 0 if that slot has never
    been written at all (cold C64 RAM — only reachable before the
    buffer's first wraparound, i.e. len(v.out) < 256). Needed for
    REPEAT=1's copy-source formula, which can legitimately reference
    not-yet-written buffer territory as a zero-fill trick (confirmed via
    live trace: a real `t=16` piece — transp2=0 — reading genuinely-zero,
    never-written RAM at buffer offset 211 while only 101 bytes had been
    decoded)."""
    L = len(v.out)
    m = (L - 1 - idx) // 256
    if m < 0:
        return 0
    return v.out[idx + 256 * m]


def _emit_piece(rd, v, vidx, pieces, variant='v1.2'):
    """Mirrors `crunch_some()`+`unpackvoice()`: consume ONE piece from the
    physical stream and append the decoded bytes to `v.out`. Once the
    shared reader is frozen (real end-of-stream reached by ANY voice),
    every call just appends the one `$c0` filler byte `stopstream` would
    produce, without touching `rd.ptr` again — matching real hardware."""
    if rd.frozen:
        v.out.append(0xc0)
        if v.frozen_at is None:
            v.frozen_at = len(v.out) - 1
        pieces.append(BlackbirdPiece(vidx, 'fill', 0xc0, len(v.out) - 1,
                                     ctrl_ptr=rd.freeze_addr))
        return

    ctrl_ptr = rd.ptr
    ctrl = rd.next()
    top5 = ctrl & 0xf8
    if top5 == 0:
        n = ctrl & 7
        if n == 0:
            # Genuine terminator. Real hardware's `beq stopstream` branches
            # BEFORE the zp_inptr decrement, so un-consume this byte and
            # freeze forever at its address.
            rd.ptr = ctrl_ptr
            rd.frozen = True
            rd.freeze_addr = ctrl_ptr
            v.out.append(0xc0)
            v.frozen_at = len(v.out) - 1
            pieces.append(BlackbirdPiece(vidx, 'end_fill', ctrl,
                                         len(v.out) - 1, ctrl_ptr=ctrl_ptr))
            return
        start = len(v.out)
        for _ in range(n):
            v.out.append(rd.next())
        pieces.append(BlackbirdPiece(vidx, 'literal', ctrl, start,
                                     ctrl_ptr=ctrl_ptr,
                                     data=bytes(v.out[start:start + n])))
    else:
        n = ctrl & 7
        count = n + 3
        t = ctrl >> 3
        transp2 = (2 * (t - 16)) & 0xff
        offset = rd.next()
        L = len(v.out)
        if variant == 'v1.2-repeat':
            # REPEAT=1 builds swap `lax (zp_inptr),y` (v1.2: load offset
            # straight into X, discarding whatever A held) for
            # `clc; adc (zp_inptr),y; tax` at this exact site -- part of
            # player.s's `#if REPEAT` conditional. First characterized (in
            # the REPEAT=1 locate work) as a same-length structural no-op;
            # it is NOT semantically equivalent. Real hardware accumulates
            # the offset byte onto the running (count+L) sum rather than
            # using it as a standalone v1.2-style distance. Confirmed via
            # live RetroDebugger single-step on Crank_Crank_Airwolf.sid
            # (X register read directly at the post-add LDA buf,X) --
            # see memory/blackbird-repeat1-variant.md.
            src = (L + count + offset) & 0xff
            dist = (L - src) & 0xff
        else:
            dist = (L - offset) & 0xff
            if dist == 0:
                dist = 256
            src = L - dist
        start = L
        for i in range(count):
            if variant == 'v1.2-repeat':
                b = _ring_read(v, (src + i) & 0xff)
            else:
                b = v.out[src + i]
            if b < 0x80:
                b = (b + transp2) & 0xff
            v.out.append(b)
        pieces.append(BlackbirdPiece(vidx, 'copy', ctrl, start,
                                     ctrl_ptr=ctrl_ptr, offset=offset,
                                     dist=dist, src=src,
                                     data=bytes(v.out[start:start + count])))


def _prep_getbyte(v):
    if v.rpos >= len(v.out):
        v.rpos += 1
        return 0xc0
    b = v.out[v.rpos]
    v.rpos += 1
    return b


def _prep_ungetbyte(v):
    v.rpos -= 1


def _run_prep1(v, vidx, pend_oob):
    v.timer = (v.timer + 1) & 0xff
    if not (v.timer & 0x80):
        b = _prep_getbyte(v)
        if b >= 0xf9:
            pend_oob[0] = b
            b = _prep_getbyte(v)
        if b >= 0xc9:
            pass  # arpeggio/fx select — consumed here, executed elsewhere
        else:
            _prep_ungetbyte(v)


def _run_prep2(v):
    if not (v.timer & 0x80):
        b = _prep_getbyte(v)
        if 0x80 <= b <= 0xb2:
            pass  # gate-off / legato / instrument select
        else:
            _prep_ungetbyte(v)


def _run_prep3(v, vidx):
    if not (v.timer & 0x80):
        b = _prep_getbyte(v)
        if 0xb8 <= b <= 0xc7:
            v.timer = 0xf0 | b
        elif b < 0x80:
            v.timer = 0xfe | b
        else:
            raise ValueError(
                f"internal stream error ${b:02x} on voice {vidx} "
                f"(rpos={v.rpos}) — out-of-grammar byte reached prepare3; "
                f"see docs/players/BLACKBIRD.md (this should never happen "
                f"on a genuine v1.2-exact file post-terminator-fix)")


@dataclass
class BlackbirdDecodeResult:
    """Full 3-voice decompression result."""
    voices: List[bytes]           # per-voice decoded stream, INCLUDING post-freeze filler
    real_lengths: List[int]       # length of each voice's stream BEFORE the freeze-fill point
    frozen: bool                  # did the shared reader reach the genuine terminator?
    freeze_addr: Optional[int]
    frames_run: int
    pieces: List[BlackbirdPiece]  # every literal/copy/fill piece, true emission order

    def real(self, voice):
        """That voice's decoded bytes up to (not including) the freeze
        filler — the genuine note-event stream."""
        return self.voices[voice][:self.real_lengths[voice]]


def decode_streams(data, la, streamstart, max_frames=200_000,
                    freeze_tail_frames=300, variant='v1.2'):
    """Run the full multi-voice interleaved decompression.

    Replicates `player.s`'s per-frame pipeline: `initroutine` explicitly
    primes voice1 (X=7) then voice0 (X=0) with ONE unpack call EACH before
    the main dispatcher loop ever starts (`preparejmp` patched to RTS at
    that point — no prepare1/2/3). Voice2 gets its first real piece
    revealed naturally inside the main loop's first iteration. Stops
    `freeze_tail_frames` frames after the shared reader freezes (genuine
    end-of-stream), or at `max_frames`, whichever comes first.

    `variant` must match the located `BlackbirdLayout.variant`
    ('v1.2' or 'v1.2-repeat') — REPEAT=1 builds use a different copy-op
    source-index formula (see `_emit_piece`).
    """
    rd = _Reader(data, la, streamstart)
    voices = [_Voice(), _Voice(), _Voice()]
    pieces: List[BlackbirdPiece] = []

    def need_refill(i):
        v = voices[i]
        return (len(v.out) - v.rpos) < 128

    _emit_piece(rd, voices[1], 1, pieces, variant=variant)
    _emit_piece(rd, voices[0], 0, pieces, variant=variant)

    freeze_frame = None
    frame = 0
    for frame in range(max_frames):
        if freeze_frame is not None and frame - freeze_frame >= freeze_tail_frames:
            break
        pend_oob = [0]
        if need_refill(2):
            _emit_piece(rd, voices[2], 2, pieces, variant=variant)
        for i in (2, 1, 0):
            _run_prep1(voices[i], i, pend_oob)
        if need_refill(1):
            _emit_piece(rd, voices[1], 1, pieces, variant=variant)
        for i in (2, 1, 0):
            _run_prep2(voices[i])
        if need_refill(0):
            _emit_piece(rd, voices[0], 0, pieces, variant=variant)
        for i in (2, 1, 0):
            _run_prep3(voices[i], i)
        if pend_oob[0] & 0x02:
            # Tempo-change OOB codes carry 2 inline literal bytes read
            # directly from the shared physical stream (not through any
            # per-voice buffer) — matches player.s's handling of the
            # tempo/sync OOB range.
            rd.next()
            rd.next()
        if rd.frozen and freeze_frame is None:
            freeze_frame = frame

    real_lengths = [v.frozen_at if v.frozen_at is not None else len(v.out)
                    for v in voices]
    return BlackbirdDecodeResult(
        voices=[bytes(v.out) for v in voices],
        real_lengths=real_lengths,
        frozen=rd.frozen,
        freeze_addr=rd.freeze_addr,
        frames_run=frame,
        pieces=pieces,
    )


def decode_file(path, **kwargs):
    """`load_sid` + `locate_blackbird` + `decode_streams` in one call.
    Returns `(BlackbirdLayout, BlackbirdDecodeResult)`, or raises
    `ValueError` if the file doesn't match the v1.2-exact template."""
    lay = locate_blackbird(path)
    if lay is None:
        raise ValueError(f"{path}: not a located Blackbird v1.2-exact rip")
    d, la, h = load_sid(path)
    kwargs.setdefault('variant', lay.variant)
    result = decode_streams(d, la, lay.streamstart, **kwargs)
    return lay, result


class BlackbirdModule:
    """Loaded + located Blackbird v1.2-exact rip, ready to decode. Mirrors
    the `*Module` convention used elsewhere in this project
    (`sidm2.kimmel_parser.KimmelModule`, `sidm2.sdi_parser.SDIModule`)."""

    def __init__(self, path=None, d=None, la=None, lay=None):
        if path is not None:
            self.path = path
            d, la, h = load_sid(path)
            lay = locate_blackbird(path)
        else:
            self.path = None
        if lay is None:
            raise ValueError("not a located Blackbird v1.2-exact rip")
        self.d, self.la, self.lay = d, la, lay
        self._result = None

    def decode(self, max_frames=200_000, freeze_tail_frames=300, force=False):
        """Run (or return the cached) full per-voice decompression."""
        if self._result is None or force:
            self._result = decode_streams(
                self.d, self.la, self.lay.streamstart,
                max_frames=max_frames, freeze_tail_frames=freeze_tail_frames,
                variant=self.lay.variant)
        return self._result

    def real_events(self, voice):
        """That voice's decoded grammar-byte stream, pre-freeze-filler."""
        return self.decode().real(voice)

    def parsed_events(self, voice):
        """`real_events(voice)` classified into `BlackbirdToken`s (no frame
        timing — see module docstring)."""
        return parse_grammar(self.real_events(voice))


# ---------------------------------------------------------------------------
# Event-byte grammar classification (no frame timing — see module docstring)
# ---------------------------------------------------------------------------
def classify_byte(b):
    """Classify one decoded grammar byte per the event-byte table in this
    module's docstring (from `player.s`'s own header comment, cross-checked
    against `cruncher.c`'s `crunch_some`). Returns one of: 'note',
    'gate_off', 'legato', 'instrument', 'delay', 'arp', 'oob', or 'unknown'
    for the (unused) gap values $82, $B3-$B7, $C8."""
    if b <= 0x7f:
        return 'note'
    if b == 0x80:
        return 'gate_off'
    if b == 0x81:
        return 'legato'
    if 0x83 <= b <= 0xb2:
        return 'instrument'
    if 0xb8 <= b <= 0xc7:
        return 'delay'
    if 0xc9 <= b <= 0xf8:
        return 'arp'
    if 0xf9 <= b <= 0xff:
        return 'oob'
    return 'unknown'


@dataclass
class BlackbirdToken:
    kind: str
    raw: int
    arg: Optional[int] = None  # decoded argument (note index incl. delay
                                # bit, instrument #, delay preset, arp index)


def parse_grammar(stream):
    """Classify a decoded per-voice byte stream (the `real_events` /
    `.real(voice)` output) into a flat list of `BlackbirdToken`s. Does NOT
    resolve frame timing (see module docstring / BLACKBIRD.md's open item
    on the tempo/pipeline model) — each byte maps to exactly one token."""
    tokens = []
    for b in stream:
        kind = classify_byte(b)
        if kind == 'note':
            arg = b >> 1
        elif kind == 'instrument':
            arg = b - 0x82
        elif kind == 'delay':
            arg = b - 0xb8
        elif kind == 'arp':
            arg = b - 0xc9
        else:
            arg = None
        tokens.append(BlackbirdToken(kind, b, arg))
    return tokens
