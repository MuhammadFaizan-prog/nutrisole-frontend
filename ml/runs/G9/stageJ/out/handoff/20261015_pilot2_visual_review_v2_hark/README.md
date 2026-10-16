# Pilot 2 AI review v2 (Hark): recovered full-resolution originals P729, P756, P773

**Provenance: `AI_ASSISTED_NOT_HUMAN`. Post-hoc adjudicator material. Keep away from both independent annotators until both
exports and attestations are hash-recorded.** Human-verified images remain **0**.

This is a NEW versioned review. The project lead's `20261015_pilot2_visual_review/` (CSV sha256 `6c17deb...d2aa`, its SHA256SUMS,
revision log and every other file) is unchanged. v2 = v1 with three rows re-examined against the originals recovered on 2026-10-15
(sha256 recorded in `G9J_pilot2_source_original_retry_hark.json`; pixels are not committed, they sit in the adjudicator-only zip).

| Item | v1 | v2 | Change | Why (short) |
|---|---|---|---|---|
| P729 | uncertain (B M) | **carrot (B M)** | label changed | Original shows only whole real carrots, most fully visible through an open clear bag; the opaque thing is a cling-wrapped non-produce package on top. Same-kind pile + clear-bag rules give carrot+B+M. Adjudicator may still pick uncertain/exclude because the frame centre falls on the package; with B it is a must-not-grade packaged negative either way. |
| P756 | other_produce / other | other_produce / other | confirmed | Ridged orange fruit (Jacaratia spinosa), not a carrot; > half visible in the hand, so not occluded. Confidence medium -> high. |
| P773 | apple (B M) | apple (B M) | confirmed | Original is 536x471, identical size to the package (no extra resolution). Apples individually clear-wrapped plus one unwrapped apple; visible through wrap, not occluded. |

The full 335-row v2 export lives under `AI_ASSISTED_NOT_HUMAN/` so `j_agree.py` / `j_annotation.validate_human_pair` reject it, and
any >=95% near-copy of it, as independent human evidence (same rule as v1). Source context (file names) was used for all three
items, so this review is not blind. Regenerate / verify: `python3 scripts/j3_ai_review_v2.py [--check]`.
