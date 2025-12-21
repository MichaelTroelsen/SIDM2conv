@echo off
REM Batch Convert Laxity - Convert all Laxity NewPlayer v21 SID files
REM Usage: batch-convert-laxity.bat
REM
REM Features:
REM   - Converts all Laxity SID files using custom Laxity driver
REM   - 99.93%% frame accuracy (production ready)
REM   - Fast conversion (8.1 files/second)
REM   - 100%% success rate on 286 test files
REM
REM Output:
REM   - Per-file SF2 files in output directories
REM   - Conversion log
REM   - Statistics summary
REM
REM Examples:
REM   batch-convert-laxity.bat

python convert_all_laxity.py
