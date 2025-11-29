"""Full 6502 CPU Emulator for SID file execution.

This module provides a complete 6502 CPU emulator that can execute
SID files and capture SID register writes for validation.

Based on the siddump.c emulator but written in Python with enhanced
logging and debugging capabilities.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable
from enum import IntFlag


class StatusFlags(IntFlag):
    """6502 processor status flags."""
    CARRY = 0x01      # C
    ZERO = 0x02       # Z
    INTERRUPT = 0x04  # I
    DECIMAL = 0x08    # D
    BREAK = 0x10      # B
    UNUSED = 0x20     # Always 1
    OVERFLOW = 0x40   # V
    NEGATIVE = 0x80   # N


@dataclass
class SIDRegisterWrite:
    """A single SID register write event."""
    frame: int
    cycle: int
    address: int  # $D400-$D41C
    value: int
    register_name: str = ""

    def __post_init__(self):
        """Set register name based on address."""
        reg_offset = self.address - 0xD400
        names = [
            "Freq Lo 1", "Freq Hi 1", "PW Lo 1", "PW Hi 1", "Control 1", "AD 1", "SR 1",
            "Freq Lo 2", "Freq Hi 2", "PW Lo 2", "PW Hi 2", "Control 2", "AD 2", "SR 2",
            "Freq Lo 3", "Freq Hi 3", "PW Lo 3", "PW Hi 3", "Control 3", "AD 3", "SR 3",
            "FC Lo", "FC Hi", "Res/Filt", "Mode/Vol"
        ]
        if 0 <= reg_offset < len(names):
            self.register_name = names[reg_offset]


@dataclass
class FrameState:
    """State of SID at end of a frame."""
    frame: int
    cycles: int
    # Voice 1
    freq1: int = 0
    pw1: int = 0
    ctrl1: int = 0
    ad1: int = 0
    sr1: int = 0
    # Voice 2
    freq2: int = 0
    pw2: int = 0
    ctrl2: int = 0
    ad2: int = 0
    sr2: int = 0
    # Voice 3
    freq3: int = 0
    pw3: int = 0
    ctrl3: int = 0
    ad3: int = 0
    sr3: int = 0
    # Filter
    fc: int = 0
    res_filt: int = 0
    mode_vol: int = 0

    def get_voice(self, voice: int) -> Tuple[int, int, int, int, int]:
        """Get (freq, pw, ctrl, ad, sr) for voice 0-2."""
        if voice == 0:
            return (self.freq1, self.pw1, self.ctrl1, self.ad1, self.sr1)
        elif voice == 1:
            return (self.freq2, self.pw2, self.ctrl2, self.ad2, self.sr2)
        else:
            return (self.freq3, self.pw3, self.ctrl3, self.ad3, self.sr3)


class CPU6502Emulator:
    """Full 6502 CPU emulator with SID register write capture."""

    # Cycle counts for each opcode (from siddump)
    CYCLE_TABLE = [
        7, 6, 0, 8, 3, 3, 5, 5, 3, 2, 2, 2, 4, 4, 6, 6,
        2, 5, 0, 8, 4, 4, 6, 6, 2, 4, 2, 7, 4, 4, 7, 7,
        6, 6, 0, 8, 3, 3, 5, 5, 4, 2, 2, 2, 4, 4, 6, 6,
        2, 5, 0, 8, 4, 4, 6, 6, 2, 4, 2, 7, 4, 4, 7, 7,
        6, 6, 0, 8, 3, 3, 5, 5, 3, 2, 2, 2, 3, 4, 6, 6,
        2, 5, 0, 8, 4, 4, 6, 6, 2, 4, 2, 7, 4, 4, 7, 7,
        6, 6, 0, 8, 3, 3, 5, 5, 4, 2, 2, 2, 5, 4, 6, 6,
        2, 5, 0, 8, 4, 4, 6, 6, 2, 4, 2, 7, 4, 4, 7, 7,
        2, 6, 2, 6, 3, 3, 3, 3, 2, 2, 2, 2, 4, 4, 4, 4,
        2, 6, 0, 6, 4, 4, 4, 4, 2, 5, 2, 5, 5, 5, 5, 5,
        2, 6, 2, 6, 3, 3, 3, 3, 2, 2, 2, 2, 4, 4, 4, 4,
        2, 5, 0, 5, 4, 4, 4, 4, 2, 4, 2, 4, 4, 4, 4, 4,
        2, 6, 2, 8, 3, 3, 5, 5, 2, 2, 2, 2, 4, 4, 6, 6,
        2, 5, 0, 8, 4, 4, 6, 6, 2, 4, 2, 7, 4, 4, 7, 7,
        2, 6, 2, 8, 3, 3, 5, 5, 2, 2, 2, 2, 4, 4, 6, 6,
        2, 5, 0, 8, 4, 4, 6, 6, 2, 4, 2, 7, 4, 4, 7, 7,
    ]

    def __init__(self, capture_writes: bool = True):
        """Initialize CPU emulator.

        Args:
            capture_writes: If True, capture all SID register writes
        """
        self.mem = bytearray(65536)
        self.pc = 0
        self.a = 0
        self.x = 0
        self.y = 0
        self.sp = 0xFF
        self.flags = 0
        self.cycles = 0
        self.capture_writes = capture_writes
        self.sid_writes: List[SIDRegisterWrite] = []
        self.current_frame = 0
        self.max_instructions = 0x100000

    def reset(self, pc: int = 0, a: int = 0, x: int = 0, y: int = 0):
        """Reset CPU state."""
        self.pc = pc
        self.a = a
        self.x = x
        self.y = y
        self.sp = 0xFF
        self.flags = 0
        self.cycles = 0

    def load_memory(self, data: bytes, address: int):
        """Load data into memory at specified address."""
        for i, b in enumerate(data):
            if address + i < 65536:
                self.mem[address + i] = b

    def read_byte(self, addr: int) -> int:
        """Read byte from memory."""
        return self.mem[addr & 0xFFFF]

    def write_byte(self, addr: int, value: int):
        """Write byte to memory, capturing SID writes."""
        addr &= 0xFFFF
        value &= 0xFF

        # Capture SID register writes
        if self.capture_writes and 0xD400 <= addr <= 0xD41C:
            self.sid_writes.append(SIDRegisterWrite(
                frame=self.current_frame,
                cycle=self.cycles,
                address=addr,
                value=value
            ))

        self.mem[addr] = value

    def fetch(self) -> int:
        """Fetch byte at PC and increment PC."""
        val = self.mem[self.pc]
        self.pc = (self.pc + 1) & 0xFFFF
        return val

    def lo(self) -> int:
        """Get byte at PC."""
        return self.mem[self.pc]

    def hi(self) -> int:
        """Get byte at PC+1."""
        return self.mem[(self.pc + 1) & 0xFFFF]

    def push(self, value: int):
        """Push value onto stack."""
        self.mem[0x100 + self.sp] = value & 0xFF
        self.sp = (self.sp - 1) & 0xFF

    def pop(self) -> int:
        """Pop value from stack."""
        self.sp = (self.sp + 1) & 0xFF
        return self.mem[0x100 + self.sp]

    # Addressing modes
    def addr_immediate(self) -> int:
        return self.lo()

    def addr_absolute(self) -> int:
        return self.lo() | (self.hi() << 8)

    def addr_absolute_x(self) -> int:
        return ((self.lo() | (self.hi() << 8)) + self.x) & 0xFFFF

    def addr_absolute_y(self) -> int:
        return ((self.lo() | (self.hi() << 8)) + self.y) & 0xFFFF

    def addr_zeropage(self) -> int:
        return self.lo() & 0xFF

    def addr_zeropage_x(self) -> int:
        return (self.lo() + self.x) & 0xFF

    def addr_zeropage_y(self) -> int:
        return (self.lo() + self.y) & 0xFF

    def addr_indirect_x(self) -> int:
        addr = (self.lo() + self.x) & 0xFF
        return self.mem[addr] | (self.mem[(addr + 1) & 0xFF] << 8)

    def addr_indirect_y(self) -> int:
        addr = self.lo()
        base = self.mem[addr] | (self.mem[(addr + 1) & 0xFF] << 8)
        return (base + self.y) & 0xFFFF

    def page_crossing(self, base: int, real: int) -> int:
        """Check for page crossing (adds extra cycle)."""
        return 1 if ((base ^ real) & 0xFF00) else 0

    # Flag operations
    def set_nz(self, value: int):
        """Set N and Z flags based on value."""
        value &= 0xFF
        if value == 0:
            self.flags = (self.flags & ~StatusFlags.NEGATIVE) | StatusFlags.ZERO
        else:
            self.flags = (self.flags & ~(StatusFlags.NEGATIVE | StatusFlags.ZERO)) | (value & 0x80)

    def branch(self):
        """Execute branch instruction."""
        self.cycles += 1
        offset = self.fetch()
        if offset < 0x80:
            target = self.pc + offset
            self.cycles += self.page_crossing(self.pc, target)
            self.pc = target & 0xFFFF
        else:
            target = self.pc + offset - 0x100
            self.cycles += self.page_crossing(self.pc, target)
            self.pc = target & 0xFFFF

    def adc(self, value: int):
        """Add with carry."""
        if self.flags & StatusFlags.DECIMAL:
            # BCD mode
            temp = (self.a & 0xF) + (value & 0xF) + (self.flags & StatusFlags.CARRY)
            if temp > 0x9:
                temp += 0x6
            if temp <= 0x0F:
                temp = (temp & 0xF) + (self.a & 0xF0) + (value & 0xF0)
            else:
                temp = (temp & 0xF) + (self.a & 0xF0) + (value & 0xF0) + 0x10
            if not ((self.a + value + (self.flags & StatusFlags.CARRY)) & 0xFF):
                self.flags |= StatusFlags.ZERO
            else:
                self.flags &= ~StatusFlags.ZERO
            if temp & 0x80:
                self.flags |= StatusFlags.NEGATIVE
            else:
                self.flags &= ~StatusFlags.NEGATIVE
            if ((self.a ^ temp) & 0x80) and not ((self.a ^ value) & 0x80):
                self.flags |= StatusFlags.OVERFLOW
            else:
                self.flags &= ~StatusFlags.OVERFLOW
            if (temp & 0x1F0) > 0x90:
                temp += 0x60
            if (temp & 0xFF0) > 0xF0:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
        else:
            temp = value + self.a + (self.flags & StatusFlags.CARRY)
            self.set_nz(temp & 0xFF)
            if not ((self.a ^ value) & 0x80) and ((self.a ^ temp) & 0x80):
                self.flags |= StatusFlags.OVERFLOW
            else:
                self.flags &= ~StatusFlags.OVERFLOW
            if temp > 0xFF:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
        self.a = temp & 0xFF

    def sbc(self, value: int):
        """Subtract with carry."""
        temp = self.a - value - ((self.flags & StatusFlags.CARRY) ^ StatusFlags.CARRY)

        if self.flags & StatusFlags.DECIMAL:
            temp2 = (self.a & 0xF) - (value & 0xF) - ((self.flags & StatusFlags.CARRY) ^ StatusFlags.CARRY)
            if temp2 & 0x10:
                temp2 = ((temp2 - 6) & 0xF) | ((self.a & 0xF0) - (value & 0xF0) - 0x10)
            else:
                temp2 = (temp2 & 0xF) | ((self.a & 0xF0) - (value & 0xF0))
            if temp2 & 0x100:
                temp2 -= 0x60
            if temp < 0x100:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
            self.set_nz(temp & 0xFF)
            if ((self.a ^ temp) & 0x80) and ((self.a ^ value) & 0x80):
                self.flags |= StatusFlags.OVERFLOW
            else:
                self.flags &= ~StatusFlags.OVERFLOW
            self.a = temp2 & 0xFF
        else:
            self.set_nz(temp & 0xFF)
            if temp < 0x100:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
            if ((self.a ^ temp) & 0x80) and ((self.a ^ value) & 0x80):
                self.flags |= StatusFlags.OVERFLOW
            else:
                self.flags &= ~StatusFlags.OVERFLOW
            self.a = temp & 0xFF

    def cmp(self, src: int, value: int):
        """Compare."""
        temp = (src - value) & 0xFF
        self.flags = (self.flags & ~(StatusFlags.CARRY | StatusFlags.NEGATIVE | StatusFlags.ZERO)) | (temp & StatusFlags.NEGATIVE)
        if not temp:
            self.flags |= StatusFlags.ZERO
        if src >= value:
            self.flags |= StatusFlags.CARRY

    def asl_mem(self, addr: int):
        """Arithmetic shift left on memory."""
        temp = self.mem[addr] << 1
        if temp & 0x100:
            self.flags |= StatusFlags.CARRY
        else:
            self.flags &= ~StatusFlags.CARRY
        self.write_byte(addr, temp)
        self.set_nz(temp)

    def lsr_mem(self, addr: int):
        """Logical shift right on memory."""
        temp = self.mem[addr]
        if temp & 1:
            self.flags |= StatusFlags.CARRY
        else:
            self.flags &= ~StatusFlags.CARRY
        temp >>= 1
        self.write_byte(addr, temp)
        self.set_nz(temp)

    def rol_mem(self, addr: int):
        """Rotate left on memory."""
        temp = self.mem[addr] << 1
        if self.flags & StatusFlags.CARRY:
            temp |= 1
        if temp & 0x100:
            self.flags |= StatusFlags.CARRY
        else:
            self.flags &= ~StatusFlags.CARRY
        self.write_byte(addr, temp)
        self.set_nz(temp)

    def ror_mem(self, addr: int):
        """Rotate right on memory."""
        temp = self.mem[addr]
        if self.flags & StatusFlags.CARRY:
            temp |= 0x100
        if temp & 1:
            self.flags |= StatusFlags.CARRY
        else:
            self.flags &= ~StatusFlags.CARRY
        temp >>= 1
        self.write_byte(addr, temp)
        self.set_nz(temp)

    def dec_mem(self, addr: int):
        """Decrement memory."""
        temp = (self.mem[addr] - 1) & 0xFF
        self.write_byte(addr, temp)
        self.set_nz(temp)

    def inc_mem(self, addr: int):
        """Increment memory."""
        temp = (self.mem[addr] + 1) & 0xFF
        self.write_byte(addr, temp)
        self.set_nz(temp)

    def run_instruction(self) -> bool:
        """Execute one instruction.

        Returns:
            True if execution should continue, False if halted
        """
        op = self.fetch()
        self.cycles += self.CYCLE_TABLE[op]

        # Giant switch on opcode - following siddump.c structure
        if op == 0x00:  # BRK
            return False

        elif op == 0x01:  # ORA (zp,X)
            self.a |= self.mem[self.addr_indirect_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x02:  # JAM
            return False

        elif op == 0x05:  # ORA zp
            self.a |= self.mem[self.addr_zeropage()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x06:  # ASL zp
            self.asl_mem(self.addr_zeropage())
            self.pc += 1

        elif op == 0x08:  # PHP
            self.push(self.flags | 0x30)

        elif op == 0x09:  # ORA #imm
            self.a |= self.addr_immediate()
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x0A:  # ASL A
            temp = self.a << 1
            if temp & 0x100:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
            self.a = temp & 0xFF
            self.set_nz(self.a)

        elif op == 0x0D:  # ORA abs
            self.a |= self.mem[self.addr_absolute()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x0E:  # ASL abs
            self.asl_mem(self.addr_absolute())
            self.pc += 2

        elif op == 0x10:  # BPL
            if not (self.flags & StatusFlags.NEGATIVE):
                self.branch()
            else:
                self.pc += 1

        elif op == 0x11:  # ORA (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.a |= self.mem[self.addr_indirect_y()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x15:  # ORA zp,X
            self.a |= self.mem[self.addr_zeropage_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x16:  # ASL zp,X
            self.asl_mem(self.addr_zeropage_x())
            self.pc += 1

        elif op == 0x18:  # CLC
            self.flags &= ~StatusFlags.CARRY

        elif op == 0x19:  # ORA abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.a |= self.mem[self.addr_absolute_y()]
            self.set_nz(self.a)
            self.pc += 2

        elif op in (0x1A, 0x3A, 0x5A, 0x7A, 0xDA, 0xFA):  # NOP (illegal)
            pass

        elif op == 0x1D:  # ORA abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.a |= self.mem[self.addr_absolute_x()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x1E:  # ASL abs,X
            self.asl_mem(self.addr_absolute_x())
            self.pc += 2

        elif op == 0x20:  # JSR
            self.push((self.pc + 1) >> 8)
            self.push((self.pc + 1) & 0xFF)
            self.pc = self.addr_absolute()

        elif op == 0x21:  # AND (zp,X)
            self.a &= self.mem[self.addr_indirect_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x24:  # BIT zp
            val = self.mem[self.addr_zeropage()]
            self.flags = (self.flags & ~(StatusFlags.NEGATIVE | StatusFlags.OVERFLOW)) | (val & (StatusFlags.NEGATIVE | StatusFlags.OVERFLOW))
            if not (val & self.a):
                self.flags |= StatusFlags.ZERO
            else:
                self.flags &= ~StatusFlags.ZERO
            self.pc += 1

        elif op == 0x25:  # AND zp
            self.a &= self.mem[self.addr_zeropage()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x26:  # ROL zp
            self.rol_mem(self.addr_zeropage())
            self.pc += 1

        elif op == 0x28:  # PLP
            self.flags = self.pop()

        elif op == 0x29:  # AND #imm
            self.a &= self.addr_immediate()
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x2A:  # ROL A
            temp = self.a << 1
            if self.flags & StatusFlags.CARRY:
                temp |= 1
            if temp & 0x100:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
            self.a = temp & 0xFF
            self.set_nz(self.a)

        elif op == 0x2C:  # BIT abs
            val = self.mem[self.addr_absolute()]
            self.flags = (self.flags & ~(StatusFlags.NEGATIVE | StatusFlags.OVERFLOW)) | (val & (StatusFlags.NEGATIVE | StatusFlags.OVERFLOW))
            if not (val & self.a):
                self.flags |= StatusFlags.ZERO
            else:
                self.flags &= ~StatusFlags.ZERO
            self.pc += 2

        elif op == 0x2D:  # AND abs
            self.a &= self.mem[self.addr_absolute()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x2E:  # ROL abs
            self.rol_mem(self.addr_absolute())
            self.pc += 2

        elif op == 0x30:  # BMI
            if self.flags & StatusFlags.NEGATIVE:
                self.branch()
            else:
                self.pc += 1

        elif op == 0x31:  # AND (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.a &= self.mem[self.addr_indirect_y()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x35:  # AND zp,X
            self.a &= self.mem[self.addr_zeropage_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x36:  # ROL zp,X
            self.rol_mem(self.addr_zeropage_x())
            self.pc += 1

        elif op == 0x38:  # SEC
            self.flags |= StatusFlags.CARRY

        elif op == 0x39:  # AND abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.a &= self.mem[self.addr_absolute_y()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x3D:  # AND abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.a &= self.mem[self.addr_absolute_x()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x3E:  # ROL abs,X
            self.rol_mem(self.addr_absolute_x())
            self.pc += 2

        elif op == 0x40:  # RTI
            if self.sp == 0xFF:
                return False
            self.flags = self.pop()
            self.pc = self.pop()
            self.pc |= self.pop() << 8

        elif op == 0x41:  # EOR (zp,X)
            self.a ^= self.mem[self.addr_indirect_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x45:  # EOR zp
            self.a ^= self.mem[self.addr_zeropage()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x46:  # LSR zp
            self.lsr_mem(self.addr_zeropage())
            self.pc += 1

        elif op == 0x48:  # PHA
            self.push(self.a)

        elif op == 0x49:  # EOR #imm
            self.a ^= self.addr_immediate()
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x4A:  # LSR A
            if self.a & 1:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
            self.a >>= 1
            self.set_nz(self.a)

        elif op == 0x4C:  # JMP abs
            self.pc = self.addr_absolute()

        elif op == 0x4D:  # EOR abs
            self.a ^= self.mem[self.addr_absolute()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x4E:  # LSR abs
            self.lsr_mem(self.addr_absolute())
            self.pc += 2

        elif op == 0x50:  # BVC
            if not (self.flags & StatusFlags.OVERFLOW):
                self.branch()
            else:
                self.pc += 1

        elif op == 0x51:  # EOR (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.a ^= self.mem[self.addr_indirect_y()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x55:  # EOR zp,X
            self.a ^= self.mem[self.addr_zeropage_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0x56:  # LSR zp,X
            self.lsr_mem(self.addr_zeropage_x())
            self.pc += 1

        elif op == 0x58:  # CLI
            self.flags &= ~StatusFlags.INTERRUPT

        elif op == 0x59:  # EOR abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.a ^= self.mem[self.addr_absolute_y()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x5D:  # EOR abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.a ^= self.mem[self.addr_absolute_x()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0x5E:  # LSR abs,X
            self.lsr_mem(self.addr_absolute_x())
            self.pc += 2

        elif op == 0x60:  # RTS
            if self.sp == 0xFF:
                return False
            self.pc = self.pop()
            self.pc |= self.pop() << 8
            self.pc += 1

        elif op == 0x61:  # ADC (zp,X)
            self.adc(self.mem[self.addr_indirect_x()])
            self.pc += 1

        elif op == 0x65:  # ADC zp
            self.adc(self.mem[self.addr_zeropage()])
            self.pc += 1

        elif op == 0x66:  # ROR zp
            self.ror_mem(self.addr_zeropage())
            self.pc += 1

        elif op == 0x68:  # PLA
            self.a = self.pop()
            self.set_nz(self.a)

        elif op == 0x69:  # ADC #imm
            self.adc(self.addr_immediate())
            self.pc += 1

        elif op == 0x6A:  # ROR A
            temp = self.a
            if self.flags & StatusFlags.CARRY:
                temp |= 0x100
            if temp & 1:
                self.flags |= StatusFlags.CARRY
            else:
                self.flags &= ~StatusFlags.CARRY
            self.a = temp >> 1
            self.set_nz(self.a)

        elif op == 0x6C:  # JMP (ind)
            addr = self.addr_absolute()
            # 6502 bug: wraps within page
            self.pc = self.mem[addr] | (self.mem[((addr + 1) & 0xFF) | (addr & 0xFF00)] << 8)

        elif op == 0x6D:  # ADC abs
            self.adc(self.mem[self.addr_absolute()])
            self.pc += 2

        elif op == 0x6E:  # ROR abs
            self.ror_mem(self.addr_absolute())
            self.pc += 2

        elif op == 0x70:  # BVS
            if self.flags & StatusFlags.OVERFLOW:
                self.branch()
            else:
                self.pc += 1

        elif op == 0x71:  # ADC (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.adc(self.mem[self.addr_indirect_y()])
            self.pc += 1

        elif op == 0x75:  # ADC zp,X
            self.adc(self.mem[self.addr_zeropage_x()])
            self.pc += 1

        elif op == 0x76:  # ROR zp,X
            self.ror_mem(self.addr_zeropage_x())
            self.pc += 1

        elif op == 0x78:  # SEI
            self.flags |= StatusFlags.INTERRUPT

        elif op == 0x79:  # ADC abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.adc(self.mem[self.addr_absolute_y()])
            self.pc += 2

        elif op == 0x7D:  # ADC abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.adc(self.mem[self.addr_absolute_x()])
            self.pc += 2

        elif op == 0x7E:  # ROR abs,X
            self.ror_mem(self.addr_absolute_x())
            self.pc += 2

        # Skip bytes for illegal NOPs
        elif op in (0x80, 0x82, 0x89, 0xC2, 0xE2, 0x04, 0x44, 0x64,
                    0x14, 0x34, 0x54, 0x74, 0xD4, 0xF4):
            self.pc += 1

        elif op in (0x0C, 0x1C, 0x3C, 0x5C, 0x7C, 0xDC, 0xFC):
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.pc += 2

        elif op == 0x81:  # STA (zp,X)
            self.write_byte(self.addr_indirect_x(), self.a)
            self.pc += 1

        elif op == 0x84:  # STY zp
            self.write_byte(self.addr_zeropage(), self.y)
            self.pc += 1

        elif op == 0x85:  # STA zp
            self.write_byte(self.addr_zeropage(), self.a)
            self.pc += 1

        elif op == 0x86:  # STX zp
            self.write_byte(self.addr_zeropage(), self.x)
            self.pc += 1

        elif op == 0x88:  # DEY
            self.y = (self.y - 1) & 0xFF
            self.set_nz(self.y)

        elif op == 0x8A:  # TXA
            self.a = self.x
            self.set_nz(self.a)

        elif op == 0x8C:  # STY abs
            self.write_byte(self.addr_absolute(), self.y)
            self.pc += 2

        elif op == 0x8D:  # STA abs
            self.write_byte(self.addr_absolute(), self.a)
            self.pc += 2

        elif op == 0x8E:  # STX abs
            self.write_byte(self.addr_absolute(), self.x)
            self.pc += 2

        elif op == 0x90:  # BCC
            if not (self.flags & StatusFlags.CARRY):
                self.branch()
            else:
                self.pc += 1

        elif op == 0x91:  # STA (zp),Y
            self.write_byte(self.addr_indirect_y(), self.a)
            self.pc += 1

        elif op == 0x94:  # STY zp,X
            self.write_byte(self.addr_zeropage_x(), self.y)
            self.pc += 1

        elif op == 0x95:  # STA zp,X
            self.write_byte(self.addr_zeropage_x(), self.a)
            self.pc += 1

        elif op == 0x96:  # STX zp,Y
            self.write_byte(self.addr_zeropage_y(), self.x)
            self.pc += 1

        elif op == 0x98:  # TYA
            self.a = self.y
            self.set_nz(self.a)

        elif op == 0x99:  # STA abs,Y
            self.write_byte(self.addr_absolute_y(), self.a)
            self.pc += 2

        elif op == 0x9A:  # TXS
            self.sp = self.x

        elif op == 0x9D:  # STA abs,X
            self.write_byte(self.addr_absolute_x(), self.a)
            self.pc += 2

        elif op == 0xA0:  # LDY #imm
            self.y = self.addr_immediate()
            self.set_nz(self.y)
            self.pc += 1

        elif op == 0xA1:  # LDA (zp,X)
            self.a = self.mem[self.addr_indirect_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xA2:  # LDX #imm
            self.x = self.addr_immediate()
            self.set_nz(self.x)
            self.pc += 1

        # LAX illegal opcodes
        elif op == 0xA3:  # LAX (zp,X)
            self.a = self.mem[self.addr_indirect_x()]
            self.x = self.a
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xA4:  # LDY zp
            self.y = self.mem[self.addr_zeropage()]
            self.set_nz(self.y)
            self.pc += 1

        elif op == 0xA5:  # LDA zp
            self.a = self.mem[self.addr_zeropage()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xA6:  # LDX zp
            self.x = self.mem[self.addr_zeropage()]
            self.set_nz(self.x)
            self.pc += 1

        elif op == 0xA7:  # LAX zp (illegal)
            self.a = self.mem[self.addr_zeropage()]
            self.x = self.a
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xA8:  # TAY
            self.y = self.a
            self.set_nz(self.y)

        elif op == 0xA9:  # LDA #imm
            self.a = self.addr_immediate()
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xAA:  # TAX
            self.x = self.a
            self.set_nz(self.x)

        elif op == 0xAC:  # LDY abs
            self.y = self.mem[self.addr_absolute()]
            self.set_nz(self.y)
            self.pc += 2

        elif op == 0xAD:  # LDA abs
            self.a = self.mem[self.addr_absolute()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0xAE:  # LDX abs
            self.x = self.mem[self.addr_absolute()]
            self.set_nz(self.x)
            self.pc += 2

        elif op == 0xAF:  # LAX abs (illegal)
            self.a = self.mem[self.addr_absolute()]
            self.x = self.a
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0xB0:  # BCS
            if self.flags & StatusFlags.CARRY:
                self.branch()
            else:
                self.pc += 1

        elif op == 0xB1:  # LDA (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.a = self.mem[self.addr_indirect_y()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xB3:  # LAX (zp),Y (illegal)
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.a = self.mem[self.addr_indirect_y()]
            self.x = self.a
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xB4:  # LDY zp,X
            self.y = self.mem[self.addr_zeropage_x()]
            self.set_nz(self.y)
            self.pc += 1

        elif op == 0xB5:  # LDA zp,X
            self.a = self.mem[self.addr_zeropage_x()]
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xB6:  # LDX zp,Y
            self.x = self.mem[self.addr_zeropage_y()]
            self.set_nz(self.x)
            self.pc += 1

        elif op == 0xB7:  # LAX zp,Y (illegal)
            self.a = self.mem[self.addr_zeropage_y()]
            self.x = self.a
            self.set_nz(self.a)
            self.pc += 1

        elif op == 0xB8:  # CLV
            self.flags &= ~StatusFlags.OVERFLOW

        elif op == 0xB9:  # LDA abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.a = self.mem[self.addr_absolute_y()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0xBA:  # TSX
            self.x = self.sp
            self.set_nz(self.x)

        elif op == 0xBC:  # LDY abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.y = self.mem[self.addr_absolute_x()]
            self.set_nz(self.y)
            self.pc += 2

        elif op == 0xBD:  # LDA abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.a = self.mem[self.addr_absolute_x()]
            self.set_nz(self.a)
            self.pc += 2

        elif op == 0xBE:  # LDX abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.x = self.mem[self.addr_absolute_y()]
            self.set_nz(self.x)
            self.pc += 2

        elif op == 0xC0:  # CPY #imm
            self.cmp(self.y, self.addr_immediate())
            self.pc += 1

        elif op == 0xC1:  # CMP (zp,X)
            self.cmp(self.a, self.mem[self.addr_indirect_x()])
            self.pc += 1

        elif op == 0xC4:  # CPY zp
            self.cmp(self.y, self.mem[self.addr_zeropage()])
            self.pc += 1

        elif op == 0xC5:  # CMP zp
            self.cmp(self.a, self.mem[self.addr_zeropage()])
            self.pc += 1

        elif op == 0xC6:  # DEC zp
            self.dec_mem(self.addr_zeropage())
            self.pc += 1

        elif op == 0xC8:  # INY
            self.y = (self.y + 1) & 0xFF
            self.set_nz(self.y)

        elif op == 0xC9:  # CMP #imm
            self.cmp(self.a, self.addr_immediate())
            self.pc += 1

        elif op == 0xCA:  # DEX
            self.x = (self.x - 1) & 0xFF
            self.set_nz(self.x)

        elif op == 0xCC:  # CPY abs
            self.cmp(self.y, self.mem[self.addr_absolute()])
            self.pc += 2

        elif op == 0xCD:  # CMP abs
            self.cmp(self.a, self.mem[self.addr_absolute()])
            self.pc += 2

        elif op == 0xCE:  # DEC abs
            self.dec_mem(self.addr_absolute())
            self.pc += 2

        elif op == 0xD0:  # BNE
            if not (self.flags & StatusFlags.ZERO):
                self.branch()
            else:
                self.pc += 1

        elif op == 0xD1:  # CMP (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.cmp(self.a, self.mem[self.addr_indirect_y()])
            self.pc += 1

        elif op == 0xD5:  # CMP zp,X
            self.cmp(self.a, self.mem[self.addr_zeropage_x()])
            self.pc += 1

        elif op == 0xD6:  # DEC zp,X
            self.dec_mem(self.addr_zeropage_x())
            self.pc += 1

        elif op == 0xD8:  # CLD
            self.flags &= ~StatusFlags.DECIMAL

        elif op == 0xD9:  # CMP abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.cmp(self.a, self.mem[self.addr_absolute_y()])
            self.pc += 2

        elif op == 0xDD:  # CMP abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.cmp(self.a, self.mem[self.addr_absolute_x()])
            self.pc += 2

        elif op == 0xDE:  # DEC abs,X
            self.dec_mem(self.addr_absolute_x())
            self.pc += 2

        elif op == 0xE0:  # CPX #imm
            self.cmp(self.x, self.addr_immediate())
            self.pc += 1

        elif op == 0xE1:  # SBC (zp,X)
            self.sbc(self.mem[self.addr_indirect_x()])
            self.pc += 1

        elif op == 0xE4:  # CPX zp
            self.cmp(self.x, self.mem[self.addr_zeropage()])
            self.pc += 1

        elif op == 0xE5:  # SBC zp
            self.sbc(self.mem[self.addr_zeropage()])
            self.pc += 1

        elif op == 0xE6:  # INC zp
            self.inc_mem(self.addr_zeropage())
            self.pc += 1

        elif op == 0xE8:  # INX
            self.x = (self.x + 1) & 0xFF
            self.set_nz(self.x)

        elif op == 0xE9:  # SBC #imm
            self.sbc(self.addr_immediate())
            self.pc += 1

        elif op == 0xEA:  # NOP
            pass

        elif op == 0xEB:  # SBC #imm (illegal)
            self.sbc(self.addr_immediate())
            self.pc += 1

        elif op == 0xEC:  # CPX abs
            self.cmp(self.x, self.mem[self.addr_absolute()])
            self.pc += 2

        elif op == 0xED:  # SBC abs
            self.sbc(self.mem[self.addr_absolute()])
            self.pc += 2

        elif op == 0xEE:  # INC abs
            self.inc_mem(self.addr_absolute())
            self.pc += 2

        elif op == 0xF0:  # BEQ
            if self.flags & StatusFlags.ZERO:
                self.branch()
            else:
                self.pc += 1

        elif op == 0xF1:  # SBC (zp),Y
            base = self.mem[self.lo()] | (self.mem[(self.lo() + 1) & 0xFF] << 8)
            self.cycles += self.page_crossing(base, self.addr_indirect_y())
            self.sbc(self.mem[self.addr_indirect_y()])
            self.pc += 1

        elif op == 0xF5:  # SBC zp,X
            self.sbc(self.mem[self.addr_zeropage_x()])
            self.pc += 1

        elif op == 0xF6:  # INC zp,X
            self.inc_mem(self.addr_zeropage_x())
            self.pc += 1

        elif op == 0xF8:  # SED
            self.flags |= StatusFlags.DECIMAL

        elif op == 0xF9:  # SBC abs,Y
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_y())
            self.sbc(self.mem[self.addr_absolute_y()])
            self.pc += 2

        elif op == 0xFD:  # SBC abs,X
            base = self.addr_absolute()
            self.cycles += self.page_crossing(base, self.addr_absolute_x())
            self.sbc(self.mem[self.addr_absolute_x()])
            self.pc += 2

        elif op == 0xFE:  # INC abs,X
            self.inc_mem(self.addr_absolute_x())
            self.pc += 2

        else:
            # Unknown opcode - halt
            return False

        return True

    def run_until_return(self) -> int:
        """Run CPU until RTS/RTI/BRK or max instructions reached.

        Returns:
            Number of instructions executed
        """
        instr = 0
        while instr < self.max_instructions:
            # Handle VIC raster simulation for SID detection
            self.mem[0xD012] = (self.mem[0xD012] + 1) & 0xFF
            if not self.mem[0xD012] or ((self.mem[0xD011] & 0x80) and self.mem[0xD012] >= 0x38):
                self.mem[0xD011] ^= 0x80
                self.mem[0xD012] = 0x00

            if not self.run_instruction():
                break

            # Check for Kernal exit vectors
            if (self.mem[0x01] & 0x07) != 0x05 and (self.pc == 0xEA31 or self.pc == 0xEA81):
                break

            instr += 1

        return instr

    def get_frame_state(self) -> FrameState:
        """Read current SID register state."""
        return FrameState(
            frame=self.current_frame,
            cycles=self.cycles,
            freq1=self.mem[0xD400] | (self.mem[0xD401] << 8),
            pw1=(self.mem[0xD402] | (self.mem[0xD403] << 8)) & 0xFFF,
            ctrl1=self.mem[0xD404],
            ad1=self.mem[0xD405],
            sr1=self.mem[0xD406],
            freq2=self.mem[0xD407] | (self.mem[0xD408] << 8),
            pw2=(self.mem[0xD409] | (self.mem[0xD40A] << 8)) & 0xFFF,
            ctrl2=self.mem[0xD40B],
            ad2=self.mem[0xD40C],
            sr2=self.mem[0xD40D],
            freq3=self.mem[0xD40E] | (self.mem[0xD40F] << 8),
            pw3=(self.mem[0xD410] | (self.mem[0xD411] << 8)) & 0xFFF,
            ctrl3=self.mem[0xD412],
            ad3=self.mem[0xD413],
            sr3=self.mem[0xD414],
            fc=(self.mem[0xD415] << 5) | (self.mem[0xD416] << 8),
            res_filt=self.mem[0xD417],
            mode_vol=self.mem[0xD418],
        )
