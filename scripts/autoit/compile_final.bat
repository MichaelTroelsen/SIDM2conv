@echo off
setlocal

set "AUTOIT_DIR=C:\Program Files (x86)\AutoIt3"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_FILE=%SCRIPT_DIR%sf2_loader.au3"
set "OUTPUT_FILE=%SCRIPT_DIR%sf2_loader.exe"

echo ========================================
echo AutoIt Compiler
echo ========================================
echo.
echo Script: %SCRIPT_FILE%
echo Output: %OUTPUT_FILE%
echo.

if not exist "%AUTOIT_DIR%\Aut2Exe\Aut2exe.exe" (
    echo ERROR: AutoIt not found at %AUTOIT_DIR%
    pause
    exit /b 1
)

if not exist "%SCRIPT_FILE%" (
    echo ERROR: Script file not found: %SCRIPT_FILE%
    pause
    exit /b 1
)

echo Compiling...
echo.

"%AUTOIT_DIR%\Aut2Exe\Aut2exe.exe" /in "%SCRIPT_FILE%" /out "%OUTPUT_FILE%" /x64 /comp 4

echo.
echo Checking result...
echo.

if exist "%OUTPUT_FILE%" (
    echo SUCCESS: Executable created!
    echo.
    dir "%OUTPUT_FILE%"
    echo.
    echo File size:
    for %%A in ("%OUTPUT_FILE%") do echo %%~zA bytes
) else (
    echo FAILED: Executable not created
    echo.
    echo Trying 32-bit compilation...
    "%AUTOIT_DIR%\Aut2Exe\Aut2exe.exe" /in "%SCRIPT_FILE%" /out "%OUTPUT_FILE%" /comp 4

    if exist "%OUTPUT_FILE%" (
        echo SUCCESS: 32-bit executable created!
        dir "%OUTPUT_FILE%"
    ) else (
        echo FAILED: Could not create executable
        echo.
        echo Please check:
        echo 1. AutoIt is properly installed
        echo 2. Script has no errors (use AU3Check.exe)
        echo 3. You have write permissions in this directory
    )
)

echo.
echo ========================================
pause
