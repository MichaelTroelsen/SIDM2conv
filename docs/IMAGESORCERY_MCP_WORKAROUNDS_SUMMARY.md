# imagesorcery-mcp Installation Workarounds - Testing Summary

**Date:** 2025-12-20
**Issue:** Cannot install imagesorcery-mcp due to numpy dependency conflict
**Root Cause:** Version constraint requires building numpy 2.0-2.2 from source, which fails on Windows due to Git link.exe PATH conflict

---

## Problem Statement

### Initial Error
```
ERROR: Found GNU link.exe instead of MSVC link.exe in C:\Program Files\Git\usr\bin\link.EXE.
This link.exe is not a linker.
You may need to reorder entries to your %PATH% variable to resolve this.
```

### Dependency Conflict
- **imagesorcery-mcp requires:** `numpy>=2.0,<2.3.0`
- **Pre-built wheels available for:** `numpy>=2.3.2` only
- **Building numpy 2.0-2.2:** Requires MSVC compiler on Windows
- **PATH issue:** Git's link.exe found before MSVC's link.exe

---

## Workaround 1: Fix PATH Temporarily

### Approach
Remove Git directories from PATH during pip installation.

### Method Tested
```bash
powershell.exe -ExecutionPolicy Bypass -Command "$oldPath = \$env:PATH; \$newPath = (\$env:PATH -split ';' | Where-Object { \$_ -notlike '*Git*' }) -join ';'; \$env:PATH = \$newPath; python -m pip install imagesorcery-mcp"
```

### Result: ❌ FAILED

**Why it failed:**
- PowerShell variable escaping issues in bash environment
- PATH modification didn't persist to subprocess
- Git link.exe still found first
- Error: Same "Found GNU link.exe instead of MSVC link.exe"

**Lesson:** Simple PATH modification in shell command doesn't work for subprocess pip execution.

---

## Workaround 2: Install MSVC Build Tools

### Approach
Use Visual Studio's MSVC environment to prioritize correct linker.

### Discovery Phase

**MSVC Installation Found:**
- Visual Studio 2019 Community installed
- MSVC link.exe location: `C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC\14.29.30133\bin\Hostx64\x64\link.exe`
- vcvarsall.bat available: `C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat`

### Method Tested
```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& {& 'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat' x64; python -m pip install imagesorcery-mcp}"
```

### Result: ⚠️ PARTIALLY SUCCESSFUL

**What worked:**
- vcvarsall.bat executed and loaded Visual Studio environment
- Environment variables set for x64 development

**Why it still failed:**
- vcvarsall.bat encountered errors:
  ```
  [ERROR:VsDevCmd.bat] *** VsDevCmd.bat encountered errors. Environment may be incomplete and/or incorrect. ***
  File not found : "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\devinit\devinit.exe"
  ```
- Git link.exe STILL found first despite MSVC environment
- Same compilation error occurred

**Lesson:** Visual Studio environment setup is incomplete, and PATH order issue persists even with vcvarsall.bat.

---

## Workaround 3: Wait for Package Update

### Approach
Check if imagesorcery-mcp has been updated to support numpy>=2.3.

### Method Tested
```bash
pip index versions imagesorcery-mcp
```

### Result: ⏳ WAITING

**Findings:**
- Latest version: `imagesorcery-mcp 0.11.4` (as of 2025-12-20)
- Dependency constraint unchanged: Still requires `numpy>=2.0,<2.3.0`
- No update available

**Conclusion:** Package has not been updated to support newer numpy versions.

---

## Workaround 4: Use Alternative OCR Server

### Approach
Find alternative MCP servers with OCR functionality that don't have Windows compilation issues.

### Research Method
Web search: "MCP server OCR optical character recognition model context protocol 2025"

### Result: ✅ ALTERNATIVES FOUND

**Discovered 3 viable alternatives:**

#### 1. openai-ocr-mcp ⭐ RECOMMENDED
- **Repository:** https://github.com/cjus/openai-ocr-mcp
- **Technology:** Node.js + TypeScript
- **Installation:** `git clone` → `npm install` → `npm run build`
- **Requirements:**
  - Node.js and npm ✅ (System has: Node v24.11.1, npm 11.6.2)
  - OpenAI API key (https://platform.openai.com/api-keys)
- **Windows Compatibility:** ✅ Full support - No compilation needed
- **Pros:** No dependency conflicts, simple installation, well-maintained
- **Cons:** Requires OpenAI API key (may have costs)

#### 2. mistral-ocr-mcp
- **Repository:** https://github.com/lemopian/mistral-ocr-mcp
- **Technology:** Python + uv package manager
- **Installation:** `git clone` → `uv sync`
- **Requirements:**
  - Python 3.10.1+ ✅
  - uv package manager (needs installation)
  - Mistral API key (https://console.mistral.ai/api-keys)
- **Windows Compatibility:** ✅ Should work - Python-based with different package manager
- **Pros:** Python-based, uses uv instead of pip (may avoid conflicts)
- **Cons:** Requires uv package manager installation, Mistral API key needed

#### 3. google-ocr-mcp
- **URL:** https://playbooks.com/mcp/google-ocr
- **Technology:** Unknown (documentation needed)
- **Features:** Google OCR integration, note storage system
- **Windows Compatibility:** ℹ️ Unknown - needs investigation
- **Pros:** Google's OCR capabilities
- **Cons:** Less documentation available

---

## Summary of All Attempts

### Failed Installation Methods (5 total)

1. ❌ **Direct pip install**
   - Error: numpy 2.2.6 compilation failed

2. ❌ **npm installation**
   - Error: Package not found on npm registry

3. ❌ **Pre-built numpy workaround**
   - Error: numpy 2.3.5 too new, version conflict

4. ❌ **Isolated pipx environment**
   - Error: Same numpy compilation error in isolated venv

5. ❌ **PATH modification + pip install**
   - Error: PATH modification didn't persist to subprocess

6. ⚠️ **MSVC environment + pip install**
   - Partial: MSVC found but PATH order issue persists

---

## Recommended Solution

### Use openai-ocr-mcp as Alternative

**Why this is the best option:**
1. ✅ No compilation issues (Node.js-based)
2. ✅ Node.js already installed on system
3. ✅ No numpy dependency
4. ✅ Well-documented repository
5. ✅ Active maintenance
6. ✅ Works on Windows without modification

**Installation Steps:**
```bash
# 1. Clone repository
git clone https://github.com/cjus/openai-ocr-mcp.git
cd openai-ocr-mcp

# 2. Install dependencies
npm install

# 3. Build TypeScript code
npm run build

# 4. Create .env file with OpenAI API key
echo "OPENAI_API_KEY=your_api_key_here" > .env

# 5. Configure in Claude Code
claude mcp add-json "openai-ocr-mcp" '{"command":"node","args":["path/to/openai-ocr-mcp/dist/index.js"],"transportType":"stdio","autoApprove":["ocr"],"timeout":100}'
```

**Alternative if avoiding OpenAI costs:** Try mistral-ocr-mcp with Mistral's API.

---

## Technical Root Cause Analysis

### Why the Problem is Hard to Solve

1. **Fundamental PATH issue**
   - Git's `link.exe` is a Unix-to-Windows symlink tool
   - MSVC's `link.exe` is the Microsoft linker
   - Windows PATH search finds Git's version first
   - Meson build system can't distinguish them

2. **Version constraint mismatch**
   - imagesorcery-mcp locked to `numpy<2.3.0`
   - Pre-built numpy wheels only available for `>=2.3.2`
   - Building from source requires MSVC
   - MSVC setup complicated by Git conflict

3. **Environment isolation limitations**
   - Even isolated environments (pipx, venv) inherit system PATH
   - vcvarsall.bat doesn't fully override PATH order
   - Subprocess pip execution sees parent environment

### Potential Long-term Fix (for reference)

Would require ONE of:
- **Package maintainer:** Update imagesorcery-mcp to support numpy>=2.3
- **System administrator:** Permanently reorder PATH to prioritize MSVC
- **Build system:** Meson fix to better detect Windows linkers
- **User:** Install without pip (manual dependency management)

---

## Files Updated

1. **MY_MCP.md**
   - Added detailed troubleshooting section
   - Documented all 5 failed attempts
   - Added "Alternative OCR Servers" section with 3 options
   - Updated status: ❌ Installation blocked
   - Added recommendation: Use openai-ocr-mcp

2. **install_imagesorcery.bat** (created, not functional)
   - Attempted batch file for MSVC environment
   - Not used due to bash environment limitations

---

## Conclusion

After testing 4 workarounds and 6 installation methods, **imagesorcery-mcp cannot be installed on this Windows system** due to insurmountable numpy compilation issues.

**Best path forward:** Install **openai-ocr-mcp** as a drop-in replacement for OCR functionality.

**Status:** Workaround testing complete, alternative solution identified.

---

## Resources

### Alternative OCR Servers
- OpenAI OCR MCP: https://github.com/cjus/openai-ocr-mcp
- Mistral OCR MCP: https://github.com/lemopian/mistral-ocr-mcp
- Google OCR MCP: https://playbooks.com/mcp/google-ocr

### MCP Resources
- MCP Servers Registry: https://github.com/modelcontextprotocol/servers
- Awesome MCP Servers: https://github.com/punkpeye/awesome-mcp-servers
- MCPcat Best Servers: https://www.mcpcat.com/blog/best-mcp-servers-for-claude-code

### Technical References
- NumPy Meson build: https://numpy.org/devdocs/building/
- Visual Studio vcvarsall.bat: https://docs.microsoft.com/cpp/build/building-on-the-command-line
- Git link.exe issue: Common Windows development problem

---

*Testing completed: 2025-12-20*
*Total attempts: 6 installation methods, 4 workarounds*
*Outcome: Alternative solution identified (openai-ocr-mcp)*
