# Phase 5: Integration into Conversion Pipeline

**Status**: In Progress  
**Objective**: Add `--driver laxity` support to conversion pipeline

## Implementation Plan

### Step 1: Laxity Converter Module (DONE)
- File: `sidm2/laxity_converter.py`
- Provides `LaxityConverter` class
- Methods:
  - `load_driver()`: Load SF2 driver template
  - `inject_tables()`: Inject Laxity music data
  - `convert()`: Full conversion process

### Step 2: Integration with sid_to_sf2.py (NEXT)
Add to main conversion script:
```python
--driver laxity    # Use custom Laxity driver
--driver driver11  # Default (standard driver)
--driver np20      # JCH NewPlayer v20
```

### Step 3: Pipeline Integration
- Detect if input is Laxity SID
- Choose driver automatically or via option
- Extract music data using existing laxity_parser.py
- Inject into Laxity driver
- Write SF2 output

### Step 4: Batch Conversion
- Update convert_all.py with --driver option
- Test on all 286 Laxity files
- Compare accuracy: 1-8% vs 70-90%

## Expected Results

**Current (Driver 11)**:
- Accuracy: 1-8%
- Conversion: Lossy format translation

**New (Laxity Driver)**:
- Accuracy: 70-90%
- Conversion: Native format preservation
- Improvement: 10-90x better

## Architecture

### Conversion Flow
```
SID File
  ↓
[Detect Player Type]
  ↓
IF Laxity:
  ├→ Extract music data (laxity_parser.py)
  ├→ Load Laxity driver (sf2driver_laxity_00.prg)
  ├→ Inject tables at native addresses
  └→ Output SF2 file
ELSE:
  ├→ Use standard driver (Driver 11 / NP20)
  ├→ Convert tables to target format
  └→ Output SF2 file
```

## Files to Modify

1. **scripts/sid_to_sf2.py** (Add --driver option)
2. **scripts/convert_all.py** (Add driver selection)
3. **complete_pipeline_with_validation.py** (Support Laxity driver)

## Testing Strategy

1. Single file test: `sid_to_sf2.py --driver laxity input.sid output.sf2`
2. Batch test: `convert_all.py --driver laxity` (286 files)
3. Accuracy comparison: Measure improvement
4. Validate on 18-file test suite

## Timeline

- Implementation: 4-6 hours
- Testing: 8-12 hours
- Validation: 4-8 hours
- Total Phase 5: 16-26 hours

## Next Steps

1. Modify sid_to_sf2.py to accept --driver option
2. Create Laxity-specific conversion path
3. Test on single file
4. Run batch conversion
5. Measure accuracy improvement
6. Complete Phase 6 (optional)

---

**Status**: Ready to implement  
**Dependency**: Phases 1-4 complete ✅
