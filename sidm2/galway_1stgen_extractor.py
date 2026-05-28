"""Extract musical data from a Martin Galway 1st-gen SID (editor view).

Phase 1 (this module, so far): recover the per-voice command-stream start
pointers (`PCn`) and the post-init (relocated) RAM image, by emulating the
player's init.

Engine map: `docs/analysis/GALWAY_1STGEN_ENGINE.md`. Detector (locates the
dispatch, hence the `PCn` ZP address and the freq tables):
`sidm2/galway_1stgen_detector.py`.

# How channel pointers are recovered

The dispatch site does `LDY #0 ; LDA (PCn),Y ; CMP #$C0`, so the byte right
before `CMP #$C0` (`B1 <zp>`) gives `PC0`'s zero-page address; `PC1`/`PC2`
follow at +2/+4 (declared consecutively in every source file seen).

`init` is emulated with py65 (`sid_init_runner.run_init`), which also
performs any self-relocation the player does at init time, so the returned
pointers and RAM are at the player's RUNTIME addresses.

# Subtune sweep

The PSID default subtune (A = start_song-1) is often silent (pointers come
back $0000) or spins forever in init for these multi-tune game rips. So we
sweep subtunes and pick the first that returns cleanly AND yields sane,
clustered pointers (≥2 voices non-zero, not in the zero/stack page, within
~$3000 of the freq tables). This recovers ~17/21 detected corpus files.

# Known un-recovered cases (need per-file work, not handled here)

- IRQ/CIA-driven players whose init never returns (e.g. Arkanoid alt-drums,
  `play=$0000`).
- Players that set the pointers only during PLAY, or store voices 1/2 in
  non-consecutive ZP (e.g. Highlander, Miami Vice, Mikie).
"""
from __future__ import annotations

from typing import NamedTuple, Optional, List

from sidm2.galway_1stgen_detector import detect_galway_1stgen, Galway1stGenLayout
from sidm2.sid_init_runner import run_init

# Command opcodes (COM = $C0; each opcode = COM + 2*index into vtn). Order is
# fixed across all 1st-gen files (confirmed via the vt0 tables in source).
RET, CALL, JMP, CT, JT, MOKE, FOR, NEXT, FLOAD, VLM, SOKE, CODE, TRANSP, \
    DMOKE, DSOKE, MASTER, FILTER, DISOWN, MBENDOFF, MBENDON, FREQ, TIME = \
    range(0xC0, 0xC0 + 22 * 2, 2)

REST_INDEX = 0x5F   # note byte $5F (or $BF) = rest
TIE_BASE = 0x60     # note bytes $60..$BE = same pitch, no-retrigger ("tie")


class GalwayChannelState(NamedTuple):
    """Recovered per-voice stream start + the post-init RAM image."""
    subtune: int            # the subtune (A value) that yielded these pointers
    pc: List[int]           # 3 voice start pointers (runtime addresses)
    pc0_zp: int             # zero-page address of PC0 (PC1=+2, PC2=+4)
    ram: bytearray          # 64KB post-init (relocated) memory image
    layout: Galway1stGenLayout  # detector result (vt0/LoFrq/HiFrq/...)


def _pc0_zp_from_layout(c64_data: bytes, sid_la: int,
                        layout: Galway1stGenLayout) -> Optional[int]:
    off = layout.dispatch_addr - sid_la
    if off < 2 or off - 2 >= len(c64_data):
        return None
    if c64_data[off - 2] != 0xB1:   # LDA (zp),Y
        return None
    return c64_data[off - 1]


def _pcs_sane(pcs: List[int], lofrq: int) -> bool:
    good = [p for p in pcs if p and (p >> 8) not in (0x00, 0x01)]
    if len(good) < 2:               # need at least 2 live voices
        return False
    return all(abs(p - lofrq) < 0x3000 for p in good)


def recover_channels(
    c64_data: bytes,
    sid_la: int,
    init_addr: int,
    *,
    songs: int = 1,
    start_song: int = 1,
    max_subtunes: int = 16,
) -> Optional[GalwayChannelState]:
    """Recover per-voice start pointers + post-init RAM for a Galway 1st-gen
    SID. Returns None if not a 1st-gen Galway file or no subtune yields sane
    pointers.

    Args:
        songs / start_song: from the PSID header (start_song is 1-based).
    """
    layout = detect_galway_1stgen(c64_data, sid_la)
    if layout is None:
        return None
    pc0_zp = _pc0_zp_from_layout(c64_data, sid_la, layout)
    if pc0_zp is None or pc0_zp + 5 > 0xFFFF:
        return None

    # Try the PSID default subtune first, then sweep the rest.
    default = max(0, start_song - 1)
    order = [default] + [a for a in range(min(songs, max_subtunes))
                         if a != default]
    for a in order:
        # Real Galway inits finish in well under this; the cap mainly bounds
        # the cost of subtunes whose init spins forever.
        mem = run_init(c64_data, sid_la, init_addr,
                       max_cycles=300_000, subtune=a)
        if mem is None:
            continue
        pcs = [mem[pc0_zp + 2 * v] | (mem[pc0_zp + 2 * v + 1] << 8)
               for v in range(3)]
        if _pcs_sane(pcs, layout.lofrq_addr):
            return GalwayChannelState(subtune=a, pc=pcs, pc0_zp=pc0_zp,
                                      ram=mem, layout=layout)
    return None


# ---------------------------------------------------------------------------
# Phase 2 — bytecode flattener
# ---------------------------------------------------------------------------

class GalwayEvent(NamedTuple):
    """One musical event from a flattened channel stream.

    kind:
      'note'  pitch = note index into LoFrq/HiFrq (after transpose); dur =
              raw duration byte (resolve via IDRT later); tie = no-retrigger.
      'rest'  dur = raw duration byte.
      'instr' value = pointer to the 5-byte instrument def (Vlm command).
      'fload' value = pointer to a Dn block loaded by FLoad; dur = byte count
              (cnt >= 26 loads the waveform/ADSR region → an instrument).
      'code'  value = inline-code pointer (Code command) — not interpreted.
      'end'   stream ended cleanly (Ret with empty call stack).
      'desync' hit a byte that is not a valid even opcode — indicates the
              walk lost sync (wrong opcode length). value = the bad byte.
    """
    kind: str
    pitch: int          # note index (notes only), else 0
    dur: int            # raw duration byte (notes/rests), else 0
    tie: bool           # note articulation flag
    value: int          # instr/code pointer, else 0
    addr: int           # stream address the event was decoded from


# Bytes consumed by each command when it falls through sequentially (commands
# that jump/loop manage PC themselves and are not in this table).
_SEQ_LEN = {
    MOKE: 3, FOR: 2, NEXT: 1, FLOAD: 4, VLM: 3, SOKE: 3, CODE: 3, TRANSP: 2,
    DMOKE: 4, DSOKE: 4, MASTER: 1, FILTER: 3, DISOWN: 1, MBENDOFF: 1,
    MBENDON: 1, FREQ: 3,
}


def _find_runtime_dispatch(ram, pc0_zp: int,
                           near: Optional[int] = None) -> Optional[int]:
    """Locate the dispatch in a (possibly relocated) RAM image by pinning on
    the known PC0 zero-page address: `LDY #0 ; LDA (pc0_zp),Y ; CMP #$C0 ;
    BCC`. Returns the dispatch address (the CMP), or None.

    A self-relocating player has BOTH a load-image copy and the live
    relocated copy; the handlers return to the LIVE read.byte, so `near`
    (a runtime channel-PC address) selects the copy in the live region."""
    pat = bytes([0xA0, 0x00, 0xB1, pc0_zp & 0xFF, 0xC9, 0xC0, 0x90])
    rb = bytes(ram)
    hits = []
    i = rb.find(pat)
    while i >= 0:
        hits.append(i + 4)
        i = rb.find(pat, i + 1)
    if not hits:
        return None
    if near is not None:
        hits.sort(key=lambda d: abs(d - near))
    return hits[0]


def _probe_opcode_length(ram, rb_entry: int, pc0_zp: int, op: int):
    """Run one command opcode through the real dispatch and measure the PCn
    advance. Returns ('seq', n) for a sequential data opcode of length n, or
    ('ctrl', 0) for control flow / inline code / unmeasurable. Variant-
    independent: it executes the file's own dispatch + handler."""
    try:
        from py65.devices.mpu6502 import MPU
    except ImportError:
        return ('ctrl', 0)
    S = 0xC000 if not (0xC000 <= rb_entry <= 0xC100) else 0x2000
    mpu = MPU()
    for i in range(0x10000):
        mpu.memory[i] = ram[i]
    mpu.memory[S] = op
    for i in range(1, 8):
        mpu.memory[S + i] = 0x00
    mpu.memory[pc0_zp] = S & 0xFF
    mpu.memory[pc0_zp + 1] = (S >> 8) & 0xFF
    mpu.memory[0x01FF] = 0xFF
    mpu.memory[0x01FE] = 0xFE
    mpu.sp = 0xFD
    mpu.pc = rb_entry
    mpu.a = mpu.x = mpu.y = 0
    try:
        # phase 1: leave the dispatch-read code block (enter the handler)
        for _ in range(80):
            pc = mpu.pc
            if pc == 0xFFFF:
                return ('ctrl', 0)
            if pc < rb_entry or pc > rb_entry + 0x28:
                break
            mpu.step()
        else:
            return ('ctrl', 0)
        # phase 2: run handler until control returns to read.byteN
        for _ in range(8000):
            pc = mpu.pc
            if pc == 0xFFFF:
                return ('ctrl', 0)
            if rb_entry <= pc <= rb_entry + 2:
                new = mpu.memory[pc0_zp] | (mpu.memory[pc0_zp + 1] << 8)
                delta = (new - S) & 0xFFFF
                return ('seq', delta) if 1 <= delta <= 8 else ('ctrl', 0)
            mpu.step()
    except Exception:
        return ('ctrl', 0)
    return ('ctrl', 0)


def derive_opcode_lengths(ram, pc0_zp: int,
                          near: Optional[int] = None) -> dict:
    """Empirically derive this file's sequential data-opcode lengths by
    running each opcode's handler in py65 and measuring the PCn advance.
    Control-flow opcodes (Ret/Call/Jmp/CT/JT/For/Next/Code) are handled
    universally by flatten_channel and are intentionally NOT included.

    `near`: a runtime channel-PC address, used to pick the live dispatch
    copy in self-relocating players.

    Returns {opcode: length}. Empty if the dispatch can't be located."""
    disp = _find_runtime_dispatch(ram, pc0_zp, near)
    if disp is None:
        return {}
    rb = disp - 4
    table = {}
    for op in range(0xC0, 0x100, 2):
        kind, n = _probe_opcode_length(ram, rb, pc0_zp, op)
        if kind == 'seq':
            table[op] = n
    return table


def flatten_all_channels(state: GalwayChannelState):
    """Flatten all 3 voices of a recovered Galway file, using the per-file
    empirically-derived opcode-length table when it flattens at least as
    cleanly as the built-in Wizball table (so generalization never regresses
    a file that already worked).

    Returns (voices, table_used) where voices is a list of 3 event lists.
    """
    derived = derive_opcode_lengths(state.ram, state.pc0_zp, near=state.pc[0])

    def total_desyncs(tbl):
        return sum(flatten_channel(state.ram, state.pc[v], seq_len=tbl)[-1].kind
                   == 'desync' for v in range(3))

    use = derived if (derived and total_desyncs(derived) <= total_desyncs(None)) \
        else None
    voices = [flatten_channel(state.ram, state.pc[v], seq_len=use)
              for v in range(3)]
    return voices, (use if use is not None else dict(_SEQ_LEN))


def flatten_channel(ram: bytes, start_pc: int,
                    max_events: int = 4000,
                    seq_len: Optional[dict] = None) -> List[GalwayEvent]:
    """Walk a Galway channel command stream into a linear event list.

    Resolves control flow (Call/Ret, For/Next, Jmp, CT/JT) and applies
    Transp. Terminates on Ret-from-empty-stack, on revisiting a stream
    address at empty call/loop depth (the song's loop point), or at
    `max_events`. Returns the event list (last event is 'end' if the stream
    terminated cleanly).

    seq_len: per-file {opcode: byte-length} table for the sequential 'data'
        commands (Moke/Vlm/Freq/Filter/... and any game-specific opcodes),
        as derived by `derive_opcode_lengths`. The control-flow opcodes
        (Ret/Call/Jmp/CT/JT/For/Next) are handled universally and need not
        appear. Defaults to Wizball's table (`_SEQ_LEN`).
    """
    if seq_len is None:
        seq_len = _SEQ_LEN
    events: List[GalwayEvent] = []
    stack: List[tuple] = []     # ('call', ret_addr) | ('for', loop_start, count)
    transpose = 0
    pc = start_pc & 0xFFFF
    visited = set()             # (pc) seen at empty stack — loop-point guard

    def rd(a):
        return ram[a & 0xFFFF]

    def w(a):
        return rd(a) | (rd(a + 1) << 8)

    while len(events) < max_events:
        if not stack and pc in visited:
            break               # reached the song loop point
        if not stack:
            visited.add(pc)
        b = rd(pc)

        if b < 0xC0:            # note record [note][duration]
            dur = rd(pc + 1)
            tie = b >= TIE_BASE
            idx = (b - TIE_BASE) if tie else b
            if idx == REST_INDEX:
                events.append(GalwayEvent('rest', 0, dur, False, 0, pc))
            else:
                pitch = (idx + transpose) & 0xFF
                events.append(GalwayEvent('note', pitch, dur, tie, 0, pc))
            pc += 2
            continue

        if b == RET:
            if not stack:
                events.append(GalwayEvent('end', 0, 0, False, 0, pc))
                break
            frame = stack.pop()
            pc = frame[1] if frame[0] == 'call' else (pc + 1)
            continue
        if b == CALL:
            stack.append(('call', pc + 3))
            pc = w(pc + 1)
            continue
        if b == JMP:
            pc = w(pc + 1)
            continue
        if b == CT:                 # transpose + call
            transpose = rd(pc + 1)
            stack.append(('call', pc + 4))
            pc = w(pc + 2)
            continue
        if b == JT:                 # transpose + jmp
            transpose = rd(pc + 1)
            pc = w(pc + 2)
            continue
        if b == FOR:
            stack.append(('for', pc + 2, rd(pc + 1)))
            pc += 2
            continue
        if b == NEXT:
            if stack and stack[-1][0] == 'for' and stack[-1][2] > 1:
                kind, loop_start, count = stack[-1]
                stack[-1] = (kind, loop_start, count - 1)
                pc = loop_start
            else:
                if stack and stack[-1][0] == 'for':
                    stack.pop()
                pc += 1
            continue
        if b == TRANSP:
            transpose = rd(pc + 1)
            pc += 2
            continue
        if b == VLM:                # set instrument (ptr to 5-byte def)
            events.append(GalwayEvent('instr', 0, 0, False, w(pc + 1), pc))
            pc += 3
            continue
        if b == FLOAD:              # load Dn block [cnt][ptr]; cnt>=26 → instr
            cnt = rd(pc + 1)
            events.append(GalwayEvent('fload', 0, cnt, False, w(pc + 2), pc))
            pc += seq_len.get(FLOAD, 4)
            continue
        if b == CODE:
            events.append(GalwayEvent('code', 0, 0, False, w(pc + 1), pc))
            pc += 3
            continue

        ln = seq_len.get(b)
        if ln is None:              # not a known even opcode → lost sync
            events.append(GalwayEvent('desync', 0, 0, False, b, pc))
            break
        pc += ln

    return events


# ---------------------------------------------------------------------------
# Phase 3 — instrument extraction
# ---------------------------------------------------------------------------

# SID waveform control-register bits (the gate/sync/ring/test low bits are
# runtime state, not instrument identity).
_WAVEFORMS = [(0x10, "triangle"), (0x20, "sawtooth"),
              (0x40, "pulse"), (0x80, "noise")]


class GalwayInstrument(NamedTuple):
    """A Galway instrument as set by a `Vlm` command (5-byte def copied into
    the voice's Dn block at VWF..VRD). Maps to SID voice registers:
      ctrl  -> $D404 (waveform + gate), ad -> $D405, sr -> $D406.
    """
    ptr: int            # source address of the 5-byte def
    ctrl: int           # VWF: waveform control byte (+gate bit)
    attack: int         # VADV high nibble
    decay: int          # VADV low nibble
    sustain: int        # VSRV high nibble
    release: int        # VSRV low nibble
    vadsd: int          # attack/decay-sustain duration seed
    vrd: int            # release duration seed
    waveforms: tuple    # decoded waveform names, e.g. ("pulse",)

    @property
    def ad(self) -> int:
        return (self.attack << 4) | self.decay

    @property
    def sr(self) -> int:
        return (self.sustain << 4) | self.release


def _decode_instrument(ram, ptr: int, vwf_off: int = 0) -> GalwayInstrument:
    """Decode an instrument from `ram`. `vwf_off` is the offset of the VWF
    byte from `ptr`: 0 for a `Vlm` 5-byte def, 24 for a full `Dn` block
    loaded by `FLoad` (VWF lives at Dn offset 24)."""
    base = (ptr + vwf_off) & 0xFFFF
    vwf = ram[base]
    vadv = ram[(base + 1) & 0xFFFF]
    vsrv = ram[(base + 2) & 0xFFFF]
    vadsd = ram[(base + 3) & 0xFFFF]
    vrd = ram[(base + 4) & 0xFFFF]
    waves = tuple(name for bit, name in _WAVEFORMS if vwf & bit)
    return GalwayInstrument(
        ptr=ptr, ctrl=vwf,
        attack=vadv >> 4, decay=vadv & 0x0F,
        sustain=vsrv >> 4, release=vsrv & 0x0F,
        vadsd=vadsd, vrd=vrd, waveforms=waves,
    )


def galway_to_voice_streams(
    voices: List[List[GalwayEvent]],
    instruments: List["GalwayInstrument"],
) -> List[bytes]:
    """Convert flattened Galway voices into 3 NP21-shape byte streams ready
    for `placeholder_edit_area.build_placeholder_edit_area(voice_streams=…)`.

    Mapping (an editor VIEW of the score; audio comes from the embedded
    player, so exact duration timing is not reproduced here):
      * set-instrument (`instr`/`fload`) → `$A0 + (instrument_index & 0x1F)`
        — the segment marker the SF2 segmenter splits patterns on.
      * note → SF2 note byte = pitch clamped to `$01..$6F`.
      * rest → `$00` (no-event row).
    One row per event keeps patterns readable; the segmenter caps length.
    """
    idx_of = {ins.ptr: i for i, ins in enumerate(instruments)}
    streams: List[bytes] = []
    for ev in voices:
        s = bytearray()
        for e in ev:
            if e.kind in ('instr', 'fload'):
                if e.value in idx_of:
                    s.append(0xA0 | (idx_of[e.value] & 0x1F))
            elif e.kind == 'note':
                s.append(min(max(e.pitch + 1, 0x01), 0x6F))
            elif e.kind == 'rest':
                s.append(0x00)
            # 'code'/'end'/'desync' produce no editor row
        streams.append(bytes(s))
    return streams


def extract_instruments(ram, voices: List[List[GalwayEvent]]
                        ) -> List[GalwayInstrument]:
    """Collect the distinct instruments set across the flattened voices,
    ordered by first use. Two mechanisms:

      * `Vlm` ($D2) — 5-byte def, VWF at offset 0.
      * `FLoad` ($D0) loading a full Dn block (cnt >= 26) — VWF at offset 24.

    Each candidate is gated on having a real SID waveform (non-empty bits),
    which filters out garbage from games whose $D0/$D2 carry different
    semantics (so a decoded ctrl=$00 is not mistaken for an instrument).
    """
    seen = {}
    for ev in voices:
        for e in ev:
            if e.kind == 'instr':
                key = ('v', e.value)
                cand = _decode_instrument(ram, e.value, 0)
            elif e.kind == 'fload' and e.dur >= 26:
                key = ('f', e.value)
                cand = _decode_instrument(ram, e.value, 24)
            else:
                continue
            if cand.waveforms and key not in seen:
                seen[key] = cand
    return list(seen.values())

