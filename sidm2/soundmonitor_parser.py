"""Sound Monitor (Chris Huelsbeck, 1986) player parser -- the Fun_Fun $C000/$C475
cluster (driver name "Musicmaster", credit string at $CBD4 -- truncated away in
some rips, e.g. Final_Luv).

Format RE'd 2026-07-10 from the play routine disasm (see
memory/soundmonitor-player.md for the full trail). Unlike the relocatable players
(Hubbard/DMC), the whole 11-file cluster shares BYTE-IDENTICAL player code at a FIXED
load (init=$C000/play=$C475) -- every table is a HARDCODED absolute address, verified
stable across load-address variants (only per-song bytes at $C010/$C011 + trailing
data differ between files).

Model: ROW (song step) -> per-voice BAR (pattern) -> STEP events (rest/tie/note).

ROW table: for row# 0..(ROW_COUNT-1), four pieces of per-voice/shared data live in
fixed tables indexed directly by the row number (no pointer chasing except for the bar
data and the row header):
  - per voice: BAR pointer (lo/hi split pages), NOTE-transpose (direct byte),
    SOUND-transpose (direct byte) -- this is the literal "a bar, transpose, instrument
    set" the format is documented as having per row/channel cell.
  - shared: ROW HEADER pointer -> a record whose byte2=SPEED, byte3=LENGTH (steps in
    this row), byte4=NEXT-row index ($FF=none), byte5&$0F=flag (role TBD).

BAR data: a sequence of (ctrl, data) byte pairs, one pair per step (LENGTH steps/row):
  ctrl == 0x00 -> REST (gate off)
  ctrl == 0x80 -> TIE (bit7 = retrigger flag with note 0 = hold, no new note)
  ctrl bit7 set -> NOTE with retrigger; ctrl 0x01-0x7F -> legato NOTE (pitch change
                  without re-gating). In both: note = (ctrl & 0x7F) + row
                  transpose[voice] (skipped if data & 0x20); instrument =
                  (data & 0x0F) + row sound-transpose[voice] (skipped if
                  data & 0x80) -- NOTE: the transpose add is NOT masked to 4 bits,
                  so effective instrument indices routinely exceed 15.
  data & 0x10 -> PORTAMENTO/GLIDE: pitch walks chromatically from the previous note
                 to this one (empirically confirmed on Dreamix: exactly the data=$17
                 notes glide, the data=$07 ones jump).
  data & 0x40 -> ARPEGGIO on: the engine at $CB65/$CB8A cycles an 8-entry table of
                 SEMITONE OFFSETS (index = frame counter & 7) added to the note.
                 The table lives INSIDE the row-header record, at offset = the LAST
                 data byte of this voice's bar (read once per row at $C9D9); e.g.
                 offset $28 -> "0C 00 0C 00..." = octave arp. The header record past
                 its 6 fixed bytes is a bank of these 8-byte chord tables.

SOUND (instrument) table: 24-byte records at SOUND_BASE + instr*24: byte0=waveform
(SID ctrl), byte1=AD, byte2=SR (confirmed vs siddump), remaining base fields TODO;
bytes 16-23 = an optional extension block copied only if byte16 != 0xFF (role TODO --
distinct from the row-header arp tables above).

Freq table: note index -> SID 16-bit freq, direct (not interleaved) split
FREQ_LO=$C416 / FREQ_HI=$C3B7.
"""
import struct

SM_INIT = 0xC000
SM_PLAY = 0xC475

ROW_COUNT_ADDR = 0xC010
ROW_START_ADDR = 0xC011

# Indexed by voice 0/1/2.
BAR_LO = (0xA000, 0xA400, 0xA800)
BAR_HI = (0xA100, 0xA500, 0xA900)
ROW_TRANSPOSE = (0xA200, 0xA600, 0xAA00)
ROW_SOUND_TRANSPOSE = (0xA300, 0xA700, 0xAB00)

ROW_HDR_LO = 0xAC00
ROW_HDR_HI = 0xAD00

SOUND_BASE = 0xAE00
SOUND_STRIDE = 24

FREQ_LO = 0xC416
FREQ_HI = 0xC3B7


def load_sid(path):
    """Return (data_bytes_at_load, load_addr, header). PSID/RSID; resolves the
    embedded load word when the header load field is 0."""
    raw = open(path, "rb").read()
    dataoff = struct.unpack(">H", raw[6:8])[0]
    load = struct.unpack(">H", raw[8:10])[0]
    init = struct.unpack(">H", raw[0x0A:0x0C])[0]
    play = struct.unpack(">H", raw[0x0C:0x0E])[0]
    if load == 0:
        load = raw[dataoff] | (raw[dataoff + 1] << 8)
        data = raw[dataoff + 2:]
    else:
        data = raw[dataoff:]

    class H:
        pass
    h = H()
    h.init_address, h.play_address = init, play
    return bytes(data), load, h


# The play routine's first 16 bytes at $C475 (JSR $CA17 / LDA $C00F / BEQ /
# JSR $C90D / LDX $02C3 / BNE), byte-identical across the cluster. Detection
# can NOT rely on the "MUSICMASTER CREATED BY CHRIS HUELSBECK" string at $CBD4:
# some rips (Final_Luv) are truncated right before it.
_PLAY_SIG = bytes.fromhex("2017caad0fc0f003200dc9aec302d023")


def is_soundmonitor(data, la, h):
    """Detect: fixed init/play entry points + the play-routine byte signature."""
    if h.init_address != SM_INIT or h.play_address != SM_PLAY:
        return False
    off = SM_PLAY - la
    return data[off:off + len(_PLAY_SIG)] == _PLAY_SIG


class SoundMonitorModule:
    """Parsed Sound Monitor song. Fixed-address tables -- no relocation needed."""

    def __init__(self, d, la):
        self.d, self.la = d, la

    def _u8(self, addr):
        off = addr - self.la
        return self.d[off] if 0 <= off < len(self.d) else 0

    @property
    def row_count(self):
        return self._u8(ROW_COUNT_ADDR)

    @property
    def row_start(self):
        return self._u8(ROW_START_ADDR)

    def row_header(self, row):
        ptr = self._u8(ROW_HDR_LO + row) | (self._u8(ROW_HDR_HI + row) << 8)
        return dict(
            ptr=ptr,
            speed=self._u8(ptr + 2),
            length=self._u8(ptr + 3),
            # byte4 is NOT a next-row chain pointer -- $C940 (row-advance) just
            # increments the row index linearly (0..row_count-1) and loops back to
            # row_start at the end. byte4 is a one-time latch (first non-$FF value
            # seen anywhere sets $CDBA/$CDBB/$CDBC and is never overwritten again);
            # kept here for completeness, not used by row iteration.
            latch=self._u8(ptr + 4),
            flag=self._u8(ptr + 5) & 0x0F,
        )

    def bar_ptr(self, voice, row):
        return self._u8(BAR_LO[voice] + row) | (self._u8(BAR_HI[voice] + row) << 8)

    def row_transpose(self, voice, row):
        return self._u8(ROW_TRANSPOSE[voice] + row)

    def row_sound_transpose(self, voice, row):
        return self._u8(ROW_SOUND_TRANSPOSE[voice] + row)

    def bar_step(self, ptr, step):
        off = ptr + step * 2
        return self._u8(off), self._u8(off + 1)

    def freq(self, note):
        return self._u8(FREQ_LO + note) | (self._u8(FREQ_HI + note) << 8)

    def sound(self, idx):
        # Full 8-bit index: the player masks the RAW data nibble (& $0F) BEFORE
        # adding the row sound-transpose, never after, so indices exceed 15.
        base = SOUND_BASE + (idx & 0xFF) * SOUND_STRIDE
        return bytes(self._u8(base + i) for i in range(SOUND_STRIDE))

    def row_arp(self, voice, row):
        """The 8-entry semitone-offset arp table for (voice, row), or None.
        Selected by the LAST data byte of the voice's bar, indexing into the
        row-header record ($C9D9 reads it once per row; $CB8A cycles it)."""
        hdr = self.row_header(row)
        bar = self.bar_ptr(voice, row)
        base = self._u8(bar + hdr['length'] * 2 - 1)
        return tuple(self._u8(hdr['ptr'] + base + i) for i in range(8))

    def row_chain(self, max_rows=512):
        """Linear row sequence starting at row_start, incrementing (with natural
        8-bit WRAPAROUND -- $02C1 is a plain INX, so row_start > row_count is
        normal and means the real range wraps through 255->0) until it equals
        row_count ($C940's `CPX $C010`). NOT a per-row jump chain."""
        chain = []
        row = self.row_start
        for _ in range(max_rows):
            chain.append((row, self.row_header(row)))
            row = (row + 1) & 0xFF
            if row == self.row_count:
                break
        return chain

    def events(self):
        """-> {voice: [(row, step, kind, note, instrument, arp, glide), ...]},
        kind in ('rest', 'tie', 'note', 'legato'). 'note' = retriggered (ctrl
        bit7); 'legato' = pitch change without re-gate (ctrl bit7 clear). arp =
        the 8-tuple of semitone offsets when data & $40, else None. glide =
        True when data & $10 (portamento from the previous pitch). Row order
        per row_chain(); per-row LENGTH steps per voice. Timing (frames/step =
        row 'speed') is left to the caller."""
        out = {0: [], 1: [], 2: []}
        for row, hdr in self.row_chain():
            for v in range(3):
                ptr = self.bar_ptr(v, row)
                transpose = self.row_transpose(v, row)
                sound_transpose = self.row_sound_transpose(v, row)
                arp_table = self.row_arp(v, row)
                for step in range(hdr['length']):
                    ctrl, data = self.bar_step(ptr, step)
                    if ctrl == 0x00:
                        out[v].append((row, step, 'rest', None, None, None, False))
                    elif ctrl == 0x80:
                        out[v].append((row, step, 'tie', None, None, None, False))
                    else:
                        kind = 'note' if ctrl & 0x80 else 'legato'
                        note = ctrl & 0x7F
                        if not (data & 0x20):
                            note = (note + transpose) & 0xFF
                        instrument = data & 0x0F
                        if not (data & 0x80):
                            instrument = (instrument + sound_transpose) & 0xFF
                        arp = arp_table if (data & 0x40) else None
                        out[v].append((row, step, kind, note, instrument, arp,
                                       bool(data & 0x10)))
        return out
