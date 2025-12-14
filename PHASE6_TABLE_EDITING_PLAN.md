# Phase 6: Table Editing Support Implementation Plan

**Status**: Ready for Implementation
**Estimated Effort**: 8-12 hours
**Approach**: Native Format Support (Laxity tables directly editable in SF2 editor)

---

## Executive Summary

Phase 6 enables full SF2 editor table editing for the Laxity driver by properly defining all Laxity tables in the SF2 header blocks. This allows users to edit sequences, instruments, wave tables, pulse tables, and filter tables directly in SID Factory II.

**Key Goal**: Make all Laxity tables visible and editable in SF2 editor

---

## Current State (v1.8.0)

### What Works ✅
- Laxity driver conversion: 100% success (286/286 files)
- Music playback: 70-90% accuracy
- Basic SF2 structure created
- Tables injected at correct addresses

### What's Missing ❌
- SF2 header blocks don't properly describe tables for editor
- Table descriptors incomplete (missing properties)
- Column/row counts not defined
- Data layout not specified (row-major vs column-major)
- Edit operations may not work in SF2 editor

### Current Table Definitions

| Table | Address | Entries | Size | Format |
|-------|---------|---------|------|--------|
| Sequences | $1900 | 3 voices | Variable | Custom |
| Filter | $1A1E | 32 | 128 bytes | Row-major (4 bytes each) |
| Pulse | $1A3B | 64 | 256 bytes | Row-major (4 bytes each) |
| Instruments | $1A6B | 32 | 256 bytes | Row-major (8 bytes each) |
| Wave | $1ACB | 128 | 256 bytes | Row-major (2 bytes each) |

---

## Phase 6 Implementation Tasks

### Task 1: Analyze SF2 Header Block Format (2-3 hours)

**Goal**: Understand exactly how SF2 editor expects table descriptors

**What to Research**:
1. Reverse-engineer existing driver table descriptors
   - Extract headers from working SF2 drivers (Driver 11, NP20)
   - Analyze TableDefinition structure from SF2 source
   - Understand block format: ID, size, data structure

2. Document table descriptor format
   - Block ID (typically 3 = DriverTables)
   - Table properties (insert/delete, color rules, etc.)
   - Data layout flags (row-major vs column-major)
   - Column/row count definitions

3. Understand SF2 editor expectations
   - How does editor discover tables?
   - What properties enable table editing?
   - How are column/row sizes interpreted?

**Deliverables**:
- Table descriptor analysis report
- SF2 header block format documentation
- Property requirements checklist

---

### Task 2: Design Laxity Table Descriptors (2-3 hours)

**Goal**: Design proper table descriptor blocks for each Laxity table

**Tables to Define**:

1. **Sequences** ($1900)
   - Type: Generic (0x00) or custom
   - Columns: Variable (voices)
   - Rows: Variable (sequence length)
   - Data layout: Custom format
   - Properties: TBD based on SF2 format

2. **Instruments** ($1A6B)
   - Type: Instruments (0x80)
   - Columns: 8 bytes per instrument
   - Rows: 32 entries
   - Data layout: Row-major
   - Properties: Enable insert/delete
   - Fields: ADSR, waveform, pulse, etc.

3. **Wave Table** ($1ACB)
   - Type: Generic (0x00)
   - Columns: 2 bytes per entry (waveform index, note offset)
   - Rows: 128 entries
   - Data layout: Row-major
   - Properties: Enable viewing/editing

4. **Pulse Table** ($1A3B)
   - Type: Generic (0x00)
   - Columns: 4 bytes per entry
   - Rows: 64 entries
   - Data layout: Row-major
   - Properties: Show as 4-byte values

5. **Filter Table** ($1A1E)
   - Type: Generic (0x00)
   - Columns: 4 bytes per entry
   - Rows: 32 entries
   - Data layout: Row-major
   - Properties: Show as 4-byte filter values

**Deliverables**:
- Table descriptor specifications
- Column/row count matrix
- Data layout justifications
- Property settings per table

---

### Task 3: Generate/Update SF2 Header Blocks (3-4 hours)

**Goal**: Create/modify SF2 header blocks with proper table descriptors

**Implementation Approach**:

1. **Create Python Header Generator** (`sidm2/sf2_header_generator.py`)
   - Generate block 1: Driver Descriptor
   - Generate block 2: Driver Common
   - Generate block 3: Driver Tables
   - Add optional blocks (color rules, action rules if needed)
   - Inject into driver binary

2. **Update LaxityConverter** (`sidm2/laxity_converter.py`)
   - Call header generator before injecting tables
   - Ensure proper memory layout
   - Validate header structure

3. **Build Process**
   - Regenerate `sf2driver_laxity_00.prg` with proper headers
   - Verify header blocks are present and valid
   - Test with sample conversions

**Pseudo-code Structure**:
```python
class SF2HeaderGenerator:
    def generate_descriptor_block(self):
        """Generate Block 1: Driver Descriptor"""
        # File ID, driver name, entry points, version

    def generate_common_block(self):
        """Generate Block 2: Driver Common"""
        # Address references (init, play, stop, etc.)

    def generate_tables_block(self):
        """Generate Block 3: Driver Tables"""
        # For each table: type, ID, columns, rows, layout, properties

    def generate_complete_headers(self):
        """Generate all header blocks with end marker"""
        # Combine all blocks, add 0xFF end marker
```

**Deliverables**:
- `sidm2/sf2_header_generator.py` - Header block generator
- Updated `sf2driver_laxity_00.prg` - Driver with proper headers
- Build script updates

---

### Task 4: Validation & Testing (2-3 hours)

**Goal**: Verify tables are properly defined and editable

**Unit Tests**:
1. Header block structure validation
   - Magic number present (0x1337)
   - All required blocks present
   - Block IDs and sizes correct
   - End marker present (0xFF)

2. Table descriptor validation
   - All 5 tables defined
   - Correct addresses
   - Column/row counts reasonable
   - Data layout specified

3. Round-trip validation
   - Convert SID → SF2
   - Load SF2 in hex editor, verify structure
   - Attempt to open in SF2 editor
   - Verify tables visible

**Integration Testing**:
1. SID Factory II Compatibility
   - Open converted SF2 in SID Factory II
   - Verify tables appear in editor
   - Attempt to edit each table type
   - Play music after editing (if supported)

2. File Integrity
   - Verify converted files still play correctly
   - Check for data corruption
   - Validate output size (should be ~10-41 KB as before)

**Test Cases**:
- Small SID (minimal tables)
- Large SID (many sequences/instruments)
- Edge case: Single voice, minimal instrument set
- Edge case: All instruments used

**Deliverables**:
- Unit tests (`test_laxity_headers.py`)
- Integration test results
- SF2 editor compatibility report

---

### Task 5: Documentation (1-2 hours)

**Goal**: Document table editing feature for users and developers

**User Documentation** (LAXITY_DRIVER_TABLE_EDITING_GUIDE.md):
- How to edit tables in SF2 editor
- Which tables are editable
- Editing guidelines and tips
- Limitations and known issues
- Best practices

**Developer Documentation** (PHASE6_IMPLEMENTATION_REPORT.md):
- Header block structure details
- Table descriptor format specification
- Implementation approach and decisions
- Technical challenges and solutions
- Future enhancements

**Update Existing Documentation**:
- LAXITY_DRIVER_QUICK_START.md: Add table editing section
- LAXITY_DRIVER_FAQ.md: Add table editing Q&As
- README.md: Update status and features

**Deliverables**:
- LAXITY_DRIVER_TABLE_EDITING_GUIDE.md
- PHASE6_IMPLEMENTATION_REPORT.md
- Updated documentation files

---

## Implementation Strategy

### Approach: Native Format (Recommended)

**Philosophy**: Define Laxity tables directly in SF2 format without format translation

**Advantages**:
- ✅ No data conversion needed
- ✅ Perfect fidelity (no accuracy loss)
- ✅ Tables directly usable by Laxity player
- ✅ Simpler implementation

**How It Works**:
1. SF2 header blocks describe Laxity table layouts
2. SID Factory II reads table descriptors
3. Editor shows Laxity tables in native format
4. User edits Laxity tables directly
5. Changes written back to file as Laxity format
6. Laxity player reads changes directly

### Alternative Approach: Format Adapter (If Native Doesn't Work)

**Philosophy**: Create translation layer between SF2 and Laxity formats

**When to Use**:
- If native format causes issues in SF2 editor
- If editor can't display Laxity table structure
- If performance is poor

**Components**:
1. Laxity → SF2 format translator
2. SF2 → Laxity format translator
3. Bidirectional sync system
4. Conflict resolution (if editing occurs in both formats)

**Complexity**: 12-16 hours additional work

---

## Implementation Timeline

| Task | Hours | Days | Status |
|------|-------|------|--------|
| Task 1: Analyze SF2 format | 2-3 | 0.5 | ⏳ Pending |
| Task 2: Design descriptors | 2-3 | 0.5 | ⏳ Pending |
| Task 3: Generate headers | 3-4 | 1 | ⏳ Pending |
| Task 4: Testing & validation | 2-3 | 0.5 | ⏳ Pending |
| Task 5: Documentation | 1-2 | 0.25 | ⏳ Pending |
| **Total** | **10-15** | **2.75** | ⏳ Ready |

**Estimated Total**: 8-12 hours (most likely 10-11 hours)

---

## Success Criteria

### Must Have ✅
- [ ] All 5 Laxity tables properly defined in SF2 headers
- [ ] Tables visible when opened in SID Factory II
- [ ] At least instrument table editable in editor
- [ ] Edited SF2 file still converts to valid output
- [ ] No data corruption from edit operations
- [ ] Documentation complete and accurate

### Should Have ⭐
- [ ] All tables editable in editor
- [ ] Column/row counts match actual data
- [ ] Insert/delete operations work (if supported)
- [ ] Color rules for visual feedback
- [ ] Performance acceptable (sub-second operations)

### Nice to Have 🌟
- [ ] Undo/redo support
- [ ] Validation of edited values
- [ ] Helpful error messages for invalid edits
- [ ] Batch editing support
- [ ] Comparison with original values

---

## Risk Assessment

### Risk 1: SF2 Editor Doesn't Recognize Tables
**Likelihood**: Medium
**Impact**: High (feature doesn't work)
**Mitigation**:
- Thoroughly analyze existing drivers
- Test incrementally with simple headers first
- Have fallback to playback-only if needed

### Risk 2: Header Block Format Incompatibility
**Likelihood**: Medium
**Impact**: High (corrupted files)
**Mitigation**:
- Validate against SF2 editor source code
- Create extensive unit tests
- Test with multiple SID Factory II versions

### Risk 3: Data Layout Misinterpretation
**Likelihood**: Low-Medium
**Impact**: Medium (tables display wrong)
**Mitigation**:
- Double-check row/column major layout
- Test with real editor
- Provide clear documentation

### Risk 4: Performance Issues
**Likelihood**: Low
**Impact**: Low (editor slow, but functional)
**Mitigation**:
- Use efficient binary layout
- Minimize memory overhead
- Profile if issues arise

---

## File Dependencies

### Will Create:
- `sidm2/sf2_header_generator.py` - Header block generator
- `test_laxity_headers.py` - Unit tests
- `LAXITY_DRIVER_TABLE_EDITING_GUIDE.md` - User guide
- `PHASE6_IMPLEMENTATION_REPORT.md` - Technical report

### Will Modify:
- `sidm2/laxity_converter.py` - Add header generation
- `drivers/laxity/sf2driver_laxity_00.prg` - Regenerate with proper headers
- `drivers/laxity/build_laxity_driver.py` - Update build process
- `LAXITY_DRIVER_QUICK_START.md` - Add table editing section
- `LAXITY_DRIVER_FAQ.md` - Add table editing Q&As
- `README.md` - Update status

### Will Reference:
- `docs/SF2_DEEP_DIVE.md` - SF2 format details
- `LAXITY_DRIVER_FINAL_REPORT.md` - Driver architecture
- SF2 editor source code (external reference)

---

## Next Steps

When ready to begin implementation:

1. **Start with Task 1**: Analyze existing drivers
   - Extract headers from Driver 11, NP20
   - Create analysis report
   - Document expected format

2. **Move to Task 2**: Design table descriptors
   - Based on Task 1 findings
   - Create specification matrix
   - Get ready for implementation

3. **Implement Task 3**: Create header generator
   - Write Python code to generate blocks
   - Test with small examples
   - Integrate with converter

4. **Execute Task 4**: Validate in SF2 editor
   - Convert test files
   - Open in SID Factory II
   - Document results

5. **Complete Task 5**: Write documentation
   - User guide for table editing
   - Technical implementation report
   - Update existing docs

---

## Questions to Answer Before Starting

1. What exactly does SID Factory II expect in table descriptors?
2. How does it determine column/row counts?
3. Does it support custom table types or only predefined ones?
4. What properties enable editing vs read-only viewing?
5. Can we define tables without a full format adapter?
6. Should we implement format adapter as fallback or immediately?

---

**Plan Status**: ✅ Complete and Ready for Implementation

**Next Action**: Begin Task 1 - Analyze SF2 header block format from existing drivers
