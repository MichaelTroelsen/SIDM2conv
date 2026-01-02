@echo off
REM Batch Analysis Tool - Compare multiple SID file pairs
REM
REM Compares SID files from two directories, generating:
REM - Individual heatmaps and comparison HTMLs
REM - Aggregate summary report (HTML + CSV + JSON)
REM
REM Usage:
REM   batch-analysis.bat dir_a/ dir_b/
REM   batch-analysis.bat originals/ exported/ -o results/
REM   batch-analysis.bat dir_a/ dir_b/ --frames 500 --no-heatmaps
REM
REM Examples:
REM   batch-analysis.bat SID/ output/ -o analysis_results/
REM   batch-analysis.bat originals/ exported/ --frames 1000
REM   batch-analysis.bat dir_a/ dir_b/ --no-comparisons -v
REM
REM Output:
REM   - batch_summary.html (interactive report with sortable table, charts)
REM   - batch_results.csv (spreadsheet export)
REM   - batch_results.json (machine-readable)
REM   - heatmaps/ (individual heatmap HTMLs for each pair)
REM   - comparisons/ (individual comparison HTMLs for each pair)
REM
REM File Pairing:
REM   Auto-pairs files by matching basenames:
REM   - song.sid <-> song_exported.sid
REM   - song.sid <-> song_laxity_exported.sid
REM   - song.sid <-> song.sf2_exported.sid
REM
REM Options:
REM   -o, --output DIR          Output directory (default: batch_analysis_output)
REM   -f, --frames N            Frames to trace per file (default: 300)
REM   --no-heatmaps             Skip heatmap generation (faster)
REM   --no-comparisons          Skip comparison HTML generation (faster)
REM   --no-html                 Skip HTML summary report
REM   --no-csv                  Skip CSV export
REM   --no-json                 Skip JSON export
REM   -v, --verbose             Increase verbosity (-v, -vv)
REM
REM For help:
REM   batch-analysis.bat --help

python pyscript\batch_analysis_tool.py %*
