@echo off
REM Complete Pipeline - Full conversion pipeline with validation
REM Usage: pipeline.bat [--quick] [--export-only]
REM
REM Pipeline Steps (13 steps):
REM   1. SID → SF2 conversion
REM   2. Sequence extraction
REM   3. Player analysis (SIDdecompiler)
REM   4. SF2 packing
REM   5. Dumps (siddump)
REM   6. Accuracy validation
REM   7. WAV rendering
REM   8. Hex dumps
REM   9. Trace analysis
REM   10. Info extraction
REM   11. Disassembly
REM   12. Validation
REM   13. MIDI comparison
REM
REM Options:
REM   --quick        Quick test on subset of files
REM   --export-only  Only export existing conversions
REM
REM Examples:
REM   pipeline.bat
REM   pipeline.bat --quick

python complete_pipeline_with_validation.py %*
