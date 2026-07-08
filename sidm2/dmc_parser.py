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
    freq: int = 0            # interleaved lo/hi freq table (note*2)
    trk_lo: int = 0          # per-voice track (orderlist) pointer tables (lo/hi)
    trk_hi: int = 0
    trk_pos: int = 0         # per-voice track-position array (init state)


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
        #   (2) the freq TABLE load: LDA freq,y / STA acc_lo,x ; LDA freq+1,y /
        #       STA acc_hi,x  (interleaved table into the stride-3 accumulator)
        if acc_lo is not None and acc_hi is not None:
            for i in _find_all(d, [0xB9, None, None, 0x9D, acc_lo & 0xFF, acc_lo >> 8,
                                   0xB9, None, None, 0x9D, acc_hi & 0xFF, acc_hi >> 8]):
                lo = d[i + 1] | (d[i + 2] << 8)
                hi = d[i + 7] | (d[i + 8] << 8)
                if hi == lo + 1:
                    lay.freq = lo
                    break

        # per-voice track pointer tables: LDA trk_lo,x / STA z ; LDA trk_hi,x / STA z
        for i in _find_all(d, [0xBD, None, None, 0x85, None,
                               0xBD, None, None, 0x85, None]):
            lo = d[i + 1] | (d[i + 2] << 8)
            hi = d[i + 6] | (d[i + 7] << 8)
            if hi > lo and d[i + 4] != d[i + 9]:
                lay.trk_lo, lay.trk_hi = lo, hi
                break
        return lay

    # ---- accessors ----
    def sector_ptr(self, sector):
        return (self._u8(self.lay.sector_lo + sector)
                | (self._u8(self.lay.sector_hi + sector) << 8))

    def note_freq(self, note):
        base = self.lay.freq + (note & 0x7F) * 2
        return self._u8(base) | (self._u8(base + 1) << 8)

    def sound(self, n):
        b = self.lay.sound + (n & 0x1F) * 8
        return [self._u8(b + k) for k in range(8)]


def summary(path):
    d, la, h = load_sid(path)
    m = DMCModule(d, la)
    L = m.lay
    return (f"load=${la:04X} init=${h.init_address:04X} play=${h.play_address:04X} "
            f"sector=${L.sector_lo:04X}/${L.sector_hi:04X} sound=${L.sound:04X} "
            f"freq=${L.freq:04X} trk=${L.trk_lo:04X}/${L.trk_hi:04X}")
