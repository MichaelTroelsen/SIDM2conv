#!/usr/bin/env python3
"""Guard native SF2 drivers against SID Factory II's 6510-emulator flag bugs.

SF2II plays a native driver with its OWN bundled 6510 emulator
(`cpumos6510.cpp`), which gets compare flags wrong in two ways. Every
fidelity metric in this repo comes from py65 / zig64 / the Python simulator,
all of which implement CORRECT 6502 semantics -- so a driver that trips these
bugs measures ~100% here and still plays wrong in the editor the user
actually listens in. Percentages cannot catch this class of defect; a lint
can.

Both behaviours below were read directly from SF2II's source
(`SIDFactoryII/source/runtime/emulation/cpumos6510.cpp`), not inferred.

CMP  (uses `unsigned short`):  C set when (A-op) == 0 or bit7 clear
     -> correct iff -128 <= A-op <= 127.
CPX/CPY (use `unsigned char`): C CLEARED on equality, and set only when
     (X-op)&0xff >= 0x80 -> effectively INVERTED for any small-value
     comparison. Z is correct, so cpx/cpy + beq/bne is safe.

History: the CMP bug made the native Galway driver silent in SF2II
(2026-06-14). The CPX/CPY inversion was found 2026-07-24 chasing an ear
report on a Blackbird build measuring 98.6% overall / 99.9% filter -- two of
its three carry-after-cpy sites were the hard-restart dispatch, so the real
editor fired the restart pre-steps for exactly the wrong instruments.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
DRIVER_GLOB = "drivers_src/*/*.asm"

# Only carry branches are affected -- the Z flag is correct in all three.
CARRY_BRANCH = re.compile(r'^\s*(bcc|bcs)\b', re.I)
CPXY = re.compile(r'^\s*(cpx|cpy)\s+(\S+)', re.I)
CMP_IMM = re.compile(r'^\s*cmp\s+#\$?([0-9a-fA-F]+)\s*(;.*)?$')


LABEL = re.compile(r'^\S+:?\s*$|^\S+:')

# Genuine, still-unfixed hazards -- allowlisted so NEW ones fail the build
# while the known debt stays visible instead of being silently suppressed.
#
# Galway's and ROMUZAK's `fp_dec` classify filter rows with `cmp #$90; bcs`
# and no high-bit guard. ADD rows carry byte0 in [$00,$0F] (a 4-bit delta),
# which is >128 below $90, so SF2II sets carry the WRONG way and executes
# every such ADD row as a SET row -- their filter sweeps are broken in the
# editor while measuring clean offline. Blackbird had the identical bug until
# B24 widened its own threshold to `cmp #$80` for unrelated reasons, which
# happens to be safe for every A and incidentally fixed it there.
#
# Not fixed here because each needs its own corpus re-verification (the
# encodings differ) -- tracked in docs/ROADMAP.md.
KNOWN_UNFIXED = {
    "galway_driver.asm:cmp #$90",
    "romuzak_driver.asm:cmp #$90",
}


def _guarded_by_high_bit_split(code, idx):
    """True if a `cmp #$80` + `bcc` dominates code[idx] in its basic block.

    Scans back to the nearest label; that is conservative (a label may be
    fallen into rather than jumped to) but never produces a false PASS for
    the straight-line classifier chains this guards.
    """
    for j in range(idx - 1, -1, -1):
        _, prev = code[j]
        if LABEL.match(prev.strip()) and not prev.startswith((' ', '\t')):
            return False
        if re.match(r'^\s*cmp\s+#\$?80\s*$', prev, re.I):
            for _, nxt in code[j + 1: j + 3]:
                if re.match(r'^\s*bcc\b', nxt, re.I):
                    return True
    return False


def _code_lines(path):
    """(1-based lineno, text) for lines that carry an instruction."""
    out = []
    for i, raw in enumerate(path.read_text(errors='ignore').splitlines(), 1):
        line = raw.split(';', 1)[0].rstrip()
        if line.strip():
            out.append((i, line))
    return out


def find_cpxy_carry_sites(path, lookahead=3):
    """cpx/cpy whose flags reach a bcc/bcs before any other compare."""
    code = _code_lines(path)
    hits = []
    for idx, (lineno, line) in enumerate(code):
        m = CPXY.match(line)
        if not m:
            continue
        for _, nxt in code[idx + 1: idx + 1 + lookahead]:
            if CARRY_BRANCH.match(nxt):
                hits.append((lineno, line.strip(), nxt.strip()))
                break
            # another compare re-defines carry -- this cpx/cpy no longer
            # reaches a carry branch
            if re.match(r'^\s*(cmp|cpx|cpy)\b', nxt, re.I):
                break
    return hits


class TestNoCarryBranchAfterCpxCpy(unittest.TestCase):
    """SF2II inverts CPX/CPY carry, so branching on it is always a bug there.

    Use `txa`/`tya` + `cmp` (keeping operands within +/-127), or restructure
    to test the Z flag with beq/bne, which SF2II gets right.
    """

    def test_no_driver_branches_on_carry_after_cpx_cpy(self):
        offenders = []
        drivers = sorted(ROOT.glob(DRIVER_GLOB))
        self.assertTrue(drivers, "no driver .asm files found -- glob wrong?")
        for path in drivers:
            for lineno, cmp_line, br_line in find_cpxy_carry_sites(path):
                offenders.append(
                    f"{path.relative_to(ROOT)}:{lineno}: {cmp_line!r} -> {br_line!r}")
        self.assertEqual(
            offenders, [],
            "SF2II's 6510 emulator INVERTS the carry flag for CPX/CPY "
            "(cpumos6510.cpp clears C on equality and sets it only when "
            "(X-op)&0xff >= 0x80), so these branch the wrong way in the real "
            "editor while every offline metric still reads clean. Replace "
            "with txa/tya + cmp, or branch on Z instead:\n  "
            + "\n  ".join(offenders))


class TestCmpOperandsStayInWindow(unittest.TestCase):
    """SF2II's CMP is correct only for |A - operand| <= 127.

    A full check needs A's reachable range, which is not statically known, so
    this flags the shape that is unsafe for SOME reachable A: an immediate
    strictly between $01 and $7f compares fine against small values but wrong
    against high ones, and vice versa. $80 is always safe (max distance is
    exactly 128 on the low side, which still resolves correctly), which is
    why "split on the high bit" is the house rule.
    """

    def test_high_immediates_are_only_the_safe_high_bit_split(self):
        """Only CARRY branches are at risk.

        `cmp #$ff; beq` is safe no matter what A is -- SF2II's Z flag is
        correct, and equality tests against sentinels like $fe/$ff are all
        over these drivers. The hazard is specifically a high immediate whose
        CARRY result is then branched on, which is what made the native
        Galway driver silent (`cmp #$c0; bcc` against note byte $19).
        """
        suspicious = []
        for path in sorted(ROOT.glob(DRIVER_GLOB)):
            code = _code_lines(path)
            for idx, (lineno, line) in enumerate(code):
                m = CMP_IMM.match(line)
                if not m:
                    continue
                val = int(m.group(1), 16) if '$' in line else int(m.group(1))
                if val <= 0x80:          # $80 is the safe high-bit split
                    continue
                if _guarded_by_high_bit_split(code, idx):
                    # A `cmp #$80; bcc` earlier in this basic block proves
                    # A >= $80 here, so even `cmp #$ff` is <= $7f away. This
                    # is the documented house fix (see parse_one in every
                    # driver) and must not be reported as a hazard.
                    continue
                key = f"{path.name}:{line.strip()}"
                if key in KNOWN_UNFIXED:
                    continue
                for _, nxt in code[idx + 1: idx + 4]:
                    if CARRY_BRANCH.match(nxt):
                        suspicious.append(
                            f"{path.relative_to(ROOT)}:{lineno}: "
                            f"{line.strip()!r} -> {nxt.strip()!r}")
                        break
                    if re.match(r'^\s*(cmp|cpx|cpy)\b', nxt, re.I):
                        break
        self.assertEqual(
            suspicious, [],
            "cmp against an immediate above $80 is >127 away from small "
            "values of A, where SF2II's CMP sets carry the wrong way (this "
            "is what made the native Galway driver silent). Split on the "
            "high bit with `cmp #$80` first:\n  " + "\n  ".join(suspicious))


class TestFlagSemanticsAreDocumentedCorrectly(unittest.TestCase):
    """Pin the emulator's actual behaviour, so the lint's rationale is
    checkable rather than folklore."""

    @staticmethod
    def _sf2ii_cmp_carry(a, op):
        v = (a - op) & 0xFFFF          # unsigned short in the C++
        return 1 if (v == 0 or (v & 0x80) == 0) else 0

    @staticmethod
    def _sf2ii_cpxy_carry(x, op):
        v = (x - op) & 0xFF            # unsigned char in the C++
        return 1 if (v != 0 and (v & 0x80) != 0) else 0

    def test_cmp_hash_80_is_safe_for_every_a(self):
        for a in range(256):
            self.assertEqual(self._sf2ii_cmp_carry(a, 0x80), 1 if a >= 0x80 else 0,
                             f"cmp #$80 diverges at A=${a:02x}")

    def test_cmp_wide_operand_is_unsafe(self):
        # The Galway case: note $19 vs `cmp #$c0`.
        self.assertNotEqual(self._sf2ii_cmp_carry(0x19, 0xC0),
                            1 if 0x19 >= 0xC0 else 0)

    def test_cpxy_carry_is_inverted_for_small_values(self):
        # Blackbird's hard-restart thresholds: slots 0..31 vs 5 and 9.
        for op in (5, 9):
            for x in range(32):
                real = 1 if x >= op else 0
                self.assertEqual(self._sf2ii_cpxy_carry(x, op), 1 - real,
                                 f"expected inversion at X={x}, op={op}")

    def test_cpxy_clears_carry_on_equality(self):
        self.assertEqual(self._sf2ii_cpxy_carry(9, 9), 0)   # real 6502: 1


if __name__ == '__main__':
    unittest.main()
