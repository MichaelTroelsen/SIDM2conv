@echo off
REM SIDwinder HTML Trace Viewer - Generate interactive frame-by-frame SID register trace
REM Usage: trace-viewer.bat <input.sid> [-o OUTPUT.html] [-f FRAMES]
REM
REM Features:
REM   - Interactive timeline with slider navigation
REM   - Timeline bars showing write activity (click to jump)
REM   - Frame-by-frame register write visualization
REM   - Real-time SID register state display (4 color-coded groups)
REM   - 29 SID registers with complete tooltips
REM   - Professional VS Code dark theme with smooth animations
REM   - Self-contained HTML (works offline)
REM
REM Options:
REM   -o, --output FILE.html  - Specify output HTML file path
REM   -f, --frames COUNT      - Number of frames to trace (default: 300)
REM
REM Examples:
REM   trace-viewer.bat "input.sid"
REM   trace-viewer.bat "input.sid" -o trace.html
REM   trace-viewer.bat "input.sid" -f 500
REM   trace-viewer.bat "SID/Beast.sid" -o beast_trace.html -f 300

if "%~1"=="" (
    echo Usage: trace-viewer.bat ^<input.sid^> [-o OUTPUT.html] [-f FRAMES]
    echo.
    echo Examples:
    echo   trace-viewer.bat "input.sid"
    echo   trace-viewer.bat "input.sid" -o trace.html -f 500
    exit /b 1
)

python pyscript/sidwinder_html_exporter.py %*
