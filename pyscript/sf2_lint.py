"""Compare an SF2 file's Block 1 / Block 5 structural fields against the
patterns observed in bundled SF2II reference files. Flags mismatches that
plausibly explain "SF2II crashes on load".

Usage: python pyscript/sf2_lint.py <our_file.sf2> [<reference.sf2> ...]
"""
import sys, os, glob


def parse_blocks(data):
    if data[2:4] != b'\x37\x13':
        raise ValueError("missing 0x1337 magic")
    out = {}
    off = 4
    while off + 1 < len(data):
        bid = data[off]
        if bid == 0xFF:
            break
        sz = data[off + 1]
        out[bid] = data[off + 2: off + 2 + sz]
        off += 2 + sz
    return out


def parse_block1(b1):
    i = 0
    drv_type = b1[i]; i += 1
    drv_size = b1[i] | (b1[i+1] << 8); i += 2
    ne = b1.index(0, i)
    name_raw = bytes(b1[i:ne])
    i = ne + 1
    code_top = b1[i] | (b1[i+1] << 8); i += 2
    code_sz  = b1[i] | (b1[i+1] << 8); i += 2
    ver_maj = b1[i] if i < len(b1) else None; i += 1
    ver_min = b1[i] if i < len(b1) else None; i += 1
    ver_rev = b1[i] if i < len(b1) else None
    return dict(drv_type=drv_type, drv_size=drv_size, name=name_raw,
                code_top=code_top, code_sz=code_sz,
                ver_maj=ver_maj, ver_min=ver_min, ver_rev=ver_rev)


def decode_petscii_name(b):
    return ''.join(chr(x + 0x60) if 1 <= x <= 0x1A else
                   (chr(x) if x >= 0x20 else f'<{x:02X}>') for x in b)


def lint(path, reference_top=0x1000):
    data = open(path, 'rb').read()
    print(f'\n=== {path} ({len(data)}B) ===')
    load_addr = data[0] | (data[1] << 8)
    print(f'  PRG load addr: ${load_addr:04X}')
    blocks = parse_blocks(data)
    print(f'  Block IDs present: {sorted(blocks)}')

    issues = []
    if 1 not in blocks:
        issues.append('CRIT: no Block 1 (Descriptor)')
    else:
        b1 = parse_block1(blocks[1])
        print(f'  Block 1: drv_type=${b1["drv_type"]:02X} drv_size=${b1["drv_size"]:04X} '
              f'name={b1["name"]!r} ({decode_petscii_name(b1["name"])!r})')
        print(f'    code_top=${b1["code_top"]:04X} code_sz=${b1["code_sz"]:04X} '
              f'ver={b1["ver_maj"]}.{b1["ver_min"]}.{b1["ver_rev"]}')
        if b1['code_top'] != reference_top:
            issues.append(
                f'CRIT: driver_code_top=${b1["code_top"]:04X} '
                f'(reference bundled files all use ${reference_top:04X})'
            )
        if b1['code_top'] + b1['code_sz'] > 0x10000:
            issues.append(f'CRIT: code_top+code_sz overflows C64 RAM')
        if b1['drv_size'] > 0x4000:
            issues.append(
                f'WARN: driver_size=${b1["drv_size"]:04X} unusually large '
                f'(bundled files: $0216-$0834)'
            )
        # Sanity: name should be PETSCII-encoded mixed case (lower bytes 0x01-0x1A)
        if all(b >= 0x20 for b in b1['name']):
            issues.append(
                f'WARN: name {b1["name"]!r} is plain ASCII; bundled files '
                f'use PETSCII (lowercase as 0x01-0x1A)'
            )

    for required in (2, 3, 4, 5):
        if required not in blocks:
            issues.append(f'CRIT: Block {required} missing')

    if issues:
        for it in issues:
            print(f'  -> {it}')
    else:
        print('  -> all checks pass')
    return issues


def gather_reference():
    """Pull driver_code_top from all bundled-good files; flag the consensus."""
    files = sorted(glob.glob('bin/music/**/*.sf2', recursive=True))
    tops = []
    for f in files:
        try:
            d = open(f, 'rb').read()
            blks = parse_blocks(d)
            if 1 in blks:
                tops.append(parse_block1(blks[1])['code_top'])
        except Exception:
            pass
    if tops:
        # most common
        from collections import Counter
        c = Counter(tops)
        print(f'Reference driver_code_top from {len(tops)} bundled files: {dict(c)}')
        return c.most_common(1)[0][0]
    return 0x1000


def main(argv):
    ref_top = gather_reference()
    targets = argv or [
        'stinsen_v330.sf2',
        'stinsen_v322_final.sf2',
        'unboxed_v330.sf2',
    ]
    failures = 0
    for t in targets:
        if not os.path.exists(t):
            print(f'\n=== {t} === MISSING')
            continue
        issues = lint(t, reference_top=ref_top)
        failures += sum(1 for i in issues if i.startswith('CRIT'))
    print(f'\n{failures} CRIT issue(s) across all files')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
