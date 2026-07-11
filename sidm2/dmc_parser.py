"""DMC (Demo Music Creator) player parser — Johannes Bjerregaard corpus.

Format RE'd 2026-07-08 from the play routine (see memory/johannes-bjerregaard-
player.md). The player is RELOCATABLE (many load addresses), so every table is
located by a code SIGNATURE, never hardcoded — same discipline as the Hubbard/
Laxity parsers.

Model: Track (orderlist) -> Sector (pattern) -> Sound (instrument).
- Track, per voice: bytes = sector numbers; $FF = loop, $FE = end.
- Sector-pointer table (lo/hi) indexed by sector number -> sector data.
- Sector event: command byte (dur = low 5 bits, flags = top 3); if cmd bit7 a
  Sound byte follows; if cmd bit6 two effect bytes follow; then a pitch byte.
  $FF ends the sector.
- Sound: 8-byte records [AD, SR, PWinit, PWrails, PWspeed, vib, filt6, flags7].
- Freq table: interleaved lo/hi, indexed by note*2.
"""
import struct
from dataclasses import dataclass


def load_sid(path):
    """Return (data_bytes_at_load, load_addr, header). PSID/RSID; resolves the
    embedded load word when the header load field is 0."""
    raw = open(path, "rb").read()
    dataoff = struct.unpack(">H", raw[6:8])[0]
    load = struct.unpack(">H", raw[8:10])[0]
    init = struct.unpack(">H", raw[0x0A:0x0C])[0]
    play = struct.unpack(">H", raw[0x0C:0x0E])[0]
    nsongs = struct.unpack(">H", raw[0x0E:0x10])[0]
    if load == 0:
        load = raw[dataoff] | (raw[dataoff + 1] << 8)
        data = raw[dataoff + 2:]
    else:
        data = raw[dataoff:]

    class H:
        pass
    h = H()
    h.init_address, h.play_address, h.nsongs = init, play, nsongs
    return bytes(data), load, h


def _find_all(d, sig):
    out = []
    n = len(sig)
    for i in range(len(d) - n):
        if all(s is None or d[i + k] == s for k, s in enumerate(sig)):
            out.append(i)
    return out


@dataclass
class DMCLayout:
    sector_lo: int = 0        # sector-pointer table lo / hi (indexed by sector#)
    sector_hi: int = 0
    sound: int = 0            # 8-byte sound (instrument) records
    freq: int = 0            # freq table lo bytes (interleaved note*2 if freq_hi==0)
    freq_hi: int = 0         # 0 = interleaved (freq[note*2]); else SPLIT hi array (freq[note] / freq_hi[note])
    trk_lo: int = 0          # per-voice track (orderlist) pointer tables (lo/hi)
    trk_hi: int = 0
    trk_interleaved: bool = False  # track ptrs interleaved lo/hi, indexed voice*2 (a
                                   # generation where TXA/ASL/TAY -> LDA trk,Y; hi=lo+1)
    trk_pos: int = 0         # per-voice track-position array (init state)
    tempo_reload: int = 0    # frames/tick immediate (DEC tempo/BPL/LDA #imm/STA)
    tempo_addr: int = 0      # the global tempo counter address


class DMCModule:
    """Detected DMC module. Addresses are signature-located (relocation-safe)."""

    def __init__(self, d, la):
        self.d, self.la = d, la
        self.lay = self._locate()

    def _u8(self, addr):
        off = addr - self.la
        return self.d[off] if 0 <= off < len(self.d) else 0

    def _rel(self, off):
        return self.la + off

    def _locate(self):
        d = self.d
        lay = DMCLayout()

        # sector-pointer table: LDA sect_lo,y / STA z / LDA sect_hi,y / STA z
        #   (BD/B9 <lo> ; 85 z ; BD/B9 <hi> ; 85 z), hi = lo + 0x80 in Balloon but
        #   don't assume — read both operands.
        for i in _find_all(d, [0xB9, None, None, 0x85, None,
                               0xB9, None, None, 0x85, None]):
            lo = d[i + 1] | (d[i + 2] << 8)
            hi = d[i + 6] | (d[i + 7] << 8)
            if hi > lo and d[i + 4] != d[i + 9]:      # two distinct ZP stores
                lay.sector_lo, lay.sector_hi = lo, hi
                break

        # sound table: a run of LDA sound+K,y reads (K = 0..7). The AD read is
        #   `LDA sound,y / STA $D405,x` — locate via STA $D405,x preceded by
        #   LDA abs,y.
        for i in _find_all(d, [0xB9, None, None, 0x9D, 0x05, 0xD4]):
            lay.sound = d[i + 1] | (d[i + 2] << 8)
            break
        # FALLBACK for the absolute-store generation (Thunder_Force / M_A_C_H): the
        # per-voice apply is UNROLLED, so voice 1's AD is `LDA base,Y / STA $D405`
        # with an ABSOLUTE store (8D), not $D405,X. AD/SR are consecutive here, so
        # base = the AD-field address serves m.sound (s[0]=AD, s[1]=SR).
        if not lay.sound:
            for i in _find_all(d, [0xB9, None, None, 0x8D, 0x05, 0xD4]):
                lay.sound = d[i + 1] | (d[i + 2] << 8)
                break
        # FALLBACK for the "state" generation (In_the_Mood class): AD/SR aren't
        # written straight to $D405/6 — the note-on copies the record into per-voice
        # state via `LDA base,Y / STA st,X / LDA base+1,Y / AND #$0F` (SR nibble).
        # Anchor on that AD+SR read pair. (The snd generation is multi-idiom; other
        # variants store the offset and index the table with a different shape — they
        # need per-version dataflow RE, so this catches only the AND-#$0F sub-variant.)
        if not lay.sound:
            for i in _find_all(d, [0xB9, None, None, 0x9D, None, None,
                                   0xB9, None, None, 0x29, 0x0F]):
                base = d[i + 1] | (d[i + 2] << 8)
                if (d[i + 7] | (d[i + 8] << 8)) == base + 1:   # AD (+0) then SR (+1)
                    lay.sound = base
                    break
        # FALLBACK for the stack/indexed-store generations (Special_Agent / Spy /
        # Twilight): the per-voice apply reloads the store index (`LDY var,X`) between
        # the field read and the SID write, so the AD/SR write is
        #   LDA field,Y / LDY var,X / STA $D405,Y   (AD, sound = field)   or
        #   LDA field,Y / LDY var,X / STA $D406,Y   (SR, sound = field-1; AD/SR adjacent)
        if not lay.sound:
            for i in _find_all(d, [0xB9, None, None, 0xBC, None, None, 0x99, 0x05, 0xD4]):
                lay.sound = d[i + 1] | (d[i + 2] << 8)         # AD field
                break
        if not lay.sound:
            for i in _find_all(d, [0xB9, None, None, 0xBC, None, None, 0x99, 0x06, 0xD4]):
                lay.sound = (d[i + 1] | (d[i + 2] << 8)) - 1   # SR field -> AD = SR-1
                break
        # FALLBACK for the state-COPY generation (Flimbos_Quest / Kamikaze / Myth_Demo
        # / Stormlord_V2 / STII8): note-on zeroes per-voice state then copies the sound
        # record into it — `LDA #$00 / STA st,X / STA st,X / LDA sound_ad,Y / STA
        # ad_state,X`. The AD state later drives $D405. Anchor on that AD load; the
        # `B9` operand is the sound table's AD field (record base).
        if not lay.sound:
            for i in _find_all(d, [0xA9, 0x00, 0x9D, None, None, 0x9D, None, None,
                                   0xB9, None, None, 0x9D, None, None]):
                lay.sound = d[i + 9] | (d[i + 10] << 8)
                break
        # FALLBACK for the abs,X staged-emit generation (Eagles / Camel_Riders /
        # Ragtime / Spacegame / Who_Is_Robb): the emit indexes the sound record with
        # X = sound#*8 and stores via Y = voice reg offset:
        #   LDA ad,X / STA $D405,Y ; LDA ad+1,X / STA $D406,Y   (AD/SR adjacent)
        # lay.sound = the AD field (record stride 8, so s[0]=AD, s[1]=SR line up).
        if not lay.sound:
            for i in _find_all(d, [0xBD, None, None, 0x99, 0x05, 0xD4,
                                   0xBD, None, None, 0x99, 0x06, 0xD4]):
                ad = d[i + 1] | (d[i + 2] << 8)
                if (d[i + 7] | (d[i + 8] << 8)) == ad + 1:
                    lay.sound = ad
                    break

        # freq table: two steps (avoids matching the sound table's AD/SR reads).
        #   (1) the freq accumulator lo/hi from the D400/D401 emit. The player
        #       state is per-voice STRIDE-3 arrays, so acc_lo and acc_hi are NOT
        #       consecutive (Balloon $1011 / $1014).
        acc_lo = acc_hi = None
        for i in _find_all(d, [0xBD, None, None, 0x99, 0x00, 0xD4]):
            acc_lo = d[i + 1] | (d[i + 2] << 8)
            break
        for i in _find_all(d, [0xBD, None, None, 0x99, 0x01, 0xD4]):
            acc_hi = d[i + 1] | (d[i + 2] << 8)
            break
        # ADC-vibrato generation (Domino_Dancing / Alf_TV_Theme / Music_Demo / Test):
        # the accumulator is written with a per-frame vibrato add, so the emit is
        #   LDA acc_lo,X / CLC / ADC vib,X / STA $D400,Y   (lo, carry cleared)
        #   LDA acc_hi,X /       ADC vib,X / STA $D401,Y   (hi, carry propagates)
        # -> the acc is the LDA operand, not the ADC (vibrato) operand.
        if acc_lo is None:
            for i in _find_all(d, [0xBD, None, None, 0x18, 0x7D, None, None,
                                   0x99, 0x00, 0xD4]):
                acc_lo = d[i + 1] | (d[i + 2] << 8)
                break
        if acc_hi is None:
            for i in _find_all(d, [0xBD, None, None, 0x7D, None, None,
                                   0x99, 0x01, 0xD4]):
                acc_hi = d[i + 1] | (d[i + 2] << 8)
                break
        #   (2) the freq TABLE load: LDA freq_lo,y / STA acc_lo,x ; LDA freq_hi,y /
        #       STA acc_hi,x. Two table layouts: INTERLEAVED (Balloon: one array,
        #       note*2 -> freq_hi == freq_lo+1) and SPLIT (the $3f00 "Fat"
        #       generation: separate lo/hi arrays, like MoN -> freq_hi far above).
        if acc_lo is not None and acc_hi is not None:
            for i in _find_all(d, [0xB9, None, None, 0x9D, acc_lo & 0xFF, acc_lo >> 8,
                                   0xB9, None, None, 0x9D, acc_hi & 0xFF, acc_hi >> 8]):
                lo = d[i + 1] | (d[i + 2] << 8)
                hi = d[i + 7] | (d[i + 8] << 8)
                if hi == lo + 1:              # interleaved: freq[note*2]
                    lay.freq = lo
                    break
                if hi > lo + 1:              # split: freq_lo[note] / freq_hi[note]
                    lay.freq, lay.freq_hi = lo, hi
                    break
        # FALLBACK for the abs,X staged-emit generation (Eagles class): freq is read
        # interleaved via `ASL A / TAY / LDA freq,Y / STA staging(abs) / LDA freq+1,Y`
        # and only later stored to $D400/1 from the staging var — so the acc-anchored
        # step-2 above never matches.
        if not lay.freq:
            for i in _find_all(d, [0x0A, 0xA8, 0xB9, None, None, 0x8D, None, None,
                                   0xB9, None, None]):
                lo = d[i + 3] | (d[i + 4] << 8)
                if (d[i + 9] | (d[i + 10] << 8)) == lo + 1:
                    lay.freq = lo            # interleaved (note*2)
                    break

        # per-voice track pointer tables: LDA trk_lo,x / STA z ; LDA trk_hi,x / STA z
        for i in _find_all(d, [0xBD, None, None, 0x85, None,
                               0xBD, None, None, 0x85, None]):
            lo = d[i + 1] | (d[i + 2] << 8)
            hi = d[i + 6] | (d[i + 7] << 8)
            if hi > lo and d[i + 4] != d[i + 9]:
                lay.trk_lo, lay.trk_hi = lo, hi
                break

        # INTERLEAVED-TRACK generation (Deel_2 / Fruitbank / Slimbo4): the primary
        # BD-form track sig misses because the track ptr is read `TXA / ASL / TAY /
        # LDA trk,Y / STA z / LDA trk+1,Y / STA z2` (Y = voice*2, interleaved lo/hi).
        # WORSE, that same read matches the sector-ptr sig FIRST, so `sector_lo` was
        # mis-set to the TRACK table. When we detect this idiom, take the track from
        # it (interleaved, voice*2) AND re-locate the real SECTOR table, which is the
        # SPLIT `TAY / LDA sec_lo,Y / STA z / LDA sec_hi,Y / STA z2` read.
        if not lay.trk_lo:
            for i in _find_all(d, [0x8A, 0x0A, 0xA8, 0xB9, None, None, 0x85, None,
                                   0xB9, None, None, 0x85, None]):
                lo = d[i + 4] | (d[i + 5] << 8)
                hi = d[i + 9] | (d[i + 10] << 8)
                if hi == lo + 1 and d[i + 7] != d[i + 12]:
                    lay.trk_lo, lay.trk_hi = lo, lo + 1
                    lay.trk_interleaved = True
                    break
            if lay.trk_interleaved:
                for i in _find_all(d, [0xA8, 0xB9, None, None, 0x85, None,
                                       0xB9, None, None, 0x85, None]):
                    sl = d[i + 2] | (d[i + 3] << 8)
                    sh = d[i + 7] | (d[i + 8] << 8)
                    if sh > sl + 1 and d[i + 5] != d[i + 10]:
                        lay.sector_lo, lay.sector_hi = sl, sh  # override the mislabel
                        break

        # tempo: DEC tempo / BPL / LDA #imm / STA tempo (same addr) — the reload
        # immediate is the per-tune speed (baked per relocated player). Several
        # sites match this idiom (per-voice waveform/wavetable counters too);
        # the real TEMPO counter is a single GLOBAL byte, never accessed indexed
        # (,x / ,y), whereas per-voice counters are (STA $addr,x). Pick the
        # candidate whose address has NO indexed reference.
        indexed = set()               # addresses touched by abs,x / abs,y ops
        for j in range(len(d) - 2):
            op = d[j]
            if op in (0xBD, 0x9D, 0xB9, 0x99, 0xBC, 0x1E, 0xDE, 0xFE,
                      0x3D, 0x5D, 0x7D, 0xDD, 0xFD, 0x1D, 0x39, 0x59, 0x79,
                      0xD9, 0xF9, 0x19):
                indexed.add(d[j + 1] | (d[j + 2] << 8))
        cands = []
        for i in _find_all(d, [0xCE, None, None, 0x10, None, 0xA9, None,
                               0x8D, None, None]):
            if d[i + 1] == d[i + 8] and d[i + 2] == d[i + 9]:
                cands.append((d[i + 1] | (d[i + 2] << 8), d[i + 6]))
        glob = [(a, r) for a, r in cands if a not in indexed]
        if glob:
            lay.tempo_addr, lay.tempo_reload = glob[0]
        elif cands:
            lay.tempo_addr, lay.tempo_reload = cands[0]
        return lay

    # ---- accessors ----
    def sector_ptr(self, sector):
        return (self._u8(self.lay.sector_lo + sector)
                | (self._u8(self.lay.sector_hi + sector) << 8))

    def note_freq(self, note):
        n = note & 0x7F
        if self.lay.freq_hi:                      # SPLIT lo/hi arrays
            return self._u8(self.lay.freq + n) | (self._u8(self.lay.freq_hi + n) << 8)
        base = self.lay.freq + n * 2              # INTERLEAVED (note*2)
        return self._u8(base) | (self._u8(base + 1) << 8)

    def sound(self, n):
        b = self.lay.sound + (n & 0x1F) * 8
        return [self._u8(b + k) for k in range(8)]


@dataclass
class DMCNote:
    ticks: int                # duration in note-ticks (cmd & $1F, +1)
    pitch: int = -1           # note index into the freq table (-1 = none/rest)
    sound: int = -1           # instrument (-1 = keep)
    effect: tuple = ()        # (byte1, byte2) when cmd bit6 set
    flag5: int = 0            # cmd bit5


def _voice_track_ptr(m, voice):
    """Per-voice track (orderlist) data pointer, from the lo/hi tables. The
    interleaved generation packs lo/hi consecutively, indexed by voice*2."""
    if m.lay.trk_interleaved:
        base = m.lay.trk_lo + voice * 2
        return m._u8(base) | (m._u8(base + 1) << 8)
    return (m._u8(m.lay.trk_lo + voice) | (m._u8(m.lay.trk_hi + voice) << 8))


def decode_track(m, voice, max_sectors=512):
    """Sector-number list for a voice until $FF (loop) / $FE (end)."""
    ptr = _voice_track_ptr(m, voice)
    out, i, loop = [], 0, False
    while i < max_sectors:
        b = m._u8(ptr + i)
        if b == 0xFF:
            loop = True
            break
        if b == 0xFE:
            break
        out.append(b)
        i += 1
    return out, loop


def decode_sector(m, sector, max_events=256):
    """Decode one sector (pattern) into [DMCNote]. Follows the play routine:
    command byte (dur low5 / bit5 flag / bit6 = 2 effect bytes / bit7 = sound
    byte) then a pitch byte; a $C0 top-3-bits value is a sector control (end/
    jump) — treated as end here; a bare $FF ends the sector."""
    ptr = m.sector_ptr(sector)
    out, y, cur_sound = [], 0, -1
    for _ in range(max_events):
        cmd = m._u8(ptr + y)
        if cmd == 0xFF:
            break
        y += 1
        dur = (cmd & 0x1F) + 1
        if (cmd & 0xE0) == 0xC0:      # REST: duration, no note (consumes 1 byte)
            out.append(DMCNote(ticks=dur, pitch=-1))
            continue
        flag5 = cmd & 0x20
        sound = -1
        if cmd & 0x80:                # sound byte follows
            sound = m._u8(ptr + y); y += 1
            cur_sound = sound
        eff = ()
        if cmd & 0x40:                # two effect bytes follow
            eff = (m._u8(ptr + y), m._u8(ptr + y + 1)); y += 2
        pitch = m._u8(ptr + y); y += 1
        out.append(DMCNote(ticks=dur, pitch=pitch, sound=sound, effect=eff,
                           flag5=flag5))
    return out


def decode_song(m, song=0, tick_budget=4000):
    """Per-voice flat [(tick, DMCNote)] streams. Walks each voice's track ->
    sectors, expanding the track loop up to tick_budget ticks."""
    voices = []
    for v in range(3):
        sectors, loop = decode_track(m, v)
        evs, tk, guard = [], 0, 0
        si = 0
        while tk < tick_budget and guard < 100000:
            guard += 1
            if si >= len(sectors):
                if loop and sectors:
                    si = 0
                else:
                    break
            for n in decode_sector(m, sectors[si]):
                evs.append((tk, n))
                tk += n.ticks
                if tk >= tick_budget:
                    break
            si += 1
        voices.append(evs)
    return voices


def measure_onsets(d, la, init_addr, play_addr, frames, song=0,
                   within_frame=False):
    """EXACT per-voice note-onset frames via py65 replay: the frame of every
    $D404 gate-rise (bit0 0->1). Ground truth for note placement — sidesteps the
    tick/tempo model entirely. Returns [ [frames...] x3 ]. (Valid only where the
    tune runs at 1x under a single play-call/frame; multispeed/self-IRQ variants
    read too slow — caller should sanity-check vs siddump.)

    within_frame=True detects gate rises in the WRITE STREAM instead of the
    end-of-frame register state: players that retrigger by writing gate OFF
    then ON inside one play call (Sound Monitor's note-set) leave the frame
    state 1->1, so the state-based scan misses EVERY such retrigger — the
    note plays legato, the envelope never re-attacks, and the build renders
    at half loudness while every per-frame register metric reads 100%."""
    # siddump CPU + $D012 raster fake + banking — a bare py65 diverges on players
    # that read the raster ($D012) or bank ROMs (the same reason Hubbard's
    # measure_tick_schedule uses it).
    from sidm2.cpu6502_emulator import CPU6502Emulator
    cpu = CPU6502Emulator()
    cpu.load_memory(bytes(d), la)
    cpu.mem[0x01] = 0x37

    def call(a, acc=0):
        cpu.mem[0xD012] = (cpu.mem[0xD012] + 1) & 0xFF
        if (cpu.mem[0xD012] == 0
                or ((cpu.mem[0xD011] & 0x80) and cpu.mem[0xD012] >= 0x38)):
            cpu.mem[0xD011] ^= 0x80
            cpu.mem[0xD012] = 0x00
        cpu.reset(a, acc & 0xFF, 0, 0)
        for _ in range(1_000_000):
            if not cpu.run_instruction():
                return

    call(init_addr, song)
    onsets = [[], [], []]
    prev = [0, 0, 0]
    if within_frame:
        wfreg = {0xD404: 0, 0xD40B: 1, 0xD412: 2}
        for fr in range(frames):
            n0 = len(cpu.sid_writes)
            call(play_addr)
            hit = [False, False, False]
            for w in cpu.sid_writes[n0:]:
                v = wfreg.get(w.address)
                if v is None:
                    continue
                g = w.value & 1
                if g == 1 and prev[v] == 0 and not hit[v]:
                    onsets[v].append(fr)
                    hit[v] = True
                prev[v] = g
        return onsets
    for fr in range(frames):
        call(play_addr)
        for v in range(3):
            g = cpu.mem[0xD404 + v * 7] & 1
            if g == 1 and prev[v] == 0:      # gate re-attack = a note onset
                onsets[v].append(fr)
            prev[v] = g
    return onsets


def summary(path):
    d, la, h = load_sid(path)
    m = DMCModule(d, la)
    L = m.lay
    return (f"load=${la:04X} init=${h.init_address:04X} play=${h.play_address:04X} "
            f"sector=${L.sector_lo:04X}/${L.sector_hi:04X} sound=${L.sound:04X} "
            f"freq=${L.freq:04X} trk=${L.trk_lo:04X}/${L.trk_hi:04X}")
