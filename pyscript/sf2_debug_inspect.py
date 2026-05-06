"""Spawn SIDFactoryII under DEBUG_PROCESS, drive it via SendInput to load a
test SF2, catch the access violation, and read register state + memory.

Goal: confirm whether at the crash at RVA 0x7EF42 the byte at [r14+0x2e]
is really 0xFF (matching what we wrote to disk) or something else.

Design: minimal custom debugger using Win32 DebugActiveProcess /
WaitForDebugEvent. No admin required. Reads CONTEXT for the faulting
thread when the AV fires. Then dumps r14, [r14] (whole TableDefinition),
and m_TableColorRules.size from DriverInfo.

Usage: py -3 pyscript/sf2_debug_inspect.py <file.sf2>
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path
import shutil
import threading

import win32api
import win32con
import win32gui
import win32process
import pyautogui

EDITOR = str(Path('bin/SIDFactoryII.exe').absolute())

# Win32 constants
DEBUG_PROCESS = 0x00000001
DEBUG_ONLY_THIS_PROCESS = 0x00000002
EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
EXCEPTION_ACCESS_VIOLATION = 0xC0000005
EXCEPTION_BREAKPOINT = 0x80000003
CONTEXT_AMD64 = 0x00100000
CONTEXT_CONTROL = (CONTEXT_AMD64 | 0x1)
CONTEXT_INTEGER = (CONTEXT_AMD64 | 0x2)
CONTEXT_FULL = (CONTEXT_AMD64 | 0x1 | 0x2 | 0x4 | 0x8)
THREAD_GET_CONTEXT = 0x0008
THREAD_SUSPEND_RESUME = 0x0002

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

class M128A(ctypes.Structure):
    _fields_ = [('Low', ctypes.c_uint64), ('High', ctypes.c_int64)]

class XMM_SAVE_AREA32(ctypes.Structure):
    _fields_ = [('_pad', ctypes.c_byte * 512)]

class CONTEXT64(ctypes.Structure):
    _fields_ = [
        ('P1Home', ctypes.c_uint64), ('P2Home', ctypes.c_uint64),
        ('P3Home', ctypes.c_uint64), ('P4Home', ctypes.c_uint64),
        ('P5Home', ctypes.c_uint64), ('P6Home', ctypes.c_uint64),
        ('ContextFlags', wt.DWORD), ('MxCsr', wt.DWORD),
        ('SegCs', wt.WORD), ('SegDs', wt.WORD),
        ('SegEs', wt.WORD), ('SegFs', wt.WORD),
        ('SegGs', wt.WORD), ('SegSs', wt.WORD),
        ('EFlags', wt.DWORD),
        ('Dr0', ctypes.c_uint64), ('Dr1', ctypes.c_uint64),
        ('Dr2', ctypes.c_uint64), ('Dr3', ctypes.c_uint64),
        ('Dr6', ctypes.c_uint64), ('Dr7', ctypes.c_uint64),
        ('Rax', ctypes.c_uint64), ('Rcx', ctypes.c_uint64),
        ('Rdx', ctypes.c_uint64), ('Rbx', ctypes.c_uint64),
        ('Rsp', ctypes.c_uint64), ('Rbp', ctypes.c_uint64),
        ('Rsi', ctypes.c_uint64), ('Rdi', ctypes.c_uint64),
        ('R8',  ctypes.c_uint64), ('R9',  ctypes.c_uint64),
        ('R10', ctypes.c_uint64), ('R11', ctypes.c_uint64),
        ('R12', ctypes.c_uint64), ('R13', ctypes.c_uint64),
        ('R14', ctypes.c_uint64), ('R15', ctypes.c_uint64),
        ('Rip', ctypes.c_uint64),
        ('FltSave', XMM_SAVE_AREA32),
        ('VectorRegister', M128A * 26),
        ('VectorControl', ctypes.c_uint64),
        ('DebugControl', ctypes.c_uint64),
        ('LastBranchToRip', ctypes.c_uint64),
        ('LastBranchFromRip', ctypes.c_uint64),
        ('LastExceptionToRip', ctypes.c_uint64),
        ('LastExceptionFromRip', ctypes.c_uint64),
    ]
    _pack_ = 16

class EXCEPTION_RECORD(ctypes.Structure): pass
EXCEPTION_RECORD._fields_ = [
    ('ExceptionCode', wt.DWORD), ('ExceptionFlags', wt.DWORD),
    ('ExceptionRecord', ctypes.POINTER(EXCEPTION_RECORD)),
    ('ExceptionAddress', ctypes.c_void_p),
    ('NumberParameters', wt.DWORD),
    ('ExceptionInformation', ctypes.c_void_p * 15),
]

class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('ExceptionRecord', EXCEPTION_RECORD),
        ('dwFirstChance', wt.DWORD),
    ]

class _DebugInfoUnion(ctypes.Union):
    _fields_ = [
        ('Exception', EXCEPTION_DEBUG_INFO),
        ('Pad', ctypes.c_byte * 256),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ('dwDebugEventCode', wt.DWORD),
        ('dwProcessId', wt.DWORD),
        ('dwThreadId', wt.DWORD),
        ('u', _DebugInfoUnion),
    ]


class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wt.DWORD), ('lpReserved', wt.LPWSTR),
        ('lpDesktop', wt.LPWSTR), ('lpTitle', wt.LPWSTR),
        ('dwX', wt.DWORD), ('dwY', wt.DWORD),
        ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
        ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD),
        ('dwFillAttribute', wt.DWORD), ('dwFlags', wt.DWORD),
        ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD),
        ('lpReserved2', ctypes.c_void_p), ('hStdInput', wt.HANDLE),
        ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wt.HANDLE), ('hThread', wt.HANDLE),
        ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD),
    ]


k32 = ctypes.windll.kernel32
k32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT), wt.DWORD]
k32.WaitForDebugEvent.restype = wt.BOOL
k32.ContinueDebugEvent.argtypes = [wt.DWORD, wt.DWORD, wt.DWORD]
k32.ContinueDebugEvent.restype = wt.BOOL
k32.GetThreadContext.argtypes = [wt.HANDLE, ctypes.POINTER(CONTEXT64)]
k32.GetThreadContext.restype = wt.BOOL
k32.OpenThread.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenThread.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [
    wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.CreateProcessW.argtypes = [
    wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
    ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype = wt.BOOL


def read_mem(hproc, addr, size):
    buf = (ctypes.c_ubyte * size)()
    n = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    if not ok:
        return None
    return bytes(buf[:n.value])


def make_input(vk, key_up=False):
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD),
                    ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                    ('dwExtraInfo', ctypes.POINTER(wt.ULONG))]
    class INPUTU(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('pad', ctypes.c_ubyte * 32)]
    class INPUT(ctypes.Structure):
        _fields_ = [('type', wt.DWORD), ('u', INPUTU)]
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = 0
    inp.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    inp.u.ki.dwFlags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    inp.u.ki.dwExtraInfo = ctypes.pointer(wt.ULONG(0))
    return inp


def send_vk(vk, hold_ms=20):
    INPUT_KEYBOARD = 1
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD),
                    ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                    ('dwExtraInfo', ctypes.POINTER(wt.ULONG))]
    class INPUTU(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('pad', ctypes.c_ubyte * 32)]
    class INPUT(ctypes.Structure):
        _fields_ = [('type', wt.DWORD), ('u', INPUTU)]
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    down = INPUT(); down.type = INPUT_KEYBOARD
    down.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    down.u.ki.dwFlags = KEYEVENTF_SCANCODE
    down.u.ki.dwExtraInfo = ctypes.pointer(wt.ULONG(0))
    up = INPUT(); up.type = INPUT_KEYBOARD
    up.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    up.u.ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    up.u.ki.dwExtraInfo = ctypes.pointer(wt.ULONG(0))
    ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    time.sleep(hold_ms/1000.0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))


def type_string(s):
    INPUT_KEYBOARD = 1
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD),
                    ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                    ('dwExtraInfo', ctypes.POINTER(wt.ULONG))]
    class INPUTU(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('pad', ctypes.c_ubyte * 32)]
    class INPUT(ctypes.Structure):
        _fields_ = [('type', wt.DWORD), ('u', INPUTU)]
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    for ch in s:
        vk = win32api.VkKeyScan(ch)
        if vk == -1: continue
        key = vk & 0xFF
        shift = bool((vk >> 8) & 1)
        events = []
        if shift:
            e = INPUT(); e.type = INPUT_KEYBOARD
            e.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(win32con.VK_SHIFT, 0)
            e.u.ki.dwFlags = KEYEVENTF_SCANCODE
            e.u.ki.dwExtraInfo = ctypes.pointer(wt.ULONG(0))
            events.append(e)
        for up in (False, True):
            e = INPUT(); e.type = INPUT_KEYBOARD
            e.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(key, 0)
            e.u.ki.dwFlags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
            e.u.ki.dwExtraInfo = ctypes.pointer(wt.ULONG(0))
            events.append(e)
        if shift:
            e = INPUT(); e.type = INPUT_KEYBOARD
            e.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(win32con.VK_SHIFT, 0)
            e.u.ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
            e.u.ki.dwExtraInfo = ctypes.pointer(wt.ULONG(0))
            events.append(e)
        for ev in events:
            ctypes.windll.user32.SendInput(1, ctypes.byref(ev), ctypes.sizeof(INPUT))
            time.sleep(0.008)
        time.sleep(0.025)


def drive_load(staged_name, delay=2.0):
    """Sleeps for delay, then types F10 + name + Enter + Y + Enter to load."""
    time.sleep(delay)
    # Find SF2II window and focus it
    import psutil
    pid = None
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and 'SIDFactory' in p.info['name']:
            pid = p.info['pid']
            break
    if pid is None:
        print('  drive_load: SF2II not found')
        return
    # Find window
    import win32gui, win32process
    hwnd = None
    deadline = time.time() + 10
    while time.time() < deadline:
        hits = []
        def cb(h, _):
            try:
                _, wpid = win32process.GetWindowThreadProcessId(h)
                if wpid == pid and win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h):
                    hits.append(h)
            except: pass
        win32gui.EnumWindows(cb, None)
        if hits:
            hwnd = hits[0]; break
        time.sleep(0.2)
    if not hwnd:
        print('  drive_load: no window'); return
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    # click to ensure focus
    rect = win32gui.GetWindowRect(hwnd)
    pyautogui.click((rect[0]+rect[2])//2, rect[1]+20)
    time.sleep(0.4)
    send_vk(win32con.VK_F10); time.sleep(1.0)
    send_vk(win32con.VK_TAB); time.sleep(0.3)
    type_string(staged_name); time.sleep(0.4)
    send_vk(win32con.VK_RETURN); time.sleep(0.8)
    send_vk(ord('Y')); time.sleep(0.2)
    send_vk(win32con.VK_RETURN)
    print(f'  drive_load: F10-load completed for {staged_name}')


def debug_loop(sf2_path):
    abs_path = str(Path(sf2_path).absolute())
    bin_dir = Path(EDITOR).parent
    test_name = f'__sf2dbg__{int(time.time()*1000)%100000}.sf2'
    staged = bin_dir / test_name
    shutil.copyfile(sf2_path, staged)

    # Spawn under debug
    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(f'"{EDITOR}" --skip-intro')
    ok = k32.CreateProcessW(
        None, cmdline, None, None, False,
        DEBUG_PROCESS, None, str(bin_dir),
        ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print('CreateProcessW failed:', ctypes.GetLastError())
        return
    print(f'Spawned SF2II pid={pi.dwProcessId} (debug mode)')
    hproc = None

    # Drive the F10-load in another thread
    threading.Thread(target=drive_load, args=(test_name,), daemon=True).start()

    try:
        evt = DEBUG_EVENT()
        deadline = time.time() + 30
        while time.time() < deadline:
            if not k32.WaitForDebugEvent(ctypes.byref(evt), 1000):
                continue
            if evt.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
                er = evt.u.Exception.ExceptionRecord
                first = evt.u.Exception.dwFirstChance
                code = er.ExceptionCode
                addr = er.ExceptionAddress
                if code == EXCEPTION_BREAKPOINT or code == 0x4000001F:  # WX86_BREAKPOINT
                    k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_CONTINUE)
                    continue
                print(f'\nEXCEPTION: code={code:#x} addr={addr:#x} firstChance={first}')
                if first and code == EXCEPTION_ACCESS_VIOLATION:
                    # First-chance AV — read context
                    hthread = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_SUSPEND_RESUME,
                                             False, evt.dwThreadId)
                    if not hthread:
                        print('  OpenThread failed:', ctypes.GetLastError())
                    ctx = CONTEXT64()
                    ctx.ContextFlags = CONTEXT_FULL
                    if k32.GetThreadContext(hthread, ctypes.byref(ctx)):
                        print(f'  RIP={ctx.Rip:#x}')
                        print(f'  RAX={ctx.Rax:#x}  RCX={ctx.Rcx:#x}  RDX={ctx.Rdx:#x}')
                        print(f'  R13={ctx.R13:#x}  R14={ctx.R14:#x}  R15={ctx.R15:#x}')
                        # Open process for memory read
                        if hproc is None:
                            from ctypes.wintypes import DWORD
                            PROCESS_VM_READ = 0x0010
                            PROCESS_QUERY_INFORMATION = 0x0400
                            k32.OpenProcess.restype = wt.HANDLE
                            hproc = k32.OpenProcess(
                                PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
                                False, evt.dwProcessId)
                        # If we're at the known crash RIP (image_base + 0x7EF42), inspect
                        # Read a wider TableDefinition at r14
                        if ctx.R14 != 0:
                            td_bytes = read_mem(hproc, ctx.R14, 0x40)
                            if td_bytes:
                                print(f'  bytes @ R14 (TableDefinition): {td_bytes.hex()}')
                                if len(td_bytes) >= 0x37:
                                    print(f'    +0x00 type={td_bytes[0]:#04x}  +0x01 id={td_bytes[1]:#04x}  +0x02 textfield={td_bytes[2]:#04x}')
                                    print(f'    +0x29 prop_insdel={td_bytes[0x29]:#04x}  +0x2a prop_vert={td_bytes[0x2a]:#04x}')
                                    print(f'    +0x2c m_InsertDeleteRuleID={td_bytes[0x2c]:#04x}')
                                    print(f'    +0x2d m_EnterActionRuleID={td_bytes[0x2d]:#04x}')
                                    print(f'    +0x2e m_ColorRuleID={td_bytes[0x2e]:#04x}  ← key field')
                                    print(f'    +0x30 address={td_bytes[0x30]|td_bytes[0x31]<<8:#06x}')
                        # Read m_TableDefinitions from DriverInfo via R13+0x358
                        di_holder = read_mem(hproc, ctx.R13 + 0x358, 8)
                        if di_holder:
                            di_ptr = int.from_bytes(di_holder, 'little')
                            print(f'  *(R13+0x358) = DriverInfo* = {di_ptr:#x}')
                            td_vec = read_mem(hproc, di_ptr + 0x88, 24)
                            if td_vec:
                                begin = int.from_bytes(td_vec[0:8], 'little')
                                end   = int.from_bytes(td_vec[8:16], 'little')
                                print(f'  m_TableDefinitions: begin={begin:#x} end={end:#x}  count={(end-begin)//0x38}')
                                # Dump all m_ColorRuleID values
                                count = (end - begin) // 0x38
                                for i in range(min(count, 12)):
                                    td = read_mem(hproc, begin + i*0x38, 0x38)
                                    if td:
                                        print(f'    [{i}] type={td[0]:#04x} id={td[1]:#04x}  insdel={td[0x2c]:#04x} enter={td[0x2d]:#04x} color={td[0x2e]:#04x}')
                            cr_vec = read_mem(hproc, di_ptr + 0xa0, 24)
                            if cr_vec:
                                begin = int.from_bytes(cr_vec[0:8], 'little')
                                end   = int.from_bytes(cr_vec[8:16], 'little')
                                print(f'  m_TableColorRules: begin={begin:#x} end={end:#x}  count={(end-begin)//24}')

                    # Don't continue — let it crash for real (second-chance) so we exit cleanly
                    k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_EXCEPTION_NOT_HANDLED)
                    print('  (passed exception to second-chance handler — process will exit)')
                    return
                k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_EXCEPTION_NOT_HANDLED)
            elif evt.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
                print('Process exited cleanly without AV — no crash to inspect.')
                return
            else:
                k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_CONTINUE)
        print('Timeout — no AV caught.')
    finally:
        try:
            if staged.exists(): staged.unlink()
        except: pass
        try: k32.TerminateProcess(pi.hProcess, 0)
        except: pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    debug_loop(sys.argv[1])
