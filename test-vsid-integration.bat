@echo off
REM Test VSID Integration in Conversion Pipeline
REM Verifies that VSID wrapper works correctly

echo.
echo ========================================
echo VSID Integration Test
echo ========================================
echo.

python pyscript/test_vsid_integration.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] All tests passed
) else (
    echo.
    echo [X] Some tests failed
    exit /b 1
)
