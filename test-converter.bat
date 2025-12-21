@echo off
REM Test Converter - Run converter unit tests
REM Usage: test-converter.bat [-v]
REM
REM Test Coverage:
REM   - SID parsing and header extraction
REM   - Laxity player analysis
REM   - Table extraction (filter, pulse, instruments)
REM   - Sequence parsing and command mapping
REM   - SF2 conversion pipeline
REM   - Roundtrip validation
REM
REM Options:
REM   -v  Verbose output
REM
REM Results:
REM   - 86 tests + 153 subtests
REM   - 100%% pass rate
REM
REM Examples:
REM   test-converter.bat
REM   test-converter.bat -v

python scripts/test_converter.py %*
