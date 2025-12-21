@echo off
REM Update File Inventory - Update docs/FILE_INVENTORY.md with current repository structure
REM Usage: update-inventory.bat
REM
REM Updates:
REM   - Complete file tree with sizes
REM   - Category summaries
REM   - Management rules
REM   - Last updated timestamp
REM
REM Output: docs/FILE_INVENTORY.md
REM
REM Examples:
REM   update-inventory.bat

python update_inventory.py
