# G9 Stage H: close-up identity verification and occlusion safety

**Status: INTERIM (H2 classifier still training on free Kaggle; kernel `mfaizannnn/nutrisole-g9h-h2`).** Prereg `G9_stageH_prereg.md`
(b9415a1, synced before any Stage H result). Branch `cv-gauntlet` only (draft PR #1 is the review path; no merge, main untouched).
G3 unchanged, no YOLO training, M-TEST not opened. All labels agent-verified: **exploratory results only**.

## Decision so far
**Not accepted yet (pending H2).** Without the close-up classifier, neither identity nor occlusion meets the frozen criteria:
- H0 and H1 both issue wrong identities and accept unsupported or cut items above the H-A2 / H-A3 limits.
- Mask-based occlusion cues alone halve the leakage but reject 35% of clean crops.

No A/B/C grade or grade-specific price is shown in the app (P6 contract in place and tested).

## Data (P1)
- **H-set:** 3595 Wikimedia Commons candidates (per-file CC / PD; never Pexels, Pixabay or Mixkit), 923 downloaded (Commons rate-limited
  the sandbox with HTTP 429).
- **Leakage audit:** pHash against 9272 references (G3 train 3562, DEV val and clips, Stage D/E/F pools 1607, M-DEV / M-TEST hashes 746,
  CU 190) plus Commons title overlap. **72 dropped:**
  - 50 title hits
  - 10 within-set duplicates
  - 6 near G3 train
  - 2 near Stage D
  - 2 near M-DEV/M-TEST
  - 2 near the DEV quality clip
- **Split by uploader:** train 417 / val 219 / eval 215 (`out/h_leak_split.json`). H-val and H-eval were triaged by the agent from
  contact sheets (`hval_triage.json`, `heval_triage.json`).
- **Identity items (`out/ident_items.jsonl`, 378):**
  - tune: CU-tune, CU-neg tune, H-val
  - eval: CU-check, CU-neg check, H-eval. Eval has 99 supported items and 77 negatives (unsupported / printed / cut).

## H0 vs H1 (eval, single still, tap at centre)
| Arm | Correct ID | Wrong ID | Abstain | Unsupported/cut accepted | Legit wrongly rejected |
|---|---|---|---|---|---|
| H0 (Stage G wide ID) | 46/99 (0.46) | 10/99 (0.10) | 0.43 | 13/77 (0.17; 10 cut, 3 unsupported) | n/a |
| H1 (G3 re-run on full-res crop must agree) | 29/99 (0.29) | 7/99 (0.07) | 0.64 | 10/77 (0.13) | 17/46 (0.37) |

- **Does G3 on the crop fix the error? No.** On the 10 eval items whose wide ID was wrong, the crop re-run **repeated the same wrong class 7
  times and corrected it 0 times**. It mostly removes correct IDs instead.
- **H1 latency:** p50 78 ms, p95 149 ms (sandbox CPU).
- **Stage G approach simulation on CU-check (H0, unchanged):** 19 identified, 6 correct, 11 graded, 8 on a wrong ID.

## Occlusion (P2)
- **The 35 Stage G leaks were reproduced exactly** (`out/leak35.json`): 24 occlusion, 7 blur, 4 low light; 9 / 9 / 11 / 6 at 96 / 128 / 192 /
  256 px.
- **Why they passed:** the condition model was ≥ 0.989 confident on every occluded leak, and the GrabCut visible fraction was 0.25-0.70,
  all above the 0.25 check. 16 of the 24 were rotten items whose visible half still showed rot. 23 of the 24 were on items without a
  correct wide ID (the feasibility suite graded regardless of identity).
- **Extended suite** (`scripts/h_occl.py`, 55 CU items x 96/192 px x 22 conditions; shaded, noisy occluders):
  - colour blocks (6 colours), skin 30%, synthetic hands (3 tones)
  - plastic bag (side 50% and full cover)
  - neighbouring produce (30% / 50%)
  - truncation (edge, and inner 25% / 40%)
  - the Stage G blur / low light / JPEG conditions
- **Stage G checks on CU-check (baseline):** occluder leakage **597 / 990 = 60%**. Examples:
  - grey block 78%, hands 67-80%, bag 76%, neighbour 67-78%, inner truncation 60-76%
  - the Stage G flat skin block 22%; edge truncation and JPEG 0%
- **Mask cues (solidity, ellipse IoU, straight-edge fraction, border fraction, segmentation agreement, flatness, colour split).** Picked on
  CU-tune, then applied to CU-check: leakage 60% -> **28%**, but **35% of clean crops are rejected** (`out/occlusion_noh2.json`). On these
  close-ups GrabCut masks are irregular even on clean items, so geometry alone cannot separate occluded from clean. The H2 half-crop
  agreement cue is pending.

## Done and tested
- `native/src/cv/pipeline/verify.ts` / `ml/eval/verify.py` + `ml/eval/occlusion.py`: identity policy H0 / P-a / P-b / P-c / H2-only,
  user-confirm, part agreement, occlusion rule, Stage H decision.
- `display.ts` / `display.py`: `closeupDisplay` (no A/B/C, no grade-specific price, category line only when verified).
- **Tests:** TS `cvVerify.test.ts` 10/10; Python `test_verify.py` + `test_closeup.py` 9/9.
- **Docs:** human-labelling protocol + CSV template; device plan with dependency review (`G9_stageH_device_test.md`); PC script
  `native/scripts/g9h-device-check.ps1`.
