@echo off
REM SF2 to SID Converter - Convert SF2 files back to SID format
REM Usage: sf2-to-sid.bat <input.sf2> <output.sid>
REM
REM Features:
REM   - Converts SF2 back to playable SID file
REM   - Preserves driver and music data
REM   - Roundtrip validation support
REM
REM Examples:
REM   sf2-to-sid.bat "input.sf2" "output.sid"
REM   sf2-to-sid.bat "output/Song/New/Song.sf2" "output/Song/New/Song_exported.sid"

if "%~1"=="" (
    echo Usage: sf2-to-sid.bat ^<input.sf2^> ^<output.sid^>
    echo.
    echo Examples:
    echo   sf2-to-sid.bat "input.sf2" "output.sid"
    exit /b 1
)

python scripts/sf2_to_sid.py %*
