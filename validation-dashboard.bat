@echo off
REM Validation Dashboard - Generate interactive HTML dashboard from validation results
REM Usage: validation-dashboard.bat [--run RUN_ID] [--output FILE.html]
REM
REM Features:
REM   - Professional HTMLComponents styling with dark VS Code theme
REM   - Enhanced search with accuracy range filters (>90, <70)
REM   - Interactive Chart.js trends across validation runs
REM   - Sidebar navigation with summary stats
REM   - Color-coded accuracy bars and fail-first sorting
REM   - Self-contained HTML (works offline, easy sharing)
REM
REM Options:
REM   --run RUN_ID        - Generate dashboard for specific validation run ID
REM   --output FILE.html  - Specify custom output file path
REM
REM Examples:
REM   validation-dashboard.bat
REM   validation-dashboard.bat --run 5
REM   validation-dashboard.bat --output custom_dashboard.html
REM   validation-dashboard.bat --run 5 --output run5.html

python scripts/generate_dashboard.py %*
