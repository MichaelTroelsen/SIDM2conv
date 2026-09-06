"""Report or assert a file's line-ending convention, by BYTE COUNT.

    py -3 endings.py <file> [<file> ...]
    py -3 endings.py <file> --expect crlf|lf     # exits 1 on a mismatch

Byte counts, never `grep -c '\\r'` -- that counts LINES CONTAINING a carriage
return and answered 549 on a 549-line pure-LF file in this repo.
"""
import sys
from pathlib import Path


def counts(path: Path):
    raw = path.read_bytes()
    crlf = raw.count(b"\r\n")
    return crlf, raw.count(b"\n") - crlf, b"\x00" in raw


def label(crlf: int, lf: int) -> str:
    if crlf and lf:
        return "MIXED"
    if crlf:
        return "crlf"
    if lf:
        return "lf"
    return "none"


def main(argv) -> int:
    expect = None
    if "--expect" in argv:
        i = argv.index("--expect")
        expect = argv[i + 1].lower()
        argv = argv[:i] + argv[i + 2:]

    files = [Path(a) for a in argv]
    if not files:
        print(__doc__)
        return 2

    rc = 0
    for f in files:
        if not f.is_file():
            print("%-52s MISSING" % f)
            rc = 1
            continue
        crlf, lf, has_nul = counts(f)
        kind = label(crlf, lf)
        note = "  <-- NUL byte: git treats this as BINARY" if has_nul else ""
        print("%-52s %-5s  crlf=%-6d lf=%-6d%s" % (f, kind, crlf, lf, note))
        if kind == "MIXED":
            rc = 1
        if expect and kind != expect:
            print("     EXPECTED %s, GOT %s" % (expect, kind))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
