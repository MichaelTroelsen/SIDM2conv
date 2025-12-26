#Region ;**** Directives ****
; #RequireAdmin  ; Removed - not needed for file loading
#AutoIt3Wrapper_Res_Description=SID Factory II Automated File Loader
#AutoIt3Wrapper_Res_Fileversion=1.0.0.0
; #AutoIt3Wrapper_Icon=sf2_icon.ico  ; Icon file not included
#EndRegion

; ============================================================================
; SID Factory II Automated File Loader with Keep-Alive
; ============================================================================
; Purpose: Launch SID Factory II, load file, prevent auto-close
; Usage: sf2_loader.exe <editor_path> <sf2_file_path> <status_file>
;
; Author: SIDM2 Project
; Version: 1.0.0
; Date: 2025-12-26
; ============================================================================

#include <File.au3>
#include <Array.au3>

; ============================================================================
; CONFIGURATION
; ============================================================================

Global Const $KEEP_ALIVE_INTERVAL = 500 ; milliseconds (0.5 seconds)
Global Const $MAX_WAIT_WINDOW = 10000   ; 10 seconds to wait for window
Global Const $MAX_WAIT_DIALOG = 5000    ; 5 seconds for dialog
Global Const $MAX_WAIT_LOAD = 30000     ; 30 seconds for file load
Global Const $F10_KEY = "{F10}"
Global Const $ENTER_KEY = "{ENTER}"
Global Const $WM_NULL = 0x0000

; Global variables
Global $g_hwnd = 0  ; Window handle (set by main before starting keep-alive)
Global $g_statusFile = ""

; ============================================================================
; MAIN FUNCTION
; ============================================================================

Func Main()
    ; Parse command line arguments
    If $CmdLine[0] < 3 Then
        WriteStatus("ERROR: Invalid arguments")
        ConsoleWrite("Usage: sf2_loader.exe <editor_path> <sf2_file> <status_file>" & @CRLF)
        ConsoleWrite("Example: sf2_loader.exe ""C:\SIDFactoryII\SIDFactoryII.exe"" ""C:\music.sf2"" ""status.txt""" & @CRLF)
        Exit(1)
    EndIf

    Local $editorPath = $CmdLine[1]
    Local $sf2File = $CmdLine[2]
    $g_statusFile = $CmdLine[3]

    ; Validate files exist
    If Not FileExists($editorPath) Then
        WriteStatus("ERROR: Editor not found: " & $editorPath)
        ConsoleWrite("ERROR: Editor not found: " & $editorPath & @CRLF)
        Exit(1)
    EndIf

    If Not FileExists($sf2File) Then
        WriteStatus("ERROR: SF2 file not found: " & $sf2File)
        ConsoleWrite("ERROR: SF2 file not found: " & $sf2File & @CRLF)
        Exit(1)
    EndIf

    ; Initialize
    WriteStatus("STARTING")
    ConsoleWrite("SF2 Loader Starting..." & @CRLF)
    ConsoleWrite("  Editor: " & $editorPath & @CRLF)
    ConsoleWrite("  File: " & $sf2File & @CRLF)
    ConsoleWrite("  Status: " & $g_statusFile & @CRLF)
    ConsoleWrite(@CRLF)

    ; Step 1: Launch editor
    WriteStatus("LAUNCHING")
    ConsoleWrite("Step 1: Launching editor..." & @CRLF)

    Local $pid = Run($editorPath, "", @SW_SHOW)

    If @error Or $pid = 0 Then
        WriteStatus("ERROR: Failed to launch editor")
        ConsoleWrite("  ERROR: Failed to launch editor (error code: " & @error & ")" & @CRLF)
        Exit(1)
    EndIf

    ConsoleWrite("  PID: " & $pid & @CRLF)

    ; Step 2: Wait for window
    WriteStatus("WAITING_WINDOW")
    ConsoleWrite("Step 2: Waiting for window..." & @CRLF)

    Local $hwnd = WaitForWindow("SID Factory II", $MAX_WAIT_WINDOW)

    If $hwnd = 0 Then
        WriteStatus("ERROR: Window not found")
        ConsoleWrite("  ERROR: Window not found within " & ($MAX_WAIT_WINDOW / 1000) & " seconds" & @CRLF)
        ProcessClose($pid)
        Exit(1)
    EndIf

    ConsoleWrite("  Window Handle: " & $hwnd & @CRLF)

    ; Step 3: Start keep-alive (prevents auto-close)
    WriteStatus("KEEP_ALIVE_STARTED")
    ConsoleWrite("Step 3: Starting keep-alive mechanism..." & @CRLF)
    AdlibRegister("KeepAlive", $KEEP_ALIVE_INTERVAL)
    ConsoleWrite("  Keep-alive interval: " & $KEEP_ALIVE_INTERVAL & "ms" & @CRLF)

    ; Step 4: Load file
    WriteStatus("LOADING_FILE")
    ConsoleWrite("Step 4: Loading file..." & @CRLF)

    Local $success = LoadFile($hwnd, $sf2File)

    If Not $success Then
        WriteStatus("ERROR: File load failed")
        ConsoleWrite("  ERROR: File load failed" & @CRLF)
        AdlibUnRegister("KeepAlive")
        Exit(1)
    EndIf

    ; Step 5: Verify file loaded
    WriteStatus("VERIFYING")
    ConsoleWrite("Step 5: Verifying file load..." & @CRLF)
    Sleep(1000) ; Give editor time to update title

    Local $title = WinGetTitle($hwnd)
    If StringInStr($title, ".sf2") > 0 Then
        WriteStatus("SUCCESS:" & $title)
        ConsoleWrite("  SUCCESS: File loaded!" & @CRLF)
        ConsoleWrite("  Window Title: " & $title & @CRLF)
    Else
        WriteStatus("WARNING: File may not be loaded (title: " & $title & ")")
        ConsoleWrite("  WARNING: File may not have loaded" & @CRLF)
        ConsoleWrite("  Window Title: " & $title & @CRLF)
        ; Don't exit - let Python decide if this is acceptable
    EndIf

    ; Step 6: Stop keep-alive and exit
    ; Editor stays open, Python will take over
    AdlibUnRegister("KeepAlive")
    ConsoleWrite(@CRLF)
    ConsoleWrite("AutoIt script exiting (editor stays open)" & @CRLF)
    ConsoleWrite("Python can now attach to editor for validation/playback" & @CRLF)

    Exit(0)
EndFunc

; ============================================================================
; KEEP-ALIVE MECHANISM
; ============================================================================

Func KeepAlive()
    ; Aggressive keep-alive to prevent auto-close
    ; Uses multiple methods to simulate user presence
    If WinExists($g_hwnd) Then
        ; Method 1: Move mouse cursor slightly (invisible to user)
        Local $pos = MouseGetPos()
        MouseMove($pos[0] + 1, $pos[1], 0)
        MouseMove($pos[0], $pos[1], 0)

        ; Method 2: Send WM_SETCURSOR to simulate mouse movement
        DllCall("user32.dll", "lresult", "SendMessageW", _
                "hwnd", $g_hwnd, _
                "uint", 0x0020, _  ; WM_SETCURSOR
                "wparam", $g_hwnd, _
                "lparam", 0x02010001)

        ; Method 3: Send WM_NCMOUSEMOVE to simulate mouse over titlebar
        DllCall("user32.dll", "lresult", "SendMessageW", _
                "hwnd", $g_hwnd, _
                "uint", 0x00A0, _  ; WM_NCMOUSEMOVE
                "wparam", 2, _  ; HTCAPTION
                "lparam", 0)
    EndIf
EndFunc

; ============================================================================
; FILE LOADING FUNCTION
; ============================================================================

Func LoadFile($hwnd, $filePath)
    ConsoleWrite("  Checking window state..." & @CRLF)

    ; Check if window is already active
    If WinActive($hwnd) Then
        ConsoleWrite("  Window is already active" & @CRLF)
    Else
        ConsoleWrite("  Activating window..." & @CRLF)

        ; Aggressive window activation
        WinSetState($hwnd, "", @SW_SHOW)
        Sleep(100)
        WinSetState($hwnd, "", @SW_RESTORE)
        Sleep(100)
        WinSetOnTop($hwnd, "", 1)  ; Set window on top
        Sleep(100)
        WinActivate($hwnd)
        Sleep(300)

        ; Try multiple times if needed
        Local $attempts = 0
        While Not WinActive($hwnd) And $attempts < 10
            ; Try different activation methods
            If Mod($attempts, 2) = 0 Then
                WinActivate($hwnd)
            Else
                ; Try clicking on the window
                WinSetState($hwnd, "", @SW_SHOW)
                ControlFocus($hwnd, "", "")
            EndIf
            Sleep(150)
            $attempts += 1
        WEnd

        If Not WinActive($hwnd) Then
            ConsoleWrite("  WARNING: Could not activate window after " & $attempts & " attempts" & @CRLF)
            ConsoleWrite("  Attempting to proceed anyway..." & @CRLF)
        Else
            ConsoleWrite("  Window activated successfully" & @CRLF)
        EndIf
    EndIf

    ; Wait a bit longer before sending keys
    Sleep(1000)

    ; Send F10 to open file dialog - use Send instead of ControlSend
    ConsoleWrite("  Sending F10 key..." & @CRLF)
    Send($F10_KEY)
    Sleep(1000)

    ; Wait for dialog to appear
    ConsoleWrite("  Waiting for file dialog..." & @CRLF)
    Local $dialogFound = False
    Local $dialogHwnd = 0
    Local $startTime = TimerInit()

    While TimerDiff($startTime) < $MAX_WAIT_DIALOG
        ; Look for file dialog windows
        Local $windowList = WinList()
        For $i = 1 To $windowList[0][0]
            Local $title = $windowList[$i][0]
            Local $handle = $windowList[$i][1]

            ; Check for common file dialog titles
            If StringInStr($title, "Open") Or _
               StringInStr($title, "Load") Or _
               StringInStr($title, "File") Then
                ; Check if owned by editor
                Local $owner = DllCall("user32.dll", "hwnd", "GetWindow", "hwnd", $handle, "uint", 4) ; GW_OWNER
                If IsArray($owner) And $owner[0] = $hwnd Then
                    $dialogHwnd = $handle
                    $dialogFound = True
                    ConsoleWrite("  Dialog found: " & $title & " (handle: " & $handle & ")" & @CRLF)
                    ExitLoop
                EndIf
            EndIf
        Next

        If $dialogFound Then ExitLoop
        Sleep(100)
    WEnd

    If Not $dialogFound Then
        ConsoleWrite("  WARNING: File dialog not found, using active window" & @CRLF)
    Else
        ; Activate dialog if found
        WinActivate($dialogHwnd)
        Sleep(200)
    EndIf

    ; Type file path using Send (works with active window)
    ConsoleWrite("  Typing file path..." & @CRLF)
    Send($filePath)
    Sleep(500)

    ; Press Enter
    ConsoleWrite("  Pressing Enter..." & @CRLF)
    Send($ENTER_KEY)
    Sleep(500)

    ; Wait for file to load (window title changes)
    ConsoleWrite("  Waiting for file to load..." & @CRLF)
    $startTime = TimerInit()
    Local $titleBefore = WinGetTitle($hwnd)

    While TimerDiff($startTime) < $MAX_WAIT_LOAD
        Sleep(500)
        Local $titleNow = WinGetTitle($hwnd)

        ; File loaded if title changed and contains .sf2
        If $titleNow <> $titleBefore And StringInStr($titleNow, ".sf2") > 0 Then
            ConsoleWrite("  File loaded! New title: " & $titleNow & @CRLF)
            ConsoleWrite("  Load time: " & Round(TimerDiff($startTime) / 1000, 2) & " seconds" & @CRLF)
            Return True
        EndIf

        ; Also check if window closed
        If Not WinExists($hwnd) Then
            ConsoleWrite("  ERROR: Editor window closed during load" & @CRLF)
            Return False
        EndIf
    WEnd

    ConsoleWrite("  Timeout waiting for file load (" & ($MAX_WAIT_LOAD / 1000) & " seconds)" & @CRLF)
    Return False
EndFunc

; ============================================================================
; HELPER FUNCTIONS
; ============================================================================

Func WaitForWindow($title, $timeout)
    Local $startTime = TimerInit()
    Local $lastCheck = 0

    While TimerDiff($startTime) < $timeout
        ; Check if window exists
        Local $hwnd = WinGetHandle($title)
        If Not @error And $hwnd <> 0 Then
            ; Store handle for keep-alive
            $g_hwnd = $hwnd
            ConsoleWrite("  Window found after " & Round(TimerDiff($startTime) / 1000, 2) & " seconds" & @CRLF)
            Return $hwnd
        EndIf

        ; Progress indicator every second
        If TimerDiff($startTime) - $lastCheck > 1000 Then
            ConsoleWrite("  Waiting... (" & Round(TimerDiff($startTime) / 1000) & "s/" & Round($timeout / 1000) & "s)" & @CRLF)
            $lastCheck = TimerDiff($startTime)
        EndIf

        Sleep(100)
    WEnd

    Return 0
EndFunc

Func WriteStatus($status)
    ; Write status to file for Python to read
    Local $handle = FileOpen($g_statusFile, 2) ; Overwrite mode
    If $handle <> -1 Then
        FileWrite($handle, $status & @CRLF)
        FileClose($handle)
    Else
        ConsoleWrite("  WARNING: Could not write status file: " & $g_statusFile & @CRLF)
    EndIf
EndFunc

; ============================================================================
; ENTRY POINT
; ============================================================================

Main()
