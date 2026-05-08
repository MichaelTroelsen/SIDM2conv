@echo off
REM star-launcher.bat — serve star.html over local HTTP so fetch() works.
REM Browsers block fetch() from file:// URLs; this spins up Python's
REM built-in http.server on port 8765 and opens the page through it.

setlocal
set PORT=8765

cd /d "%~dp0"

echo Starting local HTTP server on port %PORT%...
start "SIDM2 star.html server" /MIN cmd /c "py -3 -m http.server %PORT% 1>nul 2>nul"

REM Give the server a moment to bind
ping 127.0.0.1 -n 2 >nul

REM Open in default browser
start "" "http://localhost:%PORT%/star.html"

echo.
echo Server running at http://localhost:%PORT%/
echo Close the minimized "SIDM2 star.html server" window to stop it.
endlocal
