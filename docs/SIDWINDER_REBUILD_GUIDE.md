# SIDwinder Rebuild Guide

## Overview

SIDwinder trace functionality has been **fixed in source code** but requires rebuilding the executable.

**Current Status:**
- ✅ Source code patched (all 3 files)
- ✅ Integrated into pipeline (Step 6)
- ⚠️ **Needs rebuild to activate** - trace files currently only show "FRAME: " markers
- 🔧 Patch location: `tools/sidwinder_trace_fix.patch`

**Problem:** Trace files contain only `FRAME: ` markers without SID register write data
**Cause:** Executable (`tools/SIDwinder.exe`) is from before patches were applied
**Solution:** Rebuild SIDwinder.exe from patched source code (requires CMake)

---

## Step 1: Install CMake

### Option A: CMake Installer (Recommended)

1. **Download CMake**:
   - Visit: https://cmake.org/download/
   - Download: "Windows x64 Installer" (cmake-3.x.x-windows-x86_64.msi)
   - Current version: 3.28+ (any 3.10+ works)

2. **Run Installer**:
   - Double-click the downloaded `.msi` file
   - **IMPORTANT:** Select "Add CMake to system PATH for all users" or "...for current user"
   - Complete installation

3. **Verify Installation**:
   ```cmd
   # Open NEW command prompt (must be new to load PATH)
   cmake --version

   # Should output:
   # cmake version 3.x.x
   ```

### Option B: Visual Studio (Includes CMake)

If you have Visual Studio 2019 or later:

1. Open **Visual Studio Installer**
2. Click **Modify** on your VS installation
3. Under **Workloads**, ensure these are checked:
   - ✅ Desktop development with C++
4. Under **Individual Components**, ensure:
   - ✅ C++ CMake tools for Windows
5. Click **Modify** to install

CMake will be available at:
```
C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe
```

### Option C: Chocolatey (Package Manager)

```cmd
# Install Chocolatey first (if not installed)
# Visit: https://chocolatey.org/install

# Then install CMake
choco install cmake --installargs 'ADD_CMAKE_TO_PATH=System'
```

### Option D: Scoop (Package Manager)

```cmd
# Install Scoop first (if not installed)
# Visit: https://scoop.sh/

# Then install CMake
scoop install cmake
```

---

## Step 2: Install C++ Compiler

CMake requires a C++ compiler. Choose ONE:

### Option A: Visual Studio Build Tools (Recommended)

**Free**, official Microsoft compiler:

1. Download: https://visualstudio.microsoft.com/downloads/
2. Under "Tools for Visual Studio", download **Build Tools for Visual Studio**
3. Run installer
4. Select: **C++ build tools**
5. Install (requires ~7GB disk space)

### Option B: Visual Studio Community (Full IDE)

**Free** for personal/open-source use:

1. Download: https://visualstudio.microsoft.com/vs/community/
2. During installation, select:
   - ✅ Desktop development with C++
3. Install

### Option C: MinGW-w64

**Lightweight** alternative:

1. Download: https://www.mingw-w64.org/downloads/
2. Recommended: Use MSYS2 installer
   - Download from: https://www.msys2.org/
   - Run installer
   - Open MSYS2 terminal
   - Install MinGW-w64:
     ```bash
     pacman -S mingw-w64-x86_64-toolchain
     ```
3. Add to PATH:
   - `C:\msys64\mingw64\bin`

---

## Step 3: Verify Build Environment

After installing CMake and a C++ compiler, verify everything is ready:

```cmd
# Check CMake (MUST work)
cmake --version

# Check C++ compiler (at least ONE must work)
cl          # Visual Studio compiler
g++         # MinGW/GCC compiler
clang++     # Clang compiler

# If all fail, revisit Step 2 to install a compiler
```

---

## Step 4: Rebuild SIDwinder

### Method 1: Using build.bat (Easiest)

```cmd
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6

# Run the build script
build.bat

# Copy new executable
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\SIDwinder.exe
```

### Method 2: Manual CMake Build

```cmd
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6

# Create build directory
mkdir build
cd build

# Configure (choose one):
cmake ..                                    # Auto-detect compiler
cmake -G "Visual Studio 16 2019" ..        # VS 2019
cmake -G "Visual Studio 17 2022" ..        # VS 2022
cmake -G "MinGW Makefiles" ..              # MinGW

# Build
cmake --build . --config Release

# Copy executable
copy Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\SIDwinder.exe
```

### Method 3: Visual Studio IDE

1. Open Visual Studio
2. File → Open → CMake → Select `CMakeLists.txt`
3. Build → Build All
4. Copy from `build\Release\SIDwinder.exe`

---

## Verification

After rebuilding, test the trace functionality:

```bash
# Test trace generation
tools/SIDwinder.exe -trace=test.txt SID/Angular.sid

# Check if file has content (should be ~500KB+)
ls -lh test.txt

# View first few lines (should show register writes)
head -50 test.txt
```

**Expected output:**
```
FRAME: D400:$29,D401:$FD,D404:$11,D405:$03,D406:$F8,...
FRAME: D400:$7B,D401:$05,D404:$41,...
FRAME: ...
```

---

## What Was Fixed

### Bug #1: Callback Not Enabled
**File:** `SIDEmulator.cpp` line 129

**Before:**
```cpp
if (options.registerTrackingEnabled || options.patternDetectionEnabled) {
```

**After:**
```cpp
if (options.registerTrackingEnabled || options.patternDetectionEnabled || options.traceEnabled) {
```

### Bug #2: Missing logWrite() Method
**Files:** `TraceLogger.h` + `TraceLogger.cpp`

**Added to header:**
```cpp
void logWrite(u16 addr, u8 value);
```

**Added to implementation:**
```cpp
void TraceLogger::logWrite(u16 addr, u8 value) {
    if (!isOpen_) return;
    if (format_ == TraceFormat::Text) {
        writeTextRecord(addr, value);
    } else {
        TraceRecord record(addr, value);
        writeBinaryRecord(record);
    }
}
```

### Bug #3: Missing Trace Call in Callback
**File:** `SIDEmulator.cpp` lines 52-55

**Added:**
```cpp
// Log to trace file if tracing is enabled
if (options.traceEnabled && traceLogger_) {
    traceLogger_->logWrite(addr, value);
}
```

---

## Pipeline Integration

Once rebuilt, the pipeline will automatically:

1. Generate traces for original SID (30 seconds)
2. Generate traces for exported SID (30 seconds)
3. Save as `.txt` files in text format
4. Compare with siddump output for validation

**Files generated:**
- `output/{filename}/Original/{filename}_original.txt`
- `output/{filename}/New/{filename}_exported.txt`

---

## Troubleshooting

### "cmake not found"
Install CMake: https://cmake.org/download/

Add to PATH or use full path:
```cmd
"C:\Program Files\CMake\bin\cmake.exe" ..
```

### "No CMAKE_CXX_COMPILER could be found"
Install Visual Studio with C++ support, or install MinGW.

### Build succeeds but trace still fails
Ensure you copied the NEW executable:
```cmd
# Check version
tools/SIDwinder.exe --help | head -1
# Should show: SIDwinder 0.2.6

# Check file timestamp (should be recent)
ls -l tools/SIDwinder.exe
```

### Trace file empty or only has frames
The old (unpatched) executable is still being used. Verify:
1. Build succeeded
2. Copied from correct location
3. No other SIDwinder.exe in PATH taking precedence

---

## Alternative: Pre-built Binary

If you cannot rebuild, you can:

1. **Request pre-built binary** from SIDwinder author
2. **Use siddump instead** (already works perfectly)
3. **Wait for official SIDwinder update** with fix

The pipeline works fine without trace - it just shows warnings for those steps.

---

## Summary

| Component | Status |
|-----------|--------|
| Source patches | ✅ Applied |
| Pipeline integration | ✅ Complete |
| Documentation | ✅ Updated |
| Executable rebuild | ⚠️ **YOU MUST DO THIS** |
| Testing | ⏳ After rebuild |

**Next step:** Run `build.bat` to activate trace functionality!
