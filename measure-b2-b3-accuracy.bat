@echo off
REM Measure B2+B3 Integration Accuracy Improvements
REM
REM Usage:
REM   measure-b2-b3-accuracy.bat          (default: 10 files from Fun_Fun)
REM   measure-b2-b3-accuracy.bat 5        (test 5 files)
REM   measure-b2-b3-accuracy.bat 15       (test 15 files)

setlocal

set MAX_FILES=%1
if "%MAX_FILES%"=="" set MAX_FILES=10

echo.
echo ========================================
echo B2+B3 Accuracy Measurement
echo ========================================
echo Max files: %MAX_FILES%
echo.

python pyscript/measure_b2_b3_accuracy.py --files %MAX_FILES%

endlocal
