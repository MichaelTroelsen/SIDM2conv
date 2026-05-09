@echo off
REM Enable AppVerifier with HEAPS-only instrumentation by writing the
REM registry directly. Bypasses appverif.exe's CLI which doesn't seem to
REM persist the IFEO key correctly on this Windows build.
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

echo === Step 1: Clear any existing state ===
appverif.exe /n %EXE% 2>nul
reg delete "%IFEO%" /f 2>nul

echo.
echo === Step 2: Write minimal IFEO key for HEAPS-only AppVerifier ===
echo The Heaps GUID (4D056CEB-D8E3-4b85-B148-B543D56D9BDE) is the only
echo provider sub-key — AppVerifier loads vrfcore + vfbasics, GlobalFlag
echo 0x100 = FLG_APPLICATION_VERIFIER, VerifierFlags can be any non-zero.
reg add "%IFEO%" /v GlobalFlag /t REG_SZ /d "0x100" /f
reg add "%IFEO%" /v VerifierDlls /t REG_SZ /d "vrfcore.dll vfbasics.dll" /f
reg add "%IFEO%" /v VerifierFlags /t REG_DWORD /d 0 /f
reg add "%IFEO%\Heaps-{4D056CEB-D8E3-4b85-B148-B543D56D9BDE}" /v Default /t REG_DWORD /d 1 /f

echo.
echo === Step 3: WER LocalDumps for any crash that fires ===
set WERKEY=HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\%EXE%
reg add "%WERKEY%" /v DumpType /t REG_DWORD /d 2 /f
reg add "%WERKEY%" /v DumpCount /t REG_DWORD /d 32 /f
reg add "%WERKEY%" /v DumpFolder /t REG_EXPAND_SZ /d "%%LOCALAPPDATA%%\CrashDumps" /f

echo.
echo === Step 4: Verify ===
reg query "%IFEO%" /s

echo.
echo Done. Test:
echo     py -3 pyscript/sf2_pass_rate.py bin/_action.sf2 5
echo Disable: appverifier-disable.bat
echo.
endlocal
pause
