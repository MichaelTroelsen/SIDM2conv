@echo off
REM Batch Convert - Convert all SID files in SID/ directory
REM Usage: batch-convert.bat [--roundtrip]
REM
REM Features:
REM   - Converts all SID files in SID/ directory
REM   - Generates both NP20 and Driver 11 versions
REM   - Optional roundtrip validation (SID→SF2→SID)
REM   - Progress reporting
REM
REM Options:
REM   --roundtrip  Enable roundtrip validation
REM
REM Examples:
REM   batch-convert.bat
REM   batch-convert.bat --roundtrip

python scripts/convert_all.py %*
