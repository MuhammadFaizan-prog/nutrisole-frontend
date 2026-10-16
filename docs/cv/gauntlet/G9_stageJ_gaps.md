# G9 Stage J2: closing the remaining evidence gaps (no training)

**Status: H3 BLOCKED. Human-verified images: 0. Genuine human exports: 0. kappa: not calculated.** The AI visual review stays
`AI_ASSISTED_NOT_HUMAN`. Its labels are not ground truth, not adjudication input and not training labels. Here they are used only to estimate
survival rates for an exploratory yield projection (section 4). No training ran, Kaggle GPU was not used, M-TEST content was not opened, no eval
image was moved into training, frozen Stage J files were not modified (`j_blind_key.csv`, `j_partitions.json`, `j_batches.json`, `j_packs.json`,
the guide and the readiness doc are unchanged), and main was not touched. New material lives in `ml/runs/G9/stageJ/out/gaps/`.

## 1. Git reconcile
- Confirmed the remote `cv-gauntlet` head with `branch_get`: `05079d3eb031d52136a832b52a19e7e6534f8cda` (parent `c5b0c5c7759f4652ed161327f322610036b6b010`,
  parent `4d35a7c` = our earlier local `31c3600`).
- `c5b0c5c` ("audit annotation handoff and require independent human evidence") added 34 files and modified `j_agree.py`, `j_tool_test.py` and
  `test_j_agree.py`. New files: `j_annotation.py`, `j_handoff.py`, `test_j_handoff.py`, `.gitattributes` (`out/handoff/** -text`), the
  `out/handoff/20261015/` audit set and `docs/cv/gauntlet/G9J_handoff_workflow.md`. `05079d3` added the 41-file `20261015_visual_review/` set and
  updated the workflow doc.
- The sandbox can't `git pull` (HTTP 502), so both commits were rebuilt from the contents API as local mirror commits `1eabea6` (= c5b0c5c) and
  `e748089` (= 05079d3), with author and date preserved. All 78 blob shas match the API. The full recursive remote tree (2348 blobs) is identical
  to the local tree in paths and blob shas. The only difference is 58 old exec-bit modes (100755 locally, 100644 remotely). The contents API
  can't set modes, so the tree sha differs for that reason alone.
- `gh_sync_state.json` now has `last_synced = e748089`, with `remote_head = 05079d3` in its note. Future syncs diff from e748089 and never rewrite his commits.

## 2. Handoff verification
- The committed `AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv` equals the ZIP CSV (sha256 `4bf78b68f478…44b6ef9`). All 41
  ZIP files are byte-identical to the committed copies.
- His `REPRODUCE.ps1` consistency check, run as Python: PASS (265 rows, schema, stable ids, order and image hashes, notes and tags, queue 157,
  provenance AI_ASSISTED_NOT_HUMAN, human_verified 0, H3 BLOCKED).
- Stage J regressions: 36/36 before the change. **Full Python suite: 105 passed**, reproducing his count. `j_tool_test.py` was excluded from
  collection because it is a Playwright CLI script with no test functions and Playwright isn't installed here, so it adds no tests either way.
- j_agree guard: `validate_human_pair` already refuses the exact AI payload. It auto-discovers every committed
  `out/handoff/*/AI_ASSISTED_NOT_HUMAN/*.csv`, refuses AI or test names, and refuses duplicate files. **Gap found and closed:** an AI CSV with a
  few rows edited changed the fingerprint and passed. Added a near-copy guard: an annotator table that is ≥ 95 % identical (label, name, what,
  tags) to any known AI table on ≥ 20 shared items is refused. Added 4 tests: the real committed review renamed as a person is refused without
  `--ai-csv`, as is a copy with 5 rows edited (98 % identical); unmodified AI rows are refused; the threshold lets genuinely different labels
  through. Also added 1 test for the J2 key separation. **Stage J 41/41; full suite 110 passed** after this stage's changes.

## 3. Rate-limited originals
All **15/15** previously-429 Commons originals were retrieved. Requests were sequential, one at a time, with 4 s spacing, a descriptive
User-Agent with contact details, Retry-After honoured and at most 2 retries. Each file returned HTTP 200 on the first attempt. Every original
matches its Stage I candidate (pHash distance 0, or 2 for P049). All licences are compliant (CC0, CC BY 2.0/3.0/4.0, CC BY-SA 2.0/3.0/4.0),
and every source page matches the blind key. Pixels are not committed. sha256, size and pHash are in `j2_source_original_retry.json`. A
≤ 2048 px adjudicator-only zip with attribution was made for full-resolution follow-up. Together with P134, 16 of the 16 targeted originals are
now recovered. This shows the files are identical to the Commons originals; it does not, by itself, rebuild the historical byte chain for the
other 249 pilot items.

## 4. Eval yield (EXPLORATORY projection, not labels)
Per-stratum survival rates (source × source-kind × source-label) come from the AI review of the 265 pilot. "Strict" counts only AI-high-confidence
rows with no review flag. The new targeted packaging and occluded Commons queries have no pilot precedent, so priors are assumed
(packaging 0.15–0.25, occluded 0.08–0.15).

| Scenario | apple | banana | citrus | tomato | carrot | unsupp.+other | printed | packaging | occluded | negatives |
|---|---|---|---|---|---|---|---|---|---|---|
| Pilot 265, AI optimistic | 12 | 18 | 15 | 18 | 22 | 42 | 42 | 1 | 3 | 96 |
| Pilot 265, AI strict (high conf., no flag) | 7 | 9 | 3 | 16 | 12 | 14 | 41 | 0 | 0 | 61 |
| Pilot+pilot2, optimistic (+0.25/0.15 priors) | 39 | 42 | 50 | 34 | 37 | 47 | 61 | 17 | 15 | 153 |
| Pilot+pilot2, strict (+0.15/0.08 priors) | 23 | 21 | 11 | 30 | 22 | 17 | 58 | 9 | 6 | 101 |

The 265-photo pilot alone is short: apple 12, citrus 15, banana 18 and tomato 18 even on the optimistic reading, with packaging 1 and occluded 3.
**With pilot2** the optimistic projection clears every R2 count (each class ≥ 33, negatives ≈ 150, all sub-quotas). The strict projection is
still short on citrus (≈ 11), banana (≈ 21, marginal) and unsupported+other (≈ 17 vs 25), and occluded is uncertain (6–11). Much of that
strictness is AI caution (for example, FruitNet citrus flagged citrus_vs_lime at medium confidence), which human annotators will resolve. Only
human labels decide.

**Pilot2** (`j2_select.py`, seed 12, blind ids P501–P835, J-eval only, 335 photos). Composition by source label:
apple 63 (FruitNet 39, Commons eval 11, new Commons 13), citrus 58 (FruitNet 50, new Commons 8), banana 34 (FruitNet 22, Commons 12), tomato
26 (tomato_m 14, Commons 12), carrot 17 (carrot_m 14, Commons 3), **packaging 63, partly hidden 74** (new Commons, eval-bucket uploaders only).
Sources: existing eval pool 133 reps not used in pilot 1; 44 new FruitNet Good-quality Orange/Apple rows (FruitNet is already a whole-J-eval
source); 158 new Commons files.

## 5. Packaging and occluded (eval only)
Commons per-file CC/PD only. Banned origins (Pexels, Pixabay, Mixkit, Unsplash) were rejected on title, credit, artist and description, and
no NC/ND licence was accepted. 30 targeted queries were run. Uploaders had to hash to the frozen eval buckets (sha1 % 10 in 4–9) and not be a
J-train or J-dev person: 111 were skipped by person and 82 by bucket. After the audit, **63 packaging and 74 partly hidden** candidates are in
pilot2. Commons search is noisy: some returns are cars, cooked food, people and so on. That is expected, and the annotators will label them
`uncertain` or as negatives.

## 6. Training gap: new J-train candidates (Mendeley CC BY 4.0, licence checked via the public API first)
| Dataset | Decision |
|---|---|
| y3649cmgg6 Mango & Banana (India) | used: 58 banana + 15 mango negatives (UUID-named originals; `_0_` augmented copies skipped) |
| 56td5w4wz2 Banana & Guava (Redmi Note 10 Pro) | used: 60 banana (Class A/B) + 13 guava negatives |
| 6nxnjbn9w6 VegNet | used: 43 tomato (Ripe/Unripe) + 19 pepper/chili negatives |
| chv7dmvtfm veg_in (rest) | used: 68 tomato, 51 carrot, 29 vegetable negatives |
| 6ps7gtp2wg Spoiled & fresh fruit (224 px) | used, FRESH folders only: 40 banana, 39 orange, 38 tomato, 21 other-fruit negatives |
| bxfgvsn9kw citrus_tw (rest) | used: 17 citrus after near-dup quarantine |
| 7vb4djkbrc Banana Prata Catarina | skipped: single 1.2 GB RAR (not range-readable, no extractor) |
| j9sp322drp Ripen Banana | skipped: files 4.2 / 4.5 GB (> 1.5 GB) |
| y5h6v8w6ms Multispectral apples | skipped: 1.56 GB zip; the other parts are RAR and multispectral |
| b9rvg4f2st Vegetables Bangladesh | skipped: single 2.08 GB zip |
| s42kpg8h37 Tomato Maturity | skipped: 2.4 / 3.1 GB files |

Plus 135 Commons apple candidates from train-side uploaders (`commons_t2`; §7 lists "more Commons" for apple), with no J-dev, J-eval or
pilot2 person allowed.
**Audit** (`j2_audit.py`): 907 new files, all licence-compliant. 59 quarantined: 22 near-dups of earlier
reference sets (the reference list includes M-TEST hashes only), 22 near-dups of Stage J items, 8 within-source near-dups, and 7 person clashes
with eval owners. **Kept 848: J-train 646, pilot2 new 202.** There are 0 cross-split near-duplicates. The new datasets are not
eval sources.

**Training pack 2** (blind T501–T1146, 646 photos, same tool): apple 135, banana 158, tomato 149, citrus 56, carrot 51, 97 real-photo
negatives (mango, guava, pepper/chili, onion, potato, brinjal, garlic, ginger, chilli, lulo, strawberry, tamarillo).

## 7. Updated training-gap table (T1 ≥ 150 verified per class; expected yield Commons 0.55, datasets 0.90; human-verified = 0)
| Class | Stage J cands | Stage J exp. | J2 new (by source) | J2 exp. | Total exp. | Remaining shortfall | Sources |
|---|---|---|---|---|---|---|---|
| apple | 20 | 11 | 135 (commons_t2:135) | 74 | 85 | **65** | 2 |
| banana | 7 | 4 | 158 (bg_in:60, mb_in:58, sp_co:40) | 142 | 146 | **4** | 4 |
| citrus | 135 | 92 | 56 (citrus_tw:17, sp_co:39) | 50 | 142 | **8** | 4 |
| tomato | 14 | 8 | 149 (sp_co:38, veg_in:68, vegnet:43) | 134 | 142 | **8** | 4 |
| carrot | 138 | 105 | 51 (veg_in:51) | 46 | 151 | **0** | 4 |
| negatives (real-photo, J-train) | 65 | 65 | 97 (bg_in:13, mb_in:15, sp_co:21, veg_in:29, vegnet:19) | 87 | 152 | **0** | 6 |

Apple stays short (~65) because no usable CC BY apple dataset was within the size and format rules. Next options are *Multi-Stage Apple*
gfcmdbvw65 (outside this brief's list) or team phone photos. Banana, citrus and tomato come within ~4–8 of the target, carrot and negatives are
projected to meet it, and every class now has ≥ 2 sources. The 224 px sp_co images add class volume at low resolution.

## 8. Packs (offline tool, guide and format identical to Stage J)
| Zip | MB | Photos | sha256 |
|---|---|---|---|
| nutrisole_G9J_pilot2_annotator1.zip | 23.2 | 335 | `ab5d4f31537a9e02…` |
| nutrisole_G9J_pilot2_annotator2.zip | 23.2 | 335 | `e5f1543814be40c8…` |
| nutrisole_G9J_train2_annotator1.zip | 26.3 | 646 | `5353caf7c3965bd3…` |
| nutrisole_G9J_train2_annotator2.zip | 26.3 | 646 | `2433083569abaa73…` |

There is no Chromium in the sandbox this session, so the headless smoke test could not be re-run. `j2_pack_check.py` instead verifies that the
HTML equals the browser-tested template once the data is substituted back (so the tool code is byte-identical). It also checks that ids match
the key, all JPEGs decode with no EXIF, the two copies hold the same ids in different orders, the fallback CSV order matches, contact sheets
are complete, and `node --check` passes. Everything passes. `j_agree.py` now accepts `--batch pilot2|train2`, which uses `out/gaps/j2_blind_key.csv`.
R2 is judged on pilot + pilot2 together.

## 9. What is still needed (people)
Two independent people label pilot (265) + pilot2 (335) and training packs 1 (461) + 2 (646) on their own original copies, with no AI notes,
then sign the hash-bound attestations. A third person adjudicates. Apple training data still needs another source.
Files: `out/gaps/` (j2_candidates.json, j2_licence.csv, j2_quarantine.csv, j2_audit_summary.json, j2_mendeley_licences.json, j2_blind_key.csv
(adjudicator only), j2_batches.json, j2_packs.json, j2_pack_check.json, j2_eval_yield_projection.json, j2_training_gap.csv,
j2_partition_stats.json, j2_readiness.json (BLOCKED), j2_source_original_retry.json). Scripts: `j2_audit.py`, `j2_select.py`, `j2_yield.py`,
`j2_pack.py`, `j2_pack_check.py`, `j2_gap.py`. Collectors: `j2_collect_mendeley.py`, `j2_collect_commons.py` (images stored in the sandbox under /workspace/work/g9j2, not committed).

## 10. Pilot 2 visual-review follow-up (2026-10-15, AI-assisted)

The supplied 335-image Pilot 2 ZIPs were independently checked locally and all photographs visually reviewed.
Versioned results are in `out/handoff/20261015_pilot2_visual_review/`, explicitly `AI_ASSISTED_NOT_HUMAN`.
Counts: apple 44, banana 24, citrus/orange 37, tomato 23, carrot 25, other produce 14, printed/screen 49,
occluded 0, uncertain 119. The post-hoc queue contains 233 checks (77 HIGH, 65 MEDIUM, 91 LOW).
Many uncertain cases are clear no-target scenes or cooked foods under the annotation guide.

The 63 packaging and 74 hidden-query categories above remain collection strata. They do not prove actual
packaged/occluded evaluation coverage: this review finds only eight identifiable real-produce images with B
(five with a showcase label), no definite primary occluded case, and four potential occlusion/main-item checks.
Repeated/cropped views also require grouping; for example Pilot 1 P134 and Pilot 2 P731 show the cropped/wider
foot-carrot photograph. No IDs, frozen memberships or earlier results were changed.

Both original Pilot 2 HTML tools now pass an actual offline headless smoke test locally (335 export rows,
autosave/reload, import, stable IDs and Unicode/CSV round-trip); this supplements the earlier sandbox limitation.
The explicit Pilot 2 AI validation path, all 42 Stage J tests, all 111 ML tests and 28 protected runtime files pass.
All 30 historical frozen-input hashes and the 14 existing J2 gap files are preserved. Available combined J1/J2
metadata/pHashes show no cross-split conflict, but the earlier external reference hash store was not recovered.

The review used 17 contact sheets and 100 additional native-package detail inspections; no Pilot 2 source
original was viewed. Three original-file download attempts returned HTTP 429. Confidence remains subjective,
and source licensing/original-byte identity still needs review. Human-verified remains **0**, kappa remains
unavailable, and **H3 stays BLOCKED**. The projected training deficits in section 7, including the smaller banana,
citrus and tomato shortages, remain unresolved by evaluation-image AI review.
