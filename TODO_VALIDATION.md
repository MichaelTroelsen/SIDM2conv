# Validation Integration TODO

**Status:** Plan Approved - Ready to Implement
**Date:** 2025-11-25
**Goal:** Integrate accuracy validation into convert_all.py pipeline

---

## Completed Today ✅

1. ✅ Created `validate_sid_accuracy.py` framework (v0.1.0)
2. ✅ Created comprehensive `docs/VALIDATION_SYSTEM.md` guide
3. ✅ Added WAV conversion to convert_all.py pipeline
4. ✅ Committed all changes to git

---

## Next Tasks (In Order)

### 1. Fix validate_sid_accuracy.py Parser ⚠️ CRITICAL
**Status:** IN PROGRESS
**File:** `validate_sid_accuracy.py`
**Issue:** Currently captures 0 frames due to parser expecting hex format instead of table format

**What to fix:**
```python
def _parse_siddump_output(self, output: str):
    """Parse siddump TABLE format (not hex dumps)"""
    # Look for lines starting with |
    # Example: |     0 | 0000  ... ..  00 0000 000 | ... |
    # Extract frame number from column 1
    # Extract register values from voice columns

    for line in output.split('\n'):
        if line.strip().startswith('|') and not line.strip().startswith('| Frame'):
            # Parse table row
            # Extract frame number, register values
            pass
```

**Also fix:**
- Replace ✅ with [OK]
- Replace ❌ with [X]
- Replace ⚠️ with [!]

**Test:** `python validate_sid_accuracy.py SID/Angular.sid output/Angular/New/Angular_exported.sid --duration 5`

---

### 2. Create sidm2/validation.py Module
**Status:** TODO
**File:** `sidm2/validation.py` (NEW)
**Purpose:** Lightweight validation module for convert_all.py integration

**Functions needed:**
```python
def quick_validate(original_sid, exported_sid, duration=10):
    """
    Quick 10-second validation for pipeline
    Returns: {
        'overall_accuracy': float,
        'frame_accuracy': float,
        'voice_accuracy': float,
        'register_accuracy': float,
        'filter_accuracy': float,
        'frames_compared': int,
        'differences_found': int,
    }
    """

def generate_accuracy_summary(results):
    """
    Format accuracy results for info.txt
    Returns: multi-line string
    """

def get_accuracy_grade(accuracy):
    """
    Return grade: EXCELLENT/GOOD/FAIR/POOR
    >= 99%: EXCELLENT
    >= 95%: GOOD
    >= 80%: FAIR
    <  80%: POOR
    """
```

---

### 3. Update convert_all.py - Add Validation Call
**Status:** TODO
**File:** `convert_all.py`
**Location:** After SF2 packing (around line 875)

**Add:**
```python
# Quick validation (10 seconds for pipeline speed)
if exported_sid.exists() and original_sid_copy.exists():
    try:
        from sidm2.validation import quick_validate

        print(f"       -> Running validation...")
        validation = quick_validate(
            str(original_sid_copy),
            str(exported_sid),
            duration=10  # Quick for pipeline
        )

        acc = validation['overall_accuracy']
        grade = get_accuracy_grade(acc)
        print(f"       -> Accuracy: {acc:.1f}% [{grade}]")

        # Store for reports
        song_results['validation'] = validation

    except Exception as e:
        print(f"       -> Validation failed: {str(e)[:40]}")
        song_results['validation'] = None
```

---

### 4. Update generate_info_file() Function
**Status:** TODO
**File:** `convert_all.py`
**Function:** `generate_info_file()`

**Add validation section:**
```python
def generate_info_file(..., validation=None):
    # ... existing sections ...

    # Add accuracy section
    if validation:
        from sidm2.validation import generate_accuracy_summary

        info_lines.append("")
        info_lines.append("ACCURACY VALIDATION")
        info_lines.append("=" * 50)
        info_lines.append(generate_accuracy_summary(validation))

    # ... rest of function ...
```

---

### 5. Update generate_overview.py - Add Accuracy Columns
**Status:** TODO
**File:** `generate_overview.py`

**Changes:**

A. **Update table header:**
```python
<th>Overall</th>
<th>Frame</th>
<th>Voice</th>
<th>Filter</th>
<th>Grade</th>
```

B. **Add data cells in song row:**
```python
if song_data.get('validation'):
    v = song_data['validation']
    grade = get_accuracy_grade(v['overall_accuracy'])
    grade_class = grade.lower()

    row += f'<td class="acc-{grade_class}">{v["overall_accuracy"]:.1f}%</td>'
    row += f'<td>{v["frame_accuracy"]:.1f}%</td>'
    row += f'<td>{v["voice_accuracy"]:.1f}%</td>'
    row += f'<td>{v["filter_accuracy"]:.1f}%</td>'
    row += f'<td><span class="badge-{grade_class}">{grade}</span></td>'
else:
    row += '<td colspan="5">N/A</td>'
```

C. **Add CSS styling:**
```css
.acc-excellent { background: #d4edda; color: #155724; font-weight: bold; }
.acc-good      { background: #fff3cd; color: #856404; }
.acc-fair      { background: #f8d7da; color: #721c24; }
.acc-poor      { background: #f5c6cb; color: #721c24; font-weight: bold; }

.badge-excellent { background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; }
.badge-good      { background: #ffc107; color: #333; padding: 2px 8px; border-radius: 3px; }
.badge-fair      { background: #fd7e14; color: white; padding: 2px 8px; border-radius: 3px; }
.badge-poor      { background: #dc3545; color: white; padding: 2px 8px; border-radius: 3px; }
```

D. **Add summary statistics section:**
```python
# Calculate aggregates
total_songs = len(song_results)
avg_accuracy = sum(s['validation']['overall_accuracy'] for s in song_results if s.get('validation')) / total_songs

html += '''
<h2>Accuracy Summary</h2>
<div class="stats-grid">
    <div class="stat-card">
        <h3>Average Accuracy</h3>
        <div class="value">{avg:.1f}%</div>
    </div>
    <div class="stat-card">
        <h3>Excellent (>= 99%)</h3>
        <div class="value">{excellent}/{total}</div>
    </div>
    <div class="stat-card">
        <h3>Good (>= 95%)</h3>
        <div class="value">{good}/{total}</div>
    </div>
    <div class="stat-card">
        <h3>Needs Work (< 95%)</h3>
        <div class="value">{needs_work}/{total}</div>
    </div>
</div>
'''.format(avg=avg_accuracy, excellent=count_excellent, good=count_good, needs_work=count_needs_work, total=total_songs)
```

---

### 6. Test Integration
**Status:** TODO

**Test steps:**
```bash
# 1. Test validation tool alone
python validate_sid_accuracy.py SID/Angular.sid output/Angular/New/Angular_exported.sid --duration 5

# 2. Test on single file with validation
rm -rf output/Angular
python convert_all.py --input SID --output output

# 3. Check outputs
cat output/Angular/New/Angular_info.txt  # Should have accuracy section
open output/conversion_summary.html       # Should have accuracy columns

# 4. Run on all files (if single test passed)
python convert_all.py
```

---

## Expected Output Examples

### Info File Example
```
SONG: Angular
PLAYER: Laxity_NewPlayer_V21
...

ACCURACY VALIDATION
==================================================
Overall Accuracy:      98.7%  [GOOD]
Frame-Level:           99.1%  [EXCELLENT]
Voice Accuracy:        98.5%  [GOOD]
  Voice 1 Frequency:   99.2%
  Voice 1 Waveform:    98.8%
  Voice 2 Frequency:   99.0%
  Voice 2 Waveform:    98.5%
  Voice 3 Frequency:   98.8%
  Voice 3 Waveform:    98.2%
Register Accuracy:     97.9%
Filter Accuracy:       97.5%

Validation Duration:   10 seconds
Frames Compared:       500/500
Differences Found:     123

Grade:                 GOOD
Recommendation:        Minor improvements needed for 99% target
```

### HTML Overview Table Row
```
| Song Name | Player | ... | Overall | Frame | Voice | Filter | Grade |
|-----------|--------|-----|---------|-------|-------|--------|-------|
| Angular   | Laxity | ... | 98.7%   | 99.1% | 98.5% | 97.5%  | GOOD  |
```

---

## Files to Modify

1. ✏️ `validate_sid_accuracy.py` - Fix parser, remove emojis
2. ➕ `sidm2/validation.py` - NEW module
3. ✏️ `convert_all.py` - Add validation call
4. ✏️ `convert_all.py` - Update generate_info_file()
5. ✏️ `generate_overview.py` - Add accuracy columns and CSS

---

## Testing Checklist

- [ ] validate_sid_accuracy.py captures frames correctly
- [ ] Quick validation completes in < 15 seconds
- [ ] Info files contain accuracy section
- [ ] HTML overview has accuracy columns
- [ ] CSS styling works (colors for grades)
- [ ] Summary statistics calculate correctly
- [ ] Works on all 16 SID files without errors

---

## Performance Notes

- **Quick validation (10 sec)** for pipeline: Fast, good enough for overview
- **Full validation (30 sec)** for deep analysis: Use standalone tool
- Validation adds ~10-15 seconds per file to pipeline
- Total pipeline time: ~3-5 minutes for all 16 files (previously ~2 minutes)

---

## Next Session

Start with Step 1: Fix the siddump parser in validate_sid_accuracy.py

**Command to test:**
```bash
tools/siddump.exe SID/Angular.sid -z -t5 | head -20
# Understand the exact output format
# Then fix _parse_siddump_output() to match
```
