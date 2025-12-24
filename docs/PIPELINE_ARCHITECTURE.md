# SIDM2 Pipeline Architecture: Existing + Enhanced

**Version**: v2.0.0
**Type**: Architecture & Design Document
**Focus**: How existing (v1.8.0) and enhanced (v2.0.0) pipelines coexist

---

## Critical Design: EXTENSION Not Replacement

The enhanced pipeline is an EXTENSION of the existing conversion pipeline.

```
v1.8.0 (Existing - Still Works)
  15-step pipeline
  9 tools
  Output: SF2 + 11 text files
  Mode: Quick (default)
  Time: <1 second

        |
        | (Extension)
        v

v2.0.0 (Enhanced - Adds Optional Features)
  20-step pipeline
  14 tools (9 existing unchanged + 5 new optional)
  Output: Up to 25+ files (with optional analysis)
  Modes: Quick (original) + Standard/Comprehensive/Custom (new)
  Time: <1s (quick) to 15s (comprehensive)
```

---

## How They Coexist

### Existing Pipeline (v1.8.0) - CORE ENGINE
These 9 tools and 15 steps work EXACTLY as before:
1. SID Parser (Step 5-6)
2. CPU6502 Emulator (Step 7)
3. Python Siddump v2.6.0 (Step 7 alternative)
4. Laxity Converter (Step 9)
5. Driver11 Converter (Step 9)
6. SF2 Packer (Step 10-12)
7. SF2 Format Validator (Step 13-14)
8. SF2 Text Exporter (Step 15)
9. Accuracy Validator (optional)

Default behavior: These tools run every time

### Enhanced Mode (v2.0.0) - OPTIONAL ADDITIONS
These 5 new tools and 9 additional steps are OPTIONAL:
10. SIDwinder Tracer (Step 7.5) [INTEGRATED]
11. Comparison Tool (Step 14.5) [TO ENHANCE]
12. 6502 Disassembler (Step 8.5) [TO IMPLEMENT]
13. Audio Exporter (Step 16) [TO IMPLEMENT]
14. Memory Map Analyzer (Step 12.5) [TO IMPLEMENT]
15. Pattern Recognizer (Step 17) [TO IMPLEMENT]
16. Subroutine Tracer (Step 18) [TO IMPLEMENT]
17. Report Generator (Step 19) [TO IMPLEMENT]
18. Output Organizer (Step 20) [TO IMPLEMENT]

User control: Enable with --flags

---

## Configuration Modes

### Mode 1: QUICK (Default)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
```
- Uses: Existing 15-step pipeline (9 tools)
- Output: SF2 + 11 text files
- Time: <1 second
- Change: NONE from v1.8.0
- For: Users who want fast conversion only

### Mode 2: STANDARD
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity --trace --compare
```
- Uses: 15-step core + selected optional steps
- Output: SF2 + 11 text + trace + comparison
- Time: 2-5 seconds
- Change: Adds selected analysis tools
- For: Users who want some insights

### Mode 3: COMPREHENSIVE
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity --full-analysis
```
- Uses: All 20 steps (core + all optional)
- Output: 25+ files (complete analysis)
- Time: 10-15 seconds
- Change: Adds all analysis tools
- For: Users who want complete understanding

### Mode 4: CUSTOM
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity --disasm --patterns --report
```
- Uses: 15-step core + selected optional steps
- Output: SF2 + 11 text + selected analysis
- Time: Varies
- Change: User-selected analysis tools
- For: Users who know exactly what they need

---

## Backward Compatibility Guarantee

### What Stays the Same
- Command syntax unchanged
- Default behavior unchanged (quick mode)
- Output format unchanged (SF2 + 11 text files)
- Performance unchanged (<1 second)
- All 9 existing tools unchanged
- File locations unchanged

### What's New
- Optional CLI flags for enhanced analysis
- New output directories (analysis/, reports/) only when requested
- New optional tools that don't interfere with existing ones
- New configuration modes (standard/comprehensive/custom)

### The Promise
Existing users can keep using SIDM2 exactly as before. Nothing breaks. No changes required.

---

## File Organization (No Breaking Changes)

### Current Output (v1.8.0)
```
output/Stinsens_Test_Laxity/
├── Stinsens_Test_Laxity.sf2
└── export/
    ├── instruments.txt
    ├── wave.txt
    ├── arp.txt
    ├── commands.txt
    ├── filter.txt
    ├── hr.txt
    ├── init.txt
    ├── orderlist.txt
    ├── pulse.txt
    ├── summary.txt
    └── tempo.txt
```

### With Enhanced Mode (v2.0.0)
```
output/Stinsens_Test_Laxity/
├── Stinsens_Test_Laxity.sf2        (UNCHANGED)
├── export/                          (UNCHANGED)
│   ├── instruments.txt              (UNCHANGED)
│   ├── wave.txt                     (UNCHANGED)
│   └── ... (11 files, all same)     (UNCHANGED)
│
├── analysis/                        (NEW - optional)
│   ├── Stinsens_init.asm            (--disasm)
│   ├── Stinsens_play.asm            (--disasm)
│   ├── Stinsens_trace.txt           (--trace)
│   ├── Stinsens_memory_map.html     (--memory-analysis)
│   ├── Stinsens_patterns.json       (--patterns)
│   ├── Stinsens_callgraph.txt       (--subroutines)
│   ├── Stinsens_performance.json    (--subroutines)
│   └── Stinsens_comparison.json     (--compare)
│
└── reports/                         (NEW - optional)
    └── Stinsens_comprehensive_report.html (--report)
```

**Key**: Original files stay exactly the same. New files in separate folders.

---

## Technical Design

### Zero Impact on Existing Code
- Existing functions unchanged
- New code in new modules
- Optional imports (graceful if missing)
- Clean interfaces between tools

### Easy to Maintain
- Each tool in separate file
- Each phase independent
- Tests isolated per tool
- Can disable any optional tool

### Easy to Extend
- Add new tool = add new module + tests
- New step = wire into orchestrator
- No modification of core pipeline
- Clear dependencies

---

## Version Roadmap

### v1.8.0 (Current - Stable)
- 15-step pipeline
- 9 core tools
- Laxity driver (99.93% accuracy)
- Fast, proven, reliable

### v2.0.0-beta.1 (Available Now)
- v1.8.0 unchanged (quick mode)
- SIDwinder Tracer integrated (Phase 1 done)
- Foundation for enhanced mode

### v2.0.0-beta.2 (Phase 2 - In Progress)
- All Phase 1b-2 tools ready
- Disassembler + Audio export

### v2.0.0-rc.1 (Phase 3)
- Memory + Pattern + Subroutine tools

### v2.0.0-rc.2 (Phase 4)
- Report Generator + Output Organizer

### v2.0.0 (Final - Stable)
- All 14 tools complete
- 20-step pipeline fully functional
- Full backward compatibility verified
- Complete documentation

---

## Summary

The v2.0.0 enhancement is designed as a pure extension:
- Nothing changes for existing users (v1.8.0 still works)
- New capabilities available to users who want them
- All features are opt-in via CLI flags
- Core pipeline remains fast and simple
- Enhanced pipeline available for deep analysis

Users control the experience: Quick conversion or comprehensive analysis.

