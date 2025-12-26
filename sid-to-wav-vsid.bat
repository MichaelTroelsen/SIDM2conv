@echo off
REM Convert SID to WAV using VSID (VICE SID player)
REM Usage: sid-to-wav-vsid.bat input.sid output.wav [time_seconds]

if "%~1"=="" (
    echo Usage: %~n0 input.sid output.wav [time_seconds]
    echo.
    echo Examples:
    echo   %~n0 music.sid music.wav
    echo   %~n0 music.sid music.wav 120
    exit /b 1
)

if "%~2"=="" (
    echo ERROR: Output WAV file required
    echo Usage: %~n0 input.sid output.wav [time_seconds]
    exit /b 1
)

set INPUT_SID=%~1
set OUTPUT_WAV=%~2
set TIME_SECONDS=%~3

if "%TIME_SECONDS%"=="" (
    python pyscript/sid_to_wav_vsid.py "%INPUT_SID%" "%OUTPUT_WAV%"
) else (
    python pyscript/sid_to_wav_vsid.py "%INPUT_SID%" "%OUTPUT_WAV%" --time %TIME_SECONDS%
)

exit /b %errorlevel%
