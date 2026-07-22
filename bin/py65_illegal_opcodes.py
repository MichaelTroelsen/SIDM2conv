"""Runtime patch adding the 6502 illegal/undocumented opcodes py65's MPU
core does not implement: LAX (LDA+TAX combined) and SBX/AXS
(X = (A & X) - operand, flags like CMP).

Found 2026-07-22 while live-tracing `SID/LFT/Crank_Crank_Airwolf.sid`'s
real compiled player code (Blackbird/LFT, see docs/players/BLACKBIRD.md):
py65's `MPU.instruct` dispatch table falls back to `inst_not_implemented`
(a silent PC-only-advance no-op) for opcodes it doesn't know, INCLUDING
these two -- both used throughout `player.s` (LAX for reading `zp_master`,
SBX for the `zp_master - 7` tick countdown). A trace running on
unpatched py65 looks entirely plausible (no crash, no error) but silently
fails to update A/X/flags on these instructions, producing register
values that diverge from real hardware more and more the longer the
trace runs -- this cost a full investigation session before being
isolated (compare a hand-derived expected register value against what
py65 actually produces; the two agreed right up to the first LAX/SBX,
then diverged).

**Any py65-based trace of ORIGINAL, hand-optimized 6502 code (not code
this project's own build scripts emit, which never use illegal opcodes)
should import this module before constructing any `MPU()` instance.**
The native Blackbird/ROMUZAK/MoN/etc. driver-tracing scripts in this
directory (which trace THIS project's own 64tass-assembled output) do
NOT need it -- only traces of the ORIGINAL compiled player binary do.

Usage::

    import py65_illegal_opcodes  # patches MPU.instruct in place, once
    from py65.devices.mpu6502 import MPU
    m = MPU()  # now correctly emulates LAX/SBX too
"""
from py65.devices.mpu6502 import MPU


def _lax(self, get_address):
    self.a = self.x = self.ByteAt(get_address())
    self.FlagsNZ(self.a)


def _sbx(self):
    # SBX/AXS #imm: X = (A & X) - operand, unsigned byte subtraction,
    # flags set like CMP (carry = 1 if no borrow, i.e. (A&X) >= operand).
    operand = self.ByteAt(self.pc)
    val = self.a & self.x
    result = (val - operand) & self.byteMask
    self.p &= ~(self.CARRY | self.ZERO | self.NEGATIVE)
    if val >= operand:
        self.p |= self.CARRY
    self.x = result
    self.FlagsNZ(self.x)
    self.pc += 1


def _inst_0xa3(self):  # LAX (zp,X)
    _lax(self, self.IndirectXAddr)
    self.pc += 1


def _inst_0xa7(self):  # LAX zp
    _lax(self, self.ZeroPageAddr)
    self.pc += 1


def _inst_0xaf(self):  # LAX abs
    _lax(self, self.AbsoluteAddr)
    self.pc += 2


def _inst_0xb3(self):  # LAX (zp),Y
    _lax(self, self.IndirectYAddr)
    self.pc += 1


def _inst_0xb7(self):  # LAX zp,Y
    _lax(self, self.ZeroPageYAddr)
    self.pc += 1


def _inst_0xbf(self):  # LAX abs,Y
    _lax(self, self.AbsoluteYAddr)
    self.pc += 2


def _inst_0xcb(self):  # SBX/AXS #imm
    _sbx(self)


_PATCHED = {
    0xa3: _inst_0xa3, 0xa7: _inst_0xa7, 0xaf: _inst_0xaf,
    0xb3: _inst_0xb3, 0xb7: _inst_0xb7, 0xbf: _inst_0xbf,
    0xcb: _inst_0xcb,
}
_CYCLES = {0xa3: 6, 0xa7: 3, 0xaf: 4, 0xb3: 5, 0xb7: 4, 0xbf: 4, 0xcb: 2}

for _op, _fn in _PATCHED.items():
    MPU.instruct[_op] = _fn
for _op, _cyc in _CYCLES.items():
    MPU.cycletime[_op] = _cyc
