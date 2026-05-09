@echo off
REM ============================================================================
REM appverifier-setup.bat — enable AppVerifier + WER LocalDumps for SIDFactoryII
REM
REM ** RUN AS ADMINISTRATOR **
REM   Right-click this .bat file -> "Run as administrator"
REM
REM What it does:
REM   1. Registers SIDFactoryII.exe with Application Verifier (AppVerifier).
REM      Enables Heaps + Memory + Locks checks. With these on, every heap
REM      access is bounds-checked at the CPU level. The next time SF2II hits
REM      the OOB write that we've been chasing, AppVerifier will halt the
REM      process at the exact instruction that wrote out of bounds — not
REM      5-6 functions later when the corrupted pointer is finally dereferenced.
REM
REM   2. Enables WER LocalDumps with FullDump type for SIDFactoryII.exe.
REM      Without this, WER deduplicates after ~10 identical crash events;
REM      enabling LocalDumps with DumpType=2 (Full) captures every crash
REM      with full memory + stack into %LOCALAPPDATA%\CrashDumps\.
REM
REM Disabling later (run as admin):
REM   appverif.exe /n SIDFactoryII.exe
REM   reg delete "HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\SIDFactoryII.exe" /f
REM
REM Notes:
REM   - AppVerifier slows SF2II noticeably (heap pages individually allocated
REM     and write-protected). Expect 2-5x slower load times.
REM   - Disable AppVerifier before running normal sessions.
REM   - The LocalDumps changes affect ONLY SIDFactoryII.exe; other apps
REM     continue to use the system default (no full dumps).
REM ============================================================================

setlocal

REM Verify running as admin
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script must be run as Administrator.
    echo Right-click the .bat file and choose "Run as administrator".
    pause
    exit /b 1
)

set EXE=SIDFactoryII.exe

echo.
echo === Step 1: Configure AppVerifier ===
echo Registering %EXE% with these checks:
echo   - Heaps (heap corruption detection)
echo   - Memory (memory access violations)
echo   - Locks (critical section misuse)
echo.
appverif.exe /verify %EXE% /faults
if %errorLevel% NEQ 0 (
    echo WARNING: appverif /verify returned %errorLevel%
    echo If /faults isn't supported on your Windows build, fall back to:
    echo     appverif.exe /verify %EXE%
    appverif.exe /verify %EXE%
)

echo.
echo Enabling specific tests:
appverif.exe /verify %EXE% /enable Heaps /for %EXE%
appverif.exe /verify %EXE% /enable Memory /for %EXE%
appverif.exe /verify %EXE% /enable Locks /for %EXE%

echo.
echo === Step 2: Configure WER LocalDumps for full dumps ===
set WERKEY=HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\%EXE%
echo Setting %WERKEY% ...
reg add "%WERKEY%" /v DumpType /t REG_DWORD /d 2 /f
reg add "%WERKEY%" /v DumpCount /t REG_DWORD /d 32 /f
reg add "%WERKEY%" /v DumpFolder /t REG_EXPAND_SZ /d "%%LOCALAPPDATA%%\CrashDumps" /f

echo.
echo === Done ===
echo.
echo Next steps:
echo   1. Run the harness as usual:
echo        py -3 pyscript/sf2_pass_rate.py bin/_action.sf2 5
echo      The harness's CRASH trials should now produce AppVerifier-detected
echo      heap corruption events caught at the WRITING instruction.
echo.
echo   2. Inspect new dumps in %%LOCALAPPDATA%%\CrashDumps\ — they will be
echo      LARGER than before (full memory) and will contain stack traces.
echo.
echo   3. Decode the latest dump:
echo        py -3 pyscript/sf2_crash_analyze.py
echo.
echo   4. When done, REMEMBER TO DISABLE AppVerifier:
echo        appverif.exe /n %EXE%
echo      (or it will keep slowing down every SF2II session).
echo.
endlocal
pause
