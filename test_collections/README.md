# SID Test Collections

**Purpose**: Test data for SID to SF2 converter validation and development
**Total Files**: 620+ SID files (~5.5 MB)
**Organization**: By composer/player format

---

## Collections

### Fun_Fun (20 files, 236 KB)
**Player**: Fun/Fun player format
**Content**: Various tunes using Fun/Fun player
- Classic demos and scene music
- Examples: Byte_Bite.sid, Dreamix.sid, Final_Luv.sid

### Galway_Martin (60+ files, 388 KB)
**Composer**: Martin Galway (legendary C64 composer)
**Content**: Classic game soundtracks
- Arkanoid, Combat School, Comic Bakery
- Green Beret, Match Day, Miami Vice
- MicroProse Soccer series
- Game Over, Hyper Sports, Highlander

### Hubbard_Rob (100+ files, 832 KB)
**Composer**: Rob Hubbard (legendary C64 composer)
**Content**: Classic game soundtracks from the master
- Games and demo music by one of the most influential C64 composers

### Laxity (286 files, 1.9 MB)
**Player**: Laxity NewPlayer v21
**Purpose**: Primary test collection for Laxity driver development
**Content**: Complete Laxity NewPlayer v21 collection
- Used for Laxity driver validation (v1.8.0)
- 100% conversion success rate validated
- 99.93% accuracy baseline

### Tel_Jeroen (150+ files, 2.1 MB)
**Composer**: Jeroen Tel (legendary C64 composer)
**Content**: Classic game soundtracks
- Robocop, Cybernoid, Supremacy, and many more
- Known for innovative sound design

### SIDSF2player (18 files, 172 KB)
**Purpose**: Round-trip validation test set
**Content**: Reference SF2-exported SID files
- Used for testing perfect round-trip conversion
- 100% accuracy baseline (SID→SF2→SID)

---

## Usage

### Testing with Collections

```bash
# Test single file from collection
python scripts/sid_to_sf2.py test_collections/Laxity/Stinsens_Last_Night_of_89.sid output.sf2 --driver laxity

# Batch convert entire collection
python scripts/convert_all.py test_collections/Laxity/ output/laxity_batch/

# Validate accuracy on collection
python scripts/run_validation.py --path test_collections/Laxity/
```

### Collection-Specific Drivers

- **Laxity/**: Use `--driver laxity` for 99.93% accuracy
- **SIDSF2player/**: Use `--driver driver11` or `--driver np20` for 100% accuracy
- **Others**: Use auto-detection or standard drivers

---

## Validation Results

### Laxity Collection (v1.8.0)
- **Files**: 286
- **Success Rate**: 100% (286/286)
- **Accuracy**: 99.93% frame accuracy
- **Conversion Speed**: 8.1 files/second
- **Status**: ✅ Production validated

### SIDSF2player Collection (v0.6.0+)
- **Files**: 18
- **Success Rate**: 100% (18/18)
- **Accuracy**: 100% (perfect round-trip)
- **Status**: ✅ Reference baseline

### Other Collections
- Used for format research and testing
- Various player formats and composers
- Validation in progress

---

## Adding New Collections

To add a new test collection:

1. Create subdirectory: `test_collections/CollectionName/`
2. Add SID files
3. Update this README with collection info
4. Run validation: `python scripts/run_validation.py --path test_collections/CollectionName/`
5. Document results

---

## File Organization

```
test_collections/
├── README.md (this file)
├── Fun_Fun/          # 20 files - Fun/Fun player
├── Galway_Martin/    # 60+ files - Martin Galway classics
├── Hubbard_Rob/      # 100+ files - Rob Hubbard classics
├── Laxity/           # 286 files - Laxity NewPlayer v21 (PRIMARY)
├── Tel_Jeroen/       # 150+ files - Jeroen Tel classics
└── SIDSF2player/     # 18 files - Round-trip validation (REFERENCE)
```

---

## Notes

- **Git Tracked**: All collections are version controlled
- **Total Size**: ~5.5 MB (acceptable for test data)
- **Primary Collection**: Laxity/ (used for v1.8.0 validation)
- **Reference Collection**: SIDSF2player/ (perfect accuracy baseline)
- **Research Collections**: Fun_Fun/, Galway_Martin/, Hubbard_Rob/, Tel_Jeroen/

---

## References

- Laxity driver validation: `docs/guides/LAXITY_DRIVER_USER_GUIDE.md`
- Validation system: `docs/guides/VALIDATION_GUIDE.md`
- Round-trip testing: `scripts/test_roundtrip.py`

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

**Last Updated**: 2025-12-21
**Status**: Active test collections
