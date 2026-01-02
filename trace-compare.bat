@echo off
REM Trace Comparison Tool - Compare two SID files frame-by-frame
REM
REM Compares SID execution traces and generates interactive HTML report.
REM
REM Usage:
REM   trace-compare.bat file_a.sid file_b.sid
REM   trace-compare.bat file_a.sid file_b.sid --frames 1500
REM   trace-compare.bat file_a.sid file_b.sid --output comparison.html -v
REM
REM Examples:
REM   trace-compare.bat original.sid converted.sid
REM   trace-compare.bat laxity_orig.sid driver11_converted.sid --frames 1500
REM   trace-compare.bat a.sid b.sid -v  # Verbose output
REM
REM Output:
REM   - Interactive HTML with 3 tabs (File A, File B, Differences)
REM   - Frame-by-frame timeline visualization
REM   - 4 key metrics: Frame Match %%, Register Accuracy, Voice Accuracy, Total Diffs
REM
REM Options:
REM   --frames N         Number of frames to trace (default: 300)
REM   --output FILE      Output HTML path (default: comparison_<timestamp>.html)
REM   -v, -vv            Verbose logging
REM   --no-html          Skip HTML generation (quick comparison)
REM   --help             Show detailed help

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
    echo Trace Comparison Tool - Compare two SID files frame-by-frame
    echo.
    echo Usage: trace-compare.bat file_a.sid file_b.sid [options]
    echo.
    echo Examples:
    echo   trace-compare.bat original.sid converted.sid
    echo   trace-compare.bat a.sid b.sid --frames 1500 --output comparison.html
    echo   trace-compare.bat a.sid b.sid -v
    echo.
    echo For detailed help: trace-compare.bat --help
    exit /b 1
)

REM Run comparison tool
python pyscript\trace_comparison_tool.py %*

endlocal
