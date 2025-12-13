@echo off
REM ============================================================================
REM Build Laxity SF2 Driver
REM ============================================================================
REM Assembles the wrapper and combines with relocated player to create
REM a complete SF2 driver PRG file.
REM
REM Usage: build_driver.bat [output_name]
REM
REM Author: SIDM2 Project
REM Date: 2025-12-13
REM ============================================================================

setlocal

REM Set paths
set ASSEMBLER=C:\debugger\64tass\64tass.exe
set SCRIPT_DIR=%~dp0
set OUTPUT_NAME=%1

REM Default output name
if "%OUTPUT_NAME%"=="" set OUTPUT_NAME=sf2driver_laxity_00

echo ========================================================================
echo Building Laxity SF2 Driver
echo ========================================================================
echo.

REM Check if assembler exists
if not exist "%ASSEMBLER%" (
    echo ERROR: 64tass assembler not found at: %ASSEMBLER%
    echo Please install 64tass or update the path in this script.
    exit /b 1
)

REM Check if required files exist
if not exist "%SCRIPT_DIR%laxity_driver.asm" (
    echo ERROR: laxity_driver.asm not found!
    exit /b 1
)

if not exist "%SCRIPT_DIR%laxity_player_relocated.bin" (
    echo ERROR: laxity_player_relocated.bin not found!
    echo Please run the relocation script first:
    echo   python scripts/relocate_laxity_player.py
    exit /b 1
)

if not exist "%SCRIPT_DIR%laxity_driver_header.bin" (
    echo ERROR: laxity_driver_header.bin not found!
    echo Please run the header generator first:
    echo   python scripts/generate_sf2_header.py
    exit /b 1
)

REM Assemble the driver
echo Assembling driver...
"%ASSEMBLER%" ^
    --output "%SCRIPT_DIR%%OUTPUT_NAME%.prg" ^
    --cbm-prg ^
    --labels="%SCRIPT_DIR%%OUTPUT_NAME%.labels" ^
    --list="%SCRIPT_DIR%%OUTPUT_NAME%.list" ^
    --verbose-list ^
    "%SCRIPT_DIR%laxity_driver.asm"

if errorlevel 1 (
    echo.
    echo ERROR: Assembly failed!
    exit /b 1
)

echo.
echo ========================================================================
echo Build Complete
echo ========================================================================
echo Output: %OUTPUT_NAME%.prg
echo.

REM Show file size
for %%F in ("%SCRIPT_DIR%%OUTPUT_NAME%.prg") do (
    echo File size: %%~zF bytes ^(%%~zF bytes / 1024 = KB^)
)

echo.
echo Generated files:
if exist "%SCRIPT_DIR%%OUTPUT_NAME%.prg" echo   - %OUTPUT_NAME%.prg ^(driver binary^)
if exist "%SCRIPT_DIR%%OUTPUT_NAME%.labels" echo   - %OUTPUT_NAME%.labels ^(symbol table^)
if exist "%SCRIPT_DIR%%OUTPUT_NAME%.list" echo   - %OUTPUT_NAME%.list ^(assembly listing^)

echo.
echo ========================================================================
echo Next Steps
echo ========================================================================
echo 1. Verify driver structure:
echo    python scripts/verify_driver.py drivers/laxity/%OUTPUT_NAME%.prg
echo.
echo 2. Test in SF2 editor ^(if available^)
echo.
echo 3. Integrate into conversion pipeline ^(Phase 5^)
echo ========================================================================

endlocal
