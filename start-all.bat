@echo off
REM Start-All: Launch C64 Knowledge MCP Server + SF2 Viewer Client
REM This script starts both the server and client components

echo.
echo ========================================
echo C64 Server + SIDM2 Client Launcher
echo ========================================
echo.

REM Check if running from SIDM2 directory
if not exist "sf2_viewer_gui.py" (
    echo ERROR: Must run from SIDM2 directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo [1/2] Starting C64 Knowledge MCP Server...
echo.

REM Start MCP server in a new window
start "C64 Knowledge MCP Server" /D "..\tdz-c64-knowledge" cmd /k "launch-server-full-features.bat"

REM Wait a moment for server to initialize
timeout /t 3 /nobreak >nul

echo [2/2] Starting SF2 Viewer Client...
echo.

REM Launch SF2 Viewer client
call launch_sf2_viewer.bat

echo.
echo ========================================
echo Startup complete!
echo ========================================
echo.
echo MCP Server: Running in separate window
echo SF2 Viewer: Should be launching now
echo.
echo To stop:
echo  - Close SF2 Viewer window
echo  - Close MCP Server window (Ctrl+C)
echo.
