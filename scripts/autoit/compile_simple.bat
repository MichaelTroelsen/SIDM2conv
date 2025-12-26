@echo off
echo Compiling sf2_loader.au3...
"C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe" /in "%~dp0sf2_loader.au3" /out "%~dp0sf2_loader.exe" /x64
timeout /t 3 /nobreak >nul
if exist "%~dp0sf2_loader.exe" (
    echo SUCCESS: sf2_loader.exe created
    dir "%~dp0sf2_loader.exe"
) else (
    echo FAILED: sf2_loader.exe not created
)
