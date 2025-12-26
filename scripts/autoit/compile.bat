@echo off
REM ============================================================================
REM AutoIt Script Compiler - SF2 Loader
REM ============================================================================
REM Purpose: Compile sf2_loader.au3 to sf2_loader.exe
REM Requirements: AutoIt3 installed (https://www.autoitscript.com)
REM ============================================================================

echo.
echo ========================================================================
echo Compiling SF2 Loader AutoIt Script
echo ========================================================================
echo.

REM Check if AutoIt is installed (common locations)
set AUT2EXE=
if exist "C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe" (
    set AUT2EXE=C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe
)
if exist "C:\Program Files\AutoIt3\Aut2Exe\Aut2exe.exe" (
    set AUT2EXE=C:\Program Files\AutoIt3\Aut2Exe\Aut2exe.exe
)

if "%AUT2EXE%"=="" (
    echo ERROR: AutoIt Aut2Exe compiler not found!
    echo.
    echo Please install AutoIt3 from: https://www.autoitscript.com/site/autoit/downloads/
    echo.
    echo Installation instructions:
    echo   1. Download AutoIt Full Installation
    echo   2. Run installer and complete setup
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

echo Found AutoIt compiler: %AUT2EXE%
echo.

REM Check if source file exists
if not exist "sf2_loader.au3" (
    echo ERROR: sf2_loader.au3 not found in current directory!
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

echo Source file: sf2_loader.au3
echo Output file: sf2_loader.exe
echo.

REM Compile (x64 version for better compatibility)
echo Compiling to 64-bit executable...
"%AUT2EXE%" /in "sf2_loader.au3" /out "sf2_loader.exe" /comp 4 /x64

if %ERRORLEVEL% == 0 (
    echo.
    echo ========================================================================
    echo SUCCESS: Compilation complete!
    echo ========================================================================
    echo.
    dir sf2_loader.exe | findstr /i "sf2_loader.exe"
    echo.
    echo The compiled executable is ready to use.
    echo.
    echo Test it with:
    echo   sf2_loader.exe "path\to\SIDFactoryII.exe" "path\to\file.sf2" "status.txt"
    echo.
) else (
    echo.
    echo ========================================================================
    echo ERROR: Compilation failed!
    echo ========================================================================
    echo.
    echo Error code: %ERRORLEVEL%
    echo.
    echo Possible issues:
    echo   - Syntax error in sf2_loader.au3
    echo   - Missing AutoIt includes
    echo   - Permission issues
    echo.
    echo Check the AutoIt script for errors and try again.
    echo.
    exit /b 1
)

pause
