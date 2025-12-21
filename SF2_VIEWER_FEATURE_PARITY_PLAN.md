# SF2 Viewer Feature Parity Plan

**Goal**: Bring SF2 Viewer GUI to 100% feature parity with SF2 C++ Editor and SF2 Python Exporter

**Date**: 2025-12-21
**Status**: Planning Phase

---

## Current Feature Comparison

### SF2 C++ Editor (2025-12-21 Custom Build)
- ✅ OrderList - XXYY unpacked format (visual display)
- ✅ Track Export - 3 files with musical notation (F8 key)
- ✅ Musical Notation - C-4, F#-2, +++, --- (in track files)
- ✅ Transpose Display - +0, +2, -4 (in track files)
- ✅ Zoom Functionality - Ctrl+/Ctrl-/Ctrl+0
- ✅ Build Timestamp - In window title

### SF2 Python Exporter (v2.3.0)
- ✅ OrderList - XXYY unpacked format (orderlist.txt)
- ✅ Track Export - 3 files with musical notation (track_*.txt)
- ✅ Musical Notation - C-4, F#-2, +++, ---
- ✅ Transpose Display - +0, +2, -4
- ✅ Transpose Application - Notes transposed in track files

### SF2 Python Viewer (v2.3.0 - Current)
- ✅ OrderList - XXYY unpacked format (OrderList tab) **NEW v2.3**
- ✅ Musical Notation - C-4, F#-2, +++, --- (Sequences tab) **ALREADY EXISTS!**
- ✅ View Modes - Musician/Hex/Both (Sequences tab) **ALREADY EXISTS!**
- ❌ Track View - No dedicated track view tab
- ❌ Transpose Display - OrderList shows raw hex (A0, A2) not decoded (+0, +2)
- ❌ Transpose Application - Sequences don't show transposed notes

---

## Feature Gap Analysis

### What's Missing in SF2 Viewer

**Critical Missing Feature**:
1. **Track View Tab** - Combines OrderList + Sequences with transpose applied
   - Shows full track progression (like track export files)
   - Applies transpose to note values
   - Displays in playback order (OrderList position 0, 1, 2...)
   - Separate view for each track (1, 2, 3)

**Nice-to-Have Enhancements**:
2. **Transpose Decoding in OrderList** - Show "+0, +2, -4" instead of just "A0, A2, AC"
3. **Track Selector** - Switch between Track 1, 2, 3 views
4. **Position Highlighting** - Highlight current position in track view

---

## Implementation Plan

### Phase 1: Musical Notation in Sequences ✅ ALREADY DONE

**Status**: ✅ **COMPLETE** - Already implemented in existing viewer!

**Evidence**:
- Lines 171-187 (sf2_viewer_core.py): `note_name()` method returns C-4, F#-2, +++, ---
- Lines 189-203 (sf2_viewer_core.py): `instrument_display()` method
- Lines 763-797 (sf2_viewer_gui.py): View mode selector (Musician/Hex/Both)
- Lines 984-1034 (sf2_viewer_gui.py): Sequence display with musical notation

**No work needed!** ✅

---

### Phase 2: Add Transpose Decoding to OrderList Tab

**Goal**: Show decoded transpose values in OrderList display

**Current Display**:
```
Step  | Track 1  | Track 2  | Track 3  | Notes
------|----------|----------|----------|------------------
0000  | A00E     | A000     | A00A     |
0005  | A011     | A006     | A20A     | T3 transpose→A2
```

**Enhanced Display**:
```
Step  | Track 1      | Track 2      | Track 3      | Notes
------|--------------|--------------|--------------|------------------
0000  | A00E (+0)    | A000 (+0)    | A00A (+0)    |
0005  | A011 (+1)    | A006 (+0)    | A20A (+2)    | T3 transpose +2
```

**Implementation**:
1. Add `_decode_transpose()` helper method
2. Modify OrderList display loop to include decoded values
3. Update Notes column to show "+0, +2, -4" format

**Files Modified**:
- `sf2_viewer_gui.py` - OrderList display (lines 799-933)

**Estimated Effort**: 30 minutes
**Lines Changed**: ~20 lines

---

### Phase 3: Create Track View Tab (MAJOR FEATURE)

**Goal**: Add new tab showing track view with OrderList + Sequences + Transpose

**Tab Layout**:
```
+----------------------------------------------------------+
| Track View                                               |
+----------------------------------------------------------+
| Select Track: [Track 1 ▼] [Track 2] [Track 3]          |
+----------------------------------------------------------+
| Position 000 | OrderList: A00E | Sequence $0E | +0      |
|   0000 | --   | 08   | D-4                              |
|   0001 | --   | --   | +++                              |
|   0002 | --   | --   | E-4                              |
|   [End of sequence]                                      |
|                                                          |
| Position 001 | OrderList: A00F | Sequence $0F | +0      |
|   0000 | --   | --   | F-4                              |
|   ...                                                    |
+----------------------------------------------------------+
```

**Features**:
- Track selector (Track 1/2/3 buttons or combo box)
- Display format matching track export files
- Combines OrderList positions with sequence data
- Applies transpose to notes
- Shows musical notation
- Auto-scrolls to current position (if playback added later)

**Implementation Steps**:

1. **Create Tab UI** (15 min)
   - Add `create_track_view_tab()` method
   - Add track selector (QComboBox or buttons)
   - Add QTextEdit for track display
   - Add to tabs in `init_ui()`

2. **Add Track Display Logic** (45 min)
   - Add `update_track_view()` method
   - Combine OrderList + Sequences data
   - Apply transpose to notes
   - Format output like track export files

3. **Add Transpose Helper** (15 min)
   - Copy `_format_note()` from exporter
   - Copy `_apply_transpose()` from exporter
   - Or import from shared module

4. **Add Track Selection** (15 min)
   - Handle track selector changes
   - Refresh display on track change

**Files Modified**:
- `sf2_viewer_gui.py` - Add track view tab
- `sf2_viewer_core.py` - No changes needed (uses existing unpacked data)

**Estimated Effort**: 90 minutes (1.5 hours)
**Lines Added**: ~150-200 lines

---

### Phase 4: Test All Viewer Enhancements

**Test Files**:
1. Laxity - Stinsen - Last Night Of 89.sf2 (complex OrderList)
2. Driver 11 Test - Filter.sf2 (simple OrderList)

**Test Cases**:

**OrderList Tab**:
- ✅ Verify XXYY format display
- ✅ Verify transpose decoding (A0 → +0, A2 → +2, AC → -4)
- ✅ Verify transpose change notes

**Sequences Tab**:
- ✅ Verify musical notation (C-4, F#-2, +++, ---)
- ✅ Verify view modes (Musician/Hex/Both)
- ✅ Verify single-track and interleaved display

**Track View Tab** (NEW):
- ✅ Verify track selector works (Track 1/2/3)
- ✅ Verify OrderList + Sequence combination
- ✅ Verify transpose applied correctly
- ✅ Verify musical notation matches export files
- ✅ Verify position headers correct

**Comparison Testing**:
- ✅ Compare Track View with track export files (should match exactly)
- ✅ Compare OrderList with orderlist.txt export (should match)
- ✅ Compare Sequences with sequence export files (should match)

**Estimated Effort**: 30 minutes

---

### Phase 5: Update Documentation

**Files to Update**:

1. **CLAUDE.md**:
   - Update SF2 Viewer features section
   - Add Track View tab description
   - Add transpose decoding feature
   - Update version to v2.4.0

2. **README.md** (if exists):
   - Update feature list
   - Add screenshots (optional)

3. **New: SF2_VIEWER_COMPLETE.md**:
   - Complete feature comparison table
   - Implementation summary
   - Usage guide for Track View

**Estimated Effort**: 30 minutes

---

## Total Implementation Estimate

| Phase | Description | Effort | Lines | Status |
|-------|-------------|--------|-------|--------|
| **Phase 1** | Musical notation (Sequences) | 0 min | 0 | ✅ DONE |
| **Phase 2** | Transpose decoding (OrderList) | 30 min | ~20 | ⏹ Pending |
| **Phase 3** | Track View tab (NEW) | 90 min | ~200 | ⏹ Pending |
| **Phase 4** | Testing | 30 min | - | ⏹ Pending |
| **Phase 5** | Documentation | 30 min | - | ⏹ Pending |
| **Total** | | **180 min** | **~220** | **3h** |

---

## Feature Parity Status

### After Phase 3 Completion

| Feature | C++ Editor | Python Exporter | Python Viewer |
|---------|-----------|-----------------|---------------|
| OrderList Unpacking | ✅ | ✅ | ✅ |
| XXYY Format Display | ✅ | ✅ | ✅ |
| Track View | ✅ (F8 files) | ✅ (track_*.txt) | ✅ (Tab) |
| Musical Notation | ✅ | ✅ | ✅ |
| Transpose Display | ✅ | ✅ | ✅ |
| Transpose Application | ✅ | ✅ | ✅ |
| View Modes | ❌ | ❌ | ✅ (Musician/Hex) |

**Result**: **100% Feature Parity + Extra Features!** ✅

---

## Key Design Decisions

### Track View Tab Design

**Option 1: Single Track Display (RECOMMENDED)**
- Show one track at a time (Track 1, 2, or 3)
- Track selector at top
- Vertical scrolling through positions
- Matches track export file format exactly
- **Pros**: Simple, clean, matches export format
- **Cons**: Can't see all tracks at once

**Option 2: 3-Track Parallel Display**
- Show all 3 tracks side-by-side
- Horizontal columns for each track
- **Pros**: See all tracks simultaneously
- **Cons**: Wide display, harder to read

**Decision**: Use Option 1 (single track) for simplicity and exact export parity.

### Transpose Application Method

**Option A: Reuse Exporter Code**
- Copy `_format_note()` and `_apply_transpose()` from sf2_to_text_exporter.py
- **Pros**: Guaranteed consistency
- **Cons**: Code duplication

**Option B: Create Shared Module**
- Move helper functions to sf2_viewer_core.py
- **Pros**: No duplication, single source of truth
- **Cons**: More refactoring

**Decision**: Use Option A (copy methods) for speed, consider Option B later.

---

## Success Criteria

After implementation, the SF2 Viewer will have:

1. ✅ **OrderList Tab** - XXYY format with transpose decoding
2. ✅ **Sequences Tab** - Musical notation (already exists)
3. ✅ **Track View Tab** - Full track progression with transpose (NEW)
4. ✅ **100% Feature Parity** - Matches C++ editor and Python exporter
5. ✅ **Better than Editor** - Has view modes (Musician/Hex/Both)

**Result**: SF2 Viewer becomes the **most comprehensive SF2 analysis tool** available!

---

## Next Steps

1. **Get User Approval** - Confirm plan looks good
2. **Start Phase 2** - Add transpose decoding to OrderList
3. **Implement Phase 3** - Create Track View tab
4. **Test Everything** - Validate against export files
5. **Update Docs** - Document new features

---

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**

**Date**: 2025-12-21
**Estimated Completion**: Same day (3 hours implementation)
