"""SF2 -> native Future Composer module (.prg @ $1800), loadable in the real C64
Future Composer V1.0 editor. Closes the FC<->SF2 round-trip.

The SF2 supplies the (edited) notes; a TEMPLATE FC module supplies the player code,
freq/arp/drum tables and the 8-byte instrument records (the Driver-11 SF2 doesn't
carry FC's arp/drum bytes). Use the original FC tune as the template.

Usage:
  py -3 bin/sf2_to_fc.py edited.sf2 template.sid out.prg
  py -3 bin/sf2_to_fc.py edited.sf2 template.prg out.prg
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fc_parser import parse_fc
from sidm2.sf2_to_fc import sf2_to_fcsong
from sidm2.fc_writer import write_fc
from sidm2.sid_parser import SIDParser


def load_fc_module(path):
    raw = open(path, 'rb').read()
    if raw[:4] in (b'PSID', b'RSID'):
        h = SIDParser(path).parse_header()
        d = raw[h.data_offset:]
        la = h.load_address
        if la == 0 and len(d) >= 2:
            la = d[0] | (d[1] << 8)
            d = d[2:]
        return d, la
    return raw[2:], raw[0] | (raw[1] << 8)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    sf2_path, template_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    sf2 = open(sf2_path, 'rb').read()
    d, la = load_fc_module(template_path)
    template = parse_fc(d, la)
    song = sf2_to_fcsong(sf2, template)
    prg = write_fc(song)
    with open(out_path, 'wb') as f:
        f.write(prg)
    notes = [sum(1 for n in v if not n.is_rest) for v in song.voices]
    print(f"wrote {len(prg)} bytes -> {out_path} "
          f"(load=${prg[0] | (prg[1] << 8):04X}, sounding notes/voice={notes})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
