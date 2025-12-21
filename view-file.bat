@echo off
REM Quick SF2 file viewer launcher
REM Usage: view-file.bat <file.sf2>

if "%~1"=="" (
    echo Usage: view-file.bat ^<file.sf2^>
    echo.
    echo Opens SF2 file in the SF2 Viewer GUI
    echo.
    echo Examples:
    echo   view-file.bat output/song.sf2
    echo   view-file.bat "output/My Song.sf2"
    echo.
    echo Alternative: sf2-viewer.bat ^<file.sf2^>
    exit /b 1
)

set INPUT=%~1

REM Check if file exists
if not exist "%INPUT%" (
    echo Error: File not found: %INPUT%
    echo.
    echo Looking for SF2 files in output directory:
    if exist "output\" (
        dir /b output\*.sf2 2>nul
        if %ERRORLEVEL% NEQ 0 (
            echo   No SF2 files found in output\
        )
    ) else (
        echo   output\ directory not found
    )
    exit /b 1
)

REM Check file extension
echo %INPUT% | findstr /i "\.sf2$" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Warning: File does not have .sf2 extension
    echo Attempting to open anyway...
    echo.
)

echo ========================================
echo Opening: %INPUT%
echo ========================================
echo.

REM Launch viewer
python pyscript/sf2_viewer_gui.py "%INPUT%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo Failed to open viewer!
    echo ========================================
    echo.
    echo Possible issues:
    echo   - PyQt6 not installed (run: pip install PyQt6)
    echo   - Python not in PATH
    echo   - File corrupted or invalid SF2 format
    echo.
    echo Try: python pyscript/launch_sf2_viewer.py
    exit /b 1
)

exit /b 0
