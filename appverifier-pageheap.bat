@echo off
REM Enable old-style FULL PAGE HEAP for SIDFactoryII.exe.
REM
REM PageHeap places each heap allocation on its own page with a guard
REM page after it. ANY write past the end of an allocation triggers an
REM access violation at the WRITING instruction. This is the most
REM precise heap-bug detection mode Windows offers, and it's
REM independent of AppVerifier's "Heaps" provider.
REM
REM Memory cost: each allocation rounded up to 4KB, plus a 4KB guard
REM page. Could double or triple SF2II's memory footprint, and slows
REM down allocations measurably.
REM
REM ** RUN AS ADMINISTRATOR **

setlocal

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: Run as Administrator.
    pause
    exit /b 1
)

set EXE=SIDFactoryII.exe
set IFEO=HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\%EXE%

echo === Step 1: Clear any AppVerifier state ===
appverif.exe /n %EXE% 2>nul
reg delete "%IFEO%" /f 2>nul

echo.
echo === Step 2: Enable FULL PageHeap via NT global flags ===
echo GlobalFlag = 0x02000000 (FLG_HEAP_PAGE_ALLOCS)
echo PageHeapFlags = 0x3 (full + default end-of-page alignment)

REM GlobalFlag is REG_SZ in NT global flag format; the value "0x02000000"
REM enables FLG_HEAP_PAGE_ALLOCS.
reg add "%IFEO%" /v GlobalFlag /t REG_SZ /d "0x02000000" /f
reg add "%IFEO%" /v PageHeapFlags /t REG_DWORD /d 0x3 /f

echo.
echo === Step 3: WER LocalDumps so the crash gets captured ===
set WERKEY=HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\%EXE%
reg add "%WERKEY%" /v DumpType /t REG_DWORD /d 2 /f
reg add "%WERKEY%" /v DumpCount /t REG_DWORD /d 32 /f
reg add "%WERKEY%" /v DumpFolder /t REG_EXPAND_SZ /d "%%LOCALAPPDATA%%\CrashDumps" /f

echo.
echo === Step 4: Verify ===
reg query "%IFEO%"

echo.
echo Done. Test with:
echo     py -3 pyscript/sf2_pass_rate.py bin/_action.sf2 5
echo Disable with:
echo     appverifier-disable.bat
echo.
endlocal
pause
