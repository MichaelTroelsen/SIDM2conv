Closing — this landed as `d1b32d0` ("feat(laxity): land PR #5's all-6-in-reads floor, re-measured against today's corpus").

The `ch_seq_ptr_scanner` all-6-in-reads floor and its two regression tests (`test_lifts_min_axel_f_all6_reads`, `test_lifts_only_love_all6_reads`) are already on `master` in that commit, along with `pyscript/annotate_asm.py`'s NameError fix. `sidm2/conversion_pipeline.py`'s NameError fix from this PR was deliberately *not* carried forward — 8 commits have touched that file since this PR's May base (including native-dispatch wiring this PR's copy predates), and the NameError it fixed no longer reproduces on current `master`.

The PR description's 87% → 92% (251→264/286) headline is from May and is now 114 commits stale. `d1b32d0` re-measured the same +13-file lift against today's corpus instead of carrying that number forward: **253/286 (88.5%) → 266/286 (93.0%)**. Full suite at merge time: 2602 passed / 8 skipped / 2 xfailed.

Since all of this PR's applicable content is already on `master`, merging it now would be a no-op diff. Closing without merge.
