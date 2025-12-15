@echo off
REM SF2 Viewer - Windows Launcher
REM Automatically checks for Python and PyQt6, installs if needed, then launches the viewer

setlocal enabledelayedexpansion

echo ================================================================================
echo SF2 Viewer - SID Factory II File Viewer
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version

REM Check if PyQt6 is installed
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARN] PyQt6 is not installed
    echo PyQt6 is required to run the SF2 Viewer
    echo.
    set /p response="Would you like to install PyQt6 now? (y/n): "
    if /i "!response!"=="y" (
        echo.
        echo Installing PyQt6...
        python -m pip install PyQt6
        if errorlevel 1 (
            echo.
            echo [ERROR] Failed to install PyQt6
            echo Please try installing manually with: pip install PyQt6
            echo.
            pause
            exit /b 1
        )
        echo.
        echo [OK] PyQt6 installed successfully
    ) else (
        echo.
        echo To install PyQt6 manually, run:
        echo   pip install PyQt6
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] PyQt6 is installed
)

echo.
echo Starting SF2 Viewer...
echo.

REM Launch the viewer
python sf2_viewer_gui.py
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to launch SF2 Viewer
    echo.
    pause
    exit /b 1
)

endlocal
