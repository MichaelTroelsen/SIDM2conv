@echo off
REM Python SIDwinder Trace - Batch Launcher
REM Usage: sidwinder-trace.bat -trace=<output> -frames=<count> <input>

python pyscript\sidwinder_trace.py %*
