"""Regression tests for the CPU6502Emulator SBC carry/borrow flag.

The bug: SBC computed its carry-out as `temp < 0x100` where temp = A - M - borrow
ranges [-256, 255], so the condition was ALWAYS true -> carry was stuck SET after
every SBC. That corrupted multi-byte (16-bit) subtraction chains (SEC; SBC lo; SBC
hi) which rely on the low byte's borrow propagating into the high byte. The MoN
(Hawkeye/Cybernoid) vibrato uses such a chain, so siddump produced a wrong vibrato
depth and the native driver (built from siddump) sounded wrong "when vibrating".

A real 6502 sets carry after SBC iff no borrow occurred (temp >= 0).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidm2.cpu6502_emulator import CPU6502Emulator, StatusFlags


def _run(program, a=0, x=0, y=0, mem=None):
    """Load `program` bytes at $1000, run them until an RTS ($60) returns to the
    $0000 sentinel, and return the CPU. `mem` = dict of preset memory cells."""
    cpu = CPU6502Emulator(capture_writes=False)
    for i, b in enumerate(program):
        cpu.mem[0x1000 + i] = b
    if mem:
        for addr, val in mem.items():
            cpu.mem[addr] = val
    cpu.reset(0x1000, a, x, y)
    for _ in range(1000):
        if cpu.pc == 0x0000:
            break
        if not cpu.run_instruction():
            break
    return cpu


def test_sbc_no_borrow_sets_carry():
    # SEC; SBC #$01  with A=$05 -> $04, carry SET (no borrow)
    cpu = _run([0x38, 0xE9, 0x01, 0x60], a=0x05)
    assert cpu.a == 0x04
    assert cpu.flags & StatusFlags.CARRY


def test_sbc_borrow_clears_carry():
    # SEC; SBC #$05  with A=$01 -> $FC, carry CLEAR (borrow occurred)
    cpu = _run([0x38, 0xE9, 0x05, 0x60], a=0x01)
    assert cpu.a == 0xFC
    assert not (cpu.flags & StatusFlags.CARRY)


def test_sbc_exact_zero_sets_carry():
    # SEC; SBC #$05  with A=$05 -> $00, carry SET (no borrow), zero set
    cpu = _run([0x38, 0xE9, 0x05, 0x60], a=0x05)
    assert cpu.a == 0x00
    assert cpu.flags & StatusFlags.CARRY
    assert cpu.flags & StatusFlags.ZERO


def test_16bit_subtraction_borrow_propagates():
    # The exact bug class: 16-bit subtract $0100 - $0001 = $00FF.
    #   SEC
    #   LDA $20 ; SBC $22 ; STA $24   (low byte: $00 - $01 = $FF, borrow)
    #   LDA $21 ; SBC $23 ; STA $25   (high byte: $01 - $00 - borrow = $00)
    prog = [
        0x38,                   # SEC
        0xA5, 0x20, 0xE5, 0x22, 0x85, 0x24,   # lo
        0xA5, 0x21, 0xE5, 0x23, 0x85, 0x25,   # hi
        0x60,
    ]
    cpu = _run(prog, mem={0x20: 0x00, 0x21: 0x01, 0x22: 0x01, 0x23: 0x00})
    result = cpu.mem[0x24] | (cpu.mem[0x25] << 8)
    assert result == 0x00FF, f"16-bit SBC gave ${result:04X}, expected $00FF"


def test_16bit_subtraction_no_low_borrow():
    # $0200 - $0001 = $01FF: low $00-$01 borrows, high $02-$00-1 = $01.
    prog = [
        0x38,
        0xA5, 0x20, 0xE5, 0x22, 0x85, 0x24,
        0xA5, 0x21, 0xE5, 0x23, 0x85, 0x25,
        0x60,
    ]
    cpu = _run(prog, mem={0x20: 0x00, 0x21: 0x02, 0x22: 0x01, 0x23: 0x00})
    result = cpu.mem[0x24] | (cpu.mem[0x25] << 8)
    assert result == 0x01FF, f"16-bit SBC gave ${result:04X}, expected $01FF"
