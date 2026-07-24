@echo off
REM Audio Tightness Tool - Compare onset timing + attack shape between two renders
REM
REM Renders an original .sid and a driver .sf2/.sid/.wav to WAV, detects onsets
REM via spectral flux, aligns them, and reports timing/attack-shape divergence
REM -- catches audio-domain "not tight" problems that register-write-exact
REM trace comparison can miss. See docs/guides/AUDIO_TIGHTNESS_GUIDE.md.
REM
REM Usage:
REM   audio-tightness.bat original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
REM   audio-tightness.bat original.sid converted.sid --voice 1
REM   audio-tightness.bat a.wav b.wav --no-html
REM
REM Options:
REM   --seconds N              Render duration in seconds (default: 30)
REM   --voice {1,2,3}          Isolate one SID voice (mutes the other two on BOTH renders)
REM   --driver-init/--driver-play  Override the driver .sf2's init/play addresses
REM                            (required for bin/-only native drivers -- see docs)
REM   --onset-tolerance-ms N   Max onset delta to still count as matched (default: 150)
REM   --loose-threshold-ms N   Delta above which a matched onset is flagged loose (default: 40)
REM   --output FILE            Output HTML path
REM   --text-output FILE       Also write the text report to this path
REM   --no-html                Skip HTML generation
REM   -v, -vv                  Verbose logging
REM   --help                   Show detailed help

setlocal

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Please install Python 3.8+ or add to PATH
    exit /b 1
)

REM Check arguments
if "%~1"=="" (
    echo Audio Tightness Tool - Compare onset timing + attack shape between two renders
    echo.
    echo Usage: audio-tightness.bat original.sid converted.sf2 [options]
    echo.
    echo Examples:
    echo   audio-tightness.bat original.sid converted.sf2 --driver-init 0x1000 --driver-play 0x1003
    echo   audio-tightness.bat original.sid converted.sid --voice 1
    echo   audio-tightness.bat a.wav b.wav --no-html
    echo.
    echo For detailed help: audio-tightness.bat --help
    exit /b 1
)

REM Run audio tightness tool
python pyscript\audio_tightness_tool.py %*

endlocal
