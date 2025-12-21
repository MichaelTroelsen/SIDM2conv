@echo off
REM Validate Accuracy - Frame-by-frame accuracy validation
REM Usage: validate-accuracy.bat <original.sid> <converted.sid>
REM
REM Validation:
REM   - Frame-by-frame SID register comparison
REM   - Accuracy percentage calculation
REM   - Detailed mismatch reporting
REM
REM Examples:
REM   validate-accuracy.bat "SID/original.sid" "output/converted.sid"

if "%~1"=="" (
    echo Usage: validate-accuracy.bat ^<original.sid^> ^<converted.sid^>
    echo.
    echo Examples:
    echo   validate-accuracy.bat "SID/original.sid" "output/converted.sid"
    exit /b 1
)

python scripts/validate_sid_accuracy.py %*
