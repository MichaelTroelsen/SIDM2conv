"""Decode Block 3 (DriverTables) of two SF2 files and print each table
descriptor for comparison.

Usage: py -3 pyscript/diff_block3.py <file_a.sf2> <file_b.sf2>
"""
import struct, sys
from pathlib import Path

def find_block3(buf):
    """Find Block 3 in the SF2 file by walking from the magic. Returns
    (block_payload_offset, block_size) or (None, None)."""
    # Magic 0x1337 LE at offset 0 of header area; SF2 file format places
    # blocks sequentially as TLV. Block format: u8 id, u16 size, u8 body[size].
    # Headers start at file offset 0 (the SF2 has a small load-addr prefix
    # and then header blocks). For a quick decode, scan the first 1024 bytes
    # for `id=3` followed by a plausible size word, then validate by walking.
    # Simpler: blocks are emitted in id order 1,2,3,... after the load addr.
    p = 2  # skip 2-byte $0D7E load address
    # SF2 magic 2 bytes (0x37 0x13)
    if buf[p:p+2] != b'\x37\x13':
        # try without load-addr prefix
        if buf[0:2] == b'\x37\x13':
            p = 0
    if buf[p:p+2] == b'\x37\x13':
        p += 2
    # Walk blocks. SF2 block format: [id:1][size:1][body]
    while p < len(buf) - 2:
        bid = buf[p]
        bsize = buf[p+1]
        body = p + 2
        if bid == 0xff:
            return None, None
        if bid == 3:
            return body, bsize
        p = body + bsize
    return None, None


def decode_block3(body, size):
    """Yield TableDefinition records per ParseDriverTables in driver_info.cpp."""
    end = size
    p = 0
    tables = []
    while p < end:
        if body[p] == 0xff:
            break
        td = {}
        td['type']           = body[p]; p += 1
        td['id']             = body[p]; p += 1
        td['textfieldsize']  = body[p]; p += 1
        # null-term string
        nstart = p
        while p < end and body[p] != 0: p += 1
        td['name'] = body[nstart:p].decode('latin-1', errors='replace')
        p += 1  # skip null
        td['layout']         = body[p]; p += 1
        td['properties']     = body[p]; p += 1
        td['ins_del_rule']   = body[p]; p += 1
        td['enter_rule']     = body[p]; p += 1
        td['color_rule']     = body[p]; p += 1
        td['address']        = body[p] | (body[p+1] << 8); p += 2
        td['cols']           = body[p] | (body[p+1] << 8); p += 2
        td['rows']           = body[p] | (body[p+1] << 8); p += 2
        td['vis_rows']       = body[p]; p += 1
        tables.append(td)
    return tables


def main(argv):
    files = [Path(a) for a in argv[:2]]
    rows = []
    for f in files:
        buf = f.read_bytes()
        body_off, sz = find_block3(buf)
        if body_off is None:
            print(f'!! could not find Block 3 in {f}'); rows.append([]); continue
        ts = decode_block3(buf[body_off:body_off+sz], sz)
        rows.append(ts)
        print(f'\n=== {f}  Block 3 @ offset 0x{body_off:04x} size={sz} bytes  ({len(ts)} tables) ===')
        hdr = ('idx', 'type', 'id', 'tfs', 'name', 'lay', 'prop', 'ins', 'ent', 'col', 'addr', 'cols', 'rows', 'vis')
        print('  ' + ' '.join(f'{h:>4s}' for h in hdr))
        for i, t in enumerate(ts):
            print(f'  [{i:>2d}] {t["type"]:#04x} {t["id"]:#04x} {t["textfieldsize"]:>3d} {t["name"]:<11s} '
                  f'{t["layout"]:#04x} {t["properties"]:#04x} {t["ins_del_rule"]:#04x} {t["enter_rule"]:#04x} '
                  f'{t["color_rule"]:#04x} ${t["address"]:04X} {t["cols"]:>3d} {t["rows"]:>3d} {t["vis_rows"]:>3d}')

    # If both decoded, show side-by-side differences for matching name
    if len(rows) == 2 and rows[0] and rows[1]:
        print('\n--- side-by-side (matched on name) ---')
        names_a = {t['name']: t for t in rows[0]}
        names_b = {t['name']: t for t in rows[1]}
        all_names = sorted(set(names_a) | set(names_b))
        for n in all_names:
            a = names_a.get(n); b = names_b.get(n)
            if a is None or b is None:
                print(f'  {n}: only in {"A" if a else "B"}')
                continue
            diffs = [k for k in a if a[k] != b[k]]
            if diffs:
                print(f'  {n} diffs: ' + ', '.join(f'{k}: {a[k]!r} vs {b[k]!r}' for k in diffs))

if __name__ == '__main__':
    main(sys.argv[1:])
