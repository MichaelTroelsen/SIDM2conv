#!/bin/bash
# Test SIDwinder with a failing file and capture detailed output

echo "Testing SIDwinder disassembly with verbose output..."

# Try with a failing file
tools/SIDwinder.exe -disassemble "SIDSF2player/Driver 11 Test - Arpeggio.sid" test_debug.asm 2>&1 | tee sidwinder_debug.log

echo ""
echo "=== Debug Output ==="
cat sidwinder_debug.log

# Check what was the last valid PC before failure
echo ""
echo "=== Analysis ==="
echo "The CPU jumped to an invalid address during init execution."
echo "This suggests:"
echo "1. Indirect jump reading uninitialized memory"
echo "2. RTS with corrupted stack"
echo "3. Invalid opcode causing PC corruption"

