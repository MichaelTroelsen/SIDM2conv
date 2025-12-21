@echo off
REM SID to SF2 Converter - Convert Commodore 64 SID files to SF2 format
REM Usage: sid-to-sf2.bat <input.sid> <output.sf2> [--driver laxity|driver11|np20]
REM
REM Drivers:
REM   --driver laxity    - Laxity NewPlayer v21 driver (99.93%% accuracy) [RECOMMENDED for Laxity SIDs]
REM   --driver driver11  - SF2 Driver 11 (standard)
REM   --driver np20      - NewPlayer 20 driver
REM
REM Examples:
REM   sid-to-sf2.bat "input.sid" "output.sf2"
REM   sid-to-sf2.bat "input.sid" "output.sf2" --driver laxity
REM   sid-to-sf2.bat "SID/Laxity.sid" "output/Song/New/Song.sf2" --driver laxity

if "%~1"=="" (
    echo Usage: sid-to-sf2.bat ^<input.sid^> ^<output.sf2^> [--driver laxity^|driver11^|np20]
    echo.
    echo Examples:
    echo   sid-to-sf2.bat "input.sid" "output.sf2"
    echo   sid-to-sf2.bat "input.sid" "output.sf2" --driver laxity
    exit /b 1
)

python scripts/sid_to_sf2.py %*
