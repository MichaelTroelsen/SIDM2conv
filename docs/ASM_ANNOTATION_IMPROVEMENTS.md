# ASM Annotation System - Suggested Improvements

**Document Version**: 1.0
**Date**: 2025-12-29
**Current System**: `pyscript/annotate_asm.py` (v1.0)

---

## Overview

This document outlines suggested improvements to the ASM auto-annotation system to make it more powerful, intelligent, and useful for understanding 6502 assembly code.

---

## Priority 1: High-Value Enhancements

### 1.1 Subroutine Detection and Documentation

**Goal**: Automatically identify and document subroutines with their purpose, parameters, and return values.

**Implementation**:
```python
def detect_subroutines(asm_content: str) -> Dict[int, SubroutineInfo]:
    """
    Detect subroutines by finding:
    - JSR targets (called functions)
    - RTS instructions (function boundaries)
    - Common entry patterns
    """
    subroutines = {}

    # Find all JSR targets
    jsr_targets = find_jsr_targets(asm_content)

    # For each target, analyze the code to determine purpose
    for address in jsr_targets:
        purpose = infer_subroutine_purpose(address, asm_content)
        params = detect_parameters(address, asm_content)
        returns = detect_return_values(address, asm_content)

        subroutines[address] = SubroutineInfo(
            purpose=purpose,
            parameters=params,
            returns=returns
        )

    return subroutines
```

**Example Output**:
```asm
;------------------------------------------------------------------------------
; Subroutine: Init SID Chip
; Address: $0E00
; Purpose: Initialize SID chip and clear all voices
; Parameters: None
; Returns: None
; Modifies: A (accumulator)
; Calls: None
;------------------------------------------------------------------------------
$0E00:  LDA #$00           ; Load Accumulator - Set A to 0
$0E02:  STA $D418          ; Volume/Filter Mode - Mute all voices
$0E05:  STA $D404          ; Voice 1 Control - Stop voice 1
$0E08:  STA $D40B          ; Voice 2 Control - Stop voice 2
$0E0B:  STA $D412          ; Voice 3 Control - Stop voice 3
$0E0E:  RTS                ; Return from Subroutine
```

**Benefits**:
- Understand what each function does
- See parameter passing conventions
- Identify register usage patterns
- Create better mental model of code structure

---

### 1.2 Data vs Code Section Detection

**Goal**: Distinguish between code and data sections, annotating each appropriately.

**Implementation**:
```python
def classify_sections(asm_content: bytes, load_address: int) -> List[Section]:
    """
    Classify memory regions as:
    - CODE: Executable instructions
    - DATA: Tables, strings, constants
    - MIXED: Code with embedded data (common in 6502)
    """
    sections = []

    # Use heuristics:
    # 1. Find RTS boundaries (likely code)
    # 2. Find repeating patterns (likely data)
    # 3. Look for invalid opcodes (likely data)
    # 4. Check for known table addresses

    return sections

def annotate_data_section(data: bytes, address: int, section_type: str) -> str:
    """Generate appropriate annotation for data section"""
    if section_type == "WAVE_TABLE":
        return format_wave_table(data, address)
    elif section_type == "INSTRUMENT_TABLE":
        return format_instrument_table(data, address)
    elif section_type == "SEQUENCE_DATA":
        return format_sequence_data(data, address)
    else:
        return format_hex_dump(data, address)
```

**Example Output**:
```asm
;==============================================================================
; DATA SECTION: Wave Table - Waveforms
; Address: $18DA
; Size: 32 bytes
; Format: SID waveform bytes (1 byte per instrument)
;==============================================================================
$18DA:  .byte $11, $11, $11, $11  ; Instruments 0-3: Triangle+Sawtooth
$18DE:  .byte $20, $20, $21, $21  ; Instruments 4-7: Pulse / Pulse+Triangle
$18E2:  .byte $40, $40, $41, $41  ; Instruments 8-11: Noise / Noise+Triangle
; ... (formatted as table with descriptions)

;==============================================================================
; CODE SECTION: Wave Table Access Routine
; Address: $1545
; Purpose: Load wave table data for current instrument
;==============================================================================
$1545:  LDA $18DA,Y        ; Wave Table - Waveforms - Load waveform byte
```

**Benefits**:
- Clear separation of code and data
- Data formatted appropriately (tables, hex dumps, strings)
- Easier to understand memory layout
- Better educational value

---

### 1.3 Cross-Reference Generation

**Goal**: Create cross-references showing where addresses are referenced throughout the code.

**Implementation**:
```python
def generate_cross_references(asm_content: str) -> Dict[int, List[Reference]]:
    """
    Build cross-reference table:
    - Find all references to each address
    - Track reference type (JSR, JMP, LDA, STA, etc.)
    - Build bidirectional links
    """
    xrefs = defaultdict(list)

    # Parse all instructions
    for line_num, instruction in enumerate(asm_content):
        if references_address(instruction):
            target = get_target_address(instruction)
            ref_type = get_reference_type(instruction)
            xrefs[target].append(Reference(line_num, ref_type))

    return xrefs
```

**Example Output**:
```asm
;------------------------------------------------------------------------------
; Subroutine: Play One Frame
; Address: $0EA1
; Cross-References:
;   - Called by: $0D81 (SF2 Play Routine)
;   - Calls: $0F23 (Update Voice 1)
;   - Calls: $0F56 (Update Voice 2)
;   - Calls: $0F89 (Update Voice 3)
;------------------------------------------------------------------------------
$0EA1:  JSR $0F23          ; Update Voice 1

;------------------------------------------------------------------------------
; Data: Wave Table Waveforms
; Address: $18DA
; Cross-References:
;   - Read by: $1545 (Wave Table Access #1)
;   - Read by: $1553 (Wave Table Access #2)
;   - Read by: $15A2 (Instrument Setup)
;------------------------------------------------------------------------------
$18DA:  .byte $11, $11, $11...
```

**Benefits**:
- See how code flows between subroutines
- Understand data usage patterns
- Find all callers of a function
- Navigate large codebases easily

---

### 1.4 Register Usage Analysis

**Goal**: Track register usage through subroutines to document which registers are modified.

**Implementation**:
```python
def analyze_register_usage(subroutine_address: int, asm_content: str) -> RegisterUsage:
    """
    Analyze which registers are:
    - Read (input parameters)
    - Written (output values)
    - Preserved (pushed/popped)
    - Destroyed (modified without saving)
    """
    usage = RegisterUsage()

    # Find all instructions in subroutine
    instructions = get_subroutine_instructions(subroutine_address, asm_content)

    for instr in instructions:
        if modifies_a(instr):
            usage.a_modified = True
        if modifies_x(instr):
            usage.x_modified = True
        if modifies_y(instr):
            usage.y_modified = True
        if uses_a(instr):
            usage.a_input = True
        # ... etc

    return usage
```

**Example Output**:
```asm
;------------------------------------------------------------------------------
; Subroutine: Load Instrument
; Address: $1234
; Inputs: Y = instrument number (0-7)
; Outputs: A = waveform byte
; Modifies: A (destroyed)
; Preserves: X, Y
; Cycles: 12-15 (depending on branch)
;------------------------------------------------------------------------------
$1234:  LDA instrument_table,Y  ; Load instrument data
$1237:  AND #$0F                ; Mask lower nibble
$1239:  TAX                     ; Transfer to X
$123A:  LDA waveform_table,X    ; Get waveform
$123D:  RTS
```

**Benefits**:
- Know which registers are safe to use
- Understand calling conventions
- Document side effects
- Help with optimization

---

## Priority 2: Medium-Value Enhancements

### 2.1 Pattern Recognition for Common Routines

**Goal**: Recognize common 6502 code patterns and add specialized annotations.

**Common Patterns**:
- **16-bit addition**: `CLC; ADC lo; STA result_lo; LDA hi; ADC #0; STA result_hi`
- **16-bit comparison**: Multiple CMP/SBC sequences
- **Byte copy loop**: `LDA source,X; STA dest,X; INX; BNE loop`
- **Delay loop**: `LDX #n; DEX; BNE loop`
- **Bit manipulation**: Shifting, masking patterns

**Example Output**:
```asm
; Pattern: 16-bit addition (ptr1 + offset → ptr2)
$1000:  CLC                     ; Clear Carry
$1001:  LDA $FB                 ; Load low byte of ptr1
$1003:  ADC #$20                ; Add offset low byte
$1005:  STA $FD                 ; Store to ptr2 low
$1007:  LDA $FC                 ; Load high byte of ptr1
$1009:  ADC #$00                ; Add carry to high byte
$100B:  STA $FE                 ; Store to ptr2 high
; Result: ptr2 = ptr1 + $0020

; Pattern: Memory copy loop (32 bytes)
$1020:  LDX #$00                ; Initialize counter
$1022:  LDA $1900,X             ; Load from source
$1025:  STA $1A00,X             ; Store to destination
$1028:  INX                     ; Increment counter
$1029:  CPX #$20                ; Compare with 32
$102B:  BNE $1022               ; Loop if not done
; Result: Copied 32 bytes from $1900 to $1A00
```

**Benefits**:
- Understand high-level operations from low-level code
- Recognize algorithms quickly
- Educational for learning common techniques
- Reduce cognitive load

---

### 2.2 Control Flow Visualization

**Goal**: Generate control flow diagrams showing branches, loops, and function calls.

**Implementation**:
```python
def generate_control_flow_graph(asm_content: str) -> str:
    """
    Generate ASCII art or mermaid.js diagram showing:
    - Basic blocks
    - Branch targets
    - Loop structures
    - Function calls
    """
    cfg = ControlFlowGraph()

    # Build graph
    for instruction in asm_content:
        if is_branch(instruction):
            cfg.add_edge(current_block, target_block, "conditional")
        elif is_jump(instruction):
            cfg.add_edge(current_block, target_block, "unconditional")
        elif is_jsr(instruction):
            cfg.add_edge(current_block, target_block, "call")

    return cfg.to_ascii_art()
```

**Example Output**:
```asm
;------------------------------------------------------------------------------
; Control Flow:
;
;   $0E00 (Init Entry)
;      |
;      v
;   $0E02 (Clear SID)
;      |
;      v
;   $0E15 (Setup Voices) ←──┐
;      |                    |
;      v                    |
;   $0E20 (Next Voice)      |
;      |                    |
;      |--→ [Loop] ─────────┘
;      |
;      v
;   $0E30 (Return)
;
;------------------------------------------------------------------------------
```

**Benefits**:
- Visual understanding of code flow
- Identify loop structures
- See function hierarchy
- Debugging aid

---

### 2.3 Cycle Counting

**Goal**: Calculate execution time for routines by counting cycles.

**Implementation**:
```python
# 6502 cycle counts
CYCLE_COUNTS = {
    'LDA_IMM': 2,
    'LDA_ZP': 3,
    'LDA_ABS': 4,
    'STA_ABS': 4,
    'JSR': 6,
    'RTS': 6,
    # ... etc
}

def count_cycles(instructions: List[Instruction]) -> CycleInfo:
    """Count cycles for a sequence of instructions"""
    total = 0
    min_cycles = 0
    max_cycles = 0

    for instr in instructions:
        cycles = get_cycle_count(instr)
        total += cycles.base
        if instr.has_branch:
            min_cycles += cycles.not_taken
            max_cycles += cycles.taken
        else:
            min_cycles += cycles.base
            max_cycles += cycles.base

    return CycleInfo(total, min_cycles, max_cycles)
```

**Example Output**:
```asm
;------------------------------------------------------------------------------
; Subroutine: Init SID
; Cycles: 35 (fixed timing, no branches)
; Execution Time: ~35 µs @ 1 MHz
;------------------------------------------------------------------------------
$0E00:  LDA #$00           ; 2 cycles - Load immediate
$0E02:  STA $D418          ; 4 cycles - Store absolute
$0E05:  STA $D404          ; 4 cycles - Store absolute
$0E08:  STA $D40B          ; 4 cycles - Store absolute
$0E0B:  STA $D412          ; 4 cycles - Store absolute
$0E0E:  JSR $0F00          ; 6 cycles - Call subroutine
$0E11:  RTS                ; 6 cycles - Return
                           ; ─────────
                           ; Total: 30 cycles (+ JSR overhead)
```

**Benefits**:
- Performance analysis
- Optimize timing-critical code
- Understand raster timing
- Educational for timing concepts

---

### 2.4 Symbol Table Generation

**Goal**: Extract and generate a complete symbol table with all labels and addresses.

**Implementation**:
```python
def generate_symbol_table(asm_content: str) -> str:
    """
    Generate symbol table with:
    - All subroutine addresses and names
    - All data addresses and names
    - All referenced addresses
    - Cross-reference counts
    """
    symbols = {}

    # Find all labels
    for line in asm_content:
        if is_label(line):
            address = get_address(line)
            name = infer_name(address, context)
            refs = count_references(address, asm_content)
            symbols[address] = Symbol(name, refs)

    return format_symbol_table(symbols)
```

**Example Output**:
```asm
;==============================================================================
; SYMBOL TABLE
;==============================================================================
;
; Address  Symbol                    Type        References
; -------  ------------------------  ----------  ----------
; $0D7E    sf2_init                  CODE        1 (entry point)
; $0D81    sf2_play                  CODE        1 (entry point)
; $0D84    sf2_stop                  CODE        1 (entry point)
; $0E00    laxity_init               CODE        1 (from $0D7E)
; $0EA1    laxity_play               CODE        1 (from $0D81)
; $0F23    update_voice_1            CODE        1 (from $0EA1)
; $0F56    update_voice_2            CODE        1 (from $0EA1)
; $0F89    update_voice_3            CODE        1 (from $0EA1)
; $18DA    wave_table_waveforms      DATA        4 (read)
; $190C    wave_table_note_offsets   DATA        4 (read)
; $1837    pulse_table               DATA        3 (read)
; $1A1E    filter_table              DATA        2 (read)
; $1A6B    instrument_table          DATA        8 (read)
; $199F    sequence_pointers         DATA        1 (init only)
;
; Total: 14 symbols (9 code, 5 data)
;
;==============================================================================
```

**Benefits**:
- Quick reference for all addresses
- See symbol usage at a glance
- Export for other tools
- Documentation aid

---

## Priority 3: Advanced Features

### 3.1 Interactive HTML Output

**Goal**: Generate interactive HTML with clickable cross-references and collapsible sections.

**Features**:
- Click on address → jump to definition
- Hover over register → show usage info
- Collapsible subroutine sections
- Syntax highlighting
- Search functionality
- Side-by-side view (annotated vs original)

**Example**:
```html
<div class="subroutine" id="sub_0e00">
  <div class="header" onclick="toggle(this)">
    <span class="address">$0E00</span>
    <span class="name">laxity_init</span>
    <span class="refs">Called by: <a href="#sub_0d7e">sf2_init</a></span>
  </div>
  <div class="body">
    <div class="instruction">
      <span class="address">$0E00</span>
      <span class="opcode">LDA</span>
      <span class="operand">#$00</span>
      <span class="comment">; Load Accumulator</span>
    </div>
    <!-- ... -->
  </div>
</div>
```

---

### 3.2 Diff-Friendly Output Format

**Goal**: Generate output that works well with diff tools to track changes.

**Features**:
- Consistent line lengths
- Stable formatting
- Version control friendly
- Markdown or restructured text format

---

### 3.3 Integration with Existing Documentation

**Goal**: Link annotations to project documentation files.

**Implementation**:
```python
# In annotation output:
; See also: docs/LAXITY_PLAYER_ANALYSIS.md (Wave Table Format)
; See also: docs/reference/SF2_FORMAT_SPEC.md (Driver Structure)
```

---

### 3.4 Multiple Output Formats

**Goal**: Support different output formats for different use cases.

**Formats**:
- **Plain text** - Current format
- **Markdown** - For documentation
- **HTML** - Interactive viewing
- **JSON** - For tool integration
- **LaTeX** - For printed documentation
- **Assembly source** - For assembler (with .include, etc.)

---

### 3.5 Configuration System

**Goal**: Allow users to customize annotation behavior.

**Configuration File** (`annotation_config.yaml`):
```yaml
annotation:
  inline_comments: true
  opcode_descriptions: true
  cycle_counts: false  # Disable for cleaner output

  headers:
    memory_map: true
    sid_registers: true
    laxity_tables: true
    symbol_table: true

  sections:
    detect_subroutines: true
    detect_data_sections: true
    cross_references: true

  patterns:
    detect_loops: true
    detect_16bit_ops: true
    detect_copy_routines: true

  output:
    format: "text"  # text, markdown, html, json
    max_line_length: 100
    indent_size: 2
```

---

## Implementation Priority

### Phase 1 (Immediate Value)
1. **Subroutine detection** - Most valuable for understanding code structure
2. **Data vs code sections** - Essential for correct annotation
3. **Cross-references** - High value for navigation

### Phase 2 (Enhanced Analysis)
4. **Register usage analysis** - Useful for documentation
5. **Pattern recognition** - Educational value
6. **Symbol table** - Reference aid

### Phase 3 (Advanced Features)
7. **Cycle counting** - Specialized use cases
8. **Control flow visualization** - Nice to have
9. **Interactive HTML** - Best presentation
10. **Multiple formats** - Tool integration

---

## Testing Strategy

### Unit Tests
- Test pattern recognition on known code sequences
- Verify cross-reference accuracy
- Validate cycle counts against 6502 spec

### Integration Tests
- Annotate known files (Laxity player, SF2 drivers)
- Compare against manual annotations
- Verify no regressions in existing features

### Quality Metrics
- Annotation accuracy (% of useful comments)
- Coverage (% of instructions annotated)
- Performance (annotations per second)
- User feedback (usefulness ratings)

---

## Conclusion

These improvements would transform the annotation system from a basic commenting tool into a comprehensive 6502 code analysis and documentation system. The phased approach allows for incremental value delivery while building toward advanced features.

**Next Steps**:
1. Prioritize Phase 1 features
2. Implement subroutine detection
3. Test on Laxity player code
4. Gather user feedback
5. Iterate based on usage

