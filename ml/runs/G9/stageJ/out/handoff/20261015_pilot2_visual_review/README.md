# Pilot 2: AI visual review of all 335 supplied images

**Provenance: `AI_ASSISTED_NOT_HUMAN`. Project-lead / post-hoc review material. Keep this folder away from the two independent annotators until both have exported.**

All P501–P835 received an individual visual assessment, tag decisions, a note and subjective confidence. This is a new review of the supplied Pilot 2 photographs, separate from the earlier 265-image review. Human-verified images and authentic independent exports remain **0**; kappa is **not computable**. **H3 remains BLOCKED.** No training, model promotion, deployment or merge to main was performed.

## Files to give the development agent

| File | Use |
|---|---|
| `AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335.csv` | All 335 annotations in the original 15-column export schema. |
| `G9J_pilot2_AI_per_image_review.csv` | All 335 notes, subjective confidence, review flags, package hashes, source URLs and provenance. |
| `nutrisole_G9J_pilot2_AI_review_queue.csv` | 233 post-hoc checks, sorted HIGH (77), MEDIUM (65), LOW (91). |
| `G9J_pilot2_visual_review_metadata.json` | Exact counts, inspected-image scope, source-context use and limitations. |
| `audit/` | Package identity, per-image provenance, duplicate candidates, stored-metadata split checks, frozen-input preservation, offline-tool results and blocked H3 assessment. |
| `REPRODUCE.py` | Recheck saved decisions, CSVs, stable IDs, original display indices, hashes, queue, preserved inputs and optional original ZIPs. |
| `review_batches/` | The nine saved visual-review batches. `review_revision_log.json` records the later P729 correction, including its previous assessment. |

The AI annotation CSV's SHA256 is `6c17debff4bb545bc8841abc140242d86a1fed86dc303ade4274eac35048d2aa`.
Its `pack_id` is **G9J-pilot2**, `copy` is the real **annotator1** display ordering, and `annotator` is explicitly **AI_ASSISTED_NOT_HUMAN**. Rows are presented by stable ID; `order_index` retains the original shuffled HTML position, never a newly invented index. `seconds=0` means **not measured**, not a claim about annotation speed. Timestamps are the actual batch save times, with P729's follow-up time recorded separately. No human names, exports, agreement scores or attestations were created.

## Label counts

| Primary label | Images |
|---|---:|
| apple | 44 |
| banana | 24 |
| citrus_orange | 37 |
| tomato | 23 |
| carrot | 25 |
| other_produce | 14 |
| printed_or_screen | 49 |
| occluded | 0 |
| uncertain | 119 |
| **Total** | **335** |

These are AI visual judgments, not measured accuracy, human ground truth or model predictions. Confidence is subjective: high 243, medium 74, low 18. A high-confidence `uncertain` often means the image clearly shows a cooked dish, car, document-free scene or another object outside the raw-produce taxonomy. It does not mean a specific fruit was confidently identified.

The original guide is retained: orange-type citrus stays separate from lemon/lime and grapefruit; artworks, screens and artificial produce use `printed_or_screen`; a clearly established real main item with less than about half visible uses `occluded`. Ordinary banana skin spotting does not alone establish the X tag. Shiny or unusually shaped real produce is not automatically a toy. Mixed scenes follow the centre-item rule rather than source search terms.

## Review scope and limits

- All **17 contact sheets**, containing all **335 unique IDs**, were viewed. **100 images** received an additional native-package detail inspection; those IDs are recorded per row.
- Supplied JPEGs are at most 640 pixels on the longest side, with many dataset images at 192/256 pixels. Detail views preserve native pixels; they are not recovered full-resolution originals.
- Local source filename/context was consulted for **8 IDs**: P632, P639, P658, P729, P731, P738, P756 and P773. These records are marked; the review is **not blind**. Source class labels were not automatically copied into annotations.
- Original-file downloads were attempted for P729, P756 and P773. All three returned **HTTP 429**; **0 source originals were viewed for this Pilot 2 review**. Other source originals were not retrieved in this run. Higher-resolution inspection remains pending where the per-image table requests it.
- The other agent's recovery of 15 older Pilot 1 originals is recorded in `out/gaps/j2_source_original_retry.json`. That historical record does not establish that those pixels were available or reviewed here, and the old Pilot 1 review is unchanged.
- Recorded licence/author/credit URLs were joined by candidate key for all Pilot 2 records. This does not independently establish the original-byte-to-licence chain or revalidate current remote permissions. No images are included in this handoff ZIP or promoted to release/training eligibility.

## Findings that affect readiness

The source/query categories **63 packaging** and **74 occluded** are collection strata, not verified image contents. Among the 74 hidden-query candidates, this visual review assigns 24 artwork/printed and 42 uncertain labels, with 8 identifiable raw-produce labels; none is a definite primary `occluded` case. The packaging stratum includes 44 uncertain and 6 artwork/printed cases. This does not establish the required packaged/occluded evaluation quotas.

Eight images have both an identifiable real-produce label and B: **P531, P571, P581, P602, P666, P759, P773, P780**. Only five of these have one of the five showcase labels; the other three contain berries. Counts include cut and ambiguous cases and do not establish clean independent evaluation coverage. Potential occlusion/central-target checks are **P533, P695, P729, P773**. P729's opaque central block prevents a confident central-produce assignment; its revision is retained in the log. Zero definite AI occluded labels must not be interpreted as proof that the dataset contains no occlusion.

There are **6 within-Pilot-2** and **3 cross-pilot** pHash candidate pairs at Hamming distance <=10, with **no byte-identical JPEG pairs** in those comparisons. A pHash candidate is not a duplicate finding. Manual related views include **P134/P731**, the cropped and wider foot-carrot photograph; **P205/P701**, related food still-life framing; **P587/P737/P753**, related fruit-bowl views; and **P783/P794/P834**, related carrot views. Counts are images, not independent scenes. Preserve the existing IDs/membership and resolve grouping before any future model evaluation freeze.

The existing split auditor was reused on stored Stage J1+J2 metadata and pHashes, adapting Commons-family source names to the unified uploader/artist comparison without changing manifests. It found **0 cross-split conflicts in the available records**. Earlier `/workspace/work/g9h` reference hashes and original video/session evidence are unavailable here, so this is not a fresh complete holdout-leakage clearance. M-TEST pixels were not opened. All 30 prior Git-LF frozen manifest/gate/history hashes and all 14 existing J2 gap artifacts remain unchanged.

The older J2 training-gap projection still shows shortfalls of apple **65**, banana **4**, citrus **8**, tomato **8**, carrot **0**. These are projected yields, with **0 human-verified training images**. Apple is the largest projected gap; it is not the only unresolved readiness requirement. Training pack 2 was not visually reviewed in this task, and no evaluation image was reassigned to training.

## Validation and reproduction

Both original supplied Pilot 2 ZIPs have 335 unique IDs, matching decoded per-ID JPEG bytes, different display orders, valid CRCs, matching unlabelled fallback order, the exact export schema and no external resources. Package SHA256 values match the pre-existing J2 records:

| Copy | SHA256 |
|---|---|
| annotator1 | `ab5d4f31537a9e02410eeefc1380c1efff934232e47f37f1dcfefca7c047ef58` |
| annotator2 | `e5f1543814be40c84024c8ab88c46b1e18c6000028e89e437cd535ac008c4cdf` |

Both HTML tools passed the existing headless smoke test in fresh disposable Playwright profiles with networking disabled: all 335 export rows, stable IDs, autosave/reload, import and comma/quote/newline/Unicode round-trip passed, with no page errors or external requests. Smoke-test rows are `AUTOMATION_TEST_NOT_HUMAN` and are not included as annotations.

The three final CSVs were authored with the bundled spreadsheet artifact tool and checked for exact getter/value round-trip; a rendered sample was inspected. The validator now accepts an explicit `batch="pilot2"` while retaining the original `pilot` default and rejecting mismatched/mixed pack IDs. One existing test's path comparison was made portable to Windows. **42 Stage J tests, all 111 ML tests and the 28-file mobile-runtime integrity check pass.** No app code changed; historical native/rendered/device acceptance limitations are not resolved by these checks.

Run from the repository root (replace the Python executable if needed):

```powershell
$py = 'C:\Users\DELL\AppData\Local\Temp\nutrisole-g9j-python-20261015\Scripts\python.exe'
$review = 'ml/runs/G9/stageJ/out/handoff/20261015_pilot2_visual_review'
& $py -X utf8 "$review/REPRODUCE.py" `
  --pack1 'C:\Users\DELL\Downloads\nutrisole_G9J_pilot2_annotator1.zip' `
  --pack2 'C:\Users\DELL\Downloads\nutrisole_G9J_pilot2_annotator2.zip'
& $py -X utf8 -m pytest ml/runs/G9/stageJ/scripts/test_j_agree.py ml/runs/G9/stageJ/scripts/test_j_handoff.py -q
npm run check:runtime
```

`--output NEW_FILE.json` saves a fresh consistency result; existing output files are never overwritten. Without the ZIP arguments it checks saved evidence only. Reproduction validates consistency and hashes, not the correctness of subjective visual labels. `SHA256SUMS.txt` binds the delivered files. Full-suite execution used UTF-8 and the previously documented temporary checkout-root adapter for the historical Linux camera-test path.

To repeat that full-suite invocation without editing the old camera test:

```powershell
@'
import pathlib, sys, pytest
sys.path.insert(0, str(pathlib.Path('ml/eval').resolve()))
import test_camera_io
test_camera_io.R = str(pathlib.Path.cwd())
raise SystemExit(pytest.main(['ml', '-q', '--tb=short']))
'@ | & $py -X utf8 -
```

## Human work still required

1. Give each of two unexposed people their original annotator ZIPs for both pilots, without these AI labels, source keys or notes. Obtain truthful original-copy CSVs and hash-bound independent attestations. Anyone exposed to AI/peer predictions must disclose it rather than attest no exposure.
2. Use `j_agree.py agree A.csv B.csv --batch pilot2 --evidence HUMAN_EVIDENCE.json --out NEW_AGREEMENT_DIR`, separately from `--batch pilot`. The committed AI CSV stays in the automatic known-AI registry. Never copy it into human slots or rename its annotator as a person.
3. A third distinct human inspects disagreements and difficult full-resolution originals, adjudicates with reasons, and uses the existing `verify --batch pilot2` workflow. Original independent kappa must remain separate from adjudication. Do not calculate kappa between the AI and itself or count AI rows toward human gates.
4. Reassess R1/R2 and every training/source/licence prerequisite using genuine human evidence. Preserve all exclusions, frozen gates and splits. H3 stays blocked until the protocol is met and a later explicit training go is given.

Work remains on **cv-gauntlet**, draft **PR #1**. This handoff does not authorize a merge, deploy, model promotion or GPU training.
