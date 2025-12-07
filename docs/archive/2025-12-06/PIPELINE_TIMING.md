# Pipeline Performance Tracking

## Historical Performance Data

### Run 2025-12-06 18:17 (With WAV rendering)
- **Duration**: 269 seconds (4.5 minutes)  
- **Files**: 18
- **Per file**: 15.0 seconds avg
- **Bottleneck**: WAV rendering timeouts (120s each)

### Run 2025-12-06 18:25 (WAV disabled)  
- **Duration**: 151 seconds (2.5 minutes)
- **Files**: 18
- **Per file**: 8.4 seconds avg
- **Improvement**: 44% faster

## Performance Baselines (per file)

| Step | Expected Time | Alert If > |
|------|--------------|------------|
| 1. SID→SF2 conversion | 0.5s | 2s |
| 2. SF2→SID packing | 0.5s | 2s |
| 3. Siddump (both) | 2.0s | 5s |
| 4. WAV rendering | DISABLED | N/A |
| 5. Hexdump (both) | 0.2s | 1s |
| 6. SIDwinder trace (both) | 2.0s | 10s |
| 7. Info.txt | 0.1s | 1s |
| 8. Annotated disasm | 0.5s | 2s |
| 9. SIDwinder disasm (both) | 1.0s | 5s |

## Performance Alerts

⚠️ **WAV Rendering**: Disabled due to failures  
- Root cause: Corrupt exported SID files from packer bug
- When fixed, expected time: <5s per file

## Optimization Roadmap

1. ✅ **Disable WAV rendering** - 44% speedup (DONE)
2. ⏳ **Add parallel processing** - Expected 300-400% speedup
3. ⏳ **Fix packer bug** - Will enable WAV generation
4. ⏳ **Optimize siddump** - Can parallelize original vs exported

## Target Performance

- **Current**: 151 seconds (18 files)
- **With parallelization (6 workers)**: ~30 seconds
- **Theoretical best**: ~20 seconds

