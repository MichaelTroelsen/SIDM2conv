@echo off
REM Quick single-file validation workflow
REM Usage: validate-file.bat <input.sid> [--driver laxity|driver11|np20]

if "%~1"=="" (
    echo Usage: validate-file.bat ^<input.sid^> [--driver laxity^|driver11^|np20]
    echo.
    echo Performs complete validation:
    echo   1. Convert SID to SF2
    echo   2. Export SF2 back to SID
    echo   3. Compare accuracy
    echo   4. Generate report
    echo.
    echo Example: validate-file.bat song.sid --driver laxity
    exit /b 1
)

set INPUT=%~1
set BASENAME=%~n1
set DRIVER=%~2
set OUTPUT_DIR=output\%BASENAME%_validation

echo ========================================
echo Validating: %INPUT%
echo Output: %OUTPUT_DIR%
echo ========================================
echo.

REM Check if file exists
if not exist "%INPUT%" (
    echo Error: File not found: %INPUT%
    exit /b 1
)

REM Create output directory
mkdir "%OUTPUT_DIR%" 2>nul

echo [1/5] Converting SID to SF2...
if "%DRIVER%"=="" (
    python scripts/sid_to_sf2.py "%INPUT%" "%OUTPUT_DIR%\%BASENAME%.sf2"
) else (
    python scripts/sid_to_sf2.py "%INPUT%" "%OUTPUT_DIR%\%BASENAME%.sf2" %DRIVER% %3
)

if %ERRORLEVEL% NEQ 0 (
    echo Conversion failed!
    exit /b 1
)

echo.
echo [2/5] Exporting SF2 back to SID...
python scripts/sf2_to_sid.py "%OUTPUT_DIR%\%BASENAME%.sf2" "%OUTPUT_DIR%\%BASENAME%_exported.sid"

if %ERRORLEVEL% NEQ 0 (
    echo Export failed!
    exit /b 1
)

echo.
echo [3/5] Generating register dumps...
tools\siddump.exe "%INPUT%" -t30 > "%OUTPUT_DIR%\original.dump"
tools\siddump.exe "%OUTPUT_DIR%\%BASENAME%_exported.sid" -t30 > "%OUTPUT_DIR%\exported.dump"

echo.
echo [4/5] Validating accuracy...
python scripts/validate_sid_accuracy.py "%INPUT%" "%OUTPUT_DIR%\%BASENAME%_exported.sid" > "%OUTPUT_DIR%\accuracy_report.txt"

echo.
echo [5/5] Generating summary...
echo ======================================== > "%OUTPUT_DIR%\validation_summary.txt"
echo VALIDATION SUMMARY >> "%OUTPUT_DIR%\validation_summary.txt"
echo ======================================== >> "%OUTPUT_DIR%\validation_summary.txt"
echo. >> "%OUTPUT_DIR%\validation_summary.txt"
echo Original: %INPUT% >> "%OUTPUT_DIR%\validation_summary.txt"
echo Converted: %OUTPUT_DIR%\%BASENAME%.sf2 >> "%OUTPUT_DIR%\validation_summary.txt"
echo Exported: %OUTPUT_DIR%\%BASENAME%_exported.sid >> "%OUTPUT_DIR%\validation_summary.txt"
echo. >> "%OUTPUT_DIR%\validation_summary.txt"
type "%OUTPUT_DIR%\accuracy_report.txt" >> "%OUTPUT_DIR%\validation_summary.txt"

echo.
echo ========================================
echo Validation COMPLETE!
echo ========================================
echo.
echo Results saved to: %OUTPUT_DIR%
echo.
echo Generated files:
dir /b "%OUTPUT_DIR%"
echo.
echo View summary: type "%OUTPUT_DIR%\validation_summary.txt"

exit /b 0
