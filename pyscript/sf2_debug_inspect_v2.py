"""SF2II custom debugger v2 — adds hardware watchpoints, attach mode,
and dbghelp-backed stack walks to the v1 inspector.

Three modes:
  --watch <addr>    Set a hardware write-watchpoint at the given address
                    (1, 2, 4, or 8 bytes — controlled by --size). When the
                    CPU traps the write, we capture: PC, full register set,
                    a stack walk via dbghelp, and a memory snapshot around
                    the watched address. Then continue the process.

  --attach <pid>    Attach to an already-running SIDFactoryII.exe via
                    DebugActiveProcess instead of spawning under DEBUG_PROCESS.
                    A debugger that ATTACHES has slightly less heap-allocator
                    perturbation than one that spawns the child, since the
                    child started with the normal allocator behaviour and
                    only the post-attach allocations see the debugger's
                    DEBUG_PROCESS flag effects (e.g., Microsoft heap fills).
                    (No silver bullet — heap-attached debuggers can still
                    mask Heisenbugs — but worth a shot.)

  default (no flag) Spawn SF2II under DEBUG_PROCESS and drive F10-load via
                    SendInput, like the v1 inspector. Catches the first AV
                    and dumps registers + memory + stack walk.

Stack walk uses StackWalk64 from dbghelp.dll (already shipped with the
Windows 10 SDK at C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\
on this machine). Symbol resolution loads SIDFactoryII.exe's symbols from
the binary itself; PDB-aware symbols would need the .pdb file present.

Examples:
  # Watch the high byte of a known target. The target address has to come
  # from somewhere — typically dump m_MainTextField under the patched binary
  # then convert that pointer-storage address to an absolute one via
  # ReadProcessMemory before starting this debugger.
  py -3 pyscript/sf2_debug_inspect_v2.py --watch 0x000001fffe004248 bin/_action.sf2

  # Attach to an already-running SF2II
  py -3 pyscript/sf2_debug_inspect_v2.py --attach 12345 bin/_action.sf2

  # Default: spawn-debug + drive F10-load
  py -3 pyscript/sf2_debug_inspect_v2.py bin/_action.sf2
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import shutil
import sys
import threading
import time
from pathlib import Path

import pyautogui
import psutil
import win32api
import win32con
import win32gui
import win32process

# -- shared with v1 ---------------------------------------------------------
EDITOR = str(Path('bin/SIDFactoryII.exe').absolute())

DEBUG_PROCESS                  = 0x00000001
DEBUG_ONLY_THIS_PROCESS        = 0x00000002
EXCEPTION_DEBUG_EVENT          = 1
CREATE_THREAD_DEBUG_EVENT      = 2
CREATE_PROCESS_DEBUG_EVENT     = 3
EXIT_THREAD_DEBUG_EVENT        = 4
EXIT_PROCESS_DEBUG_EVENT       = 5
LOAD_DLL_DEBUG_EVENT           = 6
UNLOAD_DLL_DEBUG_EVENT         = 7
OUTPUT_DEBUG_STRING_EVENT      = 8
DBG_CONTINUE                   = 0x00010002
DBG_EXCEPTION_NOT_HANDLED      = 0x80010001

EXCEPTION_ACCESS_VIOLATION     = 0xC0000005
EXCEPTION_BREAKPOINT           = 0x80000003
EXCEPTION_SINGLE_STEP          = 0x80000004     # ← hardware breakpoint hit
EXCEPTION_GUARD_PAGE           = 0x80000001

CONTEXT_AMD64                  = 0x00100000
CONTEXT_CONTROL                = (CONTEXT_AMD64 | 0x1)
CONTEXT_INTEGER                = (CONTEXT_AMD64 | 0x2)
CONTEXT_SEGMENTS               = (CONTEXT_AMD64 | 0x4)
CONTEXT_FLOATING_POINT         = (CONTEXT_AMD64 | 0x8)
CONTEXT_DEBUG_REGISTERS        = (CONTEXT_AMD64 | 0x10)
CONTEXT_FULL                   = (CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS
                                  | CONTEXT_FLOATING_POINT)
CONTEXT_ALL                    = (CONTEXT_FULL | CONTEXT_DEBUG_REGISTERS)

THREAD_GET_CONTEXT             = 0x0008
THREAD_SET_CONTEXT             = 0x0010
THREAD_SUSPEND_RESUME          = 0x0002
THREAD_QUERY_INFORMATION       = 0x0040

PROCESS_VM_READ                = 0x0010
PROCESS_QUERY_INFORMATION      = 0x0400
PROCESS_VM_WRITE               = 0x0020
PROCESS_VM_OPERATION           = 0x0008

# DR7 layout (per-DBR controls)
#   bit 0   L0 (local enable for DR0)
#   bits 16-17  R/W on DR0:
#       00 = exec, 01 = write, 10 = i/o, 11 = read|write
#   bits 18-19  LEN on DR0:
#       00 = 1B, 01 = 2B, 10 = 8B, 11 = 4B
def make_dr7(slot, rw_mode, length):
    base = 0
    L_bit = 1 << (slot * 2)
    base |= L_bit
    rw_shift = 16 + slot * 4
    base |= (rw_mode & 0x3) << rw_shift
    len_shift = 18 + slot * 4
    base |= (length & 0x3) << len_shift
    return base

DR7_RW_WRITE = 0b01
DR7_RW_RDWR  = 0b11
DR7_RW_EXEC  = 0b00
DR7_LEN_1    = 0b00
DR7_LEN_2    = 0b01
DR7_LEN_8    = 0b10
DR7_LEN_4    = 0b11


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
    ('ExceptionInformation', ctypes.c_uint64 * 15),
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
k32.WaitForDebugEvent.argtypes  = [ctypes.POINTER(DEBUG_EVENT), wt.DWORD]
k32.WaitForDebugEvent.restype   = wt.BOOL
k32.ContinueDebugEvent.argtypes = [wt.DWORD, wt.DWORD, wt.DWORD]
k32.ContinueDebugEvent.restype  = wt.BOOL
k32.GetThreadContext.argtypes   = [wt.HANDLE, ctypes.POINTER(CONTEXT64)]
k32.GetThreadContext.restype    = wt.BOOL
k32.SetThreadContext.argtypes   = [wt.HANDLE, ctypes.POINTER(CONTEXT64)]
k32.SetThreadContext.restype    = wt.BOOL
k32.OpenThread.argtypes         = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenThread.restype          = wt.HANDLE
k32.OpenProcess.argtypes        = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype         = wt.HANDLE
k32.SuspendThread.argtypes      = [wt.HANDLE]
k32.SuspendThread.restype       = wt.DWORD
k32.ResumeThread.argtypes       = [wt.HANDLE]
k32.ResumeThread.restype        = wt.DWORD
k32.ReadProcessMemory.argtypes  = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype   = wt.BOOL
k32.CreateProcessW.argtypes     = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
                                   wt.BOOL, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR,
                                   ctypes.POINTER(STARTUPINFO),
                                   ctypes.POINTER(PROCESS_INFORMATION)]
k32.CreateProcessW.restype      = wt.BOOL
k32.DebugActiveProcess.argtypes = [wt.DWORD]
k32.DebugActiveProcess.restype  = wt.BOOL
k32.DebugSetProcessKillOnExit.argtypes = [wt.BOOL]
k32.DebugSetProcessKillOnExit.restype  = wt.BOOL
k32.CloseHandle.argtypes        = [wt.HANDLE]
k32.CloseHandle.restype         = wt.BOOL
k32.GetLastError.restype        = wt.DWORD
k32.TerminateProcess.argtypes   = [wt.HANDLE, wt.UINT]
k32.TerminateProcess.restype    = wt.BOOL


# -- dbghelp for stack walking ---------------------------------------------
DBGHELP_PATH = (r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64'
                r'\dbghelp.dll')

class STACKFRAME64_ADDRESS(ctypes.Structure):
    _fields_ = [
        ('Offset', ctypes.c_uint64),
        ('Segment', ctypes.c_uint16),
        ('Mode', ctypes.c_uint),  # ADDRESS_MODE enum
    ]

class STACKFRAME64(ctypes.Structure):
    _fields_ = [
        ('AddrPC',     STACKFRAME64_ADDRESS),
        ('AddrReturn', STACKFRAME64_ADDRESS),
        ('AddrFrame',  STACKFRAME64_ADDRESS),
        ('AddrStack',  STACKFRAME64_ADDRESS),
        ('AddrBStore', STACKFRAME64_ADDRESS),
        ('FuncTableEntry', ctypes.c_void_p),
        ('Params', ctypes.c_uint64 * 4),
        ('Far', ctypes.c_int),
        ('Virtual', ctypes.c_int),
        ('Reserved', ctypes.c_uint64 * 3),
        ('KdHelp_Thread', ctypes.c_uint64),
        ('KdHelp_ThCallbackStack', ctypes.c_uint64),
        ('KdHelp_ThCallbackBStore', ctypes.c_uint64),
        ('KdHelp_NextCallback', ctypes.c_uint64),
        ('KdHelp_FramePointer', ctypes.c_uint64),
        ('KdHelp_KiCallUserMode', ctypes.c_uint64),
        ('KdHelp_KeUserCallbackDispatcher', ctypes.c_uint64),
        ('KdHelp_SystemRangeStart', ctypes.c_uint64),
        ('KdHelp_KiUserExceptionDispatcher', ctypes.c_uint64),
        ('KdHelp_StackBase', ctypes.c_uint64),
        ('KdHelp_StackLimit', ctypes.c_uint64),
        ('KdHelp_BuildVersion', ctypes.c_uint),
        ('KdHelp_RetpolineStubFunctionTableSize', ctypes.c_uint),
        ('KdHelp_RetpolineStubFunctionTable', ctypes.c_uint64),
        ('KdHelp_RetpolineStubOffset', ctypes.c_uint),
        ('KdHelp_RetpolineStubSize', ctypes.c_uint),
        ('KdHelp_Reserved0', ctypes.c_uint64 * 2),
    ]

IMAGE_FILE_MACHINE_AMD64 = 0x8664

ADDRESS_MODE_ADDRMODE_FLAT = 3

def load_dbghelp():
    try:
        return ctypes.CDLL(DBGHELP_PATH)
    except OSError:
        # Fall back to system dbghelp (older but available)
        try:
            return ctypes.CDLL('dbghelp.dll')
        except OSError as e:
            print(f'dbghelp.dll not loadable: {e}')
            return None


def stack_walk(hproc, hthread, ctx, max_frames=24):
    """Return a list of (PC, RVA-or-None, module_name) for the call stack."""
    dbghelp = load_dbghelp()
    if dbghelp is None:
        return [(ctx.Rip, None, '?')]
    dbghelp.SymInitialize.argtypes = [wt.HANDLE, wt.LPCSTR, wt.BOOL]
    dbghelp.SymInitialize.restype  = wt.BOOL
    dbghelp.SymCleanup.argtypes    = [wt.HANDLE]
    dbghelp.SymCleanup.restype     = wt.BOOL
    dbghelp.StackWalk64.argtypes = [
        wt.DWORD, wt.HANDLE, wt.HANDLE,
        ctypes.POINTER(STACKFRAME64), ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p,
    ]
    dbghelp.StackWalk64.restype  = wt.BOOL
    dbghelp.SymFunctionTableAccess64.argtypes = [wt.HANDLE, ctypes.c_uint64]
    dbghelp.SymFunctionTableAccess64.restype  = ctypes.c_void_p
    dbghelp.SymGetModuleBase64.argtypes = [wt.HANDLE, ctypes.c_uint64]
    dbghelp.SymGetModuleBase64.restype  = ctypes.c_uint64

    if not dbghelp.SymInitialize(hproc, None, True):
        # invasive=True triggers automatic symbol load for all loaded modules
        pass

    sf = STACKFRAME64()
    sf.AddrPC.Offset    = ctx.Rip
    sf.AddrPC.Mode      = ADDRESS_MODE_ADDRMODE_FLAT
    sf.AddrFrame.Offset = ctx.Rbp
    sf.AddrFrame.Mode   = ADDRESS_MODE_ADDRMODE_FLAT
    sf.AddrStack.Offset = ctx.Rsp
    sf.AddrStack.Mode   = ADDRESS_MODE_ADDRMODE_FLAT

    frames = []
    for _ in range(max_frames):
        ok = dbghelp.StackWalk64(
            IMAGE_FILE_MACHINE_AMD64, hproc, hthread,
            ctypes.byref(sf), ctypes.byref(ctx),
            None,
            dbghelp.SymFunctionTableAccess64,
            dbghelp.SymGetModuleBase64,
            None,
        )
        if not ok or sf.AddrPC.Offset == 0:
            break
        pc = sf.AddrPC.Offset
        modbase = dbghelp.SymGetModuleBase64(hproc, pc)
        rva = pc - modbase if modbase else None
        modname = module_for_addr(hproc, pc)
        frames.append((pc, rva, modname))

    dbghelp.SymCleanup(hproc)
    return frames


# -- module enumeration ----------------------------------------------------
class MODULEINFO(ctypes.Structure):
    _fields_ = [('lpBaseOfDll', ctypes.c_void_p),
                ('SizeOfImage', wt.DWORD),
                ('EntryPoint',  ctypes.c_void_p)]

_psapi = ctypes.windll.psapi
_psapi.EnumProcessModules.argtypes = [wt.HANDLE, ctypes.POINTER(wt.HMODULE),
                                       wt.DWORD, ctypes.POINTER(wt.DWORD)]
_psapi.EnumProcessModules.restype  = wt.BOOL
_psapi.GetModuleBaseNameW.argtypes = [wt.HANDLE, wt.HMODULE, wt.LPWSTR, wt.DWORD]
_psapi.GetModuleBaseNameW.restype  = wt.DWORD
_psapi.GetModuleInformation.argtypes = [wt.HANDLE, wt.HMODULE,
                                         ctypes.POINTER(MODULEINFO), wt.DWORD]
_psapi.GetModuleInformation.restype  = wt.BOOL


def list_modules(hproc):
    arr_size = 1024
    arr = (wt.HMODULE * arr_size)()
    needed = wt.DWORD()
    if not _psapi.EnumProcessModules(hproc, arr, ctypes.sizeof(arr), ctypes.byref(needed)):
        return []
    n = needed.value // ctypes.sizeof(wt.HMODULE)
    out = []
    for i in range(min(n, arr_size)):
        h = arr[i]
        name = (ctypes.c_wchar * 260)()
        _psapi.GetModuleBaseNameW(hproc, h, name, 260)
        info = MODULEINFO()
        _psapi.GetModuleInformation(hproc, h, ctypes.byref(info), ctypes.sizeof(info))
        out.append((info.lpBaseOfDll, info.SizeOfImage, name.value))
    return out


def module_for_addr(hproc, addr):
    for base, size, name in list_modules(hproc):
        b = base or 0
        if b <= addr < b + size:
            return name
    return '?'


def addr_to_rva(hproc, addr):
    for base, size, name in list_modules(hproc):
        b = base or 0
        if b <= addr < b + size:
            return name, addr - b
    return None, None


# -- shared helpers --------------------------------------------------------
def read_mem(hproc, addr, size):
    buf = (ctypes.c_ubyte * size)()
    n = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size, ctypes.byref(n))
    if not ok:
        return None
    return bytes(buf[:n.value])


# -- HW watchpoint installer -----------------------------------------------
def set_hw_write_watchpoint(pid, address, size_bytes=8, slot=0):
    """Install a hardware write-watchpoint on every thread of `pid`.

    DR0..DR3 are the 4 available debug registers (one per slot). DR7
    controls them. We:
      1. Open every thread of the process
      2. Suspend it, GetThreadContext, set Dr<slot> = address, modify Dr7
      3. SetThreadContext, ResumeThread

    Per-thread because Win64 maintains one set of debug registers per
    thread (not per process). NEW threads created after this point will
    have empty DRs and won't trap; if reproducibility allows, set the
    watchpoint AFTER F10-load is in progress so the relevant rendering
    threads are already up.
    """
    if size_bytes == 1:   length = DR7_LEN_1
    elif size_bytes == 2: length = DR7_LEN_2
    elif size_bytes == 4: length = DR7_LEN_4
    elif size_bytes == 8: length = DR7_LEN_8
    else:                 raise ValueError('size must be 1, 2, 4, or 8')
    new_dr7 = make_dr7(slot, DR7_RW_WRITE, length)

    proc = psutil.Process(pid)
    threads = proc.threads()
    print(f'[hw_watch] Installing slot{slot} write @ 0x{address:x} '
          f'(size={size_bytes}) on {len(threads)} threads')
    set_count = 0
    for t in threads:
        ht = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_SET_CONTEXT
                            | THREAD_SUSPEND_RESUME, False, t.id)
        if not ht:
            print(f'    tid={t.id}: OpenThread failed err={k32.GetLastError()}')
            continue
        try:
            k32.SuspendThread(ht)
            ctx = CONTEXT64()
            ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
            if not k32.GetThreadContext(ht, ctypes.byref(ctx)):
                print(f'    tid={t.id}: GetThreadContext failed')
                continue
            # Stash address in chosen DRn
            setattr(ctx, f'Dr{slot}', address)
            ctx.Dr7 = new_dr7
            ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
            if k32.SetThreadContext(ht, ctypes.byref(ctx)):
                set_count += 1
            else:
                print(f'    tid={t.id}: SetThreadContext failed err={k32.GetLastError()}')
        finally:
            k32.ResumeThread(ht)
            k32.CloseHandle(ht)
    print(f'[hw_watch] Set on {set_count}/{len(threads)} threads')
    return set_count


# -- INPUT helpers (copy of v1's) ------------------------------------------
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
    time.sleep(delay)
    pid = None
    for p in psutil.process_iter(['pid', 'name']):
        if p.info['name'] and 'SIDFactory' in p.info['name']:
            pid = p.info['pid']; break
    if pid is None:
        print('  drive_load: SF2II not found'); return
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
        if hits: hwnd = hits[0]; break
        time.sleep(0.2)
    if not hwnd:
        print('  drive_load: no window'); return
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # Foreground-window stealing can fail when another window has it —
        # the Click below normally still focuses SF2II, so don't bail.
        pass
    time.sleep(0.4)
    rect = win32gui.GetWindowRect(hwnd)
    pyautogui.click((rect[0]+rect[2])//2, rect[1]+20); time.sleep(0.4)
    send_vk(win32con.VK_F10);    time.sleep(1.0)
    send_vk(win32con.VK_TAB);    time.sleep(0.3)
    type_string(staged_name);    time.sleep(0.4)
    send_vk(win32con.VK_RETURN); time.sleep(0.8)
    send_vk(ord('Y'));           time.sleep(0.2)
    send_vk(win32con.VK_RETURN)
    print(f'  drive_load: F10-load completed for {staged_name}')


# -- main debug pump ------------------------------------------------------
def report_event(hproc, hthread, ctx, kind, info_extra=''):
    print(f'\n=========== {kind} ===========')
    if info_extra:
        print(info_extra)
    print(f'  RIP = 0x{ctx.Rip:x}')
    rva_mod, rva = addr_to_rva(hproc, ctx.Rip)
    if rva is not None:
        print(f'        -> {rva_mod} + 0x{rva:x}')
    print(f'  Registers: RAX={ctx.Rax:#x} RCX={ctx.Rcx:#x} RDX={ctx.Rdx:#x}')
    print(f'             RBX={ctx.Rbx:#x} RSI={ctx.Rsi:#x} RDI={ctx.Rdi:#x}')
    print(f'             R8={ctx.R8:#x}  R9={ctx.R9:#x}  R10={ctx.R10:#x}')
    print(f'             R11={ctx.R11:#x} R12={ctx.R12:#x} R13={ctx.R13:#x}')
    print(f'             R14={ctx.R14:#x} R15={ctx.R15:#x} RBP={ctx.Rbp:#x} RSP={ctx.Rsp:#x}')
    print(f'             Dr6={ctx.Dr6:#x} Dr7={ctx.Dr7:#x}')

    # 32 bytes of code AT RIP (so user can disassemble)
    code = read_mem(hproc, ctx.Rip, 32)
    if code:
        print(f'  code @ RIP: {code.hex()}')

    # Stack walk
    print('  stack:')
    frames = stack_walk(hproc, hthread, ctx, max_frames=24)
    for i, (pc, rva, mod) in enumerate(frames):
        if rva is not None:
            print(f'    [{i:>2d}] 0x{pc:x}  {mod} + 0x{rva:x}')
        else:
            print(f'    [{i:>2d}] 0x{pc:x}  {mod}')


def debug_loop(sf2_path=None, mode='spawn', pid=None, watch_addr=None, watch_size=8):
    """
    mode='spawn'  : CreateProcessW with DEBUG_PROCESS + drive F10-load
    mode='attach' : DebugActiveProcess on `pid`
    """
    if mode == 'spawn':
        if sf2_path is None:
            print('--watch / spawn requires an sf2 path to drive F10-load against')
            return
        bin_dir = Path(EDITOR).parent
        test_name = f'__sf2dbg__{int(time.time()*1000)%100000}.sf2'
        staged = bin_dir / test_name
        shutil.copyfile(sf2_path, staged)

        si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
        pi = PROCESS_INFORMATION()
        cmdline = ctypes.create_unicode_buffer(f'"{EDITOR}" --skip-intro')
        ok = k32.CreateProcessW(None, cmdline, None, None, False,
                                DEBUG_PROCESS, None, str(bin_dir),
                                ctypes.byref(si), ctypes.byref(pi))
        if not ok:
            print(f'CreateProcessW failed: {k32.GetLastError()}'); return
        target_pid = pi.dwProcessId
        target_handle = pi.hProcess
        print(f'Spawned SF2II pid={target_pid} (DEBUG_PROCESS)')
        threading.Thread(target=drive_load, args=(test_name,), daemon=True).start()

    elif mode == 'attach':
        if pid is None:
            print('--attach requires --pid'); return
        # Don't kill the target if our debugger exits abnormally
        k32.DebugSetProcessKillOnExit(False)
        if not k32.DebugActiveProcess(pid):
            print(f'DebugActiveProcess({pid}) failed: {k32.GetLastError()}'); return
        target_pid = pid
        target_handle = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
                                         False, pid)
        print(f'Attached to SF2II pid={pid}')
        staged = None
    else:
        print(f'unknown mode {mode}'); return

    hproc = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
                             | PROCESS_VM_OPERATION, False, target_pid)

    # If a watchpoint was requested, defer setting it until the F10-load is
    # likely in progress — that way the relevant rendering threads exist.
    # In spawn mode we wait ~3s; in attach mode we set immediately.
    if watch_addr is not None:
        if mode == 'spawn':
            # Run a deferred installer in another thread
            def deferred_install():
                time.sleep(3.0)
                set_hw_write_watchpoint(target_pid, watch_addr, watch_size)
            threading.Thread(target=deferred_install, daemon=True).start()
        else:
            set_hw_write_watchpoint(target_pid, watch_addr, watch_size)

    try:
        evt = DEBUG_EVENT()
        deadline = time.time() + 60
        captured = 0
        while time.time() < deadline:
            if not k32.WaitForDebugEvent(ctypes.byref(evt), 1000):
                continue
            code  = -1
            first = 1
            if evt.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
                er = evt.u.Exception.ExceptionRecord
                first = evt.u.Exception.dwFirstChance
                code  = er.ExceptionCode
                addr  = er.ExceptionAddress

                # Filter loader/SDL breakpoints
                if code in (EXCEPTION_BREAKPOINT, 0x4000001F):
                    k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_CONTINUE)
                    continue

                hthread = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_SUSPEND_RESUME,
                                         False, evt.dwThreadId)
                ctx = CONTEXT64()
                ctx.ContextFlags = CONTEXT_ALL
                k32.GetThreadContext(hthread, ctypes.byref(ctx))

                if code == EXCEPTION_SINGLE_STEP:
                    # Hardware breakpoint hit. Dr6 indicates which DR.
                    dr6 = ctx.Dr6
                    fired = []
                    for s in range(4):
                        if dr6 & (1 << s):
                            fired.append(s)
                    info = (f'  Watchpoint fired (Dr6 = {dr6:#x}, '
                            f'slot{",".join(str(s) for s in fired) or "?"})')
                    info += f'\n  Watched value (8 bytes @ {watch_addr:#x}): '
                    val = read_mem(hproc, watch_addr, 8) if watch_addr else None
                    if val:
                        info += val.hex()
                    report_event(hproc, hthread, ctx, 'HW WATCHPOINT', info)
                    captured += 1
                    # Continue. Note: Intel restarts the trapping insn, so we
                    # must clear Dr6 so the SAME insn doesn't re-trap forever.
                    ctx.Dr6 = 0
                    ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
                    k32.SetThreadContext(hthread, ctypes.byref(ctx))
                    k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_CONTINUE)
                    continue

                if code == EXCEPTION_ACCESS_VIOLATION and first:
                    info = ''
                    if er.NumberParameters >= 2:
                        rwf  = er.ExceptionInformation[0]   # 0=read, 1=write, 8=DEP
                        bad  = er.ExceptionInformation[1]
                        info = (f'  AV: {"WRITE" if rwf == 1 else "READ" if rwf == 0 else "DEP"} '
                                f'at 0x{bad:x}')
                    report_event(hproc, hthread, ctx, 'ACCESS VIOLATION', info)
                    # Pass to second-chance so process exits cleanly
                    k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId,
                                           DBG_EXCEPTION_NOT_HANDLED)
                    return

                k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId,
                                        DBG_EXCEPTION_NOT_HANDLED)
                continue

            elif evt.dwDebugEventCode == EXIT_PROCESS_DEBUG_EVENT:
                print(f'Process exited (captured {captured} watchpoint events).')
                return

            else:
                k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, DBG_CONTINUE)

        print(f'Timeout — captured {captured} watchpoint events, no AV.')
    finally:
        if mode == 'spawn' and staged is not None:
            try:
                if staged.exists(): staged.unlink()
            except: pass
            try: k32.TerminateProcess(target_handle, 0)
            except: pass


def main(argv):
    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('sf2', nargs='?', help='SF2 path (for spawn mode)')
    p.add_argument('--attach', type=int, metavar='PID',
        help='Attach to running pid via DebugActiveProcess')
    p.add_argument('--watch', type=lambda x: int(x, 0), metavar='ADDR',
        help='Hardware write-watchpoint at this absolute address')
    p.add_argument('--size', type=int, default=8, choices=[1, 2, 4, 8],
        help='Watchpoint size in bytes (default 8)')
    args = p.parse_args(argv)

    if args.attach:
        debug_loop(args.sf2, mode='attach', pid=args.attach,
                   watch_addr=args.watch, watch_size=args.size)
    else:
        if not args.sf2:
            p.error('sf2 path required for spawn mode')
        debug_loop(args.sf2, mode='spawn',
                   watch_addr=args.watch, watch_size=args.size)


if __name__ == '__main__':
    main(sys.argv[1:])
