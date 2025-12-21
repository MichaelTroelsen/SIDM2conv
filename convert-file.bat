@echo off
REM Quick single-file SID to SF2 converter
REM Usage: convert-file.bat <input.sid> [--driver laxity|driver11|np20]

if "%~1"=="" (
    echo Usage: convert-file.bat ^<input.sid^> [--driver laxity^|driver11^|np20]
    echo.
    echo Examples:
    echo   convert-file.bat song.sid
    echo   convert-file.bat "My Song.sid" --driver laxity
    echo.
    echo Automatically detects Laxity files and suggests --driver laxity
    echo Output: output/^<basename^>.sf2
    exit /b 1
)

set INPUT=%~1
set BASENAME=%~n1
set OUTPUT=output\%BASENAME%.sf2
set DRIVER=%~2

REM Check if file exists
if not exist "%INPUT%" (
    echo Error: File not found: %INPUT%
    exit /b 1
)

echo ========================================
echo Converting: %INPUT%
echo Output: %OUTPUT%
echo ========================================
echo.

REM Detect player type
echo [1/3] Detecting player type...
tools\player-id.exe "%INPUT%" > temp_player_id.txt
findstr /C:"Laxity" temp_player_id.txt >nul
if %ERRORLEVEL% EQU 0 (
    echo Player: Laxity NewPlayer detected
    if "%DRIVER%"=="" (
        echo.
        echo TIP: Use --driver laxity for best accuracy (99.93%%)
        echo      Example: convert-file.bat "%INPUT%" --driver laxity
        echo.
    )
) else (
    echo Player: Non-Laxity player detected
)
del temp_player_id.txt 2>nul

echo.
echo [2/3] Converting to SF2...
if "%DRIVER%"=="" (
    python scripts/sid_to_sf2.py "%INPUT%" "%OUTPUT%"
) else (
    python scripts/sid_to_sf2.py "%INPUT%" "%OUTPUT%" %DRIVER% %3
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo Conversion FAILED!
    echo ========================================
    exit /b 1
)

echo.
echo [3/3] Verifying output...
if exist "%OUTPUT%" (
    echo ✓ Created: %OUTPUT%
    for %%A in ("%OUTPUT%") do echo   Size: %%~zA bytes
    echo.
    echo ========================================
    echo Conversion SUCCESSFUL!
    echo ========================================
    echo.
    echo Next steps:
    echo   - View: sf2-viewer.bat "%OUTPUT%"
    echo   - Export: sf2-export.bat "%OUTPUT%"
    echo   - Validate: validate-file.bat "%INPUT%"
) else (
    echo ✗ Output file not created!
    exit /b 1
)

exit /b 0
