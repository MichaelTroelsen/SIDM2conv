@echo off
REM Run all test suites
REM Usage: test-all.bat

echo ========================================
echo Running All Test Suites
echo ========================================
echo.

set FAILED=0

echo [1/7] Running converter tests...
python scripts/test_converter.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [2/7] Running SF2 format tests...
python scripts/test_sf2_format.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [3/7] Running Laxity driver tests...
python scripts/test_laxity_driver.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [4/7] Running driver selection tests...
python pyscript/test_driver_selector.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [5/7] Running 6502 disassembler tests...
python pyscript/test_disasm6502.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [6/7] Running SIDdecompiler tests...
python pyscript/test_siddecompiler_complete.py
if %ERRORLEVEL% NEQ 0 set FAILED=1

echo.
echo [7/7] Running SIDwinder trace tests...
python pyscript/test_sidwinder_trace.py
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
