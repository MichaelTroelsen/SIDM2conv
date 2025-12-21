@echo off
REM Run quick subset of tests for fast feedback
REM Usage: quick-test.bat

echo ========================================
echo Running Quick Test Suite (Fast Feedback)
echo ========================================
echo.

echo Running core converter tests only...
python scripts/test_converter.py TestSIDParser TestSF2Writer

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Quick tests PASSED!
    echo Run 'test-all.bat' for complete suite
    echo ========================================
    exit /b 0
) else (
    echo.
    echo ========================================
    echo Quick tests FAILED!
    echo ========================================
    exit /b 1
)
