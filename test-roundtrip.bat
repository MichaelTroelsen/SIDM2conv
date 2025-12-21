@echo off
REM Test Roundtrip - Test SID→SF2→SID roundtrip conversion
REM Usage: test-roundtrip.bat <input.sid>
REM
REM Test Process:
REM   1. Convert SID → SF2
REM   2. Convert SF2 → SID
REM   3. Compare original vs exported
REM   4. Validate accuracy
REM
REM Examples:
REM   test-roundtrip.bat "SID/test.sid"

if "%~1"=="" (
    echo Usage: test-roundtrip.bat ^<input.sid^>
    echo.
    echo Examples:
    echo   test-roundtrip.bat "SID/test.sid"
    exit /b 1
)

python scripts/test_roundtrip.py %*
