#!/usr/bin/env python3
"""Test all 22 sequences to find best match with reference"""

from sf2_viewer_core import SF2Parser
from compare_track3_flexible import FlexibleReferenceParser, Track3Comparator

parser = SF2Parser('learnings/Laxity - Stinsen - Last Night Of 89.sf2')
ref = FlexibleReferenceParser('track_3.txt')

print(f'Reference has {len(ref.entries)} steps')
print()
print('=' * 100)
print('TESTING ALL 22 SEQUENCES')
print('=' * 100)
print()
print('Seq | Total | Track3 | Match% | Matches/Total | Status')
print('----|-------|--------|--------|---------------|------------------')

results = []

for seq_idx in sorted(parser.sequences.keys()):
    seq = parser.sequences[seq_idx]
    track3_count = len(seq[2::3])

    try:
        comparator = Track3Comparator('learnings/Laxity - Stinsen - Last Night Of 89.sf2', 'track_3.txt', seq_idx)
        matches, total, diffs = comparator.compare()
        match_rate = 100 * matches / total if total > 0 else 0

        results.append({
            'seq_idx': seq_idx,
            'total': len(seq),
            'track3': track3_count,
            'match_rate': match_rate,
            'matches': matches,
            'total_steps': total
        })

        status = ''
        if match_rate > 50:
            status = '<-- GOOD MATCH!'
        elif match_rate > 30:
            status = '<-- Partial match'
        elif track3_count == len(ref.entries):
            status = '<-- Same length'

        print(f'{seq_idx:3d} | {len(seq):5d} | {track3_count:6d} | {match_rate:5.1f}% | {matches:5d}/{total:5d} | {status}')
    except Exception as e:
        print(f'{seq_idx:3d} | {len(seq):5d} | {track3_count:6d} | ERROR | {str(e)[:30]}')

# Sort by match rate
results.sort(key=lambda x: x['match_rate'], reverse=True)

print()
print('=' * 100)
print('TOP 10 MATCHES (sorted by match rate)')
print('=' * 100)
print()
print('Rank | Seq | Total | Track3 | Match% | Matches/Total')
print('-----|-----|-------|--------|--------|---------------')

for i, result in enumerate(results[:10], 1):
    print(f'{i:4d} | {result["seq_idx"]:3d} | {result["total"]:5d} | {result["track3"]:6d} | {result["match_rate"]:5.1f}% | {result["matches"]:5d}/{result["total_steps"]:5d}')

print()
print('=' * 100)
print(f'BEST MATCH: Sequence {results[0]["seq_idx"]} with {results[0]["match_rate"]:.1f}% match rate')
print('=' * 100)

if results[0]['match_rate'] >= 80:
    print()
    print('✓ EXCELLENT MATCH FOUND!')
    print(f'  Sequence {results[0]["seq_idx"]} matches {results[0]["match_rate"]:.1f}% of reference')
elif results[0]['match_rate'] >= 50:
    print()
    print('✓ GOOD MATCH FOUND!')
    print(f'  Sequence {results[0]["seq_idx"]} matches {results[0]["match_rate"]:.1f}% of reference')
elif results[0]['match_rate'] >= 30:
    print()
    print('⚠ PARTIAL MATCH FOUND')
    print(f'  Sequence {results[0]["seq_idx"]} matches {results[0]["match_rate"]:.1f}% of reference')
else:
    print()
    print('✗ NO GOOD MATCH FOUND')
    print(f'  Best match is sequence {results[0]["seq_idx"]} with only {results[0]["match_rate"]:.1f}% match')
    print('  This suggests the reference might be from a different file or sequence format')
