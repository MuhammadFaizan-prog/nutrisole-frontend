# Stage J handoff implementation and usage

The supplied execution specification is the design for this change. Keep the nine-label taxonomy, the G3 champion, H0/H1/H2,
all frozen gates, all data memberships, and the complete app intact. Extend `j_agree.py`; add one shared CSV/provenance validator
and one read-only audit/report command. Reports distinguish recorded source metadata, automated checks, AI assistance, human
self-attestation, and missing evidence. No command in this workflow starts training.

Implementation sequence (2026-10-15):

- [x] Add failing regression tests for strict CSV validation, stable IDs, independent-human evidence, AI-copy rejection,
  subtype/tag disagreements, undefined kappa, split leakage, and a blocked H3 gate.
- [x] Implement `j_annotation.py`, then improve the existing `j_agree.py` agreement/adjudication flow.
- [x] Implement `j_handoff.py` to audit the original ZIPs, source/license records, frozen partitions and training shortages.
- [x] Make the existing offline tool smoke test portable and test both supplied copies in an isolated offline browser.
- [x] Generate versioned reports without filling in missing labels or overwriting historical artifacts.
- [x] Run the Stage J, Python, TypeScript, native and runtime-preservation checks; record limitations.
- [x] Independently review the exact diff and fix the three findings. Commit/push/PR synchronization is reported in the final handoff.

## Inputs and boundaries

The authoritative current results are under `ml/runs/G9/stageJ/out/handoff/20261015/`. That directory is for the lead and
adjudicator **after** the two independent exports. Give annotators only their original ZIP. Do not send this directory,
`j_blind_key.csv`, source labels, AI suggestions or the review-priority sheet to independent annotators.

Present: the two original pilot ZIPs, their unchanged extracted HTML tools, guide and blank fallback CSVs, and the committed
Stage I/J manifests. Missing: the AI handoff ZIP and all three named contents; genuine human exports; original training ZIPs;
full-resolution original/download stores and their byte provenance; earlier reference hash stores. Historical `TestAnnotator`
exports are synthetic smoke-test outputs. Do not import them as human work. Browser-saved personal labels must be exported by
the person using that browser; this workflow never reads their storage.

Pilot is evaluation only. The training batch includes **382 J-train + 79 J-dev representatives**, not 461 training examples.
The old guide's 458 is stale. Original physical training ZIP inventory cannot be rechecked until those files are recovered.
The prepared blank training CSVs are explicitly incomplete materials without photos, not replacement packs.

## Reproduce the audit and tests (PowerShell from the repository root)

```powershell
$py = Join-Path $env:TEMP 'nutrisole-g9j-python-20261015\Scripts\python.exe'
$stage = 'ml/runs/G9/stageJ'
& $py -X utf8 "$stage/scripts/j_handoff.py" `
  --pack1 '../nutrisole_G9J_pilot_annotator1.zip' `
  --pack2 '../nutrisole_G9J_pilot_annotator2.zip' `
  --out "$stage/out/handoff/reproduction-20261015"
& $py -X utf8 -m pytest "$stage/scripts/test_j_agree.py" "$stage/scripts/test_j_handoff.py" -q
```

Each output path must be new. Re-running into existing reports is rejected. Audit success means the check executed;
`G9J_H3_readiness.json: BLOCKED` is still the expected dataset verdict. The 36 Stage J regression tests include known-AI copies
renamed as people, forged/missing human evidence, duplicate IDs, malformed CSV values, constant-category kappa, subtype/all-tag
disagreements, whitespace adjudication flags, a non-third adjudicator, immutable original agreement, frozen membership and
readiness batch/run binding. Tests use temporary synthetic fixtures only.

For a fresh audit-only Python environment, use Python 3.13 with `pytest pillow numpy scipy imagehash playwright`. The full
existing Python suite additionally uses `opencv-python`, `requests`, `beautifulsoup4`, `lxml`, `onnxruntime`,
`ultralytics==8.4.175` and `lap` (the dependency resolver supplies torch/torchvision). Exact installed versions are recorded in
the validation evidence. Installing test dependencies does not run training or inference on the pilot.

The existing camera test hardcodes the old Linux checkout. This **temporary test-runner path adapter** runs its original
assertions against this checkout without editing any evaluation source or changing test logic. UTF-8 is needed for Urdu fixtures:

```powershell
@'
import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path('ml/eval').resolve()))
import test_camera_io
test_camera_io.R = str(pathlib.Path.cwd())
raise SystemExit(pytest.main(['ml', '-q', '--tb=short']))
'@ | & $py -X utf8 -
npm test
npm --prefix native test
npm run test:expansion
npm run test:sites
npm run check:runtime
npm run build
npm --prefix native run typecheck
npm run test:runtime -- --reporter=line --workers=1
```

`G9J_validation_results.md/json` state the actual outcomes and pre-existing/environment limitations. Passing Python/TS tests
does not prove on-device camera, installer, actual missing ONNX checkpoints, or backend integration QA. No app/backend source
is changed in this task.

For each original HTML, test offline in a disposable profile (never the person's profile):

```powershell
& $py -X utf8 "$stage/scripts/j_tool_test.py" `
  'C:/Users/DELL/Downloads/nutrisole_G9J_pilot_annotator1/NutriSole_labelling_pilot_annotator1.html' `
  (Join-Path $env:TEMP 'nutrisole-g9j-offline-repro-a')
& $py -X utf8 "$stage/scripts/j_tool_test.py" `
  'C:/Users/DELL/Downloads/nutrisole_G9J_pilot_annotator2/NutriSole_labelling_pilot_annotator2.html' `
  (Join-Path $env:TEMP 'nutrisole-g9j-offline-repro-b')
```

Use `--browser` for an installed Chromium binary when autodiscovery is unavailable. This uses an isolated automation browser,
not the user's Chrome session. The test checks offline save/reload, 265-row export, stable IDs, tags, import and UTF-8 CSV
escaping. Its three labels are always **AUTOMATION_TEST_NOT_HUMAN** and are rejected by human validation.

## When the missing AI handoff is recovered

Extract it to a separate local folder, read its README, and rerun the audit into a **new** output directory with these extra args:

```powershell
--ai-csv 'AI-folder/nutrisole_G9J_AI_assisted_pilot_labels_265.csv' `
--review-queue 'AI-folder/nutrisole_G9J_AI_review_queue.csv' `
--ai-readme 'AI-folder/nutrisole_G9J_AI_annotation_handoff_README.txt'
```

The entire AI CSV is validated for the exact 15 columns, IDs, coverage, labels, flags, encoding and duplicates. Actual counts
are compared to the request's unverified distribution. Original CSV bytes are saved with SHA256 under
`AI_ASSISTED_NOT_HUMAN/`. The original queue must have unique pilot IDs; its actual size is reported. The generated 265-row
post-hoc priority report is not represented as the missing 113-row queue. Known AI payload fingerprints are rejected from
human slots even if names, notes, ordering or timestamps change. Automatically discovered AI registries must remain present
alongside human agreement reports; `--ai-csv` can explicitly include additional known AI inputs.

## When genuine independent human CSVs are available

1. Obtain original-copy exports from two distinct real people who did not see AI or peer labels. If either was exposed, record
   that fact; do not claim independence. A fallback export may omit optional columns, but absent tag columns remain unknown
   and must be adjudicated. Do not silently convert unknown flags to zero.
2. Copy `human_evidence.BLANK.template.json` to a separate input directory. Each person supplies their real name, original copy,
   exact CSV SHA256, timezone-bearing `attested_at`, and truthful `independently_labelled` / `no_ai_or_peer_labels_seen` values.
   Compute a hash with `(Get-FileHash -Algorithm SHA256 -LiteralPath 'A.csv').Hash.ToLower()`. The blank template deliberately
   fails validation. Self-attestations are evidence from people, not cryptographic proof of their identity or honesty.
3. Run the existing agreement command with that evidence and both originals:

```powershell
& $py -X utf8 "$stage/scripts/j_agree.py" agree 'A.csv' 'B.csv' --batch pilot `
  --evidence 'human_evidence.json' --out "$stage/out/handoff/human-pilot-run1/agreement"
```

Add `--ai-csv` for a recovered known AI input. The script snapshots exact original CSVs, evidence, normalized A/B history and
the original agreement report. Joins use stable item IDs. All primary-label, subtype, underlying-item and C/B/M/X differences,
missing labels/tags and uncertain cases go to `adjudication_sheet.csv`. Agreement is computed on jointly labeled items; missing
coverage blocks completeness. Cohen's kappa is undefined for a single constant category and cannot pass the gate.

4. A third distinct real person completes a copy of `adjudication_sheet.csv`. Supply `final_label` or explicit `exclude`, a reason,
   and explicit final subtype/tag decisions for mismatches. Blank/space-only disputed tags remain unresolved. `uncertain` and
   `exclude` stay excluded. The adjudicator must inspect full-resolution originals for difficult images; the provided 640px
   JPEGs and contact sheets cannot establish that review. Nobody may substitute AI review for this person.
5. Import final decisions into a separate versioned output directory:

```powershell
& $py -X utf8 "$stage/scripts/j_agree.py" verify --batch pilot `
  --agree-dir "$stage/out/handoff/human-pilot-run1/agreement" `
  --adjudicated 'completed_adjudication.csv' `
  --out "$stage/out/handoff/human-pilot-run1/verified"
```

Use repeatable `--image-root` for original image directories keyed by candidate ID. Supply `--identity-manifest` only when
the original ingestion chain is recovered: CSV columns `key,image_sha256,source_url,file_url`, matching the recorded source
and actual original bytes. Hashing an arbitrary new file does not establish its provenance. Missing identity/license evidence
always leaves `release_eligible=false`. Original adjudication and identity CSVs are snapshotted with hashes. The final manifest
and `.sha256` are separate from the immutable original agreement; adjudication never improves the original kappa.

6. Repeat with `--batch train` for the recovered separate 461-item batch. J-train and J-dev counts remain separate. Do not
   resolve shortages using pilot/J-eval or earlier locked holdouts. Use the training-gap report to collect licensed diverse
   phone-style training close-ups and negatives from appropriately separated sources.

The pure `assess_readiness` helper in `j_handoff.py` requires correct batch, matching agreement document/evidence hashes and
the original kappa in the verified summary. When using it on future reports, add the actual agreement file's byte SHA256 as
`document_sha256`; do not invent values or reuse another run. Audit R4 (committed pre-model freeze), source/session diversity,
original-byte licensing and all earlier reference hashes separately. The current report names every missing R/T prerequisite.
All gates must be satisfied and reported to the user before a later explicit training go. No tool here launches H3/Kaggle/GPU work.
