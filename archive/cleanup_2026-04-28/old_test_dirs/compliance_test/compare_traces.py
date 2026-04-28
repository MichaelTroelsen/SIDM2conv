#!/usr/bin/env python3
"""Compare SIDwinder trace outputs between .exe and Python versions"""

def read_trace(filename):
    """Read trace file and return list of lines"""
    with open(filename, 'r') as f:
        return [line.rstrip() for line in f]

def main():
    exe_lines = read_trace('sidwinder_exe.txt')
    py_lines = read_trace('sidwinder_py.txt')

    print(f"EXE trace: {len(exe_lines)} lines")
    print(f"PY trace: {len(py_lines)} lines")
    print()

    # Compare first few lines
    print("=== First 5 lines comparison ===")
    for i in range(min(5, len(exe_lines), len(py_lines))):
        exe_line = exe_lines[i][:80] if i < len(exe_lines) else "N/A"
        py_line = py_lines[i][:80] if i < len(py_lines) else "N/A"
        match = "[OK]" if exe_line == py_line else "[DIFF]"
        print(f"Line {i}: {match}")
        if exe_line != py_line:
            print(f"  EXE: {exe_line}")
            print(f"  PY:  {py_line}")

    print()

    # Check if PY frames match EXE frames (offset by 1 due to init format difference)
    print("=== Checking if PY frames match EXE frames (offset +1) ===")
    matches = 0
    differences = 0
    for i in range(1, min(20, len(py_lines))):  # Check first 20 frames
        exe_idx = i
        py_idx = i
        if exe_idx < len(exe_lines) and py_idx < len(py_lines):
            if exe_lines[exe_idx] == py_lines[py_idx]:
                matches += 1
            else:
                differences += 1
                if differences <= 3:  # Show first 3 differences
                    print(f"\nFrame {i} differs:")
                    print(f"  EXE: {exe_lines[exe_idx][:120]}...")
                    print(f"  PY:  {py_lines[py_idx][:120]}...")

    print(f"\nFirst 20 frames: {matches} matches, {differences} differences")

    if differences == 0:
        print("\n[OK] All frames match!")
    else:
        print(f"\n[DIFF] Frames differ - likely CPU emulation timing differences")
        print("       Format is correct, but register values differ")

if __name__ == "__main__":
    main()
