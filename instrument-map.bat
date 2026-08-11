@echo off
REM Instrument Map - which SF2 instrument is sounding on each siddump frame
REM
REM Reads note onsets out of a register trace of the ORIGINAL, keys them by ADSR
REM ($D405/$D406 -- in many players a verbatim per-instrument copy of the
REM instrument record), locates the converted SF2's instrument table BY SEARCH
REM against those values, and reports what each side actually sounds per
REM instrument. See docs/plans/INSTRUMENT_MAP_PLAN.md.
REM
REM The first section is always the verdict on whether ADSR identifies an
REM instrument in this file AT ALL. When it does not, no table is emitted --
REM that is the result, not a failure to produce one.
REM
REM Usage:
REM   instrument-map.bat original.sid converted.sf2
REM   instrument-map.bat original.sid converted.sf2 -t 30 --annotate dump.txt
REM   instrument-map.bat original.sid                       (key verdict + profile only)
REM
REM Options:
REM   -t N              Trace seconds (default: 20)
REM   --init/--play A   Converted driver addresses (default 0x1000 / 0x1003)
REM   --declared ADDR   Skip the search and use this instrument-table address
REM   --shape S         row-major (default) or column-major, with --declared
REM   --step N          Record stride (row-major) or column delta (column-major)
REM   --count N         Records to read (default 32) -- a READ LENGTH, not a
REM                     detected instrument count
REM   --annotate FILE   Write siddump with Ins1/Ins2/Ins3 columns appended
REM   --json            Emit the raw result object
REM   -o FILE           Write the Markdown here instead of stdout
REM   --settle-max N    Frames to look ahead for a settled sample (default: 4)
REM   --min-onsets N    Below this the verdict is insufficient-data (default: 30)

setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

if "%~1"=="" (
    echo Instrument Map - which SF2 instrument is sounding on each siddump frame
    echo.
    echo Usage: instrument-map.bat original.sid [converted.sf2] [options]
    echo.
    echo Examples:
    echo   instrument-map.bat SID\Angular.sid SF2\Angular.sf2
    echo   instrument-map.bat SID\Angular.sid SF2\Angular.sf2 --annotate dump.txt
    echo.
    echo For detailed help: instrument-map.bat --help
    exit /b 1
)

python pyscript\instrument_map_report.py %*

endlocal
