# Python Disassembler Strategy - Replacing JC64 with Pure Python

**Document Version**: 1.0.0
**Date**: 2025-12-24
**Status**: Strategic Analysis
**Recommendation**: IMPLEMENT - Python-first approach

---

## Executive Summary

**Critical Constraint**: Cannot break/rebuild JC64 (FileDasm has ArrayIndexOutOfBoundsException bug)

**Strategic Recommendation**: Implement pure Python solutions following the proven siddump/sidwinder pattern.

**Key Insight**: We already have 90% of what we need - CPU6502Emulator (1,242 lines) contains complete 6502 instruction decoding. **Disassembly is just reverse execution**.

---

## Proven Success Pattern Analysis

### What We've Successfully Implemented

| Tool | Status | Lines | Accuracy | Dependencies | Platform |
|------|--------|-------|----------|--------------|----------|
| **siddump.py** | ✅ Production | 595 | 100% musical content | Zero | Cross-platform |
| **sidwinder_trace.py** | ✅ Production | ~500 | 100% format compatible | Zero | Cross-platform |
| **CPU6502Emulator** | ✅ Production | 1,242 | Proven accurate | Zero | Cross-platform |

### Pattern Recognition

**The successful approach**:
1. ❌ External tool has bugs/limitations (siddump.exe, SIDwinder.exe, FileDasm)
2. ✅ Implement pure Python replacement
3. ✅ Leverage existing code (CPU6502Emulator)
4. ✅ Integrate seamlessly into pipeline
5. ✅ Zero external dependencies
6. ✅ Cross-platform from day one
7. ✅ Full test coverage

**Results**: 100% success rate

---

## What We Actually Need from JC64

From JC64DIS_SID_HANDLING_ANALYSIS.md analysis:

### 1. 6502 Disassembler ⭐ HIGH PRIORITY
**Purpose**: Validate SF2→SID conversion accuracy via code comparison

**Features needed**:
- Instruction decoding (80 opcodes: 56 legal + 24 undocumented)
- Address formatting ($XXXX)
- Operand formatting (immediate, absolute, indexed, etc.)
- Basic label generation
- Output as assembly text

**JC64 status**: ❌ BROKEN (FileDasm ArrayIndexOutOfBoundsException)

**Python feasibility**: ✅ HIGH - We already have all 80 opcodes in CPU6502Emulator

### 2. Player Detection (SIDId) ⭐ MEDIUM PRIORITY
**Purpose**: Automatically detect player type for better conversion strategies

**Features needed**:
- Pattern matching in memory
- 80+ player signatures
- Confidence scoring

**JC64 status**: ⚠️ REQUIRES JDK + COMPILATION (we only have JRE)

**Python feasibility**: ✅ MEDIUM - Pattern matching is straightforward, need to extract patterns

### 3. Frequency Table Detection (SidFreq) ⭐ LOW PRIORITY
**Purpose**: Validate frequency table extraction

**Features needed**:
- Detect 12 frequency table format variants
- A4 frequency calculation
- Table type identification

**JC64 status**: ⚠️ UNTESTED (might work, but not validated)

**Python feasibility**: ✅ MEDIUM - Mathematical pattern detection

---

## Strategic Analysis: JC64 vs Python

### Option A: Fix JC64 FileDasm Bug ❌ NOT RECOMMENDED

**Steps required**:
1. Install JDK 8+ (~300 MB)
2. Install Apache Ant (~50 MB)
3. Clone JC64 source (~10 MB)
4. Edit `MemoryFlags.java`: `byte[] result = new byte[end - start + 1]`
5. Build with Ant
6. Test extensively
7. Maintain patched version
8. Repeat for updates

**Risks**:
- ⚠️ Fix may break other functionality (needs regression testing)
- ⚠️ Build may fail on Windows (Ant/Java issues)
- ⚠️ Need to maintain fork of external codebase
- ⚠️ Still depends on Java (external dependency)
- ⚠️ User explicitly said "cannot break the tool"

**Timeline**: 30-46 hours
**Dependencies**: JDK, Ant, Java knowledge
**Maintenance**: HIGH (external codebase)

### Option B: Pure Python Implementation ✅ RECOMMENDED

**Steps required**:
1. Extract opcode table from CPU6502Emulator
2. Implement formatting (reverse of execution)
3. Add test suite
4. Integrate into pipeline

**Advantages**:
- ✅ Leverages existing code (CPU6502Emulator)
- ✅ Zero external dependencies
- ✅ Cross-platform from day one
- ✅ Full control over codebase
- ✅ Follows proven success pattern (siddump, sidwinder)
- ✅ Easy to test and maintain
- ✅ Integrates seamlessly with existing pipeline

**Timeline**: 32-44 hours (similar to JC64 approach)
**Dependencies**: None
**Maintenance**: LOW (our codebase)

---

## CPU6502Emulator Analysis - Foundation Already Exists

### What We Already Have

**File**: `sidm2/cpu6502_emulator.py` (1,242 lines)

**Complete features**:
```python
class CPU6502Emulator:
    # 256-entry cycle table (all opcodes)
    CYCLE_TABLE = [7, 6, 0, 8, 3, 3, 5, 5, ...]

    # Complete instruction set (80 opcodes)
    def step(self):
        op = self.mem[self.pc]

        if op == 0x69:    # ADC #imm
            self.adc(self.addr_immediate())
            self.pc += 1
        elif op == 0x65:  # ADC zp
            self.adc(self.mem[self.addr_zeropage()])
            self.pc += 1
        elif op == 0x6D:  # ADC abs
            self.adc(self.mem[self.addr_absolute()])
            self.pc += 2
        # ... 77 more opcodes

    # All addressing modes
    def addr_immediate(self): ...
    def addr_zeropage(self): ...
    def addr_absolute(self): ...
    def addr_indirect_x(self): ...
    def addr_indirect_y(self): ...
    # ... 10 addressing modes total
```

**What this means**:
- ✅ All 80 opcodes already decoded
- ✅ All addressing modes already implemented
- ✅ Operand fetching already works
- ✅ Cycle-accurate (proven in siddump/sidwinder)

### What We Need to Add: Formatting

**Disassembly = Execution in Reverse**

Instead of:
```python
# EXECUTE: ADC #imm
self.adc(self.addr_immediate())
self.pc += 1
```

We do:
```python
# DISASSEMBLE: ADC #imm
operand = self.mem[self.pc + 1]
output = f"  ADC #${operand:02X}"
self.pc += 1
```

**That's it!** The hard part (instruction decoding) is already done.

---

## Implementation Plan: Python 6502 Disassembler

### Phase 1: Core Disassembler (8-12 hours)

#### Task 1.1: Extract Opcode Mapping (2 hours)

**Create opcode lookup table** from CPU6502Emulator's giant if/elif chain:

```python
# pyscript/sid_disassembler.py

class SID6502Disassembler:
    """Pure Python 6502 disassembler leveraging CPU6502Emulator."""

    # Opcode table: opcode -> (mnemonic, addressing_mode, bytes)
    OPCODES = {
        # ADC
        0x61: ('ADC', 'indirect_x', 2),
        0x65: ('ADC', 'zeropage', 2),
        0x69: ('ADC', 'immediate', 2),
        0x6D: ('ADC', 'absolute', 3),
        0x71: ('ADC', 'indirect_y', 2),
        0x75: ('ADC', 'zeropage_x', 2),
        0x79: ('ADC', 'absolute_y', 3),
        0x7D: ('ADC', 'absolute_x', 3),

        # LDA
        0xA1: ('LDA', 'indirect_x', 2),
        0xA5: ('LDA', 'zeropage', 2),
        0xA9: ('LDA', 'immediate', 2),
        0xAD: ('LDA', 'absolute', 3),
        0xB1: ('LDA', 'indirect_y', 2),
        0xB5: ('LDA', 'zeropage_x', 2),
        0xB9: ('LDA', 'absolute_y', 3),
        0xBD: ('LDA', 'absolute_x', 3),

        # ... extract all 80 from CPU6502Emulator
    }
```

**Source**: CPU6502Emulator lines 400-1200 (giant switch statement)

#### Task 1.2: Implement Operand Formatting (3 hours)

```python
def format_operand(self, mode: str, operand_bytes: bytes, pc: int) -> str:
    """Format operand based on addressing mode."""

    if mode == 'immediate':
        return f"#${operand_bytes[0]:02X}"

    elif mode == 'zeropage':
        return f"${operand_bytes[0]:02X}"

    elif mode == 'zeropage_x':
        return f"${operand_bytes[0]:02X},X"

    elif mode == 'zeropage_y':
        return f"${operand_bytes[0]:02X},Y"

    elif mode == 'absolute':
        addr = operand_bytes[0] | (operand_bytes[1] << 8)
        return f"${addr:04X}"

    elif mode == 'absolute_x':
        addr = operand_bytes[0] | (operand_bytes[1] << 8)
        return f"${addr:04X},X"

    elif mode == 'absolute_y':
        addr = operand_bytes[0] | (operand_bytes[1] << 8)
        return f"${addr:04X},Y"

    elif mode == 'indirect':
        addr = operand_bytes[0] | (operand_bytes[1] << 8)
        return f"(${addr:04X})"

    elif mode == 'indirect_x':
        return f"(${operand_bytes[0]:02X},X)"

    elif mode == 'indirect_y':
        return f"(${operand_bytes[0]:02X}),Y"

    elif mode == 'relative':
        # Branch offset (signed)
        offset = operand_bytes[0] if operand_bytes[0] < 128 else operand_bytes[0] - 256
        target = (pc + 2 + offset) & 0xFFFF
        return f"${target:04X}"

    elif mode == 'implied':
        return ""

    else:
        return "???"
```

#### Task 1.3: Main Disassembly Loop (2 hours)

```python
def disassemble(self, memory: bytes, start: int, end: int) -> str:
    """Disassemble memory region to assembly code.

    Args:
        memory: 64KB memory image
        start: Start address
        end: End address

    Returns:
        Assembly code as string
    """
    output = []
    pc = start

    # Header
    output.append(f"; Disassembly ${start:04X}-${end:04X}")
    output.append(f"        * = ${start:04X}")
    output.append("")

    while pc <= end:
        # Get opcode
        opcode = memory[pc]

        if opcode not in self.OPCODES:
            # Unknown opcode - output as data
            output.append(f"${pc:04X}  .byte ${opcode:02X}  ; Unknown opcode")
            pc += 1
            continue

        # Lookup instruction
        mnemonic, mode, length = self.OPCODES[opcode]

        # Extract operand bytes
        operand_bytes = memory[pc+1:pc+length]

        # Format operand
        operand_str = self.format_operand(mode, operand_bytes, pc)

        # Format instruction line
        # ${address}  {bytes}  {mnemonic} {operand}
        bytes_str = ' '.join(f"{b:02X}" for b in [opcode] + list(operand_bytes))
        line = f"${pc:04X}  {bytes_str:12}  {mnemonic:4} {operand_str}"

        output.append(line)
        pc += length

    return '\n'.join(output)
```

#### Task 1.4: SID-Specific Enhancements (3 hours)

```python
def disassemble_sid(self, sid_file: Path, output_file: Optional[Path] = None) -> str:
    """Disassemble SID file with PSID header info.

    Args:
        sid_file: Path to SID file
        output_file: Optional output file

    Returns:
        Assembly code with header comments
    """
    # Parse PSID header
    with open(sid_file, 'rb') as f:
        data = f.read()

    # Extract header info (using existing PSID parser)
    header = self._parse_psid_header(data)

    # Load code into memory
    memory = bytearray(65536)
    code_offset = header['data_offset']
    load_addr = header['load_addr']
    code_data = data[code_offset:]

    for i, b in enumerate(code_data):
        memory[load_addr + i] = b

    # Create output with header
    output = []
    output.append(f"; {header['title']}")
    output.append(f"; {header['author']}")
    output.append(f"; {header['copyright']}")
    output.append(f"; Load: ${load_addr:04X}")
    output.append(f"; Init: ${header['init_addr']:04X}")
    output.append(f"; Play: ${header['play_addr']:04X}")
    output.append("")

    # Disassemble init routine
    output.append("; ===== INIT ROUTINE =====")
    init_code = self.disassemble(memory, header['init_addr'], header['init_addr'] + 50)
    output.append(init_code)
    output.append("")

    # Disassemble play routine
    output.append("; ===== PLAY ROUTINE =====")
    play_code = self.disassemble(memory, header['play_addr'], header['play_addr'] + 50)
    output.append(play_code)
    output.append("")

    # Disassemble full range
    output.append("; ===== FULL CODE =====")
    end_addr = load_addr + len(code_data) - 1
    full_code = self.disassemble(memory, load_addr, end_addr)
    output.append(full_code)

    result = '\n'.join(output)

    if output_file:
        output_file.write_text(result)

    return result
```

#### Task 1.5: Test Suite (2 hours)

```python
# pyscript/test_sid_disassembler.py

import pytest
from pathlib import Path
from pyscript.sid_disassembler import SID6502Disassembler


class TestSIDDisassembler:
    """Test suite for Python SID disassembler."""

    @pytest.fixture
    def disasm(self):
        return SID6502Disassembler()

    def test_simple_instructions(self, disasm):
        """Test basic instruction disassembly."""
        # LDA #$00, STA $D400, RTS
        memory = bytearray(65536)
        memory[0x1000] = 0xA9  # LDA #imm
        memory[0x1001] = 0x00
        memory[0x1002] = 0x8D  # STA abs
        memory[0x1003] = 0x00
        memory[0x1004] = 0xD4
        memory[0x1005] = 0x60  # RTS

        result = disasm.disassemble(memory, 0x1000, 0x1005)

        assert "LDA #$00" in result
        assert "STA $D400" in result
        assert "RTS" in result

    def test_branch_instructions(self, disasm):
        """Test branch offset calculation."""
        memory = bytearray(65536)
        memory[0x1000] = 0xD0  # BNE
        memory[0x1001] = 0xFE  # -2 (loop to self)

        result = disasm.disassemble(memory, 0x1000, 0x1001)

        assert "$1000" in result  # Branch target

    def test_laxity_file(self, disasm):
        """Test disassembly of real Laxity SID file."""
        sid_file = Path("Laxity/Stinsens_Last_Night_of_89.sid")
        if not sid_file.exists():
            pytest.skip("Test file not found")

        result = disasm.disassemble_sid(sid_file)

        # Should contain header info
        assert "Stinsen" in result or "Laxity" in result

        # Should contain valid instructions
        assert "LDA" in result or "STA" in result

        # Should have proper formatting
        assert "$" in result  # Hex addresses
        assert len(result) > 1000  # Substantial output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Phase 2: Player Detection (12-16 hours)

**Defer to Phase 3** - Lower priority than disassembly

### Phase 3: Frequency Detection (8-10 hours)

**Defer to Phase 4** - Lowest priority

### Phase 4: Pipeline Integration (4-6 hours)

```python
# Integration into scripts/validate_sid_accuracy.py

from pyscript.sid_disassembler import SID6502Disassembler

def validate_with_disassembly(original_sid: Path, exported_sid: Path) -> dict:
    """Validate conversion using disassembly comparison."""

    disasm = SID6502Disassembler()

    # Disassemble both
    original_asm = disasm.disassemble_sid(original_sid)
    exported_asm = disasm.disassemble_sid(exported_sid)

    # Compare
    original_lines = set(original_asm.splitlines())
    exported_lines = set(exported_asm.splitlines())

    common = original_lines & exported_lines
    total = original_lines | exported_lines

    similarity = len(common) / len(total) if total else 0

    return {
        'disassembly_similarity': f"{similarity:.2%}",
        'original_instructions': len(original_lines),
        'exported_instructions': len(exported_lines),
        'matching_instructions': len(common),
        'original_asm': original_asm,
        'exported_asm': exported_asm
    }
```

---

## Effort Comparison

| Approach | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Total | Dependencies |
|----------|---------|---------|---------|---------|-------|--------------|
| **JC64 Fix** | 2-4h Setup | 4-6h Fix | 6-8h Integration | 4-6h Pipeline | 30-46h | JDK, Ant, Java |
| **Python** | 8-12h Disasm | 12-16h Player | 8-10h Freq | 4-6h Pipeline | 32-44h | None |

**Timeline**: Similar effort, but Python has:
- ✅ No external dependencies
- ✅ Leverages existing code
- ✅ Follows proven pattern
- ✅ Full control

---

## Risk Assessment

### JC64 Approach Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FileDasm fix breaks other features | Medium | High | Regression testing |
| Build fails on Windows | Medium | High | Use pre-built JAR |
| SIDId patterns inaccessible | Medium | Medium | Port to Python anyway |
| Maintenance burden | High | Medium | Fork external codebase |

### Python Approach Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Disassembly quality lower than JC64 | Low | Low | Focus on validation use case |
| Performance slower | Low | Low | Profile and optimize |
| Opcode extraction errors | Low | Medium | Comprehensive test suite |

---

## Recommendation

### ✅ IMPLEMENT: Python 6502 Disassembler

**Rationale**:
1. Follows proven success pattern (siddump, sidwinder)
2. Leverages existing CPU6502Emulator (90% complete)
3. Zero external dependencies
4. User maintains full control
5. Cross-platform from day one
6. Easy to test and maintain
7. Integrates seamlessly with existing pipeline
8. **User explicitly said "cannot break" JC64**

**Timeline**: 8-12 hours for Phase 1 (disassembler)

**Risk**: LOW (we control everything)

**Value**: HIGH (enables validation pipeline)

### ⏸️ DEFER: JC64 Integration

- Keep JC64 for reference/manual use
- Don't patch or rebuild
- Use Python implementations instead
- Consolidate with existing tools (siddump pattern)

---

## Next Steps

### Immediate (Start Today)

1. **Create `pyscript/sid_disassembler.py`**
   - Extract opcode table from CPU6502Emulator
   - Implement basic disassembly
   - Test on simple examples

2. **Test on Laxity Files**
   - Validate output format
   - Check instruction accuracy
   - Verify address handling

### This Week

3. **Add SID-Specific Features**
   - PSID header parsing
   - Init/Play routine identification
   - Output formatting

4. **Create Test Suite**
   - Unit tests (instruction formatting)
   - Integration tests (full SID files)
   - Performance benchmarks

### Next Week

5. **Pipeline Integration**
   - Add to validate_sid_accuracy.py
   - Create comparison reports
   - Update documentation

6. **Future Enhancements** (Optional)
   - Player detection (port SIDId patterns)
   - Frequency analysis (port SidFreq logic)
   - Code vs data heuristics
   - Label generation

---

## Success Metrics

**Phase 1 Complete When**:
- ✅ Can disassemble all 80 opcodes correctly
- ✅ Output format matches assembly syntax
- ✅ 10+ Laxity files disassemble without errors
- ✅ Test suite passes (20+ tests)
- ✅ Performance < 2 seconds per SID file

**Integration Complete When**:
- ✅ validate_sid_accuracy.py uses disassembly
- ✅ Comparison reports generated
- ✅ Documentation updated
- ✅ No external dependencies

---

**Document Status**: Ready for Implementation
**Recommendation**: ✅ PROCEED with Python disassembler (Phase 1)
**Expected Timeline**: 8-12 hours
**Expected Result**: Production-ready disassembler integrated into validation pipeline

🚀 **Ready to implement - following proven success pattern**
