@echo off
REM Fully disable AppVerifier for SIDFactoryII.exe.
REM Use this to revert appverifier-setup.bat.
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

echo Disabling AppVerifier for %EXE%...
appverif.exe /n %EXE%

echo.
echo Removing IFEO entry to be safe...
reg delete "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\%EXE%" /f 2>nul

echo.
echo Removing WER LocalDumps entry (revert to system default)...
reg delete "HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps\%EXE%" /f 2>nul

echo.
echo Done. SF2II should now run without AppVerifier instrumentation.
echo.
endlocal
pause
