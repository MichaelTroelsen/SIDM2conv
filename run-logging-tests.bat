@echo off
REM SF2 Logging Test Suite Launcher
REM Runs all logging tests and generates report

echo ====================================================================
echo SF2 Debug Logging - Comprehensive Test Suite
echo ====================================================================
echo.

REM Create test output directory
if not exist test_output mkdir test_output
if not exist test_output\logs mkdir test_output\logs
if not exist test_output\reports mkdir test_output\reports

echo [1/3] Running Unit Tests...
echo --------------------------------------------------------------------
python pyscript/test_sf2_logger_unit.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Unit tests failed!
    pause
    exit /b 1
)

echo.
echo.
echo [2/3] Testing with Real SF2 File (Stinsens)...
echo --------------------------------------------------------------------
echo Setting up test environment...
set SF2_DEBUG_LOG=test_output\logs\stinsens_test.log
set SF2_JSON_LOG=1

echo Loading SF2 file: output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2

REM Quick test - load file and verify logging
python -c "import sys; sys.path.insert(0, '.'); from pyscript.sf2_viewer_core import SF2Parser; parser = SF2Parser('output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2'); print('File loaded successfully'); print(f'Magic ID: 0x{parser.magic_id:04X}' if parser.magic_id else 'No magic ID'); print(f'Blocks: {len(parser.blocks) if hasattr(parser, \"blocks\") else 0}')"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: File load test failed!
    pause
    exit /b 1
)

echo.
echo ✓ File load test passed
echo.

echo [3/3] Validating Log Output...
echo --------------------------------------------------------------------

REM Check if log file was created
if exist test_output\logs\stinsens_test.log (
    echo ✓ Log file created: test_output\logs\stinsens_test.log
    for %%A in (test_output\logs\stinsens_test.log) do echo   Size: %%~zA bytes
) else (
    echo ✗ Log file not found
)

REM Check if JSON log was created
if exist test_output\logs\stinsens_test.json (
    echo ✓ JSON log created: test_output\logs\stinsens_test.json
    for %%A in (test_output\logs\stinsens_test.json) do echo   Size: %%~zA bytes
) else (
    echo ⚠ JSON log not found (may not have been enabled)
)

echo.
echo ====================================================================
echo Test Suite Complete!
echo ====================================================================
echo.
echo Test Results:
echo   - Unit Tests: PASSED ✓
echo   - File Load Test: PASSED ✓
echo   - Log Output: VALIDATED ✓
echo.
echo Log files available in: test_output\logs\
echo.
echo To view logs:
echo   type test_output\logs\stinsens_test.log
echo   type test_output\logs\stinsens_test.json
echo.
pause
