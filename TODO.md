# SIDM2 Project - TODO List

**Last Updated**: 2025-12-18

## Recently Completed ✅

- ✅ SF2 Text Exporter tool (export all SF2 data to human-readable text files)
- ✅ Single-track sequence support in SF2 Viewer
- ✅ Format detection (single vs 3-track interleaved)
- ✅ Track 3 comparison tool with flexible reference parsing
- ✅ GUI display for both sequence formats
- ✅ Hex notation in sequence display (e.g., "Sequence 10 ($0A)")
- ✅ Unpacker bug fix (instrument/command carryover)
- ✅ Parser fix (comprehensive file scanning, 22 sequences detected)
- ✅ 96.9% match rate achieved for Track 3 reference

## High Priority 🔴

### SF2 Viewer Improvements

1. **Loop Marker Support**
   - Parse loop markers in sequences (0x7E in wave tables)
   - Display looped sequences with full length
   - Show loop points in GUI
   - **Why**: Reference shows 41 steps, sequence 8 has 32 (may be looped)

2. **Format Indicator in GUI**
   - Add visual indicator showing sequence format type
   - Show "Single-track" or "3-track interleaved" label
   - Color-code or icon-based indicator
   - **Why**: Better user understanding of data structure

3. **Test Other Laxity Files**
   - Verify format detection on all 286 Laxity files
   - Check for edge cases or detection failures
   - Document any special cases
   - **Why**: Ensure robust detection across all files

### Sequence/Track System

4. **Sequence Numbering Investigation**
   - Understand SID Factory II sequence numbering vs parser indexing
   - Document the mapping between the two systems
   - Add SID Factory II sequence number to GUI if different
   - **Why**: User confusion about sequence indices

5. **All Tracks Comparison**
   - Extend comparison tool to handle Track 1, Track 2, Track 3
   - Add side-by-side 3-track comparison
   - Generate detailed reports for all tracks
   - **Why**: Complete validation of all sequence data

## Medium Priority 🟡

### Testing & Validation

6. **Automated Test Suite**
   - Add unit tests for format detection
   - Test single-track extraction
   - Test interleaved extraction
   - Regression tests for unpacker bug
   - **Why**: Prevent regressions in future changes

7. **Format Detection Improvements**
   - Add more heuristics for edge cases
   - Handle sequences with mixed patterns
   - Add confidence score to detection
   - **Why**: Improve robustness

8. **Manual Format Override**
   - Add GUI option to override auto-detected format
   - Allow user to force 'single' or 'interleaved'
   - Save override preferences per file
   - **Why**: Handle detection failures gracefully

### Documentation

9. **User Guide for SF2 Viewer**
   - Document all tabs and features
   - Add screenshots for each function
   - Explain sequence formats
   - Create troubleshooting section
   - **Why**: Help users understand the tool

10. **SF2 Format Documentation**
    - Document single-track vs interleaved format
    - Add examples from real files
    - Explain detection algorithm
    - **Why**: Knowledge preservation

## Low Priority 🟢

### SF2 Viewer Features

11. **Sequence Export**
    - Export sequences to CSV
    - Export to MIDI
    - Export to text format
    - **Why**: Enable external analysis

12. **Sequence Editing**
    - Allow basic sequence editing in GUI
    - Save modifications back to SF2
    - Undo/redo support
    - **Why**: Make SF2 Viewer a full editor

13. **Waveform Visualization**
    - Show waveform data graphically
    - Display pulse tables as graphs
    - Visualize filter curves
    - **Why**: Better understanding of audio data

### Code Quality

14. **Code Refactoring**
    - Extract common code to utilities
    - Improve error handling
    - Add type hints throughout
    - **Why**: Maintainability

15. **Performance Optimization**
    - Optimize large file loading
    - Cache parsed data
    - Lazy loading for sequences
    - **Why**: Better UX for large files

## Research & Investigation 🔍

16. **Sequence Pointer Table**
    - Investigate pointer table at 0x16D2
    - Understand why it contains zeros
    - Check if other files have valid tables
    - **Why**: May improve sequence detection

17. **Loop Commands**
    - Document all loop/jump commands in SF2 format
    - Understand 0x7F (end) vs 0x7E (loop) usage
    - Test loop handling in player
    - **Why**: Complete sequence playback

18. **Other Player Formats**
    - Research other SID player formats
    - Check if single-track format is common
    - Document format variations
    - **Why**: Broader compatibility

## Backlog 📋

19. **Multi-file Batch Processing**
    - Batch validate all sequences in a directory
    - Generate summary reports
    - Compare multiple SF2 files
    - **Why**: Large-scale validation

20. **GUI Improvements**
    - Dark mode support
    - Customizable fonts and colors
    - Keyboard shortcuts
    - Recent files menu
    - **Why**: Better user experience

21. **Cross-platform Testing**
    - Test on Linux
    - Test on macOS
    - Fix platform-specific issues
    - **Why**: Broader platform support

## Completed Archive 📦

### 2025-12-18 (Evening)
- ✅ SF2 Text Exporter tool created
  - Exports all SF2 data to text files
  - Auto-detects sequence formats
  - 12 exported files per SF2
  - Human-readable reference format
  - Validation and debugging aid

### 2025-12-18 (Morning)
- ✅ Single-track sequence support
- ✅ Format detection implementation
- ✅ Track 3 comparison tool
- ✅ Hex notation in sequence display
- ✅ Unpacker bug fix
- ✅ Parser comprehensive scanning

### 2025-12-17
- ✅ SF2 Viewer v2.1 release
- ✅ Recent files menu
- ✅ Visualization tab
- ✅ Playback support

### 2025-12-14
- ✅ Laxity driver implementation (99.93% accuracy)
- ✅ Production validation (286 files)

## Notes

- Focus on high-priority items first
- Keep documentation up-to-date with each change
- Test thoroughly before marking items complete
- Archive completed items with date stamps

## How to Use This File

1. **Pick a task**: Choose from High Priority section
2. **Create branch**: `git checkout -b feature/task-name`
3. **Implement**: Make changes, test thoroughly
4. **Document**: Update relevant docs
5. **Mark complete**: Move to Completed Archive with date
6. **Update inventory**: Run `python update_inventory.py`
