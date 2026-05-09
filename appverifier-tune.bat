@echo off
REM Tune AppVerifier — disable Memory + Locks, keep Heaps only.
REM
REM Background: full Heaps+Memory+Locks crashes SIDFactoryII.exe at startup
REM (~50ms after launch, exit code 0xC0000421 = STATUS_ASSERTION_FAILURE).
REM Some Memory or Locks check is intrusive enough that SDL or NVIDIA's
REM Direct3D path trips it. Heaps alone is much lighter and is the only
REM check we actually need for the OOB-write hunt.
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

echo Removing Memory + Locks checks (keeping Heaps)...
appverif.exe /verify %EXE% /disable Memory /for %EXE%
appverif.exe /verify %EXE% /disable Locks /for %EXE%

echo.
echo Current AppVerifier state for %EXE%:
appverif.exe /query %EXE%

echo.
echo Done. Re-run the harness:
echo     py -3 pyscript/sf2_pass_rate.py bin/_action.sf2 5
echo.
endlocal
pause
