# SIDM2 Documentation Index

**Quick navigation to all project documentation**

**Last Updated**: 2025-12-07
**Version**: 0.7.0

---

## 📚 Core Documentation

Start here for general information:

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | **Main user guide** - Installation, usage, examples |
| [CLAUDE.md](../CLAUDE.md) | **AI assistant guide** - Project structure, conventions |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | **Contribution guidelines** - How to contribute |
| [TODO.md](../TODO.md) | **Project tasks** - Current and planned work |

---

## 🔍 Reference Documentation

Technical specifications and format details:

### SID & SF2 Formats
| Document | Content |
|----------|---------|
| [SID_FORMATS.md](reference/SID_FORMATS.md) | PSID/RSID and Laxity NewPlayer specifications |
| [SF2_FORMAT_SPEC.md](reference/SF2_FORMAT_SPEC.md) | Complete SF2 format specification |
| [DRIVER_REFERENCE.md](reference/DRIVER_REFERENCE.md) | All SF2 drivers (11-16, NP20) |
| [CONVERSION_STRATEGY.md](reference/CONVERSION_STRATEGY.md) | Laxity → SF2 mapping details |

### Player Analysis
| Document | Content |
|----------|---------|
| [STINSENS_PLAYER_DISASSEMBLY.md](reference/STINSENS_PLAYER_DISASSEMBLY.md) | Laxity NewPlayer v21 disassembly |
| [SF2_CLASSES.md](reference/SF2_CLASSES.md) | SF2 class structure reference |
| [sid-registers.md](reference/sid-registers.md) | SID chip register reference |

### Implementation Details
| Document | Content |
|----------|---------|
| [SF2_TO_SID_LIMITATIONS.md](reference/SF2_TO_SID_LIMITATIONS.md) | Known packer limitations |
| [WAVE_TABLE_PACKING.md](reference/WAVE_TABLE_PACKING.md) | Wave table packing details |
| [format-specification.md](reference/format-specification.md) | General SID file formats |

---

## 📖 Guides

Step-by-step guides and how-tos:

| Guide | Purpose |
|-------|---------|
| [SIDWINDER_GUIDE.md](guides/SIDWINDER_GUIDE.md) | **Complete SIDwinder integration guide** - Features, usage, rebuilding |
| [VALIDATION_GUIDE.md](guides/VALIDATION_GUIDE.md) | **Validation system guide** - Tools, workflows, accuracy |
| [DEVELOPER_GUIDE.md](guides/DEVELOPER_GUIDE.md) | **Development guide** - Setup, API, contributing *(to be created)* |

---

## 🔬 Analysis & Research

Technical analysis and findings:

| Document | Content |
|----------|---------|
| [TECHNICAL_ANALYSIS.md](analysis/TECHNICAL_ANALYSIS.md) | **Comprehensive technical analysis** - SF2, Laxity, Audio Quality |
| [ACCURACY_ROADMAP.md](analysis/ACCURACY_ROADMAP.md) | **Accuracy improvement plan** - Path to 99% accuracy |
| [PACK_STATUS.md](analysis/PACK_STATUS.md) | **Packer status** - SF2→SID implementation details |

---

## 📦 Archive

Historical reports and completed work:

| Directory | Content |
|-----------|---------|
| [archive/2025-12-06/](archive/2025-12-06/) | Pipeline execution reports from Dec 6, 2025 |
| [archive/](archive/) | Phase completion reports, validation findings |

---

## 🗂️ Auto-Generated

| Document | Purpose |
|----------|---------|
| [FILE_INVENTORY.md](FILE_INVENTORY.md) | Complete file inventory (auto-generated) |

---

## Quick Links by Task

### I want to...

**...convert a SID file**
→ Start with [README.md - Basic Conversion](../README.md#basic-conversion)

**...understand SF2 format**
→ Read [SF2_FORMAT_SPEC.md](reference/SF2_FORMAT_SPEC.md)

**...use SIDwinder**
→ See [SIDWINDER_GUIDE.md](guides/SIDWINDER_GUIDE.md)

**...validate conversion accuracy**
→ See [VALIDATION_GUIDE.md](guides/VALIDATION_GUIDE.md)

**...understand Laxity format**
→ Read [STINSENS_PLAYER_DISASSEMBLY.md](reference/STINSENS_PLAYER_DISASSEMBLY.md)

**...contribute code**
→ See [CONTRIBUTING.md](../CONTRIBUTING.md)

**...understand the codebase**
→ Read [CLAUDE.md](../CLAUDE.md)

**...improve accuracy**
→ See [ACCURACY_ROADMAP.md](analysis/ACCURACY_ROADMAP.md)

---

## Documentation Statistics

**Total Documentation Files**: ~25 (down from 46)

**Organization**:
- Core: 4 files (root)
- Reference: 9 files
- Guides: 2 files
- Analysis: 3 files
- Archive: 10+ files
- Auto-generated: 1 file

**Reduction**: 46 → 25 files (45% fewer files)

---

## Maintenance

To update the file inventory:
```bash
python scripts/update_inventory.py
```

---

**Document Status**: New simplified index (replaces COMPLETE_DOCUMENTATION_INDEX.md)
**Last Consolidation**: 2025-12-07
**Maintainer**: SIDM2 Project
