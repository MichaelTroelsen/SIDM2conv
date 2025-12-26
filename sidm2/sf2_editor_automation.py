#!/usr/bin/env python3
"""
SF2 Editor Automation - Automate SID Factory II editor operations

Provides automation for:
- Launching SID Factory II editor
- Loading SF2 files
- Detecting load completion
- Starting/stopping playback
- Packing SF2 to SID
- Closing editor

Uses Windows API for process and window control.
"""

import subprocess
import time
import psutil
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

# Windows-specific imports (conditional)
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WINDOWS_API_AVAILABLE = True
except ImportError:
    WINDOWS_API_AVAILABLE = False
    print("Warning: pywin32 not available - SF2 Editor automation will be limited")
    print("Install with: pip install pywin32")

from sidm2.sf2_debug_logger import get_sf2_logger, SF2EventType
from sidm2.automation_config import AutomationConfig

# PyAutoGUI imports (conditional)
try:
    import sys
    # Add pyscript to path for PyAutoGUI automation module
    pyscript_path = Path(__file__).parent.parent / "pyscript"
    if str(pyscript_path) not in sys.path:
        sys.path.insert(0, str(pyscript_path))

    from sf2_pyautogui_automation import SF2PyAutoGUIAutomation
    PYAUTOGUI_AVAILABLE = True
except ImportError as e:
    PYAUTOGUI_AVAILABLE = False
    SF2PyAutoGUIAutomation = None


class SF2EditorAutomationError(Exception):
    """Base exception for editor automation errors"""
    pass


class SF2EditorNotFoundError(SF2EditorAutomationError):
    """Editor executable not found"""
    pass


class SF2EditorTimeoutError(SF2EditorAutomationError):
    """Editor operation timeout"""
    pass


class SF2EditorAutomation:
    """Automate SID Factory II editor operations"""

    def __init__(self, editor_path: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize SF2 Editor automation

        Args:
            editor_path: Path to SIDFactoryII.exe (auto-detected if None)
            config_path: Path to configuration file (default: config/sf2_automation.ini)
        """
        # Load configuration
        self.config = AutomationConfig(config_path)

        self.logger = get_sf2_logger()
        self.editor_path = editor_path or self._find_editor()
        self.process: Optional[subprocess.Popen] = None
        self.window_handle: Optional[int] = None
        self.pid: Optional[int] = None
        self.stdout_file = None
        self.stderr_file = None

        # AutoIt configuration (from config file)
        self.autoit_script = self.config.autoit_script_path
        self.autoit_enabled = self.config.autoit_enabled and self.autoit_script.exists()
        self.autoit_timeout = self.config.autoit_timeout
        self.use_autoit_by_default = self.autoit_enabled

        # PyAutoGUI configuration
        self.pyautogui_enabled = self.config.pyautogui_enabled and PYAUTOGUI_AVAILABLE
        self.pyautogui_automation = None
        if self.pyautogui_enabled:
            try:
                self.pyautogui_automation = SF2PyAutoGUIAutomation(self.editor_path)
            except Exception as e:
                self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                    'message': 'Failed to initialize PyAutoGUI automation',
                    'error': str(e)
                })
                self.pyautogui_enabled = False

        # Determine default automation mode (priority: PyAutoGUI > AutoIt > Manual)
        if self.pyautogui_enabled:
            self.default_automation_mode = 'pyautogui'
        elif self.autoit_enabled:
            self.default_automation_mode = 'autoit'
        else:
            self.default_automation_mode = 'manual'

        if not WINDOWS_API_AVAILABLE:
            self.logger.log_action("Windows API not available - automation limited", {
                'platform': 'non-Windows or missing pywin32'
            })

        self.logger.log_action("SF2 Editor Automation initialized", {
            'editor_path': self.editor_path,
            'windows_api': WINDOWS_API_AVAILABLE,
            'autoit_enabled': self.autoit_enabled,
            'autoit_script': str(self.autoit_script) if self.autoit_enabled else None,
            'pyautogui_enabled': self.pyautogui_enabled,
            'pyautogui_available': PYAUTOGUI_AVAILABLE,
            'default_mode': self.default_automation_mode,
            'config_file': str(self.config.config_path),
            'config_exists': self.config.config_path.exists()
        })

    def _find_editor(self) -> str:
        """Find SIDFactoryII.exe using configured paths

        Returns:
            Path to editor executable

        Raises:
            SF2EditorNotFoundError: If editor not found
        """
        # Use config to find editor
        editor_path = self.config.find_editor_path()

        if editor_path:
            self.logger.log_action("Found SIDFactoryII.exe", {
                'path': str(editor_path)
            })
            return str(editor_path)

        # If not found, report error with configured paths
        search_paths = self.config.editor_paths
        error_msg = f"SIDFactoryII.exe not found in configured locations: {search_paths}"
        self.logger.log_event(SF2EventType.EDITOR_ERROR, {
            'message': error_msg,
            'error': 'Editor executable not found',
            'searched_paths': search_paths
        })
        raise SF2EditorNotFoundError(error_msg)

    def launch_editor(self, sf2_path: Optional[str] = None, timeout: int = 30) -> bool:
        """Launch SID Factory II editor

        Args:
            sf2_path: Optional SF2 file to load on launch
            timeout: Timeout in seconds for editor to start

        Returns:
            True if editor launched successfully, False otherwise

        Raises:
            SF2EditorTimeoutError: If editor doesn't start within timeout
        """
        try:
            self.logger.log_event(SF2EventType.EDITOR_LAUNCH, {
                'message': 'Launching SID Factory II editor',
                'editor_path': self.editor_path,
                'sf2_file': sf2_path,
                'timeout_s': timeout
            })

            # Build command - always launch without file argument
            # File loading is done via menu (F10) after window appears
            cmd = [self.editor_path]

            # Launch process with output redirection to temp files
            # Using files instead of PIPE to avoid blocking GUI applications
            import tempfile
            self.stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_editor_stdout.log')
            self.stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_editor_stderr.log')

            start_time = time.time()
            self.process = subprocess.Popen(
                cmd,
                stdout=self.stdout_file,
                stderr=self.stderr_file,
                cwd=str(Path(self.editor_path).parent)
            )
            self.pid = self.process.pid

            self.logger.log_action("Editor process started", {
                'pid': self.pid,
                'command': ' '.join(cmd),
                'stdout_log': self.stdout_file.name,
                'stderr_log': self.stderr_file.name
            })

            # Wait for window to appear
            if WINDOWS_API_AVAILABLE:
                window_found = self._wait_for_window(timeout)
                if not window_found:
                    error_msg = f"Editor window not found within {timeout}s"
                    self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                        'message': error_msg,
                        'timeout_s': timeout,
                        'elapsed_s': time.time() - start_time
                    })
                    raise SF2EditorTimeoutError(error_msg)

                elapsed = time.time() - start_time
                self.logger.log_event(SF2EventType.EDITOR_LOAD_COMPLETE, {
                    'message': 'Editor launched successfully',
                    'elapsed_s': elapsed,
                    'window_handle': self.window_handle,
                    'pid': self.pid
                })

                # If file was provided, load it via menu IMMEDIATELY
                # Skip running check since we just confirmed the window exists
                if sf2_path:
                    self.logger.log_action("Loading file via menu after launch", {
                        'file_path': sf2_path
                    })
                    return self.load_file_via_menu(sf2_path, timeout=timeout, skip_running_check=True)

                return True
            else:
                # Without Windows API, just wait a bit
                time.sleep(3)
                if self.process.poll() is None:
                    self.logger.log_action("Editor launched (no window detection)", {
                        'pid': self.pid
                    })
                    return True
                else:
                    error_msg = "Editor process terminated unexpectedly"
                    self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                        'message': error_msg,
                        'returncode': self.process.returncode
                    })
                    return False

        except FileNotFoundError as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Editor executable not found',
                'error': str(e),
                'path': self.editor_path
            })
            raise SF2EditorNotFoundError(f"Editor not found: {self.editor_path}")
        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Failed to launch editor',
                'error': str(e),
                'exception_type': type(e).__name__
            })
            raise

    def _wait_for_window(self, timeout: int = 30) -> bool:
        """Wait for editor window to appear

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if window found, False otherwise
        """
        if not WINDOWS_API_AVAILABLE:
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Find window by title or class
            def callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "SID Factory" in title or "SF2" in title:
                        _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if win_pid == self.pid:
                            self.window_handle = hwnd
                            return False  # Stop enumeration
                return True

            win32gui.EnumWindows(callback, None)

            if self.window_handle:
                self.logger.log_action("Editor window found", {
                    'window_handle': self.window_handle,
                    'title': win32gui.GetWindowText(self.window_handle),
                    'elapsed_s': time.time() - start_time
                })
                return True

            time.sleep(0.5)

        return False

    def is_editor_running(self) -> bool:
        """Check if editor is currently running

        Returns:
            True if editor is running, False otherwise
        """
        if self.process:
            return self.process.poll() is None

        if self.pid:
            return psutil.pid_exists(self.pid)

        return False

    def get_window_title(self) -> Optional[str]:
        """Get current window title

        Returns:
            Window title string or None if not available
        """
        if not WINDOWS_API_AVAILABLE or not self.window_handle:
            return None

        try:
            return win32gui.GetWindowText(self.window_handle)
        except Exception as e:
            self.logger.log_action("Failed to get window title", {
                'error': str(e)
            })
            return None

    def is_file_loaded(self) -> bool:
        """Check if a file is currently loaded in the editor

        Returns:
            True if file appears to be loaded, False otherwise
        """
        title = self.get_window_title()
        if not title:
            return False

        # Window title typically shows filename when loaded
        # e.g., "SID Factory II - filename.sf2"
        return '.sf2' in title.lower() or 'sid factory' in title.lower()

    def is_playing(self) -> bool:
        """Check if editor is currently playing music

        Returns:
            True if music appears to be playing, False otherwise
        """
        title = self.get_window_title()
        if not title:
            return False

        # Window title may show play indicator
        # Common patterns: "[Playing]", "►", or position indicator
        play_indicators = ['[playing]', '►', 'playing', '▶']
        title_lower = title.lower()

        return any(indicator in title_lower for indicator in play_indicators)

    def get_playback_state(self) -> Dict[str, Any]:
        """Get detailed playback state information

        Returns:
            Dictionary with playback state details
        """
        state = {
            'running': self.is_editor_running(),
            'file_loaded': self.is_file_loaded(),
            'playing': self.is_playing(),
            'window_title': self.get_window_title(),
            'window_handle': self.window_handle,
            'pid': self.pid
        }

        self.logger.log_action("Playback state retrieved", state)
        return state

    def wait_for_load(self, timeout: int = 10) -> bool:
        """Wait for SF2 file to finish loading

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if load completed, False if timeout
        """
        self.logger.log_event(SF2EventType.EDITOR_LOAD_START, {
            'message': 'Waiting for file load to complete',
            'timeout_s': timeout
        })

        start_time = time.time()

        # Wait for file to appear in window title
        while time.time() - start_time < timeout:
            # Check if editor is still running
            if not self.is_editor_running():
                self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                    'message': 'Editor terminated during load',
                    'elapsed_s': time.time() - start_time
                })
                return False

            # Check if file is loaded (appears in window title)
            if self.is_file_loaded():
                elapsed = time.time() - start_time
                self.logger.log_event(SF2EventType.EDITOR_LOAD_COMPLETE, {
                    'message': 'File load completed',
                    'elapsed_s': elapsed,
                    'window_title': self.get_window_title()
                })
                return True

            time.sleep(0.5)

        # Timeout
        self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
            'message': 'File load timeout',
            'elapsed_s': time.time() - start_time
        })
        return False

    def start_playback(self) -> bool:
        """Start playback in editor

        Returns:
            True if playback started, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot start playback - editor not running'
            })
            return False

        self.logger.log_event(SF2EventType.EDITOR_PLAYBACK_START, {
            'message': 'Starting playback in editor'
        })

        if WINDOWS_API_AVAILABLE and self.window_handle:
            try:
                # Send F5 key (common play shortcut)
                win32gui.SetForegroundWindow(self.window_handle)
                time.sleep(0.2)
                # Simulate F5 keypress
                win32api.keybd_event(win32con.VK_F5, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(win32con.VK_F5, 0, win32con.KEYEVENTF_KEYUP, 0)

                self.logger.log_action("Playback command sent", {
                    'method': 'F5 keypress'
                })
                return True
            except Exception as e:
                self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                    'message': 'Failed to send playback command',
                    'error': str(e)
                })
                return False
        else:
            self.logger.log_action("Playback start requested (no API available)")
            return False

    def stop_playback(self) -> bool:
        """Stop playback in editor

        Returns:
            True if playback stopped, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot stop playback - editor not running'
            })
            return False

        self.logger.log_event(SF2EventType.EDITOR_PLAYBACK_STOP, {
            'message': 'Stopping playback in editor'
        })

        if WINDOWS_API_AVAILABLE and self.window_handle:
            try:
                # Send F8 key (common stop shortcut)
                win32gui.SetForegroundWindow(self.window_handle)
                time.sleep(0.2)
                win32api.keybd_event(win32con.VK_F8, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(win32con.VK_F8, 0, win32con.KEYEVENTF_KEYUP, 0)

                self.logger.log_action("Stop command sent", {
                    'method': 'F8 keypress'
                })
                return True
            except Exception as e:
                self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                    'message': 'Failed to send stop command',
                    'error': str(e)
                })
                return False
        else:
            self.logger.log_action("Playback stop requested (no API available)")
            return False

    def load_file_via_menu(self, sf2_path: str, timeout: int = 15, skip_running_check: bool = False) -> bool:
        """Load SF2 file via F10 menu (alternative to command-line loading)

        Args:
            sf2_path: Path to SF2 file to load
            timeout: Maximum time to wait for file load (seconds)
            skip_running_check: Skip initial running check (for immediate use after launch)

        Returns:
            True if file loaded successfully, False otherwise
        """
        self.logger.log_action("load_file_via_menu called", {
            'skip_running_check': skip_running_check,
            'window_handle': self.window_handle,
            'windows_api': WINDOWS_API_AVAILABLE
        })

        # Skip running check if called immediately after launch
        if not skip_running_check and not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot load file - editor not running'
            })
            return False

        if not WINDOWS_API_AVAILABLE:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot load file - Windows API not available',
                'windows_api': WINDOWS_API_AVAILABLE
            })
            return False

        if not self.window_handle:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot load file - No window handle',
                'window_handle': self.window_handle
            })
            return False

        # Convert to absolute Windows path
        abs_path = str(Path(sf2_path).absolute())

        self.logger.log_event(SF2EventType.EDITOR_LOAD_START, {
            'message': 'Loading file via F10 menu',
            'file_path': abs_path
        })

        try:
            # Bring editor to foreground IMMEDIATELY (no delay)
            win32gui.SetForegroundWindow(self.window_handle)
            time.sleep(0.1)  # Reduced from 0.3 to minimize close risk

            # Send F10 to open load dialog
            self.logger.log_action("Sending F10 to open file dialog")
            win32api.keybd_event(win32con.VK_F10, 0, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(win32con.VK_F10, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Wait for dialog to appear
            time.sleep(1.0)

            # Type the file path
            self.logger.log_action("Typing file path", {'path': abs_path})
            for char in abs_path:
                # Get virtual key code for character
                vk = win32api.VkKeyScan(char)
                if vk == -1:
                    continue  # Skip unsupported characters

                key_code = vk & 0xFF
                shift_state = (vk >> 8) & 0xFF

                # Press shift if needed
                if shift_state & 1:
                    win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)

                # Press and release key
                win32api.keybd_event(key_code, 0, 0, 0)
                time.sleep(0.01)
                win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

                # Release shift if needed
                if shift_state & 1:
                    win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)

                time.sleep(0.01)

            # Press Enter to confirm
            time.sleep(0.2)
            self.logger.log_action("Pressing Enter to load file")
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Wait for file to load
            self.logger.log_action("Waiting for file to load", {'timeout_s': timeout})
            start_time = time.time()

            while time.time() - start_time < timeout:
                if not self.is_editor_running():
                    self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                        'message': 'Editor terminated during file load'
                    })
                    return False

                # Check window title for changes
                title = self.get_window_title()
                # File is loaded if title is not empty and editor is still running
                if title and len(title) > len("SID Factory II"):
                    self.logger.log_event(SF2EventType.EDITOR_LOAD_COMPLETE, {
                        'message': 'File loaded successfully',
                        'window_title': title,
                        'elapsed_s': time.time() - start_time
                    })
                    return True

                time.sleep(0.5)

            # Timeout
            self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                'message': 'File load timeout via menu',
                'elapsed_s': time.time() - start_time
            })
            return False

        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Failed to load file via menu',
                'error': str(e),
                'exception_type': type(e).__name__
            })
            return False

    def load_file_via_window_messages(self, sf2_path: str, timeout: int = 15, skip_running_check: bool = False) -> bool:
        """Load SF2 file using direct window messages instead of keyboard events

        This approach sends window messages directly to the window handle, which:
        1. Doesn't require SetForegroundWindow (no focus stealing)
        2. Might be faster and work even if window is closing
        3. More reliable than simulated keyboard input

        Args:
            sf2_path: Path to SF2 file to load
            timeout: Maximum time to wait for file to load (seconds)
            skip_running_check: If True, skip checking if editor is running
                              (useful when called immediately after launch)

        Returns:
            True if file loaded successfully, False otherwise
        """
        self.logger.log_action("load_file_via_window_messages called", {
            'sf2_path': sf2_path,
            'timeout': timeout,
            'skip_running_check': skip_running_check
        })

        # Skip running check if called immediately after launch
        if not skip_running_check and not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot load file - editor not running'
            })
            return False

        if not WINDOWS_API_AVAILABLE:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot load file - Windows API not available',
                'windows_api': WINDOWS_API_AVAILABLE
            })
            return False

        if not self.window_handle:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot load file - No window handle',
                'window_handle': self.window_handle
            })
            return False

        # Convert to absolute Windows path
        abs_path = str(Path(sf2_path).absolute())

        self.logger.log_event(SF2EventType.EDITOR_LOAD_START, {
            'message': 'Loading file via window messages (no keyboard events)',
            'file_path': abs_path
        })

        try:
            # Send F10 directly to window (no SetForegroundWindow needed)
            self.logger.log_action("Sending WM_KEYDOWN F10 to window")
            win32gui.SendMessage(self.window_handle, win32con.WM_KEYDOWN, win32con.VK_F10, 0)
            time.sleep(0.02)
            win32gui.SendMessage(self.window_handle, win32con.WM_KEYUP, win32con.VK_F10, 0)

            # Wait for dialog to appear
            time.sleep(0.8)

            # Try to find the file dialog window
            dialog_candidates = []
            def find_dialog(hwnd, param):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)

                        # Log ALL visible windows for debugging
                        if title:  # Only if window has a title
                            self.logger.log_action("Enumerating visible window", {
                                'handle': hwnd,
                                'title': title,
                                'class': class_name
                            })

                        # Look for common file dialog patterns
                        if any(pattern in title.lower() for pattern in ['open', 'load', 'file']):
                            # Check if it's owned by the editor
                            owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
                            dialog_candidates.append({
                                'handle': hwnd,
                                'title': title,
                                'class': class_name,
                                'owner': owner
                            })
                            self.logger.log_action("Found potential dialog window", {
                                'handle': hwnd,
                                'title': title,
                                'class': class_name,
                                'owner': owner,
                                'is_owned_by_editor': owner == self.window_handle
                            })
                except Exception as e:
                    pass  # Ignore errors enumerating individual windows
                return True

            win32gui.EnumWindows(find_dialog, None)

            # Choose best dialog candidate
            dialog_handle = None
            if dialog_candidates:
                # Prefer dialogs owned by the editor
                owned_dialogs = [d for d in dialog_candidates if d['owner'] == self.window_handle]
                if owned_dialogs:
                    dialog_handle = owned_dialogs[0]['handle']
                    self.logger.log_action("Selected dialog owned by editor", owned_dialogs[0])
                else:
                    dialog_handle = dialog_candidates[0]['handle']
                    self.logger.log_action("Selected first dialog candidate", dialog_candidates[0])

            # Try to find edit control within dialog if dialog found
            edit_control = None
            if dialog_handle:
                def find_edit(hwnd, param):
                    nonlocal edit_control
                    try:
                        class_name = win32gui.GetClassName(hwnd)
                        # Look for edit control class names
                        if 'edit' in class_name.lower():
                            edit_control = hwnd
                            self.logger.log_action("Found edit control in dialog", {
                                'handle': hwnd,
                                'class': class_name
                            })
                            return False  # Stop enumeration
                    except:
                        pass
                    return True

                try:
                    win32gui.EnumChildWindows(dialog_handle, find_edit, None)
                except:
                    pass  # Dialog might not have child windows

            # Determine target for typing
            target_handle = edit_control if edit_control else (dialog_handle if dialog_handle else self.window_handle)

            self.logger.log_action("Typing file path via WM_CHAR", {
                'path': abs_path,
                'target_handle': target_handle,
                'using_dialog': dialog_handle is not None,
                'using_edit_control': edit_control is not None,
                'dialog_candidates_found': len(dialog_candidates)
            })

            # Type the file path using WM_CHAR messages
            for char in abs_path:
                char_code = ord(char)
                # Send WM_CHAR message directly
                win32gui.SendMessage(target_handle, win32con.WM_CHAR, char_code, 0)
                time.sleep(0.005)  # Very short delay between characters

            # Press Enter to confirm (via window message)
            time.sleep(0.1)
            self.logger.log_action("Sending WM_KEYDOWN Enter to confirm")
            win32gui.SendMessage(target_handle, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.02)
            win32gui.SendMessage(target_handle, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

            # Wait for file to load
            self.logger.log_action("Waiting for file to load", {'timeout_s': timeout})
            start_time = time.time()

            while time.time() - start_time < timeout:
                if not self.is_editor_running():
                    self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                        'message': 'Editor terminated during file load'
                    })
                    return False

                # Check window title for changes
                title = self.get_window_title()
                # File is loaded if title is not empty and editor is still running
                if title and len(title) > len("SID Factory II"):
                    self.logger.log_event(SF2EventType.EDITOR_LOAD_COMPLETE, {
                        'message': 'File loaded successfully via window messages',
                        'window_title': title,
                        'elapsed_s': time.time() - start_time
                    })
                    return True

                time.sleep(0.5)

            # Timeout
            self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                'message': 'File load timeout via window messages',
                'elapsed_s': time.time() - start_time
            })
            return False

        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Failed to load file via window messages',
                'error': str(e),
                'exception_type': type(e).__name__
            })
            import traceback
            self.logger.log_action("Exception traceback", {
                'traceback': traceback.format_exc()
            })
            return False

    def set_position(self, position: int) -> bool:
        """Seek to specific position in playback (Phase 4)

        Args:
            position: Position in seconds or pattern number

        Returns:
            True if position set successfully, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot set position - editor not running'
            })
            return False

        self.logger.log_action("Setting playback position", {
            'position': position,
            'note': 'Position seeking not yet implemented - requires UI automation'
        })

        # TODO: Implement position seeking via menu or UI automation
        # This would require:
        # 1. Click on position slider/field
        # 2. Enter position value
        # 3. Confirm

        return False

    def set_volume(self, volume: int) -> bool:
        """Set playback volume (Phase 4)

        Args:
            volume: Volume level (0-100)

        Returns:
            True if volume set successfully, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot set volume - editor not running'
            })
            return False

        volume = max(0, min(100, volume))  # Clamp to 0-100

        self.logger.log_action("Setting playback volume", {
            'volume': volume,
            'note': 'Volume control not yet implemented - requires UI automation'
        })

        # TODO: Implement volume control via menu or UI automation
        # This would require:
        # 1. Open settings/volume menu
        # 2. Adjust volume slider
        # 3. Confirm

        return False

    def toggle_loop(self, enable: bool) -> bool:
        """Toggle loop playback (Phase 4)

        Args:
            enable: True to enable loop, False to disable

        Returns:
            True if loop toggled successfully, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot toggle loop - editor not running'
            })
            return False

        self.logger.log_action("Toggling loop playback", {
            'enable': enable,
            'note': 'Loop control not yet implemented - requires UI automation'
        })

        # TODO: Implement loop toggle via menu or keyboard shortcut
        # Common patterns:
        # - Menu: View -> Loop Playback
        # - Keyboard: Ctrl+L or similar

        return False

    def pack_to_sid(self, output_path: str, timeout: int = 30) -> bool:
        """Pack SF2 file to SID using editor

        Args:
            output_path: Path for output SID file
            timeout: Maximum time to wait for packing

        Returns:
            True if packing successful, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Cannot pack - editor not running'
            })
            return False

        self.logger.log_event(SF2EventType.EDITOR_PACK_START, {
            'message': 'Starting SF2 to SID packing',
            'output_path': output_path,
            'timeout_s': timeout
        })

        # This would typically:
        # 1. Open File menu
        # 2. Select "Export to SID" or similar
        # 3. Enter filename
        # 4. Wait for completion

        # For now, just log that this is not yet fully implemented
        self.logger.log_event(SF2EventType.EDITOR_PACK_ERROR, {
            'message': 'Editor packing not yet fully implemented',
            'note': 'Use Python sf2_to_sid.py as alternative'
        })

        return False

    def get_editor_output(self) -> Dict[str, str]:
        """Get current editor stdout/stderr output (public method)

        Returns:
            Dictionary with stdout and stderr content
        """
        return self._capture_editor_output()

    def _capture_editor_output(self) -> Dict[str, str]:
        """Capture and log editor stdout/stderr output (internal)

        Returns:
            Dictionary with stdout and stderr content
        """
        output = {'stdout': '', 'stderr': ''}

        try:
            if self.stdout_file:
                # Flush and seek to beginning
                self.stdout_file.flush()
                self.stdout_file.seek(0)
                output['stdout'] = self.stdout_file.read()

                if output['stdout']:
                    self.logger.log_action("Editor stdout captured", {
                        'lines': len(output['stdout'].splitlines()),
                        'bytes': len(output['stdout'])
                    })
                    # Log first few lines for debugging
                    lines = output['stdout'].splitlines()
                    if lines:
                        self.logger.log_action("Editor stdout preview", {
                            'preview': lines[:10]  # First 10 lines
                        })
        except Exception as e:
            self.logger.log_action("Failed to capture stdout", {'error': str(e)})

        try:
            if self.stderr_file:
                # Flush and seek to beginning
                self.stderr_file.flush()
                self.stderr_file.seek(0)
                output['stderr'] = self.stderr_file.read()

                if output['stderr']:
                    self.logger.log_action("Editor stderr captured", {
                        'lines': len(output['stderr'].splitlines()),
                        'bytes': len(output['stderr'])
                    })
                    # Log first few lines for debugging
                    lines = output['stderr'].splitlines()
                    if lines:
                        self.logger.log_action("Editor stderr preview", {
                            'preview': lines[:10]  # First 10 lines
                        })
        except Exception as e:
            self.logger.log_action("Failed to capture stderr", {'error': str(e)})

        return output

    def close_editor(self, force: bool = False, timeout: int = 10) -> bool:
        """Close SID Factory II editor

        Args:
            force: Force close without saving
            timeout: Maximum time to wait for graceful close

        Returns:
            True if editor closed, False otherwise
        """
        if not self.is_editor_running():
            self.logger.log_action("Editor already closed")
            return True

        self.logger.log_event(SF2EventType.EDITOR_EXIT, {
            'message': 'Closing editor',
            'force': force,
            'timeout_s': timeout
        })

        try:
            if force:
                # Force kill
                if self.process:
                    self.process.kill()
                elif self.pid:
                    proc = psutil.Process(self.pid)
                    proc.kill()

                self.logger.log_action("Editor force closed", {
                    'method': 'kill'
                })
            else:
                # Graceful close
                if WINDOWS_API_AVAILABLE and self.window_handle:
                    # Send WM_CLOSE message
                    win32gui.PostMessage(self.window_handle, win32con.WM_CLOSE, 0, 0)

                    # Wait for close
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        if not self.is_editor_running():
                            self.logger.log_action("Editor closed gracefully", {
                                'elapsed_s': time.time() - start_time
                            })
                            return True
                        time.sleep(0.5)

                    # Timeout - force close
                    self.logger.log_action("Graceful close timeout - forcing", {
                        'timeout_s': timeout
                    })
                    if self.process:
                        self.process.kill()
                else:
                    # Without Windows API, just terminate
                    if self.process:
                        self.process.terminate()
                        self.process.wait(timeout)

            # Capture editor output before cleanup
            self._capture_editor_output()

            # Clean up temp files
            import os
            try:
                if self.stdout_file:
                    self.stdout_file.close()
                    if os.path.exists(self.stdout_file.name):
                        os.unlink(self.stdout_file.name)
                if self.stderr_file:
                    self.stderr_file.close()
                    if os.path.exists(self.stderr_file.name):
                        os.unlink(self.stderr_file.name)
            except Exception as e:
                self.logger.log_action("Failed to clean up temp files", {'error': str(e)})

            # Clean up
            self.process = None
            self.window_handle = None
            self.pid = None
            self.stdout_file = None
            self.stderr_file = None

            return True

        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'Failed to close editor',
                'error': str(e),
                'exception_type': type(e).__name__
            })
            return False

    def get_editor_info(self) -> Dict[str, Any]:
        """Get current editor state information

        Returns:
            Dictionary with editor state info
        """
        info = {
            'running': self.is_editor_running(),
            'pid': self.pid,
            'window_handle': self.window_handle,
            'editor_path': self.editor_path,
            'windows_api_available': WINDOWS_API_AVAILABLE
        }

        if WINDOWS_API_AVAILABLE and self.window_handle:
            try:
                info['window_title'] = win32gui.GetWindowText(self.window_handle)
                info['window_visible'] = win32gui.IsWindowVisible(self.window_handle)
            except Exception:
                pass

        return info

    # ========================================================================
    # AutoIt Hybrid Automation
    # ========================================================================

    def launch_editor_with_file(self, sf2_path: str, timeout: int = 60,
                                mode: Optional[str] = None,
                                use_autoit: Optional[bool] = None) -> bool:
        """Launch editor and load file (PyAutoGUI, AutoIt, or Manual mode)

        Args:
            sf2_path: Path to SF2 file to load
            timeout: Maximum time to wait for file load (seconds)
            mode: Automation mode: 'pyautogui', 'autoit', or 'manual'
                 If None, uses default mode from config (priority: PyAutoGUI > AutoIt > Manual)
            use_autoit: DEPRECATED - Use 'mode' parameter instead
                       If True, uses AutoIt. If False, uses manual mode.

        Returns:
            True if file loaded successfully, False otherwise

        Example:
            # Auto-detect mode (uses PyAutoGUI if available, falls back to AutoIt, then Manual)
            automation.launch_editor_with_file("file.sf2")

            # Force PyAutoGUI mode
            automation.launch_editor_with_file("file.sf2", mode='pyautogui')

            # Force AutoIt mode
            automation.launch_editor_with_file("file.sf2", mode='autoit')

            # Force manual mode
            automation.launch_editor_with_file("file.sf2", mode='manual')
        """

        # Handle deprecated use_autoit parameter
        if use_autoit is not None and mode is None:
            mode = 'autoit' if use_autoit else 'manual'

        # Determine mode (priority: explicit mode > default mode)
        if mode is None:
            mode = self.default_automation_mode

        # Normalize mode
        mode = mode.lower()

        self.logger.log_action(f"Launching editor with mode: {mode}", {
            'file_path': str(sf2_path),
            'requested_mode': mode,
            'default_mode': self.default_automation_mode,
            'pyautogui_enabled': self.pyautogui_enabled,
            'autoit_enabled': self.autoit_enabled
        })

        # Launch with selected mode
        if mode == 'pyautogui':
            if not self.pyautogui_enabled:
                self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                    'message': 'PyAutoGUI mode requested but not available',
                    'fallback': 'autoit or manual mode'
                })
                # Fallback to AutoIt or manual
                if self.autoit_enabled:
                    return self._launch_with_autoit(sf2_path, timeout)
                else:
                    return self._launch_manual_workflow(sf2_path)

            return self._launch_with_pyautogui(sf2_path)

        elif mode == 'autoit':
            if not self.autoit_enabled:
                self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                    'message': 'AutoIt mode requested but sf2_loader.exe not found',
                    'script_path': str(self.autoit_script),
                    'fallback': 'manual mode'
                })
                return self._launch_manual_workflow(sf2_path)

            return self._launch_with_autoit(sf2_path, timeout)

        elif mode == 'manual':
            return self._launch_manual_workflow(sf2_path)

        else:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': f'Unknown automation mode: {mode}',
                'fallback': 'default mode'
            })
            # Use default mode
            return self.launch_editor_with_file(sf2_path, timeout, mode=self.default_automation_mode)

    def _launch_with_autoit(self, sf2_path: str, timeout: int) -> bool:
        """Launch editor with AutoIt automated file loading

        Uses compiled AutoIt script (sf2_loader.exe) to:
        1. Launch editor
        2. Keep it alive with periodic null messages
        3. Load file via F10 menu
        4. Verify file loaded
        5. Exit (editor stays open)

        Args:
            sf2_path: Path to SF2 file
            timeout: Maximum time to wait for completion

        Returns:
            True if file loaded successfully, False otherwise
        """
        import tempfile

        sf2_path = Path(sf2_path).absolute()

        if not sf2_path.exists():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'SF2 file not found',
                'path': str(sf2_path)
            })
            return False

        # Create temp status file for AutoIt communication
        status_file = tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix='_autoit_status.txt'
        )
        status_path = status_file.name
        status_file.close()

        self.logger.log_event(SF2EventType.EDITOR_LAUNCH, {
            'message': 'Launching editor with AutoIt',
            'file_path': str(sf2_path),
            'status_file': status_path,
            'autoit_script': str(self.autoit_script)
        })

        try:
            # Build command
            cmd = [
                str(self.autoit_script),
                str(self.editor_path),
                str(sf2_path),
                status_path
            ]

            # Execute AutoIt script
            self.logger.log_action("Executing AutoIt script", {
                'command': ' '.join(cmd)
            })

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor status file
            start_time = time.time()
            last_status = None

            while time.time() - start_time < timeout:
                # Read status
                try:
                    with open(status_path, 'r') as f:
                        status = f.read().strip()

                    if status != last_status:
                        self.logger.log_action("AutoIt status update", {
                            'status': status
                        })
                        last_status = status

                    # Check for completion
                    if status.startswith("SUCCESS"):
                        # Extract window title
                        window_title = status.split(":", 1)[1] if ":" in status else ""

                        self.logger.log_event(SF2EventType.EDITOR_LOAD_COMPLETE, {
                            'message': 'File loaded successfully via AutoIt',
                            'window_title': window_title,
                            'elapsed_s': time.time() - start_time
                        })

                        # Attach to running editor
                        time.sleep(0.5)  # Give editor time to stabilize
                        if self.attach_to_running_editor():
                            # Clean up status file
                            try:
                                Path(status_path).unlink()
                            except:
                                pass
                            return True
                        else:
                            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                                'message': 'AutoIt succeeded but could not attach to editor'
                            })
                            return False

                    elif status.startswith("ERROR"):
                        self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                            'message': 'AutoIt reported error',
                            'error': status
                        })
                        break

                    elif status.startswith("WARNING"):
                        # Continue - file may have loaded despite warning
                        self.logger.log_action("AutoIt warning", {
                            'warning': status
                        })

                except FileNotFoundError:
                    # Status file not created yet
                    pass

                # Check if process finished
                if process.poll() is not None:
                    # Process ended
                    stdout, stderr = process.communicate()

                    if process.returncode != 0:
                        self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                            'message': 'AutoIt script failed',
                            'return_code': process.returncode,
                            'stdout': stdout[:500] if stdout else '',
                            'stderr': stderr[:500] if stderr else ''
                        })
                        break
                    else:
                        # Process exited successfully
                        # Try to attach one more time
                        time.sleep(1)
                        if self.attach_to_running_editor():
                            try:
                                Path(status_path).unlink()
                            except:
                                pass
                            return True
                        break

                time.sleep(0.5)

            # Timeout or error
            self.logger.log_event(SF2EventType.EDITOR_LOAD_ERROR, {
                'message': 'AutoIt file loading timeout or error',
                'elapsed_s': time.time() - start_time,
                'last_status': last_status
            })

            # Kill AutoIt process if still running
            if process.poll() is None:
                process.kill()

            return False

        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'AutoIt execution failed',
                'error': str(e),
                'exception_type': type(e).__name__
            })
            import traceback
            self.logger.log_action("Exception traceback", {
                'traceback': traceback.format_exc()
            })
            return False

        finally:
            # Clean up status file
            try:
                if Path(status_path).exists():
                    Path(status_path).unlink()
            except:
                pass

    def _launch_with_pyautogui(self, sf2_path: str) -> bool:
        """Launch editor with PyAutoGUI automated file loading

        Uses PyAutoGUI Python library to:
        1. Launch editor with --skip-intro CLI flag
        2. Wait for window to appear
        3. Verify file loaded
        4. Store window handle and process for further automation

        Args:
            sf2_path: Path to SF2 file

        Returns:
            True if file loaded successfully, False otherwise
        """
        sf2_path = Path(sf2_path).absolute()

        if not sf2_path.exists():
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'SF2 file not found',
                'path': str(sf2_path)
            })
            return False

        if not self.pyautogui_enabled:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'PyAutoGUI mode not enabled',
                'fallback': 'manual mode'
            })
            return self._launch_manual_workflow(sf2_path)

        self.logger.log_event(SF2EventType.EDITOR_LAUNCH, {
            'message': 'Launching editor with PyAutoGUI',
            'file_path': str(sf2_path),
            'skip_intro': self.config.pyautogui_skip_intro,
            'window_timeout': self.config.pyautogui_window_timeout
        })

        try:
            # Launch with PyAutoGUI automation
            success = self.pyautogui_automation.launch_with_file(
                str(sf2_path),
                skip_intro=self.config.pyautogui_skip_intro,
                timeout=self.config.pyautogui_window_timeout
            )

            if success:
                # Store process and window information
                self.process = self.pyautogui_automation.process
                if self.process:
                    self.pid = self.process.pid

                # Update window handle if using Windows API
                if WINDOWS_API_AVAILABLE and self.pyautogui_automation.window:
                    try:
                        # Try to get window handle from pygetwindow
                        window_title = self.pyautogui_automation.window.title
                        self.window_handle = win32gui.FindWindow(None, window_title)
                    except:
                        pass

                self.logger.log_event(SF2EventType.FILE_LOAD_COMPLETE, {
                    'file_path': str(sf2_path),
                    'pid': self.pid,
                    'window_handle': self.window_handle,
                    'automation_mode': 'pyautogui'
                })

                return True
            else:
                self.logger.log_event(SF2EventType.FILE_LOAD_ERROR, {
                    'file_path': str(sf2_path),
                    'automation_mode': 'pyautogui'
                })
                return False

        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': 'PyAutoGUI automation failed',
                'error': str(e),
                'fallback': 'manual mode'
            })
            return self._launch_manual_workflow(sf2_path)

    def _launch_manual_workflow(self, sf2_path: str) -> bool:
        """Launch with manual file loading (existing workflow)

        Args:
            sf2_path: Path to SF2 file

        Returns:
            True if file loaded successfully, False otherwise
        """

        self.logger.log_event(SF2EventType.EDITOR_LAUNCH, {
            'message': 'Using manual workflow',
            'file_path': sf2_path
        })

        print("=" * 70)
        print("Manual File Loading Workflow")
        print("=" * 70)
        print()
        print(f"File to load: {sf2_path}")
        print()
        print("STEPS:")
        print("1. Launch SID Factory II (double-click SIDFactoryII.exe)")
        print(f"2. Load file: {sf2_path}")
        print("   - Press F10 or use File → Open")
        print()
        input("Press Enter when file is loaded...")
        print()

        # Attach to running editor
        if self.attach_to_running_editor():
            if self.is_file_loaded():
                print("✅ File loaded successfully!")
                return True
            else:
                print("⚠️  Editor attached but no file loaded")
                return False
        else:
            print("❌ Could not attach to editor")
            return False


# Convenience functions
def launch_editor_and_load(sf2_path: str, editor_path: Optional[str] = None) -> SF2EditorAutomation:
    """Launch editor and load SF2 file

    Args:
        sf2_path: Path to SF2 file
        editor_path: Optional path to editor executable

    Returns:
        SF2EditorAutomation instance

    Raises:
        SF2EditorAutomationError: If launch or load fails
    """
    automation = SF2EditorAutomation(editor_path)

    if not automation.launch_editor(sf2_path):
        raise SF2EditorAutomationError("Failed to launch editor")

    if not automation.wait_for_load():
        raise SF2EditorAutomationError("Failed to load SF2 file")

    return automation


def validate_sf2_with_editor(
    sf2_path: str,
    play_duration: int = 5,
    editor_path: Optional[str] = None
) -> Tuple[bool, str]:
    """Validate SF2 file by loading and playing in editor

    Args:
        sf2_path: Path to SF2 file
        play_duration: How long to play in seconds
        editor_path: Optional path to editor executable

    Returns:
        Tuple of (success, message)
    """
    logger = get_sf2_logger()
    automation = None

    try:
        logger.log_action("Starting SF2 validation with editor", {
            'sf2_path': sf2_path,
            'play_duration': play_duration
        })

        # Launch and load
        automation = launch_editor_and_load(sf2_path, editor_path)

        # Start playback
        if not automation.start_playback():
            return False, "Failed to start playback"

        # Wait
        time.sleep(play_duration)

        # Stop playback
        automation.stop_playback()

        logger.log_action("SF2 validation successful", {
            'sf2_path': sf2_path,
            'duration_s': play_duration
        })

        return True, "SF2 file validated successfully"

    except Exception as e:
        logger.log_event(SF2EventType.EDITOR_ERROR, {
            'message': 'SF2 validation failed',
            'error': str(e),
            'sf2_path': sf2_path
        })
        return False, f"Validation failed: {e}"

    finally:
        # Clean up
        if automation:
            automation.close_editor(force=True)
