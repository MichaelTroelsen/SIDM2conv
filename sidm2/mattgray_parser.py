"""Matt Gray (C64) song extractor.

Reverse-engineered from the player embedded in the Driller SID rip
(load $0900, init $15E0, play $0E46).  Matt Gray wrote this driver from
scratch -- it is *not* derived from Hubbard or Galway -- and refined it
per game, so treat the Driller layout as one confirmed build rather than
a canonical map.

The player is a three-voice pattern interpreter.  `music_play` is a thin
shim that calls one shared `play_voice` routine three times with
X = $00/$07/$0E, so every per-voice state array has a stride of 7 and is
indexed by that X:

    tune            -> per-voice track pointer + tempo
    track           -> a list of pattern numbers  ($ff loop, $fe stop)
    pattern         -> a byte stream of control codes + note rows
    instrument      -> TWO parallel 8-byte records (tables A0 and A1)
    freq table      -> 96-entry lo/hi pair, the player's own (not PAL-generic)

Pattern byte semantics (RE'd from the `read_note_or_ctrl` loop at $09e0 and
confirmed against a siddump of the real rip):

    >= $fd  ($fd/$fe)  -> set duration; next byte is the duration value.
                          Duration is *sticky* -- it applies to every
                          following note until changed.
    $fc                -> slide/portamento type 2; next byte is the rate
    $fb                -> slide/portamento type 1; next byte is the rate
    $fa                -> set instrument;  next byte is the instrument index
    $00                -> REST (note-off): the driver restores the previous
                          note and ANDs the gate bit out of the waveform
    $01-$f9            -> note; index into the 96-entry freq table
    $ff                -> end of pattern (consumed after a note, not here)

Track byte semantics (checked at $0ad6 after each note):

    $ff  -> restart this voice's track at index 0
    $fe  -> stop the tune
    else -> pattern number

Tempo model (confirmed empirically -- onsets land on frames 1, 257, 513 ...
for Driller's opening duration of $3f):

    `tempo_ctr` counts down once per frame and reloads with `tempo` when it
    goes negative, so a row tick happens once every (tempo + 1) frames.
    On each row tick a voice decrements its own duration counter, and fetches
    the next pattern event when that counter goes negative.  A duration byte
    of D therefore holds a note for (D + 1) row ticks.

All table addresses are recovered by *backward dataflow from the code
operands* (every site is an `LDA abs,y` = opcode $b9), never from absolute
addresses, so the parser survives relocation to a different load address.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- code-site offsets from the play_voice base ------------------------------
# Each value is the offset of the 16-bit operand; the byte before it must be
# $b9 (LDA abs,y).  Verified against the Driller rip, where play_voice = $0900.
_SITE_V1_TRK_LO = 0x0075   # $0974: lda voice1_tune_trackptr_lo,y
_SITE_V1_TRK_HI = 0x007B   # $097a
_SITE_V2_TRK_LO = 0x0081   # $0980
_SITE_V2_TRK_HI = 0x0087   # $0986
_SITE_V3_TRK_LO = 0x008D   # $098c
_SITE_V3_TRK_HI = 0x0093   # $0992
_SITE_TEMPO     = 0x0099   # $0998: lda tune_tempo,y
_SITE_PAT_LO    = 0x00C7   # $09c6: lda pattern_lobytes,y
_SITE_PAT_HI    = 0x00CC   # $09cb: lda pattern_hibytes,y
_SITE_INSTR_A0  = 0x012D   # $0a2c: lda instr_a0,y
_SITE_FRQ_HI    = 0x018D   # $0a8c: lda frq_hi,y
_SITE_FRQ_LO    = 0x0199   # $0a98: lda frq_lo,y
_SITE_INSTR_A1_4 = 0x020A  # $0b09: lda instr_a1+4,y   (so A1 = operand - 4)
_SITE_ARP_TABLE = 0x028D   # $0b8c: lda arpeggio_table,y

_ALL_SITES = (
    _SITE_V1_TRK_LO, _SITE_V1_TRK_HI, _SITE_V2_TRK_LO, _SITE_V2_TRK_HI,
    _SITE_V3_TRK_LO, _SITE_V3_TRK_HI, _SITE_TEMPO, _SITE_PAT_LO, _SITE_PAT_HI,
    _SITE_INSTR_A0, _SITE_FRQ_HI, _SITE_FRQ_LO, _SITE_INSTR_A1_4,
    _SITE_ARP_TABLE,
)

NUM_NOTES = 96          # freq table entries
INSTR_SIZE = 8          # bytes per record, in each of the two parallel tables
VOICE_X = (0x00, 0x07, 0x0E)   # the X values music_play passes to play_voice

# pattern control codes
PC_INSTR = 0xFA
PC_SLIDE1 = 0xFB
PC_SLIDE2 = 0xFC
PC_DUR = 0xFD           # $fd and $fe both take this path (>= $fd)
PC_PAT_END = 0xFF
TRK_LOOP = 0xFF
TRK_STOP = 0xFE
NOTE_REST = 0x00


class MattGrayError(Exception):
    """Raised when a file does not look like a Matt Gray player."""


@dataclass
class MattGrayInstrument:
    """One instrument: the two parallel 8-byte records, A0 and A1.

    Field names follow what the driver actually *does* with each byte; the
    ones still unconfirmed keep a neutral name rather than a guessed one.
    """
    index: int
    a0: List[int]
    a1: List[int]

    # --- table A0 (the byte offsets the driver reads) ---
    @property
    def pulse(self) -> int:
        """A0[0]: hi nibble -> $d402, lo nibble -> $d403 (12-bit pulse width)."""
        return self.a0[0]

    @property
    def pulse_width(self) -> int:
        """The 12-bit pulse value the driver actually programs."""
        return ((self.a0[0] & 0x0F) << 8) | (self.a0[0] & 0xF0)

    @property
    def waveform(self) -> int:
        """A0[1]: sustained waveform, ANDed with the gate mask -> $d404."""
        return self.a0[1]

    @property
    def ad(self) -> int:
        """A0[2] -> $d405 attack/decay."""
        return self.a0[2]

    @property
    def sr(self) -> int:
        """A0[3] -> $d406 sustain/release."""
        return self.a0[3]

    @property
    def pulse_sweep(self) -> int:
        """A0[4]: per-frame pulse-width delta (0 = no PWM)."""
        return self.a0[4]

    @property
    def arp_ctrl(self) -> int:
        """A0[5]: nonzero enables the arpeggio path.

        lo nibble = arpeggio-table index, hi nibble = arpeggio length.
        """
        return self.a0[5]

    @property
    def attack_waveform(self) -> int:
        """A0[6]: waveform written on the note-attack frame."""
        return self.a0[6]

    @property
    def flags(self) -> int:
        """A0[7]: bit0 = drum/effect path, bit1 = pulse reset on note,
        bit2 = two-frame attack-waveform swap."""
        return self.a0[7]

    # --- table A1 ---
    @property
    def slide_rate(self) -> int:
        """A1[0]: nonzero enables the automatic pitch slide."""
        return self.a1[0]

    @property
    def slide_period(self) -> int:
        """A1[1]: slide step reload period."""
        return self.a1[1]

    @property
    def alt_waveform(self) -> int:
        """A1[2]: waveform used by the two-frame swap and the drum path."""
        return self.a1[2]

    @property
    def auto_effect_rate(self) -> int:
        """A1[3]: rate used when A1[4] auto-starts an effect."""
        return self.a1[3]

    @property
    def auto_effect(self) -> int:
        """A1[4]: nonzero auto-starts slide effect type N on every note."""
        return self.a1[4]

    @property
    def drum_len(self) -> int:
        """A1[5]: drum/effect repeat length (compared against a counter)."""
        return self.a1[5]

    @property
    def raw(self) -> List[int]:
        return list(self.a0) + list(self.a1)


@dataclass
class MattGrayNote:
    """One decoded note event from the sequencer simulation."""
    frame: int          # frame the driver writes the note on
    tick: int           # row tick index (frame = first_tick + tick*(tempo+1))
    voice: int          # 0..2
    note: int           # freq-table index; 0 = rest / note-off
    instrument: int     # instrument index in effect
    duration: int       # duration byte in effect (holds duration+1 ticks)
    track_index: int
    pattern: int
    # A $fb/$fc slide command consumed during THIS note's fetch, as
    # (type, rate) with type 1 = $fb, 2 = $fc; None if the note is unslid.
    # The driver clears the effect slot at the top of every fetch (L09b6), so
    # a slide only ever applies to the note that immediately follows it.
    slide: Optional[Tuple[int, int]] = None

    @property
    def is_rest(self) -> bool:
        return self.note == NOTE_REST


@dataclass
class MattGraySong:
    """A parsed Matt Gray tune."""
    load_addr: int
    init_addr: int
    play_addr: int
    play_voice: int
    subtune: int
    tempo: int
    tracks: List[List[int]] = field(default_factory=list)         # per voice
    patterns: List[List[int]] = field(default_factory=list)
    pattern_addrs: List[int] = field(default_factory=list)
    instruments: List[MattGrayInstrument] = field(default_factory=list)
    freq_lo: List[int] = field(default_factory=list)
    freq_hi: List[int] = field(default_factory=list)
    arp_table_addr: int = 0
    table_addrs: Dict[str, int] = field(default_factory=dict)

    @property
    def frames_per_tick(self) -> int:
        """A row tick happens once every (tempo + 1) frames."""
        return self.tempo + 1

    def freq(self, note: int) -> int:
        """The 16-bit SID frequency the player programs for a note index."""
        if not 0 <= note < len(self.freq_lo):
            return 0
        return self.freq_lo[note] | (self.freq_hi[note] << 8)


def _u16(buf: bytes, off: int) -> int:
    return buf[off] | (buf[off + 1] << 8)


class MattGrayParser:
    """Locate and decode a Matt Gray player inside a PSID/PRG image."""

    def __init__(self, data: bytes, load_addr: int, init_addr: int,
                 play_addr: int) -> None:
        self.data = data
        self.load = load_addr
        self.init = init_addr
        self.play = play_addr
        self.play_voice = self._find_play_voice()

    # --- memory helpers ------------------------------------------------
    def _off(self, addr: int) -> int:
        off = addr - self.load
        if not 0 <= off < len(self.data):
            raise MattGrayError(
                f"address ${addr:04x} outside image "
                f"${self.load:04x}-${self.load + len(self.data) - 1:04x}")
        return off

    def byte(self, addr: int) -> int:
        return self.data[self._off(addr)]

    def word(self, addr: int) -> int:
        return _u16(self.data, self._off(addr))

    def slice(self, addr: int, n: int) -> bytes:
        o = self._off(addr)
        return self.data[o:o + n]

    # --- location ------------------------------------------------------
    def _find_play_voice(self) -> int:
        """`music_play` is `ldx #$00 / jsr play_voice / ldx #$07 / jsr ... `.

        Read the JSR operand rather than assuming play_voice sits at the
        load address -- that only happens to be true for the Driller rip.
        """
        try:
            head = self.slice(self.play, 16)
        except MattGrayError as exc:
            raise MattGrayError(f"play address unreadable: {exc}") from exc
        if len(head) < 5 or head[0] != 0xA2 or head[2] != 0x20:
            raise MattGrayError(
                f"play $%04x is not a Matt Gray music_play shim "
                f"(got {head[:5].hex(' ')}, expected 'a2 00 20 lo hi')"
                % self.play)
        pv = head[3] | (head[4] << 8)
        # the shim must call the same routine three times, with X = 0/7/14
        for i, x in enumerate(VOICE_X):
            base = i * 5
            if head[base] != 0xA2 or head[base + 1] != x:
                raise MattGrayError(
                    f"music_play voice {i} does not load X=${x:02x}")
            if head[base + 2] != 0x20 or (head[base + 3] | (head[base + 4] << 8)) != pv:
                raise MattGrayError(
                    f"music_play voice {i} does not jsr ${pv:04x}")
        return pv

    def _site(self, off: int, what: str) -> int:
        """Read a table address from an `LDA abs,y` operand at play_voice+off."""
        addr = self.play_voice + off
        opcode = self.byte(addr - 1)
        if opcode != 0xB9:
            raise MattGrayError(
                f"{what}: expected LDA abs,y ($b9) at ${addr - 1:04x}, "
                f"got ${opcode:02x} -- not a known Matt Gray build")
        return self.word(addr)

    def verify(self) -> None:
        """Check every code site looks like the expected instruction."""
        for off in _ALL_SITES:
            if self.byte(self.play_voice + off - 1) != 0xB9:
                raise MattGrayError(
                    f"code site +${off:04x} is not LDA abs,y -- "
                    f"unsupported Matt Gray variant")

    # --- decode --------------------------------------------------------
    def parse(self, subtune: int = 1) -> MattGraySong:
        self.verify()

        pat_lo = self._site(_SITE_PAT_LO, "pattern_lobytes")
        pat_hi = self._site(_SITE_PAT_HI, "pattern_hibytes")
        instr_a0 = self._site(_SITE_INSTR_A0, "instr_A0")
        instr_a1 = self._site(_SITE_INSTR_A1_4, "instr_A1") - 4
        frq_lo = self._site(_SITE_FRQ_LO, "frq_lo")
        frq_hi = self._site(_SITE_FRQ_HI, "frq_hi")
        tempo_tab = self._site(_SITE_TEMPO, "tune_tempo")
        arp_tab = self._site(_SITE_ARP_TABLE, "arpeggio_table")

        trk_sites = ((_SITE_V1_TRK_LO, _SITE_V1_TRK_HI),
                     (_SITE_V2_TRK_LO, _SITE_V2_TRK_HI),
                     (_SITE_V3_TRK_LO, _SITE_V3_TRK_HI))
        trk_tabs = [(self._site(lo, "trackptr_lo"), self._site(hi, "trackptr_hi"))
                    for lo, hi in trk_sites]

        # The lo-table is immediately followed by the hi-table, so their
        # distance is the number of tunes.  Same trick for the pattern table.
        n_tunes = trk_tabs[0][1] - trk_tabs[0][0]
        if n_tunes <= 0:
            raise MattGrayError("could not size the tune table")
        if not 0 <= subtune < n_tunes:
            raise MattGrayError(
                f"subtune {subtune} out of range (file has {n_tunes})")

        n_patterns = pat_hi - pat_lo
        if n_patterns <= 0:
            raise MattGrayError("could not size the pattern table")
        n_instr = max(0, (instr_a1 - instr_a0) // INSTR_SIZE)
        if n_instr <= 0:
            raise MattGrayError("could not size the instrument table")

        # --- tracks (orderlists), one per voice
        tracks: List[List[int]] = []
        for lo_tab, hi_tab in trk_tabs:
            base = self.byte(lo_tab + subtune) | (self.byte(hi_tab + subtune) << 8)
            tracks.append(self._read_track(base))

        # --- patterns
        pattern_addrs = [self.byte(pat_lo + i) | (self.byte(pat_hi + i) << 8)
                         for i in range(n_patterns)]
        patterns = [self._read_pattern(a) for a in pattern_addrs]

        # --- instruments
        instruments = [
            MattGrayInstrument(
                index=i,
                a0=list(self.slice(instr_a0 + i * INSTR_SIZE, INSTR_SIZE)),
                a1=list(self.slice(instr_a1 + i * INSTR_SIZE, INSTR_SIZE)),
            )
            for i in range(n_instr)
        ]

        song = MattGraySong(
            load_addr=self.load,
            init_addr=self.init,
            play_addr=self.play,
            play_voice=self.play_voice,
            subtune=subtune,
            tempo=self.byte(tempo_tab + subtune),
            tracks=tracks,
            patterns=patterns,
            pattern_addrs=pattern_addrs,
            instruments=instruments,
            freq_lo=list(self.slice(frq_lo, NUM_NOTES)),
            freq_hi=list(self.slice(frq_hi, NUM_NOTES)),
            arp_table_addr=arp_tab,
            table_addrs={
                "play_voice": self.play_voice,
                "pattern_lobytes": pat_lo, "pattern_hibytes": pat_hi,
                "instr_a0": instr_a0, "instr_a1": instr_a1,
                "frq_lo": frq_lo, "frq_hi": frq_hi,
                "tune_tempo": tempo_tab, "arpeggio_table": arp_tab,
            },
        )
        return song

    def _read_track(self, base: int, cap: int = 512) -> List[int]:
        out: List[int] = []
        for i in range(cap):
            b = self.byte(base + i)
            out.append(b)
            if b in (TRK_LOOP, TRK_STOP):
                return out
        raise MattGrayError(f"track at ${base:04x} has no $ff/$fe terminator")

    def _read_pattern(self, base: int, cap: int = 512) -> List[int]:
        out: List[int] = []
        i = 0
        while i < cap:
            b = self.byte(base + i)
            out.append(b)
            if b == PC_PAT_END:
                return out
            # control codes consume one parameter byte; that parameter must
            # not be mistaken for an $ff terminator
            if b >= PC_INSTR:
                i += 1
                out.append(self.byte(base + i))
            i += 1
        raise MattGrayError(f"pattern at ${base:04x} has no $ff terminator")


# --------------------------------------------------------------------------
# Sequencer simulation
# --------------------------------------------------------------------------

@dataclass
class _VoiceState:
    track: List[int]
    track_index: int = 0
    pattern_index: int = 0
    duration: int = 0        # sticky duration byte
    counter: int = 0         # ctrl2 countdown
    instrument: int = 0
    stopped: bool = False
    last_note: int = 0
    looped: bool = False       # track hit its $ff and wrapped to index 0


def simulate(song: MattGraySong, frames: int = 3000,
             stop_on_loop: bool = False) -> List[List[MattGrayNote]]:
    """Run the sequencer for `frames` frames and return per-voice note events.

    This mirrors the driver's control flow exactly: `tempo_ctr` ticks once per
    frame; on a tick each voice decrements its duration counter and fetches the
    next pattern event when the counter goes negative (an 8-bit `dec` + `bmi`).

    Only the *sequencer* is modelled -- the synth side (slides, arpeggios,
    PWM, the drum path) is deliberately out of scope for Stage A.
    """
    voices = [_VoiceState(track=song.tracks[v]) for v in range(3)]
    out: List[List[MattGrayNote]] = [[], [], []]

    # reset_voices leaves tempo_ctr = 1, all counters and indices zeroed
    tempo_ctr = 1
    tick = 0

    for frame in range(frames):
        if tempo_ctr == 0:
            for vi, st in enumerate(voices):
                if st.stopped:
                    continue
                st.counter = (st.counter - 1) & 0xFF
                if st.counter & 0x80:            # bmi -> fetch next event
                    ev = _fetch(song, st, vi, frame, tick)
                    if ev is not None:
                        out[vi].append(ev)
                    if stop_on_loop and st.looped:
                        st.stopped = True
            tick += 1
        # voice_done runs the tempo counter once per frame, after voice 3
        tempo_ctr = (tempo_ctr - 1) & 0xFF
        if tempo_ctr & 0x80:
            tempo_ctr = song.tempo
        if all(v.stopped for v in voices):
            break
    return out


def _fetch(song: MattGraySong, st: _VoiceState, vi: int,
           frame: int, tick: int) -> Optional[MattGrayNote]:
    """One pass of `read_note_or_ctrl`, ending when a note row is consumed."""
    # L09b6 re-derives the pattern pointer from the track on every fetch
    pat_no = st.track[st.track_index] if st.track_index < len(st.track) else 0
    if pat_no >= len(song.patterns):
        st.stopped = True
        return None
    pattern = song.patterns[pat_no]

    # L09b6 zeroes the effect slot on every fetch, so a slide seen here applies
    # only to the note this fetch is about to consume.
    slide: Optional[Tuple[int, int]] = None

    guard = 0
    while guard < 1024:
        guard += 1
        if st.pattern_index >= len(pattern):
            st.stopped = True
            return None
        b = pattern[st.pattern_index]

        if b >= PC_DUR:                       # $fd/$fe: set duration
            st.pattern_index += 1
            st.duration = pattern[st.pattern_index]
            st.pattern_index += 1
            continue
        if b >= PC_SLIDE1:                    # $fb/$fc: slide, one param byte
            st.pattern_index += 1
            slide = (1 if b == PC_SLIDE1 else 2, pattern[st.pattern_index])
            st.pattern_index += 1
            continue
        if b >= PC_INSTR:                     # $fa: set instrument
            st.pattern_index += 1
            st.instrument = pattern[st.pattern_index]
            st.pattern_index += 1
            continue

        # --- a plain note row
        note = b
        st.counter = st.duration
        ev = MattGrayNote(
            frame=frame, tick=tick, voice=vi, note=note,
            instrument=st.instrument, duration=st.duration,
            track_index=st.track_index, pattern=pat_no, slide=slide,
        )
        if note != NOTE_REST:
            st.last_note = note
        st.pattern_index += 1

        # end-of-pattern / track advance, checked right after the note
        if st.pattern_index < len(pattern) and pattern[st.pattern_index] == PC_PAT_END:
            st.pattern_index = 0
            st.track_index += 1
            if st.track_index >= len(st.track):
                st.stopped = True
            else:
                tb = st.track[st.track_index]
                if tb == TRK_LOOP:
                    st.track_index = 0
                    st.looped = True
                elif tb == TRK_STOP:
                    st.stopped = True
        return ev

    raise MattGrayError(f"pattern {pat_no} did not yield a note row")


# --------------------------------------------------------------------------
# PSID front door
# --------------------------------------------------------------------------

def load_sid(path: str) -> Tuple[bytes, int, int, int, int, int]:
    """Return (body, load, init, play, songs, startsong) for a PSID/RSID file.

    Handles the `load == 0` quirk, where the real load address is the first
    two bytes of the data block rather than the header field.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:4] not in (b"PSID", b"RSID"):
        raise MattGrayError(f"{path}: not a PSID/RSID file")
    _ver, doff, load, init, play, songs, start = struct.unpack(">HHHHHHH", raw[4:18])
    body = raw[doff:]
    if load == 0:
        load = _u16(body, 0)
        body = body[2:]
    return body, load, init, play, songs, start


def parse_sid(path: str, subtune: int = 1) -> MattGraySong:
    """Parse a Matt Gray SID straight from disk."""
    body, load, init, play, _songs, _start = load_sid(path)
    return MattGrayParser(body, load, init, play).parse(subtune=subtune)
