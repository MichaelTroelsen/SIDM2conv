"""Show top AI-detected tables summary"""
from ai_table_detector import AITableDetector

detector = AITableDetector('../analysis/Ocean_Loader_1_temp.asm')
candidates = detector.analyze()

# Group by type
by_type = {}
for c in candidates:
    if c.table_type not in by_type:
        by_type[c.table_type] = []
    by_type[c.table_type].append(c)

print('\n' + '='*80)
print('TOP AI-DETECTED MUSIC TABLES (Galway Player - Ocean Loader 1)')
print('='*80)

for table_type in ['note_freq', 'instrument', 'arpeggio', 'wave', 'pulse', 'filter']:
    if table_type not in by_type:
        continue
    print(f'\n{table_type.upper()} TABLES (Top 5):')
    print('-' * 80)
    for candidate in sorted(by_type[table_type], key=lambda c: c.confidence, reverse=True)[:5]:
        print(f'  ${candidate.address:04X} - {candidate.size:3d} bytes - {candidate.confidence:5.0%} confidence')
        for reason in candidate.reasons[:2]:  # Show first 2 reasons
            print(f'    * {reason}')
        if candidate.size <= 32:
            hex_str = ' '.join(f'${b:02X}' for b in candidate.data[:8])
            if len(candidate.data) > 8:
                hex_str += '...'
            print(f'    Data: {hex_str}')
