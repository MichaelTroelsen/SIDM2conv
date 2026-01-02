@echo off
REM Batch Analysis with Validation Pipeline Integration
REM
REM Runs batch analysis and stores results in validation database
REM
REM Usage:
REM   batch-analysis-validate.bat originals/ exported/
REM   batch-analysis-validate.bat originals/ exported/ --frames 500
REM   batch-analysis-validate.bat originals/ exported/ --run-id 5
REM   batch-analysis-validate.bat originals/ exported/ --no-heatmaps
REM
REM Examples:
REM   batch-analysis-validate.bat SID/ output/converted/
REM   batch-analysis-validate.bat originals/ exported/ --notes "Testing v3.1"
REM
REM Output:
REM   - Batch analysis results (HTML, CSV, JSON)
REM   - Results stored in validation/database.sqlite
REM   - Metrics added to validation trends
REM
REM Integration:
REM   - Results viewable in validation dashboard
REM   - Linked to validation runs
REM   - Tracks accuracy trends over time
REM
REM For help:
REM   batch-analysis-validate.bat --help

python scripts\validation\batch_analysis_integration.py %*
