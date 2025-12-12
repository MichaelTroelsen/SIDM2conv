@echo off
REM Build modified siddump with memory tracing
REM This script automates the patching and compilation process

echo ========================================
echo Building siddump_trace.exe
echo ========================================
echo.

REM Check if backup exists
if not exist siddump.c.orig (
    echo Creating backups...
    copy siddump.c siddump.c.orig
    copy cpu.c cpu.c.orig
    copy cpu.h cpu.h.orig
    echo Backups created.
    echo.
)

echo Applying modifications...
echo.

REM Create modified cpu.c
echo Modifying cpu.c...
python ../apply_siddump_trace_patch.py

if errorlevel 1 (
    echo ERROR: Patch application failed!
    echo Try manual patching - see BUILD_SIDDUMP_TRACE.md
    pause
    exit /b 1
)

echo.
echo Compiling...
gcc -o siddump_trace.exe siddump.c cpu.c -lm -O2

if errorlevel 1 (
    echo ERROR: Compilation failed!
    echo Make sure MinGW/GCC is installed and in PATH
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS!
echo ========================================
echo.
echo siddump_trace.exe created successfully!
echo.
echo Usage:
echo   siddump_trace.exe -trace SID/file.sid -t1
echo.
echo Output will be written to: siddump_trace.txt
echo.
echo To restore original files:
echo   copy siddump.c.orig siddump.c
echo   copy cpu.c.orig cpu.c
echo   copy cpu.h.orig cpu.h
echo.
pause
