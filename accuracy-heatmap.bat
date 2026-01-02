@echo off
REM Accuracy Heatmap Tool - Visualize frame-by-frame register accuracy
REM
REM Generates interactive Canvas-based heatmap comparing two SID files
REM with 4 visualization modes, tooltips, zoom, and accuracy statistics.
REM
REM Usage:
REM   accuracy-heatmap.bat file_a.sid file_b.sid
REM   accuracy-heatmap.bat file_a.sid file_b.sid --frames 1500
REM   accuracy-heatmap.bat file_a.sid file_b.sid --output heatmap.html -v
REM
REM Examples:
REM   accuracy-heatmap.bat original.sid converted.sid
REM   accuracy-heatmap.bat original.sid converted.sid --frames 1000 --output my_heatmap.html
REM   accuracy-heatmap.bat a.sid b.sid -vv  (verbose debugging)
REM
REM Visualization Modes:
REM   Mode 1: Binary Match/Mismatch (green=match, red=mismatch)
REM   Mode 2: Value Delta Magnitude (color intensity by difference)
REM   Mode 3: Register Group Highlighting (Voice 1/2/3/Filter colored)
REM   Mode 4: Frame Accuracy Summary (per-frame accuracy percentage)
REM
REM Output:
REM   - Interactive HTML file (heatmap_<timestamp>.html)
REM   - Canvas-based visualization (frames × 29 registers)
REM   - Switchable modes, hover tooltips, zoom controls
REM   - Accuracy statistics sidebar
REM
REM For help:
REM   accuracy-heatmap.bat --help

python pyscript\accuracy_heatmap_tool.py %*
