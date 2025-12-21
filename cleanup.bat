@echo off
REM Cleanup Tool - Clean temporary and experimental files
REM Usage: cleanup.bat [--scan|--clean] [--force] [--update-inventory]
REM
REM Modes:
REM   --scan              Scan and show what would be cleaned (default)
REM   --clean             Actually remove files (requires confirmation)
REM   --force             Skip confirmation prompt
REM   --update-inventory  Update FILE_INVENTORY.md after cleanup
REM   --output-only       Clean only output directory
REM   --experiments       Clean only experiments directory
REM   --all               Clean everything (root + output + experiments)
REM
REM Safety Features:
REM   - RULE 1: NEVER cleans git-tracked files
REM   - RULE 2: Explicit keep files list
REM   - RULE 3: Keep directories protected
REM   - Backup list created for every cleanup
REM
REM Examples:
REM   cleanup.bat
REM   cleanup.bat --scan
REM   cleanup.bat --clean
REM   cleanup.bat --clean --force --update-inventory
REM   cleanup.bat --all --clean --update-inventory

python pyscript/cleanup.py %*
