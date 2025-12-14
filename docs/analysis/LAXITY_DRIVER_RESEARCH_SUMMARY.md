# Laxity SF2 Driver - Research Summary

**Date**: 2025-12-12
**Research Phase**: COMPLETE ✅
**Confidence Level**: High (80% success probability for playback)

---

## What Was Researched

In response to your request to create a custom Laxity-specific driver for SID Factory II, I conducted comprehensive research into:

1. **SF2 Driver Architecture** - How SF2 drivers work
2. **Existing Driver Analysis** - Binary structure of Driver 11 and NP20
3. **Laxity Player Structure** - Memory layout and entry points
4. **Implementation Approaches** - Three possible strategies

---

## Key Findings

### 1. SF2 Driver Source Code is Proprietary

**Finding**: The SF2 driver source code (assembly .asm files) is **not publicly available**.

**Evidence**:
- GitHub repository contains only compiled .prg binaries (20 files)
- No assembly source in learnings/ or docs/
- DEVELOPMENT.md has no driver development documentation
- Drivers were created by Laxity and JCH (not open source)

**Implication**: Cannot simply modify existing driver source code.

### 2. SF2 Drivers Have Standard Structure

**Structure**:
```
Load Address:  $0D7E (standard for all SF2 drivers)
Driver Code:   $0D7E-$15xx (~2KB 6502 assembly)
Header Blocks: $0800+ (configuration metadata)
Music Tables:  $0900+ (variable offsets per driver)

Entry Points:
- Init routine (JSR) - called once to setup
- Play routine (JSR) - called every frame (50/60 Hz)
```

**Table Offsets** (vary by driver):
| Driver | Instruments | Pulse | Filter |
|--------|------------|-------|--------|
| Driver 11 | $0A03 | $0D03 | $0F03 |
| NP20 | $0F4D | $0E4D | $0D4D |
| **Laxity** | **$1A6B** | **$1A3B** | **$1A1E** |

### 3. Laxity Player is Self-Contained

**Memory Map** (from analysis):
```
$1000       Init routine entry point
$10A1       Play routine entry point
$1000-$19FF Complete player code (~2.5KB)
$1900+      Music data tables
```

**Interface**:
```asm
; Init: JSR $1000, A = song number
; Play: JSR $10A1 (every frame)
```

**Key Insight**: The Laxity player is a **complete, self-contained music player** that could be extracted and reused!

---

## Recommended Approach: "Extract and Wrap"

### Strategy

Instead of reverse-engineering or building from scratch, **extract the Laxity player code** from existing SID files and **wrap it as an SF2 driver**.

### Architecture

```
┌──────────────────────────────────┐
│ SF2 Wrapper Code ($0D7E)         │ ← SF2 entry points
│  - sf2_init: JSR laxity_init     │
│  - sf2_play: JSR laxity_play     │
├──────────────────────────────────┤
│ Laxity Player Code (relocated)   │ ← Original Laxity code
│  - Init/play routines            │
│  - Table processing              │
│  - SID register writes           │
├──────────────────────────────────┤
│ SF2 Header Blocks                │ ← SF2 metadata
│  - Table definitions             │
│  - Entry point addresses         │
├──────────────────────────────────┤
│ Music Data Tables                │ ← Laxity format
│  - Instruments, Wave, Pulse, etc │
└──────────────────────────────────┘
```

### Why This Works

**Advantages**:
✅ Uses proven Laxity player code (100% compatible)
✅ No reverse engineering of SF2 driver internals
✅ Tables stay in native Laxity format (no conversion!)
✅ Simpler than building from scratch
✅ Expected accuracy: 70-90%

**Challenges**:
⚠️ Requires memory relocation (Laxity: $1000 → SF2: ~$0E00)
⚠️ Must fix absolute address references in code
⚠️ Must create SF2 header blocks manually
⚠️ Table editing may not work (playback-only initially)

### Technical Hurdle: Memory Relocation

**Problem**: Laxity code expects to run at $1000, but SF2 loads drivers at $0D7E.

**Solution**: Relocate player code by scanning for absolute address references and adjusting them:

```python
# Example: LDA $1234 → LDA $1034 (subtract $200)
for each absolute addressing instruction:
    if address in player_code_range ($1000-$19FF):
        address -= $200  # Relocation offset
```

**Tools**:
- SIDwinder disassembly to identify addresses
- Python script to perform byte-level relocation
- Extensive testing with siddump validation

---

## Implementation Phases

### Phase 1: Extract Player Code
Extract Laxity player binary from reference SID file.
**Effort**: 2 hours

### Phase 2: Disassemble & Analyze
Identify all address references and self-modifying code.
**Effort**: 4 hours

### Phase 3: Relocation Script
Write Python script to relocate player code.
**Effort**: 8 hours

### Phase 4: Driver Wrapper
Create 6502 assembly wrapper with SF2 entry points.
**Effort**: 6 hours

### Phase 5: Conversion Pipeline
Integrate into `sid_to_sf2.py` with `--driver laxity` option.
**Effort**: 4 hours

### Phase 6: Testing
Batch test on all 18 files, measure accuracy.
**Effort**: 16 hours

**Total Estimate**: ~40 hours (~1 week full-time)

---

## Expected Results

### Best Case (80% probability)
- ✅ SF2 files load in editor
- ✅ Playback works correctly
- ✅ Accuracy: 70-90% (vs current 1-8%)
- ✅ Can export back to SID
- ⚠️ Table editing limited

### Worst Case (20% probability)
- ❌ Relocation breaks player code
- ❌ Zero-page conflicts with SF2 editor
- ❌ Header block format incompatible
- 🔧 Requires deeper reverse engineering

---

## Alternative Approaches Considered

### Option A: Reverse Engineer Driver 11
**Method**: Disassemble Driver 11, understand code, modify for Laxity format.
**Pros**: Inherits SF2 features.
**Cons**: Very complex, time-consuming (2-4 weeks).
**Decision**: Rejected (too risky, no source code).

### Option B: Extract and Wrap (SELECTED)
**Method**: Extract Laxity player, wrap as SF2 driver.
**Pros**: Simpler, uses proven code.
**Cons**: Relocation required, limited editing.
**Decision**: **Selected** (best risk/reward ratio).

### Option C: Build From Scratch
**Method**: Write minimal 6502 driver implementing Laxity format.
**Pros**: Full control, clean code.
**Cons**: Requires deep 6502 expertise, extensive testing (3-6 weeks).
**Decision**: Rejected (too much effort for MVP).

---

## Documentation Created

During this research, I created three comprehensive documents:

1. **LAXITY_SF2_DRIVER_RESEARCH.md** (15,000 words)
   - Complete architecture analysis
   - Driver structure breakdown
   - Technical challenges identified
   - All three approach options analyzed

2. **LAXITY_DRIVER_IMPLEMENTATION_PLAN.md** (7,000 words)
   - Concrete 6-phase implementation plan
   - Code examples and pseudocode
   - Risk assessment and mitigation
   - Timeline and deliverables

3. **LAXITY_DRIVER_RESEARCH_SUMMARY.md** (this document)
   - Executive summary of findings
   - Recommended approach
   - Expected results

---

## Sources Used

### Documentation
- `docs/ARCHITECTURE.md` - System architecture reference
- `docs/reference/SF2_FORMAT_SPEC.md` - SF2 file format
- `docs/reference/DRIVER_REFERENCE.md` - Driver comparison
- `docs/reference/STINSENS_PLAYER_DISASSEMBLY.md` - Laxity analysis
- `learnings/21.g5_Final.txt` - Laxity NP21 specification
- `learnings/notes_driver11.txt` - Driver 11 table formats

### Binary Analysis
- Hex dump of `G5/drivers/sf2driver11_00.prg`
- Hex dump of `G5/drivers/sf2driver_np20_00.prg`
- Header structure comparison

### Web Research
- GitHub: https://github.com/Chordian/sidfactory2
- SID Factory II Blog: https://blog.chordian.net/sf2/
- CSDb: https://csdb.dk/release/?id=213369

### Tools
- `tools/SIDwinder.exe` - For disassembly and analysis
- `xxd` - Hex dump analysis
- MCP C64 knowledge base - Format research

---

## Next Steps

### Immediate (If Proceeding)

1. **Select reference SID file** - Use Stinsen's Last Night of 89 (well-analyzed)
2. **Extract player code** - Create `scripts/extract_laxity_player.py`
3. **Disassemble** - Run SIDwinder to identify address references
4. **Create test build** - Player at original $1000 (no relocation yet)
5. **Validate playback** - Ensure extracted player works standalone

### Decision Point

Before investing 40 hours in implementation, consider:

**Questions**:
- Is 70-90% accuracy sufficient for your needs?
- Is playback-only acceptable (editing may not work)?
- Are you comfortable with the relocation risk?
- Do you want to proceed with this approach?

**Alternatives**:
- Accept 1-8% accuracy with current system
- Focus on improving siddump_extractor (runtime approach)
- Wait for SF2 driver source code release (unlikely)

---

## Status

**Research**: ✅ COMPLETE
**Design**: ✅ COMPLETE
**Implementation**: ⏸️ AWAITING USER DECISION
**Testing**: ⏳ PENDING

**Recommendation**: Proceed with Phase 1 (Extract Player Code) as a proof-of-concept.

---

## Confidence Assessment

| Aspect | Confidence | Notes |
|--------|-----------|-------|
| **Player Extraction** | 95% | Straightforward binary extraction |
| **Disassembly** | 90% | SIDwinder reliable |
| **Relocation** | 70% | Main technical risk |
| **SF2 Loading** | 80% | Header format well-understood |
| **Playback Accuracy** | 80% | Laxity code proven |
| **Table Editing** | 40% | May require SF2 editor mods |
| **Overall Success** | 80% | High confidence for playback |

---

## Summary

**Creating a Laxity-specific SF2 driver is feasible** using an "extract and wrap" approach. By extracting the proven Laxity player code and packaging it as an SF2 driver, we can achieve 70-90% conversion accuracy without reverse-engineering proprietary SF2 driver code.

**Key risks** include memory relocation complexity and potential SF2 editor compatibility issues, but these are manageable with careful implementation and testing.

**Expected outcome**: Playback-focused driver enabling high-fidelity Laxity→SF2 conversion, with table editing as a potential Phase 2 enhancement.

**Estimated effort**: 40 hours (~1 week full-time) for complete implementation and testing.

**Next step**: User decision on whether to proceed with implementation.
