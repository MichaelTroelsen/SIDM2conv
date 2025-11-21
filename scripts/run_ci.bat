@echo off
REM Local CI Runner for Windows
REM Usage: run_ci.bat [--push] [--message "commit message"]

cd /d "%~dp0\.."
python scripts\ci_local.py %*
