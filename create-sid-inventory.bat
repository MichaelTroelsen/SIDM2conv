@echo off
REM Create SID Inventory - Batch Launcher
REM
REM Scans all SID files (excluding output/) and creates SID_INVENTORY.md
REM
REM Tools used:
REM - SID header parser (Python)
REM - player-id.exe (player identification)
REM - File system (size, path)

echo ================================================================================
echo SID File Inventory Creator
echo ================================================================================
echo.
echo This script will:
echo   1. Scan all SID files (excluding output folder)
echo   2. Parse SID headers (title, author, copyright, addresses)
echo   3. Identify player types using player-id.exe
echo   4. Generate SID_INVENTORY.md with detailed grid view
echo.
echo Estimated time: ~2-5 minutes for 650+ files
echo.
echo ================================================================================
echo.

REM Run Python script
python pyscript\create_sid_inventory.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create inventory
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo SUCCESS!
echo ================================================================================
echo.
echo Inventory created: SID_INVENTORY.md
echo.
echo You can now:
echo   - Open SID_INVENTORY.md in a markdown viewer
echo   - Search for specific titles/authors/players
echo   - Use as reference for batch conversion
echo.
pause
