@echo off
REM ============================================================================
REM Batch SF2 File Testing with PyAutoGUI Automation
REM ============================================================================
REM Purpose: Test multiple SF2 files using PyAutoGUI automation
REM Version: 1.0.0
REM Date: 2025-12-26
REM ============================================================================

setlocal

REM Python launcher (try python3 first, fallback to python)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python3
) else (
    set PYTHON=python
)

REM Default arguments
set DIRECTORY=output
set PATTERN=*.sf2
set PLAYBACK=3
set STABILITY=2
set MAX_FILES=
set TIMEOUT=30

REM Parse command-line arguments
:parse_args
if "%~1"=="" goto run_test
if /i "%~1"=="--directory" set DIRECTORY=%~2& shift & shift & goto parse_args
if /i "%~1"=="-d" set DIRECTORY=%~2& shift & shift & goto parse_args
if /i "%~1"=="--pattern" set PATTERN=%~2& shift & shift & goto parse_args
if /i "%~1"=="-p" set PATTERN=%~2& shift & shift & goto parse_args
if /i "%~1"=="--playback" set PLAYBACK=%~2& shift & shift & goto parse_args
if /i "%~1"=="-pb" set PLAYBACK=%~2& shift & shift & goto parse_args
if /i "%~1"=="--stability" set STABILITY=%~2& shift & shift & goto parse_args
if /i "%~1"=="-s" set STABILITY=%~2& shift & shift & goto parse_args
if /i "%~1"=="--max-files" set MAX_FILES=%~2& shift & shift & goto parse_args
if /i "%~1"=="-m" set MAX_FILES=%~2& shift & shift & goto parse_args
if /i "%~1"=="--timeout" set TIMEOUT=%~2& shift & shift & goto parse_args
if /i "%~1"=="-t" set TIMEOUT=%~2& shift & shift & goto parse_args
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-h" goto show_help
shift
goto parse_args

:run_test
REM Build command
set CMD=%PYTHON% pyscript/test_batch_pyautogui.py --directory "%DIRECTORY%" --pattern "%PATTERN%" --playback %PLAYBACK% --stability %STABILITY% --timeout %TIMEOUT%

if not "%MAX_FILES%"=="" set CMD=%CMD% --max-files %MAX_FILES%

REM Run test
echo.
echo ============================================================================
echo PyAutoGUI Batch Testing Launcher
echo ============================================================================
echo.
echo Directory:   %DIRECTORY%
echo Pattern:     %PATTERN%
echo Playback:    %PLAYBACK%s
echo Stability:   %STABILITY%s
echo Max Files:   %MAX_FILES%
echo Timeout:     %TIMEOUT%s
echo.
echo ============================================================================
echo.

%CMD%

goto end

:show_help
echo.
echo PyAutoGUI Batch Testing Launcher
echo.
echo Usage:
echo   test-batch-pyautogui.bat [OPTIONS]
echo.
echo Options:
echo   --directory, -d DIR      Directory to search for SF2 files (default: output)
echo   --pattern, -p PATTERN    Glob pattern for SF2 files (default: *.sf2)
echo   --playback, -pb SECS     Playback duration per file (default: 3)
echo   --stability, -s SECS     Window stability check duration (default: 2)
echo   --max-files, -m NUM      Maximum number of files to test (default: all)
echo   --timeout, -t SECS       Timeout per file (default: 30)
echo   --help, -h               Show this help message
echo.
echo Examples:
echo   test-batch-pyautogui.bat
echo   test-batch-pyautogui.bat --directory output/Laxity --max-files 5
echo   test-batch-pyautogui.bat --pattern "Driver*.sf2" --playback 5
echo.

:end
endlocal
