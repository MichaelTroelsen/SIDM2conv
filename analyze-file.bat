@echo off
REM Complete analysis of a single SID file
REM Usage: analyze-file.bat <input.sid>

if "%~1"=="" (
    echo Usage: analyze-file.bat ^<input.sid^>
    echo.
    echo Performs complete analysis including:
    echo   - Player identification
    echo   - SID register dump
    echo   - Disassembly
    echo   - Memory analysis
    echo.
    echo Example: analyze-file.bat SID/Angular.sid
    exit /b 1
)

set INPUT=%~1
set BASENAME=%~n1
set OUTPUT=output\%BASENAME%_analysis

echo ========================================
echo Analyzing: %INPUT%
echo Output: %OUTPUT%
echo ========================================
echo.

mkdir "%OUTPUT%" 2>nul

echo [1/4] Identifying player type...
tools\player-id.exe "%INPUT%" > "%OUTPUT%\player_id.txt"

echo [2/4] Generating register dump...
tools\siddump.exe "%INPUT%" -t30 > "%OUTPUT%\registers.dump"

echo [3/4] Creating disassembly...
tools\SIDwinder.exe disassemble "%INPUT%" > "%OUTPUT%\disassembly.asm"

echo [4/4] Rendering audio...
tools\SID2WAV.EXE -t30 -16 "%INPUT%" "%OUTPUT%\audio.wav"

echo.
echo ========================================
echo Analysis complete!
echo Output directory: %OUTPUT%
echo ========================================
echo.
echo Generated files:
dir /b "%OUTPUT%"

exit /b 0
