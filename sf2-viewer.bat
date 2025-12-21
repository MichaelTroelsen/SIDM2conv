@echo off
REM SF2 Viewer - View and analyze SF2 files with interactive GUI
REM Usage: sf2-viewer.bat [optional_file.sf2]
REM
REM Features:
REM   - Multi-tab interface (Overview, Header Blocks, Tables, Memory Map, OrderList, Sequences, Track View, Visualization, Playback)
REM   - Track View with transpose application
REM   - Musical notation display
REM   - Recent files menu
REM   - Drag-and-drop support
REM
REM Examples:
REM   sf2-viewer.bat
REM   sf2-viewer.bat "learnings/Laxity - Stinsen - Last Night Of 89.sf2"

python sf2_viewer_gui.py %*
