# Dataset split audit

**Automated checks on recorded manifests; original-byte/reference-store verification pending.**

Audited 956 items ({'J-dev': 79, 'J-eval': 485, 'J-train': 392}), including stored 64-bit pHashes, unified uploader/artist identity, dataset and duplicate groups. Cross-split conflicts: 0; manifest mismatches: 0.

Stage I versus Stage J eval: {'stageI': 486, 'stageJ': 485, 'removed': ['c0350'], 'added': []}. The removed c0350 was license-excluded previously; the old claim that membership was entirely unchanged needs this qualification. No membership was changed in this handoff. Pilot IDs remain 265 J-eval-only.

Preserved 14 previous quarantine decisions and 6 license exclusions. Original video/session metadata and earlier /workspace/work/g9h/eval_hashes.json, hset/hhash.json and refhash.json are missing. Their claimed reference comparison cannot be reproduced locally. M-TEST images were never opened. New cross-split conflicts, if any, are listed in G9J_split_quarantine.csv; eval stays frozen.
