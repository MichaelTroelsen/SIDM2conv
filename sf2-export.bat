@echo off
REM SF2 Text Exporter - Export SF2 data to human-readable text files
REM Usage: sf2-export.bat <input.sf2> [output_dir]
REM
REM Exports:
REM   - orderlist.txt (sequence playback order, 3 tracks)
REM   - track_1.txt, track_2.txt, track_3.txt (full track progression)
REM   - sequence_XX.txt (individual sequences with musical notation)
REM   - instruments.txt, wave.txt, pulse.txt, filter.txt (table data)
REM   - commands.txt, summary.txt (reference and statistics)
REM
REM Examples:
REM   sf2-export.bat "file.sf2"
REM   sf2-export.bat "file.sf2" "output/export_dir"

if "%~1"=="" (
    echo Usage: sf2-export.bat ^<input.sf2^> [output_dir]
    echo.
    echo Examples:
    echo   sf2-export.bat "file.sf2"
    echo   sf2-export.bat "file.sf2" "output/export_dir"
    exit /b 1
)

python pyscript/sf2_to_text_exporter.py %*
