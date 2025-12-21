@echo off
REM SIDM2 Tools Launcher - Quick access to all SIDM2 tools
REM Usage: TOOLS.bat
REM
REM This launcher provides a menu-driven interface to all SIDM2 tools

:MENU
cls
echo ================================================================================
echo                         SIDM2 TOOLS LAUNCHER
echo ================================================================================
echo.
echo [MAIN TOOLS]
echo   1. SF2 Viewer          - View and analyze SF2 files (GUI)
echo   2. SF2 Text Exporter   - Export SF2 to text files
echo   3. SID to SF2          - Convert SID file to SF2
echo   4. SF2 to SID          - Convert SF2 file to SID
echo.
echo [BATCH OPERATIONS]
echo   5. Batch Convert All   - Convert all SID files
echo   6. Batch Convert Laxity - Convert all Laxity SID files
echo   7. Complete Pipeline   - Full validation pipeline
echo.
echo [TESTING ^& VALIDATION]
echo   8. Test Converter      - Run unit tests
echo   9. Test Roundtrip      - Test SID→SF2→SID
echo  10. Validate Accuracy   - Frame-by-frame validation
echo.
echo [MAINTENANCE]
echo  11. Cleanup             - Clean temporary files
echo  12. Update Inventory    - Update file inventory
echo.
echo [OTHER]
echo  13. List All Tools      - Show complete tools reference
echo   0. Exit
echo.
echo ================================================================================
set /p choice="Select tool (0-13): "

if "%choice%"=="1" goto VIEWER
if "%choice%"=="2" goto EXPORT
if "%choice%"=="3" goto SID2SF2
if "%choice%"=="4" goto SF22SID
if "%choice%"=="5" goto BATCH
if "%choice%"=="6" goto BATCH_LAXITY
if "%choice%"=="7" goto PIPELINE
if "%choice%"=="8" goto TEST
if "%choice%"=="9" goto ROUNDTRIP
if "%choice%"=="10" goto VALIDATE
if "%choice%"=="11" goto CLEANUP
if "%choice%"=="12" goto INVENTORY
if "%choice%"=="13" goto LIST
if "%choice%"=="0" goto END
goto MENU

:VIEWER
cls
echo Starting SF2 Viewer...
echo.
set /p file="Enter SF2 file path (or press Enter for empty viewer): "
if "%file%"=="" (
    call sf2-viewer.bat
) else (
    call sf2-viewer.bat "%file%"
)
pause
goto MENU

:EXPORT
cls
echo SF2 Text Exporter
echo.
set /p infile="Enter SF2 file path: "
if "%infile%"=="" (
    echo Error: Input file required
    pause
    goto MENU
)
set /p outdir="Enter output directory (or press Enter for auto): "
if "%outdir%"=="" (
    call sf2-export.bat "%infile%"
) else (
    call sf2-export.bat "%infile%" "%outdir%"
)
pause
goto MENU

:SID2SF2
cls
echo SID to SF2 Converter
echo.
set /p infile="Enter SID file path: "
if "%infile%"=="" (
    echo Error: Input file required
    pause
    goto MENU
)
set /p outfile="Enter SF2 output path: "
if "%outfile%"=="" (
    echo Error: Output file required
    pause
    goto MENU
)
echo.
echo Select driver:
echo   1. Laxity (99.93%% accuracy - recommended for Laxity SIDs)
echo   2. Driver 11 (standard)
echo   3. NP20
echo   4. Auto-detect
set /p driver="Driver (1-4): "
if "%driver%"=="1" (
    call sid-to-sf2.bat "%infile%" "%outfile%" --driver laxity
) else if "%driver%"=="2" (
    call sid-to-sf2.bat "%infile%" "%outfile%" --driver driver11
) else if "%driver%"=="3" (
    call sid-to-sf2.bat "%infile%" "%outfile%" --driver np20
) else (
    call sid-to-sf2.bat "%infile%" "%outfile%"
)
pause
goto MENU

:SF22SID
cls
echo SF2 to SID Converter
echo.
set /p infile="Enter SF2 file path: "
if "%infile%"=="" (
    echo Error: Input file required
    pause
    goto MENU
)
set /p outfile="Enter SID output path: "
if "%outfile%"=="" (
    echo Error: Output file required
    pause
    goto MENU
)
call sf2-to-sid.bat "%infile%" "%outfile%"
pause
goto MENU

:BATCH
cls
echo Batch Convert All SID Files
echo.
echo This will convert all SID files in SID/ directory
set /p confirm="Continue? (y/n): "
if /i "%confirm%"=="y" (
    call batch-convert.bat
)
pause
goto MENU

:BATCH_LAXITY
cls
echo Batch Convert Laxity SID Files
echo.
echo This will convert all Laxity NewPlayer v21 SID files
set /p confirm="Continue? (y/n): "
if /i "%confirm%"=="y" (
    call batch-convert-laxity.bat
)
pause
goto MENU

:PIPELINE
cls
echo Complete Pipeline with Validation
echo.
echo This runs the full 13-step pipeline on test files
set /p confirm="Continue? (y/n): "
if /i "%confirm%"=="y" (
    call pipeline.bat
)
pause
goto MENU

:TEST
cls
echo Running Converter Unit Tests...
echo.
call test-converter.bat -v
pause
goto MENU

:ROUNDTRIP
cls
echo Test Roundtrip Conversion
echo.
set /p infile="Enter SID file path: "
if "%infile%"=="" (
    echo Error: Input file required
    pause
    goto MENU
)
call test-roundtrip.bat "%infile%"
pause
goto MENU

:VALIDATE
cls
echo Validate Accuracy
echo.
set /p orig="Enter original SID file path: "
if "%orig%"=="" (
    echo Error: Original file required
    pause
    goto MENU
)
set /p conv="Enter converted SID file path: "
if "%conv%"=="" (
    echo Error: Converted file required
    pause
    goto MENU
)
call validate-accuracy.bat "%orig%" "%conv%"
pause
goto MENU

:CLEANUP
cls
echo Cleanup Tool
echo.
echo Select cleanup mode:
echo   1. Scan only (show what would be cleaned)
echo   2. Clean with confirmation
echo   3. Clean with force (no confirmation)
echo   4. Clean all + update inventory
set /p mode="Mode (1-4): "
if "%mode%"=="1" (
    call cleanup.bat --scan
) else if "%mode%"=="2" (
    call cleanup.bat --clean
) else if "%mode%"=="3" (
    call cleanup.bat --clean --force
) else if "%mode%"=="4" (
    call cleanup.bat --all --clean --force --update-inventory
)
pause
goto MENU

:INVENTORY
cls
echo Updating File Inventory...
echo.
call update-inventory.bat
pause
goto MENU

:LIST
cls
type TOOLS_REFERENCE.txt
pause
goto MENU

:END
exit /b 0
