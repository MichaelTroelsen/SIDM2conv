@echo off
REM Run all test suites
REM Usage: test-all.bat

echo ========================================
echo Running All Test Suites
echo ========================================
echo.

set FAILED=0

echo [1/3] Running converter tests...
python scripts/test_converter.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [2/3] Running SF2 format tests...
python scripts/test_sf2_format.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [3/3] Running Laxity driver tests...
python scripts/test_laxity_driver.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo ========================================
if %FAILED% EQU 0 (
    echo All tests PASSED!
    echo ========================================
    exit /b 0
) else (
    echo Some tests FAILED!
    echo ========================================
    exit /b 1
)
