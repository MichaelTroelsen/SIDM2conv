"""Spawn an SF2II build with an SF2 as argv[1] (main.cpp:95 auto-loads
it — no pyautogui needed) under DEBUG_PROCESS, and on the access
violation resolve the faulting RIP + call stack to function + source:line
via dbghelp against the build's .pdb.

Usage:
  py -3 pyscript/sf2_argv_crash.py <exe> <sf2> [--frames-timeout S]

Use the SYMBOLIZED local build:
  py -3 pyscript/sf2_argv_crash.py \
    "C:/Users/mit/AppData/Local/Temp/sf2-src/sidfactory2/Release/SIDFactoryII.exe" \
    bin/_tri_3545_I.sf2
"""
import ctypes, sys, time
from ctypes import wintypes as wt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sf2_debug_inspect_v2 as D

k32 = D.k32
SYMBOL_NAME_LEN = 1024


class SYMBOL_INFO(ctypes.Structure):
    _fields_ = [
        ("SizeOfStruct", wt.ULONG), ("TypeIndex", wt.ULONG),
        ("Reserved", ctypes.c_uint64 * 2), ("Index", wt.ULONG),
        ("Size", wt.ULONG), ("ModBase", ctypes.c_uint64),
        ("Flags", wt.ULONG), ("Value", ctypes.c_uint64),
        ("Address", ctypes.c_uint64), ("Register", wt.ULONG),
        ("Scope", wt.ULONG), ("Tag", wt.ULONG),
        ("NameLen", wt.ULONG), ("MaxNameLen", wt.ULONG),
        ("Name", ctypes.c_char * SYMBOL_NAME_LEN),
    ]


class IMAGEHLP_LINE64(ctypes.Structure):
    _fields_ = [
        ("SizeOfStruct", wt.DWORD), ("Key", ctypes.c_void_p),
        ("LineNumber", wt.DWORD), ("FileName", ctypes.c_char_p),
        ("Address", ctypes.c_uint64),
    ]


def resolve(dbghelp, hproc, addr):
    """Return 'func+0xNN (file:line)' or '0x.. (module)'."""
    buf = ctypes.create_string_buffer(ctypes.sizeof(SYMBOL_INFO))
    sym = ctypes.cast(buf, ctypes.POINTER(SYMBOL_INFO)).contents
    sym.SizeOfStruct = 88  # sizeof without Name array (Win SDK value)
    sym.MaxNameLen = SYMBOL_NAME_LEN - 1
    disp = ctypes.c_uint64(0)
    dbghelp.SymFromAddr.argtypes = [wt.HANDLE, ctypes.c_uint64,
                                    ctypes.POINTER(ctypes.c_uint64),
                                    ctypes.POINTER(SYMBOL_INFO)]
    dbghelp.SymFromAddr.restype = wt.BOOL
    name = "?"
    if dbghelp.SymFromAddr(hproc, addr, ctypes.byref(disp), ctypes.byref(sym)):
        name = f"{sym.Name.decode('latin1','replace')}+0x{disp.value:x}"
    line = IMAGEHLP_LINE64()
    line.SizeOfStruct = ctypes.sizeof(IMAGEHLP_LINE64)
    ld = wt.DWORD(0)
    dbghelp.SymGetLineFromAddr64.argtypes = [wt.HANDLE, ctypes.c_uint64,
                                             ctypes.POINTER(wt.DWORD),
                                             ctypes.POINTER(IMAGEHLP_LINE64)]
    dbghelp.SymGetLineFromAddr64.restype = wt.BOOL
    src = ""
    if dbghelp.SymGetLineFromAddr64(hproc, addr, ctypes.byref(ld),
                                    ctypes.byref(line)) and line.FileName:
        fn = line.FileName.decode("latin1", "replace")
        src = f"  ({Path(fn).name}:{line.LineNumber})"
    return f"{name}{src}"


def main(argv):
    if len(argv) < 2:
        print(__doc__); sys.exit(2)
    exe = str(Path(argv[0]).resolve())
    sf2 = str(Path(argv[1]).resolve())

    si = D.STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = D.PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(f'"{exe}" "{sf2}"')
    workdir = str(Path(exe).parent)
    if not k32.CreateProcessW(None, cmdline, None, None, False,
                              D.DEBUG_PROCESS, None, workdir,
                              ctypes.byref(si), ctypes.byref(pi)):
        print(f"CreateProcessW failed: {k32.GetLastError()}"); sys.exit(1)
    print(f"Spawned {Path(exe).name} pid={pi.dwProcessId} with arg {Path(sf2).name}")

    dbghelp = D.load_dbghelp()
    dbghelp.SymInitialize.argtypes = [wt.HANDLE, wt.LPCSTR, wt.BOOL]
    dbghelp.SymInitialize.restype = wt.BOOL
    sym_inited = False

    evt = D.DEBUG_EVENT()
    deadline = time.time() + 90
    crashed = False
    while time.time() < deadline:
        if not k32.WaitForDebugEvent(ctypes.byref(evt), 1000):
            continue
        code = evt.dwDebugEventCode
        if code == 5:  # EXIT_PROCESS_DEBUG_EVENT
            print("Process exited (no crash captured)")
            break
        if code == 1:  # EXCEPTION_DEBUG_EVENT
            er = evt.u.Exception.ExceptionRecord
            first = evt.u.Exception.dwFirstChance
            if er.ExceptionCode == D.EXCEPTION_ACCESS_VIOLATION and first:
                hthread = k32.OpenThread(0x1FFFFF, False, evt.dwThreadId)
                ctx = D.CONTEXT64(); ctx.ContextFlags = D.CONTEXT_ALL
                k32.GetThreadContext(hthread, ctypes.byref(ctx))
                if not sym_inited:
                    dbghelp.SymInitialize(pi.hProcess, None, True)
                    sym_inited = True
                acc = er.ExceptionInformation[0]
                addr = er.ExceptionInformation[1]
                print("\n=== ACCESS VIOLATION ===")
                print(f"  {'WRITE' if acc==1 else 'READ'} at 0x{addr:x}")
                print(f"  RIP = 0x{ctx.Rip:x}")
                print(f"  -> {resolve(dbghelp, pi.hProcess, ctx.Rip)}")
                print("  call stack:")
                for i, (pc, rva, mod) in enumerate(
                        D.stack_walk(pi.hProcess, hthread, ctx, 20)):
                    s = resolve(dbghelp, pi.hProcess, pc)
                    print(f"    [{i:2d}] 0x{pc:x} {mod}  {s}")
                crashed = True
                k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId,
                                       D.DBG_EXCEPTION_NOT_HANDLED)
                break
            k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId,
                                   D.DBG_EXCEPTION_NOT_HANDLED)
            continue
        k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, D.DBG_CONTINUE)

    try:
        k32.TerminateProcess(pi.hProcess, 0)
    except Exception:
        pass
    sys.exit(0 if crashed else 3)


if __name__ == "__main__":
    main(sys.argv[1:])
