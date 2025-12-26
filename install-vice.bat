@echo off
REM Install VICE Emulator (includes vsid for SID to WAV conversion)
echo Installing VICE Emulator...
python pyscript/install_vice.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: VICE installation failed
    pause
    exit /b 1
)
echo.
echo VICE installation complete!
pause
