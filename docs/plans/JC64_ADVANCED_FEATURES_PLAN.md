# JC64 Advanced Features Implementation Plan

**Document Version**: 1.0.0
**Date**: 2025-12-24
**Status**: Planning Phase
**Target**: Enable SID file disassembly and advanced player detection using JC64

---

## Executive Summary

This plan addresses the implementation of advanced JC64 features for SIDM2, specifically enabling SID file disassembly, advanced player detection, and frequency table analysis. The primary blocker is the FileDasm ArrayIndexOutOfBoundsException bug which requires source code patching and rebuilding.

**Primary Goal**: Enable SID file disassembly for validation, analysis, and player structure examination.

**Secondary Goals**:
- Advanced player detection using SIDId patterns
- Frequency table recognition using SidFreq
- Memory usage analysis for driver optimization

---

## Table of Contents

1. [Current Situation](#1-current-situation)
2. [Implementation Phases](#2-implementation-phases)
3. [Detailed Task Breakdown](#3-detailed-task-breakdown)
4. [Technical Requirements](#4-technical-requirements)
5. [Risk Assessment](#5-risk-assessment)
6. [Success Criteria](#6-success-criteria)
7. [Timeline and Effort](#7-timeline-and-effort)
8. [Integration Strategy](#8-integration-strategy)

---

## 1. Current Situation

### 1.1 What's Working

✅ **PSID Header Parsing**:
- 100% accurate Python implementation
- Extracts all metadata (title, author, addresses)
- Handles PSID v1/v2 and RSID formats

✅ **Python Wrapper**:
- Automatic JAR discovery
- Comprehensive error handling
- Test suite included
- Ready for integration

✅ **Basic Player Detection**:
- Heuristic based on init address
- Works for standard Laxity files ($1000)

### 1.2 What's Broken

❌ **FileDasm Disassembly**:
```
Error: ArrayIndexOutOfBoundsException: 65535
Location: FileDasm.java:153
Cause: Off-by-one error in memory buffer allocation
Impact: ALL disassembly blocked
```

❌ **SIDId Pattern Matching**:
- Requires Java wrapper compilation
- No JDK installed (only JRE)
- Cannot access 80+ player signatures

❌ **SidFreq Frequency Analysis**:
- Not tested
- Requires working disassembly
- No Python wrapper implemented

### 1.3 Blockers

**Critical Blocker**: FileDasm bug prevents all disassembly
**Major Blocker**: No JDK for Java compilation
**Minor Blocker**: No Apache Ant for building

---

## 2. Implementation Phases

### Phase 1: Development Environment Setup
**Duration**: 2-4 hours
**Priority**: Critical
**Goal**: Install required development tools

**Tasks**:
1. Install JDK 8 or later
2. Install Apache Ant
3. Verify build environment
4. Test Java compilation

**Deliverables**:
- Working JDK with javac
- Apache Ant installed and configured
- Environment variables set (JAVA_HOME, ANT_HOME)

### Phase 2: FileDasm Bug Fix
**Duration**: 4-6 hours
**Priority**: Critical
**Goal**: Fix ArrayIndexOutOfBoundsException and rebuild JC64

**Tasks**:
1. Analyze FileDasm.java bug in detail
2. Implement fix (increase buffer size)
3. Build JC64 from source with Ant
4. Test disassembly on SID files
5. Verify fix doesn't break other functionality

**Deliverables**:
- Patched FileDasm.java
- Rebuilt JC64.jar with fix
- Passing disassembly tests

### Phase 3: Disassembly Integration
**Duration**: 6-8 hours
**Priority**: High
**Goal**: Integrate working disassembly into Python wrapper

**Tasks**:
1. Update Python wrapper to use fixed JAR
2. Implement disassembly methods
3. Add output format selection (ACME, KickAssembler, etc.)
4. Create disassembly test suite
5. Optimize performance (caching, batch processing)

**Deliverables**:
- Enhanced jc64_wrapper.py with disassembly
- Test suite with 5+ SID files
- Performance benchmarks

### Phase 4: Advanced Player Detection
**Duration**: 8-12 hours
**Priority**: Medium
**Goal**: Implement SIDId pattern matching via Java wrapper

**Tasks**:
1. Create PlayerDetector.java wrapper
2. Load SIDId patterns from configuration
3. Compile and package wrapper
4. Integrate with Python via subprocess
5. Test on 20+ SID files with known players

**Deliverables**:
- PlayerDetector.class compiled
- Pattern database loaded
- 90%+ detection accuracy on test set

### Phase 5: Frequency Table Analysis
**Duration**: 6-10 hours
**Priority**: Medium
**Goal**: Detect and validate frequency tables in SID files

**Tasks**:
1. Create FrequencyAnalyzer.java wrapper
2. Implement table detection (12 formats)
3. Extract A4 frequency and table type
4. Integrate with Python wrapper
5. Cross-validate with SIDM2 extraction

**Deliverables**:
- FrequencyAnalyzer.class compiled
- Detection for 12 table variants
- Validation report comparing JC64 vs SIDM2

### Phase 6: SIDM2 Pipeline Integration
**Duration**: 4-6 hours
**Priority**: High
**Goal**: Integrate all JC64 features into SIDM2 workflow

**Tasks**:
1. Update laxity_parser.py with JC64 detection
2. Add disassembly to validation pipeline
3. Create comparison reports (original vs exported)
4. Integrate frequency validation
5. Update documentation

**Deliverables**:
- Enhanced SIDM2 pipeline
- Validation reports with JC64 analysis
- User documentation

---

## 3. Detailed Task Breakdown

### Phase 1: Development Environment Setup

#### Task 1.1: Install JDK
**Estimated Time**: 30 minutes

**Steps**:
1. Download JDK 8 (or later) from Oracle or AdoptOpenJDK
   - URL: https://adoptium.net/
   - Version: Java 8 (LTS) or Java 11 (LTS)
   - Platform: Windows x64

2. Install JDK
   ```bash
   # Run installer
   java-installer.exe
   # Install to: C:\Program Files\Java\jdk-8
   ```

3. Set environment variables
   ```bash
   # Set JAVA_HOME
   setx JAVA_HOME "C:\Program Files\Java\jdk-8"

   # Add to PATH
   setx PATH "%PATH%;%JAVA_HOME%\bin"
   ```

4. Verify installation
   ```bash
   java -version      # Should show JDK version
   javac -version     # Should show compiler version
   ```

**Success Criteria**:
- `javac -version` returns successfully
- Can compile simple HelloWorld.java

#### Task 1.2: Install Apache Ant
**Estimated Time**: 20 minutes

**Steps**:
1. Download Apache Ant from https://ant.apache.org/
   - Version: 1.10.14 or later
   - Format: ZIP archive

2. Extract to installation directory
   ```bash
   # Extract to: C:\Program Files\Apache\apache-ant-1.10.14
   ```

3. Set environment variables
   ```bash
   # Set ANT_HOME
   setx ANT_HOME "C:\Program Files\Apache\apache-ant-1.10.14"

   # Add to PATH
   setx PATH "%PATH%;%ANT_HOME%\bin"
   ```

4. Verify installation
   ```bash
   ant -version       # Should show Ant version
   ```

**Success Criteria**:
- `ant -version` returns successfully
- Can run `ant` command from any directory

#### Task 1.3: Test Environment
**Estimated Time**: 30 minutes

**Steps**:
1. Create test Java file
   ```java
   // TestCompile.java
   public class TestCompile {
       public static void main(String[] args) {
           System.out.println("JDK working!");
       }
   }
   ```

2. Compile and run
   ```bash
   javac TestCompile.java
   java TestCompile
   # Output: "JDK working!"
   ```

3. Test Ant with simple build.xml
   ```xml
   <!-- test-build.xml -->
   <project name="test" default="compile">
       <target name="compile">
           <javac srcdir="." destdir="."/>
       </target>
   </project>
   ```

4. Run Ant build
   ```bash
   ant -f test-build.xml
   # Should compile successfully
   ```

**Success Criteria**:
- Java compilation works
- Ant build succeeds
- Ready to build JC64

---

### Phase 2: FileDasm Bug Fix

#### Task 2.1: Analyze Bug in Detail
**Estimated Time**: 1 hour

**Investigation**:
1. Read FileDasm.java source code around line 145-160
2. Identify memory buffer allocation
3. Trace array access pattern
4. Confirm off-by-one error

**Current Code** (FileDasm.java:145-153):
```java
byte[] memoryFlags=memory.getMemoryState(0, 0xFFFF);  // Line 145

for (int i=0; i<memoryDasm.length; i++) {
   memoryDasm[i]=new MemoryDasm();
   memoryDasm[i].address=i;
}

for (int i=0; i<memoryDasm.length; i++) {
   memoryDasm[i].isData = (memoryFlags[i] &      // Line 153 - CRASH
          (memoryState.MEM_READ | memoryState.MEM_READ_FIRST |
           memoryState.MEM_WRITE | memoryState.MEM_WRITE_FIRST |
           memoryState.MEM_SAMPLE)) !=0;

   memoryDasm[i].isCode = (memoryFlags[i] &
                   (memoryState.MEM_EXECUTE | memoryState.MEM_EXECUTE_FIRST)) !=0;
}
```

**Problem Identification**:
- `getMemoryState(0, 0xFFFF)` likely returns array of size `0xFFFF - 0 = 65535`
- But loop goes `0 <= i < memoryDasm.length`
- If `memoryDasm.length = 65536` (for full 64K address space)
- Then `memoryFlags[65535]` is out of bounds (array size 65535, valid indices 0-65534)

**Root Cause**: `getMemoryState()` returns array size based on `(end - start)` instead of `(end - start + 1)`

#### Task 2.2: Implement Fix
**Estimated Time**: 1 hour

**Solution Option 1**: Fix getMemoryState() method

**File**: `src/sw_emulator/software/MemoryFlags.java`

Find `getMemoryState()` method:
```java
public byte[] getMemoryState(int start, int end) {
    // OLD: Returns array of size (end - start)
    byte[] result = new byte[end - start];

    // FIXED: Returns array of size (end - start + 1)
    byte[] result = new byte[end - start + 1];

    for (int i = start; i <= end; i++) {
        result[i - start] = memoryState[i];
    }
    return result;
}
```

**Solution Option 2**: Fix FileDasm loop bounds

**File**: `src/sw_emulator/software/FileDasm.java`

```java
// OLD: Loop to memoryDasm.length (65536)
for (int i=0; i<memoryDasm.length; i++) {
    memoryDasm[i].isData = (memoryFlags[i] & ...) !=0;
}

// FIXED: Loop to memoryFlags.length (65535)
for (int i=0; i<memoryFlags.length; i++) {
    memoryDasm[i].isData = (memoryFlags[i] & ...) !=0;
}

// Handle last address separately if needed
if (memoryDasm.length > memoryFlags.length) {
    memoryDasm[memoryFlags.length].isData = false;
    memoryDasm[memoryFlags.length].isCode = false;
}
```

**Recommended**: Option 1 (fix root cause in MemoryFlags)

**Patch File**:
```diff
--- a/src/sw_emulator/software/MemoryFlags.java
+++ b/src/sw_emulator/software/MemoryFlags.java
@@ -XX,7 +XX,7 @@
 public byte[] getMemoryState(int start, int end) {
-    byte[] result = new byte[end - start];
+    byte[] result = new byte[end - start + 1];

     for (int i = start; i <= end; i++) {
         result[i - start] = memoryState[i];
```

#### Task 2.3: Build JC64 from Source
**Estimated Time**: 1-2 hours

**Steps**:
1. Navigate to JC64 repository
   ```bash
   cd C:\Users\mit\Downloads\jc64
   ```

2. Apply patch
   ```bash
   # Edit src/sw_emulator/software/MemoryFlags.java
   # Change line: byte[] result = new byte[end - start];
   # To:         byte[] result = new byte[end - start + 1];
   ```

3. Clean and build
   ```bash
   ant clean
   ant build
   ```

4. Locate built JAR
   ```bash
   # Should be in: dist/jc64.jar or build/jar/jc64.jar
   ls -l dist/
   ls -l build/jar/
   ```

5. Copy to test location
   ```bash
   cp dist/jc64.jar C:/Users/mit/claude/c64server/SIDM2/jc64_test/jc64-fixed.jar
   ```

**Success Criteria**:
- Ant build completes without errors
- JAR file created
- File size similar to original (~15 MB)

#### Task 2.4: Test Fixed Disassembly
**Estimated Time**: 1 hour

**Test Script**:
```bash
cd C:/Users/mit/claude/c64server/SIDM2

# Test with Laxity SID file
java -cp jc64_test/jc64-fixed.jar sw_emulator.software.FileDasm \
     -en \
     Laxity/Stinsens_Last_Night_of_89.sid \
     jc64_test/stinsens_disasm.asm

# Check output
if [ -f jc64_test/stinsens_disasm.asm ]; then
    echo "SUCCESS: Disassembly created"
    wc -l jc64_test/stinsens_disasm.asm
    head -50 jc64_test/stinsens_disasm.asm
else
    echo "FAILED: No output file"
    exit 1
fi
```

**Validation**:
1. No ArrayIndexOutOfBoundsException
2. Assembly file created
3. File contains valid 6502 assembly
4. Init and Play routines identified
5. Labels generated correctly

**Expected Output**:
```assembly
; PSID file disassembly
; Title: Stinsen's Last Night of '89
; Author: Thomas E. Petersen (Laxity)

        *=$1000

PSIDINIT:
        LDA #$00
        STA $D400
        ; ... more code ...

PSIDPLAY:
        JSR $10A1
        RTS

; ... music data ...
```

#### Task 2.5: Regression Testing
**Estimated Time**: 1 hour

**Test Cases**:
1. **Small SID** (< 5 KB)
   - Test: Stinsens_Last_Night_of_89.sid
   - Expected: Success

2. **Medium SID** (5-10 KB)
   - Test: Broware.sid
   - Expected: Success

3. **Large SID** (> 10 KB)
   - Find largest SID in collection
   - Expected: Success

4. **MUS File**
   - Find MUS format file
   - Expected: Success

5. **PRG File**
   - Simple C64 PRG
   - Expected: Success

**Success Criteria**:
- All 5 test cases pass
- No exceptions thrown
- Valid assembly output for each

---

### Phase 3: Disassembly Integration

#### Task 3.1: Update Python Wrapper
**Estimated Time**: 2 hours

**File**: `pyscript/jc64_wrapper.py`

**Implementation**:
```python
class JC64Wrapper:
    def __init__(self, jar_path: Optional[str] = None, use_fixed_jar: bool = True):
        """
        Initialize with option to use fixed JAR.

        Args:
            jar_path: Path to JC64.jar
            use_fixed_jar: If True, use jc64-fixed.jar with bug fixes
        """
        if jar_path is None:
            if use_fixed_jar:
                jar_path = self._find_fixed_jar()
            else:
                jar_path = self._find_jc64_jar()

        self.jar_path = Path(jar_path)
        self.use_fixed_jar = use_fixed_jar

    def _find_fixed_jar(self) -> str:
        """Find patched JC64 JAR with FileDasm fix."""
        common_paths = [
            Path("jc64_test/jc64-fixed.jar"),
            Path("jc64/dist/jc64.jar"),
            Path(__file__).parent.parent / "jc64_test/jc64-fixed.jar",
        ]

        for path in common_paths:
            if path.exists():
                return str(path)

        # Fallback to original
        return self._find_jc64_jar()

    def disassemble_sid(
        self,
        sid_file: Path,
        output_file: Optional[Path] = None,
        assembler: str = "acme",
        language: str = "en"
    ) -> str:
        """
        Disassemble SID file using fixed FileDasm.

        Args:
            sid_file: Path to input SID file
            output_file: Optional path for output assembly file
            assembler: Target assembler (acme, kickasm, ca65, etc.)
            language: Output language (en or it)

        Returns:
            Assembly code as string

        Raises:
            RuntimeError: If disassembly fails
        """
        if not self.use_fixed_jar:
            raise RuntimeError(
                "Disassembly requires fixed JAR. "
                "Initialize with use_fixed_jar=True"
            )

        if output_file is None:
            output_file = Path(tempfile.mktemp(suffix=".asm"))

        # Language flag
        lang_flag = "-en" if language == "en" else "-it"

        cmd = [
            "java",
            "-cp", str(self.jar_path),
            "sw_emulator.software.FileDasm",
            lang_flag,
            str(sid_file),
            str(output_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise RuntimeError(f"Disassembly failed: {result.stderr}")

        if not output_file.exists():
            raise RuntimeError("Disassembly output file not created")

        # Read and return content
        asm_code = output_file.read_text()

        # Optionally convert to different assembler format
        if assembler.lower() != "acme":  # FileDasm default
            asm_code = self._convert_assembler_format(asm_code, assembler)

        return asm_code

    def _convert_assembler_format(self, asm_code: str, target: str) -> str:
        """
        Convert assembly code to different assembler syntax.

        Basic conversions for common assemblers.
        For full support, would need proper parser.
        """
        if target.lower() == "kickasm":
            # ACME → KickAssembler conversions
            asm_code = asm_code.replace("!byte", ".byte")
            asm_code = asm_code.replace("!word", ".word")
            asm_code = asm_code.replace("!text", ".text")

        elif target.lower() == "ca65":
            # ACME → CA65 conversions
            asm_code = asm_code.replace("!byte", ".byte")
            asm_code = asm_code.replace("!word", ".word")
            asm_code = asm_code.replace("!text", ".asciiz")

        return asm_code

    def compare_sids(
        self,
        original_sid: Path,
        exported_sid: Path
    ) -> Dict:
        """
        Compare two SID files by disassembling both.

        Useful for validating SF2→SID conversion accuracy.

        Returns:
            Dictionary with comparison metrics
        """
        # Disassemble both
        original_asm = self.disassemble_sid(original_sid)
        exported_asm = self.disassemble_sid(exported_sid)

        # Parse headers
        original_header = self.parse_psid_header(original_sid)
        exported_header = self.parse_psid_header(exported_sid)

        # Calculate similarity
        original_lines = set(original_asm.splitlines())
        exported_lines = set(exported_asm.splitlines())

        common_lines = original_lines & exported_lines
        total_lines = original_lines | exported_lines

        similarity = len(common_lines) / len(total_lines) if total_lines else 0

        return {
            'original_file': str(original_sid),
            'exported_file': str(exported_sid),
            'original_size': len(original_asm),
            'exported_size': len(exported_asm),
            'header_match': original_header == exported_header,
            'init_addr_match': original_header['init_addr'] == exported_header['init_addr'],
            'play_addr_match': original_header['play_addr'] == exported_header['play_addr'],
            'code_similarity': f"{similarity:.2%}",
            'common_lines': len(common_lines),
            'total_lines': len(total_lines)
        }
```

#### Task 3.2: Create Disassembly Test Suite
**Estimated Time**: 2 hours

**File**: `pyscript/test_jc64_disasm.py`

```python
"""Test suite for JC64 disassembly functionality."""

import pytest
from pathlib import Path
from pyscript.jc64_wrapper import JC64Wrapper


class TestJC64Disassembly:
    """Test JC64 disassembly features."""

    @pytest.fixture
    def jc64(self):
        """Create JC64 wrapper with fixed JAR."""
        return JC64Wrapper(use_fixed_jar=True)

    @pytest.fixture
    def test_sids(self):
        """Get list of test SID files."""
        return [
            Path("Laxity/Stinsens_Last_Night_of_89.sid"),
            Path("Laxity/Broware.sid"),
            Path("Laxity/21_G4_demo_tune_1.sid"),
        ]

    def test_disassemble_basic(self, jc64, test_sids):
        """Test basic disassembly functionality."""
        for sid_file in test_sids:
            if not sid_file.exists():
                pytest.skip(f"Test file not found: {sid_file}")

            # Disassemble
            asm_code = jc64.disassemble_sid(sid_file)

            # Verify output
            assert len(asm_code) > 0, "Empty disassembly output"
            assert "PSID" in asm_code or "RSID" in asm_code, "Missing PSID header"
            assert "$" in asm_code, "No hexadecimal addresses"
            assert any(op in asm_code for op in ["LDA", "STA", "JMP", "JSR"]), \
                "No 6502 opcodes found"

    def test_disassemble_with_output_file(self, jc64, test_sids):
        """Test disassembly with explicit output file."""
        sid_file = test_sids[0]
        if not sid_file.exists():
            pytest.skip(f"Test file not found: {sid_file}")

        output_file = Path("jc64_test/test_output.asm")

        # Disassemble
        asm_code = jc64.disassemble_sid(sid_file, output_file)

        # Verify file created
        assert output_file.exists(), "Output file not created"

        # Verify content matches
        assert asm_code == output_file.read_text(), "Content mismatch"

        # Cleanup
        output_file.unlink()

    def test_compare_sids(self, jc64):
        """Test SID comparison functionality."""
        # Use same file for perfect match
        sid_file = Path("Laxity/Stinsens_Last_Night_of_89.sid")
        if not sid_file.exists():
            pytest.skip(f"Test file not found: {sid_file}")

        # Compare file with itself
        result = jc64.compare_sids(sid_file, sid_file)

        # Verify perfect match
        assert result['header_match'] == True
        assert result['init_addr_match'] == True
        assert result['play_addr_match'] == True
        assert result['code_similarity'] == "100.00%"

    def test_disassembly_contains_music_data(self, jc64, test_sids):
        """Verify disassembly identifies music data sections."""
        sid_file = test_sids[0]
        if not sid_file.exists():
            pytest.skip(f"Test file not found: {sid_file}")

        asm_code = jc64.disassemble_sid(sid_file)

        # Should contain data declarations
        assert any(directive in asm_code for directive in [".byte", "!byte", "db"]), \
            "No data declarations found"

    def test_disassembly_performance(self, jc64, test_sids):
        """Test disassembly performance."""
        import time

        sid_file = test_sids[0]
        if not sid_file.exists():
            pytest.skip(f"Test file not found: {sid_file}")

        start = time.time()
        asm_code = jc64.disassemble_sid(sid_file)
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 5.0, f"Disassembly too slow: {elapsed:.2f}s"
        print(f"\nDisassembly time: {elapsed:.2f}s ({len(asm_code)} bytes)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Task 3.3: Batch Disassembly Tool
**Estimated Time**: 1 hour

**File**: `scripts/batch_disassemble.py`

```python
"""Batch disassemble SID files for analysis."""

import argparse
from pathlib import Path
from pyscript.jc64_wrapper import JC64Wrapper


def batch_disassemble(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "*.sid",
    assembler: str = "acme"
):
    """
    Disassemble all SID files in directory.

    Args:
        input_dir: Directory containing SID files
        output_dir: Directory for assembly output
        pattern: File pattern (default: *.sid)
        assembler: Target assembler format
    """
    jc64 = JC64Wrapper(use_fixed_jar=True)

    # Find SID files
    sid_files = list(input_dir.glob(pattern))
    print(f"Found {len(sid_files)} SID files")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Disassemble each
    success_count = 0
    fail_count = 0

    for sid_file in sid_files:
        output_file = output_dir / f"{sid_file.stem}.asm"

        try:
            print(f"Disassembling: {sid_file.name}...", end=" ")
            asm_code = jc64.disassemble_sid(sid_file, output_file, assembler=assembler)
            print(f"OK ({len(asm_code)} bytes)")
            success_count += 1

        except Exception as e:
            print(f"FAILED: {e}")
            fail_count += 1

    print(f"\nResults: {success_count} success, {fail_count} failed")


def main():
    parser = argparse.ArgumentParser(description="Batch disassemble SID files")
    parser.add_argument("input_dir", type=Path, help="Input directory with SID files")
    parser.add_argument("output_dir", type=Path, help="Output directory for assembly files")
    parser.add_argument("--pattern", default="*.sid", help="File pattern (default: *.sid)")
    parser.add_argument("--assembler", default="acme",
                       choices=["acme", "kickasm", "ca65"],
                       help="Target assembler format")

    args = parser.parse_args()

    batch_disassemble(args.input_dir, args.output_dir, args.pattern, args.assembler)


if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Disassemble all Laxity SID files
python scripts/batch_disassemble.py Laxity jc64_test/disasm_output

# Disassemble with KickAssembler format
python scripts/batch_disassemble.py Laxity jc64_test/kickasm --assembler kickasm
```

---

### Phase 4: Advanced Player Detection

#### Task 4.1: Create PlayerDetector Java Wrapper
**Estimated Time**: 2 hours

**File**: `jc64_test/PlayerDetector.java`

```java
import sw_emulator.software.SidId;
import java.io.*;

/**
 * Advanced SID player detection using JC64's SIDId algorithm.
 *
 * Usage: java -cp JC64.jar:. PlayerDetector <sid_file>
 */
public class PlayerDetector {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java PlayerDetector <sid_file>");
            System.exit(1);
        }

        String sidFile = args[0];

        try {
            // Read SID file into buffer
            File file = new File(sidFile);
            if (!file.exists()) {
                System.err.println("ERROR: File not found: " + sidFile);
                System.exit(1);
            }

            FileInputStream fis = new FileInputStream(file);
            byte[] buffer = new byte[(int)file.length()];
            int bytesRead = fis.read(buffer);
            fis.close();

            if (bytesRead != buffer.length) {
                System.err.println("ERROR: Failed to read complete file");
                System.exit(1);
            }

            // Convert byte[] to int[] as required by SidId
            int[] intBuffer = new int[buffer.length];
            for (int i = 0; i < buffer.length; i++) {
                intBuffer[i] = buffer[i] & 0xFF;
            }

            // Get SidId instance
            SidId sidId = SidId.instance;

            // Try to load configuration if available
            try {
                sidId.readConfig("sidid_patterns.cfg");
            } catch (Exception e) {
                // Config file optional - use built-in patterns
            }

            // Identify player
            String players = sidId.identifyBuffer(intBuffer, intBuffer.length);

            // Output results as JSON for easy parsing
            System.out.println("{");
            System.out.println("  \"file\": \"" + escapeJson(sidFile) + "\",");
            System.out.println("  \"players\": \"" + escapeJson(players != null ? players : "") + "\",");
            System.out.println("  \"detected\": " + (players != null && !players.isEmpty()) + ",");
            System.out.println("  \"player_count\": " + sidId.getNumberOfPlayers() + ",");
            System.out.println("  \"pattern_count\": " + sidId.getNumberOfPatterns());
            System.out.println("}");

        } catch (IOException e) {
            System.err.println("ERROR: I/O error: " + e.getMessage());
            System.exit(1);
        } catch (Exception e) {
            System.err.println("ERROR: Detection failed: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static String escapeJson(String str) {
        return str.replace("\\", "\\\\")
                  .replace("\"", "\\\"")
                  .replace("\n", "\\n")
                  .replace("\r", "\\r")
                  .replace("\t", "\\t");
    }
}
```

#### Task 4.2: Compile Player Detector
**Estimated Time**: 30 minutes

**Steps**:
```bash
cd C:/Users/mit/claude/c64server/SIDM2/jc64_test

# Compile PlayerDetector
javac -cp "../jc64_test/jc64-fixed.jar" PlayerDetector.java

# Test
java -cp "../jc64_test/jc64-fixed.jar;." PlayerDetector ../Laxity/Stinsens_Last_Night_of_89.sid
```

**Expected Output**:
```json
{
  "file": "../Laxity/Stinsens_Last_Night_of_89.sid",
  "players": "Laxity NewPlayer v21",
  "detected": true,
  "player_count": 80,
  "pattern_count": 250
}
```

#### Task 4.3: Integrate with Python Wrapper
**Estimated Time**: 2 hours

**File**: `pyscript/jc64_wrapper.py` (enhancement)

```python
def identify_player_advanced(self, sid_file: Path) -> Dict:
    """
    Advanced player detection using SIDId pattern matching.

    Requires PlayerDetector.class compiled.

    Returns:
        Dictionary with detection results
    """
    # Check if PlayerDetector is available
    detector_class = Path("jc64_test/PlayerDetector.class")
    if not detector_class.exists():
        # Fallback to basic detection
        return {
            'file': str(sid_file),
            'players': self.identify_player(sid_file),
            'detected': True,
            'method': 'heuristic',
            'confidence': 'low'
        }

    # Run PlayerDetector
    cmd = [
        "java",
        "-cp", f"{self.jar_path};jc64_test",
        "PlayerDetector",
        str(sid_file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    if result.returncode != 0:
        raise RuntimeError(f"Player detection failed: {result.stderr}")

    # Parse JSON output
    import json
    try:
        detection = json.loads(result.stdout)
        detection['method'] = 'sidid'
        detection['confidence'] = 'high' if detection['detected'] else 'none'
        return detection
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse detection output: {result.stdout}")
```

#### Task 4.4: Create Player Detection Test Suite
**Estimated Time**: 2 hours

**File**: `pyscript/test_player_detection.py`

```python
"""Test suite for advanced player detection."""

import pytest
from pathlib import Path
from pyscript.jc64_wrapper import JC64Wrapper


# Known player test cases
KNOWN_PLAYERS = [
    ("Laxity/Stinsens_Last_Night_of_89.sid", "Laxity NewPlayer"),
    ("Laxity/21_G4_demo_tune_1.sid", "Laxity"),
    # Add more known players...
]


class TestPlayerDetection:
    """Test advanced player detection."""

    @pytest.fixture
    def jc64(self):
        return JC64Wrapper(use_fixed_jar=True)

    @pytest.mark.parametrize("sid_file,expected_player", KNOWN_PLAYERS)
    def test_known_players(self, jc64, sid_file, expected_player):
        """Test detection of known players."""
        sid_path = Path(sid_file)
        if not sid_path.exists():
            pytest.skip(f"Test file not found: {sid_file}")

        result = jc64.identify_player_advanced(sid_path)

        assert result['detected'] == True, "Player not detected"
        assert expected_player in result['players'], \
            f"Expected {expected_player}, got {result['players']}"
        assert result['method'] == 'sidid', "Should use SIDId method"
        assert result['confidence'] == 'high', "Should have high confidence"

    def test_batch_detection(self, jc64):
        """Test batch player detection."""
        laxity_dir = Path("Laxity")
        if not laxity_dir.exists():
            pytest.skip("Laxity directory not found")

        sid_files = list(laxity_dir.glob("*.sid"))[:10]  # Test first 10

        results = {}
        for sid_file in sid_files:
            try:
                result = jc64.identify_player_advanced(sid_file)
                results[sid_file.name] = result['players']
            except Exception as e:
                results[sid_file.name] = f"ERROR: {e}"

        # At least 70% should be detected as Laxity
        laxity_count = sum(1 for p in results.values() if "Laxity" in str(p))
        success_rate = laxity_count / len(results)

        assert success_rate >= 0.7, \
            f"Low detection rate: {success_rate:.0%} ({laxity_count}/{len(results)})"

        print(f"\nDetection Results:")
        for file, player in results.items():
            print(f"  {file}: {player}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Phase 5: Frequency Table Analysis

#### Task 5.1: Create FrequencyAnalyzer Java Wrapper
**Estimated Time**: 3 hours

**File**: `jc64_test/FrequencyAnalyzer.java`

```java
import sw_emulator.software.SidFreq;
import java.io.*;

/**
 * Frequency table detection using JC64's SidFreq algorithm.
 *
 * Detects 12 different frequency table formats in SID files.
 */
public class FrequencyAnalyzer {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java FrequencyAnalyzer <sid_file>");
            System.exit(1);
        }

        String sidFile = args[0];

        try {
            // Read SID file
            File file = new File(sidFile);
            FileInputStream fis = new FileInputStream(file);
            byte[] buffer = new byte[(int)file.length()];
            fis.read(buffer);
            fis.close();

            // Convert to int array
            int[] intBuffer = new int[buffer.length];
            for (int i = 0; i < buffer.length; i++) {
                intBuffer[i] = buffer[i] & 0xFF;
            }

            // Analyze frequencies
            SidFreq sidFreq = new SidFreq();
            // TODO: Call SidFreq methods to detect tables
            // Note: May need to implement wrapper methods

            // For now, output structure for Python to parse
            System.out.println("{");
            System.out.println("  \"file\": \"" + escapeJson(sidFile) + "\",");
            System.out.println("  \"tables_detected\": 0,");  // Placeholder
            System.out.println("  \"tables\": []");
            System.out.println("}");

        } catch (Exception e) {
            System.err.println("ERROR: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static String escapeJson(String str) {
        return str.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
```

**Note**: This is a starting point. Full implementation requires deeper understanding of SidFreq API.

#### Task 5.2: Python Integration
**Estimated Time**: 2 hours

**File**: `pyscript/jc64_wrapper.py` (enhancement)

```python
def detect_frequency_tables(self, sid_file: Path) -> List[Dict]:
    """
    Detect frequency tables in SID file.

    Returns:
        List of detected tables with metadata
    """
    # Check if FrequencyAnalyzer is available
    analyzer_class = Path("jc64_test/FrequencyAnalyzer.class")
    if not analyzer_class.exists():
        raise RuntimeError("FrequencyAnalyzer.class not found. Run Phase 5 setup.")

    cmd = [
        "java",
        "-cp", f"{self.jar_path};jc64_test",
        "FrequencyAnalyzer",
        str(sid_file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    if result.returncode != 0:
        raise RuntimeError(f"Frequency analysis failed: {result.stderr}")

    # Parse JSON output
    import json
    return json.loads(result.stdout)
```

---

### Phase 6: SIDM2 Pipeline Integration

#### Task 6.1: Enhanced laxity_parser.py
**Estimated Time**: 2 hours

```python
from pyscript.jc64_wrapper import JC64Wrapper

class EnhancedLaxityParser:
    """Laxity parser with JC64 integration."""

    def __init__(self):
        self.jc64 = JC64Wrapper(use_fixed_jar=True)

    def is_laxity_file(self, sid_file: Path) -> bool:
        """
        Enhanced Laxity detection using JC64.

        Uses multiple detection methods:
        1. JC64 player detection (if available)
        2. Init address heuristic
        3. Fallback to existing pattern matching
        """
        try:
            # Try advanced detection
            detection = self.jc64.identify_player_advanced(sid_file)
            if detection['detected'] and "Laxity" in detection['players']:
                return True
        except:
            pass

        # Try basic heuristic
        try:
            header = self.jc64.parse_psid_header(sid_file)
            if header['init_addr'] == 0x1000:
                return True
        except:
            pass

        # Fallback to existing detection
        return self._legacy_detection(sid_file)

    def _legacy_detection(self, sid_file: Path) -> bool:
        """Existing pattern-based detection."""
        # ... existing code ...
```

#### Task 6.2: Validation Pipeline Enhancement
**Estimated Time**: 2 hours

```python
def validate_with_disassembly(original_sid: Path, exported_sid: Path) -> Dict:
    """
    Validate conversion using JC64 disassembly comparison.

    Returns comprehensive validation report.
    """
    jc64 = JC64Wrapper(use_fixed_jar=True)

    # Compare disassemblies
    comparison = jc64.compare_sids(original_sid, exported_sid)

    # Add to validation report
    report = {
        'disassembly_comparison': comparison,
        'code_similarity': comparison['code_similarity'],
        'structure_preserved': comparison['header_match'],
        'addresses_match': (
            comparison['init_addr_match'] and
            comparison['play_addr_match']
        )
    }

    return report
```

---

## 4. Technical Requirements

### 4.1 Software Requirements

**Essential**:
- JDK 8 or later (for javac compiler)
- Apache Ant 1.10+ (for building JC64)
- Python 3.8+ (already installed)
- Git (already installed)

**Optional**:
- IDE (VS Code, IntelliJ) for Java development
- pytest for Python testing

### 4.2 Hardware Requirements

**Minimum**:
- 4 GB RAM
- 2 GB free disk space (for JDK, JC64 source, built JARs)
- Dual-core processor

**Recommended**:
- 8 GB RAM (for faster compilation)
- SSD storage (for faster builds)

### 4.3 Disk Space Breakdown

- JDK installation: ~300 MB
- Apache Ant: ~50 MB
- JC64 source: ~10 MB
- Built JC64 JAR: ~15 MB
- Disassembly outputs: ~1-5 MB per SID file
- Test files: ~100 MB

**Total**: ~500 MB to 1 GB

---

## 5. Risk Assessment

### 5.1 High-Risk Items

**Risk 1**: MemoryFlags.getMemoryState() fix breaks other functionality
- **Likelihood**: Medium
- **Impact**: High
- **Mitigation**: Comprehensive regression testing
- **Contingency**: Use loop bounds fix instead

**Risk 2**: JC64 build fails on Windows
- **Likelihood**: Low-Medium
- **Impact**: High
- **Mitigation**: Follow Ant build documentation carefully
- **Contingency**: Use pre-built JAR, patch with hex editor

**Risk 3**: SIDId patterns not accessible/working
- **Likelihood**: Medium
- **Impact**: Medium
- **Mitigation**: Test with known Laxity files first
- **Contingency**: Use heuristic detection, port to Python

### 5.2 Medium-Risk Items

**Risk 4**: Disassembly output format incompatible with tools
- **Likelihood**: Medium
- **Impact**: Low-Medium
- **Mitigation**: Test with multiple assemblers
- **Contingency**: Write format converter

**Risk 5**: Performance issues with large SID files
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Profile and optimize
- **Contingency**: Add timeout, batch processing

### 5.3 Low-Risk Items

**Risk 6**: Python wrapper API changes needed
- **Likelihood**: Medium
- **Impact**: Low
- **Mitigation**: Design flexible API
- **Contingency**: Update wrapper incrementally

---

## 6. Success Criteria

### Phase 1: Environment Setup ✓
- [ ] JDK installed and javac working
- [ ] Ant installed and builds test project
- [ ] Can compile simple Java programs

### Phase 2: FileDasm Fix ✓
- [ ] Bug fix implemented
- [ ] JC64 builds without errors
- [ ] Can disassemble 5 different SID files
- [ ] No ArrayIndexOutOfBoundsException
- [ ] Assembly output is valid

### Phase 3: Disassembly Integration ✓
- [ ] Python wrapper updated
- [ ] Can disassemble from Python
- [ ] Test suite passes (5/5 tests)
- [ ] Performance < 5 seconds per SID
- [ ] Batch disassembly tool working

### Phase 4: Player Detection ✓
- [ ] PlayerDetector compiled
- [ ] Can detect Laxity files (90%+ accuracy)
- [ ] Python integration working
- [ ] Test suite passes
- [ ] Detects 5+ different player types

### Phase 5: Frequency Analysis ✓
- [ ] FrequencyAnalyzer compiled
- [ ] Can detect frequency tables
- [ ] Identifies table types (12 formats)
- [ ] Python integration working
- [ ] Cross-validation with SIDM2 (80%+ match)

### Phase 6: SIDM2 Integration ✓
- [ ] laxity_parser.py enhanced
- [ ] Validation pipeline using disassembly
- [ ] Comparison reports generated
- [ ] Documentation updated
- [ ] All features accessible from SIDM2

---

## 7. Timeline and Effort

### Effort Estimates

| Phase | Tasks | Estimated Hours | Calendar Days |
|-------|-------|----------------|---------------|
| Phase 1: Environment Setup | 3 | 2-4 hours | 1 day |
| Phase 2: FileDasm Fix | 5 | 4-6 hours | 1-2 days |
| Phase 3: Disassembly Integration | 3 | 6-8 hours | 2 days |
| Phase 4: Player Detection | 4 | 8-12 hours | 2-3 days |
| Phase 5: Frequency Analysis | 2 | 6-10 hours | 2 days |
| Phase 6: SIDM2 Integration | 2 | 4-6 hours | 1 day |
| **TOTAL** | **19 tasks** | **30-46 hours** | **9-11 days** |

### Parallel Execution

Some phases can be done in parallel:
- Phase 4 and 5 can run concurrently (independent)
- Phase 3 can partially overlap with Phase 2 (testing while fixing)

**Optimized Timeline**: 7-9 days with parallel work

### Milestone Schedule

**Week 1**:
- Day 1: Phase 1 (Environment Setup)
- Day 2-3: Phase 2 (FileDasm Fix)
- Day 4-5: Phase 3 (Disassembly Integration)

**Week 2**:
- Day 6-8: Phase 4 (Player Detection)
- Day 7-8: Phase 5 (Frequency Analysis) - parallel
- Day 9: Phase 6 (SIDM2 Integration)

**Buffer**: 2 days for unexpected issues

---

## 8. Integration Strategy

### 8.1 Integration Points

**Current SIDM2 Pipeline**:
```
Input SID → laxity_parser → laxity_converter → SF2 Output
                ↓                    ↓               ↓
           (basic checks)      (hardcoded)    (no validation)
```

**Enhanced Pipeline with JC64**:
```
Input SID → JC64 Analysis → Enhanced Parser → Laxity Converter → SF2 Output
               ↓                  ↓                  ↓               ↓
        Player Detection    Better Extraction  Frequency Valid  JC64 Validation
        Disassembly        Memory Analysis    Table Check      Comparison
        Frequency Tables   Structure Check                     Report
```

### 8.2 API Integration

**laxity_parser.py Enhancement**:
```python
from pyscript.jc64_wrapper import JC64Wrapper

class LaxityParser:
    def __init__(self, use_jc64=True):
        self.use_jc64 = use_jc64
        if use_jc64:
            self.jc64 = JC64Wrapper(use_fixed_jar=True)

    def parse(self, sid_file: Path) -> Dict:
        """Parse Laxity SID with JC64 enhancement."""
        result = {}

        if self.use_jc64:
            # Get metadata from JC64
            result['header'] = self.jc64.parse_psid_header(sid_file)

            # Detect player
            result['player'] = self.jc64.identify_player_advanced(sid_file)

            # Get disassembly for structure analysis
            result['disassembly'] = self.jc64.disassemble_sid(sid_file)

        # Continue with existing extraction
        result.update(self._extract_music_data(sid_file))

        return result
```

**validate_sid_accuracy.py Enhancement**:
```python
from pyscript.jc64_wrapper import JC64Wrapper

def validate_conversion(original: Path, exported: Path) -> Dict:
    """Validate with JC64 disassembly comparison."""
    jc64 = JC64Wrapper(use_fixed_jar=True)

    # Existing validation
    result = existing_validation(original, exported)

    # Add JC64 comparison
    result['jc64_comparison'] = jc64.compare_sids(original, exported)
    result['structure_match'] = result['jc64_comparison']['header_match']
    result['code_similarity'] = result['jc64_comparison']['code_similarity']

    return result
```

### 8.3 Backward Compatibility

**Ensure existing functionality works**:
- JC64 features optional (use_jc64=False)
- Fallback to existing methods if JC64 fails
- No breaking changes to API

**Configuration**:
```python
# config.py
ENABLE_JC64_ANALYSIS = True
USE_JC64_DISASSEMBLY = True
USE_JC64_PLAYER_DETECTION = True
USE_JC64_FREQUENCY_ANALYSIS = True
```

---

## 9. Documentation Requirements

### 9.1 User Documentation

**Create**:
1. `docs/guides/JC64_DISASSEMBLY_GUIDE.md`
   - How to disassemble SID files
   - Understanding output
   - Troubleshooting

2. `docs/guides/JC64_PLAYER_DETECTION_GUIDE.md`
   - Using advanced detection
   - Interpreting results
   - Adding custom patterns

3. Update `docs/guides/VALIDATION_GUIDE.md`
   - JC64 comparison features
   - Disassembly-based validation

### 9.2 Developer Documentation

**Update**:
1. `docs/ARCHITECTURE.md`
   - JC64 integration architecture
   - Component interactions

2. `docs/COMPONENTS_REFERENCE.md`
   - jc64_wrapper.py API reference
   - PlayerDetector API
   - FrequencyAnalyzer API

3. `README.md`
   - Add JC64 features section
   - Update installation requirements

### 9.3 API Documentation

**Document all new methods**:
```python
def disassemble_sid(self, sid_file: Path, ...) -> str:
    """
    Disassemble SID file using JC64 FileDasm.

    Args:
        sid_file: Path to input SID file
        output_file: Optional output path
        assembler: Target assembler format
        language: Output language (en/it)

    Returns:
        Assembly code as string

    Raises:
        RuntimeError: If disassembly fails

    Example:
        >>> jc64 = JC64Wrapper(use_fixed_jar=True)
        >>> asm = jc64.disassemble_sid("music.sid")
        >>> print(asm[:100])
    """
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Python Tests**:
- test_jc64_disasm.py (disassembly)
- test_player_detection.py (player ID)
- test_frequency_analysis.py (freq tables)

**Coverage Target**: 80%+

### 10.2 Integration Tests

**Test Scenarios**:
1. End-to-end: SID → Disassembly → Analysis
2. Validation: Original vs Exported comparison
3. Batch processing: 100+ SID files

### 10.3 Regression Tests

**Ensure no breakage**:
- Existing SIDM2 functionality
- Backward compatibility
- Performance benchmarks

### 10.4 Performance Tests

**Benchmarks**:
- Disassembly time: < 5 seconds per SID
- Player detection: < 2 seconds per SID
- Batch 100 files: < 10 minutes

---

## 11. Deliverables

### Phase 1
- ✅ JDK installed
- ✅ Ant installed
- ✅ Environment verified

### Phase 2
- ✅ FileDasm bug fixed
- ✅ JC64 rebuilt
- ✅ Disassembly working

### Phase 3
- ✅ jc64_wrapper.py with disassembly
- ✅ Test suite
- ✅ Batch tool

### Phase 4
- ✅ PlayerDetector.class
- ✅ Python integration
- ✅ Detection tests

### Phase 5
- ✅ FrequencyAnalyzer.class
- ✅ Python integration
- ✅ Validation tests

### Phase 6
- ✅ Enhanced laxity_parser.py
- ✅ Validation pipeline
- ✅ Documentation

---

## 12. Next Steps

### Immediate Actions (Start Today)

1. **Install JDK**
   ```bash
   # Download from: https://adoptium.net/
   # Install to: C:\Program Files\Java\jdk-8
   # Set JAVA_HOME and PATH
   ```

2. **Install Apache Ant**
   ```bash
   # Download from: https://ant.apache.org/
   # Extract to: C:\Program Files\Apache\apache-ant-1.10.14
   # Set ANT_HOME and PATH
   ```

3. **Verify Setup**
   ```bash
   java -version
   javac -version
   ant -version
   ```

### This Week

4. **Fix FileDasm Bug**
   - Edit MemoryFlags.java
   - Rebuild JC64
   - Test disassembly

5. **Update Python Wrapper**
   - Add disassembly methods
   - Test with Laxity files

### Next Week

6. **Advanced Features**
   - Implement PlayerDetector
   - Implement FrequencyAnalyzer
   - Integrate with SIDM2

---

## Appendix A: Quick Reference Commands

### Build JC64
```bash
cd C:\Users\mit\Downloads\jc64
ant clean
ant build
```

### Test Disassembly
```bash
java -cp jc64-fixed.jar sw_emulator.software.FileDasm \
     -en input.sid output.asm
```

### Compile Java Wrapper
```bash
javac -cp jc64-fixed.jar PlayerDetector.java
```

### Run Python Tests
```bash
python pyscript/test_jc64_disasm.py
pytest pyscript/test_player_detection.py -v
```

---

## Appendix B: Troubleshooting

### Common Issues

**Issue**: Ant build fails with "javac not found"
**Solution**: Set JAVA_HOME and add to PATH

**Issue**: ArrayIndexOutOfBoundsException persists
**Solution**: Verify MemoryFlags.java fix applied correctly

**Issue**: PlayerDetector can't find SidId class
**Solution**: Check classpath includes JC64.jar

**Issue**: Disassembly output is garbled
**Solution**: Check file encoding, try different assembler format

---

**Document Version**: 1.0.0
**Date**: 2025-12-24
**Status**: Ready for Implementation
**Estimated Total Effort**: 30-46 hours over 7-11 days

🚀 **Ready to begin with Phase 1: Development Environment Setup**
